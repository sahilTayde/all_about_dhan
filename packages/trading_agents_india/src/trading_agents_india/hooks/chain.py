"""Option-chain watcher inputs: Dhan chain if tokens work, else fixtures.

Flags fake-breakout / thin-wall as HYPOTHESIS; DI when no data.
Never invents live OI walls as SOURCE_FACT without a parseable chain.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

ChainLean = Literal["CE", "PE", "NEUTRAL", "NO_TRADE"]
HypothesisFlag = Literal[
    "NONE",
    "FAKE_BREAKOUT_HYPOTHESIS",
    "THIN_WALL_HYPOTHESIS",
    "BOTH_HYPOTHESIS",
]

# VERIFY vs workspace.yaml / instrument master — not hard truth.
_SCRIP_HINTS = {
    "NIFTY": (13, "IDX_I"),
    "BANKNIFTY": (25, "IDX_I"),
    "SENSEX": (51, "IDX_I"),
}
_STRIKE_STEP = {"NIFTY": 50.0, "BANKNIFTY": 100.0, "SENSEX": 100.0}
_ITM_POINTS = {"NIFTY": 100.0, "BANKNIFTY": 100.0, "SENSEX": 100.0}


def itm_wing_strikes(underlying: str, atm: float) -> dict[str, float]:
    """~100 pts ITM (STRAT-006 paper wing). CE below ATM, PE above. Not a promote."""
    und = underlying.upper()
    step = _STRIKE_STEP.get(und, 50.0)
    points = _ITM_POINTS.get(und, 100.0)
    n = max(1, int(round(float(points) / step)))
    atm_f = float(atm)
    return {"CE": atm_f - n * step, "PE": atm_f + n * step}


def _pack_leg(row: Any) -> dict[str, Any]:
    return {
        "ce": getattr(row, "ce_ltp", None),
        "pe": getattr(row, "pe_ltp", None),
        "ce_delta": getattr(row, "ce_delta", None),
        "pe_delta": getattr(row, "pe_delta", None),
        "ce_gamma": getattr(row, "ce_gamma", None),
        "pe_gamma": getattr(row, "pe_gamma", None),
        "ce_theta": getattr(row, "ce_theta", None),
        "pe_theta": getattr(row, "pe_theta", None),
        "ce_vega": getattr(row, "ce_vega", None),
        "pe_vega": getattr(row, "pe_vega", None),
        "ce_iv": getattr(row, "ce_iv", None),
        "pe_iv": getattr(row, "pe_iv", None),
        "ce_volume": getattr(row, "ce_volume", None),
        "pe_volume": getattr(row, "pe_volume", None),
        "ce_oi": getattr(row, "ce_oi", None),
        "pe_oi": getattr(row, "pe_oi", None),
    }


def _attach_itm_quotes(rows: list[Any], underlying: str, meta: dict[str, Any]) -> None:
    atm = meta.get("atm_strike")
    if atm is None:
        return
    by = {float(r.strike): r for r in rows}
    wings = itm_wing_strikes(underlying, float(atm))
    meta["itm_ce_strike"] = wings["CE"]
    meta["itm_pe_strike"] = wings["PE"]
    ce_row = by.get(float(wings["CE"]))
    pe_row = by.get(float(wings["PE"]))
    atm_row = by.get(float(atm))
    if ce_row is not None:
        meta["itm_ce_ltp"] = ce_row.ce_ltp
        meta["itm_ce_delta"] = ce_row.ce_delta
        meta["itm_ce_gamma"] = ce_row.ce_gamma
        meta["itm_ce_theta"] = ce_row.ce_theta
        meta["itm_ce_vega"] = ce_row.ce_vega
        meta["itm_ce_iv"] = ce_row.ce_iv
    if pe_row is not None:
        meta["itm_pe_ltp"] = pe_row.pe_ltp
        meta["itm_pe_delta"] = pe_row.pe_delta
        meta["itm_pe_gamma"] = pe_row.pe_gamma
        meta["itm_pe_theta"] = pe_row.pe_theta
        meta["itm_pe_vega"] = pe_row.pe_vega
        meta["itm_pe_iv"] = pe_row.pe_iv
    if atm_row is not None:
        meta["atm_ce_delta"] = atm_row.ce_delta
        meta["atm_pe_delta"] = atm_row.pe_delta
        meta["atm_ce_gamma"] = atm_row.ce_gamma
        meta["atm_pe_gamma"] = atm_row.pe_gamma
        meta["atm_ce_theta"] = atm_row.ce_theta
        meta["atm_pe_theta"] = atm_row.pe_theta
        meta["atm_ce_vega"] = atm_row.ce_vega
        meta["atm_pe_vega"] = atm_row.pe_vega
        meta["atm_ce_iv"] = atm_row.ce_iv
        meta["atm_pe_iv"] = atm_row.pe_iv
    step = _STRIKE_STEP.get(underlying.upper(), 50.0)
    quotes: dict[str, Any] = {}
    for k in range(-6, 7):
        strike = float(atm) + k * step
        row = by.get(strike)
        if row is None:
            continue
        key = str(int(strike)) if strike == int(strike) else str(strike)
        quotes[key] = _pack_leg(row)
    meta["wing_quotes"] = quotes


@dataclass
class ChainWatchResult:
    underlying: str
    source: str  # dhan_live | fixture | desk_intel | unavailable
    chain_lean: ChainLean
    hypothesis_flag: HypothesisFlag
    summary: str
    layer: str = "HYPOTHESIS"
    data_gaps: list[str] = field(default_factory=list)
    wall_notes: list[str] = field(default_factory=list)
    raw_keys: list[str] = field(default_factory=list)
    spot: Optional[float] = None
    strike_count: int = 0
    atm_strike: Optional[float] = None
    pcr_oi: Optional[float] = None
    atm_ce_ltp: Optional[float] = None
    atm_pe_ltp: Optional[float] = None
    itm_ce_strike: Optional[float] = None
    itm_pe_strike: Optional[float] = None
    itm_ce_ltp: Optional[float] = None
    itm_pe_ltp: Optional[float] = None
    atm_ce_iv: Optional[float] = None
    atm_pe_iv: Optional[float] = None
    atm_ce_delta: Optional[float] = None
    atm_pe_delta: Optional[float] = None
    atm_ce_gamma: Optional[float] = None
    atm_pe_gamma: Optional[float] = None
    atm_ce_theta: Optional[float] = None
    atm_pe_theta: Optional[float] = None
    itm_ce_iv: Optional[float] = None
    itm_pe_iv: Optional[float] = None
    itm_ce_delta: Optional[float] = None
    itm_pe_delta: Optional[float] = None
    itm_ce_gamma: Optional[float] = None
    itm_pe_gamma: Optional[float] = None
    itm_ce_theta: Optional[float] = None
    itm_pe_theta: Optional[float] = None
    atm_ce_vega: Optional[float] = None
    atm_pe_vega: Optional[float] = None
    itm_ce_vega: Optional[float] = None
    itm_pe_vega: Optional[float] = None
    atm_ce_volume: Optional[float] = None
    atm_pe_volume: Optional[float] = None
    pcr_volume: Optional[float] = None
    wing_quotes: dict[str, Any] = field(default_factory=dict)
    expiry: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fixture_watch(underlying: str, chain_lean: ChainLean) -> ChainWatchResult:
    flag: HypothesisFlag = "NONE"
    walls: list[str] = []
    if chain_lean == "NEUTRAL":
        flag = "THIN_WALL_HYPOTHESIS"
        walls.append(
            "HYPOTHESIS: fixture NEUTRAL lean — treat ATM walls as thin / untrusted"
        )
    elif chain_lean == "PE":
        # Soft fade days often fake CE breakouts then reverse — hypothesis only
        flag = "FAKE_BREAKOUT_HYPOTHESIS"
        walls.append(
            "HYPOTHESIS: PE lean fixture — watch for failed CE spray / fake breakout"
        )
    return ChainWatchResult(
        underlying=underlying,
        source="fixture",
        chain_lean=chain_lean,
        hypothesis_flag=flag,
        summary=(
            f"Chain watcher ({underlying}): fixture lean={chain_lean}; "
            f"flag={flag}. Not live OI. Fake-breakout/thin-wall are hypotheses only."
        ),
        data_gaps=[
            "DATA_INSUFFICIENT: live Dhan chain not required for dry fixtures",
        ],
        wall_notes=walls,
    )


def _metrics_from_dhan_payload(
    payload: dict[str, Any],
    *,
    underlying: str,
    expiry: Optional[str],
) -> tuple[ChainLean, list[str], dict[str, Any]]:
    """Parse documented Dhan ``data.oc`` / ``last_price`` via desk-intel.

    Lean from ATM±N OI buildup (CHAIN_METRICS VALIDATION stub) — not a promote.
    """
    meta: dict[str, Any] = {
        "spot": None,
        "strike_count": 0,
        "atm_strike": None,
        "pcr_oi": None,
        "atm_ce_ltp": None,
        "atm_pe_ltp": None,
        "itm_ce_strike": None,
        "itm_pe_strike": None,
        "itm_ce_ltp": None,
        "itm_pe_ltp": None,
        "atm_ce_volume": None,
        "atm_pe_volume": None,
        "pcr_volume": None,
        "wing_quotes": {},
        "expiry": expiry,
    }
    try:
        from desk_intel.option_chain_poller import (
            atm_index,
            compute_chain_bias,
            parse_oc,
            unwrap_chain_payload,
        )
        from desk_intel.schema import ChainSnapshot
        from desk_intel.time_ist import now_ist_iso
    except Exception:
        return _parse_chain_lean_from_payload(payload)[0], [
            "DATA_INSUFFICIENT: desk_intel chain parser unavailable — NEUTRAL"
        ], meta

    data = unwrap_chain_payload(payload)
    if not data:
        lean, gaps = _parse_chain_lean_from_payload(payload)
        gaps.append("DATA_INSUFFICIENT: option-chain payload has no data.oc")
        return lean, gaps, meta

    spot_raw = data.get("last_price")
    try:
        spot = float(spot_raw) if spot_raw not in (None, "") else None
    except (TypeError, ValueError):
        spot = None
    rows = parse_oc(data.get("oc"))
    meta["spot"] = spot
    meta["strike_count"] = len(rows)
    if not rows:
        return "NEUTRAL", [
            "DATA_INSUFFICIENT: option-chain oc empty after parse — NEUTRAL"
        ], meta

    idx = atm_index(rows, spot)
    atm = rows[idx] if idx is not None else None
    if atm is not None:
        meta["atm_strike"] = float(atm.strike)
        meta["atm_ce_ltp"] = atm.ce_ltp
        meta["atm_pe_ltp"] = atm.pe_ltp
        meta["atm_ce_volume"] = atm.ce_volume
        meta["atm_pe_volume"] = atm.pe_volume
        _attach_itm_quotes(rows, underlying, meta)

    snap = ChainSnapshot(
        underlying=underlying,
        expiry=expiry,
        spot=spot,
        as_of_ist=now_ist_iso(),
        mode="full_chain_3m",
        dry_run=False,
        strikes=rows,
        source="dhan_option_chain",
        note="agent tick parse — CHAIN_METRICS VALIDATION stub",
    )

    class _Wing:
        atm_wing = 2

    bias = compute_chain_bias(snap, _Wing())  # type: ignore[arg-type]
    lean = str(bias.lean or "NEUTRAL").upper()
    if lean not in ("CE", "PE", "NEUTRAL", "NO_TRADE"):
        lean = "NEUTRAL"
    meta["pcr_oi"] = bias.pcr_oi
    meta["pcr_volume"] = getattr(bias, "pcr_volume", None)
    meta["atm_strike"] = bias.atm_strike if bias.atm_strike is not None else meta["atm_strike"]
    if meta.get("atm_strike") is not None:
        _attach_itm_quotes(rows, underlying, meta)
    gaps: list[str] = []
    if lean == "NEUTRAL":
        gaps.append(
            "VALIDATION: chain oc parsed; ATM±N buildup not decisive — lean NEUTRAL (not missing payload)"
        )
    return lean, gaps, meta  # type: ignore[return-value]


def _parse_chain_lean_from_payload(payload: dict[str, Any]) -> tuple[ChainLean, list[str]]:
    """Fallback: explicit bias fields only; else DI→NEUTRAL."""
    gaps: list[str] = []
    for key in ("chain_lean", "lean", "bias", "option_bias"):
        val = payload.get(key)
        if isinstance(val, str) and val.upper() in ("CE", "PE", "NEUTRAL", "NO_TRADE"):
            return val.upper(), gaps  # type: ignore[return-value]
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("chain_lean", "lean"):
            val = data.get(key)
            if isinstance(val, str) and val.upper() in ("CE", "PE", "NEUTRAL", "NO_TRADE"):
                return val.upper(), gaps  # type: ignore[return-value]
    gaps.append(
        "DATA_INSUFFICIENT: option-chain payload lacks parseable lean — NEUTRAL"
    )
    return "NEUTRAL", gaps


def _hypotheses_from_lean(lean: ChainLean) -> tuple[HypothesisFlag, list[str]]:
    if lean == "NEUTRAL":
        return "THIN_WALL_HYPOTHESIS", [
            "HYPOTHESIS: thin/unclear wall — do not treat as alpha"
        ]
    if lean == "NO_TRADE":
        return "BOTH_HYPOTHESIS", [
            "HYPOTHESIS: NO_TRADE chain — fake-breakout + thin wall risk"
        ]
    return "NONE", []


def try_fetch_dhan_chain(underlying: str) -> Optional[ChainWatchResult]:
    """Attempt live Dhan optionchain. Fail soft → None (caller uses fixture)."""
    und = underlying.upper()
    hint = _SCRIP_HINTS.get(und)
    if hint is None:
        return None
    scrip, seg = hint
    try:
        from dhan_client import DhanClient  # type: ignore
    except Exception:
        return None
    try:
        client = DhanClient(dry_run=False)
        # If tokens empty, client may dry-run or error — treat as unavailable
        if getattr(client.settings, "dry_run", True):
            client.close()
            return None
        body_u = {"UnderlyingScrip": scrip, "UnderlyingSeg": seg}
        expiries = client.option_chain.expiry_list(body_u)
        # Expiry list shape varies — pick first string date if present
        expiry = None
        data = expiries.get("data") if isinstance(expiries, dict) else None
        if isinstance(data, list) and data:
            expiry = str(data[0])
        elif isinstance(data, dict):
            lst = data.get("expiryList") or data.get("expiries") or []
            if lst:
                expiry = str(lst[0])
        if not expiry:
            client.close()
            return ChainWatchResult(
                underlying=und,
                source="unavailable",
                chain_lean="NEUTRAL",
                hypothesis_flag="THIN_WALL_HYPOTHESIS",
                summary="Dhan expiry list empty/unparsed — DI",
                data_gaps=["DATA_INSUFFICIENT: no expiry from Dhan optionchain"],
            )
        raw = client.option_chain.chain({**body_u, "Expiry": expiry})
        client.close()
        lean, gaps, meta = _metrics_from_dhan_payload(
            raw if isinstance(raw, dict) else {},
            underlying=und,
            expiry=expiry,
        )
        flag, walls = _hypotheses_from_lean(lean)
        keys = sorted(raw.keys()) if isinstance(raw, dict) else []
        pcr = meta.get("pcr_oi")
        pcr_txt = f"{pcr:.2f}" if isinstance(pcr, float) else "n/a"
        return ChainWatchResult(
            underlying=und,
            source="dhan_live",
            chain_lean=lean,
            hypothesis_flag=flag,
            summary=(
                f"Chain watcher ({und}): Dhan POST /optionchain lean={lean}; "
                f"spot={meta.get('spot')} atm={meta.get('atm_strike')} "
                f"strikes={meta.get('strike_count')} PCR(OI)={pcr_txt}; "
                f"flag={flag}. Buildup lean is CHAIN_METRICS VALIDATION stub."
            ),
            layer="SOURCE_FACT" if lean != "NEUTRAL" or "DATA_INSUFFICIENT" not in str(gaps) else "HYPOTHESIS",
            data_gaps=gaps
            + [
                "VALIDATION: OI wall / fake-breakout still HYPOTHESIS without validated parser"
            ],
            wall_notes=walls,
            raw_keys=keys[:24],
            spot=meta.get("spot"),
            strike_count=int(meta.get("strike_count") or 0),
            atm_strike=meta.get("atm_strike"),
            pcr_oi=meta.get("pcr_oi"),
            atm_ce_ltp=meta.get("atm_ce_ltp"),
            atm_pe_ltp=meta.get("atm_pe_ltp"),
            itm_ce_strike=meta.get("itm_ce_strike"),
            itm_pe_strike=meta.get("itm_pe_strike"),
            itm_ce_ltp=meta.get("itm_ce_ltp"),
            itm_pe_ltp=meta.get("itm_pe_ltp"),
            atm_ce_iv=meta.get("atm_ce_iv"),
            atm_pe_iv=meta.get("atm_pe_iv"),
            atm_ce_delta=meta.get("atm_ce_delta"),
            atm_pe_delta=meta.get("atm_pe_delta"),
            atm_ce_gamma=meta.get("atm_ce_gamma"),
            atm_pe_gamma=meta.get("atm_pe_gamma"),
            atm_ce_theta=meta.get("atm_ce_theta"),
            atm_pe_theta=meta.get("atm_pe_theta"),
            itm_ce_iv=meta.get("itm_ce_iv"),
            itm_pe_iv=meta.get("itm_pe_iv"),
            itm_ce_delta=meta.get("itm_ce_delta"),
            itm_pe_delta=meta.get("itm_pe_delta"),
            itm_ce_gamma=meta.get("itm_ce_gamma"),
            itm_pe_gamma=meta.get("itm_pe_gamma"),
            itm_ce_theta=meta.get("itm_ce_theta"),
            itm_pe_theta=meta.get("itm_pe_theta"),
            atm_ce_vega=meta.get("atm_ce_vega"),
            atm_pe_vega=meta.get("atm_pe_vega"),
            itm_ce_vega=meta.get("itm_ce_vega"),
            itm_pe_vega=meta.get("itm_pe_vega"),
            atm_ce_volume=meta.get("atm_ce_volume"),
            atm_pe_volume=meta.get("atm_pe_volume"),
            pcr_volume=meta.get("pcr_volume"),
            wing_quotes=meta.get("wing_quotes") or {},
            expiry=expiry,
        )
    except Exception as exc:  # noqa: BLE001
        return ChainWatchResult(
            underlying=und,
            source="unavailable",
            chain_lean="NEUTRAL",
            hypothesis_flag="THIN_WALL_HYPOTHESIS",
            summary=f"Dhan chain fetch failed ({type(exc).__name__}) — DI",
            data_gaps=[f"DATA_INSUFFICIENT: dhan chain error {type(exc).__name__}"],
        )


def watch_chain(
    underlying: str,
    *,
    fixture_lean: ChainLean = "NEUTRAL",
    prefer_live: bool = False,
) -> ChainWatchResult:
    if prefer_live:
        live = try_fetch_dhan_chain(underlying)
        if live is not None and live.source == "dhan_live":
            return live
        if live is not None and live.source == "unavailable":
            # Merge DI onto fixture
            fx = _fixture_watch(underlying, fixture_lean)
            fx.data_gaps = list(dict.fromkeys(list(live.data_gaps) + list(fx.data_gaps)))
            fx.summary = live.summary + " | falling back to fixture. " + fx.summary
            return fx
    return _fixture_watch(underlying, fixture_lean)
