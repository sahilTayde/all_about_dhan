"""WAITING MIX-LEAN / impulse / PCR-hold / INDEX-proxy scores from gather.

PAPER only. NO_PROMOTE. Never CONFIRMED (5m ST/MACD stays confirm-or-kill).
Does not rewrite MIX-DEFAULT-BUY. Empty SL/TP when ATM LTP is missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

IMPULSE_LOOKBACK_BARS = 5
IMPULSE_MIN_FRAC = 0.0008  # HYPOTHESIS short-lookback; not a win-rate claim

LEAN_MIX_IDS = (
    "MIX-LEAN-SPOT-ATM",
    "MIX-IMPULSE-1M",
    "MIX-003-INDEX-PROXY",
    "MIX-006-INDEX-PROXY",
    "MIX-PCR-EXTREME-HOLD",
    "MIX-SELL-CREDIT-PARK",
    "MIX-DUAL-INDEX-MASTER",
)


@dataclass
class MixScore:
    mix_id: str
    available: bool
    lean: str  # BUY_CE | BUY_PE | HOLD
    stage: str  # WATCH | EARLY | VETOED | PARKED
    outcome: str
    data_gaps: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    entry: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None


def _close(bar: Any) -> Optional[float]:
    try:
        if isinstance(bar, dict):
            return float(bar["close"])
        return float(bar.close)
    except (TypeError, ValueError, KeyError, AttributeError):
        return None


def _last_close(bars: Optional[list[Any]]) -> Optional[float]:
    if not bars:
        return None
    return _close(bars[-1])


def _bar_field(bar: Any, field: str) -> Optional[float]:
    try:
        if isinstance(bar, dict):
            return float(bar[field])
        return float(getattr(bar, field))
    except (TypeError, ValueError, KeyError, AttributeError):
        return None


def _ema(values: list[float], length: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if len(values) < length:
        return out
    seed = sum(values[:length]) / length
    out[length - 1] = seed
    prev = seed
    k = 2.0 / (length + 1.0)
    for i in range(length, len(values)):
        prev = values[i] * k + prev * (1.0 - k)
        out[i] = prev
    return out


def _session_vwap_last(bars: list[Any]) -> Optional[float]:
    num = 0.0
    den = 0.0
    for bar in bars:
        high = _bar_field(bar, "high")
        low = _bar_field(bar, "low")
        close = _bar_field(bar, "close")
        if high is None or low is None or close is None:
            continue
        volume = _bar_field(bar, "volume")
        weight = volume if volume and volume > 0 else 1.0
        num += ((high + low + close) / 3.0) * weight
        den += weight
    return num / den if den else None


def _premium_levels(prem: dict[str, Any], side: str) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """ATM LTP ticket numbers only. Empty SL/TP when LTP missing."""
    ltp = prem.get("option_ltp") or prem.get("ltp") or prem.get("entry")
    src = str(prem.get("source") or "")
    try:
        px = float(ltp) if ltp not in (None, "") else None
    except (TypeError, ValueError):
        px = None
    if px is None or px <= 0 or src in ("index_proxy", "unavailable", ""):
        # INDEX proxy must not fill option SL/TP.
        if src != "optionchain_atm":
            return None, None, None
    if px is None or px <= 0:
        return None, None, None
    if side not in ("BUY_CE", "BUY_PE"):
        return px, None, None
    return px, round(px * 0.75, 2), round(px * 1.25, 2)


def _spot(ticket: Any, bars: Optional[list[Any]]) -> Optional[float]:
    prem = getattr(ticket, "premium_lean", None) or {}
    for key in ("spot",):
        raw = prem.get(key)
        try:
            if raw not in (None, ""):
                return float(raw)
        except (TypeError, ValueError):
            pass
    meta = getattr(ticket, "index_bar_meta", None) or {}
    raw = meta.get("last_close")
    try:
        if raw not in (None, ""):
            return float(raw)
    except (TypeError, ValueError):
        pass
    return _last_close(bars)


def _chain_lean(ticket: Any) -> str:
    prem = getattr(ticket, "premium_lean", None) or {}
    watch = prem  # pipeline copies chain fields onto premium_lean
    for key in ("chain_lean",):
        val = str(watch.get(key) or "").upper()
        if val in ("CE", "PE", "NEUTRAL", "NO_TRADE"):
            return val
    # Heartbeat stores lean as BUY_CE from premium; chain watcher may be in provenance
    lean = str(prem.get("lean") or "").upper()
    if lean == "BUY_CE":
        return "CE"
    if lean == "BUY_PE":
        return "PE"
    blob = " ".join(str(x) for x in list(getattr(ticket, "reasons", None) or [])).upper()
    if "CHAIN_LEAN=CE" in blob or "LEAN=CE" in blob:
        return "CE"
    if "CHAIN_LEAN=PE" in blob or "LEAN=PE" in blob:
        return "PE"
    return "NEUTRAL"


def _pcr(ticket: Any) -> Optional[float]:
    prem = getattr(ticket, "premium_lean", None) or {}
    raw = prem.get("pcr_oi")
    try:
        if raw not in (None, ""):
            return float(raw)
    except (TypeError, ValueError):
        return None
    return None


def _source(ticket: Any) -> str:
    prem = getattr(ticket, "premium_lean", None) or {}
    return str(prem.get("source") or "")


def score_pcr_extreme_hold(ticket: Any, *, bars: Optional[list[Any]] = None) -> MixScore:
    """HOLD overlay. PCR without price is not an entry. No numeric PCR law."""
    pcr = _pcr(ticket)
    spot = _spot(ticket, bars)
    chain = _chain_lean(ticket)
    gaps: list[str] = []
    if pcr is None:
        gaps.append("DATA_INSUFFICIENT: MIX-PCR-EXTREME-HOLD — PCR(OI) not on gather")
        return MixScore(
            mix_id="MIX-PCR-EXTREME-HOLD",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="ALLOW",
            data_gaps=gaps,
            reasons=["PCR not on ticket — overlay idle (not a STRAT delete)"],
            provenance={
                "layer": "HYPOTHESIS",
                "NO_PROMOTE": True,
                "customer_default": False,
                "note": "03 CHAIN_METRICS: extreme PCR without price is not a signal",
            },
        )
    # SOURCE_FACT: PCR present. VALIDATION: without spot, PCR-only = hold.
    if spot is None or chain in ("NEUTRAL", "NO_TRADE"):
        return MixScore(
            mix_id="MIX-PCR-EXTREME-HOLD",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="HOLD",
            data_gaps=[],
            reasons=[
                "MIX-PCR-EXTREME-HOLD: PCR(OI) present without a priced CE/PE wall — HOLD ticket",
                "05 CUSTOMER_TALK: news/extreme PCR = hold, not alpha, not catalog delete",
            ],
            provenance={
                "layer": "VALIDATION",
                "NO_PROMOTE": True,
                "customer_default": False,
                "pcr_oi": pcr,
                "chain_lean": chain,
                "spot": spot,
                "win_rate": None,
            },
        )
    return MixScore(
        mix_id="MIX-PCR-EXTREME-HOLD",
        available=True,
        lean="HOLD",
        stage="WATCH",
        outcome="ALLOW",
        data_gaps=[],
        reasons=["PCR present with priced chain lean — overlay idle; not an entry MIX"],
        provenance={
            "layer": "HYPOTHESIS",
            "NO_PROMOTE": True,
            "customer_default": False,
            "pcr_oi": pcr,
            "chain_lean": chain,
        },
    )


def score_lean_spot_atm(ticket: Any, *, bars: Optional[list[Any]] = None) -> MixScore:
    """INDEX last + ATM PCR/OI wall → BUY_CE / BUY_PE WATCH/EARLY."""
    prem = getattr(ticket, "premium_lean", None) or {}
    spot = _spot(ticket, bars)
    chain = _chain_lean(ticket)
    src = _source(ticket)
    gaps: list[str] = []
    if spot is None:
        gaps.append("DATA_INSUFFICIENT: MIX-LEAN-SPOT-ATM needs INDEX last / spot")
    if chain not in ("CE", "PE"):
        gaps.append("DATA_INSUFFICIENT: MIX-LEAN-SPOT-ATM needs ATM OI-wall lean CE|PE")
    if spot is None or chain not in ("CE", "PE"):
        return MixScore(
            mix_id="MIX-LEAN-SPOT-ATM",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="DATA_INSUFFICIENT" if gaps else "WATCH",
            data_gaps=gaps,
            reasons=["MIX-LEAN-SPOT-ATM waiting on INDEX last + ATM wall"],
            provenance={
                "origin": "PROJECT-DERIVED",
                "layer": "HYPOTHESIS",
                "NO_PROMOTE": True,
                "customer_default": False,
                "premium_source": src,
            },
        )
    lean = "BUY_CE" if chain == "CE" else "BUY_PE"
    entry, stop, target = _premium_levels(prem, lean)
    has_ltp = entry is not None
    stage = "EARLY" if has_ltp and src == "optionchain_atm" else "WATCH"
    if not has_ltp:
        gaps.append("DATA_INSUFFICIENT: ATM LTP missing — Entry/SL/TP empty (not index pts)")
    return MixScore(
        mix_id="MIX-LEAN-SPOT-ATM",
        available=True,
        lean=lean,
        stage=stage,
        outcome=lean,
        data_gaps=gaps,
        reasons=[
            f"MIX-LEAN-SPOT-ATM {lean} from INDEX last={spot} + ATM OI wall={chain}",
            "PROJECT-DERIVED WAITING — not MIX-DEFAULT-BUY; NO_PROMOTE",
            "EARLY is a valid ticket; 5m ST/MACD remains confirm-or-kill (not CONFIRMED)",
        ],
        provenance={
            "origin": "PROJECT-DERIVED",
            "layer": "HYPOTHESIS",
            "NO_PROMOTE": True,
            "customer_default": False,
            "spot": spot,
            "chain_lean": chain,
            "premium_source": src,
            "win_rate": None,
        },
        entry=entry,
        stop=stop,
        target=target,
    )


def score_impulse_1m(ticket: Any, *, bars: Optional[list[Any]] = None) -> MixScore:
    """1m close vs short lookback; ATM LTP for ticket numbers only."""
    prem = getattr(ticket, "premium_lean", None) or {}
    src = _source(ticket)
    if not bars or len(bars) <= IMPULSE_LOOKBACK_BARS:
        return MixScore(
            mix_id="MIX-IMPULSE-1M",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="DATA_INSUFFICIENT",
            data_gaps=["DATA_INSUFFICIENT: MIX-IMPULSE-1M needs INDEX 1m lookback bars"],
            reasons=["impulse waiting on INDEX 1m"],
            provenance={
                "origin": "PROJECT-DERIVED",
                "layer": "HYPOTHESIS",
                "NO_PROMOTE": True,
                "customer_default": False,
                "lookback_bars": IMPULSE_LOOKBACK_BARS,
            },
        )
    last = _close(bars[-1])
    prev = _close(bars[-(IMPULSE_LOOKBACK_BARS + 1)])
    if last is None or prev is None or prev <= 0:
        return MixScore(
            mix_id="MIX-IMPULSE-1M",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="DATA_INSUFFICIENT",
            data_gaps=["DATA_INSUFFICIENT: MIX-IMPULSE-1M closes unparseable"],
            reasons=[],
            provenance={"origin": "PROJECT-DERIVED", "NO_PROMOTE": True, "customer_default": False},
        )
    chg = (last - prev) / prev
    lean = "HOLD"
    if chg > IMPULSE_MIN_FRAC:
        lean = "BUY_CE"
    elif chg < -IMPULSE_MIN_FRAC:
        lean = "BUY_PE"
    entry, stop, target = _premium_levels(prem, lean) if lean != "HOLD" else (None, None, None)
    gaps: list[str] = []
    if lean != "HOLD" and entry is None:
        gaps.append("DATA_INSUFFICIENT: ATM LTP missing — ticket numbers empty")
    stage = "WATCH"
    if lean != "HOLD":
        stage = "EARLY" if entry is not None and src == "optionchain_atm" else "WATCH"
    return MixScore(
        mix_id="MIX-IMPULSE-1M",
        available=True,
        lean=lean,
        stage=stage if lean != "HOLD" else "WATCH",
        outcome=lean if lean != "HOLD" else "WATCH",
        data_gaps=gaps,
        reasons=[
            f"MIX-IMPULSE-1M close {last} vs lookback {prev} frac={chg:.5f} → {lean}",
            "ATM LTP used for Entry/SL/TP only; INDEX pts never pasted as premium",
            "PROJECT-DERIVED WAITING — NO_PROMOTE; not CONFIRMED",
        ],
        provenance={
            "origin": "PROJECT-DERIVED",
            "layer": "HYPOTHESIS",
            "NO_PROMOTE": True,
            "customer_default": False,
            "lookback_bars": IMPULSE_LOOKBACK_BARS,
            "frac": chg,
            "last_close": last,
            "premium_source": src,
            "win_rate": None,
        },
        entry=entry,
        stop=stop,
        target=target,
    )


def _last_non_skip(leans: list[str]) -> str:
    for val in reversed(leans):
        if val in ("CE", "PE"):
            return val
    return "SKIP"


def score_003_index_proxy(ticket: Any, *, bars: Optional[list[Any]] = None) -> MixScore:
    """STRAT-003 recipe on INDEX 1m→3m resample. PROXY ≠ FUTIDX/OPTIDX."""
    if not bars or len(bars) < 40:
        return MixScore(
            mix_id="MIX-003-INDEX-PROXY",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="DATA_INSUFFICIENT",
            data_gaps=["DATA_INSUFFICIENT: MIX-003-INDEX-PROXY needs INDEX 1m (≥40) to resample 3m"],
            reasons=["PROXY WAITING — spoken 003 is 3m FUTIDX"],
            provenance={
                "recipe_origin": "DHAN-DERIVED",
                "path_origin": "PROJECT-DERIVED",
                "proxy_label": "INDEX_RESAMPLE_NE_FUTIDX",
                "NO_PROMOTE": True,
                "customer_default": False,
            },
        )
    try:
        from backtest_engine.algos import strat_003_leans
        from backtest_engine.resample import resample
    except Exception as exc:  # pragma: no cover
        return MixScore(
            mix_id="MIX-003-INDEX-PROXY",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="DATA_INSUFFICIENT",
            data_gaps=[f"DATA_INSUFFICIENT: strat_003 import {exc.__class__.__name__}"],
            reasons=[],
            provenance={"NO_PROMOTE": True, "customer_default": False},
        )
    bars_3m = resample(bars, 3)
    leans = strat_003_leans(bars_3m, equal_weight_vwap=True)
    side = _last_non_skip(leans)
    lean = "HOLD"
    if side == "CE":
        lean = "BUY_CE"
    elif side == "PE":
        lean = "BUY_PE"
    return MixScore(
        mix_id="MIX-003-INDEX-PROXY",
        available=True,
        lean=lean,
        stage="WATCH",
        outcome=lean if lean != "HOLD" else "WATCH",
        data_gaps=[
            "VALIDATION: INDEX 1m resampled 3m ≠ spoken FUTIDX 3m — PROXY labeled"
        ],
        reasons=[
            f"MIX-003-INDEX-PROXY last all-three={side} on INDEX resample (not FUTIDX)",
            "WAITING PROXY — not customer default; 5m ST/MACD not used as entry",
        ],
        provenance={
            "recipe_origin": "DHAN-DERIVED",
            "path_origin": "PROJECT-DERIVED",
            "proxy_label": "INDEX_RESAMPLE_NE_FUTIDX",
            "layer": "HYPOTHESIS",
            "NO_PROMOTE": True,
            "customer_default": False,
            "bars_3m": len(bars_3m),
            "win_rate": None,
        },
    )


def score_006_index_proxy(ticket: Any, *, bars: Optional[list[Any]] = None) -> MixScore:
    """STRAT-006 EMA 10/20 on INDEX 1m→2m. PROXY ≠ OPTIDX premium tape."""
    if not bars or len(bars) < 40:
        return MixScore(
            mix_id="MIX-006-INDEX-PROXY",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="DATA_INSUFFICIENT",
            data_gaps=["DATA_INSUFFICIENT: MIX-006-INDEX-PROXY needs INDEX 1m (≥40)"],
            reasons=["PROXY WAITING — spoken 006 is 2m premium"],
            provenance={
                "recipe_origin": "DHAN-DERIVED",
                "path_origin": "PROJECT-DERIVED",
                "proxy_label": "INDEX_RESAMPLE_NE_OPTIDX",
                "NO_PROMOTE": True,
                "customer_default": False,
            },
        )
    try:
        from backtest_engine.algos import strat_006_leans
    except Exception as exc:  # pragma: no cover
        return MixScore(
            mix_id="MIX-006-INDEX-PROXY",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="DATA_INSUFFICIENT",
            data_gaps=[f"DATA_INSUFFICIENT: strat_006 import {exc.__class__.__name__}"],
            reasons=[],
            provenance={"NO_PROMOTE": True, "customer_default": False},
        )
    _bars2, leans = strat_006_leans(bars)
    side = _last_non_skip(leans)
    lean = "HOLD"
    if side == "CE":
        lean = "BUY_CE"
    elif side == "PE":
        lean = "BUY_PE"
    return MixScore(
        mix_id="MIX-006-INDEX-PROXY",
        available=True,
        lean=lean,
        stage="WATCH",
        outcome=lean if lean != "HOLD" else "WATCH",
        data_gaps=["VALIDATION: INDEX 1m resampled 2m ≠ OPTIDX 2m — PROXY labeled"],
        reasons=[
            f"MIX-006-INDEX-PROXY last EMA10/20={side} on INDEX resample (not OPTIDX)",
            "WAITING PROXY — VIX filter still DATA_INSUFFICIENT; NO_PROMOTE",
        ],
        provenance={
            "recipe_origin": "DHAN-DERIVED",
            "path_origin": "PROJECT-DERIVED",
            "proxy_label": "INDEX_RESAMPLE_NE_OPTIDX",
            "layer": "HYPOTHESIS",
            "NO_PROMOTE": True,
            "customer_default": False,
            "win_rate": None,
        },
    )


def score_sell_credit_park(_ticket: Any, *, bars: Optional[list[Any]] = None) -> MixScore:
    _ = bars
    return MixScore(
        mix_id="MIX-SELL-CREDIT-PARK",
        available=True,
        lean="HOLD",
        stage="PARKED",
        outcome="PARKED",
        data_gaps=[],
        reasons=[
            "MIX-SELL-CREDIT-PARK: STRAT-013/014 seller books — never evaluated as buy entries",
            "KEEP_ALL IDs stay; WAITING not buy UI",
        ],
        provenance={
            "origin": "DHAN-DERIVED",
            "layer": "SOURCE_FACT",
            "NO_PROMOTE": True,
            "customer_default": False,
            "attached": ["STRAT-013", "STRAT-014"],
            "phase1_buy_ui": False,
        },
    )


def score_dual_index_master(
    ticket: Any,
    *,
    bars: Optional[list[Any]] = None,
    premium_bars: Optional[list[Any]] = None,
) -> MixScore:
    """SENSEX-only shadow candidate from MRR dual-index backtest.

    With a persisted rolling 1m CALL premium tape (``premium_bars``) the full
    premium gate is evaluated (same math as scripts/backtest_mrr.py). Without
    it, this scorer records readiness and blockers only. Either way the output
    is paper-watch observation: NO_PROMOTE, never a customer ticket rewrite.
    """
    underlying = str(getattr(ticket, "underlying", "") or "").upper()
    if underlying == "NIFTY":
        return MixScore(
            mix_id="MIX-DUAL-INDEX-MASTER",
            available=True,
            lean="HOLD",
            stage="PARKED",
            outcome="PARKED",
            data_gaps=[],
            reasons=[
                "MIX-DUAL-INDEX-MASTER: NIFTY arm failed latest 1m CALL premium backtest",
                "Recorded for audit only; do not promote or route customer ticket",
            ],
            provenance={
                "origin": "PROJECT-DERIVED",
                "layer": "HYPOTHESIS",
                "NO_PROMOTE": True,
                "customer_default": False,
                "latest_shadow_oos_expectancy": -3.3988,
            },
        )
    if underlying == "BANKNIFTY":
        return MixScore(
            mix_id="MIX-DUAL-INDEX-MASTER",
            available=True,
            lean="HOLD",
            stage="PARKED",
            outcome="PARKED",
            data_gaps=[],
            reasons=[
                "MIX-DUAL-INDEX-MASTER: BANKNIFTY not part of dual-index spec",
                "Avoid until separate BANKNIFTY risk/spot rules exist",
            ],
            provenance={
                "origin": "PROJECT-DERIVED",
                "layer": "HYPOTHESIS",
                "NO_PROMOTE": True,
                "customer_default": False,
            },
        )
    if underlying != "SENSEX":
        return MixScore(
            mix_id="MIX-DUAL-INDEX-MASTER",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="DATA_INSUFFICIENT",
            data_gaps=[f"DATA_INSUFFICIENT: unsupported underlying {underlying or '?'}"],
            reasons=["MIX-DUAL-INDEX-MASTER supports SENSEX working path only"],
            provenance={"origin": "PROJECT-DERIVED", "NO_PROMOTE": True, "customer_default": False},
        )
    gaps: list[str] = []
    if not bars or len(bars) < 25:
        gaps.append("DATA_INSUFFICIENT: SENSEX index 1m bars <25 for spot VWAP/EMA21 gate")
        spot_bullish = False
        spot = None
        spot_vwap = None
        spot_ema21 = None
    else:
        closes = [_close(b) for b in bars]
        valid_closes = [c for c in closes if c is not None]
        spot = valid_closes[-1] if valid_closes else None
        spot_vwap = _session_vwap_last(bars)
        ema21 = _ema(valid_closes, 21)
        spot_ema21 = ema21[-1] if ema21 else None
        spot_bullish = (
            spot is not None
            and spot_vwap is not None
            and spot_ema21 is not None
            and spot > spot_vwap
            and spot > spot_ema21
        )
    prem = getattr(ticket, "premium_lean", None) or {}
    premium_source = str(prem.get("source") or "")
    option_ltp = prem.get("option_ltp") or prem.get("ltp") or prem.get("entry")
    if option_ltp in (None, ""):
        gaps.append("DATA_INSUFFICIENT: SENSEX CALL option LTP missing on ticket")

    gate: dict[str, Any] = {"evaluated": False, "reason": "no premium tape passed"}
    lean: str = "HOLD"
    reasons: list[str]
    if premium_bars:
        from trading_agents_india.premium_tape import dual_master_gate

        gate = dual_master_gate(list(premium_bars))
    if gate.get("evaluated"):
        premium_pass = bool(gate.get("all_pass"))
        if premium_pass and spot_bullish:
            lean = "BUY_CE"
            outcome = "WATCH"
            reasons = [
                "MIX-DUAL-INDEX-MASTER SENSEX: premium gate + spot gate all pass",
                "Paper-watch observation only — 5m confirm-or-kill not applied; NO_PROMOTE",
            ]
        else:
            failed = [k for k, v in (gate.get("conditions") or {}).items() if not v]
            if not spot_bullish:
                failed.append("spot_bullish")
            outcome = "WATCH"
            reasons = [
                "MIX-DUAL-INDEX-MASTER SENSEX: gate evaluated on persisted premium tape",
                f"Failed conditions: {', '.join(failed) or 'none'}",
            ]
    else:
        gaps.append(
            "DATA_INSUFFICIENT: MIX-DUAL-INDEX-MASTER needs rolling 1m SENSEX CALL premium OHLC "
            "for MRR/VWAP/SuperTrend/EMA/volume replay; current loop has only snapshot LTP"
        )
        outcome = "DATA_INSUFFICIENT" if spot_bullish else "WATCH"
        reasons = [
            f"MIX-DUAL-INDEX-MASTER SENSEX spot_bullish={spot_bullish}",
            "Waiting on option premium OHLC persistence before paper-watch signals",
        ]
    reasons.append("Latest cached backtest positive but UNVALIDATED; NO_PROMOTE")
    return MixScore(
        mix_id="MIX-DUAL-INDEX-MASTER",
        available=True,
        lean=lean,  # type: ignore[arg-type]
        stage="WATCH",
        outcome=outcome,
        data_gaps=list(dict.fromkeys(gaps)),
        reasons=reasons,
        provenance={
            "origin": "PROJECT-DERIVED",
            "layer": "HYPOTHESIS",
            "NO_PROMOTE": True,
            "customer_default": False,
            "spot": spot,
            "spot_vwap": spot_vwap,
            "spot_ema21": spot_ema21,
            "spot_bullish": spot_bullish,
            "premium_source": premium_source,
            "option_ltp_present": option_ltp not in (None, ""),
            "premium_gate": gate,
            "latest_shadow_report": "teams/06_backtesting/docs/MRR_BACKTEST_2026-09-10.md",
            "latest_shadow_oos_win_rate": 0.3711,
            "latest_shadow_oos_expectancy": 4.8399,
            "win_rate_claim": None,
        },
    )


SCORERS = {
    "MIX-LEAN-SPOT-ATM": score_lean_spot_atm,
    "MIX-IMPULSE-1M": score_impulse_1m,
    "MIX-003-INDEX-PROXY": score_003_index_proxy,
    "MIX-006-INDEX-PROXY": score_006_index_proxy,
    "MIX-PCR-EXTREME-HOLD": score_pcr_extreme_hold,
    "MIX-SELL-CREDIT-PARK": score_sell_credit_park,
    "MIX-DUAL-INDEX-MASTER": score_dual_index_master,
}


def score_mix(
    mix_id: str,
    ticket: Any,
    *,
    bars: Optional[list[Any]] = None,
    premium_bars: Optional[list[Any]] = None,
) -> MixScore:
    fn = SCORERS.get(mix_id)
    if fn is None:
        return MixScore(
            mix_id=mix_id,
            available=False,
            lean="HOLD",
            stage="WATCH",
            outcome="DATA_INSUFFICIENT",
            data_gaps=["DATA_INSUFFICIENT: unknown lean MIX id"],
            reasons=[],
            provenance={"NO_PROMOTE": True},
        )
    if mix_id == "MIX-DUAL-INDEX-MASTER":
        return score_dual_index_master(ticket, bars=bars, premium_bars=premium_bars)
    return fn(ticket, bars=bars)


def pick_customer_lean(
    ticket: Any,
    *,
    bars: Optional[list[Any]] = None,
) -> MixScore:
    """First useful gather ticket: PCR hold, else spot+ATM, else 1m impulse.

    003/006 proxies score in the catalog but do not drive the customer ticket.
    """
    pcr = score_pcr_extreme_hold(ticket, bars=bars)
    if pcr.outcome == "HOLD":
        return pcr
    spot = score_lean_spot_atm(ticket, bars=bars)
    if spot.lean in ("BUY_CE", "BUY_PE"):
        return spot
    impulse = score_impulse_1m(ticket, bars=bars)
    if impulse.lean in ("BUY_CE", "BUY_PE"):
        return impulse
    if spot.outcome == "DATA_INSUFFICIENT" and impulse.outcome == "DATA_INSUFFICIENT":
        return MixScore(
            mix_id="MIX-LEAN-SPOT-ATM",
            available=True,
            lean="HOLD",
            stage="WATCH",
            outcome="WATCH",
            data_gaps=list(dict.fromkeys(spot.data_gaps + impulse.data_gaps)),
            reasons=["lean MIX waiting on INDEX 1m + ATM wall"],
            provenance={"NO_PROMOTE": True, "customer_default": False},
        )
    return spot
