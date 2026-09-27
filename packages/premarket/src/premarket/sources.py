"""Pre-market data sources. Each source fails on its own; the service marks it MISSING and carries on.

Sources are small classes registered by `type` name, built from `config/premarket.yaml`, so another
market (forex later) reuses the same types with its own symbols, feeds and rules.
Nothing here needs credentials or calls a broker.
"""

from __future__ import annotations

import http.cookiejar
import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Optional
from xml.etree import ElementTree

MAX_BYTES = 2_000_000
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) all_about_dhan-premarket/0.1 (paper research)"


# ------------------------------------------------------------------ fetchers


class OfflineError(RuntimeError):
    pass


class LiveFetcher:
    """Plain HTTPS GET with a short timeout and a size cap. One cookie jar per run (NSE needs one)."""

    def __init__(self, timeout_s: float = 6.0) -> None:
        self.timeout_s = timeout_s
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def get(self, key: str, url: str, headers: Optional[dict[str, str]] = None) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*", **(headers or {})})
        with self._opener.open(req, timeout=self.timeout_s) as resp:
            data = resp.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError(f"response over {MAX_BYTES} bytes")
        return data


class FixtureFetcher:
    """Reads `<dir>/<key>` instead of the network (synthetic fixtures, offline runs, tests)."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)

    def get(self, key: str, url: str, headers: Optional[dict[str, str]] = None) -> bytes:
        path = self.folder / key
        if not path.is_file():
            raise FileNotFoundError(f"no fixture {key}")
        return path.read_bytes()


class NoNetworkFetcher:
    def get(self, key: str, url: str, headers: Optional[dict[str, str]] = None) -> bytes:
        raise OfflineError("offline: network sources disabled")


def fixture_key(prefix: str, name: str) -> str:
    return f"{prefix}_{re.sub(r'[^A-Za-z0-9_.-]', '_', name)}"


# ------------------------------------------------------------------ results


@dataclass
class SourceContext:
    session_date: date
    now: datetime
    root: Path
    fetcher: Any
    stale_after_h: float = 96.0


@dataclass
class SourceResult:
    name: str
    status: str = "OK"  # OK | STALE | MISSING
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    as_of: Optional[str] = None
    elapsed_ms: Optional[float] = None

    def summary(self) -> dict[str, Any]:
        out: dict[str, Any] = {"status": self.status}
        for k in ("error", "as_of", "elapsed_ms"):
            if getattr(self, k) is not None:
                out[k] = getattr(self, k)
        return out


SOURCE_TYPES: dict[str, type] = {}


def register_source_type(name: str) -> Callable[[type], type]:
    def deco(cls: type) -> type:
        SOURCE_TYPES[name] = cls
        cls.type_name = name
        return cls
    return deco


class Source:
    """`fetch(ctx) -> SourceResult`. Raise on failure; the service turns exceptions into MISSING."""

    type_name = "base"

    def __init__(self, name: str, **params: Any) -> None:
        self.name = name
        self.params = params

    def fetch(self, ctx: SourceContext) -> SourceResult:  # pragma: no cover - interface
        raise NotImplementedError


# ------------------------------------------------------------------ Yahoo chart (quotes + daily bars)


def _yahoo_url(symbol: str) -> str:
    return f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(symbol, safe='')}?range=10d&interval=1d"


def _yahoo_bars(raw: bytes) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blob = json.loads(raw)
    res = ((blob.get("chart") or {}).get("result") or [None])[0]
    if not res:
        err = (blob.get("chart") or {}).get("error")
        raise ValueError(f"no chart result ({err})" if err else "no chart result")
    meta = res.get("meta") or {}
    q = (((res.get("indicators") or {}).get("quote")) or [{}])[0]
    tz = timezone(timedelta(seconds=int(meta.get("gmtoffset") or 0)))
    bars = []
    for i, ts in enumerate(res.get("timestamp") or []):
        row = {k: (q.get(k) or [None] * (i + 1))[i] for k in ("open", "high", "low", "close")}
        if row["close"] is None:
            continue
        bars.append({"date": datetime.fromtimestamp(int(ts), tz).date().isoformat(), "ts": int(ts),
                     **{k: round(float(v), 4) if v is not None else None for k, v in row.items()}})
    return meta, bars


@register_source_type("yahoo_quotes")
class YahooQuotes(Source):
    """Last price and % change vs the previous daily close, per configured symbol (`symbols: {KEY: ticker}`)."""

    def fetch(self, ctx: SourceContext) -> SourceResult:
        symbols: dict[str, str] = dict(self.params.get("symbols") or {})
        if not symbols:
            raise ValueError("no free endpoint configured (add a symbol in config/premarket.yaml to enable)")
        quotes, errors, stale, newest = {}, [], [], None
        for key, sym in symbols.items():
            try:
                meta, bars = _yahoo_bars(ctx.fetcher.get(fixture_key("yahoo", sym) + ".json", _yahoo_url(sym)))
                price = meta.get("regularMarketPrice")
                price = float(price) if price is not None else (bars[-1]["close"] if bars else None)
                if price is None or len(bars) < 2:
                    raise ValueError("fewer than two daily closes")
                last_ts = int(meta.get("regularMarketTime") or bars[-1]["ts"])
                prev = bars[-2]["close"]  # the last bar is the current (or latest) session
                as_of = datetime.fromtimestamp(last_ts, timezone.utc)
                quotes[key] = {"symbol": sym, "price": round(price, 4), "prev_close": prev,
                               "change_pct": round(100.0 * (price - prev) / prev, 3) if prev else None,
                               "as_of": as_of.isoformat(timespec="seconds")}
                if (ctx.now - as_of).total_seconds() > ctx.stale_after_h * 3600:
                    stale.append(key)
                newest = max(newest, as_of) if newest else as_of
            except Exception as exc:  # noqa: BLE001 - one bad symbol must not drop the others
                errors.append(f"{key}: {type(exc).__name__}: {exc}"[:160])
        if not quotes:
            raise RuntimeError("; ".join(errors) or "no quotes")
        status = "STALE" if len(stale) == len(quotes) else "OK"
        err = "; ".join(errors + [f"{k}: stale" for k in stale]) or None
        return SourceResult(self.name, status, {"quotes": quotes, "stale": stale}, err,
                            newest.isoformat(timespec="seconds") if newest else None)


@register_source_type("prev_day_levels")
class PrevDayLevels(Source):
    """Previous completed session OHLC + classic floor pivots per underlying (`symbols: {NIFTY: ^NSEI}`)."""

    def fetch(self, ctx: SourceContext) -> SourceResult:
        levels, errors = {}, []
        for und, sym in dict(self.params.get("symbols") or {}).items():
            try:
                _meta, bars = _yahoo_bars(ctx.fetcher.get(fixture_key("yahoo", sym) + ".json", _yahoo_url(sym)))
                done = [b for b in bars if b["date"] < ctx.session_date.isoformat() and None not in (b["high"], b["low"])]
                if not done:
                    raise ValueError("no completed session before today")
                b = done[-1]
                levels[und] = {"prev_day": {k: b[k] for k in ("date", "open", "high", "low", "close")},
                               **pivots(b["high"], b["low"], b["close"])}
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{und}: {type(exc).__name__}: {exc}"[:160])
        if not levels:
            raise RuntimeError("; ".join(errors) or "no symbols configured")
        stale = any(ctx.session_date - date.fromisoformat(v["prev_day"]["date"]) > timedelta(days=5) for v in levels.values())
        return SourceResult(self.name, "STALE" if stale else "OK", {"levels": levels}, "; ".join(errors) or None,
                            max(v["prev_day"]["date"] for v in levels.values()))


def pivots(high: float, low: float, close: float) -> dict[str, float]:
    p = (high + low + close) / 3.0
    return {k: round(v, 2) for k, v in {"pivot": p, "r1": 2 * p - low, "s1": 2 * p - high,
                                         "r2": p + (high - low), "s2": p - (high - low)}.items()}


# ------------------------------------------------------------------ RSS / Atom headlines


def parse_feed(raw: bytes, source: str) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(raw)
    items: list[dict[str, Any]] = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        fields = {c.tag.rsplit("}", 1)[-1]: c for c in el}
        title = (fields.get("title").text or "").strip() if fields.get("title") is not None else ""
        link_el = fields.get("link")
        link = (link_el.get("href") or link_el.text or "").strip() if link_el is not None else ""
        # Not `a or b`: an Element with no children is falsy.
        when_el = next((fields[k] for k in ("pubDate", "published", "updated") if fields.get(k) is not None), None)
        published = None
        if when_el is not None and when_el.text:
            try:
                dt = parsedate_to_datetime(when_el.text.strip())
            except (TypeError, ValueError):
                try:
                    dt = datetime.fromisoformat(when_el.text.strip().replace("Z", "+00:00"))
                except ValueError:
                    dt = None
            if dt is not None:
                published = (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat(timespec="seconds")
        if title:
            items.append({"title": re.sub(r"\s+", " ", title)[:240], "link": link[:500], "published": published,
                          "source": source})
    return items


@register_source_type("rss")
class RssHeadlines(Source):
    """Headlines from one or more RSS/Atom feeds (`urls: [...]`), newest first, within `max_age_h`."""

    def fetch(self, ctx: SourceContext) -> SourceResult:
        urls = list(self.params.get("urls") or [])
        max_age = timedelta(hours=float(self.params.get("max_age_h", 36)))
        limit = int(self.params.get("limit", 25))
        items, errors = [], []
        for i, url in enumerate(urls):
            try:
                items += parse_feed(ctx.fetcher.get(fixture_key("rss", f"{self.name}_{i}") + ".xml", url),
                                    source=re.sub(r"^https?://(www\.)?", "", url).split("/")[0])
            except Exception as exc:  # noqa: BLE001
                errors.append(f"feed {i}: {type(exc).__name__}: {exc}"[:160])
        if not items and errors:
            raise RuntimeError("; ".join(errors))
        fresh = [it for it in items if it["published"] is None
                 or ctx.now - datetime.fromisoformat(it["published"]) <= max_age]
        seen, out = set(), []
        for it in sorted(fresh, key=lambda x: x["published"] or "", reverse=True):
            k = it["title"].lower()
            if k not in seen:
                seen.add(k)
                out.append(it)
        newest = out[0]["published"] if out and out[0]["published"] else None
        status = "OK" if out else "STALE"
        return SourceResult(self.name, status, {"items": out[:limit]}, "; ".join(errors) or None, newest)


# ------------------------------------------------------------------ NSE FII/DII provisional cash flows


def _num(x: Any) -> Optional[float]:
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


@register_source_type("nse_fii_dii")
class NseFiiDii(Source):
    """FII/FPI and DII provisional cash-market net (₹ crore) from NSE's public JSON."""

    def fetch(self, ctx: SourceContext) -> SourceResult:
        url = str(self.params.get("url") or "https://www.nseindia.com/api/fiidiiTradeReact")
        try:  # NSE sets its cookies on the home page; the API refuses cookieless calls.
            ctx.fetcher.get(fixture_key("nse", "home") + ".html", "https://www.nseindia.com/")
        except Exception:  # noqa: BLE001 - the API call below decides
            pass
        rows = json.loads(ctx.fetcher.get(fixture_key("nse", self.name) + ".json", url,
                                          headers={"Accept": "application/json", "Referer": "https://www.nseindia.com/"}))
        flows: dict[str, Any] = {}
        for r in rows if isinstance(rows, list) else []:
            cat = str(r.get("category") or "").upper()
            key = "FII_NET_CR" if "FII" in cat or "FPI" in cat else "DII_NET_CR" if "DII" in cat else None
            if key:
                flows[key] = _num(r.get("netValue"))
                flows["date"] = r.get("date")
        if flows.get("FII_NET_CR") is None and flows.get("DII_NET_CR") is None:
            raise ValueError("no FII/DII rows")
        status = "OK"
        try:
            flow_day = datetime.strptime(str(flows.get("date")), "%d-%b-%Y").date()
            if ctx.session_date - flow_day > timedelta(days=5):
                status = "STALE"
        except ValueError:
            pass
        return SourceResult(self.name, status, {"flows": flows}, None, flows.get("date"))


# ------------------------------------------------------------------ local option-chain OI walls


@register_source_type("local_oi_walls")
class LocalOiWalls(Source):
    """Call/put OI walls from the recorder's last option-chain snapshot (`data/recon/option_chain/YYYYMMDD.jsonl`)."""

    def fetch(self, ctx: SourceContext) -> SourceResult:
        folder = ctx.root / str(self.params.get("folder") or "data/recon/option_chain")
        cutoff = ctx.session_date.strftime("%Y%m%d")
        files = sorted(p for p in folder.glob("*.jsonl") if p.stem.isdigit() and p.stem <= cutoff) if folder.is_dir() else []
        if not files:
            raise FileNotFoundError("no local option-chain snapshot (recorder not run)")
        path = files[-1]
        last: dict[tuple[str, str, float, str], dict[str, Any]] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                key = (str(r["underlying"]).upper(), str(r.get("expiry")), float(r["strike"]), str(r["option_type"]).upper())
            except (ValueError, KeyError, TypeError):
                continue
            if r.get("open_interest") is not None:
                last[key] = r
        walls: dict[str, Any] = {}
        for und in sorted({k[0] for k in last}):
            expiries = sorted({k[1] for k in last if k[0] == und})
            expiry = expiries[0]  # nearest expiry in the snapshot
            ce = {k[2]: float(v["open_interest"]) for k, v in last.items() if k[0] == und and k[1] == expiry and k[3] == "CE"}
            pe = {k[2]: float(v["open_interest"]) for k, v in last.items() if k[0] == und and k[1] == expiry and k[3] == "PE"}
            if not ce or not pe:
                continue
            cw, pw = max(ce, key=ce.get), max(pe, key=pe.get)
            walls[und] = {"expiry": expiry, "call_wall_strike": cw, "call_wall_oi": ce[cw], "put_wall_strike": pw,
                          "put_wall_oi": pe[pw], "pcr_oi": round(sum(pe.values()) / sum(ce.values()), 3) if sum(ce.values()) else None,
                          "snapshot_file": path.name}
        if not walls:
            raise ValueError(f"{path.name}: no CE+PE open interest")
        age = ctx.session_date - datetime.strptime(path.stem, "%Y%m%d").date()
        return SourceResult(self.name, "STALE" if age > timedelta(days=5) else "OK", {"oi_walls": walls}, None,
                            path.stem)
