"""Research overlay: current-month index futures + top NIFTY cash names.

Resolved from the Dhan scrip master at startup. Security ids are never hardcoded.
Rows go to stream ``md:research`` so DEPTH_QUOTE / QUOTE_SNAPSHOT readers stay unchanged.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import date

from dhan_client.futidx import FutIdxContract, parse_all_futidx_csv

from marketdata.instruments import UNDERLYINGS, Instrument, StartupError
from marketdata.strikes import DHAN_FEED_LIMITS, OPTION_WINGS, STEADY_INSTRUMENTS

log = logging.getLogger(__name__)

RESEARCH_STREAM = "md:research"
RESEARCH_EVENT = "RESEARCH_QUOTE"
RESEARCH_TAPE = "research_quotes"

# Named cash names (not Dhan ids). Ids come from the scrip master.
NIFTY_HEAVYWEIGHTS: tuple[str, ...] = (
    "HDFCBANK",
    "RELIANCE",
    "ICICIBANK",
    "INFY",
    "BHARTIARTL",
    "TCS",
    "LT",
    "ITC",
    "AXISBANK",
    "KOTAKBANK",
)
RESEARCH_FUTURE_UNDERLYINGS: tuple[str, ...] = ("NIFTY", "SENSEX")

_EQUITY_INST = frozenset({"EQUITY", "EQ", "ES"})
_EQ_SERIES = frozenset({"", "EQ"})
_EQ_EXCH = frozenset({"NSE", "NSE_EQ"})
_EQ_SEG = frozenset({"", "E", "EQ", "NSE_EQ"})
_NAME_COLUMNS = (
    "SEM_TRADING_SYMBOL",
    "SYMBOL_NAME",
    "SEM_CUSTOM_SYMBOL",
    "SM_SYMBOL_NAME",
    "DISPLAY_NAME",
    "UNDERLYING_SYMBOL",
)
_ID_COLUMNS = ("SEM_SMST_SECURITY_ID", "SECURITY_ID", "SEM_SECURITY_ID", "SMST_SECURITY_ID")


def _pick(row: dict[str, str], *names: str) -> str:
    lower = {k.strip().lower(): v for k, v in row.items() if k}
    for name in names:
        value = lower.get(name.lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def options_per_book() -> int:
    return OPTION_WINGS


def steady_book_count() -> int:
    """Index + nearest future + listed option wings (ATM/ITM/OTM)."""
    return STEADY_INSTRUMENTS


def research_named_count() -> int:
    return len(RESEARCH_FUTURE_UNDERLYINGS) + len(NIFTY_HEAVYWEIGHTS)


def default_unique_subscribe_count(*, extra_futures: int = 0, books: int = 2) -> int:
    """Unique feed ids for the default NIFTY+SENSEX CLI plus the research overlay.

    Current-month futures that already sit on a strike book do not add a subscribe
    slot (``extra_futures=0``). After a monthly expiry the fallback front-month
    contract is the same nearest future the book already has.
    """
    return books * steady_book_count() + len(NIFTY_HEAVYWEIGHTS) + extra_futures


def after_recentre_count(*, extra_futures: int = 0, books: int = 2) -> int:
    """Steady unique ids plus retained wings (10 min) on every book."""
    return default_unique_subscribe_count(extra_futures=extra_futures, books=books) + books * options_per_book()


def within_dhan_caps(n: int) -> bool:
    """One socket, one subscribe JSON. Caps are SOURCE_FACT from StrikeSet.DHAN_FEED_LIMITS."""
    return 0 < n <= DHAN_FEED_LIMITS["ids_per_subscribe"] and n <= DHAN_FEED_LIMITS["instruments_per_socket"]


def dhan_feed_caps() -> dict[str, int]:
    return {
        "sockets_per_user": DHAN_FEED_LIMITS["sockets"],
        "ids_per_socket": DHAN_FEED_LIMITS["instruments_per_socket"],
        "ids_per_subscribe_json": DHAN_FEED_LIMITS["ids_per_subscribe"],
    }


def _symbol_token(raw: str) -> str:
    text = raw.strip().upper().replace("_", "")
    if not text:
        return ""
    token = text.replace("-", " ").split()[0]
    return token.split(".")[0]


def parse_equity_ids(text: str, symbols: tuple[str, ...] = NIFTY_HEAVYWEIGHTS) -> dict[str, str]:
    """Cash-segment (NSE EQ) security ids for ``symbols``. Raises if any name is missing."""
    wanted: dict[str, str | None] = {s.upper(): None for s in symbols}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        sid = _pick(row, *_ID_COLUMNS)
        if not sid:
            continue
        exch = _pick(row, "SEM_EXM_EXCH_ID", "EXCH_ID").upper()
        if exch not in _EQ_EXCH:
            continue
        seg = _pick(row, "SEM_SEGMENT", "SEGMENT").upper().replace(" ", "_")
        if seg not in _EQ_SEG:
            continue
        inst = _pick(row, "SEM_INSTRUMENT_NAME", "INSTRUMENT").upper()
        if inst not in _EQUITY_INST:
            continue
        series = _pick(row, "SEM_SERIES", "SERIES").upper()
        if series not in _EQ_SERIES:
            continue
        names = {_symbol_token(_pick(row, col)) for col in _NAME_COLUMNS}
        for name in names:
            if name in wanted and wanted[name] is None:
                wanted[name] = sid
    missing = [s for s, sid in wanted.items() if sid is None]
    if missing:
        raise StartupError(
            f"scrip master has no NSE_EQ cash row for {', '.join(missing)}; "
            "cannot resolve research stock security ids"
        )
    return {s: sid for s, sid in wanted.items() if sid is not None}


def current_month_futidx(text: str, as_of: date, underlying: str) -> FutIdxContract | None:
    """Unexpired FUTIDX in ``as_of``'s calendar month, else the nearest unexpired (front month)."""
    listed = parse_all_futidx_csv(text).get(underlying, [])
    day = as_of.isoformat()
    month = day[:7]
    same_month = [c for c in listed if c.expiry >= day and c.expiry[:7] == month]
    if same_month:
        return min(same_month, key=lambda c: c.expiry)
    unexpired = [c for c in listed if c.expiry >= day]
    return min(unexpired, key=lambda c: c.expiry) if unexpired else None


def _future_instrument(contract: FutIdxContract) -> Instrument:
    exchange, _ = UNDERLYINGS[contract.underlying]
    return Instrument(
        instrument_id=f"{exchange}_FNO:{contract.underlying}:{contract.expiry}",
        security_id=contract.security_id,
        exchange_segment=contract.exchange_segment,
        kind="FUTURE",
        expiry=contract.expiry,
    )


def _equity_instrument(symbol: str, security_id: str) -> Instrument:
    return Instrument(
        instrument_id=f"NSE_EQ:{symbol}",
        security_id=security_id,
        exchange_segment="NSE_EQ",
        kind="EQUITY",
    )


@dataclass(frozen=True)
class ResearchSet:
    futures: tuple[Instrument, ...]
    stocks: tuple[Instrument, ...]

    def all_instruments(self) -> list[Instrument]:
        return list(self.futures) + list(self.stocks)

    def __len__(self) -> int:
        return len(self.futures) + len(self.stocks)


def load_research_set(csv_text: str, day: date) -> ResearchSet:
    """Resolve current-month NIFTY/SENSEX futures and the 10 cash names from one CSV."""
    if "," not in csv_text.partition("\n")[0]:
        raise StartupError("the scrip master download is not a CSV (empty or unexpected content)")
    futures: list[Instrument] = []
    for name in RESEARCH_FUTURE_UNDERLYINGS:
        contract = current_month_futidx(csv_text, day, name)
        if contract is None:
            log.warning("no unexpired %s FUTIDX in the scrip master; research overlay skips it", name)
            continue
        if contract.expiry[:7] != day.isoformat()[:7]:
            log.info(
                "%s current-month FUTIDX already expired; using front-month %s id=%s",
                name,
                contract.expiry,
                contract.security_id,
            )
        futures.append(_future_instrument(contract))
    ids = parse_equity_ids(csv_text, NIFTY_HEAVYWEIGHTS)
    stocks = tuple(_equity_instrument(sym, ids[sym]) for sym in NIFTY_HEAVYWEIGHTS)
    out = ResearchSet(futures=tuple(futures), stocks=stocks)
    log.info(
        "research overlay futures=%s stocks=%d ids=%s",
        [i.instrument_id for i in out.futures],
        len(out.stocks),
        [i.security_id for i in out.stocks],
    )
    return out
