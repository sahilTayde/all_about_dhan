"""Load attached live tapes. Dual-tape JSONL via desk_ml.tape fields; V2 via marketdata rows."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from exitlab.clock import IST, as_ist
from exitlab.types import Bar, Quote


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                yield row


def _parse_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return as_ist(raw)
    text = str(raw).strip()
    if not text:
        return None
    try:
        return as_ist(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def _f(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if val != val or val <= 0:
        return None
    return val


def dual_tape_days(root: Path) -> list[Path]:
    folder = root / "tape"
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.jsonl") if p.is_file())


def load_dual_tape_session(path: Path, *, underlying: str = "NIFTY") -> list[dict[str, Any]]:
    """One tick per JSONL row: NIFTY snap + as_of_ist. No fabrication."""
    und = underlying.upper()
    out: list[dict[str, Any]] = []
    for blob in iter_jsonl(path):
        as_of = _parse_ts(blob.get("as_of_ist"))
        snaps = blob.get("underlyings") or []
        nifty = next(
            (
                s
                for s in snaps
                if isinstance(s, dict) and str(s.get("underlying") or "").upper() == und
            ),
            None,
        )
        if nifty is None or as_of is None:
            continue
        idx1 = nifty.get("index_1m") if isinstance(nifty.get("index_1m"), dict) else {}
        out.append(
            {
                "available_ts": as_of,
                "snap_ts": _parse_ts(nifty.get("as_of_ist")) or as_of,
                "index": _f(nifty.get("index_ltp")),
                "index_1m": idx1,
                "atm_strike": _f(nifty.get("atm_strike")),
                "atm_ce": _f(nifty.get("atm_ce_ltp")),
                "atm_pe": _f(nifty.get("atm_pe_ltp")),
                "itm_ce": _f(nifty.get("itm_ce_ltp")),
                "itm_pe": _f(nifty.get("itm_pe_ltp")),
                "itm_ce_strike": _f(nifty.get("itm_ce_strike")),
                "itm_pe_strike": _f(nifty.get("itm_pe_strike")),
                "atm_ce_iv": _f(nifty.get("atm_ce_iv")),
                "atm_pe_iv": _f(nifty.get("atm_pe_iv")),
                "itm_ce_iv": _f(nifty.get("itm_ce_iv")),
                "itm_pe_iv": _f(nifty.get("itm_pe_iv")),
                "pcr_oi": _f(nifty.get("pcr_oi")),
                "index_volume": _f(nifty.get("index_volume")),
                "expiry": nifty.get("expiry"),
                "wing_quotes": nifty.get("wing_quotes")
                if isinstance(nifty.get("wing_quotes"), dict)
                else {},
                "stale": bool(nifty.get("stale")),
                "session": path.stem,
                "source": "legacy_dual_tape",
            }
        )
    return out


def strike_ltp(tick: dict[str, Any], *, side: str, strike: float) -> float | None:
    """LTP of this exact strike only. Never the rolling ATM/ITM contract."""
    hit = wing_ltp(tick, side=side, strike=strike)
    if hit is not None:
        return hit
    side_u = side.upper()
    if side_u == "CE":
        if _same_strike(tick.get("atm_strike"), strike):
            return _f(tick.get("atm_ce"))
        if _same_strike(tick.get("itm_ce_strike"), strike):
            return _f(tick.get("itm_ce"))
    else:
        if _same_strike(tick.get("atm_strike"), strike):
            return _f(tick.get("atm_pe"))
        if _same_strike(tick.get("itm_pe_strike"), strike):
            return _f(tick.get("itm_pe"))
    return None


def _same_strike(raw: Any, strike: float) -> bool:
    try:
        return raw is not None and abs(float(raw) - float(strike)) < 1e-6
    except (TypeError, ValueError):
        return False


def measure_v2_spreads(data: Path) -> dict[str, Any]:
    """Bid/ask spread by moneyness and TOD from V2 quote_snapshots. No fabrication."""
    root = data / "tape" / "v2"
    if not root.is_dir():
        return {"ok": False, "n": 0, "note": "no tape/v2"}
    by_rule: dict[str, list[float]] = {}
    by_cell: dict[str, list[float]] = {}
    n = 0
    days: list[str] = []
    for path in sorted(root.glob("*/quote_snapshots.jsonl")):
        days.append(path.parent.name)
        for row in iter_jsonl(path):
            raw_payload = row.get("payload")
            payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
            bid, ask = _f(payload.get("bid")), _f(payload.get("ask"))
            if bid is None or ask is None or ask <= bid:
                continue
            spread = ask - bid
            rule = str(payload.get("rule") or "UNKNOWN")
            avail = _parse_ts(row.get("available_ts") or row.get("event_ts"))
            if avail is None:
                continue
            tod = f"{avail.hour:02d}:{0 if avail.minute < 30 else 30:02d}"
            by_rule.setdefault(rule, []).append(spread)
            by_cell.setdefault(f"{rule}|{tod}", []).append(spread)
            n += 1

    def _pct(xs: list[float], p: float) -> float | None:
        if not xs:
            return None
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(p * (len(xs) - 1)))]

    table: dict[str, float] = {}
    rule_rows = []
    for rule, xs in sorted(by_rule.items()):
        p50 = _pct(xs, 0.50)
        if p50 is not None:
            table[rule] = float(p50)
        rule_rows.append(
            {
                "rule": rule,
                "n": len(xs),
                "p50": p50,
                "p80": _pct(xs, 0.80),
                "mean": (sum(xs) / len(xs)) if xs else None,
            }
        )
    cell_rows = []
    for key, xs in sorted(by_cell.items()):
        rule, tod = key.split("|", 1)
        cell_rows.append(
            {"rule": rule, "tod": tod, "n": len(xs), "p50": _pct(xs, 0.50), "p80": _pct(xs, 0.80)}
        )
    return {
        "ok": n > 0,
        "n": n,
        "days": days,
        "by_rule": rule_rows,
        "by_rule_tod": cell_rows,
        "spread_pts_p50": table,
        "note": (
            "V2 quote_snapshots bid/ask. Dual-tape JSONL has no book. "
            "Use spread_pts_p50 as the no-book half-spread source (full spread, split in half)."
        ),
    }


def spread_pts_for(moneyness: str, table: dict[str, float] | None = None) -> float:
    tab = table or {}
    key = moneyness.upper()
    if key in tab:
        return float(tab[key])
    if key.startswith("ITM200"):
        return float(tab.get("ITM200") or 0.55)
    if key.startswith("ITM"):
        return float(tab.get("ITM100") or tab.get("ITM") or 0.35)
    return float(tab.get("ATM") or 0.20)


def premium_quote(tick: dict[str, Any], *, side: str, moneyness: str) -> Quote:
    side_u = side.upper()
    if moneyness.upper() == "ITM200" or moneyness.upper() == "ITM":
        ltp = tick["itm_ce"] if side_u == "CE" else tick["itm_pe"]
        strike = tick["itm_ce_strike"] if side_u == "CE" else tick["itm_pe_strike"]
        iv = tick["itm_ce_iv"] if side_u == "CE" else tick["itm_pe_iv"]
    else:
        ltp = tick["atm_ce"] if side_u == "CE" else tick["atm_pe"]
        strike = tick["atm_strike"]
        iv = tick["atm_ce_iv"] if side_u == "CE" else tick["atm_pe_iv"]
    return Quote(
        available_ts=tick["available_ts"],
        bid=None,
        ask=None,
        ltp=ltp,
        index=tick.get("index"),
        iv=iv,
        strike=strike,
        side=side_u,
        stale=bool(tick.get("stale")),
        source="legacy_dual_tape",
    )


def wing_ltp(tick: dict[str, Any], *, side: str, strike: float) -> float | None:
    wings = tick.get("wing_quotes") or {}
    key = str(int(strike)) if float(strike).is_integer() else str(strike)
    cell = wings.get(key) or wings.get(str(round(strike)))
    if not isinstance(cell, dict):
        return None
    return _f(cell.get(side.lower()))


def ticks_to_index_bars(ticks: list[dict[str, Any]]) -> list[Bar]:
    """Last index_1m per minute, known at the tick that first carries that closed bar."""
    order: list[int] = []
    seen: dict[int, Bar] = {}
    for tick in ticks:
        raw = tick.get("index_1m") or {}
        ts_unix = raw.get("ts")
        close = _f(raw.get("close"))
        if ts_unix is None or close is None:
            continue
        key = int(ts_unix)
        if key in seen:
            continue
        avail = tick["available_ts"]
        bar_ts = datetime.fromtimestamp(key, tz=IST)
        # 1m bar known only after close; first tape row that carries it.
        bar = Bar(
            ts=bar_ts,
            available_ts=avail,
            open=float(raw.get("open") or close),
            high=float(raw.get("high") or close),
            low=float(raw.get("low") or close),
            close=close,
            volume=_f(raw.get("volume")),
            index_open=float(raw.get("open") or close),
            index_high=float(raw.get("high") or close),
            index_low=float(raw.get("low") or close),
            index_close=close,
        )
        seen[key] = bar
        order.append(key)
    return [seen[k] for k in order]


def load_v2_quotes(day_dir: Path) -> list[Quote]:
    path = day_dir / "quote_snapshots.jsonl"
    if not path.is_file():
        return []
    out: list[Quote] = []
    for row in iter_jsonl(path):
        raw_payload = row.get("payload")
        payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
        avail = _parse_ts(row.get("available_ts") or row.get("event_ts") or row.get("timestamp"))
        if avail is None:
            continue
        inst = str(payload.get("instrument_id") or "")
        parts = inst.split(":")
        strike = _f(parts[3]) if len(parts) >= 5 else None
        side = parts[4] if len(parts) >= 5 else payload.get("side")
        bid, ask = _f(payload.get("bid")), _f(payload.get("ask"))
        spread = None
        if bid is not None and ask is not None:
            spread = ask - bid
        out.append(
            Quote(
                available_ts=avail,
                bid=bid,
                ask=ask,
                ltp=_f(payload.get("ltp")),
                strike=strike,
                side=str(side).upper() if side else None,
                spread=spread,
                oi=_f(payload.get("oi")),
                stale=bool(payload.get("stale")),
                source="v2_quote_snapshot",
            )
        )
    return out


def load_v2_index(day_dir: Path) -> list[Quote]:
    path = day_dir / "depth_quotes.jsonl"
    if not path.is_file():
        return []
    out: list[Quote] = []
    for row in iter_jsonl(path):
        raw_payload = row.get("payload")
        payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
        inst = str(payload.get("instrument_id") or "")
        if inst.count(":") > 2:
            continue  # option depth; index id is NSE_FNO:NIFTY:expiry
        avail = _parse_ts(
            payload.get("exchange_ts") or row.get("available_ts") or row.get("event_ts")
        )
        if avail is None:
            continue
        ltp = _f(payload.get("ltp"))
        out.append(
            Quote(
                available_ts=avail,
                bid=_f(payload.get("bid")),
                ask=_f(payload.get("ask")),
                ltp=ltp,
                index=ltp,
                source="v2_depth",
            )
        )
    return out
