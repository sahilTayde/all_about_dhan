"""Resolve the recorder's instruments from the scrip master CSV and the option-chain API.

- Scrip master CSV: index security id, nearest index future, and every listed option
  contract of the underlying (compact or detailed column names).
- ``/optionchain/expirylist``: nearest expiry on or after the session day.
- ``/optionchain``: spot (``data.last_price``) and per-strike ``security_id`` for that
  expiry (``data.oc["<strike>"].ce/pe``), the same fields ``desk_intel`` reads live.

``InstrumentSource`` is the only thing that talks to Dhan, so tests stub it. The Dhan
source uses REST data endpoints only; it never touches order endpoints.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol, TypeVar

from dhan_client.config import Settings
from dhan_client.errors import DhanApiError
from dhan_client.futidx import parse_futidx_csv
from dhan_client.instruments import InstrumentClient
from dhan_client.option_chain import OptionChainClient
from dhan_client.rest import RestClient
from dhan_client.types import FeedInstrument

log = logging.getLogger(__name__)

T = TypeVar("T")


# underlying -> (exchange id in the CSV, derivatives feed segment)
UNDERLYINGS: dict[str, tuple[str, str]] = {
    "NIFTY": ("NSE", "NSE_FNO"),
    "BANKNIFTY": ("NSE", "NSE_FNO"),
    "SENSEX": ("BSE", "BSE_FNO"),
}
_INDEX_ALIASES: dict[str, frozenset[str]] = {
    "NIFTY": frozenset({"NIFTY", "NIFTY 50", "NIFTY50"}),
    "BANKNIFTY": frozenset({"BANKNIFTY", "NIFTY BANK", "NIFTYBANK", "BANK NIFTY"}),
    "SENSEX": frozenset({"SENSEX"}),
}
_ID_COLUMNS = ("SEM_SMST_SECURITY_ID", "SECURITY_ID", "SEM_SECURITY_ID", "SMST_SECURITY_ID")
# Dhan error codes for bad credentials / no data subscription / account blocked.
_AUTH_CODES = frozenset({"DH-901", "DH-902", "DH-903"})


class StartupError(Exception):
    """Startup cannot continue. The message is safe to print (no secrets).

    ``retryable`` is true for network / 5xx / rate-limit failures, false for bad
    credentials or unusable data."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    security_id: str
    exchange_segment: str
    kind: str  # INDEX | FUTURE | OPTION
    expiry: str | None = None
    strike: int | None = None
    option_type: str | None = None

    @property
    def feed(self) -> FeedInstrument:
        return FeedInstrument(exchange_segment=self.exchange_segment, security_id=self.security_id)


@dataclass(frozen=True)
class Universe:
    underlying: str
    expiry: str
    spot: float
    strike_step: int
    index: Instrument
    future: Instrument | None
    options: dict[tuple[int, str], Instrument] = field(repr=False)

    def all_instruments(self) -> list[Instrument]:
        fixed = [self.index] + ([self.future] if self.future else [])
        return fixed + list(self.options.values())


class InstrumentSource(Protocol):
    def scrip_master_csv(self) -> str: ...

    def expiry_list(self, underlying_scrip: int, underlying_seg: str) -> list[str]: ...

    def option_chain(self, underlying_scrip: int, underlying_seg: str, expiry: str) -> dict[str, Any]: ...


class DhanInstrumentSource:
    """Live source. Caches the (public) scrip master CSV once per day under ``cache_dir``."""

    def __init__(self, settings: Settings, cache_dir: Path, *, day: date) -> None:
        self._rest = RestClient(settings, timeout=60.0)
        self._instruments = InstrumentClient(self._rest)
        self._chain = OptionChainClient(self._rest)
        self._cache = cache_dir / f"scrip_master_{day.isoformat()}.csv"

    def close(self) -> None:
        self._rest.close()

    def scrip_master_csv(self) -> str:
        if self._cache.is_file() and self._cache.stat().st_size > 0:
            log.info("scrip master from cache %s", self._cache)
            return self._cache.read_text(encoding="utf-8")
        text = self._instruments.fetch_scrip_master_text()
        self._cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._cache.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(self._cache)
        return text

    def expiry_list(self, underlying_scrip: int, underlying_seg: str) -> list[str]:
        body = {"UnderlyingScrip": underlying_scrip, "UnderlyingSeg": underlying_seg}
        data = self._chain.expiry_list(body).get("data")  # type: ignore[arg-type]
        return [str(x) for x in data if x] if isinstance(data, list) else []

    def option_chain(self, underlying_scrip: int, underlying_seg: str, expiry: str) -> dict[str, Any]:
        body = {"UnderlyingScrip": underlying_scrip, "UnderlyingSeg": underlying_seg, "Expiry": expiry}
        data = self._chain.chain(body).get("data")  # type: ignore[arg-type]
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            data = data["data"]
        return data if isinstance(data, dict) else {}


def _pick(row: dict[str, str], *names: str) -> str:
    lower = {k.strip().lower(): v for k, v in row.items() if k}
    for name in names:
        value = lower.get(name.lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _expiry(raw: str) -> str | None:
    text = raw.strip()
    if len(text) >= 10 and text[4] == "-":
        try:
            return date.fromisoformat(text[:10]).isoformat()
        except ValueError:
            return None
    for fmt in ("%d-%b-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text.split(" ")[0], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _strike(raw: Any) -> int | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return int(round(value)) if value > 0 and abs(value - round(value)) < 1e-6 else None


def _token(text: str) -> str:
    return text.upper().replace("-", " ").split(" ")[0] if text else ""


@dataclass
class ScripMaster:
    index_ids: list[str]
    underlying_ids: Counter[str]
    # expiry -> (strike, CE/PE) -> security id
    options: dict[str, dict[tuple[int, str], str]]


def parse_scrip_master(text: str, underlying: str) -> ScripMaster:
    exchange, _ = UNDERLYINGS[underlying]
    reader = csv.DictReader(io.StringIO(text))
    index_ids: list[str] = []
    underlying_ids: Counter[str] = Counter()
    options: dict[str, dict[tuple[int, str], str]] = {}
    for row in reader:
        sid = _pick(row, *_ID_COLUMNS)
        if not sid or _pick(row, "SEM_EXM_EXCH_ID", "EXCH_ID").upper() != exchange:
            continue
        inst = _pick(row, "SEM_INSTRUMENT_NAME", "INSTRUMENT").upper()
        if inst == "INDEX":
            names = {
                _pick(row, name).upper()
                for name in ("SEM_TRADING_SYMBOL", "SYMBOL_NAME", "UNDERLYING_SYMBOL", "SEM_CUSTOM_SYMBOL")
            }
            if names & _INDEX_ALIASES[underlying]:
                index_ids.append(sid)
        elif inst == "OPTIDX":
            und = _pick(row, "UNDERLYING_SYMBOL").upper() or _token(_pick(row, "SEM_TRADING_SYMBOL", "SYMBOL_NAME"))
            side = _pick(row, "SEM_OPTION_TYPE", "OPTION_TYPE").upper()
            strike = _strike(_pick(row, "SEM_STRIKE_PRICE", "STRIKE_PRICE"))
            expiry = _expiry(_pick(row, "SEM_EXPIRY_DATE", "SM_EXPIRY_DATE", "EXPIRY_DATE"))
            if und != underlying or side not in ("CE", "PE") or strike is None or expiry is None:
                continue
            options.setdefault(expiry, {})[(strike, side)] = sid
            uid = _pick(row, "UNDERLYING_SECURITY_ID")
            if uid:
                underlying_ids[uid] += 1
    return ScripMaster(index_ids, underlying_ids, options)


def chain_security_ids(chain: dict[str, Any]) -> dict[tuple[int, str], str]:
    out: dict[tuple[int, str], str] = {}
    oc = chain.get("oc")
    if not isinstance(oc, dict):
        return out
    for key, cell in oc.items():
        strike = _strike(key)
        if strike is None or not isinstance(cell, dict):
            continue
        for side in ("CE", "PE"):
            leg = cell.get(side.lower()) or cell.get(side)
            sid = leg.get("security_id") if isinstance(leg, dict) else None
            if sid not in (None, "", 0, "0"):
                out[(strike, side)] = str(int(float(sid)))
    return out


def strike_step(strikes: list[int], spot: float) -> int:
    """Most common gap between listed strikes within 3% of spot (50 for NIFTY, 100 for SENSEX)."""
    near = sorted({s for s in strikes if abs(s - spot) <= spot * 0.03})
    gaps = Counter(b - a for a, b in zip(near, near[1:], strict=False) if b > a)
    if not gaps:
        raise StartupError(f"cannot infer the strike step: no listed strikes near spot {spot}")
    return gaps.most_common(1)[0][0]


def _index_id(sm: ScripMaster, underlying: str) -> str:
    ids = list(dict.fromkeys(sm.index_ids))
    if len(ids) == 1:
        return ids[0]
    top = sm.underlying_ids.most_common(1)[0][0] if sm.underlying_ids else None
    if top and (not ids or top in ids):
        return top
    if ids:
        log.warning("several %s INDEX rows %s; using %s", underlying, ids, ids[0])
        return ids[0]
    raise StartupError(
        f"{underlying} INDEX row not found in the scrip master CSV; cannot resolve the index security id"
    )


def build_universe(
    csv_text: str,
    sm: ScripMaster,
    chain: dict[str, Any],
    underlying: str,
    day: date,
    expiry: str,
) -> Universe:
    exchange, fno_segment = UNDERLYINGS[underlying]
    index_sid = _index_id(sm, underlying)

    try:
        spot = float(chain.get("last_price") or 0.0)
    except (TypeError, ValueError):
        spot = 0.0
    if spot <= 0:
        raise StartupError(f"option chain for {underlying} {expiry} has no last_price (spot)")

    ids = dict(sm.options.get(expiry, {}))
    from_chain = chain_security_ids(chain)
    mismatched = sum(1 for k, v in from_chain.items() if k in ids and ids[k] != v)
    if mismatched:
        log.warning("%d option security ids differ between CSV and option chain; using the chain", mismatched)
    ids.update(from_chain)
    if not ids:
        raise StartupError(f"no {underlying} option contracts found for expiry {expiry} (CSV or option chain)")
    step = strike_step([k[0] for k in ids], spot)

    def option(strike: int, side: str, sid: str) -> Instrument:
        return Instrument(
            instrument_id=f"{exchange}_FNO:{underlying}:{expiry}:{strike}:{side}",
            security_id=sid,
            exchange_segment=fno_segment,
            kind="OPTION",
            expiry=expiry,
            strike=strike,
            option_type=side,
        )

    fut = parse_futidx_csv(csv_text, as_of=day).get(underlying)
    future = (
        Instrument(
            instrument_id=f"{exchange}_FNO:{underlying}:{fut.expiry}",
            security_id=fut.security_id,
            exchange_segment=fut.exchange_segment,
            kind="FUTURE",
            expiry=fut.expiry,
        )
        if fut
        else None
    )
    if future is None:
        log.warning("no %s index future found in the scrip master; recording without it", underlying)
    return Universe(
        underlying=underlying,
        expiry=expiry,
        spot=spot,
        strike_step=step,
        index=Instrument(f"{exchange}_IDX:{underlying}", index_sid, "IDX_I", "INDEX"),
        future=future,
        options={k: option(k[0], k[1], v) for k, v in sorted(ids.items())},
    )


def _describe(exc: DhanApiError) -> str:
    parts = [f"HTTP {exc.status_code}" if exc.status_code else "no HTTP response"]
    if exc.error_code:
        parts.append(exc.error_code)
    parts.append(str(exc))
    return ", ".join(parts)


def _call(what: str, fn: Callable[[], T], attempts: int, sleep: Callable[[float], None]) -> T:
    delay = 2.0
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except DhanApiError as exc:
            if exc.status_code in (401, 403) or exc.error_code in _AUTH_CODES:
                raise StartupError(
                    f"Dhan rejected the credentials while fetching {what} ({_describe(exc)}). "
                    "Check DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in the environment or .env; "
                    "access tokens expire every 24 hours."
                ) from exc
            retryable = exc.status_code is None or exc.status_code == 429 or exc.status_code >= 500
            if not retryable:
                raise StartupError(f"Dhan returned an error for {what}: {_describe(exc)}") from exc
            if attempt == attempts:
                raise StartupError(
                    f"could not reach Dhan for {what} after {attempts} attempts ({_describe(exc)}); "
                    "check the network connection",
                    retryable=True,
                ) from exc
            log.warning("%s failed (%s); retry %d/%d in %.0fs", what, _describe(exc), attempt, attempts, delay)
            sleep(delay)
            delay = min(delay * 2, 30.0)
    raise AssertionError("unreachable")


def load_universe(
    source: InstrumentSource,
    underlying: str,
    day: date,
    *,
    attempts: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> Universe:
    """Fetch and resolve everything the recorder needs. Raises StartupError with a clear message."""
    csv_text = _call("the scrip master CSV", source.scrip_master_csv, attempts, sleep)
    if "," not in csv_text.partition("\n")[0]:
        raise StartupError("the scrip master download is not a CSV (empty or unexpected content)")
    sm = parse_scrip_master(csv_text, underlying)
    index_sid = _index_id(sm, underlying)
    seg = "IDX_I"
    expiries = _call("the option expiry list", lambda: source.expiry_list(int(index_sid), seg), attempts, sleep)
    upcoming = sorted(e for e in (_expiry(x) for x in expiries) if e and e >= day.isoformat())
    if upcoming:
        expiry = upcoming[0]
    else:
        listed = sorted(e for e in sm.options if e >= day.isoformat())
        if not listed:
            raise StartupError(f"no upcoming {underlying} expiry from the expiry list API or the CSV")
        expiry = listed[0]
        log.warning("expiry list API returned nothing usable; nearest CSV expiry %s", expiry)
    chain = _call(
        f"the option chain ({expiry})", lambda: source.option_chain(int(index_sid), seg, expiry), attempts, sleep
    )
    universe = build_universe(csv_text, sm, chain, underlying, day, expiry)
    log.info(
        "universe %s expiry=%s spot=%.2f step=%d index=%s future=%s options=%d",
        underlying,
        universe.expiry,
        universe.spot,
        universe.strike_step,
        universe.index.security_id,
        universe.future.instrument_id if universe.future else None,
        len(universe.options),
    )
    return universe


def save_universe(universe: Universe, cache_dir: Path, day: date) -> Path:
    """Remember the resolved instruments so a restart can survive a Dhan/network outage."""
    path = cache_dir / f"universe_{universe.underlying}_{day.isoformat()}.json"
    data = {
        "underlying": universe.underlying,
        "expiry": universe.expiry,
        "spot": universe.spot,
        "strike_step": universe.strike_step,
        "index": asdict(universe.index),
        "future": asdict(universe.future) if universe.future else None,
        "options": [asdict(i) for i in universe.options.values()],
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(path)
    return path


def load_cached_universe(cache_dir: Path, underlying: str, day: date) -> tuple[Universe, Path] | None:
    """Newest cached universe whose option expiry has not passed on ``day``."""
    for path in sorted(cache_dir.glob(f"universe_{underlying}_*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data["expiry"] < day.isoformat():
                continue
            options = [Instrument(**o) for o in data["options"]]
            universe = Universe(
                underlying=data["underlying"],
                expiry=data["expiry"],
                spot=float(data["spot"]),
                strike_step=int(data["strike_step"]),
                index=Instrument(**data["index"]),
                future=Instrument(**data["future"]) if data["future"] else None,
                options={(o.strike or 0, o.option_type or ""): o for o in options},
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            log.warning("ignoring unreadable instrument cache %s: %s", path, exc)
            continue
        return universe, path
    return None
