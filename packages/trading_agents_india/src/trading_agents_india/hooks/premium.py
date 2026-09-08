"""OPTIDX premium chart lean if client can fetch; else INDEX proxy (HYPOTHESIS)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import timedelta
from typing import Any, Literal, Optional

from trading_agents_india.session_clock import now_ist

PremiumLean = Literal["BUY_CE", "BUY_PE", "HOLD"]
PremiumSource = Literal["optidx_rolling", "optionchain_atm", "index_proxy", "unavailable"]

_INDEX_HINTS = {
    "NIFTY": ("13", "IDX_I", "INDEX"),
    "BANKNIFTY": ("25", "IDX_I", "INDEX"),
    "SENSEX": ("51", "IDX_I", "INDEX"),
}


@dataclass
class PremiumLeanResult:
    underlying: str
    lean: PremiumLean
    source: PremiumSource
    layer: str
    summary: str
    data_gaps: list[str] = field(default_factory=list)
    bar_count: int = 0
    option_ltp: Optional[float] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    atm_strike: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _lean_from_closes(closes: list[float]) -> PremiumLean:
    if len(closes) < 3:
        return "HOLD"
    first = closes[0]
    last = closes[-1]
    if first <= 0:
        return "HOLD"
    chg = (last - first) / first
    if chg > 0.0015:
        return "BUY_CE"
    if chg < -0.0015:
        return "BUY_PE"
    return "HOLD"


def _extract_closes(payload: dict[str, Any]) -> list[float]:
    closes: list[float] = []
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(data, dict):
        return closes
    raw = data.get("close") or data.get("c") or data.get("Close")
    if isinstance(raw, list):
        for x in raw:
            try:
                closes.append(float(x))
            except (TypeError, ValueError):
                continue
    return closes


def try_optidx_premium_lean(underlying: str) -> Optional[PremiumLeanResult]:
    """Try POST /charts/rollingoption. Fail soft → None."""
    und = underlying.upper()
    hint = _INDEX_HINTS.get(und)
    if hint is None:
        return None
    sid, _seg, _inst = hint
    try:
        from dhan_client import DhanClient  # type: ignore
    except Exception:
        return None
    try:
        client = DhanClient(dry_run=False)
        if getattr(client.settings, "dry_run", True):
            client.close()
            return None
        end = now_ist()
        start = end - timedelta(days=2)
        body = {
            "exchangeSegment": "NSE_FNO" if und != "SENSEX" else "BSE_FNO",
            "interval": "5",
            "securityId": sid,
            "instrument": "OPTIDX",
            "expiryFlag": "WEEK",
            "expiryCode": 1,
            "strike": "ATM",
            "drvOptionType": "CALL",
            "requiredData": ["open", "high", "low", "close", "volume"],
            "fromDate": start.strftime("%Y-%m-%d"),
            "toDate": end.strftime("%Y-%m-%d"),
        }
        raw = client.historical.rolling_option(body)
        client.close()
        closes = _extract_closes(raw if isinstance(raw, dict) else {})
        if not closes:
            return PremiumLeanResult(
                underlying=und,
                lean="HOLD",
                source="unavailable",
                layer="HYPOTHESIS",
                summary="OPTIDX rollingoption returned no closes — DI",
                data_gaps=["DATA_INSUFFICIENT: OPTIDX premium bars empty/unparsed"],
            )
        lean = _lean_from_closes(closes)
        return PremiumLeanResult(
            underlying=und,
            lean=lean,
            source="optidx_rolling",
            layer="SOURCE_FACT",
            summary=(
                f"OPTIDX rollingoption CALL ATM proxy lean={lean} "
                f"(n={len(closes)} closes). Not a fill model."
            ),
            bar_count=len(closes),
            data_gaps=["VALIDATION: ATM CALL path only; PE book not dual-fetched in v0"],
        )
    except Exception as exc:  # noqa: BLE001
        return PremiumLeanResult(
            underlying=und,
            lean="HOLD",
            source="unavailable",
            layer="HYPOTHESIS",
            summary=f"OPTIDX fetch failed ({type(exc).__name__})",
            data_gaps=[f"DATA_INSUFFICIENT: OPTIDX {type(exc).__name__}"],
        )


def index_proxy_lean(
    underlying: str,
    *,
    trend_plain: str = "",
    chain_lean: str = "NEUTRAL",
) -> PremiumLeanResult:
    """Labeled INDEX proxy when OPTIDX unavailable."""
    lean: PremiumLean = "HOLD"
    if chain_lean == "CE":
        lean = "BUY_CE"
    elif chain_lean == "PE":
        lean = "BUY_PE"
    return PremiumLeanResult(
        underlying=underlying.upper(),
        lean=lean,
        source="index_proxy",
        layer="HYPOTHESIS",
        summary=(
            f"INDEX proxy lean={lean} from chain_lean={chain_lean} "
            f"(not OPTIDX premium). trend={trend_plain[:80]!r}. "
            "Labeled HYPOTHESIS — not option-premium SOURCE_FACT."
        ),
        data_gaps=[
            "DATA_INSUFFICIENT: OPTIDX premium chart not fetched — INDEX proxy",
        ],
    )


def resolve_premium_lean(
    underlying: str,
    *,
    prefer_live: bool = False,
    trend_plain: str = "",
    chain_lean: str = "NEUTRAL",
    chain_watch: Optional[dict[str, Any]] = None,
) -> PremiumLeanResult:
    watch = chain_watch or {}
    atm_ce = watch.get("atm_ce_ltp")
    atm_pe = watch.get("atm_pe_ltp")
    side = str(chain_lean or "").upper()
    ltp = None
    if side == "CE":
        ltp = atm_ce
    elif side == "PE":
        ltp = atm_pe
    elif atm_ce is not None or atm_pe is not None:
        ltp = atm_ce if atm_ce is not None else atm_pe
    if prefer_live and ltp not in (None, ""):
        try:
            px = float(ltp)
        except (TypeError, ValueError):
            px = None
        if px is not None and px > 0:
            lean: PremiumLean = "HOLD"
            if side == "CE":
                lean = "BUY_CE"
            elif side == "PE":
                lean = "BUY_PE"
            strike = watch.get("atm_strike")
            try:
                strike_f = float(strike) if strike not in (None, "") else None
            except (TypeError, ValueError):
                strike_f = None
            return PremiumLeanResult(
                underlying=underlying.upper(),
                lean=lean,
                source="optionchain_atm",
                layer="SOURCE_FACT",
                summary=(
                    f"ATM option last_price={px} from live optionchain "
                    f"(side={side or 'n/a'} strike={strike_f}). "
                    "Entry=LTP · Stop=0.75× · Target=1.25× PAPER starter. Not a fill."
                ),
                bar_count=0,
                option_ltp=px,
                entry=px,
                stop=round(px * 0.75, 2),
                target=round(px * 1.25, 2),
                atm_strike=strike_f,
                data_gaps=[
                    "VALIDATION: ATM last_price from POST /optionchain — PAPER starter levels only"
                ],
            )
    if prefer_live:
        opt = try_optidx_premium_lean(underlying)
        if opt is not None and opt.source == "optidx_rolling":
            return opt
        if opt is not None and opt.source == "unavailable":
            proxy = index_proxy_lean(
                underlying, trend_plain=trend_plain, chain_lean=chain_lean
            )
            proxy.data_gaps = list(
                dict.fromkeys(list(opt.data_gaps) + list(proxy.data_gaps))
            )
            proxy.summary = opt.summary + " | " + proxy.summary
            return proxy
    return index_proxy_lean(underlying, trend_plain=trend_plain, chain_lean=chain_lean)
