"""Parallel PAPER scalper books on INDEX+ATM tape. No live Dhan. No MIX-DEFAULT-BUY write.

Each book_id × underlying has at most one OPEN. Books never veto each other.
Default paper path: do **not** deny a model's CE/PE signal (founder paper). Overlay HOLD
is logged, not a skip. MIX-ML-LOGIT is an INDEX scan book, not the customer default.
Desk capital ₹5.7L on MIX-DEFAULT-BUY (SOD). New fills 20–30 lots (target 25). Skip if capital cannot buy the min. Lot size from instrument master when available. Never 1-lot paper.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from desk_ml.features import Triple, build_feature_rows
from desk_ml.fill_contract import FOLLOWS_CLOCK, OBSERVER_CLOCK, grade_fill
from desk_ml.sod_exam import compact_exam_event
from desk_ml.fit import fit_from_rows, score_features_dict
from desk_ml.inventory import inventory_recon
from desk_ml.model import OVERLAY_HOLD, premium_divergence_pattern
from desk_ml.llm_review import maybe_llm_review, overlay_to_boss
from desk_ml.observer import follow_gap_series_itm_1m, review_fill_intents, review_picker_ticket
from desk_ml.picker import (
    SIGNAL_LOG_MAX,
    SOD_LAB_OBSERVE,
    SOD_ONE_OPEN,
    SOD_PRODUCT_BOOK,
    apply_picker_to_intents,
    collect_analyst_votes,
    greeks_vote_intent,
    picker_majority,
    track_model_signals,
)
from desk_ml.mrr import Z_HOLD, ols_beta, rolling_z
from desk_ml.persist import pack_estimators, repo_root
from desk_ml.paper_lots import (
    STARTING_CAPITAL_INR,
    pnl_inr,
    resolve_lot_size,
    size_lots,
)

DESK_CAPITAL_INR = 570000.0  # prior ₹70k + founder +₹5L (2026-09-18). PAPER.
PAPER_MIN_LOTS = 20
PAPER_TARGET_LOTS = 25
PAPER_MAX_LOTS = 30
DASHBOARD_HEARTBEAT_SECONDS = 2
TICK_NE_DASHBOARD_REASON = (
    "Live mock: dual-tape REST poll default 2s (clamp ≥2). "
    "Dashboard JSON/MD rewrite every 2s from the last tick — not a new Dhan poll. "
    "WS feed parse has LTP/volume/OI, not IV/greeks — MIX-ML-GREEKS stays on POST /optionchain."
)
LIMIT_DISCOUNT_FRAC = 0.012  # working buy limit below signal LTP; fill is not assumed at signal
from desk_ml.groww_costs import as_dict as groww_cost_meta
from desk_ml.groww_costs import breakeven_premium, groww_round_trip_charges, net_pnl_inr
from desk_ml.greeks_ml import score_greeks_ticket, session_iv_median, wing_ivs
from desk_ml.tape import (
    index_1m_close_vol_from_ticks,
    index_1m_ohlcv_from_ticks,
    ist_calendar_date,
    load_dual_tape_triples,
    load_index_closes,
    load_triples,
    minute_key,
)

try:
    from warehouse.feasibility import evaluate_long_premium
except ImportError:  # pragma: no cover
    evaluate_long_premium = None  # type: ignore[assignment]

try:
    from trading_agents_india.desk_divergence import judge_tick
except ImportError:  # pragma: no cover
    judge_tick = None  # type: ignore[assignment]

IST = timezone(timedelta(hours=5, minutes=30))
# Founder lock: data 09:00–15:30; NEW 09:30–15:16; flatten 15:16; ITM premium only. No Sat/Sun.
FLATTEN_MINUTES_IST = 15 * 60 + 16
NO_NEW_MINUTES_IST = 15 * 60 + 16
NO_NEW_BEFORE_MINUTES_IST = 9 * 60 + 30
OPEN_SETTLE_GATE = "NO_NEW_BEFORE_0930"
OPEN_SETTLE_35M = "NO_NEW_BEFORE_0930"
WEEKEND_NO_MARKET = "WEEKEND_NO_MARKET"
NO_NEW_AFTER_1516 = "NO_NEW_AFTER_1516"
FLATTEN_1516 = "FLATTEN_1516"
MAX_TARGET_R = 2.0
MAX_TYPICAL_VS_ENTRY = 0.28
INDEX_LIKE_PREMIUM = 5000.0
PAPER_ADD_LOT = False
TARGET_STEP_MAX = 2
TRAIL_BAND_MIN = 4.0  # premium ₹ after fill; founder ±5–10, scaled by vol
TRAIL_BAND_MAX = 12.0
MIN_STOP_PREMIUM = 8.0  # legacy floor when index profile is off
MIN_STOP_FRAC_ENTRY = 0.06
PAPER_FOCUS_UNDERLYINGS = ("NIFTY", "SENSEX")
INDEX_POINT_PROFILES: dict[str, dict[str, float]] = {
    "NIFTY": {
        "atr_stop_k": 1.2,
        "min_stop": 6.0,
        "max_stop": 18.0,
        "trail_k": 0.9,
        "trail_min": 4.0,
        "trail_max": 10.0,
        "rr_continue": 2.5,
        "rr_trend": 2.0,
        "rr_sr": 1.25,
        "rr_base": 1.5,
        "chop_target_cap": 10.0,
    },
    "SENSEX": {
        "atr_stop_k": 1.7,
        "min_stop": 18.0,
        "max_stop": 42.0,
        "trail_k": 1.45,
        "trail_min": 12.0,
        "trail_max": 28.0,
        "rr_continue": 2.2,
        "rr_trend": 1.8,
        "rr_sr": 1.2,
        "rr_base": 1.4,
    },
}
T1_CONFIRM_SECONDS = 60  # 1m candle confirm before lock/T2
BIN_SIDE_MISMATCH = "BIN_SIDE_MISMATCH"
BIN_LONG_UNWIND = "BIN_LONG_UNWIND"
COVER_LONG_UNWIND = "COVER_LONG_UNWIND"
FILL_AWAY_FRAC = 0.03  # unfilled buy: LTP ran this far above limit
UNFILLED_BARS = 2  # 1m buckets; do not count 10s bar_i
UNFILLED_SECONDS = UNFILLED_BARS * 60
SCALP_HOLD_BARS = 8  # time-exit = hold_bars * 60s wall clock, not 10s ticks
RANGE_LOOKBACK = 20
# INDEX 1m regime (HYPOTHESIS paper overlay). Not option L2. Not a MIX rewrite.
# Window = last 15 1m bars (matches JSONL keep). EMA 21 if n>=21 else EMA 15.
REGIME_LOOKBACK = 15
REGIME_MIN_BARS = 12
REGIME_ER_MAX = 0.30  # Kaufman efficiency |net|/path; at or below → chop
REGIME_FLIP_MIN = 0.38
REGIME_RANGE_ATR_MAX = 4.0  # window high-low / mean |1m close change|
REGIME_RSI_MID_LO = 45.0
REGIME_RSI_MID_HI = 55.0
REGIME_RV_WIDEN = 0.0006  # 1m return stdev → wider paper stop, cap target
# Last-3 1m impulse can TREND even when the 15m ER is lunch-chop. HYPOTHESIS.
LAST3_IMPULSE_ER = 0.55
LAST3_IMPULSE_FRAC = 0.00025  # ~6 NIFTY pts at 24k; scales for BN/SENSEX
CANDLE_WICK_REJECT = 2.0  # wick vs body → shooting star / hammer
CANDLE_DOJI_BODY = 0.22
CANDLE_STRONG_BODY = 0.50
SR_NEAR_FRAC = 0.0008  # ~0.08% (~20 NIFTY / ~60 SENSEX pts)
VOL_BAR_VS_MEDIAN = 1.05
SIDEWAYS_HOLD = "SIDEWAYS_HOLD"
REGIME_UNKNOWN_WAIT = "REGIME_UNKNOWN_WAIT"
VOL_NOT_EXPANDING = "VOL_NOT_EXPANDING"
CANCEL_BIN_ROLL = "CANCEL_BIN_ROLL"
CANCEL_STALL = "CANCEL_STALL"
CANCEL_NO_PROGRESS = "CANCEL_NO_PROGRESS"
CANCEL_BOOK_NEAR = "CANCEL_BOOK_NEAR"
CANCEL_AGAINST = "CANCEL_AGAINST"
HUMAN_EXIT = "HUMAN_EXIT"
CANCEL_HUMAN = "CANCEL_HUMAN"
HUMAN_OVERRIDE_NAME = "human_trade_override.json"
SOFT_CANCEL_REASONS = {
    CANCEL_BIN_ROLL,
    "CANCEL_STRIKE_ROLL",
    "CANCEL_SIDEWAYS",
}
HARD_EXIT_REASONS = {
    "STOP",
    "TIME",
    "FLATTEN_1500",
    "FLATTEN_1516",
    "FLATTEN_1515",
    "CANCEL_ADVERSE",
    COVER_LONG_UNWIND,
    CANCEL_STALL,
    CANCEL_NO_PROGRESS,
    CANCEL_BOOK_NEAR,
    CANCEL_AGAINST,
    HUMAN_EXIT,
    CANCEL_HUMAN,
}
# Stale-high stall (HYPOTHESIS): not a constant 9m TIME clock.
STALL_MIN_SEC = 20 * 60
STALL_HIGH_STALE_SEC = 8 * 60
STALL_MIN_SEC_CHOP = 8 * 60
STALL_HIGH_STALE_CHOP = 3 * 60
STALL_ER_MAX = 0.18
STALL_TREND_ER = 0.35
STALL_TARGET_PROGRESS = 0.55
STALL_CHOP_PROGRESS = 0.40
# Filled MIX-DEFAULT-BUY booking overlay (SOD desk). Causal closed 1m only.
EXIT_NO_PROG_BARS = 3
EXIT_NO_PROG_MFE = 2.0
EXIT_BOOK_NEAR_FRAC = 0.70
STALL_LOOKBACK = 15
TIME_HARD_SEC = 45 * 60
PREMIUM_PRINT_CAP = 24
BIN_VOL_EXPAND = 1.15
BIN_MIN_VOTES = 2  # two ITM-leg confirms — do not wait three INDEX 1m bars
BIN_KEEP_TICKS = 36
STOP_FRAC = 0.40
TARGET_FRAC = 0.55
STRIKE_STEP = {"NIFTY": 50.0, "BANKNIFTY": 100.0, "SENSEX": 100.0}
# Founder: ITM only. NIFTY 23500 → 23300 CE / 23700 PE (200pt). BN/SX 3×100.
ITM_POINTS = {"NIFTY": 200.0, "BANKNIFTY": 300.0, "SENSEX": 300.0}
ITM_STEPS_MIN = 3
GIVE_UP_FRAC = 0.12  # cancel if same-side premium dumps this far below entry

LIVE_BOOKS = (
    "MIX-DEFAULT-BUY",
    "ML-001",
    "ML-002",
    "ML-1",
    "MIX-ML-LOGIT",
    "MIX-ML-LOGIT-XR",
    "MIX-TV-EP-024",
    "MIX-ML-GREEKS",
)
ML_BOOK_IDS = (
    "ML-001",
    "ML-002",
    "ML-1",
    "MIX-ML-LOGIT",
    "MIX-ML-LOGIT-XR",
    "MIX-ML-GREEKS",
)
# Books that may FILL. Observe-only books stay on the board with n_open 0.
FILL_ELIGIBLE_BOOKS = (
    "MIX-DEFAULT-BUY",
    "MIX-ML-LOGIT",
    "MIX-ML-LOGIT-XR",
    "MIX-ML-GREEKS",
)
OBSERVE_ONLY_BOOKS = (
    "ML-001",
    "ML-002",
    "ML-1",
    "MIX-TV-EP-024",
)
# Desk "earned" uses unique fill books (not KMeans/TV clones).
UNIQUE_PNL_BOOKS = (
    "MIX-DEFAULT-BUY",
    "MIX-ML-LOGIT",
    "MIX-ML-LOGIT-XR",
    "MIX-ML-GREEKS",
)

TV_EP_KEEP_ALL = tuple(f"MIX-TV-EP-{i:03d}" for i in range(1, 26))
TV_EP_SHORTLIST = ("MIX-TV-EP-018", "MIX-TV-EP-010", "MIX-TV-EP-009")

STOP_FLAG_NAME = "ml_paper_scalp_STOPPED.flag"
DASH_JSON_NAME = "ml_paper_dashboard.json"
LOG_JSONL_NAME = "ml_paper_model_logs.jsonl"
PAPER_PARAMS_NAME = "ml_paper_session_params.json"
MISTAKES_NAME = "ml_paper_mistakes.jsonl"
FIX_FIRST_SINCE_IST = "2026-09-17"
FIX_FIRST_PROGRESS_NAME = "fix_first_progress.json"
FIX_FIRST_SKILL_BOOK = "MIX-DEFAULT-BUY"
DASH_MD_REL = Path("teams") / "06_backtesting" / "docs" / "ML_PAPER_DASHBOARD.md"
MOCK_JSON_REL = Path("apps") / "web" / "public" / "mock" / "ml_paper_dashboard.json"
DEFAULT_PAPER_PARAMS = {
    "stop_frac": STOP_FRAC,
    "target_frac": TARGET_FRAC,
    "scalp_hold_bars": SCALP_HOLD_BARS,
    "give_up_frac": GIVE_UP_FRAC,
    "skip_sideways": True,
    "skip_trend_against": True,
    "limit_discount_frac": LIMIT_DISCOUNT_FRAC,
    "desk_capital_inr": DESK_CAPITAL_INR,
    "paper_min_lots": PAPER_MIN_LOTS,
    "paper_target_lots": PAPER_TARGET_LOTS,
    "paper_max_lots": PAPER_MAX_LOTS,
    "dashboard_heartbeat_seconds": DASHBOARD_HEARTBEAT_SECONDS,
    "regime_lookback": REGIME_LOOKBACK,
    "regime_er_max": REGIME_ER_MAX,
    "regime_flip_min": REGIME_FLIP_MIN,
    "regime_range_atr_max": REGIME_RANGE_ATR_MAX,
    "paper_add_lot": PAPER_ADD_LOT,
    "max_target_r": MAX_TARGET_R,
    "open_settle_gate": OPEN_SETTLE_GATE,
    "paper_book_epoch_ts": None,
    "production_params_written": False,
    "trail_band_min": TRAIL_BAND_MIN,
    "trail_band_max": TRAIL_BAND_MAX,
    "target_step_max": TARGET_STEP_MAX,
    "min_stop_premium": MIN_STOP_PREMIUM,
    "t1_confirm_seconds": T1_CONFIRM_SECONDS,
    "note": "PAPER session only. Never writes MIX-DEFAULT-BUY.",
    "skip_banknifty": False,
    "skip_sensex": False,
    "nifty_need_strength": True,
    "nifty_allow_sides": ["CE", "PE"],
    "nifty_align_impulse": True,
    "nifty_skip_ce_after_stop": True,
    "nifty_skip_side_after_stop": False,
    "nifty_max_filled_per_book": None,
    "apply_target_shift": False,
    "observer_veto_fills": True,
    "sod_one_ticket": True,
    "picker_majority": True,
    "nifty_cover_closed_1m": True,
}


# Same strength overlay on both wings. Founder: do not lock PE all session.
OVERLAY_SHIP = {
    "skip_banknifty": False,
    "skip_sensex": False,
    "nifty_need_strength": True,
    "nifty_allow_sides": ["CE", "PE"],
    "nifty_align_impulse": True,
    "nifty_skip_ce_after_stop": True,
    "nifty_skip_side_after_stop": False,
    "nifty_max_filled_per_book": None,
    "apply_target_shift": False,
}


def _ist_dt(ts: int) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=IST)


def minutes_ist(ts: int) -> int:
    dt = _ist_dt(ts)
    return dt.hour * 60 + dt.minute


def new_paper_blocked(ts: int) -> Optional[str]:
    """Mon–Fri 09:30–15:16 IST only. No Sat/Sun. Flatten/cancel callers must not use this."""
    dt = _ist_dt(ts)
    if dt.weekday() >= 5:
        return WEEKEND_NO_MARKET
    mins = minutes_ist(ts)
    if mins < NO_NEW_BEFORE_MINUTES_IST:
        return OPEN_SETTLE_GATE
    if mins >= NO_NEW_MINUTES_IST:
        return NO_NEW_AFTER_1516
    return None


def paper_open_justification(
    *,
    underlying: str,
    side: str,
    classified: dict[str, Any],
    levels: dict[str, Any],
    strike: Optional[float],
    strike_source: str,
    engine: "BookEngine",
) -> str:
    """Plain-language why this PAPER ticket exists. Not a live order."""
    und = str(underlying).upper()
    bin_side = ((classified.get("itm_bin") or {}) if isinstance(classified.get("itm_bin"), dict) else {}).get("side")
    regime = classified.get("regime") or "UNKNOWN"
    direction = classified.get("direction") or "UNKNOWN"
    impulse = classified.get("last3_impulse") or "none"
    pause = classified.get("last3_reason") or ""
    stop = levels.get("stop")
    target = levels.get("target")
    bits = [
        f"{und} buy {side} ITM strike {strike} ({strike_source})",
        f"bin={bin_side or 'n/a'} regime={regime}/{direction} last3={impulse}",
    ]
    if pause:
        bits.append(f"impulse_note={pause}")
    bits.append(f"path stop {stop} → target {target} (premium points; strict first TARGET; T2 parked)")
    if und == "NIFTY":
        allow = list(getattr(engine, "nifty_allow_sides", None) or [])
        if allow == ["PE"]:
            bits.append("overlay=PE+strength")
        elif set(allow) >= {"CE", "PE"} or not allow:
            bits.append("overlay=CE+PE+strength")
        else:
            bits.append("overlay=NIFTY-gates")
        if getattr(engine, "nifty_need_strength", False):
            bits.append(
                "need_strength: last-3 / pause_continue / SHORT_COVER / itm_bin confirm / TREND ER≥0.35 same wing"
            )
        cap = getattr(engine, "nifty_max_filled_per_book", None)
        if cap:
            bits.append(f"session cap {cap} filled/book")
        if side == "PE":
            bits.append("why_now=PE: dump / PE bin / PE short-cover (CE still allowed when CE strength prints)")
        elif side == "CE":
            bits.append("why_now=CE: rally / CE bin / CE short-cover (not PE-locked)")
    if und == "SENSEX" and getattr(engine, "skip_sensex", False):
        bits.append("SENSEX NEW skipped on this ship (FOCUS_NIFTY_ONLY)")
    if regime == "SIDEWAYS":
        bits.append("SIDEWAYS: new opens should have been skipped — if open, it is a hold/flatten path")
    bits.append("PAPER only. NO_PROMOTE. Groww+STT on fill.")
    return "; ".join(bits)


def paper_close_result(*, unfilled: bool, reason: str, won: bool) -> str:
    """SUCCESS = first TARGET printed. TIME green ≠ SUCCESS. Money wr still uses won."""
    if unfilled:
        return "CANCELLED"
    if str(reason) == "TARGET" and won:
        return "SUCCESS"
    if not won:
        return "LOSS"
    if str(reason) in {"FLATTEN_1516", "FLATTEN_1515", "FLATTEN_1500"}:
        return "FLATTEN"
    if str(reason) in {CANCEL_STALL, CANCEL_NO_PROGRESS, CANCEL_BOOK_NEAR}:
        return "STALL"
    if str(reason) == CANCEL_AGAINST:
        return "AGAINST"
    return "TIME"


def _row_filled(row: dict[str, Any]) -> bool:
    if row.get("filled") is False:
        return False
    if row.get("filled") is True:
        return True
    return str(row.get("result") or "") in {"SUCCESS", "LOSS", "TIME", "FLATTEN", "STALL", "AGAINST"}


def paper_close_justification(
    *,
    open_why: str,
    reason: str,
    result: str,
    status: str,
    unfilled: bool,
    inr: Optional[float],
    sl_hit: bool,
    target_hit: bool = False,
    exit_px: Optional[float] = None,
    target_px: Optional[float] = None,
) -> str:
    """Why this PAPER ticket ended (SUCCESS=TARGET / TIME / LOSS / CANCEL)."""
    if unfilled:
        money = "₹0 unfilled — no Groww+STT"
    elif inr is None:
        money = "net ₹n/a"
    else:
        money = f"net ₹{round(float(inr), 2)}"
    bits = [
        f"EXIT {reason}",
        f"result={result}",
        f"status={status}",
        f"P/L {money}",
    ]
    if sl_hit:
        bits.append("SL hit")
    if unfilled:
        bits.append("working limit never filled")
    elif str(reason).startswith("CANCEL"):
        bits.append("filled cancel still books round-trip Groww+STT")
    elif reason == "TARGET":
        bits.append("strict first TARGET booked; T2 parked")
    elif reason == "STOP":
        bits.append("path stop hit before target")
    elif reason == "TIME":
        bits.append("hold clock expired — not a TARGET hit; SUCCESS is TARGET only")
        if exit_px is not None and target_px is not None:
            bits.append(f"exit {round(float(exit_px), 4)} vs target {round(float(target_px), 4)}")
    elif reason == CANCEL_STALL:
        bits.append(
            "stale premium high + low Kaufman ER + no last-3 continuation — "
            "book chop, do not wait a constant TIME clock"
        )
        if exit_px is not None and target_px is not None:
            bits.append(f"exit {round(float(exit_px), 4)} vs target {round(float(target_px), 4)}")
    elif reason == CANCEL_NO_PROGRESS:
        bits.append(
            f"exit overlay: {EXIT_NO_PROG_BARS} closed 1m with MFE < {EXIT_NO_PROG_MFE} pts — "
            "flatten dead fill; do not sit to AGAINST"
        )
    elif reason == CANCEL_BOOK_NEAR:
        bits.append(
            f"exit overlay: running MFE ≥ {EXIT_BOOK_NEAR_FRAC:.0%} of target span and "
            "closed 1m reversed — book; do not wait for TARGET or AGAINST"
        )
    elif reason in {"FLATTEN_1516", "FLATTEN_1515", "FLATTEN_1500"}:
        bits.append("session flatten — leftover OPEN at 15:16 IST")
    if target_hit:
        bits.append("target_hit=true")
    elif not unfilled:
        bits.append("target_hit=false")
    why = (open_why or "").strip()
    close = "CLOSE: " + "; ".join(bits)
    return f"{why} | {close}" if why else close


def agent_ticket_status(pos: "OpenPaper") -> str:
    if pos.cancel_eligible:
        return "CANCEL_ELIGIBLE"
    if not pos.filled:
        return "WORKING_LIMIT"
    if pos.target_step >= 1:
        return f"TARGET_STEP_{min(int(pos.target_step), 3)}"
    if pos.trail_step >= 1:
        return "TRAIL_STOP"
    return "IN_TRADE"


def _ema_last(values: Sequence[float], length: int) -> Optional[float]:
    vals = [float(x) for x in values]
    if length <= 0 or len(vals) < length:
        return None
    k = 2.0 / (length + 1)
    prev = sum(vals[:length]) / length
    for v in vals[length:]:
        prev = v * k + prev * (1.0 - k)
    return float(prev)


def _rsi_last(closes: Sequence[float], period: int = 14) -> Optional[float]:
    vals = [float(x) for x in closes]
    n = len(vals)
    if n < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        d = vals[i] - vals[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    avg_g = gains / period
    avg_l = losses / period
    for i in range(period + 1, n):
        d = vals[i] - vals[i - 1]
        g = d if d > 0 else 0.0
        l = -d if d < 0 else 0.0
        avg_g = (avg_g * (period - 1) + g) / period
        avg_l = (avg_l * (period - 1) + l) / period
    if avg_l == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_g / avg_l)


def _vwap_window(
    closes: Sequence[float], volumes: Optional[Sequence[Optional[float]]]
) -> tuple[Optional[float], str]:
    vals = [float(x) for x in closes]
    vols = list(volumes) if volumes is not None else [None] * len(vals)
    if len(vols) < len(vals):
        vols = vols + [None] * (len(vals) - len(vols))
    num = 0.0
    den = 0.0
    used_vol = False
    for c, v in zip(vals, vols):
        w = 1.0
        if v is not None:
            try:
                fv = float(v)
            except (TypeError, ValueError):
                fv = 0.0
            if fv > 0:
                w = fv
                used_vol = True
        num += c * w
        den += w
    if den <= 0:
        return None, "DATA_INSUFFICIENT"
    return num / den, ("OK" if used_vol else "EQUAL_WEIGHT_PROJECT")


def _vol_last3(volumes: Optional[Sequence[Optional[float]]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "status": "DATA_INSUFFICIENT",
        "expand": None,
        "last3_sum": None,
        "prev3_sum": None,
    }
    if not volumes:
        return out

    def _pos(raw: Optional[float]) -> Optional[float]:
        if raw is None:
            return None
        try:
            v = float(raw)
        except (TypeError, ValueError):
            return None
        return v if v > 0 else None

    last3 = [_pos(v) for v in list(volumes)[-3:]]
    if len(last3) < 3 or any(v is None for v in last3):
        return out
    last_sum = float(sum(float(v) for v in last3 if v is not None))
    out["last3_sum"] = round(last_sum, 4)
    prev_raw = list(volumes)[-6:-3] if len(list(volumes)) >= 6 else []
    prev3 = [_pos(v) for v in prev_raw]
    if len(prev3) == 3 and all(v is not None for v in prev3):
        prev_sum = float(sum(float(v) for v in prev3 if v is not None))
        out["prev3_sum"] = round(prev_sum, 4)
        out["status"] = "OK"
        out["expand"] = last_sum >= prev_sum * 1.05 if prev_sum > 0 else None
        return out
    out["status"] = "PARTIAL"
    return out


def _last3_impulse(window: Sequence[float]) -> dict[str, Any]:
    """PUT/CE strength on the last three 1m candles (close now vs close 3m ago).

    Uses four closes when present so three candle *bodies* count (a ~100pt SENSEX
    dump is three 1m bars, not the last two diffs). Volume is not used here.
    """
    out: dict[str, Any] = {
        "last3_closes": None,
        "last3_er": None,
        "last3_net": None,
        "last3_impulse": None,
        "last3_reason": "short_last3",
    }
    if len(window) < 3:
        return out
    last3 = [float(x) for x in window[-3:]]
    out["last3_closes"] = [round(x, 4) for x in last3]
    path_closes = [float(x) for x in window[-4:]] if len(window) >= 4 else last3
    diffs = [path_closes[i] - path_closes[i - 1] for i in range(1, len(path_closes))]
    path = sum(abs(d) for d in diffs)
    net = path_closes[-1] - path_closes[0]
    er = (abs(net) / path) if path > 1e-9 else 0.0
    out["last3_er"] = round(er, 4)
    out["last3_net"] = round(net, 4)
    last = path_closes[-1]
    if last <= 1e-9:
        out["last3_reason"] = "bad_last_close"
        return out
    if er < float(LAST3_IMPULSE_ER):
        out["last3_reason"] = "last3_not_efficient"
        return out
    if abs(net) < abs(last) * float(LAST3_IMPULSE_FRAC):
        out["last3_reason"] = "last3_move_too_small"
        return out
    if net < 0:
        out["last3_impulse"] = "DOWN"
        out["last3_reason"] = "last3_impulse_put"
    else:
        out["last3_impulse"] = "UP"
        out["last3_reason"] = "last3_impulse_call"
    return out


def _ohlc_from_closes(closes: Sequence[float]) -> list[dict[str, Any]]:
    """Close-to-close synthetic 1m bars. No wick beyond the two prints."""
    out: list[dict[str, Any]] = []
    prev: Optional[float] = None
    for raw in closes:
        c = float(raw)
        o = float(prev) if prev is not None else c
        out.append({"open": o, "high": max(o, c), "low": min(o, c), "close": c})
        prev = c
    return out


def candle_shape(
    bar: Optional[dict[str, Any]],
    *,
    prior_range: Optional[float] = None,
) -> dict[str, Any]:
    """Price-action flags. Proxy POC = typical (H+L+C)/3 — not order-flow volume profile."""
    empty = {
        "shape": "DATA_INSUFFICIENT",
        "shooting_star": False,
        "hammer": False,
        "doji": False,
        "injection": False,
        "strong_up": False,
        "strong_down": False,
        "proxy_poc": None,
        "close_vs_poc": None,
        "body_frac": None,
    }
    if not bar:
        return empty
    try:
        o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
    except (KeyError, TypeError, ValueError):
        return empty
    rng = h - l
    if rng <= 1e-9:
        return {**empty, "shape": "flat", "proxy_poc": round(c, 4), "close_vs_poc": 0.0, "body_frac": 0.0}
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    typical = (h + l + c) / 3.0
    body_frac = body / rng
    doji = body_frac < float(CANDLE_DOJI_BODY)
    shooting = upper >= float(CANDLE_WICK_REJECT) * max(body, rng * 0.05) and (max(o, c) - l) / rng <= 0.45
    hammer = lower >= float(CANDLE_WICK_REJECT) * max(body, rng * 0.05) and (h - min(o, c)) / rng <= 0.45
    injection = False
    if prior_range is not None and float(prior_range) > 1e-9:
        injection = rng >= 2.2 * float(prior_range) and body_frac < 0.28
    strong_up = c > o and body_frac >= float(CANDLE_STRONG_BODY) and not shooting
    strong_down = c < o and body_frac >= float(CANDLE_STRONG_BODY) and not hammer
    shape = "strong_up" if strong_up else ("strong_down" if strong_down else None)
    if injection:
        shape = "injection"
    elif shooting:
        shape = "shooting_star"
    elif hammer:
        shape = "hammer"
    elif doji:
        shape = "doji"
    elif shape is None:
        shape = "mixed"
    return {
        "shape": shape,
        "shooting_star": shooting,
        "hammer": hammer,
        "doji": doji,
        "injection": injection,
        "strong_up": strong_up,
        "strong_down": strong_down,
        "proxy_poc": round(typical, 4),
        "close_vs_poc": round(c - typical, 4),
        "body_frac": round(body_frac, 4),
    }


def volume_confirms_impulse(
    volumes: Optional[Sequence[Optional[float]]],
    vol_expand: Optional[bool],
) -> tuple[bool, str]:
    """Real 1m volume vs prior. Missing volume never invents strength."""
    if vol_expand is True:
        return True, "vol_expand"
    vals: list[float] = []
    for raw in list(volumes or []):
        try:
            v = float(raw) if raw is not None else 0.0
        except (TypeError, ValueError):
            continue
        if v > 0:
            vals.append(v)
    if len(vals) < 4:
        return False, "vol_missing"
    last = vals[-1]
    prior = vals[-11:-1] if len(vals) > 4 else vals[:-1]
    if not prior:
        return False, "vol_no_baseline"
    ordered = sorted(prior)
    med = ordered[len(ordered) // 2]
    if med > 0 and last + 1e-9 >= float(VOL_BAR_VS_MEDIAN) * med:
        return True, "vol_vs_median"
    if vol_expand is False:
        return False, "vol_shrinking"
    return False, "vol_weak"


def option_confirms_impulse(direction: str, opt: Optional[dict[str, Any]]) -> tuple[Optional[bool], str]:
    """ITM/ATM premium confirm. Missing prints → None (do not invent)."""
    if not opt:
        return None, "opt_missing"
    ce = opt.get("itm_ce_chg") if opt.get("itm_ce_chg") is not None else opt.get("ce_chg")
    pe = opt.get("itm_pe_chg") if opt.get("itm_pe_chg") is not None else opt.get("pe_chg")
    try:
        ce_f = float(ce) if ce is not None else None
        pe_f = float(pe) if pe is not None else None
    except (TypeError, ValueError):
        return None, "opt_missing"
    if ce_f is None or pe_f is None:
        return None, "opt_missing"
    if direction == "UP":
        if ce_f > 0 and pe_f <= 0:
            return True, "opt_ce_confirms"
        if pe_f > 0 and ce_f < 0:
            return False, "opt_pe_absorbing"
        return None, "opt_mixed"
    if pe_f > 0 and ce_f <= 0:
        return True, "opt_pe_confirms"
    if ce_f > 0 and pe_f < 0:
        return False, "opt_ce_absorbing"
    return None, "opt_mixed"


def nearest_sr(px: float, sr: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Closest PDH/PDL / session H/L / HTF swing. Close-proxy levels, not L2."""
    out: dict[str, Any] = {"near": False, "name": None, "px": None, "kind": None, "dist_frac": None}
    if not sr or px <= 1e-9:
        return out
    levels: list[tuple[str, str, float]] = []
    for name, kind in (
        ("pdh", "R"),
        ("pdl", "S"),
        ("session_high", "R"),
        ("session_low", "S"),
    ):
        raw = sr.get(name)
        if raw is None:
            continue
        try:
            levels.append((name, kind, float(raw)))
        except (TypeError, ValueError):
            continue
    for sw in sr.get("swings") or []:
        if not isinstance(sw, dict) or sw.get("px") is None:
            continue
        try:
            levels.append(
                (
                    f"{sw.get('tf') or 'htf'}_{sw.get('kind') or ''}",
                    str(sw.get("kind") or ""),
                    float(sw["px"]),
                )
            )
        except (TypeError, ValueError):
            continue
    if not levels:
        return out
    name, kind, lvl = min(levels, key=lambda row: abs(px - row[2]))
    dist = abs(px - lvl) / px
    out["name"] = name
    out["kind"] = kind
    out["px"] = round(lvl, 4)
    out["dist_frac"] = round(dist, 6)
    out["near"] = dist <= float(SR_NEAR_FRAC)
    return out


def confirm_last3_impulse(
    *,
    impulse_dir: Optional[str],
    last_bar: Optional[dict[str, Any]],
    prior_range: Optional[float],
    volumes: Optional[Sequence[Optional[float]]],
    vol_expand: Optional[bool],
    sr: Optional[dict[str, Any]] = None,
    opt_confirm: Optional[dict[str, Any]] = None,
    greeks: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Last-3 dump/rally may override the ITM bin only after strength confirms. PAPER."""
    pack = candle_shape(last_bar, prior_range=prior_range)
    vol_ok, vol_why = volume_confirms_impulse(volumes, vol_expand)
    opt_ok, opt_why = option_confirms_impulse(str(impulse_dir or ""), opt_confirm)
    close = float((last_bar or {}).get("close") or 0.0) if last_bar else 0.0
    sr_hit = nearest_sr(close, sr) if close > 0 else {"near": False}
    greeks = greeks or {}
    trap: Optional[str] = None
    if impulse_dir not in {"UP", "DOWN"}:
        trap = "no_raw_impulse"
    elif not vol_ok:
        trap = vol_why
    elif pack.get("injection") or pack.get("doji"):
        trap = str(pack.get("shape") or "weak_candle")
    elif impulse_dir == "UP" and (
        pack.get("shooting_star") or not (pack.get("strong_up") or (pack.get("close_vs_poc") or 0) >= 0)
    ):
        trap = "up_rejection_or_below_poc"
    elif impulse_dir == "DOWN" and (
        pack.get("hammer") or not (pack.get("strong_down") or (pack.get("close_vs_poc") or 0) <= 0)
    ):
        trap = "down_absorption_or_above_poc"
    elif opt_ok is False:
        trap = opt_why
    elif sr_hit.get("near"):
        if impulse_dir == "UP" and sr_hit.get("kind") == "R" and close + 1e-9 < float(sr_hit.get("px") or close):
            trap = f"false_break_up_{sr_hit.get('name')}"
        elif impulse_dir == "DOWN" and sr_hit.get("kind") == "S" and close + 1e-9 > float(sr_hit.get("px") or close):
            trap = f"false_break_down_{sr_hit.get('name')}"
    if trap is None:
        try:
            ce_d = greeks.get("ce_delta")
            pe_d = greeks.get("pe_delta")
            if ce_d is not None and pe_d is not None:
                if impulse_dir == "UP" and abs(float(pe_d)) > abs(float(ce_d)) + 0.08:
                    trap = "greeks_pe_delta_against"
                elif impulse_dir == "DOWN" and abs(float(ce_d)) > abs(float(pe_d)) + 0.08:
                    trap = "greeks_ce_delta_against"
        except (TypeError, ValueError):
            pass
    return {
        "ok": trap is None,
        "trap": trap,
        "vol_why": vol_why,
        "opt_why": opt_why,
        "candle": pack,
        "sr": sr_hit,
        "note": "Confirmed last-3 may override ITM bin. Unconfirmed waits for bin strength. NO_PROMOTE.",
    }


IMPULSE_PAUSE_MAX_BARS = 4  # 1m bars after first spike; not a 3-vs-5 guess


def apply_impulse_pause_continue(
    engine: "BookEngine",
    und: str,
    classified: dict[str, Any],
    ts: int,
) -> dict[str, Any]:
    """Do not buy the first 3-bar spike. Wait a pause, then volume continuation. PAPER."""
    out = dict(classified)
    raw = out.get("last3_impulse_raw")
    first_ok = bool(out.get("last3_confirmed"))
    # First print never overrides the bin — founder trap / sweep.
    out["last3_impulse"] = None
    out["last3_confirmed"] = False
    pending = dict(engine.impulse_pending.get(und) or {})
    mk = minute_key(int(ts))

    if raw in {"UP", "DOWN"} and pending.get("dir") not in {None, raw}:
        pending = {}

    if raw in {"UP", "DOWN"}:
        if pending.get("dir") != raw:
            engine.impulse_pending[und] = {
                "dir": raw,
                "armed_min": mk,
                "last_min": mk,
                "pause_seen": False,
                "bars": 0,
                "net": out.get("last3_net"),
            }
            out["last3_reason"] = "wait_pause_after_impulse"
            out["last3_trap"] = out.get("last3_trap") or "wait_pause"
            return out
        if mk != pending.get("last_min"):
            pending["bars"] = int(pending.get("bars") or 0) + 1
            pending["last_min"] = mk
        if pending.get("pause_seen") and first_ok:
            out["last3_impulse"] = raw
            out["last3_confirmed"] = True
            out["last3_reason"] = "pause_continue"
            out["last3_trap"] = None
            if out.get("regime") in {"SIDEWAYS", "UNKNOWN"}:
                out["regime"] = "TREND"
                out["direction"] = raw
            engine.impulse_pending.pop(und, None)
            return out
        engine.impulse_pending[und] = pending
        out["last3_reason"] = "wait_pause_after_impulse"
        return out

    if not pending.get("dir"):
        return out
    if mk != pending.get("last_min"):
        pending["bars"] = int(pending.get("bars") or 0) + 1
        pending["last_min"] = mk
    if int(pending.get("bars") or 0) > int(IMPULSE_PAUSE_MAX_BARS):
        engine.impulse_pending.pop(und, None)
        out["last3_reason"] = "pause_expired"
        return out
    shape = str(out.get("candle_shape") or "")
    if shape in {"doji", "mixed", "flat", "hammer", "shooting_star"} or str(out.get("regime") or "") == "SIDEWAYS":
        pending["pause_seen"] = True
    engine.impulse_pending[und] = pending
    out["last3_reason"] = "pause_wait_continuation"
    return out


def _htf_swings(closes_by_ts: dict[int, float], step_minutes: int, *, tf_name: str) -> list[dict[str, Any]]:
    buckets: dict[int, list[float]] = {}
    order: list[int] = []
    for ts, px in sorted((int(k), float(v)) for k, v in closes_by_ts.items()):
        dt = _ist_dt(ts)
        total = dt.hour * 60 + dt.minute
        floored = total - (total % int(step_minutes))
        key = int(
            datetime(dt.year, dt.month, dt.day, floored // 60, floored % 60, tzinfo=IST).timestamp()
        )
        if key not in buckets:
            order.append(key)
            buckets[key] = [px, px]
        else:
            buckets[key][0] = max(buckets[key][0], px)
            buckets[key][1] = min(buckets[key][1], px)
    swings: list[dict[str, Any]] = []
    for i in range(1, len(order) - 1):
        hi, lo = buckets[order[i]]
        phi, _plo = buckets[order[i - 1]]
        nhi, _nlo = buckets[order[i + 1]]
        if hi >= phi and hi >= nhi:
            swings.append({"tf": tf_name, "kind": "R", "px": round(hi, 4)})
        if lo <= buckets[order[i - 1]][1] and lo <= buckets[order[i + 1]][1]:
            swings.append({"tf": tf_name, "kind": "S", "px": round(lo, 4)})
    return swings[-8:]


def build_sr_levels(
    closes_by_ts: dict[int, float],
    *,
    session_ist_date: str,
) -> dict[str, Any]:
    """Premarket PDH/PDL + HTF swings from INDEX closes. Today H/L filled as session prints arrive."""
    by_day: dict[str, list[float]] = {}
    for ts, px in closes_by_ts.items():
        by_day.setdefault(ist_calendar_date(int(ts)), []).append(float(px))
    days = sorted(by_day)
    prev = None
    for d in days:
        if d < session_ist_date:
            prev = d
    pdh = pdl = pdc = None
    if prev and by_day.get(prev):
        rows = by_day[prev]
        pdh, pdl, pdc = max(rows), min(rows), rows[-1]
    today = by_day.get(session_ist_date) or []
    swings: list[dict[str, Any]] = []
    for step, name in ((15, "15m"), (30, "30m"), (60, "60m")):
        swings.extend(_htf_swings(closes_by_ts, step, tf_name=name))
    daily_hl = [(d, max(v), min(v)) for d, v in by_day.items() if v]
    daily_hl.sort(key=lambda row: row[0])
    if len(daily_hl) >= 3:
        for i in range(1, len(daily_hl) - 1):
            _d, hi, lo = daily_hl[i]
            _pd, phi, plo = daily_hl[i - 1]
            _nd, nhi, nlo = daily_hl[i + 1]
            if hi >= phi and hi >= nhi:
                swings.append({"tf": "1d", "kind": "R", "px": round(hi, 4)})
            if lo <= plo and lo <= nlo:
                swings.append({"tf": "1d", "kind": "S", "px": round(lo, 4)})
    weeks: dict[tuple[int, int], list[float]] = {}
    for ts, px in closes_by_ts.items():
        iso = _ist_dt(int(ts)).isocalendar()
        weeks.setdefault((int(iso[0]), int(iso[1])), []).append(float(px))
    week_rows = sorted((k, max(v), min(v)) for k, v in weeks.items() if v)
    if len(week_rows) >= 3:
        for i in range(1, len(week_rows) - 1):
            _k, hi, lo = week_rows[i]
            _pk, phi, plo = week_rows[i - 1]
            _nk, nhi, nlo = week_rows[i + 1]
            if hi >= phi and hi >= nhi:
                swings.append({"tf": "1w", "kind": "R", "px": round(hi, 4)})
            if lo <= plo and lo <= nlo:
                swings.append({"tf": "1w", "kind": "S", "px": round(lo, 4)})
    return {
        "layer": "HYPOTHESIS",
        "session_ist_date": session_ist_date,
        "prior_session": prev,
        "pdh": round(float(pdh), 4) if pdh is not None else None,
        "pdl": round(float(pdl), 4) if pdl is not None else None,
        "pdc": round(float(pdc), 4) if pdc is not None else None,
        "session_high": round(max(today), 4) if today else None,
        "session_low": round(min(today), 4) if today else None,
        "swings": swings[-24:],
        "note": "PDH/PDL from INDEX 1m closes (true high/low DATA_INSUFFICIENT if only LTP). NO_PROMOTE.",
    }


def _realized_vol(closes: Sequence[float]) -> Optional[float]:
    vals = [float(x) for x in closes]
    if len(vals) < 4:
        return None
    rets: list[float] = []
    for i in range(1, len(vals)):
        if abs(vals[i - 1]) < 1e-9:
            continue
        rets.append((vals[i] - vals[i - 1]) / abs(vals[i - 1]))
    if len(rets) < 3:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return var ** 0.5


def classify_index_regime(
    closes: Sequence[float],
    *,
    volumes: Optional[Sequence[Optional[float]]] = None,
    lookback: int = REGIME_LOOKBACK,
    er_max: float = REGIME_ER_MAX,
    flip_min: float = REGIME_FLIP_MIN,
    range_atr_max: float = REGIME_RANGE_ATR_MAX,
    greeks: Optional[dict[str, Any]] = None,
    ohlc: Optional[Sequence[dict[str, Any]]] = None,
    sr: Optional[dict[str, Any]] = None,
    opt_confirm: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """TREND | SIDEWAYS | UNKNOWN. Kaufman ER + VWAP + EMA 15/21 + last-3 vol + RSI + greeks.

    HYPOTHESIS overlay. Missing volume/greeks → DATA_INSUFFICIENT votes, never invented.
    """
    vals = [float(x) for x in closes if x is not None]
    n = len(vals)
    base = {
        "regime": "UNKNOWN",
        "direction": "UNKNOWN",
        "layer": "HYPOTHESIS",
        "n": n,
        "lookback": int(lookback),
        "er": None,
        "flip_frac": None,
        "range_over_atr": None,
        "net_signed": None,
        "vwap": None,
        "ema": None,
        "ema_len": None,
        "rsi": None,
        "vol_expand": None,
        "realized_vol": None,
        "reason": "short_index_path",
    }
    if n < REGIME_MIN_BARS:
        return base
    win_n = max(REGIME_MIN_BARS, int(lookback))
    window = vals[-win_n:]
    vol_all = list(volumes) if volumes is not None else [None] * n
    if len(vol_all) < n:
        vol_all = vol_all + [None] * (n - len(vol_all))
    vol_win = vol_all[-len(window) :]
    diffs = [window[i] - window[i - 1] for i in range(1, len(window))]
    path = sum(abs(d) for d in diffs)
    net = abs(window[-1] - window[0])
    er = (net / path) if path > 1e-9 else 0.0
    atr = (path / len(diffs)) if diffs else 0.0
    rng = max(window) - min(window)
    range_over_atr = (rng / atr) if atr > 1e-9 else 0.0
    signs = [1 if d > 0 else (-1 if d < 0 else 0) for d in diffs]
    nz = [s for s in signs if s != 0]
    flips = sum(1 for i in range(1, len(nz)) if nz[i] != nz[i - 1])
    flip_frac = (flips / (len(nz) - 1)) if len(nz) > 1 else 0.0
    mean = sum(window) / len(window)
    mid_dev_atr = (abs(window[-1] - mean) / atr) if atr > 1e-9 else 999.0
    vwap, vwap_src = _vwap_window(window, vol_win)
    ema_len = 21 if len(vals) >= 21 else 15
    ema = _ema_last(vals, ema_len)
    rsi = _rsi_last(vals, 14)
    vol_pack = _vol_last3(vol_win)
    rv = _realized_vol(window)
    last = window[-1]
    net_signed = window[-1] - window[0]
    votes_up = 0
    votes_down = 0
    if net_signed > 0:
        votes_up += 1
    elif net_signed < 0:
        votes_down += 1
    if vwap is not None:
        if last > vwap:
            votes_up += 1
        elif last < vwap:
            votes_down += 1
    if ema is not None:
        if last > ema:
            votes_up += 1
        elif last < ema:
            votes_down += 1
    if rsi is not None:
        if rsi >= float(REGIME_RSI_MID_HI):
            votes_up += 1
        elif rsi <= float(REGIME_RSI_MID_LO):
            votes_down += 1
    greeks = greeks or {}
    iv = greeks.get("iv")
    ce_d = greeks.get("ce_delta")
    pe_d = greeks.get("pe_delta")
    try:
        if ce_d is not None and pe_d is not None:
            if abs(float(ce_d)) > abs(float(pe_d)) + 0.05:
                votes_up += 1
            elif abs(float(pe_d)) > abs(float(ce_d)) + 0.05:
                votes_down += 1
    except (TypeError, ValueError):
        pass
    if votes_up >= 3 and votes_up > votes_down:
        direction = "UP"
    elif votes_down >= 3 and votes_down > votes_up:
        direction = "DOWN"
    elif net_signed > 0 and votes_up > votes_down:
        direction = "UP"
    elif net_signed < 0 and votes_down > votes_up:
        direction = "DOWN"
    else:
        direction = "FLAT"
    chop = er <= float(er_max) and (
        flip_frac >= float(flip_min) or range_over_atr <= float(range_atr_max)
    )
    tight_mr = er <= float(er_max) and mid_dev_atr < 1.25 and range_over_atr <= float(range_atr_max)
    rsi_mid = rsi is not None and float(REGIME_RSI_MID_LO) < float(rsi) < float(REGIME_RSI_MID_HI)
    near_vwap = vwap is not None and atr > 1e-9 and abs(last - vwap) / atr < 0.75
    iv_chop = False
    try:
        if iv is not None and float(iv) >= 25.0 and er <= float(er_max):
            iv_chop = True
    except (TypeError, ValueError):
        iv_chop = False
    aligned = False
    if direction == "UP":
        ok_v = vwap is None or last > vwap
        ok_e = ema is None or last > ema
        aligned = ok_v and ok_e and (vwap is not None or ema is not None)
    elif direction == "DOWN":
        ok_v = vwap is None or last < vwap
        ok_e = ema is None or last < ema
        aligned = ok_v and ok_e and (vwap is not None or ema is not None)
    er_trend = er >= 0.45 or (er >= 0.35 and range_over_atr >= 5.0)
    vol_expand = vol_pack.get("expand")
    impulse = _last3_impulse(window)
    impulse_raw = impulse.get("last3_impulse")
    bars = list(ohlc) if ohlc else _ohlc_from_closes(window)
    last_bar = bars[-1] if bars else None
    prior_range = None
    if len(bars) >= 2:
        try:
            prev_b = bars[-2]
            prior_range = float(prev_b["high"]) - float(prev_b["low"])
        except (KeyError, TypeError, ValueError):
            prior_range = None
    confirmed = confirm_last3_impulse(
        impulse_dir=str(impulse_raw) if impulse_raw in {"UP", "DOWN"} else None,
        last_bar=last_bar,
        prior_range=prior_range,
        volumes=vol_win,
        vol_expand=vol_expand if isinstance(vol_expand, bool) else None,
        sr=sr,
        opt_confirm=opt_confirm,
        greeks=greeks,
    )
    impulse_dir = impulse_raw if confirmed.get("ok") else None
    # Confirmed last-3 may TREND through 15m chop. Unconfirmed waits for the ITM bin.
    if impulse_dir in {"UP", "DOWN"}:
        regime = "TREND"
        direction = str(impulse_dir)
        reason = str(impulse.get("last3_reason") or "last3_impulse")
        aligned = True
    elif chop or tight_mr or rsi_mid or iv_chop or (near_vwap and er <= float(er_max)):
        regime = "SIDEWAYS"
        reason = "low_er_rsi_mid_or_vwap_band"
        if iv_chop:
            reason = "iv_rich_chop"
        elif rsi_mid:
            reason = "rsi_mid_sideways"
    elif er_trend and aligned and direction in {"UP", "DOWN"} and vol_expand is not False:
        regime = "TREND"
        reason = "er_vwap_ema_vol_rsi"
    elif er_trend and not aligned:
        regime = "UNKNOWN"
        reason = "er_vs_vwap_ema_disagree"
        direction = "FLAT"
    else:
        regime = "UNKNOWN"
        reason = "mixed_index_path"
    return {
        "regime": regime,
        "direction": direction,
        "layer": "HYPOTHESIS",
        "n": n,
        "lookback": len(window),
        "er": round(er, 4),
        "flip_frac": round(flip_frac, 4),
        "range_over_atr": round(range_over_atr, 4),
        "mid_dev_atr": round(float(mid_dev_atr), 4) if mid_dev_atr < 900 else None,
        "net_signed": round(float(net_signed), 4),
        "vwap": round(float(vwap), 4) if vwap is not None else None,
        "vwap_src": vwap_src,
        "ema": round(float(ema), 4) if ema is not None else None,
        "ema_len": ema_len,
        "rsi": round(float(rsi), 2) if rsi is not None else None,
        "vol_expand": vol_expand,
        "vol_status": vol_pack.get("status"),
        "vol_last3_sum": vol_pack.get("last3_sum"),
        "realized_vol": round(float(rv), 6) if rv is not None else None,
        "iv": iv,
        "votes_up": votes_up,
        "votes_down": votes_down,
        "reason": reason,
        "last3_closes": impulse.get("last3_closes"),
        "last3_er": impulse.get("last3_er"),
        "last3_net": impulse.get("last3_net"),
        "last3_impulse_raw": impulse_raw,
        "last3_impulse": impulse_dir,
        "last3_confirmed": bool(confirmed.get("ok")),
        "last3_trap": confirmed.get("trap"),
        "last3_reason": (
            str(impulse.get("last3_reason") or "")
            if confirmed.get("ok")
            else (str(confirmed.get("trap") or impulse.get("last3_reason")))
        ),
        "candle_shape": (confirmed.get("candle") or {}).get("shape"),
        "proxy_poc": (confirmed.get("candle") or {}).get("proxy_poc"),
        "sr_near": confirmed.get("sr"),
    }


def regime_rr_adjust(
    classified: Optional[dict[str, Any]],
    *,
    stop_frac: float,
    target_frac: float,
) -> dict[str, Any]:
    """Paper R:R from 1m realized vol + last-3 volume. Never invents greeks. NO_PROMOTE."""
    sf = float(stop_frac)
    tf = float(target_frac)
    notes: list[str] = []
    pack = classified or {}
    if str(pack.get("regime") or "") != "TREND":
        return {"stop_frac": sf, "target_frac": tf, "notes": notes}
    if pack.get("vol_expand") is True:
        tf = min(0.70, tf * 1.06)
        notes.append("last-3 1m volume expanding vs prior-3: slightly better paper target")
    rv = pack.get("realized_vol")
    try:
        if rv is not None and float(rv) >= REGIME_RV_WIDEN:
            sf = min(0.55, sf * 1.10)
            tf = min(tf, float(TARGET_FRAC))
            notes.append("high 1m realized vol: wider stop, cap target (do not 3–4× R)")
    except (TypeError, ValueError):
        pass
    iv = pack.get("iv")
    try:
        if iv is not None and float(iv) >= 22.0:
            sf = min(0.55, sf * 1.08)
            notes.append("chain IV elevated: wider stop only")
    except (TypeError, ValueError):
        pass
    return {"stop_frac": sf, "target_frac": tf, "notes": notes}


def allocate_desk_capital(
    *,
    total: float = DESK_CAPITAL_INR,
    books: Sequence[str] = LIVE_BOOKS,
    tradable: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    """Equal ₹ split of desk capital. SKIP/DATA_INSUFFICIENT books get ₹0; remainder to traders."""
    book_list = list(books)
    want = set(tradable) if tradable is not None else set(book_list)
    active = [b for b in book_list if b in want]
    skipped = [b for b in book_list if b not in want]
    per_book = {b: 0.0 for b in book_list}
    unallocated = round(float(total), 2)
    if active:
        n = len(active)
        paisa = int(round(float(total) * 100))
        base_paisa, rem_paisa = divmod(paisa, n)
        for i, book in enumerate(active):
            extra = rem_paisa if i == 0 else 0
            per_book[book] = (base_paisa + extra) / 100.0
        unallocated = 0.0
    return {
        "desk_capital_inr": round(float(total), 2),
        "n_books": len(book_list),
        "n_tradable": len(active),
        "tradable": active,
        "skipped": skipped,
        "per_book": per_book,
        "unallocated_inr": unallocated,
        "note": "SOD default: desk capital on MIX-DEFAULT-BUY only. LAB books observe-or-skip. --sod-off (tests) splits logit + FOLLOWS + XR + greeks. Observe clones get ₹0.",
        "production_params_written": False,
    }


def tradable_fill_books(*, has_greeks: bool, sod_one_ticket: bool = True) -> list[str]:
    """Capital seats. SOD product = MIX-DEFAULT-BUY only. LAB observe-or-skip."""
    if sod_one_ticket:
        return [SOD_PRODUCT_BOOK]
    out: list[str] = []
    for book in LIVE_BOOKS:
        if book in OBSERVE_ONLY_BOOKS:
            continue
        if book == "MIX-ML-GREEKS" and not has_greeks:
            continue
        if book in FILL_ELIGIBLE_BOOKS:
            out.append(book)
    return out


def resolve_fill_intents(
    *,
    dealer_confirm: Optional[str],
    dealer_verdict: str,
    logit: dict[str, Any],
    logit_xr: dict[str, Any],
    ml001_hold: bool,
    follow_gap: bool,
    ml002_hold: bool,
    ml1: dict[str, Any],
    impulse_side: Optional[str] = None,
) -> dict[str, tuple[Optional[str], Optional[str]]]:
    """--sod-off / pytest A/B only. Not the SOD fill router.

    SOD path: votes → picker → observer → _try_open(MIX-DEFAULT-BUY).
    Analyst logic stays here so old parallel-book tests still work.
    """
    logit_own = logit.get("side") if logit.get("side") in {"CE", "PE"} else None
    xr_own = logit_xr.get("side") if logit_xr.get("side") in {"CE", "PE"} else None
    dealer_own = dealer_confirm if dealer_confirm in {"CE", "PE"} else None
    verdict = str(dealer_verdict or "HOLD")
    impulse_own = impulse_side if impulse_side in {"CE", "PE"} else None
    # Last-3 1m path owns FILL side. 10s logit/dealer bounce after a 100pt dump is not the ticket.
    if impulse_own:
        logit_own = impulse_own
        if xr_own is not None:
            xr_own = impulse_own

    if logit_own:
        if dealer_own == logit_own:
            dealer_fill, dealer_skip = dealer_own, None
        elif impulse_own and dealer_own is None:
            dealer_fill, dealer_skip = impulse_own, None
        else:
            dealer_fill, dealer_skip = None, f"DEALER_{verdict}_VS_LOGIT_{logit_own}"
    elif dealer_own:
        dealer_fill, dealer_skip = dealer_own, None
    else:
        dealer_fill, dealer_skip = None, f"DEALER_{verdict}"

    if ml001_hold or follow_gap:
        ml001 = (None, "ML-001_HOLD")
    else:
        ml001 = (None, "OBSERVE_NO_OWN_SIDE")
    if ml002_hold or follow_gap:
        ml002 = (None, "ML-002_HOLD")
    else:
        ml002 = (None, "OBSERVE_NO_OWN_SIDE")

    if ml1.get("status") != "OK":
        ml1_skip = str(ml1.get("reason") or "ML-1_DATA_INSUFFICIENT")
    elif ml1.get("take") is False:
        ml1_skip = "ML-1_SKIP"
    else:
        ml1_skip = "OBSERVE_NO_OWN_SIDE"

    logit_skip = None if logit_own else str(logit.get("reason") or logit.get("status") or "NO_SIDE")
    xr_skip = None if xr_own else str(logit_xr.get("reason") or logit_xr.get("status") or "XR_NO_OWN_SIDE")

    greeks_side, greeks_skip = greeks_vote_intent(
        dealer_confirm=dealer_confirm,
        logit=logit,
        impulse_side=impulse_side,
    )

    return {
        "MIX-DEFAULT-BUY": (dealer_fill, dealer_skip),
        "ML-001": ml001,
        "ML-002": ml002,
        "ML-1": (None, ml1_skip),
        "MIX-ML-LOGIT": (logit_own, logit_skip),
        "MIX-ML-LOGIT-XR": (xr_own, xr_skip),
        "MIX-TV-EP-024": (None, "OBSERVE_NO_OWN_FILL"),
        "MIX-ML-GREEKS": (greeks_side, greeks_skip),
    }


def tape_has_dhan_greeks(triples: Sequence[Triple]) -> bool:
    """True only if a parsed greeks/IV field is present. Never invent."""
    for tick in triples:
        wings = tick.wing_quotes if isinstance(tick.wing_quotes, dict) else {}
        for cell in wings.values():
            if not isinstance(cell, dict):
                continue
            for key in (
                "ce_delta",
                "pe_delta",
                "ce_theta",
                "pe_theta",
                "ce_gamma",
                "pe_gamma",
                "ce_vega",
                "pe_vega",
                "ce_iv",
                "pe_iv",
            ):
                if cell.get(key) is not None:
                    return True
    return False


def sleep_with_beats(
    total_seconds: float,
    *,
    beat_seconds: float = DASHBOARD_HEARTBEAT_SECONDS,
    sleep_fn: Callable[[float], None],
    on_beat: Optional[Callable[[float], None]] = None,
    stop_fn: Optional[Callable[[], bool]] = None,
) -> str:
    """Sleep `total_seconds`, calling on_beat about every `beat_seconds`. No Dhan poll."""
    remaining = max(0.0, float(total_seconds))
    beat = max(0.05, float(beat_seconds))
    while remaining > 1e-9:
        if stop_fn is not None and stop_fn():
            return "stopped"
        chunk = min(beat, remaining)
        sleep_fn(chunk)
        remaining = round(remaining - chunk, 6)
        if on_beat is not None:
            on_beat(remaining)
    return "slept"


def refresh_dashboard_clock(board: dict[str, Any], *, tick_seconds: int) -> dict[str, Any]:
    """Rewrite as_of from last tick. Does not re-walk the tape or call Dhan."""
    stamp = datetime.now(IST).isoformat(timespec="seconds")
    board["as_of_ist"] = stamp
    heart = dict(board.get("heartbeat") or {})
    heart["as_of_ist"] = stamp
    heart["alive"] = True
    heart["dashboard_write_seconds"] = DASHBOARD_HEARTBEAT_SECONDS
    heart["tick_seconds"] = int(tick_seconds)
    heart["tick_ne_dashboard_reason"] = TICK_NE_DASHBOARD_REASON
    board["heartbeat"] = heart
    return board


def round_atm_strike(underlying: str, index_ltp: float) -> float:
    step = STRIKE_STEP.get(underlying.upper(), 50.0)
    return round(float(index_ltp) / step) * step


def itm_depth_points(underlying: str) -> float:
    und = underlying.upper()
    step = STRIKE_STEP.get(und, 50.0)
    points = ITM_POINTS.get(und, 200.0)
    n = max(ITM_STEPS_MIN, int(round(float(points) / step)))
    return n * step


def itm_wing_strikes(underlying: str, atm: float) -> dict[str, float]:
    """Buy-side ITM: CE below ATM, PE above ATM. Never ATM/OTM."""
    und = underlying.upper()
    depth = itm_depth_points(und)
    atm_f = float(atm)
    return {"CE": atm_f - depth, "PE": atm_f + depth}


def chain_atm(tick: Triple, underlying: str) -> float:
    """Dhan ATM if present, else round INDEX. Never invent a strike."""
    if tick.atm_strike is not None:
        return float(tick.atm_strike)
    return round_atm_strike(underlying, tick.idx_close)


def paper_itm_strike(tick: Triple, side: str, underlying: str) -> float:
    """Founder-depth ITM vs the tighter of Dhan ATM and rounded INDEX.

    If Dhan ATM is 74300 and INDEX rounds to 74400, CE ITM is 74200 not 74300
    (74300 is the ATM the trader sees).
    """
    und = underlying.upper()
    dhan = chain_atm(tick, und)
    idx_atm = round_atm_strike(und, tick.idx_close)
    if side == "CE":
        return itm_wing_strikes(und, min(dhan, idx_atm))["CE"]
    return itm_wing_strikes(und, max(dhan, idx_atm))["PE"]


def is_buy_itm(side: str, strike: float, tick: Triple, underlying: str) -> bool:
    """True only if the strike is ITM vs Dhan ATM *and* vs INDEX LTP. ATM/OTM = false."""
    atm = chain_atm(tick, underlying)
    idx = float(tick.idx_close)
    k = float(strike)
    if abs(k - float(atm)) < 1e-6:
        return False
    if side == "CE":
        return k < float(atm) - 1e-6 and k < idx - 1e-6
    return k > float(atm) + 1e-6 and k > idx + 1e-6


def is_deep_itm(side: str, strike: float, tick: Triple, underlying: str) -> bool:
    """ITM and at least founder depth (NIFTY 200pt / BN+SX 300pt). Shallow 1-step ticks refused."""
    if not is_buy_itm(side, strike, tick, underlying):
        return False
    atm = chain_atm(tick, underlying)
    need = itm_depth_points(underlying)
    k = float(strike)
    if side == "CE":
        return float(atm) - k >= need - 1e-6
    return k - float(atm) >= need - 1e-6


def _opt_px(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def quote_for_side(
    tick: Triple,
    side: str,
    *,
    strike: Optional[float] = None,
    itm_only: bool = False,
) -> tuple[Optional[float], Optional[float], str]:
    """Return (ltp, low, source). Booked strike never silently uses a rolled ATM/ITM print.

    SOD product OPEN/CLOSE/MTM: `itm_only=True` — missing ITM is DATA_INSUFFICIENT,
    never ATM LTP as if it were ITM. FOLLOWS may still read ATM last-tick for its vote.
    """
    want = float(strike) if strike is not None else None
    wings = tick.wing_quotes if isinstance(tick.wing_quotes, dict) else {}

    def _from_cell(cell: Any, src: str) -> Optional[tuple[float, float, str]]:
        if not isinstance(cell, dict):
            return None
        key = "ce" if side == "CE" else "pe"
        ltp = _opt_px(cell.get(key))
        if ltp is None:
            return None
        low = _opt_px(cell.get(f"{key}_low")) or ltp
        return ltp, low, src

    if want is not None:
        cell = wings.get(str(int(want))) or wings.get(str(want)) or wings.get(f"{want:.1f}")
        hit = _from_cell(cell, f"STRIKE_{int(want)}")
        if hit is not None:
            return hit
        if side == "CE" and tick.itm_ce_strike is not None and abs(float(tick.itm_ce_strike) - want) < 1e-6:
            itm = _opt_px(tick.itm_ce_close)
            if itm is not None:
                return itm, _opt_px(tick.itm_ce_low) or itm, "ITM_100"
        if side == "PE" and tick.itm_pe_strike is not None and abs(float(tick.itm_pe_strike) - want) < 1e-6:
            itm = _opt_px(tick.itm_pe_close)
            if itm is not None:
                return itm, _opt_px(tick.itm_pe_low) or itm, "ITM_100"
        if tick.atm_strike is not None and abs(float(tick.atm_strike) - want) < 1e-6:
            if itm_only:
                return None, None, "MISSING_ITM"
            if side == "CE":
                atm = _opt_px(tick.ce_close)
                return atm, (_opt_px(tick.ce_low) or atm) if atm is not None else None, "ATM"
            atm = _opt_px(tick.pe_close)
            return atm, (_opt_px(tick.pe_low) or atm) if atm is not None else None, "ATM"
        if not wings and tick.atm_strike is None:
            if itm_only:
                return None, None, "MISSING_ITM"
            if side == "CE":
                atm = _opt_px(tick.ce_close)
                return atm, _opt_px(tick.ce_low) or atm, "ATM"
            atm = _opt_px(tick.pe_close)
            return atm, _opt_px(tick.pe_low) or atm, "ATM"
        return None, None, "MISSING_STRIKE"
    if side == "CE":
        itm = _opt_px(tick.itm_ce_close)
        if itm is not None:
            return itm, _opt_px(tick.itm_ce_low) or itm, "ITM_100"
        if itm_only:
            return None, None, "MISSING_ITM"
        atm = _opt_px(tick.ce_close)
        return atm, _opt_px(tick.ce_low) or atm, "ATM"
    itm = _opt_px(tick.itm_pe_close)
    if itm is not None:
        return itm, _opt_px(tick.itm_pe_low) or itm, "ITM_100"
    if itm_only:
        return None, None, "MISSING_ITM"
    atm = _opt_px(tick.pe_close)
    return atm, _opt_px(tick.pe_low) or atm, "ATM"


# STRAT-006 spoken 0.55–0.60 is WEAK. Paper band only. HAUS ~0.40 adverse.
DELTA_PREF = 0.55
DELTA_BAND = (0.45, 0.70)
DELTA_SKIP_BELOW = 0.40


def _wing_cell(tick: Triple, strike: float) -> dict[str, Any]:
    wings = tick.wing_quotes if isinstance(tick.wing_quotes, dict) else {}
    return wings.get(str(int(strike))) or wings.get(str(strike)) or wings.get(f"{strike:.1f}") or {}


def leg_greeks(tick: Triple, side: str, strike: float) -> dict[str, Optional[float]]:
    cell = _wing_cell(tick, strike)
    prefix = "ce" if side == "CE" else "pe"

    def _num(raw: Any) -> Optional[float]:
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    return {
        "delta": _num(cell.get(f"{prefix}_delta")),
        "gamma": _num(cell.get(f"{prefix}_gamma")),
        "theta": _num(cell.get(f"{prefix}_theta")),
        "vega": _num(cell.get(f"{prefix}_vega")),
        "iv": _num(cell.get(f"{prefix}_iv")),
    }


def pick_paper_strike(tick: Triple, side: str, atm: float, underlying: str) -> float:
    """ITM_100 default. Delta may pick another ITM cell in 0.45–0.70. Never ATM/OTM."""
    default = paper_itm_strike(tick, side, underlying)
    if not is_deep_itm(side, default, tick, underlying):
        default = itm_wing_strikes(underlying, float(atm))[side]
    wings = tick.wing_quotes if isinstance(tick.wing_quotes, dict) else {}
    best: Optional[float] = None
    best_dist = 9.0
    prefix = "ce" if side == "CE" else "pe"
    for key, cell in wings.items():
        if not isinstance(cell, dict):
            continue
        try:
            strike = float(key)
            delta = float(cell[f"{prefix}_delta"])
        except (TypeError, ValueError, KeyError):
            continue
        if not is_deep_itm(side, strike, tick, underlying):
            continue
        ad = abs(delta)
        if ad < DELTA_BAND[0] or ad > DELTA_BAND[1]:
            continue
        dist = abs(ad - DELTA_PREF)
        if dist < best_dist:
            best_dist = dist
            best = strike
    return float(best) if best is not None else default


def _bin_num(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def moneyness_of_strike(side: str, strike: float, atm: float, index_ltp: Optional[float] = None) -> str:
    """ITM / ATM / OTM vs chain ATM. INDEX LTP can still mark a 'ITM vs ATM' cell ATM/OTM vs spot."""
    step = 1e-6
    if abs(float(strike) - float(atm)) < step:
        return "ATM"
    if side == "CE":
        vs_atm = "ITM" if float(strike) < float(atm) else "OTM"
    else:
        vs_atm = "ITM" if float(strike) > float(atm) else "OTM"
    if index_ltp is None or vs_atm != "ITM":
        return vs_atm
    if side == "CE" and float(strike) >= float(index_ltp) - step:
        return "OTM" if float(strike) > float(index_ltp) + step else "ATM"
    if side == "PE" and float(strike) <= float(index_ltp) + step:
        return "OTM" if float(strike) < float(index_ltp) - step else "ATM"
    return vs_atm


def itm_leg_pack(tick: Triple, underlying: str, side: str) -> dict[str, Any]:
    """One ITM CE or PE cell from the chain. Missing volume/OI/delta = DATA_INSUFFICIENT, not invent."""
    und = underlying.upper()
    atm = chain_atm(tick, und)
    strike = paper_itm_strike(tick, side, und)
    cell = _wing_cell(tick, strike)
    prefix = "ce" if side == "CE" else "pe"
    px, low, src = quote_for_side(tick, side, strike=strike)
    return {
        "side": side,
        "strike": strike,
        "atm": atm,
        "moneyness": moneyness_of_strike(side, strike, atm, index_ltp=tick.idx_close),
        "px": px,
        "low": low,
        "quote_src": src,
        "volume": _bin_num(cell.get(f"{prefix}_volume")),
        "oi": _bin_num(cell.get(f"{prefix}_oi")),
        "delta": _bin_num(cell.get(f"{prefix}_delta")),
        "layer": "HYPOTHESIS",
    }


def bin_both_wings_packet(bin_rec: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Desk always looks at both ITM CE and PE. OI only if Dhan printed it."""
    rec = bin_rec or {}
    ce = dict(rec.get("ce") or {})
    pe = dict(rec.get("pe") or {})

    def _oi(leg: dict[str, Any]) -> Any:
        if leg.get("oi") is None:
            return "DATA_INSUFFICIENT"
        return leg.get("oi")

    return {
        "ce": {
            "strike": ce.get("strike"),
            "px": ce.get("px"),
            "volume": ce.get("volume"),
            "oi": _oi(ce),
            "trend_votes": list(rec.get("ce_votes") or []),
        },
        "pe": {
            "strike": pe.get("strike"),
            "px": pe.get("px"),
            "volume": pe.get("volume"),
            "oi": _oi(pe),
            "trend_votes": list(rec.get("pe_votes") or []),
        },
        "side": rec.get("side"),
        "reason": rec.get("reason"),
        "missing": list(rec.get("missing") or []),
        "note": "Both wings. OI never invented.",
    }


def score_itm_bin(prev: dict[str, Any], curr: dict[str, Any]) -> dict[str, Any]:
    """ITM CE chart vs ITM PE chart. CE selling + PE volume/OI/delta confirms PUT. Never invents."""
    missing: list[str] = []
    pe_votes: list[str] = []
    ce_votes: list[str] = []

    def _chg(leg: str, field: str) -> Optional[float]:
        a = (prev.get(leg) or {}).get(field)
        b = (curr.get(leg) or {}).get(field)
        if a is None or b is None:
            missing.append(f"{leg}_{field}")
            return None
        try:
            return float(b) - float(a)
        except (TypeError, ValueError):
            missing.append(f"{leg}_{field}")
            return None

    pe_vol_chg = _chg("pe", "volume")
    pe_px_chg = _chg("pe", "px")
    ce_px_chg = _chg("ce", "px")
    pe_oi_chg = _chg("pe", "oi")
    ce_oi_chg = _chg("ce", "oi")
    ce_vol_chg = _chg("ce", "volume")
    pe_d_chg = _chg("pe", "delta")
    ce_d_chg = _chg("ce", "delta")
    prev_pe_vol = (prev.get("pe") or {}).get("volume")
    if pe_vol_chg is not None and prev_pe_vol is not None and float(prev_pe_vol) > 0:
        if (curr.get("pe") or {}).get("volume") is not None and float(
            (curr["pe"] or {}).get("volume") or 0
        ) >= float(prev_pe_vol) * float(BIN_VOL_EXPAND):
            pe_votes.append("PE_VOL_EXPAND")
    if pe_px_chg is not None and pe_px_chg > 0:
        pe_votes.append("PE_PREMIUM_UP")
    if ce_px_chg is not None and ce_px_chg < 0:
        pe_votes.append("CE_PREMIUM_DOWN")
    if pe_oi_chg is not None and pe_oi_chg > 0 and pe_px_chg is not None and pe_px_chg > 0:
        pe_votes.append("PE_OI_UP_WITH_PREMIUM")
    if ce_vol_chg is not None and ce_vol_chg > 0 and ce_px_chg is not None and ce_px_chg < 0:
        pe_votes.append("CE_SELL_VOLUME")
    if pe_d_chg is not None and pe_d_chg < 0:
        pe_votes.append("PE_DELTA_MORE_ITM")
    if ce_px_chg is not None and ce_px_chg > 0:
        ce_votes.append("CE_PREMIUM_UP")
    if pe_px_chg is not None and pe_px_chg < 0:
        ce_votes.append("PE_PREMIUM_DOWN")
    if ce_vol_chg is not None and prev.get("ce") and (prev["ce"] or {}).get("volume"):
        prev_ce_vol = float((prev["ce"] or {}).get("volume") or 0)
        if prev_ce_vol > 0 and (curr.get("ce") or {}).get("volume") is not None:
            if float((curr["ce"] or {}).get("volume") or 0) >= prev_ce_vol * float(BIN_VOL_EXPAND):
                ce_votes.append("CE_VOL_EXPAND")
    if ce_oi_chg is not None and ce_oi_chg > 0 and ce_px_chg is not None and ce_px_chg > 0:
        ce_votes.append("CE_OI_UP_WITH_PREMIUM")
    if ce_d_chg is not None and ce_d_chg > 0:
        ce_votes.append("CE_DELTA_MORE_ITM")
    if pe_oi_chg is not None and pe_px_chg is not None:
        if pe_oi_chg < 0 and pe_px_chg > 0:
            pe_votes.append("PE_SHORT_COVER")
        if pe_oi_chg < 0 and pe_px_chg < 0:
            pe_votes.append("PE_LONG_UNWIND")
    if ce_oi_chg is not None and ce_px_chg is not None:
        if ce_oi_chg < 0 and ce_px_chg > 0:
            ce_votes.append("CE_SHORT_COVER")
        if ce_oi_chg < 0 and ce_px_chg < 0:
            ce_votes.append("CE_LONG_UNWIND")
    flow = {
        "PE_VOL_EXPAND",
        "PE_OI_UP_WITH_PREMIUM",
        "PE_SHORT_COVER",
        "CE_SELL_VOLUME",
        "PE_DELTA_MORE_ITM",
        "CE_VOL_EXPAND",
        "CE_OI_UP_WITH_PREMIUM",
        "CE_SHORT_COVER",
        "CE_DELTA_MORE_ITM",
    }

    def _enough(votes: list[str]) -> bool:
        if len(votes) < int(BIN_MIN_VOTES):
            return False
        return any(v in flow for v in votes)

    side = None
    reason = "itm_bin_wait"
    if _enough(pe_votes) and len(pe_votes) >= len(ce_votes):
        side = "PE"
        reason = "itm_bin_pe_confirm"
    elif _enough(ce_votes) and len(ce_votes) > len(pe_votes):
        side = "CE"
        reason = "itm_bin_ce_confirm"
    return {
        "layer": "HYPOTHESIS",
        "side": side,
        "direction": "DOWN" if side == "PE" else ("UP" if side == "CE" else None),
        "reason": reason,
        "pe_votes": pe_votes,
        "ce_votes": ce_votes,
        "n_pe_votes": len(pe_votes),
        "n_ce_votes": len(ce_votes),
        "missing": missing,
        "wait_3_index_bars": False,
        "note": (
            "ITM CE chart vs ITM PE chart vs INDEX. Two votes is enough — do not wait three INDEX 1m bars. "
            "OI up + premium up = new longs (or cover). OI down + premium up = short covering. "
            "OI down + premium down = long unwind. Missing OI is DATA_INSUFFICIENT not invent. "
            "NO_PROMOTE."
        ),
    }


def update_itm_bin(engine: BookEngine, underlying: str, tick: Triple) -> dict[str, Any]:
    """Keep the ITM CE/PE bin (trader's three charts). Roll strikes each tick to ~100pt ITM."""
    und = underlying.upper()
    pack = {
        "ts": int(tick.ts),
        "index": float(tick.idx_close),
        "ce": itm_leg_pack(tick, und, "CE"),
        "pe": itm_leg_pack(tick, und, "PE"),
    }
    hist = engine.itm_bins.setdefault(und, {"ticks": [], "last": None})
    ticks = list(hist.get("ticks") or [])
    prev = ticks[-1] if ticks else None
    scored = (
        score_itm_bin(prev, pack)
        if prev is not None
        else {
            "layer": "HYPOTHESIS",
            "side": None,
            "direction": None,
            "reason": "itm_bin_need_prior_tick",
            "pe_votes": [],
            "ce_votes": [],
            "n_pe_votes": 0,
            "n_ce_votes": 0,
            "missing": [],
            "wait_3_index_bars": False,
            "note": "Need one prior ITM print. Not three INDEX 1m bars.",
        }
    )
    rec = {**pack, **scored}
    ticks.append(rec)
    hist["ticks"] = ticks[-int(BIN_KEEP_TICKS) :]
    hist["last"] = rec
    form_key = hist.get("forming_key")
    now_key = minute_key(int(tick.ts))
    if form_key is not None and int(form_key) != int(now_key) and hist.get("forming") is not None:
        closed = list(hist.get("closed_1m") or [])
        closed.append({"ce": hist["forming"].get("ce"), "pe": hist["forming"].get("pe")})
        hist["closed_1m"] = closed[-8:]
    hist["forming_key"] = now_key
    hist["forming"] = {"ce": pack.get("ce"), "pe": pack.get("pe")}
    engine.itm_bins[und] = hist
    return rec


def closed_1m_cover_votes(hist: Optional[dict[str, Any]], side: str) -> list[str]:
    """Cover/OI votes from the last two *closed* 1m ITM packs. Not the forming minute."""
    bars = list((hist or {}).get("closed_1m") or [])
    if len(bars) < 2:
        return []
    scored = score_itm_bin(bars[-2], bars[-1])
    wing = str(side or "").upper()
    return list(scored.get("pe_votes" if wing == "PE" else "ce_votes") or [])


def closed_1m_has_cover_strength(hist: Optional[dict[str, Any]], side: str) -> bool:
    wing = str(side or "").upper()
    votes = closed_1m_cover_votes(hist, wing)
    return f"{wing}_SHORT_COVER" in votes or f"{wing}_OI_UP_WITH_PREMIUM" in votes


def apply_itm_bin_to_regime(classified: dict[str, Any], bin_rec: dict[str, Any]) -> dict[str, Any]:
    """ITM bin can TREND from chop. A 10s wing tick must not overwrite INDEX TREND / last-3 raw."""
    out = dict(classified)
    if "index_direction" not in out:
        out["index_direction"] = out.get("direction")
    out["itm_bin"] = {
        "side": bin_rec.get("side"),
        "reason": bin_rec.get("reason"),
        "pe_votes": list(bin_rec.get("pe_votes") or []),
        "ce_votes": list(bin_rec.get("ce_votes") or []),
        "n_pe_votes": bin_rec.get("n_pe_votes"),
        "n_ce_votes": bin_rec.get("n_ce_votes"),
        "missing": list(bin_rec.get("missing") or []),
        "ce": bin_rec.get("ce"),
        "pe": bin_rec.get("pe"),
        "index": bin_rec.get("index"),
        "wait_3_index_bars": False,
    }
    if out.get("last3_impulse") in {"UP", "DOWN"}:
        return out
    side = bin_rec.get("side")
    if side not in {"CE", "PE"}:
        return out
    want = "DOWN" if side == "PE" else "UP"
    raw = out.get("last3_impulse_raw")
    idx_dir = out.get("index_direction")
    try:
        er = float(out.get("er") or 0.0)
    except (TypeError, ValueError):
        er = 0.0
    try:
        votes_up = int(out.get("votes_up") or 0)
        votes_down = int(out.get("votes_down") or 0)
    except (TypeError, ValueError):
        votes_up, votes_down = 0, 0
    strong_idx = er >= float(STALL_TREND_ER) and (
        (idx_dir == "UP" and votes_up > votes_down) or (idx_dir == "DOWN" and votes_down > votes_up)
    )
    if raw in {"UP", "DOWN"} and raw != want:
        if out.get("regime") != "TREND":
            out["regime"] = "TREND"
            out["direction"] = str(raw)
            out["reason"] = "last3_raw_holds_bin"
        return out
    if strong_idx and idx_dir in {"UP", "DOWN"} and idx_dir != want:
        return out
    out["regime"] = "TREND"
    out["direction"] = want
    out["reason"] = str(bin_rec.get("reason") or "itm_bin")
    return out


def paper_impulse_side(classified: dict[str, Any]) -> Optional[str]:
    """Last-3 INDEX impulse wins; else ITM CE/PE bin. Do not wait three INDEX 1m bars."""
    if classified.get("last3_impulse") == "DOWN":
        return "PE"
    if classified.get("last3_impulse") == "UP":
        return "CE"
    bin_side = (classified.get("itm_bin") or {}).get("side")
    if bin_side in {"CE", "PE"}:
        return bin_side
    return None


def paper_impulse_fill(classified: dict[str, Any]) -> bool:
    if str(classified.get("last3_impulse") or "") in {"UP", "DOWN"}:
        return True
    reason = str(classified.get("reason") or "")
    return reason.startswith("itm_bin_") and reason.endswith("_confirm")


def nifty_has_entry_strength(
    classified: Optional[dict[str, Any]],
    side: str,
    *,
    cover_closed_1m: bool = False,
    closed_1m_has_cover: bool = False,
) -> bool:
    """NIFTY NEW: last-3 / pause-continue / short-cover, or ITM-bin confirm+flow.

    Pause-wait at session high must not lock the dealer when the bin already confirms.
    cover_closed_1m (live default): 10s SHORT_COVER / OI-up is WATCH. Strength
    needs the same vote on the last closed 1m, and live must not be LONG_UNWIND.
    last-3 UP/DOWN and pause_continue still fill. PAPER only. NO_PROMOTE.
    """
    cl = classified or {}
    wing = str(side or "").upper()
    if cl.get("last3_impulse") in {"UP", "DOWN"}:
        return True
    if cl.get("last3_reason") == "pause_continue":
        return True
    if cover_closed_1m:
        if covering_label(cl, wing) == "LONG_UNWIND":
            return False
        return bool(closed_1m_has_cover)
    if covering_label(cl, wing) == "SHORT_COVER":
        return True
    if paper_impulse_fill(cl):
        return True
    try:
        er = float(cl.get("er") or 0.0)
    except (TypeError, ValueError):
        er = 0.0
    direction = cl.get("index_direction") or cl.get("direction")
    if cl.get("regime") == "TREND" and er >= float(STALL_TREND_ER):
        if direction == "UP" and wing == "CE":
            return True
        if direction == "DOWN" and wing == "PE":
            return True
    return False


def dealer_entry_book(book_id: str) -> bool:
    """WAIT_STRENGTH / impulse-align are dealer entry. ML fill books keep their own CE/PE."""
    return str(book_id) == "MIX-DEFAULT-BUY"


def covering_label(classified: Optional[dict[str, Any]], side: str) -> Optional[str]:
    """ITM-strike OI vs premium. Missing votes → None, never invent covering."""
    rec = (classified or {}).get("itm_bin") or {}
    votes = list(rec.get("pe_votes" if side == "PE" else "ce_votes") or [])
    tag = f"{side}_SHORT_COVER"
    unwind = f"{side}_LONG_UNWIND"
    if tag in votes:
        return "SHORT_COVER"
    if unwind in votes:
        return "LONG_UNWIND"
    return None


def ticket_against_market(
    pos: "OpenPaper",
    classified: Optional[dict[str, Any]],
    ltp: Optional[float] = None,
) -> bool:
    """Flatten a *dead* wing into the other side. Do not flatten a green CE on a 1m DOWN flicker.

    Need last-3 raw / INDEX against AND (underwater vs entry OR ER≥0.35 opposite).
    Opposite ITM flow still counts when the ticket is underwater.
    """
    cl = classified or {}
    side = str(getattr(pos, "side", None) or "").upper()
    if side not in {"CE", "PE"}:
        return False
    raw = cl.get("last3_impulse_raw")
    impulse = cl.get("last3_impulse")
    idx_dir = cl.get("index_direction") or cl.get("direction")
    against_raw = (side == "PE" and (impulse == "UP" or raw == "UP")) or (
        side == "CE" and (impulse == "DOWN" or raw == "DOWN")
    )
    try:
        live = float(ltp) if ltp is not None else float(getattr(pos, "last_ltp", None) or 0.0)
        entry = float(getattr(pos, "entry", None) or 0.0)
    except (TypeError, ValueError):
        live, entry = 0.0, 0.0
    underwater = entry > 0 and live > 0 and live + 3.0 < entry
    try:
        er = float(cl.get("er") or 0.0)
    except (TypeError, ValueError):
        er = 0.0
    try:
        votes_up = int(cl.get("votes_up") or 0)
        votes_down = int(cl.get("votes_down") or 0)
    except (TypeError, ValueError):
        votes_up, votes_down = 0, 0
    strong_opp = er >= float(STALL_TREND_ER) and (
        (side == "PE" and idx_dir == "UP" and votes_up > votes_down)
        or (side == "CE" and idx_dir == "DOWN" and votes_down > votes_up)
    )
    rec = cl.get("itm_bin") or {}
    bin_side = rec.get("side")
    flow_opp = False
    if side == "PE" and bin_side == "CE":
        flow = {
            "CE_PREMIUM_UP",
            "CE_VOL_EXPAND",
            "CE_OI_UP_WITH_PREMIUM",
            "CE_SHORT_COVER",
            "PE_PREMIUM_DOWN",
        }
        flow_opp = any(v in flow for v in list(rec.get("ce_votes") or []))
    if side == "CE" and bin_side == "PE":
        flow = {
            "PE_PREMIUM_UP",
            "PE_VOL_EXPAND",
            "PE_OI_UP_WITH_PREMIUM",
            "PE_SHORT_COVER",
            "CE_PREMIUM_DOWN",
        }
        flow_opp = any(v in flow for v in list(rec.get("pe_votes") or []))
    if against_raw and (underwater or strong_opp):
        return True
    if strong_opp and underwater:
        return True
    if flow_opp and underwater:
        return True
    return False


def bin_side_allows(classified: dict[str, Any], side: str) -> bool:
    """Do not buy CE against a PE ITM-bin (and reverse) unless a *confirmed* last-3 impulse owns the side."""
    if side not in {"CE", "PE"}:
        return False
    impulse = classified.get("last3_impulse")
    if impulse == "UP" and side == "CE":
        return True
    if impulse == "DOWN" and side == "PE":
        return True
    bin_side = (classified.get("itm_bin") or {}).get("side")
    if bin_side in {"CE", "PE"} and side != bin_side:
        return False
    return True


def floor_path_stop(*, entry: float, stop: float, min_stop: Optional[float] = None) -> float:
    """Path SL in premium points. Per-index floor when min_stop is set. PAPER."""
    e = float(entry)
    s = float(stop)
    need = max(float(min_stop if min_stop is not None else MIN_STOP_PREMIUM), e * MIN_STOP_FRAC_ENTRY)
    if e - s + 1e-9 < need:
        s = e - need
    return round(max(0.05, s), 4)


def cancel_if_bin_rolled(pos: OpenPaper, tick: Triple) -> Optional[str]:
    """Booked ITM_100 strike is no longer buy-side ITM vs Dhan ATM and INDEX."""
    if not str(pos.strike_source or "").startswith("ITM"):
        return None
    if pos.atm_strike is None:
        return None
    if is_buy_itm(pos.side, float(pos.atm_strike), tick, pos.underlying):
        return None
    return CANCEL_BIN_ROLL


def is_soft_cancel_reason(reason: Optional[str]) -> bool:
    """Filled-ticket cancel that should trail SL, not flatten. Unfilled stays hard."""
    if not reason:
        return False
    r = str(reason)
    if r in HARD_EXIT_REASONS or r.startswith("CANCEL_UNFILLED"):
        return False
    if r in SOFT_CANCEL_REASONS:
        return True
    return r.startswith("CANCEL_GREEKS")


def trail_premium_band(
    classified: Optional[dict[str, Any]] = None,
    *,
    idx_volume: Optional[float] = None,
    prev_idx_volume: Optional[float] = None,
    side: Optional[str] = None,
    underlying: Optional[str] = None,
    premium_atr: Optional[float] = None,
) -> float:
    """Trail in premium points. NIFTY tight, SENSEX wide. Not a shared ₹4–12 band."""
    und = str(underlying or "").upper()
    prof = INDEX_POINT_PROFILES.get(und)
    cl = classified or {}
    atr = premium_atr
    if atr is None:
        try:
            atr = float(cl["premium_atr"]) if cl.get("premium_atr") is not None else None
        except (TypeError, ValueError):
            atr = None
    if prof is not None and atr is not None and float(atr) > 0:
        band = float(atr) * float(prof["trail_k"])
        lo, hi = float(prof["trail_min"]), float(prof["trail_max"])
        if cl.get("last3_impulse") in {"UP", "DOWN"}:
            band *= 1.1
        if idx_volume is not None and prev_idx_volume is not None and float(prev_idx_volume) > 0:
            ratio = float(idx_volume) / float(prev_idx_volume)
            if ratio >= 1.5:
                band *= 1.15
            elif ratio <= 0.7:
                band *= 0.9
        return float(min(hi, max(lo, band)))
    band = 6.0
    rv = cl.get("realized_vol")
    er = cl.get("er")
    if rv is not None and float(rv) >= REGIME_RV_WIDEN:
        band += 2.0
    if er is not None and float(er) >= REGIME_FLIP_MIN:
        band += 1.5
    if cl.get("last3_impulse") in {"UP", "DOWN"}:
        band += 1.5
    if idx_volume is not None and prev_idx_volume is not None and float(prev_idx_volume) > 0:
        ratio = float(idx_volume) / float(prev_idx_volume)
        if ratio >= 1.5:
            band += 3.0
        elif ratio <= 0.7:
            band -= 1.5
    if side in {"CE", "PE"}:
        cover = covering_label(cl, side)
        if cover == "SHORT_COVER":
            band += 2.0
        elif cover == "LONG_UNWIND":
            band -= 2.0
    return float(min(TRAIL_BAND_MAX, max(TRAIL_BAND_MIN, band)))


def apply_filled_trail(
    engine: "BookEngine",
    pos: OpenPaper,
    *,
    ltp: float,
    ts: int,
    reason: str,
    classified: Optional[dict[str, Any]] = None,
    idx_volume: Optional[float] = None,
    prev_idx_volume: Optional[float] = None,
) -> bool:
    """Keep a filled ticket. Before T1 keep the path SL — do not BE-lock into 10s chop."""
    if not pos.filled:
        return False
    px = float(ltp)
    path = float(pos.path_stop) if pos.path_stop is not None else float(pos.stop)
    if int(pos.target_step) < 1:
        if px <= path + 1e-9:
            return False
        pos.stop = path
        return True
    if px <= float(pos.stop) + 1e-9:
        return False
    band = trail_premium_band(
        classified,
        idx_volume=idx_volume,
        prev_idx_volume=prev_idx_volume,
        side=pos.side,
        underlying=pos.underlying,
    )
    be = breakeven_premium(entry=float(pos.entry), qty=pos.qty)
    new_stop = max(float(pos.stop), px - band, be)
    if new_stop >= px - 0.25:
        return False
    new_stop = round(new_stop, 4)
    moved = new_stop > float(pos.stop) + 1e-9
    pos.stop = new_stop
    pos.agent_status = "TRAIL_STOP"
    if moved:
        pos.trail_step += 1
        if engine.root is not None:
            append_model_log(
                engine.root,
                {
                    "event": "TRAIL_STOP",
                    "book_id": pos.book_id,
                    "trade_id": pos.trade_id,
                    "status": "TRAIL_STOP",
                    "reason": reason,
                    "trail_step": pos.trail_step,
                    "stop": pos.stop,
                    "band": band,
                    "breakeven": be,
                    "ltp": px,
                    "ts": int(ts),
                    "hypothesis": "filled_soft_cancel_trails_sl",
                    "note": "PAPER: soft CANCEL trails stop; STOP/TIME/FLATTEN/ADVERSE still flatten",
                },
            )
    return True


def apply_target_lock_shift(
    engine: "BookEngine",
    pos: OpenPaper,
    *,
    ltp: float,
    ts: int,
    classified: Optional[dict[str, Any]] = None,
    idx_volume: Optional[float] = None,
    prev_idx_volume: Optional[float] = None,
) -> bool:
    """Optional T1 lock+T2. Default off: first TARGET flattens. Trail SL is separate. PAPER."""
    if not getattr(engine, "apply_target_shift", False):
        return False
    if not pos.filled:
        return False
    if int(pos.target_step) >= TARGET_STEP_MAX:
        return False
    px = float(ltp)
    old_target = float(pos.target)
    if px + 1e-9 < old_target:
        pos.target_touch_ts = None
        return False
    if pos.target_touch_ts is None:
        pos.target_touch_ts = int(ts)
        return True
    if int(ts) - int(pos.target_touch_ts) < int(T1_CONFIRM_SECONDS):
        return True
    band = trail_premium_band(
        classified,
        idx_volume=idx_volume,
        prev_idx_volume=prev_idx_volume,
        side=pos.side,
        underlying=pos.underlying,
    )
    be = breakeven_premium(entry=float(pos.entry), qty=pos.qty)
    orig_stop = float(pos.path_stop) if pos.path_stop is not None else float(pos.stop)
    lock = max(float(pos.stop), be, old_target - band)
    cover = covering_label(classified, pos.side)
    if cover == "SHORT_COVER":
        lock = max(lock, be)
    if lock >= px - 0.25:
        lock = max(float(pos.stop), min(be, px - band))
    if lock >= px - 0.25:
        return False
    reward = max(old_target - float(pos.entry), band)
    nxt = old_target + max(band, 0.5 * reward)
    if cover == "SHORT_COVER":
        nxt = old_target + max(band * 1.5, reward)
    risk_open = max(float(pos.entry) - orig_stop, band)
    cap = float(pos.entry) + risk_open * float(engine.max_target_r)
    nxt = min(nxt, max(cap, old_target + band))
    if nxt <= old_target + 1e-9:
        nxt = old_target + band
    pos.stop = round(lock, 4)
    pos.target = round(float(nxt), 4)
    pos.target_step += 1
    pos.trail_step += 1
    pos.agent_status = f"TARGET_STEP_{pos.target_step}"
    if engine.root is not None:
        append_model_log(
            engine.root,
            {
                "event": "TARGET_LOCK_SHIFT",
                "book_id": pos.book_id,
                "trade_id": pos.trade_id,
                "status": pos.agent_status,
                "target_step": pos.target_step,
                "stop": pos.stop,
                "target": pos.target,
                "old_target": old_target,
                "breakeven": be,
                "band": band,
                "ltp": px,
                "ts": int(ts),
                "hypothesis": "target_hit_lock_be_shift",
                "note": "PAPER: do not flatten on first target; lock SL (BE/charges or old target) and extend",
            },
        )
    return True


def greeks_paper_adjust(
    *,
    entry: float,
    stop_frac: float,
    target_frac: float,
    delta: Optional[float] = None,
    gamma: Optional[float] = None,
    theta: Optional[float] = None,
    iv: Optional[float] = None,
    classified: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Paper-only overlay from QUANT books. Missing greeks → no skip, no invent."""
    notes: list[str] = []
    if delta is not None and abs(float(delta)) < DELTA_SKIP_BELOW:
        return {
            "skip": True,
            "reason": "DELTA_TOO_LOW",
            "stop_frac": stop_frac,
            "target_frac": target_frac,
            "notes": [f"|delta|={delta} < {DELTA_SKIP_BELOW} (HAUS ~40d adverse)"],
        }
    rr = regime_rr_adjust(classified, stop_frac=stop_frac, target_frac=target_frac)
    sf = float(rr["stop_frac"])
    tf = float(rr["target_frac"])
    notes.extend(list(rr.get("notes") or []))
    if iv is not None and float(iv) >= 25.0:
        sf = min(0.55, sf * 1.15)
        notes.append(f"IV={iv}: wider paper STOP only — must not widen target")
    # IV never multiplies target_frac. Theta may tighten target; never 3–4× it.
    if theta is not None and entry > 0 and abs(float(theta)) / float(entry) >= 0.05:
        tf = max(0.28, min(tf, tf * 0.85))
        notes.append("theta/entry high: closer target (Natenberg long premium pays theta)")
    if gamma is not None and float(gamma) >= 0.01 and entry > 0:
        sf = min(0.55, sf * 1.08)
        notes.append("gamma present: slightly wider path stop (faster premium vs index)")
    return {"skip": False, "reason": None, "stop_frac": sf, "target_frac": tf, "notes": notes}


def feasibility_long(*, entry: float, stop: float, target: float, typical_range: float) -> dict[str, Any]:
    if evaluate_long_premium is None:
        return {
            "ok": False,
            "action": "HOLD",
            "reason_code": "DATA_INSUFFICIENT",
            "note": "warehouse.feasibility not importable",
        }
    dec = evaluate_long_premium(
        entry=entry,
        stop=stop,
        target=target,
        stage="EARLY",
        typical_premium_range=typical_range,
    )
    return dec.to_dict()


def same_contract_premium_path(entry: float, premiums: Sequence[float]) -> list[float]:
    """Drop index-sized leaks and other-strike premiums so typical ≠ 74300 path."""
    out: list[float] = []
    try:
        e = float(entry)
    except (TypeError, ValueError):
        return []
    if e <= 0:
        return []
    lo, hi = e * 0.35, e * 2.2
    for raw in premiums:
        if raw is None:
            continue
        try:
            v = float(raw)
        except (TypeError, ValueError):
            continue
        if v <= 0 or v >= INDEX_LIKE_PREMIUM:
            continue
        if v < lo or v > hi:
            continue
        out.append(v)
    if len(out) < 2:
        return [e, e * 1.01]
    return out


def path_typical_range(entry: float, premiums: Sequence[float]) -> float:
    path = same_contract_premium_path(entry, premiums)
    typical = max(path) - min(path)
    if typical <= 0:
        typical = max(0.5, float(entry) * 0.04)
    cap = max(0.5, float(entry) * MAX_TYPICAL_VS_ENTRY)
    return min(typical, cap)


def close_to_close_atr(closes: Sequence[float], n: int = 14) -> float:
    """1m LTP-tape ATR proxy in premium points. Not exchange true-range. PAPER."""
    vals: list[float] = []
    for raw in closes:
        try:
            v = float(raw)
        except (TypeError, ValueError):
            continue
        if v > 0:
            vals.append(v)
    if len(vals) < 3:
        return 0.0
    diffs = [abs(vals[i] - vals[i - 1]) for i in range(1, len(vals))]
    w = diffs[-max(1, int(n)) :]
    return float(sum(w) / len(w)) if w else 0.0


def dynamic_rr(underlying: str, classified: Optional[dict[str, Any]] = None) -> tuple[float, str]:
    """R:R in premium points. Not a fixed 1:2. PAPER HYPOTHESIS."""
    und = str(underlying or "NIFTY").upper()
    p = INDEX_POINT_PROFILES.get(und) or INDEX_POINT_PROFILES["NIFTY"]
    cl = classified or {}
    sr = cl.get("sr") if isinstance(cl.get("sr"), dict) else {}
    trap = str(cl.get("last3_trap") or "")
    near_sr = bool(sr.get("near") or trap in {"sr_false_break", "pdl_bounce", "pdh_reject"})
    iv = cl.get("iv")
    try:
        iv_f = float(iv) if iv is not None else None
    except (TypeError, ValueError):
        iv_f = None
    er = cl.get("er")
    try:
        er_f = float(er) if er is not None else 0.0
    except (TypeError, ValueError):
        er_f = 0.0
    if cl.get("last3_reason") == "pause_continue" and cl.get("vol_expand"):
        rr, why = float(p["rr_continue"]), "pause_continue"
    elif near_sr:
        rr, why = float(p["rr_sr"]), "near_sr"
    elif str(cl.get("regime") or "") == "TREND" and er_f >= 0.45:
        rr, why = float(p["rr_trend"]), "trend_er"
    else:
        rr, why = float(p["rr_base"]), "base"
    if iv_f is not None and iv_f >= 25.0:
        rr = max(1.15, rr - 0.25)
        why = why + "+iv"
    theta = cl.get("theta")
    try:
        if theta is not None and abs(float(theta)) >= 1.0:
            rr = max(1.15, rr - 0.15)
            why = why + "+theta"
    except (TypeError, ValueError):
        pass
    return round(float(rr), 3), why


def propose_index_point_levels(
    entry: float,
    premiums: Sequence[float],
    *,
    underlying: str,
    classified: Optional[dict[str, Any]] = None,
    limit_discount_frac: float = LIMIT_DISCOUNT_FRAC,
) -> dict[str, Any]:
    """Stop/target in premium points via ATR + fib 0.382/0.618. Display still ₹. PAPER."""
    und = str(underlying).upper()
    base = dict(INDEX_POINT_PROFILES[und])
    extra = classified.get("_profile_override") if isinstance(classified, dict) else None
    if isinstance(extra, dict):
        base.update({k: float(v) for k, v in extra.items() if v is not None})
    prof = base
    typical = path_typical_range(float(entry), premiums)
    path = same_contract_premium_path(float(entry), premiums)
    atr = close_to_close_atr(path)
    if atr <= 1e-9:
        atr = max(typical / 4.0, float(prof["min_stop"]) * 0.5)
    swing = max(typical, 1e-6)
    fib_stop = 0.382 * swing
    fib_t618 = 0.618 * swing
    fib_t1618 = 1.618 * swing
    risk = float(atr) * float(prof["atr_stop_k"])
    risk = max(risk, fib_stop, float(prof["min_stop"]))
    risk = min(risk, float(prof["max_stop"]), float(entry) * 0.35)
    stop = floor_path_stop(entry=float(entry), stop=float(entry) - risk, min_stop=float(prof["min_stop"]))
    risk = max(1e-9, float(entry) - stop)
    rr, rr_why = dynamic_rr(und, classified)
    reward = risk * rr
    cl = classified or {}
    if cl.get("last3_reason") == "pause_continue":
        reward = min(reward, fib_t1618)
    else:
        reward = min(reward, max(fib_t618, risk * float(prof["rr_sr"])))
    try:
        idx_er = float(cl["er"]) if cl.get("er") is not None else None
    except (TypeError, ValueError):
        idx_er = None
    chop_cap = prof.get("chop_target_cap")
    if idx_er is not None and idx_er < float(STALL_TREND_ER) and chop_cap is not None:
        reward = min(reward, float(chop_cap))
        rr_why = str(rr_why) + "+chop_cap"
    target = float(entry) + max(0.05, reward)
    feas = feasibility_long(
        entry=float(entry),
        stop=stop,
        target=target,
        typical_range=max(typical, risk * max(rr, 1.5), atr * 4.0),
    )
    clipped = not bool(feas.get("ok"))
    if clipped:
        stop = floor_path_stop(
            entry=float(entry),
            stop=float(entry) - min(risk, float(prof["max_stop"])),
            min_stop=float(prof["min_stop"]),
        )
        risk = max(1e-9, float(entry) - stop)
        target = float(entry) + min(risk * max(1.15, rr * 0.85), fib_t618, float(entry) * 0.22)
        feas = feasibility_long(
            entry=float(entry),
            stop=stop,
            target=target,
            typical_range=max(typical, risk * 2.0, atr * 4.0),
        )
    disc = max(0.0, min(0.08, float(limit_discount_frac)))
    limit_px = round(float(entry) * (1.0 - disc), 4)
    if limit_px <= 0:
        limit_px = round(float(entry), 4)
    return {
        "ok": True,
        "entry": round(float(entry), 4),
        "signal_ltp": round(float(entry), 4),
        "limit_price": limit_px,
        "stop": round(stop, 4),
        "target": round(target, 4),
        "typical_premium_range": round(typical, 4),
        "premium_atr": round(atr, 4),
        "stop_points": round(risk, 4),
        "target_points": round(float(target) - float(entry), 4),
        "rr": rr,
        "rr_why": rr_why,
        "unit": "premium_points",
        "feasibility": feas,
        "clipped_target": clipped,
        "raw_target": round(target, 4),
        "reason_code": (
            feas.get("reason_code")
            if feas.get("ok") and not clipped
            else ("CLAMPED_PAPER_LEVELS" if feas.get("ok") else feas.get("reason_code") or "TARGET_FEASIBILITY_FAIL")
        ),
        "scalp_hold_bars": SCALP_HOLD_BARS,
        "flatten_ist": "15:16",
    }


def propose_levels(
    entry: float,
    premiums: Sequence[float],
    *,
    stop_frac: float = STOP_FRAC,
    target_frac: float = TARGET_FRAC,
    limit_discount_frac: float = LIMIT_DISCOUNT_FRAC,
    max_target_r: float = MAX_TARGET_R,
    underlying: Optional[str] = None,
    classified: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Scalp stop/target from same-contract premium path. Kills 150/96/250 and 266/219/615.

    Working limit sits below signal LTP so a fill is a cheaper buy — never assumed at signal.
    IV is not an input here; greeks_paper_adjust may widen stop_frac only.
    NIFTY/SENSEX use ATR+fib premium-point profiles (not a shared ₹8 floor).
    """
    if entry is None or entry <= 0:
        return {"ok": False, "reason_code": "DATA_INSUFFICIENT", "data_gaps": ["entry missing"]}
    und = str(underlying or "").upper()
    if und in INDEX_POINT_PROFILES:
        return propose_index_point_levels(
            float(entry),
            premiums,
            underlying=und,
            classified=classified,
            limit_discount_frac=limit_discount_frac,
        )
    typical = path_typical_range(float(entry), premiums)
    stop = entry - float(stop_frac) * typical
    raw_target = entry + float(target_frac) * typical
    if stop <= 0:
        stop = max(0.05, entry * 0.85)
    stop = floor_path_stop(entry=entry, stop=stop)
    risk = max(1e-9, entry - stop)
    max_reward = min(typical, risk * float(max_target_r), entry * 0.22)
    target = entry + min(max(0.05, raw_target - entry), max_reward)
    feas = feasibility_long(entry=entry, stop=stop, target=target, typical_range=typical)
    clipped = False
    if not feas.get("ok"):
        stop = floor_path_stop(
            entry=entry, stop=max(0.05, entry - min(float(stop_frac) * typical, entry * 0.12))
        )
        risk = max(1e-9, entry - stop)
        target = entry + min(typical, risk * float(max_target_r), entry * 0.18)
        feas = feasibility_long(entry=entry, stop=stop, target=target, typical_range=typical)
        clipped = True
    if abs(target - raw_target) > 1e-6:
        clipped = True
    disc = max(0.0, min(0.08, float(limit_discount_frac)))
    limit_px = round(float(entry) * (1.0 - disc), 4)
    if limit_px <= 0:
        limit_px = round(entry, 4)
    return {
        "ok": True,
        "entry": round(entry, 4),
        "signal_ltp": round(entry, 4),
        "limit_price": limit_px,
        "stop": round(stop, 4),
        "target": round(target, 4),
        "typical_premium_range": round(typical, 4),
        "feasibility": feas,
        "clipped_target": clipped,
        "raw_target": round(raw_target, 4),
        "reason_code": (
            feas.get("reason_code")
            if feas.get("ok") and not clipped
            else ("CLAMPED_PAPER_LEVELS" if feas.get("ok") else feas.get("reason_code") or "TARGET_FEASIBILITY_FAIL")
        ),
        "scalp_hold_bars": SCALP_HOLD_BARS,
        "flatten_ist": "15:16",
    }


@dataclass
class OpenPaper:
    book_id: str
    underlying: str
    side: str
    trade_id: str
    entry: float
    stop: float
    target: float
    atm_strike: Optional[float]
    opened_ts: int
    opened_bar: int
    strike_source: str
    limit_price: float = 0.0
    lot_size: Optional[int] = None
    lots: int = 1
    qty: Optional[int] = None
    notional_inr: Optional[float] = None
    capital_inr: float = STARTING_CAPITAL_INR
    lot_status: str = "DATA_INSUFFICIENT"
    filled: bool = False
    last_ltp: Optional[float] = None
    seen_low: Optional[float] = None
    seen_high: Optional[float] = None
    seen_high_ts: Optional[int] = None
    premium_prints: list[float] = field(default_factory=list)
    quote_src: str = ""
    idx_at_open: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    iv: Optional[float] = None
    vega: Optional[float] = None
    greeks_notes: list[str] = field(default_factory=list)
    index_regime: str = "UNKNOWN"
    regime_er: Optional[float] = None
    regime_flip_frac: Optional[float] = None
    regime_reason: Optional[str] = None
    regime_range_over_atr: Optional[float] = None
    regime_rv: Optional[float] = None
    market_kind_open: str = "UNKNOWN"
    target_step: int = 0
    trail_step: int = 0
    agent_status: str = "WORKING_LIMIT"
    cancel_eligible: bool = False
    idx_volume: Optional[float] = None
    last_updated_ts: Optional[int] = None
    path_stop: Optional[float] = None
    target_touch_ts: Optional[int] = None
    justification: str = ""
    model_names: list[str] = field(default_factory=list)
    opened_minute_key: Optional[str] = None
    wing_bar_key: Optional[str] = None
    wing_bar_high: Optional[float] = None
    wing_bar_close: Optional[float] = None
    closed_wing_bars: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BookEngine:
    opens: dict[tuple[str, str], OpenPaper] = field(default_factory=dict)
    closed: list[dict[str, Any]] = field(default_factory=list)
    skips: list[dict[str, Any]] = field(default_factory=list)
    last_step: dict[str, Any] = field(default_factory=dict)
    equity: dict[str, float] = field(default_factory=dict)
    lot_by_und: dict[str, tuple[Optional[int], str]] = field(default_factory=dict)
    root: Optional[Path] = None
    deny_model_signals: bool = True
    starting_capital: float = STARTING_CAPITAL_INR
    paper_stop_frac: float = STOP_FRAC
    paper_target_frac: float = TARGET_FRAC
    paper_hold_bars: int = SCALP_HOLD_BARS
    paper_give_up_frac: float = GIVE_UP_FRAC
    skip_new_when_sideways: bool = True
    paper_add_lot: bool = PAPER_ADD_LOT
    paper_min_lots: int = PAPER_MIN_LOTS
    paper_target_lots: int = PAPER_TARGET_LOTS
    paper_max_lots: int = PAPER_MAX_LOTS
    max_target_r: float = MAX_TARGET_R
    skip_trend_against: bool = True
    limit_discount_frac: float = LIMIT_DISCOUNT_FRAC
    capital_by_book: dict[str, float] = field(default_factory=dict)
    capital_plan: dict[str, Any] = field(default_factory=dict)
    regime_lookback: int = REGIME_LOOKBACK
    regime_er_max: float = REGIME_ER_MAX
    regime_flip_min: float = REGIME_FLIP_MIN
    regime_range_atr_max: float = REGIME_RANGE_ATR_MAX
    last_regime: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_step_by_und: dict[str, dict[str, Any]] = field(default_factory=dict)
    regime_book_counts: dict[str, int] = field(default_factory=dict)
    itm_bins: dict[str, dict[str, Any]] = field(default_factory=dict)
    sr_levels: dict[str, dict[str, Any]] = field(default_factory=dict)
    impulse_pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    skip_bn_unless_last3: bool = True
    apply_impulse_pause: bool = True
    apply_target_shift: bool = False  # founder: strict first target; trail SL only until then
    skip_banknifty: bool = False  # founder desk START/STOP is the index gate
    skip_sensex: bool = False  # NIFTY-only paper via params; do not mix unique P/L with SENSEX
    sensex_need_strength: bool = True  # SENSEX: continuation or short-cover, not every bin tick
    sensex_no_pause_wait: bool = True  # SENSEX last-3 confirm without extra pause (NIFTY still waits)
    nifty_need_strength: bool = False
    nifty_cover_closed_1m: bool = True  # live paper Joint #2. 10s cover is WATCH. NO_PROMOTE.
    nifty_bin_only: bool = False  # never let last-3 override the ITM bin on NIFTY
    nifty_allow_sides: Optional[tuple[str, ...]] = None  # e.g. ("PE",)
    nifty_min_abs_delta: Optional[float] = None
    no_new_after_minutes: Optional[int] = None
    nifty_no_flip_minutes: Optional[int] = None
    nifty_no_pause_wait: bool = False  # last-3 without extra pause (SENSEX-style)
    nifty_align_impulse: bool = False  # skip CE on last-3 DOWN / PE on last-3 UP
    nifty_skip_side_after_stop: bool = False  # do not rebuy a wing that already STOP'd today
    nifty_skip_ce_after_stop: bool = False  # CE-only: do not rebuy CE after a CE STOP
    nifty_max_filled_per_book: Optional[int] = None
    nifty_halt_after_stops: Optional[int] = None  # session STOP count on MIX-DEFAULT-BUY then skip NEW
    last_exit_by_und: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_stop_side_by_und: dict[str, dict[str, int]] = field(default_factory=dict)
    session_stop_count: dict[str, int] = field(default_factory=dict)
    session_open_idx: dict[str, float] = field(default_factory=dict)
    nifty_session_lean: bool = False  # after 10:30, PE if idx < open else CE
    point_profile_overrides: dict[str, dict[str, float]] = field(default_factory=dict)
    last_1m_close: dict[str, Triple] = field(default_factory=dict)
    prev_1m_close: dict[str, Triple] = field(default_factory=dict)
    observer_review: dict[str, dict[str, Any]] = field(default_factory=dict)
    observer_by_book: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    observer_veto_fills: bool = True  # fill-path family; ATM/DI = PASS
    sod_one_ticket: bool = True  # locked product: votes → picker → observer → one desk ticket
    picker_majority: bool = True  # RULES majority; implied by sod_one_ticket
    signal_log: list[dict[str, Any]] = field(default_factory=list)  # logit/XR/greeks vs picker even on VETO
    exam_events: list[dict[str, Any]] = field(default_factory=list)  # 06 honesty exam; not a fill
    hold_trending_open_stall: bool = False  # write=false A/B only. Default off. NO_PROMOTE.

    def book_capital(self, book_id: str) -> float:
        if book_id in self.capital_by_book:
            return float(self.capital_by_book[book_id])
        return float(self.starting_capital)

    def book_equity(self, book_id: str) -> float:
        return float(self.equity.setdefault(book_id, self.book_capital(book_id)))

    def has_open(self, book_id: str, underlying: str) -> bool:
        return (book_id, underlying) in self.opens

    def has_working_underlying(self, underlying: str) -> bool:
        und = str(underlying).upper()
        return any(u == und for (_book, u) in self.opens.keys())

    def bump_regime_book(self, book_id: str, regime: str, action: str) -> None:
        """HYPOTHESIS recon counter. KMeans is not a CE/PE model — still counted as SKIP."""
        key = f"{regime}|{book_id}|{action}"
        self.regime_book_counts[key] = int(self.regime_book_counts.get(key) or 0) + 1

    def mark_skip(self, book_id: str, underlying: str, reason: str, **extra: Any) -> None:
        classified = self.last_regime.get(str(underlying).upper()) or {}
        regime = str(extra.get("index_regime") or classified.get("regime") or "UNKNOWN")
        self.bump_regime_book(book_id, regime, f"SKIP:{reason}")
        self.skips.append(
            {
                "book_id": book_id,
                "underlying": underlying,
                "action": "SKIP",
                "reason": reason,
                **extra,
            }
        )


def dealer_side(
    index_delta: Optional[float],
    ce_delta: Optional[float],
    pe_delta: Optional[float],
    *,
    underlying: str = "NIFTY",
) -> dict[str, Any]:
    """FOLLOWS analyst (MIX-FORM-FOLLOWS / judge_tick). Vote only — not desk fill."""
    if judge_tick is None:
        return {"side": None, "verdict": "DATA_INSUFFICIENT", "case": "NO_FOLLOWS"}
    note = judge_tick(
        underlying=underlying,
        index_delta=index_delta,
        ce_delta=ce_delta,
        pe_delta=pe_delta,
        paper_train=True,
    )
    side = None
    if note.verdict == "BUY_CE_CONFIRM":
        side = "CE"
    elif note.verdict == "BUY_PE_CONFIRM":
        side = "PE"
    return {
        "side": side,
        "verdict": note.verdict,
        "case": note.case,
        "allow_new_paper_ce_pe": note.allow_new_paper_ce_pe,
        "dealer_note": note.dealer_note,
        "extra": note.extra,
    }


def _sma(vals: Sequence[float], n: int) -> Optional[float]:
    if len(vals) < n:
        return None
    chunk = vals[-n:]
    return sum(chunk) / n


def tv_ep_024_side(idx_closes: Sequence[float]) -> Optional[str]:
    sma20 = _sma(list(idx_closes), 20)
    if sma20 is None:
        return None
    last = float(idx_closes[-1])
    if last > sma20:
        return "CE"
    if last < sma20:
        return "PE"
    return None


def paper_hit_rate(pnls: Sequence[float]) -> Optional[float]:
    """Closed-paper hit rate: share of realized_pnl > 0. Not a live claim. NO_PROMOTE."""
    if not pnls:
        return None
    wins = sum(1 for p in pnls if float(p) > 0)
    return round(wins / len(pnls), 4)


def paper_hit_rate_pct(pnls: Sequence[float]) -> Optional[float]:
    rate = paper_hit_rate(pnls)
    if rate is None:
        return None
    return round(rate * 100.0, 2)


def append_model_log(root: Path, rec: dict[str, Any]) -> None:
    path = root / "data" / "recon" / LOG_JSONL_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {**rec, "ts_ist": datetime.now(IST).isoformat(timespec="seconds")}
    rec.setdefault("trade_id", rec.get("trade_id"))
    rec.setdefault("book_id", rec.get("model") or rec.get("book_id"))
    rec.setdefault("status", rec.get("status"))
    rec.setdefault("target_step", rec.get("target_step"))
    rec.setdefault("filled", rec.get("filled"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def human_override_path(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / "data" / "recon" / HUMAN_OVERRIDE_NAME


def load_human_override(root: Optional[Path] = None) -> dict[str, Any]:
    path = human_override_path(root)
    if not path.is_file():
        return {"ok": True, "active": False, "orders": "REFUSED", "promote": False}
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "active": False, "orders": "REFUSED", "promote": False}
    if not isinstance(blob, dict):
        return {"ok": False, "active": False, "orders": "REFUSED", "promote": False}
    blob.setdefault("ok", True)
    blob.setdefault("orders", "REFUSED")
    blob.setdefault("promote", False)
    blob["active"] = bool(blob.get("active", True))
    return blob


def _human_px(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if not (v > 0) or v != v:
        return None
    return round(v, 4)


def save_human_override(body: dict[str, Any], *, root: Optional[Path] = None) -> dict[str, Any]:
    """Paper-only human instruction. Naked EXIT on an open fill is refused.

    Filled tickets: SET_LEVELS / MANAGE with required target + stop.
    Unfilled working limits: CANCEL. CLEAR drops the instruction.
    Live broker orders stay REFUSED.
    """
    body = body if isinstance(body, dict) else {}
    action = str(body.get("action") or "").upper().replace("-", "_").replace(" ", "_")
    if action in {"SET_TARGET_STOP", "MANAGE", "MANAGE_TRADE", "SET_LEVELS", "OVERRIDE"}:
        action = "SET_LEVELS"
    target = _human_px(body.get("target"))
    stop = _human_px(body.get("stop"))
    if action == "EXIT" and target is not None and stop is not None:
        action = "SET_LEVELS"
    allowed = {"SET_LEVELS", "CANCEL", "CLEAR"}
    if action not in allowed:
        return {
            "ok": False,
            "active": False,
            "action": action or "EXIT",
            "error": "HUMAN_LEVELS_REQUIRED",
            "trade_id": body.get("trade_id"),
            "underlying": str(body.get("underlying") or "").upper() or None,
            "side": str(body.get("side") or "").upper() or None,
            "reason": "HUMAN_PRIORITY",
            "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
            "orders": "REFUSED",
            "promote": False,
            "note": (
                "Naked EXIT refused. Ask the human for TARGET and STOP, confirm, "
                "then apply paper SET_LEVELS. No live broker order."
            ),
        }
    if action == "SET_LEVELS":
        if target is None or stop is None:
            return {
                "ok": False,
                "active": False,
                "action": "SET_LEVELS",
                "error": "HUMAN_LEVELS_REQUIRED",
                "trade_id": body.get("trade_id"),
                "underlying": str(body.get("underlying") or "").upper() or None,
                "side": str(body.get("side") or "").upper() or None,
                "reason": "HUMAN_PRIORITY",
                "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
                "orders": "REFUSED",
                "promote": False,
                "note": "Target and stop are required. Immediate flatten is refused.",
            }
        if not (target > stop):
            return {
                "ok": False,
                "active": False,
                "action": "SET_LEVELS",
                "error": "LEVELS_ORDER",
                "target": target,
                "stop": stop,
                "trade_id": body.get("trade_id"),
                "underlying": str(body.get("underlying") or "").upper() or None,
                "side": str(body.get("side") or "").upper() or None,
                "reason": "HUMAN_PRIORITY",
                "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
                "orders": "REFUSED",
                "promote": False,
                "note": "Long premium: target must be above stop.",
            }
    payload = {
        "ok": True,
        "active": action != "CLEAR",
        "action": action,
        "trade_id": body.get("trade_id"),
        "underlying": str(body.get("underlying") or "").upper() or None,
        "side": str(body.get("side") or "").upper() or None,
        "target": target,
        "stop": stop,
        "reason": "HUMAN_PRIORITY",
        "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
        "orders": "REFUSED",
        "promote": False,
        "note": (
            "Human paper SET_LEVELS (target+stop). Highest priority over boss/desk. "
            "No live broker order."
            if action == "SET_LEVELS"
            else "Human-in-loop paper override. Highest priority over boss/desk for open paper tickets."
        ),
    }
    path = human_override_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def resample_closes_3m(closes: dict[int, float]) -> list[Any]:
    """3m INDEX bars from 1m closes. Does not fabricate missing days."""
    try:
        from backtest_engine.indicators import Bar
    except ImportError:
        return []
    buckets: dict[int, list[tuple[int, float]]] = {}
    for ts, close in sorted(closes.items()):
        key = int(ts) - (int(ts) % 180)
        buckets.setdefault(key, []).append((int(ts), float(close)))
    bars = []
    for key in sorted(buckets):
        grp = buckets[key]
        cs = [c for _, c in grp]
        bars.append(
            Bar(
                ts=grp[-1][0],
                open=float(cs[0]),
                high=float(max(cs)),
                low=float(min(cs)),
                close=float(cs[-1]),
                volume=0.0,
            )
        )
    return bars


def resample_index_3m(triples: Sequence[Triple]) -> list[Any]:
    """3m INDEX bars from 1m triples. Does not fabricate missing days."""
    return resample_closes_3m({int(t.ts): float(t.idx_close) for t in triples})


def logit_side_series(
    triples: Sequence[Triple],
    *,
    index_closes: Optional[dict[int, float]] = None,
    xr: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Walk-forward INDEX 3m logit. Train on INDEX history *before* the ATM session."""
    thin = {
        "side": None,
        "status": "DATA_INSUFFICIENT",
        "reason": "INDEX 3m train < 200 labeled rows before session (no fabricate)",
        "n_3m": 0,
    }
    if not triples:
        return [], {"n_3m": 0, "n_index_1m": 0}
    closes = dict(index_closes or {})
    for t in triples:
        closes.setdefault(int(t.ts), float(t.idx_close))
    bars = resample_closes_3m(closes)
    meta: dict[str, Any] = {"n_3m": len(bars), "n_index_1m": len(closes)}
    if len(bars) < 40:
        meta["status"] = "DATA_INSUFFICIENT"
        return [{**thin, "n_3m": len(bars)} for _ in triples], meta
    try:
        from backtest_engine.ml_leans import lean_ml_logit
        from backtest_engine.patterns import lean_range_exp
    except ImportError:
        meta["status"] = "DATA_INSUFFICIENT"
        reason = "backtest_engine.ml_leans not importable"
        return [{**thin, "reason": reason, "n_3m": len(bars)} for _ in triples], meta
    train_end = int(triples[0].ts)
    meta["train_end_ts"] = train_end
    leans = lean_ml_logit(bars, train_end_ts=train_end)
    xr_leans = lean_range_exp(bars) if xr else None
    labeled_before = sum(1 for bar in bars if bar.ts < train_end)
    meta["n_train_3m_bars_before_session"] = labeled_before
    out: list[dict[str, Any]] = []
    last_logit = "SKIP"
    last_xr = "SKIP"
    last_sess: Optional[str] = None
    bi = 0
    for t in triples:
        sess = ist_calendar_date(int(t.ts))
        if last_sess is not None and sess != last_sess:
            last_logit = "SKIP"
            last_xr = "SKIP"
        last_sess = sess
        while bi < len(bars) and bars[bi].ts <= int(t.ts):
            if ist_calendar_date(int(bars[bi].ts)) == sess:
                last_logit = leans[bi]
                if xr_leans is not None:
                    last_xr = xr_leans[bi]
            bi += 1
        if xr:
            if last_logit in {"CE", "PE"} and last_logit == last_xr:
                out.append(
                    {
                        "side": last_logit,
                        "status": "OK",
                        "n_3m": len(bars),
                        "train_end_ts": train_end,
                    }
                )
            else:
                out.append(
                    {
                        "side": None,
                        "status": "SKIP",
                        "reason": f"XR filter logit={last_logit} range={last_xr}",
                        "n_3m": len(bars),
                        "train_end_ts": train_end,
                    }
                )
            continue
        if last_logit in {"CE", "PE"}:
            out.append(
                {
                    "side": last_logit,
                    "status": "OK",
                    "n_3m": len(bars),
                    "train_end_ts": train_end,
                }
            )
        else:
            out.append(
                {
                    "side": None,
                    "status": "DATA_INSUFFICIENT" if last_logit == "SKIP" else "SKIP",
                    "reason": (
                        "lean_ml_logit SKIP (needs ≥200 labeled 3m train rows before cutoff; "
                        "label is next INDEX close, not premium)"
                    ),
                    "n_3m": len(bars),
                    "train_end_ts": train_end,
                }
            )
    meta["status"] = "OK" if any(r.get("side") in {"CE", "PE"} for r in out) else "DATA_INSUFFICIENT"
    return out, meta


def logit_last_side(triples: Sequence[Triple], *, xr: bool = False) -> dict[str, Any]:
    series, meta = logit_side_series(triples, xr=xr)
    if series:
        return {**series[-1], **{k: v for k, v in meta.items() if k not in series[-1]}}
    return {
        "side": None,
        "status": "DATA_INSUFFICIENT",
        "reason": "no triples",
        "n_3m": meta.get("n_3m", 0),
    }


def ml1_meta_label(closed: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """AFML-style take/skip. Needs closed paper labels; else DATA_INSUFFICIENT."""
    labeled = [c for c in closed if c.get("realized_pnl") is not None]
    if len(labeled) < 30:
        return {
            "take": None,
            "status": "DATA_INSUFFICIENT",
            "reason": f"ML-1 meta-label needs ≥30 closed paper rows; have {len(labeled)}",
        }
    pnls = [float(c["realized_pnl"]) for c in labeled]
    rate = paper_hit_rate(pnls)
    take = rate is not None and rate >= 0.5
    return {
        "take": take,
        "status": "OK",
        "n_labels": len(labeled),
        "win_rate": rate,
        "win_rate_kind": "paper_closed_premium_gt_0",
        "promote": False,
    }


def _greeks_cancel_reason(
    *,
    side: str,
    entry: float,
    live: dict[str, Optional[float]],
    minutes: int,
    session_iv: Optional[float],
    wing_iv_list: Optional[Sequence[float]] = None,
    filled: bool,
) -> Optional[str]:
    """Cancel if Dhan greeks say the long-premium thesis died. Missing greeks → no invent."""
    if live.get("delta") is None and live.get("iv") is None and live.get("theta") is None:
        return None
    scored = score_greeks_ticket(
        side=side,
        entry=entry,
        delta=live.get("delta"),
        gamma=live.get("gamma"),
        theta=live.get("theta"),
        iv=live.get("iv"),
        session_iv=session_iv,
        minutes_ist=minutes,
        wing_iv_list=wing_iv_list,
    )
    if scored.get("take"):
        return None
    reason = str(scored.get("reason") or "")
    if reason in {"DELTA_TOO_LOW", "DELTA_OTM_BAND", "IV_RICH_ABS", "IV_RICH_VS_SESSION", "THETA_LATE_BLEED"}:
        prefix = "CANCEL_GREEKS" if filled else "CANCEL_UNFILLED_GREEKS"
        return f"{prefix}_{reason}"
    return None


def _unfilled_reason(
    pos: OpenPaper,
    ltp: float,
    ts: int,
    bar_i: int,
    *,
    side_low: Optional[float] = None,
    dealer_verdict: Optional[str] = None,
    live_delta: Optional[float] = None,
    live_greeks: Optional[dict[str, Optional[float]]] = None,
    index_ltp: Optional[float] = None,
    session_iv: Optional[float] = None,
    wing_iv_list: Optional[Sequence[float]] = None,
    index_regime: Optional[str] = None,
) -> Optional[str]:
    """Working buy limit. Do not assume a fill. Cancel if the candle walked away."""
    px = float(ltp)
    low = float(side_low) if side_low is not None else px
    if pos.seen_low is not None:
        touch = min(px, low, float(pos.seen_low))
    else:
        touch = min(px, low)
    limit = float(pos.limit_price or pos.entry)
    if touch <= limit + 1e-9:
        return "FILL"
    if px >= limit * (1.0 + FILL_AWAY_FRAC):
        return "CANCEL_UNFILLED_AWAY"
    if int(ts) - int(pos.opened_ts) >= UNFILLED_SECONDS:
        return "CANCEL_UNFILLED_TIMEOUT"
    verdict = str(dealer_verdict or "")
    if pos.side == "CE" and verdict == "BUY_PE_CONFIRM":
        return "CANCEL_UNFILLED_THESIS"
    if pos.side == "PE" and verdict == "BUY_CE_CONFIRM":
        return "CANCEL_UNFILLED_THESIS"
    if live_delta is not None and abs(float(live_delta)) < DELTA_SKIP_BELOW:
        return "CANCEL_UNFILLED_DELTA"
    if str(index_regime or "") == "SIDEWAYS":
        return "CANCEL_UNFILLED_SIDEWAYS"
    if str(index_regime or "") == "UNKNOWN":
        return "CANCEL_UNFILLED_REGIME_WAIT"
    g_dead = _greeks_cancel_reason(
        side=pos.side,
        entry=float(pos.limit_price or pos.entry),
        live=live_greeks or {"delta": live_delta},
        minutes=minutes_ist(ts),
        session_iv=session_iv,
        wing_iv_list=wing_iv_list,
        filled=False,
    )
    if g_dead:
        return g_dead
    if pos.idx_at_open is not None and index_ltp is not None:
        step = STRIKE_STEP.get(pos.underlying.upper(), 50.0)
        moved = float(index_ltp) - float(pos.idx_at_open)
        if pos.side == "CE" and moved <= -0.5 * step:
            return "CANCEL_UNFILLED_INDEX"
        if pos.side == "PE" and moved >= 0.5 * step:
            return "CANCEL_UNFILLED_INDEX"
    if minutes_ist(ts) >= FLATTEN_MINUTES_IST:
        return "CANCEL_UNFILLED_FLAT"
    return None


def _kaufman_er(closes: Sequence[float]) -> Optional[float]:
    vals = [float(x) for x in closes if x is not None]
    if len(vals) < 8:
        return None
    diffs = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    path = sum(abs(d) for d in diffs)
    net = abs(vals[-1] - vals[0])
    if path <= 1e-9:
        return 0.0
    return float(net / path)


def _target_progress(pos: OpenPaper, peak: Optional[float]) -> Optional[float]:
    try:
        entry = float(pos.entry)
        target = float(pos.target)
        hi = float(peak) if peak is not None else None
    except (TypeError, ValueError):
        return None
    if hi is None:
        return None
    span = target - entry
    if span <= 1e-9:
        return None
    return float((hi - entry) / span)


def _index_is_chop(classified: Optional[dict[str, Any]]) -> bool:
    """INDEX Kaufman ER, not itm_bin TREND. Missing ER is not assumed chop."""
    cl = classified or {}
    try:
        er = cl.get("er")
        if er is None:
            return False
        return float(er) < float(STALL_TREND_ER)
    except (TypeError, ValueError):
        return False


def market_kind(classified: Optional[dict[str, Any]] = None, *, require_er: bool = False) -> str:
    """Diagnostic tape label. Not an exit rule. INDEX path, not itm_bin TREND.

    TRENDING = efficient (ER≥0.35). VOLATILE = wide range / high RV but not efficient.
    CHOPPY = low ER + flips. SIDEWAYS = low ER, quiet band.
    Fill/close stamps use require_er=True: missing ER → UNKNOWN (itm_bin TREND is ignored).
    """
    cl = classified or {}
    try:
        er = float(cl["er"]) if cl.get("er") is not None else None
    except (TypeError, ValueError):
        er = None
    if require_er and er is None:
        return "UNKNOWN"
    try:
        flip = float(cl["flip_frac"]) if cl.get("flip_frac") is not None else None
    except (TypeError, ValueError):
        flip = None
    try:
        roa = float(cl["range_over_atr"]) if cl.get("range_over_atr") is not None else None
    except (TypeError, ValueError):
        roa = None
    try:
        rv = float(cl["realized_vol"]) if cl.get("realized_vol") is not None else None
    except (TypeError, ValueError):
        rv = None
    if er is not None and er >= float(STALL_TREND_ER):
        return "TRENDING"
    wide = (roa is not None and roa >= 5.0) or (rv is not None and rv >= float(REGIME_RV_WIDEN))
    if wide:
        return "VOLATILE"
    if er is not None and er < float(STALL_TREND_ER) and flip is not None and flip >= float(REGIME_FLIP_MIN):
        return "CHOPPY"
    if er is not None and er < float(STALL_TREND_ER):
        return "SIDEWAYS"
    return "UNKNOWN"


def market_kind_from_row(row: dict[str, Any], *, at: str = "open") -> str:
    """Fill kind = open ER. Exit kind = close ER. Missing ER → UNKNOWN."""
    stamped = row.get("market_kind_open") if at == "open" else row.get("market_kind_close")
    if stamped:
        return str(stamped)
    if at == "close":
        return market_kind(
            {
                "er": row.get("regime_er_close"),
                "flip_frac": row.get("regime_flip_frac_close"),
                "range_over_atr": row.get("regime_range_over_atr_close"),
                "realized_vol": row.get("regime_rv_close"),
            },
            require_er=True,
        )
    return market_kind(
        {
            "er": row.get("regime_er"),
            "flip_frac": row.get("regime_flip_frac"),
            "range_over_atr": row.get("regime_range_over_atr"),
            "realized_vol": row.get("regime_rv"),
        },
        require_er=True,
    )


def _trend_continuation(
    pos: OpenPaper,
    *,
    classified: Optional[dict[str, Any]] = None,
) -> bool:
    """True TREND pause on the *same wing*. Chop + 55% of a wide target is not a hold."""
    cl = classified or {}
    if int(getattr(pos, "target_step", 0) or 0) >= 1:
        return True
    chop = _index_is_chop(cl)
    progress = _target_progress(pos, getattr(pos, "seen_high", None))
    if (
        (not chop)
        and progress is not None
        and progress >= float(STALL_TARGET_PROGRESS)
    ):
        return True
    side = str(pos.side or "").upper()
    raw = cl.get("last3_impulse_raw")
    impulse = cl.get("last3_impulse")
    if (side == "PE" and (impulse == "UP" or raw == "UP")) or (
        side == "CE" and (impulse == "DOWN" or raw == "DOWN")
    ):
        return False
    idx_dir = cl.get("index_direction") or cl.get("direction")
    try:
        er = cl.get("er")
        if er is not None and float(er) >= float(STALL_TREND_ER):
            if side == "PE" and idx_dir == "UP":
                return False
            if side == "CE" and idx_dir == "DOWN":
                return False
            if side == "PE" and (impulse == "DOWN" or raw == "DOWN" or idx_dir == "DOWN"):
                return True
            if side == "CE" and (impulse == "UP" or raw == "UP" or idx_dir == "UP"):
                return True
            return False
    except (TypeError, ValueError):
        pass
    if side == "CE" and impulse == "UP":
        return True
    if side == "PE" and impulse == "DOWN":
        return True
    if cl.get("vol_expand") is True and (
        (side == "CE" and impulse == "UP") or (side == "PE" and impulse == "DOWN")
    ):
        return True
    return False


def _ist_minute_key(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=IST).strftime("%Y-%m-%dT%H:%M")


def note_filled_wing_1m(pos: OpenPaper, ts: int, px: float) -> Optional[dict[str, Any]]:
    """Close the prior IST minute on the booked wing. Entry minute is not a bar."""
    if not pos.filled:
        return None
    try:
        price = float(px)
    except (TypeError, ValueError):
        return None
    key = _ist_minute_key(int(ts))
    opened_key = getattr(pos, "opened_minute_key", None)
    if not opened_key:
        pos.opened_minute_key = _ist_minute_key(int(pos.opened_ts))
        opened_key = pos.opened_minute_key
    cur = getattr(pos, "wing_bar_key", None)
    if cur is None:
        pos.wing_bar_key = key
        pos.wing_bar_high = price
        pos.wing_bar_close = price
        return None
    if key == cur:
        hi = getattr(pos, "wing_bar_high", None)
        pos.wing_bar_high = price if hi is None else max(float(hi), price)
        pos.wing_bar_close = price
        return None
    if key < cur:
        return None
    closed = None
    if cur > opened_key:
        try:
            closed = {
                "key": cur,
                "high": float(pos.wing_bar_high),
                "close": float(pos.wing_bar_close),
            }
        except (TypeError, ValueError):
            closed = None
        if closed is not None:
            bars = list(getattr(pos, "closed_wing_bars", None) or [])
            bars.append(closed)
            pos.closed_wing_bars = bars[-16:]
    pos.wing_bar_key = key
    pos.wing_bar_high = price
    pos.wing_bar_close = price
    return closed


def exit_overlay_reason(pos: OpenPaper) -> Optional[str]:
    """Causal closed-1m bleed stop. No clocks. No peek of the live minute."""
    if not pos.filled:
        return None
    if str(getattr(pos, "book_id", "") or "") != "MIX-DEFAULT-BUY":
        return None
    if int(getattr(pos, "target_step", 0) or 0) >= 1:
        return None
    bars = list(getattr(pos, "closed_wing_bars", None) or [])
    if not bars:
        return None
    try:
        entry = float(pos.entry)
        target = float(pos.target)
    except (TypeError, ValueError):
        return None
    mfe = entry
    prev_close: Optional[float] = None
    span = (target - entry) if target > entry else None
    for i, raw in enumerate(bars, start=1):
        try:
            high = float(raw["high"])
            close = float(raw["close"])
        except (TypeError, ValueError, KeyError):
            continue
        mfe = max(mfe, high)
        if i >= int(EXIT_NO_PROG_BARS) and (mfe - entry) < float(EXIT_NO_PROG_MFE):
            return CANCEL_NO_PROGRESS
        if (
            span
            and span > 0
            and (mfe - entry) >= float(EXIT_BOOK_NEAR_FRAC) * span
            and prev_close is not None
            and close < prev_close
        ):
            return CANCEL_BOOK_NEAR
        prev_close = close
    return None


def stall_book_reason(
    pos: OpenPaper,
    ltp: float,
    ts: int,
    *,
    classified: Optional[dict[str, Any]] = None,
    idx_volume: Optional[float] = None,
    prev_idx_volume: Optional[float] = None,
    hold_trending_open_stall: bool = False,
) -> Optional[str]:
    """Book a dead long-premium when the high is stale and the path is inefficient.

    HYPOTHESIS overlay. Not a 9-minute clock. Chop (INDEX ER < 0.35) books
    earlier: 8m age, 3m stale high, or ≥40% of target then fade. True TREND
    continuation (same-wing ER ≥ 0.35) still vetoes.
    write=false A/B: hold_trending_open_stall skips STALL when the ticket
    opened in TRENDING. Default off. NO_PROMOTE — not the live book.
    """
    if not pos.filled:
        return None
    if int(getattr(pos, "target_step", 0) or 0) >= 1:
        return None
    if hold_trending_open_stall and str(getattr(pos, "market_kind_open", "") or "").upper() == "TRENDING":
        return None
    cl = classified or {}
    chop = _index_is_chop(cl)
    min_sec = int(STALL_MIN_SEC_CHOP if chop else STALL_MIN_SEC)
    stale_sec = int(STALL_HIGH_STALE_CHOP if chop else STALL_HIGH_STALE_SEC)
    age = int(ts) - int(pos.opened_ts)
    if age < min_sec:
        return None
    if _trend_continuation(pos, classified=classified):
        return None
    prints = list(getattr(pos, "premium_prints", None) or [])
    if ltp is not None:
        try:
            prints = prints + [float(ltp)]
        except (TypeError, ValueError):
            pass
    er = _kaufman_er(prints[-int(STALL_LOOKBACK) :])
    if er is None:
        er = _kaufman_er(prints)
    if er is None or float(er) > float(STALL_ER_MAX):
        return None
    high = getattr(pos, "seen_high", None)
    high_ts = getattr(pos, "seen_high_ts", None)
    if high is None or high_ts is None:
        return None
    try:
        px = float(ltp)
        peak = float(high)
    except (TypeError, ValueError):
        return None
    at_failed_high = abs(px - peak) <= 0.6 and age >= min_sec + 5 * 60
    stale_scratch = (
        int(ts) - int(high_ts) >= stale_sec
        and px + 1e-9 >= float(pos.entry)
        and px <= peak - 0.15
    )
    prog = _target_progress(pos, peak)
    chop_near = (
        chop
        and px + 1e-9 >= float(pos.entry)
        and prog is not None
        and prog >= float(STALL_CHOP_PROGRESS)
        and (stale_scratch or at_failed_high or px <= peak - 0.15)
    )
    if not (at_failed_high or stale_scratch or chop_near):
        return None
    vol_expand = cl.get("vol_expand")
    if vol_expand is True:
        return None
    if idx_volume is not None and prev_idx_volume is not None:
        try:
            if float(prev_idx_volume) > 0 and float(idx_volume) / float(prev_idx_volume) >= 1.25:
                return None
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    return CANCEL_STALL


def _exit_reason(
    pos: OpenPaper,
    ltp: float,
    ts: int,
    bar_i: int,
    *,
    hold_bars: int = SCALP_HOLD_BARS,
    give_up_frac: float = GIVE_UP_FRAC,
    side_low: Optional[float] = None,
    atm_strike: Optional[float] = None,
    dealer_verdict: Optional[str] = None,
    live_greeks: Optional[dict[str, Optional[float]]] = None,
    session_iv: Optional[float] = None,
    wing_iv_list: Optional[Sequence[float]] = None,
    index_regime: Optional[str] = None,
    classified: Optional[dict[str, Any]] = None,
    idx_volume: Optional[float] = None,
    prev_idx_volume: Optional[float] = None,
    hold_trending_open_stall: bool = False,
) -> Optional[str]:
    """Exit a stuck long premium. Minute low counts. Do not wait out a dead contract.

    Hard path: STOP / TARGET / ADVERSE / STALL / TIME. Soft thesis/greeks trail
    must not skip STALL or TIME.
    """
    px = float(ltp)
    low = float(side_low) if side_low is not None else px
    seen = float(pos.seen_low) if pos.seen_low is not None else px
    path = float(pos.path_stop) if pos.path_stop is not None else float(pos.stop)
    dump_px = min(px, low, seen)
    if int(pos.target_step) < 1:
        if px <= path:
            return "STOP"
        stop_px = px
    else:
        stop_px = dump_px
        if stop_px <= pos.stop:
            return "STOP"
    if px >= pos.target:
        return "TARGET"
    overlay = exit_overlay_reason(pos)
    if overlay:
        return overlay
    if ticket_against_market(pos, classified, ltp=px):
        return CANCEL_AGAINST
    give_up = float(pos.entry) * (1.0 - float(give_up_frac))
    if dump_px <= give_up:
        return "CANCEL_ADVERSE"
    stall = stall_book_reason(
        pos,
        px,
        ts,
        classified=classified,
        idx_volume=idx_volume,
        prev_idx_volume=prev_idx_volume,
        hold_trending_open_stall=hold_trending_open_stall,
    )
    if stall:
        return stall
    age = int(ts) - int(pos.opened_ts)
    cont = _trend_continuation(pos, classified=classified)
    can_stall = getattr(pos, "seen_high_ts", None) is not None
    if age >= int(TIME_HARD_SEC):
        return "TIME"
    if age >= int(hold_bars) * 60 and not cont and not can_stall:
        return "TIME"
    step = STRIKE_STEP.get(pos.underlying.upper(), 50.0)
    if (
        pos.atm_strike is not None
        and atm_strike is not None
        and abs(float(atm_strike) - float(pos.atm_strike)) >= step - 1e-9
        and dump_px < float(pos.entry)
    ):
        return "CANCEL_STRIKE_ROLL"
    underwater = dump_px < float(pos.entry)
    verdict = str(dealer_verdict or "")
    if underwater and pos.side == "CE" and verdict == "BUY_PE_CONFIRM":
        return "CANCEL_THESIS"
    if underwater and pos.side == "PE" and verdict == "BUY_CE_CONFIRM":
        return "CANCEL_THESIS"
    if underwater and str(index_regime or "") == "SIDEWAYS":
        return "CANCEL_SIDEWAYS"
    g_dead = _greeks_cancel_reason(
        side=pos.side,
        entry=float(pos.entry),
        live=live_greeks or {},
        minutes=minutes_ist(ts),
        session_iv=session_iv,
        wing_iv_list=wing_iv_list,
        filled=True,
    )
    if g_dead:
        return g_dead
    if minutes_ist(ts) >= FLATTEN_MINUTES_IST:
        return "FLATTEN_1516"
    return None


def _close_status(*, unfilled: bool, reason: str) -> str:
    """Unfilled working limit ≠ filled ticket we pulled. Both are paper, not live."""
    if unfilled:
        return "CANCELLED_UNFILLED"
    if str(reason).startswith("CANCEL"):
        return "CLOSED_CANCEL"
    return "CLOSED_PAPER"


def _close(engine: BookEngine, pos: OpenPaper, *, ltp: float, ts: int, reason: str, root: Optional[Path] = None) -> None:
    unfilled = (not pos.filled) or str(reason).startswith("CANCEL_UNFILLED")
    qty = pos.qty
    if qty is None and pos.lot_size is not None and int(pos.lot_size) > 0:
        qty = int(pos.lot_size) * int(pos.lots)
    charges = groww_round_trip_charges(
        exit_premium=float(ltp),
        entry_premium=float(pos.entry) if pos.entry is not None else None,
        qty=qty,
        filled=not unfilled,
    )
    if unfilled:
        points = 0.0
        gross = 0.0
        inr = 0.0
        result = "CANCELLED"
        won = False
    else:
        points = float(ltp) - float(pos.entry)
        gross = pnl_inr(points=points, lot_size=pos.lot_size, lots=pos.lots)
        inr = net_pnl_inr(gross_inr=gross, charges_inr=float(charges["charges_inr"]))
        if inr is None:
            won = points > 0
        else:
            won = inr > 0
        result = paper_close_result(unfilled=False, reason=str(reason), won=bool(won))
    target_hit = (not unfilled) and str(reason) == "TARGET"
    sl_hit = (not unfilled) and reason in {"STOP", "CANCEL_ADVERSE"}
    sl_loss_inr = inr if sl_hit and inr is not None and inr < 0 else (0.0 if sl_hit and inr is None else None)
    if sl_hit and inr is None:
        sl_loss_inr = round(points, 4)
    if sl_hit and inr is not None:
        sl_loss_inr = inr if inr < 0 else 0.0
    status = _close_status(unfilled=unfilled, reason=reason)
    cl_close = engine.last_regime.get(str(pos.underlying).upper()) or {}
    kind_open = str(
        getattr(pos, "market_kind_open", None)
        or market_kind(
            {
                "er": pos.regime_er,
                "flip_frac": pos.regime_flip_frac,
                "range_over_atr": getattr(pos, "regime_range_over_atr", None),
                "realized_vol": getattr(pos, "regime_rv", None),
            },
            require_er=True,
        )
    )
    kind_close = market_kind(cl_close if isinstance(cl_close, dict) else {}, require_er=True)
    close_why = paper_close_justification(
        open_why=str(pos.justification or ""),
        reason=str(reason),
        result=str(result),
        status=status,
        unfilled=unfilled,
        inr=inr,
        sl_hit=sl_hit,
        target_hit=target_hit,
        exit_px=float(ltp),
        target_px=float(pos.target) if pos.target is not None else None,
    )
    engine.closed.append(
        {
            "book_id": pos.book_id,
            "model_names": list(getattr(pos, "model_names", None) or [pos.book_id]),
            "underlying": pos.underlying,
            "side": pos.side,
            "trade_id": pos.trade_id,
            "status": status,
            "target_step": pos.target_step,
            "entry": pos.entry,
            "limit_price": pos.limit_price or pos.entry,
            "exit": round(float(ltp), 4),
            "stop": pos.stop,
            "target": pos.target,
            "atm_strike": pos.atm_strike,
            "strike_source": pos.strike_source,
            "exit_reason": reason,
            "sl_hit": sl_hit,
            "sl_loss_inr": sl_loss_inr if sl_hit else None,
            "realized_pnl": round(points, 4),
            "gross_pnl_inr": gross,
            "brokerage_inr": charges["brokerage_inr"],
            "gst_inr": charges["gst_inr"],
            "stt_inr": charges["stt_inr"],
            "exchange_inr": charges.get("exchange_inr"),
            "sebi_inr": charges.get("sebi_inr"),
            "stamp_inr": charges.get("stamp_inr"),
            "charges_inr": charges["charges_inr"],
            "realized_pnl_inr": inr,
            "lot_size": pos.lot_size,
            "lots": pos.lots,
            "qty": qty,
            "notional_inr": pos.notional_inr,
            "capital_inr": pos.capital_inr,
            "lot_status": pos.lot_status,
            "delta": pos.delta,
            "gamma": pos.gamma,
            "theta": pos.theta,
            "iv": pos.iv,
            "greeks_notes": pos.greeks_notes,
            "index_regime": pos.index_regime,
            "justification": close_why,
            "regime_er": pos.regime_er,
            "regime_flip_frac": pos.regime_flip_frac,
            "regime_reason": pos.regime_reason,
            "regime_range_over_atr": getattr(pos, "regime_range_over_atr", None),
            "regime_rv": getattr(pos, "regime_rv", None),
            "market_kind_open": kind_open,
            "market_kind_close": kind_close,
            "regime_er_close": cl_close.get("er") if isinstance(cl_close, dict) else None,
            "regime_flip_frac_close": cl_close.get("flip_frac") if isinstance(cl_close, dict) else None,
            "regime_range_over_atr_close": cl_close.get("range_over_atr") if isinstance(cl_close, dict) else None,
            "regime_rv_close": cl_close.get("realized_vol") if isinstance(cl_close, dict) else None,
            "index_regime_close": (cl_close.get("regime") if isinstance(cl_close, dict) else None)
            or "UNKNOWN",
            "opened_ts": pos.opened_ts,
            "closed_ts": ts,
            "last_updated_ts": int(ts),
            "opened_ist": _ist_dt(pos.opened_ts).isoformat(timespec="seconds"),
            "closed_ist": _ist_dt(ts).isoformat(timespec="seconds"),
            "last_updated_ist": _ist_dt(ts).isoformat(timespec="seconds"),
            "shadow": True,
            "execution": "refused",
            "promote": False,
            "won": won,
            "result": result,
            "target_hit": target_hit,
            "filled": (not unfilled),
        }
    )
    if inr is not None:
        engine.equity[pos.book_id] = engine.book_equity(pos.book_id) + inr
    engine.opens.pop((pos.book_id, pos.underlying), None)
    if not unfilled:
        und_key = str(pos.underlying).upper()
        engine.last_exit_by_und[und_key] = {
            "side": pos.side,
            "ts": int(ts),
            "reason": str(reason),
        }
        if str(reason) == "STOP" and pos.side in {"CE", "PE"}:
            bucket = engine.last_stop_side_by_und.setdefault(und_key, {})
            bucket[str(pos.side)] = int(ts)
            if pos.book_id == "MIX-DEFAULT-BUY":
                engine.session_stop_count[und_key] = int(engine.session_stop_count.get(und_key) or 0) + 1
    if root is not None:
        append_model_log(
            root,
            {
                "event": "CLOSE",
                "model": pos.book_id,
                "book_id": pos.book_id,
                "trade_id": pos.trade_id,
                "status": status,
                "target_step": pos.target_step,
                "filled": not unfilled,
                "underlying": pos.underlying,
                "side": pos.side,
                "strike": pos.atm_strike,
                "limit": pos.limit_price or pos.entry,
                "target": pos.target,
                "stop": pos.stop,
                "exit_reason": reason,
                "sl_hit": sl_hit,
                "pnl_points": round(points, 4),
                "gross_pnl_inr": gross,
                "charges_inr": charges["charges_inr"],
                "pnl_inr": inr,
                "equity_inr": engine.book_equity(pos.book_id),
                "justification": close_why,
                "market_kind_open": kind_open,
                "market_kind_close": kind_close,
            },
        )


def _try_open(
    engine: BookEngine,
    *,
    book_id: str,
    underlying: str,
    side: Optional[str],
    tick: Triple,
    ce_path: Sequence[float],
    pe_path: Sequence[float],
    bar_i: int,
    skip_reason: Optional[str] = None,
    strike: Optional[float] = None,
    strike_source: str = "ROUND_INDEX_HYPOTHESIS",
) -> None:
    gate = new_paper_blocked(tick.ts)
    if gate:
        engine.mark_skip(book_id, underlying, gate, ts=tick.ts, seen_side=side)
        if engine.root is not None:
            append_model_log(
                engine.root,
                {
                    "event": "HOLD",
                    "model": book_id,
                    "book_id": book_id,
                    "underlying": underlying,
                    "status": "HOLD",
                    "reason": gate,
                    "filled": False,
                    "target_step": 0,
                },
            )
        return
    if engine.has_open(book_id, underlying):
        if bool(getattr(engine, "sod_one_ticket", False)):
            engine.mark_skip(book_id, underlying, SOD_ONE_OPEN, ts=tick.ts, seen_side=side)
        return
    try:
        from desk_ml.founder_session import new_fill_decision

        decision = new_fill_decision(underlying, root=getattr(engine, "root", None))
        if not decision.get("allow"):
            engine.mark_skip(
                book_id,
                underlying,
                str(decision.get("reason") or "FOUNDER_STOP_TRADING_ON_INDEX"),
                ts=tick.ts,
                seen_side=side,
                detail=decision.get("note"),
            )
            return
    except Exception:
        if str(underlying).upper() not in {"NIFTY"}:
            return
    if getattr(engine, "skip_banknifty", False) and str(underlying).upper() == "BANKNIFTY":
        engine.mark_skip(
            book_id,
            underlying,
            "FOCUS_NIFTY_SENSEX",
            ts=tick.ts,
            seen_side=side,
        )
        return
    if getattr(engine, "skip_sensex", False) and str(underlying).upper() == "SENSEX":
        engine.mark_skip(
            book_id,
            underlying,
            "FOCUS_NIFTY_ONLY",
            ts=tick.ts,
            seen_side=side,
        )
        return
    classified = engine.last_regime.get(underlying.upper()) or {}
    regime = str(classified.get("regime") or "UNKNOWN")
    if skip_reason:
        engine.mark_skip(
            book_id, underlying, skip_reason, ts=tick.ts, index_regime=regime, seen_side=side
        )
        if engine.root is not None:
            append_model_log(
                engine.root,
                {"event": "SKIP", "model": book_id, "underlying": underlying, "reason": skip_reason},
            )
        return
    capital = engine.book_capital(book_id)
    if capital <= 0:
        engine.mark_skip(
            book_id,
            underlying,
            "CAPITAL_SKIP_DATA_INSUFFICIENT",
            ts=tick.ts,
            index_regime=regime,
            seen_side=side,
        )
        return
    if regime == "UNKNOWN":
        engine.mark_skip(
            book_id,
            underlying,
            REGIME_UNKNOWN_WAIT,
            ts=tick.ts,
            index_regime=regime,
            regime_er=classified.get("er"),
            regime_flip_frac=classified.get("flip_frac"),
            regime_reason=classified.get("reason") or "short_or_mixed_1m_path",
            seen_side=side,
        )
        if engine.root is not None:
            append_model_log(
                engine.root,
                {
                    "event": "SKIP",
                    "model": book_id,
                    "underlying": underlying,
                    "reason": REGIME_UNKNOWN_WAIT,
                    "index_regime": regime,
                },
            )
        return
    if engine.skip_new_when_sideways and regime == "SIDEWAYS":
        engine.mark_skip(
            book_id,
            underlying,
            SIDEWAYS_HOLD,
            ts=tick.ts,
            index_regime=regime,
            regime_er=classified.get("er"),
            regime_flip_frac=classified.get("flip_frac"),
            regime_reason=classified.get("reason"),
            seen_side=side,
        )
        if engine.root is not None:
            append_model_log(
                engine.root,
                {
                    "event": "SKIP",
                    "model": book_id,
                    "underlying": underlying,
                    "reason": SIDEWAYS_HOLD,
                    "index_regime": regime,
                },
            )
        return
    if side not in {"CE", "PE"}:
        engine.mark_skip(book_id, underlying, "NO_SIDE", ts=tick.ts, seen_side=side)
        return
    if not bin_side_allows(classified, side):
        engine.mark_skip(
            book_id,
            underlying,
            BIN_SIDE_MISMATCH,
            ts=tick.ts,
            index_regime=regime,
            seen_side=side,
            bin_side=(classified.get("itm_bin") or {}).get("side"),
        )
        return
    if covering_label(classified, side) == "LONG_UNWIND":
        engine.mark_skip(
            book_id,
            underlying,
            BIN_LONG_UNWIND,
            ts=tick.ts,
            index_regime=regime,
            seen_side=side,
            covering="LONG_UNWIND",
        )
        return
    if getattr(engine, "sensex_need_strength", True) and underlying.upper() == "SENSEX":
        strong = (
            classified.get("last3_impulse") in {"UP", "DOWN"}
            or classified.get("last3_reason") == "pause_continue"
            or covering_label(classified, side) == "SHORT_COVER"
        )
        if not strong:
            engine.mark_skip(
                book_id,
                underlying,
                "SENSEX_WAIT_STRENGTH",
                ts=tick.ts,
                index_regime=regime,
                seen_side=side,
            )
            return
    if (
        getattr(engine, "nifty_need_strength", False)
        and underlying.upper() == "NIFTY"
        and dealer_entry_book(book_id)
    ):
        closed_ok = False
        if bool(getattr(engine, "nifty_cover_closed_1m", False)):
            closed_ok = closed_1m_has_cover_strength(
                (getattr(engine, "itm_bins", None) or {}).get(underlying.upper()),
                side,
            )
        strong = nifty_has_entry_strength(
            classified,
            side,
            cover_closed_1m=bool(getattr(engine, "nifty_cover_closed_1m", False)),
            closed_1m_has_cover=closed_ok,
        )
        if not strong:
            engine.mark_skip(
                book_id,
                underlying,
                "NIFTY_WAIT_STRENGTH",
                ts=tick.ts,
                index_regime=regime,
                seen_side=side,
            )
            return
    allow = getattr(engine, "nifty_allow_sides", None)
    if allow and underlying.upper() == "NIFTY" and side not in allow:
        engine.mark_skip(
            book_id,
            underlying,
            "NIFTY_SIDE_FILTER",
            ts=tick.ts,
            index_regime=regime,
            seen_side=side,
        )
        return
    if (
        getattr(engine, "nifty_align_impulse", False)
        and underlying.upper() == "NIFTY"
        and dealer_entry_book(book_id)
    ):
        impulse = classified.get("last3_impulse")
        if (impulse == "DOWN" and side == "CE") or (impulse == "UP" and side == "PE"):
            engine.mark_skip(
                book_id,
                underlying,
                "NIFTY_IMPULSE_ALIGN",
                ts=tick.ts,
                index_regime=regime,
                seen_side=side,
                last3_impulse=impulse,
            )
            return
    if getattr(engine, "nifty_skip_side_after_stop", False) and underlying.upper() == "NIFTY":
        stopped = (getattr(engine, "last_stop_side_by_und", None) or {}).get(str(underlying).upper()) or {}
        if side in stopped:
            engine.mark_skip(
                book_id,
                underlying,
                "NIFTY_SIDE_AFTER_STOP",
                ts=tick.ts,
                index_regime=regime,
                seen_side=side,
            )
            return
    if getattr(engine, "nifty_skip_ce_after_stop", False) and underlying.upper() == "NIFTY" and side == "CE":
        stopped = (getattr(engine, "last_stop_side_by_und", None) or {}).get("NIFTY") or {}
        if "CE" in stopped:
            engine.mark_skip(
                book_id,
                underlying,
                "NIFTY_CE_AFTER_STOP",
                ts=tick.ts,
                index_regime=regime,
                seen_side=side,
            )
            return
    halt_n = getattr(engine, "nifty_halt_after_stops", None)
    if halt_n is not None and underlying.upper() == "NIFTY":
        if int(engine.session_stop_count.get("NIFTY") or 0) >= int(halt_n):
            engine.mark_skip(
                book_id,
                underlying,
                "NIFTY_TWO_STOP_HALT",
                ts=tick.ts,
                index_regime=regime,
                seen_side=side,
            )
            return
    if getattr(engine, "nifty_session_lean", False) and underlying.upper() == "NIFTY":
        if minutes_ist(tick.ts) >= (10 * 60 + 30):
            open_px = (getattr(engine, "session_open_idx", None) or {}).get("NIFTY")
            try:
                px = float(tick.idx_close)
            except (TypeError, ValueError):
                px = None
            if open_px is not None and px is not None:
                if px < float(open_px) and side == "CE":
                    engine.mark_skip(
                        book_id,
                        underlying,
                        "NIFTY_SESSION_LEAN",
                        ts=tick.ts,
                        index_regime=regime,
                        seen_side=side,
                    )
                    return
                if px > float(open_px) and side == "PE":
                    engine.mark_skip(
                        book_id,
                        underlying,
                        "NIFTY_SESSION_LEAN",
                        ts=tick.ts,
                        index_regime=regime,
                        seen_side=side,
                    )
                    return
    cap = getattr(engine, "nifty_max_filled_per_book", None)
    if cap is not None and underlying.upper() == "NIFTY":
        filled_n = sum(
            1
            for row in engine.closed
            if row.get("filled")
            and row.get("book_id") == book_id
            and str(row.get("underlying") or "").upper() == "NIFTY"
        )
        if filled_n >= int(cap):
            engine.mark_skip(
                book_id,
                underlying,
                "NIFTY_MAX_FILLED",
                ts=tick.ts,
                index_regime=regime,
                seen_side=side,
            )
            return
    cutoff = getattr(engine, "no_new_after_minutes", None)
    if cutoff is not None and minutes_ist(tick.ts) >= int(cutoff):
        engine.mark_skip(
            book_id,
            underlying,
            "NO_NEW_AFTER_CUTOFF",
            ts=tick.ts,
            index_regime=regime,
            seen_side=side,
        )
        return
    prev = (getattr(engine, "last_exit_by_und", None) or {}).get(str(underlying).upper())
    flip_m = getattr(engine, "nifty_no_flip_minutes", None)
    if (
        flip_m
        and str(underlying).upper() == "NIFTY"
        and isinstance(prev, dict)
        and str(prev.get("reason") or "") == "TARGET"
        and prev.get("side") in {"CE", "PE"}
        and side in {"CE", "PE"}
        and prev.get("side") != side
        and int(tick.ts) - int(prev.get("ts") or 0) < int(flip_m) * 60
    ):
        engine.mark_skip(
            book_id,
            underlying,
            "NIFTY_NO_FLIP",
            ts=tick.ts,
            index_regime=regime,
            seen_side=side,
        )
        return
    if engine.skip_bn_unless_last3 and underlying.upper() == "BANKNIFTY":
        if classified.get("last3_impulse") not in {"UP", "DOWN"}:
            engine.mark_skip(
                book_id,
                underlying,
                "WIDE_WAIT_CONTINUATION",
                ts=tick.ts,
                index_regime=regime,
                seen_side=side,
            )
            return
    if engine.skip_trend_against and regime == "TREND":
        direction = str(classified.get("direction") or "UNKNOWN")
        if direction == "UP" and side == "PE":
            engine.mark_skip(
                book_id,
                underlying,
                "TREND_UP_KILL_PE",
                ts=tick.ts,
                index_regime=regime,
                regime_direction=direction,
                seen_side=side,
            )
            return
        if direction == "DOWN" and side == "CE":
            engine.mark_skip(
                book_id,
                underlying,
                "TREND_DOWN_KILL_CE",
                ts=tick.ts,
                index_regime=regime,
                regime_direction=direction,
                seen_side=side,
            )
            return
    if (
        regime == "TREND"
        and classified.get("vol_expand") is False
        and not classified.get("last3_impulse")
        and not paper_impulse_fill(classified)
    ):
        engine.mark_skip(
            book_id,
            underlying,
            VOL_NOT_EXPANDING,
            ts=tick.ts,
            index_regime=regime,
            vol_status=classified.get("vol_status"),
            vol_last3_sum=classified.get("vol_last3_sum"),
            seen_side=side,
        )
        return
    atm = strike if strike is not None else chain_atm(tick, underlying)
    sod_product = bool(getattr(engine, "sod_one_ticket", True)) and book_id == SOD_PRODUCT_BOOK
    tape_kind = str(getattr(tick, "premium_kind", None) or "").upper()
    if sod_product:
        want = pick_paper_strike(tick, side, atm, underlying)
    else:
        want = float(atm) if tape_kind == "ATM" else pick_paper_strike(tick, side, atm, underlying)
    greeks = leg_greeks(tick, side, want)
    itm_px, _itm_low, itm_src = quote_for_side(tick, side, strike=want, itm_only=sod_product)
    booked_src = str(itm_src or "")
    if sod_product:
        booked_ok = (
            itm_px is not None
            and booked_src not in {"ATM", "MISSING_ITM"}
            and not booked_src.startswith("MISSING")
            and is_buy_itm(side, float(want), tick, underlying)
        )
    elif tape_kind == "ATM":
        booked_ok = itm_px is not None and not booked_src.startswith("MISSING")
    else:
        booked_ok = (
            itm_px is not None
            and booked_src != "ATM"
            and not booked_src.startswith("MISSING")
            and is_buy_itm(side, float(want), tick, underlying)
        )
    if not booked_ok:
        engine.mark_skip(
            book_id,
            underlying,
            "ITM_ONLY_NO_QUOTE" if itm_px is None or booked_src in {"ATM", "MISSING_ITM"} else "ITM_ONLY_NOT_ITM",
            ts=tick.ts,
            index_regime=regime,
            seen_side=side,
            strike=want,
            quote_src=booked_src,
        )
        return
    entry = float(itm_px)
    booked = want
    source = "ITM_100"
    path = []
    for t in (ce_path if side == "CE" else pe_path):
        try:
            path.append(float(t))
        except (TypeError, ValueError):
            continue
    if not path:
        path = [entry]
    adj = greeks_paper_adjust(
        entry=float(entry),
        stop_frac=engine.paper_stop_frac,
        target_frac=engine.paper_target_frac,
        delta=greeks.get("delta"),
        gamma=greeks.get("gamma"),
        theta=greeks.get("theta"),
        iv=greeks.get("iv"),
        classified=classified,
    )
    if adj.get("skip"):
        engine.mark_skip(book_id, underlying, str(adj.get("reason") or "GREEKS_SKIP"), ts=tick.ts, **{k: greeks.get(k) for k in ("delta", "theta", "iv")})
        return
    dmin = getattr(engine, "nifty_min_abs_delta", None)
    if dmin is not None and str(underlying).upper() == "NIFTY" and greeks.get("delta") is not None:
        try:
            if abs(float(greeks["delta"])) < float(dmin):
                engine.mark_skip(
                    book_id,
                    underlying,
                    "NIFTY_DELTA_BAND",
                    ts=tick.ts,
                    seen_side=side,
                    delta=greeks.get("delta"),
                )
                return
        except (TypeError, ValueError):
            pass
    impulse_fill = paper_impulse_fill(classified)
    discount = 0.0 if impulse_fill else float(engine.limit_discount_frac)
    cl = dict(classified) if isinstance(classified, dict) else {}
    ov = (getattr(engine, "point_profile_overrides", None) or {}).get(str(underlying).upper())
    if ov:
        cl["_profile_override"] = ov
    levels = propose_levels(
        float(entry),
        path,
        stop_frac=float(adj["stop_frac"]),
        target_frac=float(adj["target_frac"]),
        limit_discount_frac=discount,
        underlying=underlying,
        classified=cl,
    )
    lot_size, lot_src = engine.lot_by_und.get(underlying.upper(), (None, "unset"))
    sized = size_lots(
        entry=float(levels["limit_price"] or levels["entry"]),
        lot_size=lot_size,
        capital_inr=capital,
        min_lots=int(getattr(engine, "paper_min_lots", PAPER_MIN_LOTS) or PAPER_MIN_LOTS),
        target_lots=int(getattr(engine, "paper_target_lots", PAPER_TARGET_LOTS) or PAPER_TARGET_LOTS),
        max_lots=int(getattr(engine, "paper_max_lots", PAPER_MAX_LOTS) or PAPER_MAX_LOTS),
    )
    n_lots = int(sized.get("lots") or 0)
    min_need = int(getattr(engine, "paper_min_lots", PAPER_MIN_LOTS) or PAPER_MIN_LOTS)
    if n_lots < min_need:
        engine.mark_skip(
            book_id,
            underlying,
            str(sized.get("lot_status") or "SKIP_BELOW_MIN_LOTS"),
            ts=tick.ts,
            seen_side=side,
            lots=n_lots,
            afford_lots=sized.get("afford_lots"),
            capital_inr=capital,
            min_lots=min_need,
        )
        return
    pos = OpenPaper(
        book_id=book_id,
        underlying=underlying,
        side=side,
        trade_id=f"paper-{book_id}-{underlying}-{tick.ts}-{side}",
        entry=float(levels["entry"]),
        stop=float(levels["stop"]),
        target=float(levels["target"]),
        atm_strike=booked,
        opened_ts=tick.ts,
        opened_bar=bar_i,
        strike_source=source,
        limit_price=float(levels.get("limit_price") or levels["entry"]),
        lot_size=sized.get("lot_size"),
        lots=n_lots,
        qty=sized.get("qty"),
        notional_inr=sized.get("notional_inr"),
        capital_inr=capital,
        lot_status=str(sized.get("lot_status") or lot_src),
        filled=impulse_fill,
        last_ltp=float(levels["entry"]),
        idx_at_open=float(tick.idx_close),
        delta=greeks.get("delta"),
        gamma=greeks.get("gamma"),
        theta=greeks.get("theta"),
        iv=greeks.get("iv"),
        vega=greeks.get("vega"),
        greeks_notes=list(adj.get("notes") or []),
        index_regime=regime,
        regime_er=classified.get("er"),
        regime_flip_frac=classified.get("flip_frac"),
        regime_reason=classified.get("reason"),
        regime_range_over_atr=classified.get("range_over_atr"),
        regime_rv=classified.get("realized_vol"),
        market_kind_open=market_kind(classified if isinstance(classified, dict) else {}, require_er=True),
        target_step=0,
        agent_status="IN_TRADE" if impulse_fill else "WORKING_LIMIT",
        idx_volume=getattr(tick, "idx_volume", None),
        last_updated_ts=int(tick.ts),
        path_stop=float(levels["stop"]),
        target_touch_ts=None,
        justification=paper_open_justification(
            underlying=underlying,
            side=side,
            classified=classified if isinstance(classified, dict) else {},
            levels=levels,
            strike=booked,
            strike_source=source,
            engine=engine,
        ),
        model_names=list(getattr(engine, "_current_model_names", None) or [book_id]),
    )
    engine.opens[(book_id, underlying)] = pos
    engine.bump_regime_book(book_id, regime, f"OPEN_{side}")
    if engine.root is not None:
        append_model_log(
            engine.root,
            {
                "event": "OPEN",
                "model": book_id,
                "book_id": book_id,
                "trade_id": pos.trade_id,
                "status": "IN_TRADE" if impulse_fill else "WORKING_LIMIT",
                "target_step": 0,
                "filled": impulse_fill,
                "underlying": underlying,
                "side": side,
                "strike": pos.atm_strike,
                "strike_source": pos.strike_source,
                "limit": pos.limit_price,
                "target": pos.target,
                "stop": pos.stop,
                "lot_size": pos.lot_size,
                "lots": pos.lots,
                "notional_inr": pos.notional_inr,
                "delta": pos.delta,
                "gamma": pos.gamma,
                "theta": pos.theta,
                "iv": pos.iv,
                "greeks_notes": pos.greeks_notes,
                "index_regime": pos.index_regime,
                "justification": pos.justification,
            },
        )


def paper_watch_ticket(
    engine: BookEngine,
    pos: OpenPaper,
    tick: Triple,
    underlying: str,
) -> Optional[str]:
    """PAPER overlay watch. No live add-on orders. Default no size-up."""
    pos.agent_status = agent_ticket_status(pos)
    risk = float(pos.entry) - float(pos.stop)
    reward = float(pos.target) - float(pos.entry)
    if risk > 0 and reward / risk > float(engine.max_target_r) + 1e-9:
        pos.cancel_eligible = True
        pos.agent_status = "CANCEL_ELIGIBLE"
        if engine.root is not None:
            append_model_log(
                engine.root,
                {
                    "event": "CANCEL_ELIGIBLE",
                    "book_id": pos.book_id,
                    "trade_id": pos.trade_id,
                    "status": "CANCEL_ELIGIBLE",
                    "target_step": pos.target_step,
                    "filled": pos.filled,
                    "target": pos.target,
                    "note": "R>max_target_r — prefer cancel vs sitting on fantasy; do not silent-clip mid-flight",
                },
            )
    vol = getattr(tick, "idx_volume", None)
    hist = getattr(engine, "_prev_idx_vol", None)
    if not isinstance(hist, dict):
        hist = {}
        engine._prev_idx_vol = hist  # type: ignore[attr-defined]
    prev_vol = hist.get(underlying.upper())
    shock = (
        vol is not None
        and prev_vol is not None
        and float(prev_vol) > 0
        and float(vol) >= 1.5 * float(prev_vol)
    )
    if (
        engine.paper_add_lot
        and not pos.cancel_eligible
        and pos.filled
        and int(pos.lots) == 1
        and pos.index_regime == "TREND"
        and shock
    ):
        feas = feasibility_long(
            entry=float(pos.entry),
            stop=float(pos.stop),
            target=float(pos.target),
            typical_range=max(reward, 0.5),
        )
        if feas.get("ok"):
            pos.lots = 2
            if pos.lot_size:
                pos.qty = int(pos.lot_size) * 2
            if engine.root is not None:
                append_model_log(
                    engine.root,
                    {
                        "event": "PAPER_ADD_LOT",
                        "book_id": pos.book_id,
                        "trade_id": pos.trade_id,
                        "status": pos.agent_status,
                        "target_step": pos.target_step,
                        "filled": True,
                        "lots": pos.lots,
                        "hypothesis": "paper_add_lot",
                        "note": "PAPER only +1 lot; default flag is false",
                    },
                )
    cl = engine.last_regime.get(underlying.upper()) or {}
    cover = covering_label(cl, pos.side)
    if (
        pos.filled
        and not pos.cancel_eligible
        and pos.last_ltp is not None
        and cover == "SHORT_COVER"
        and int(pos.target_step) >= 1
    ):
        band = trail_premium_band(cl, side=pos.side, underlying=pos.underlying)
        nxt = float(pos.target) + band
        if nxt > float(pos.target) + 1e-6:
            pos.target = round(nxt, 4)
    if pos.filled and cover == "LONG_UNWIND" and pos.last_ltp is not None:
        try:
            underwater = float(pos.last_ltp) + 3.0 < float(pos.entry)
        except (TypeError, ValueError):
            underwater = False
        if int(pos.target_step) >= 1:
            return COVER_LONG_UNWIND
        if underwater and _index_is_chop(cl):
            return COVER_LONG_UNWIND
    pos.agent_status = agent_ticket_status(pos)
    return None


def mark_to_market(
    engine: BookEngine,
    tick: Triple,
    underlying: str,
    bar_i: int,
    *,
    dealer_verdict: Optional[str] = None,
    atm_strike: Optional[float] = None,
    index_regime: Optional[str] = None,
) -> None:
    """Flatten/cancel OPEN tickets every bar. SIDEWAYS must not freeze an already-open book."""
    regime = str(
        index_regime
        or (engine.last_regime.get(underlying.upper()) or {}).get("regime")
        or ""
    )
    for book_id in list(LIVE_BOOKS):
        pos = engine.opens.get((book_id, underlying))
        if pos is None:
            continue
        sod_mtm = bool(getattr(engine, "sod_one_ticket", True)) and book_id == SOD_PRODUCT_BOOK
        ltp, side_low, src = quote_for_side(tick, pos.side, strike=pos.atm_strike, itm_only=sod_mtm)
        if ltp is None and pos.last_ltp is not None:
            ltp = float(pos.last_ltp)
            side_low = pos.seen_low if pos.seen_low is not None else ltp
            src = "LAST_PRINT"
        if ltp is None and pos.entry is not None:
            ltp = float(pos.entry)
            side_low = pos.seen_low if pos.seen_low is not None else ltp
            src = "ENTRY_PRINT"
        override = load_human_override(engine.root)
        if override.get("active"):
            wants_trade = not override.get("trade_id") or override.get("trade_id") == pos.trade_id
            wants_und = not override.get("underlying") or override.get("underlying") == underlying.upper()
            wants_side = not override.get("side") or override.get("side") == pos.side
            if wants_trade and wants_und and wants_side:
                action = str(override.get("action") or "").upper()
                if action == "CANCEL" or (action == "EXIT" and not pos.filled):
                    human_reason = CANCEL_HUMAN
                    exit_px = float(ltp if ltp is not None else pos.last_ltp or pos.entry)
                    _close(engine, pos, ltp=exit_px, ts=tick.ts, reason=human_reason, root=engine.root)
                    if engine.root is not None:
                        append_model_log(
                            engine.root,
                            {
                                "event": "HUMAN_OVERRIDE",
                                "model": book_id,
                                "book_id": book_id,
                                "trade_id": pos.trade_id,
                                "underlying": underlying,
                                "side": pos.side,
                                "reason": human_reason,
                                "status": "CLOSED_BY_HUMAN",
                                "filled": bool(pos.filled),
                                "priority": "HUMAN_SUPERIOR",
                            },
                        )
                    if engine.root is not None:
                        save_human_override({"action": "CLEAR"}, root=engine.root)
                    continue
                if action in {"SET_LEVELS", "MANAGE", "MANAGE_TRADE", "SET_TARGET_STOP"}:
                    new_tgt = _human_px(override.get("target"))
                    new_stop = _human_px(override.get("stop"))
                    entry = float(pos.entry) if pos.entry is not None else None
                    levels_ok = (
                        new_tgt is not None
                        and new_stop is not None
                        and new_tgt > new_stop
                        and (entry is None or (new_tgt > entry > new_stop))
                    )
                    if levels_ok:
                        pos.stop = float(new_stop)
                        pos.path_stop = float(new_stop)
                        pos.target = float(new_tgt)
                        pos.justification = (
                            f"{pos.justification} | HUMAN_SET_LEVELS stop={new_stop} target={new_tgt}"
                        ).strip(" |")
                        if engine.root is not None:
                            append_model_log(
                                engine.root,
                                {
                                    "event": "HUMAN_SET_LEVELS",
                                    "model": book_id,
                                    "book_id": book_id,
                                    "trade_id": pos.trade_id,
                                    "underlying": underlying,
                                    "side": pos.side,
                                    "stop": new_stop,
                                    "target": new_tgt,
                                    "status": "OPEN_PAPER",
                                    "filled": bool(pos.filled),
                                    "priority": "HUMAN_SUPERIOR",
                                    "orders": "REFUSED",
                                },
                            )
                        if engine.root is not None:
                            save_human_override({"action": "CLEAR"}, root=engine.root)
                    else:
                        if engine.root is not None:
                            append_model_log(
                                engine.root,
                                {
                                    "event": "HUMAN_LEVELS_REJECTED",
                                    "model": book_id,
                                    "book_id": book_id,
                                    "trade_id": pos.trade_id,
                                    "reason": "LEVELS_ORDER",
                                    "status": "OPEN_PAPER",
                                    "orders": "REFUSED",
                                },
                            )
                            save_human_override({"action": "CLEAR"}, root=engine.root)
                    # Do not flatten. Fall through to normal MTM with new levels.
                else:
                    # Naked EXIT on a fill is suicide — ignore flatten, keep the ticket.
                    if engine.root is not None:
                        append_model_log(
                            engine.root,
                            {
                                "event": "HUMAN_EXIT_REFUSED",
                                "model": book_id,
                                "book_id": book_id,
                                "trade_id": pos.trade_id,
                                "underlying": underlying,
                                "side": pos.side,
                                "reason": "HUMAN_LEVELS_REQUIRED",
                                "status": "OPEN_PAPER",
                                "filled": bool(pos.filled),
                                "priority": "HUMAN_SUPERIOR",
                                "orders": "REFUSED",
                            },
                        )
                        save_human_override({"action": "CLEAR"}, root=engine.root)
        if ltp is None:
            if minutes_ist(tick.ts) >= FLATTEN_MINUTES_IST:
                _close(
                    engine,
                    pos,
                    ltp=float(pos.entry),
                    ts=tick.ts,
                    reason="CANCEL_UNFILLED_FLAT" if not pos.filled else "FLATTEN_1516",
                    root=engine.root,
                )
            continue
        if side_low is None:
            side_low = ltp
        pos.last_ltp = float(ltp)
        pos.quote_src = src
        pos.last_updated_ts = int(tick.ts)
        low_v = float(side_low)
        pos.seen_low = min(pos.seen_low if pos.seen_low is not None else low_v, low_v, float(ltp))
        px_now = float(ltp)
        prev_hi = getattr(pos, "seen_high", None)
        if prev_hi is None or px_now >= float(prev_hi) - 1e-9:
            if prev_hi is None or px_now > float(prev_hi) + 1e-9:
                pos.seen_high_ts = int(tick.ts)
            pos.seen_high = px_now if prev_hi is None else max(float(prev_hi), px_now)
        prints = list(getattr(pos, "premium_prints", None) or [])
        prints.append(px_now)
        pos.premium_prints = prints[-int(PREMIUM_PRINT_CAP) :]
        if pos.filled:
            note_filled_wing_1m(pos, int(tick.ts), px_now)
        if not pos.filled:
            live = leg_greeks(tick, pos.side, float(pos.atm_strike or 0))
            hist = getattr(engine, "_greeks_iv_hist", None)
            prior = list((hist or {}).get(underlying.upper()) or [])
            u_reason = _unfilled_reason(
                pos,
                float(ltp),
                tick.ts,
                bar_i,
                side_low=low_v,
                dealer_verdict=dealer_verdict,
                live_delta=live.get("delta"),
                live_greeks=live,
                index_ltp=tick.idx_close,
                session_iv=session_iv_median(prior),
                wing_iv_list=wing_ivs(tick.wing_quotes),
                index_regime=regime,
            )
            if u_reason == "FILL":
                pos.filled = True
                pos.agent_status = "IN_TRADE"
                limit = float(pos.limit_price or pos.entry)
                if float(ltp) <= limit + 1e-9:
                    pos.entry = min(float(ltp), limit)
                else:
                    pos.entry = limit
                pos.opened_minute_key = _ist_minute_key(int(tick.ts))
                note_filled_wing_1m(pos, int(tick.ts), float(ltp))
            elif u_reason:
                _close(engine, pos, ltp=float(ltp), ts=tick.ts, reason=u_reason, root=engine.root)
                continue
            else:
                continue
        watch_kill = paper_watch_ticket(engine, pos, tick, underlying)
        if watch_kill:
            _close(engine, pos, ltp=float(ltp), ts=tick.ts, reason=watch_kill, root=engine.root)
            continue
        live_atm = atm_strike if atm_strike is not None else tick.atm_strike
        classified = engine.last_regime.get(underlying.upper()) or {}
        hist_vol = getattr(engine, "_prev_idx_vol", None)
        prev_vol = hist_vol.get(underlying.upper()) if isinstance(hist_vol, dict) else None
        idx_vol = getattr(tick, "idx_volume", None)
        trail_kw = dict(
            classified=classified if isinstance(classified, dict) else None,
            idx_volume=float(idx_vol) if idx_vol is not None else None,
            prev_idx_volume=float(prev_vol) if prev_vol is not None else None,
        )
        reason = _exit_reason(
            pos,
            float(ltp),
            tick.ts,
            bar_i,
            hold_bars=engine.paper_hold_bars,
            give_up_frac=engine.paper_give_up_frac,
            side_low=low_v,
            atm_strike=float(live_atm) if live_atm is not None else None,
            dealer_verdict=dealer_verdict,
            live_greeks=leg_greeks(tick, pos.side, float(pos.atm_strike or 0)),
            session_iv=session_iv_median(
                list((getattr(engine, "_greeks_iv_hist", None) or {}).get(underlying.upper()) or [])
            ),
            wing_iv_list=wing_ivs(tick.wing_quotes),
            index_regime=regime,
            classified=classified if isinstance(classified, dict) else None,
            idx_volume=float(idx_vol) if idx_vol is not None else None,
            prev_idx_volume=float(prev_vol) if prev_vol is not None else None,
            hold_trending_open_stall=bool(getattr(engine, "hold_trending_open_stall", False)),
        )
        roll = cancel_if_bin_rolled(pos, tick) if pos.filled else None
        if reason == "TARGET":
            if apply_target_lock_shift(engine, pos, ltp=float(ltp), ts=tick.ts, **trail_kw):
                continue
        soft = reason if is_soft_cancel_reason(reason) else (roll if pos.filled else None)
        if soft and pos.filled:
            if apply_filled_trail(engine, pos, ltp=float(ltp), ts=tick.ts, reason=str(soft), **trail_kw):
                continue
        if reason or roll:
            exit_reason = reason or roll
            exit_px = float(ltp)
            if exit_reason in {"STOP", "CANCEL_ADVERSE"}:
                exit_px = min(exit_px, low_v, float(pos.seen_low or exit_px))
            _close(engine, pos, ltp=exit_px, ts=tick.ts, reason=str(exit_reason), root=engine.root)


def step_underlying(
    engine: BookEngine,
    *,
    underlying: str,
    triples: Sequence[Triple],
    i: int,
    ml001_hold: bool,
    ml002_hold: bool,
    follow_gap: bool,
    logit: dict[str, Any],
    logit_xr: dict[str, Any],
    ml1: dict[str, Any],
    tv_side: Optional[str],
    deny_model_signals: bool = True,
) -> None:
    if i < 1:
        return
    und = underlying.upper()
    tick = triples[i]
    prev = triples[i - 1]
    idx_d = tick.idx_close - prev.idx_close
    bars, vols = index_1m_ohlcv_from_ticks(
        [
            (int(t.ts), float(t.idx_close), getattr(t, "idx_volume", None))
            for t in triples[: i + 1]
        ]
    )
    closes = [float(b["close"]) for b in bars]
    sr = engine.sr_levels.setdefault(und, {})
    px = float(tick.idx_close)
    sr["session_high"] = max(float(sr["session_high"]) if sr.get("session_high") is not None else px, px)
    sr["session_low"] = min(float(sr["session_low"]) if sr.get("session_low") is not None else px, px)
    strike_hint = tick.atm_strike if tick.atm_strike is not None else round_atm_strike(und, tick.idx_close)
    ce_g = leg_greeks(tick, "CE", float(strike_hint or 0))
    pe_g = leg_greeks(tick, "PE", float(strike_hint or 0))
    opt_confirm: dict[str, Any] = {
        "ce_chg": float(tick.ce_close) - float(prev.ce_close),
        "pe_chg": float(tick.pe_close) - float(prev.pe_close),
    }
    if tick.itm_ce_close is not None and prev.itm_ce_close is not None:
        opt_confirm["itm_ce_chg"] = float(tick.itm_ce_close) - float(prev.itm_ce_close)
    if tick.itm_pe_close is not None and prev.itm_pe_close is not None:
        opt_confirm["itm_pe_chg"] = float(tick.itm_pe_close) - float(prev.itm_pe_close)
    classified = classify_index_regime(
        closes,
        volumes=vols,
        lookback=engine.regime_lookback,
        er_max=engine.regime_er_max,
        flip_min=engine.regime_flip_min,
        range_atr_max=engine.regime_range_atr_max,
        greeks={
            "iv": (ce_g.get("iv") if ce_g.get("iv") is not None else pe_g.get("iv")),
            "ce_delta": ce_g.get("delta"),
            "pe_delta": pe_g.get("delta"),
        },
        ohlc=bars[-max(REGIME_LOOKBACK, REGIME_MIN_BARS) :],
        sr=sr,
        opt_confirm=opt_confirm,
    )
    if engine.apply_impulse_pause and not (
        (und == "SENSEX" and getattr(engine, "sensex_no_pause_wait", True))
        or (und == "NIFTY" and getattr(engine, "nifty_no_pause_wait", False))
    ):
        classified = apply_impulse_pause_continue(engine, und, classified, int(tick.ts))
    bin_rec = update_itm_bin(engine, und, tick)
    classified = apply_itm_bin_to_regime(classified, bin_rec)
    if und == "NIFTY" and getattr(engine, "nifty_bin_only", False):
        classified["last3_impulse"] = None
        classified["last3_confirmed"] = False
        classified["last3_reason"] = "nifty_bin_only"
    prem_path: list[float] = []
    for t in triples[max(0, i - 20) : i + 1]:
        px = t.itm_ce_close if (bin_rec or {}).get("side") == "CE" else t.itm_pe_close
        if px is None:
            px = t.ce_close if (bin_rec or {}).get("side") == "CE" else t.pe_close
        try:
            prem_path.append(float(px))
        except (TypeError, ValueError):
            continue
    classified["premium_atr"] = close_to_close_atr(prem_path)
    if und == "NIFTY" and minutes_ist(tick.ts) >= NO_NEW_BEFORE_MINUTES_IST:
        engine.session_open_idx.setdefault("NIFTY", float(tick.idx_close))
    engine.last_regime[und] = classified
    ce_d = tick.ce_close - prev.ce_close
    pe_d = tick.pe_close - prev.pe_close
    dealer = dealer_side(idx_d, ce_d, pe_d, underlying=und)
    strike = round_atm_strike(und, tick.idx_close)
    if tick.atm_strike is not None:
        strike = float(tick.atm_strike)
    mark_to_market(
        engine,
        tick,
        und,
        i,
        dealer_verdict=str(dealer.get("verdict") or ""),
        atm_strike=strike,
    )
    vol_hist = getattr(engine, "_prev_idx_vol", None)
    if not isinstance(vol_hist, dict):
        vol_hist = {}
        engine._prev_idx_vol = vol_hist  # type: ignore[attr-defined]
    ivol = getattr(tick, "idx_volume", None)
    if ivol is not None:
        vol_hist[und] = float(ivol)

    dealer_confirm = dealer.get("side") if dealer.get("side") in {"CE", "PE"} else None
    window = triples[max(0, i - RANGE_LOOKBACK) : i + 1]
    ce_path = [
        float(t.itm_ce_close if t.itm_ce_close is not None else t.ce_close) for t in window
    ]
    pe_path = [
        float(t.itm_pe_close if t.itm_pe_close is not None else t.pe_close) for t in window
    ]
    deny = bool(deny_model_signals)

    def _open(book_id: str, side: Optional[str], skip: Optional[str]) -> None:
        _try_open(
            engine,
            book_id=book_id,
            underlying=und,
            side=side,
            tick=tick,
            ce_path=ce_path,
            pe_path=pe_path,
            bar_i=i,
            skip_reason=skip,
            strike=strike,
        )

    impulse_side = paper_impulse_side(classified) if classified.get("regime") == "TREND" else None
    greeks_intent_side, greeks_intent_skip = greeks_vote_intent(
        dealer_confirm=dealer_confirm,
        logit=logit,
        impulse_side=impulse_side,
    )
    rolled_1m = int(tick.ts) // 60 != int(prev.ts) // 60
    if rolled_1m:
        engine.prev_1m_close[und] = engine.last_1m_close.get(und)
        engine.last_1m_close[und] = prev
    older = engine.prev_1m_close.get(und)
    closed_1m = engine.last_1m_close.get(und)
    extra_votes = getattr(engine, "_sod_extra_votes", None)
    votes = collect_analyst_votes(
        follows=dealer,
        logit=logit,
        logit_xr=logit_xr,
        greeks_side=greeks_intent_side,
        greeks_skip=greeks_intent_skip,
        ml001_hold=ml001_hold,
        ml002_hold=ml002_hold,
        ml1=ml1,
        tv_side=tv_side,
        classified=classified,
        extra=list(extra_votes) if extra_votes else None,
    )
    model_name_map = {
        "follows": "MIX-FORM-FOLLOWS",
        "logit": "MIX-ML-LOGIT",
        "xr": "MIX-ML-LOGIT-XR",
        "greeks": "MIX-ML-GREEKS",
    }
    spoken_model_names = [
        model_name_map.get(str(v.source), str(v.source))
        for v in votes
        if hasattr(v, "spoken") and v.spoken()
    ]
    engine._current_model_names = spoken_model_names  # type: ignore[attr-defined]
    picker = picker_majority(votes, prev=older, closed=closed_1m, classified=classified)
    sod = bool(getattr(engine, "sod_one_ticket", False))
    use_picker = sod or bool(getattr(engine, "picker_majority", False))
    fill_router = "sod_desk" if sod else "resolve_fill_intents"
    greeks_skip_final = greeks_intent_skip
    n_open_before = sum(1 for (_b, u) in engine.opens if u == und)
    if sod:
        proposed = picker.get("side") if picker.get("action") == "TICKET" else None
        review = review_picker_ticket(
            side=proposed if isinstance(proposed, str) else None,
            prev=older,
            closed=closed_1m,
            classified=classified,
            dealer=dealer,
            logit=logit,
            bar_closed_1m=older is not None and closed_1m is not None,
        )
        by_book = {SOD_PRODUCT_BOOK: review}
        engine.observer_review[und] = review
        engine.observer_by_book[und] = by_book
        desk_side = proposed if proposed in {"CE", "PE"} else None
        desk_skip: Optional[str] = None
        if review.get("action") == "VETO" and getattr(engine, "observer_veto_fills", True):
            desk_skip = str(review.get("reason") or "FOLLOW_GAP")
        elif desk_side is None:
            desk_skip = str(picker.get("skip") or "HOLD_MAJORITY")
        if engine.has_working_underlying(und) and desk_skip is None:
            desk_skip = SOD_ONE_OPEN
        # Lab books never OPEN on SOD. Do not call _try_open for them.
        if desk_side is not None or desk_skip is not None:
            _open(SOD_PRODUCT_BOOK, desk_side, desk_skip)
    else:
        intents = resolve_fill_intents(
            dealer_confirm=dealer_confirm,
            dealer_verdict=str(dealer.get("verdict") or "HOLD"),
            logit=logit,
            logit_xr=logit_xr,
            ml001_hold=ml001_hold,
            follow_gap=follow_gap,
            ml002_hold=ml002_hold,
            ml1=ml1,
            impulse_side=impulse_side,
        )
        if use_picker:
            intents = apply_picker_to_intents(
                intents,
                picker,
                fill_books=FILL_ELIGIBLE_BOOKS,
                observe_books=OBSERVE_ONLY_BOOKS,
                sod_one_ticket=False,
            )
        intents, review, by_book = review_fill_intents(
            intents,
            prev=older,
            closed=closed_1m,
            classified=classified,
            dealer=dealer,
            logit=logit,
            fill_books=FILL_ELIGIBLE_BOOKS,
            observe_books=OBSERVE_ONLY_BOOKS,
            apply_veto=bool(getattr(engine, "observer_veto_fills", True)),
            bar_closed_1m=older is not None and closed_1m is not None,
        )
        engine.observer_review[und] = review
        engine.observer_by_book[und] = by_book
        greeks_skip_final = intents["MIX-ML-GREEKS"][1]
        for book_id in LIVE_BOOKS:
            side, skip = intents[book_id]
            if book_id == "MIX-ML-GREEKS":
                greeks_side = side
                greeks_skip = skip
                if greeks_side in {"CE", "PE"} and greeks_skip is None:
                    want = pick_paper_strike(
                        tick, greeks_side, float(strike or round_atm_strike(und, tick.idx_close)), und
                    )
                    greeks = leg_greeks(tick, greeks_side, want)
                    px, _, _src = quote_for_side(tick, greeks_side, strike=want)
                    entry = float(px) if px is not None else (
                        tick.ce_close if greeks_side == "CE" else tick.pe_close
                    )
                    hist = getattr(engine, "_greeks_iv_hist", None)
                    if not isinstance(hist, dict):
                        hist = {}
                        engine._greeks_iv_hist = hist  # type: ignore[attr-defined]
                    prior = list(hist.get(und) or [])
                    atm_iv = greeks.get("iv")
                    scored = score_greeks_ticket(
                        side=greeks_side,
                        entry=entry,
                        delta=greeks.get("delta"),
                        gamma=greeks.get("gamma"),
                        theta=greeks.get("theta"),
                        iv=atm_iv,
                        session_iv=session_iv_median(prior),
                        minutes_ist=minutes_ist(tick.ts),
                        wing_iv_list=wing_ivs(tick.wing_quotes),
                    )
                    if atm_iv is not None:
                        hist.setdefault(und, []).append(float(atm_iv))
                    if not scored.get("take"):
                        greeks_skip = str(scored.get("reason") or "GREEKS_HOLD")
                        greeks_side = None
                greeks_skip_final = greeks_skip
                _open("MIX-ML-GREEKS", greeks_side, greeks_skip)
                continue
            _open(book_id, side, skip)

    opened_this_tick = sum(1 for (_b, u) in engine.opens if u == und) > n_open_before
    pos = engine.opens.get((SOD_PRODUCT_BOOK, und)) if sod else next(
        (p for (b, u), p in engine.opens.items() if u == und), None
    )
    obs_action = str(review.get("action") or "") if isinstance(review, dict) else ""
    desk_fill_side = pos.side if pos is not None and pos.side in {"CE", "PE"} else None
    model_signals = track_model_signals(
        votes,
        picker,
        review if isinstance(review, dict) else None,
        underlying=und,
        ts=int(tick.ts),
        desk_opened=opened_this_tick,
        desk_side=desk_fill_side,
    )
    if rolled_1m or obs_action in {"ALLOW", "VETO"} or any(
        r.get("vs_picker") in {"SPOKEN_PICKER_HOLD", "DISSENT"} for r in model_signals
    ):
        engine.signal_log.extend(model_signals)
        if len(engine.signal_log) > SIGNAL_LOG_MAX:
            engine.signal_log = engine.signal_log[-SIGNAL_LOG_MAX:]
    llm_trigger = "ALLOW" if obs_action == "ALLOW" else None
    llm_side = picker.get("side") if picker.get("side") in {"CE", "PE"} else None
    if llm_side is None and pos is not None:
        llm_side = pos.side if pos.side in {"CE", "PE"} else None
    llm_review = maybe_llm_review(
        trigger=llm_trigger,
        compact={"side": llm_side, "underlying": und, "opened": opened_this_tick},
        observer_action=obs_action or None,
        opened_this_tick=opened_this_tick,
        force_mock=True,
    )
    overlay_pkt = None
    if pos is not None:
        overlay_pkt = overlay_to_boss(
            open_pos={
                "book_id": pos.book_id,
                "underlying": pos.underlying,
                "side": pos.side,
                "filled": pos.filled,
                "entry": pos.entry,
                "stop": pos.stop,
                "target": pos.target,
                "agent_status": pos.agent_status,
            },
            itm_bin=bin_both_wings_packet(bin_rec),
            ml_overlay={"hold": bool(ml001_hold or ml002_hold), "regime": classified.get("regime")},
            classified=classified,
            trigger="1M_CLOSE" if rolled_1m else None,
        )
        overlay_pkt["llm_review"] = llm_review
        overlay_pkt["opened_this_tick"] = opened_this_tick

    engine.last_step = {
        "underlying": und,
        "ts": tick.ts,
        "follows": dealer,
        "dealer": dealer,
        "ml001_hold": ml001_hold,
        "ml002_hold": ml002_hold,
        "overlay_follow_gap": follow_gap,
        "logit": logit,
        "logit_xr": logit_xr,
        "ml1": ml1,
        "tv_ep_024": tv_side,
        "mix_ml_greeks_skip": greeks_skip_final,
        "index_regime": classified,
        "itm_bin": classified.get("itm_bin"),
        "bin_both_wings": bin_both_wings_packet(bin_rec),
        "deny_model_signals": deny,
        "analyst_votes": [
            v.packet() if hasattr(v, "packet") else (asdict(v) if hasattr(v, "source") else v)
            for v in votes
        ],
        "model_signals": model_signals,
        "picker": picker,
        "observer": review,
        "observer_by_book": {k: {"action": v.get("action"), "reason": v.get("reason"), "side": v.get("side")} for k, v in (by_book or {}).items()},
        "desk": {
            "sod_one_ticket": sod,
            "product_book": SOD_PRODUCT_BOOK if sod else None,
            "kind": "DESK",
            "opened_this_tick": opened_this_tick,
            "working": engine.has_working_underlying(und),
            "fill_quote": "ITM",
            "fill_router": fill_router,
            "quote_src": (
                next(
                    (
                        getattr(p, "quote_src", None)
                        for (b, u), p in engine.opens.items()
                        if u == und and b == SOD_PRODUCT_BOOK
                    ),
                    None,
                )
                if opened_this_tick
                else None
            ),
        },
        "overlay_to_boss": overlay_pkt,
        "llm_review": llm_review,
        "follow_gap": bool(review.get("follow_gap") if isinstance(review, dict) else False),
        "follow_gap_rule": "FOLLOW_GAP_ITM_1M",
        "independent": False if sod else True,
        "fill_router": fill_router,
        "trace": ["follows", "picker", "observer", "desk"],
        "note": (
            "Locked SOD: analyst room (FOLLOWS + logit + XR + greeks + STRAT KEEP_ALL + "
            "TV lab) → picker_majority → observer FOLLOW_GAP_ITM_1M → desk MIX-DEFAULT-BUY "
            "ITM fill only. Lab never OPEN. resolve_fill_intents is --sod-off only. "
            "LLM allow-review is async/fail-soft. Track MATCH/DISSENT/SPOKEN_PICKER_HOLD "
            "even when picker HOLD / observer VETO / desk ignores. KMeans is not CE/PE. "
            "KEEP_ALL. NO_PROMOTE."
        ),
    }
    quote_src = (engine.last_step.get("desk") or {}).get("quote_src")
    bar_closed = older is not None and closed_1m is not None
    exam = grade_fill(
        bar_closed_1m=bar_closed,
        opened=bool(opened_this_tick and sod),
        quote_src=str(quote_src) if quote_src else None,
        tape_kind=str(getattr(tick, "premium_kind", None) or ""),
        rolled_1m=rolled_1m,
    )
    exam["follows_clock"] = FOLLOWS_CLOCK
    exam["observer_clock"] = OBSERVER_CLOCK
    engine.last_step["exam"] = exam
    engine.last_step_by_und[und] = dict(engine.last_step)
    engine.exam_events.append(
        compact_exam_event(engine.last_step, opened=bool(opened_this_tick and sod), quote_src=quote_src)
    )
    if len(engine.exam_events) > 800:
        engine.exam_events = engine.exam_events[-800:]


def _hold_series(triples: Sequence[Triple], *, seed: int = 14) -> tuple[list[bool], list[bool], list[bool], dict[str, Any]]:
    rows = build_feature_rows(list(triples))
    meta: dict[str, Any] = {"n_feature_rows": len(rows)}
    if len(rows) < 20:
        n = len(triples)
        return [False] * n, [False] * n, [False] * n, {**meta, "status": "DATA_INSUFFICIENT"}
    train = rows[: max(16, int(len(rows) * 0.6))]
    fitted = fit_from_rows(train, seed=seed)
    bundle = pack_estimators(
        scaler=fitted["scaler"],
        kmeans=fitted["kmeans"],
        cluster_labels=fitted["cluster_labels"],
        forest=fitted["forest"],
    )
    idx_rets = [r["idx_ret"] for r in rows]
    k_ce = ols_beta(idx_rets, [r["ce_ret"] for r in rows])
    k_pe = ols_beta(idx_rets, [r["pe_ret"] for r in rows])
    residual: list[float] = []
    if k_ce is not None and k_pe is not None:
        residual = [
            0.5 * ((r["ce_ret"] - k_ce * r["idx_ret"]) + (r["pe_ret"] - k_pe * r["idx_ret"]))
            for r in rows
        ]
    zs = rolling_z(residual, 40) if residual else []
    names = ("idx_ret", "ce_ret", "pe_ret", "spread_chg", "abs_residual")
    by_ts = {int(r["ts"]): r for r in rows}
    ml001: list[bool] = []
    ml002: list[bool] = []
    row_i = -1
    for t in triples:
        feat_row = by_ts.get(int(t.ts))
        if feat_row is None:
            ml001.append(False)
            ml002.append(False)
            continue
        row_i += 1
        feat = {name: float(feat_row[name]) for name in names}
        scored = score_features_dict(feat, bundle)
        z_hold = False
        if row_i < len(zs) and zs[row_i] is not None:
            z_hold = abs(float(zs[row_i])) >= Z_HOLD
        ml001.append(scored.get("overlay") == OVERLAY_HOLD)
        ml002.append(z_hold)
    gap = follow_gap_series_itm_1m(list(triples))
    if len(gap) != len(triples):
        gap = [False] * len(triples)
    meta["status"] = "OK"
    meta["follow_gap_rule"] = "FOLLOW_GAP_ITM_1M"
    return ml001, ml002, gap, meta


def load_paper_params(root: Path) -> dict[str, Any]:
    path = root / "data" / "recon" / PAPER_PARAMS_NAME
    out = dict(DEFAULT_PAPER_PARAMS)
    if not path.is_file():
        return out
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    if not isinstance(blob, dict):
        return out
    for key in (
        "stop_frac",
        "target_frac",
        "scalp_hold_bars",
        "give_up_frac",
        "nudge_n_closed",
        "skip_sideways",
        "skip_trend_against",
        "limit_discount_frac",
        "desk_capital_inr",
        "paper_min_lots",
        "paper_target_lots",
        "paper_max_lots",
        "dashboard_heartbeat_seconds",
        "regime_lookback",
        "regime_er_max",
        "regime_flip_min",
        "regime_range_atr_max",
        "paper_add_lot",
        "max_target_r",
        "open_settle_gate",
        "paper_book_epoch_ts",
        "paper_book_epoch_ist",
        "skip_banknifty",
        "skip_sensex",
        "nifty_need_strength",
        "nifty_bin_only",
        "nifty_allow_sides",
        "nifty_min_abs_delta",
        "no_new_after_minutes",
        "nifty_no_flip_minutes",
        "nifty_no_pause_wait",
        "nifty_align_impulse",
        "nifty_skip_side_after_stop",
        "nifty_skip_ce_after_stop",
        "nifty_max_filled_per_book",
        "nifty_halt_after_stops",
        "nifty_session_lean",
        "apply_target_shift",
        "nifty_cover_closed_1m",
    ):
        if key in blob:
            out[key] = blob[key]
    try:
        lookback = int(out.get("regime_lookback") or REGIME_LOOKBACK)
    except (TypeError, ValueError):
        lookback = REGIME_LOOKBACK
    out["regime_lookback"] = min(max(lookback, REGIME_MIN_BARS), REGIME_LOOKBACK)
    try:
        cap = float(out.get("desk_capital_inr") or 0)
    except (TypeError, ValueError):
        cap = 0.0
    if cap + 1e-9 < float(DESK_CAPITAL_INR):
        out["desk_capital_inr"] = float(DESK_CAPITAL_INR)
    try:
        min_lots = int(out.get("paper_min_lots") or 0)
    except (TypeError, ValueError):
        min_lots = 0
    out["paper_min_lots"] = max(min_lots, int(PAPER_MIN_LOTS))
    try:
        target_lots = int(out.get("paper_target_lots") or 0)
    except (TypeError, ValueError):
        target_lots = 0
    out["paper_target_lots"] = min(
        max(target_lots, int(PAPER_TARGET_LOTS), int(out["paper_min_lots"])),
        int(PAPER_MAX_LOTS),
    )
    try:
        max_lots = int(out.get("paper_max_lots") or 0)
    except (TypeError, ValueError):
        max_lots = 0
    out["paper_max_lots"] = max(max_lots, int(PAPER_MAX_LOTS), int(out["paper_target_lots"]))
    out["production_params_written"] = False
    return out


def save_paper_params(root: Path, params: dict[str, Any]) -> None:
    recon = root / "data" / "recon"
    recon.mkdir(parents=True, exist_ok=True)
    payload = {
        **DEFAULT_PAPER_PARAMS,
        **params,
        "production_params_written": False,
        "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
    }
    (recon / PAPER_PARAMS_NAME).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def mistakes_from_closed(closed: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in closed:
        if str(row.get("result")) != "LOSS":
            continue
        reason = str(row.get("exit_reason") or "")
        if row.get("sl_hit"):
            lesson = "STOP_HIT: side was wrong or stop sat inside 1m noise"
            tweak = "widen paper stop_frac slightly, or skip when dealer case is PREMIUM_DIVERGENCE"
        elif reason == "TIME":
            lesson = "TIME_EXIT_LOSS: premium faded before target; hold bars too long"
            tweak = "cut scalp_hold_bars"
        elif reason in {
            "CANCEL_ADVERSE",
            "CANCEL_THESIS",
            "CANCEL_STRIKE_ROLL",
            "CANCEL_SIDEWAYS",
            CANCEL_BIN_ROLL,
            CANCEL_AGAINST,
        }:
            lesson = f"{reason}: ticket was dead; cancel instead of sitting to TIME"
            tweak = "give-up / thesis-flip / strike-roll / against-wing cancel is the paper rule"
        elif reason.startswith("CANCEL_UNFILLED"):
            lesson = f"{reason}: limit never filled — candle walked away or thesis/greeks died"
            tweak = "do not assume fill at signal print; cancel unfilled limits"
        elif reason in {"FLATTEN_1500", "FLATTEN_1515", "FLATTEN_1516"}:
            lesson = "FLATTEN_LOSS: still open into 15:16 IST"
            tweak = "do not open after 14:40 IST"
        else:
            lesson = f"LOSS via {reason or 'unknown'}"
            tweak = "review side vs INDEX delta"
        out.append(
            {
                "trade_id": row.get("trade_id"),
                "book_id": row.get("book_id"),
                "underlying": row.get("underlying"),
                "side": row.get("side"),
                "atm_strike": row.get("atm_strike"),
                "limit_price": row.get("limit_price"),
                "stop": row.get("stop"),
                "target": row.get("target"),
                "status": row.get("status"),
                "result": "LOSS",
                "sl_hit": row.get("sl_hit"),
                "money_lost_inr": row.get("realized_pnl_inr"),
                "exit_reason": reason,
                "lesson": lesson,
                "paper_tweak": tweak,
                "closed_ist": row.get("closed_ist"),
                "justification": row.get("justification"),
            }
        )
    return out


def successes_from_closed(closed: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in closed:
        if str(row.get("result")) != "SUCCESS":
            continue
        out.append(
            {
                "trade_id": row.get("trade_id"),
                "book_id": row.get("book_id"),
                "underlying": row.get("underlying"),
                "side": row.get("side"),
                "atm_strike": row.get("atm_strike"),
                "exit_reason": row.get("exit_reason"),
                "realized_pnl_inr": row.get("realized_pnl_inr"),
                "lesson": "KEEP: booked strike printed first TARGET (not TIME green)",
                "justification": row.get("justification"),
            }
        )
    return out


def nudge_paper_params(closed: Sequence[dict[str, Any]], current: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Session-only overfit. Never writes production MIX."""
    notes: list[str] = []
    n = len(closed)
    params = dict(current)
    params["production_params_written"] = False
    last_n = int(params.get("nudge_n_closed") or 0)
    if n < 8:
        notes.append("need ≥8 session closes before paper-param nudge")
        return params, notes
    if n - last_n < 8:
        notes.append(f"hold paper params until +8 closes (have {n}, last nudge at {last_n})")
        return params, notes
    sl_hits = sum(1 for c in closed if c.get("sl_hit"))
    time_loss = sum(1 for c in closed if c.get("result") == "LOSS" and c.get("exit_reason") == "TIME")
    wins = sum(1 for c in closed if c.get("won"))
    sl_rate = sl_hits / n
    time_loss_rate = time_loss / n
    wr = wins / n
    stop_frac = float(params.get("stop_frac") or STOP_FRAC)
    hold = int(params.get("scalp_hold_bars") or SCALP_HOLD_BARS)
    target_frac = float(params.get("target_frac") or TARGET_FRAC)
    if sl_rate >= 0.45:
        stop_frac = min(0.55, round(stop_frac + 0.02, 4))
        notes.append(f"high SL-hit {sl_rate:.0%} → paper stop_frac={stop_frac}")
        er_max = float(params.get("regime_er_max") or REGIME_ER_MAX)
        params["regime_er_max"] = min(0.40, round(er_max + 0.02, 4))
        notes.append(
            f"high SL-hit → paper regime_er_max={params['regime_er_max']} (more SIDEWAYS HOLD, session only)"
        )
    elif wr >= 0.55 and sl_rate <= 0.25:
        stop_frac = max(0.28, round(stop_frac - 0.02, 4))
        notes.append(f"few SL hits + wr {wr:.0%} → tighter paper stop_frac={stop_frac}")
    if time_loss_rate >= 0.30:
        hold = max(4, hold - 1)
        notes.append(f"time-exit losses {time_loss_rate:.0%} → scalp_hold_bars={hold}")
    elif wr >= 0.58 and time_loss_rate <= 0.10:
        hold = min(12, hold + 1)
        notes.append(f"time exits working → scalp_hold_bars={hold}")
    tgt_hits = sum(1 for c in closed if c.get("exit_reason") == "TARGET" and c.get("result") == "SUCCESS")
    if n and tgt_hits / n >= 0.40:
        notes.append("many TARGET wins — do not raise target_frac (fantasy 1:4 / 615 lesson). keep path cap.")
    sl_morning = sum(
        1
        for c in closed
        if c.get("sl_hit")
        and str(c.get("opened_ist") or "").find("T09:") >= 0
    )
    if sl_morning >= max(3, n // 5):
        params["skip_sideways"] = True
        notes.append("morning SL cluster → keep skip_sideways (chop). session only.")
    fantasy = sum(
        1
        for c in closed
        if c.get("entry")
        and c.get("stop")
        and c.get("target")
        and (float(c["target"]) - float(c["entry"])) / max(1e-9, float(c["entry"]) - float(c["stop"])) > 2.0
    )
    if fantasy:
        target_frac = min(target_frac, TARGET_FRAC)
        notes.append(f"{fantasy} tickets had R>2 — clip target_frac={target_frac}, no MIX write")
    params["stop_frac"] = stop_frac
    params["target_frac"] = target_frac
    params["paper_add_lot"] = False
    params["max_target_r"] = MAX_TARGET_R
    params["scalp_hold_bars"] = hold
    params["nudge_n_closed"] = n
    if not notes:
        notes.append("session mix inside band; keep paper params")
    return params, notes


def _as_side_tuple(value: Any) -> Optional[tuple[str, ...]]:
    if not value:
        return None
    if isinstance(value, str):
        token = value.strip().upper()
        return (token,) if token in {"CE", "PE"} else None
    out: list[str] = []
    for item in value:
        token = str(item).strip().upper()
        if token in {"CE", "PE"}:
            out.append(token)
    return tuple(out) or None


def replay_paper_scalp(
    *,
    root: Optional[Path] = None,
    underlyings: Sequence[str] = ("NIFTY", "BANKNIFTY", "SENSEX"),
    source: str = "cache",
    triples_by_und: Optional[dict[str, list[Triple]]] = None,
    write: bool = False,
    max_closes: int = 0,
    deny_model_signals: bool = True,
    starting_capital: Optional[float] = None,
    live_session: bool = False,
    session_ist_date: Optional[str] = None,
    desk_capital: Optional[float] = None,
    skip_bn_unless_last3: Optional[bool] = None,
    apply_impulse_pause: Optional[bool] = None,
    apply_target_shift: Optional[bool] = None,
    skip_banknifty: Optional[bool] = None,
    skip_sensex: Optional[bool] = None,
    sensex_need_strength: Optional[bool] = None,
    sensex_no_pause_wait: Optional[bool] = None,
    nifty_need_strength: Optional[bool] = None,
    nifty_bin_only: Optional[bool] = None,
    nifty_allow_sides: Optional[Sequence[str]] = None,
    nifty_min_abs_delta: Optional[float] = None,
    no_new_after_minutes: Optional[int] = None,
    nifty_no_flip_minutes: Optional[int] = None,
    nifty_no_pause_wait: Optional[bool] = None,
    nifty_align_impulse: Optional[bool] = None,
    nifty_skip_side_after_stop: Optional[bool] = None,
    nifty_skip_ce_after_stop: Optional[bool] = None,
    nifty_max_filled_per_book: Optional[int] = None,
    nifty_halt_after_stops: Optional[int] = None,
    nifty_session_lean: Optional[bool] = None,
    point_profile_overrides: Optional[dict[str, dict[str, float]]] = None,
    paper_hold_bars: Optional[int] = None,
    observer_veto_fills: Optional[bool] = None,
    sod_one_ticket: Optional[bool] = None,
    picker_majority: Optional[bool] = None,
    hold_trending_open_stall: bool = False,
    nifty_cover_closed_1m: Optional[bool] = None,
) -> dict[str, Any]:
    if hold_trending_open_stall and write:
        raise ValueError("hold_trending_open_stall is write=false A/B only. NO_PROMOTE.")
    base = root or repo_root()
    now = datetime.now(IST)
    session_day = session_ist_date or (now.date().isoformat() if live_session else None)
    params = load_paper_params(base) if live_session else dict(DEFAULT_PAPER_PARAMS)
    params = dict(params)
    if live_session:
        # Founder /pm START/STOP is the only NEW-fill halt. Do not auto-stop after 4 fills.
        params["nifty_max_filled_per_book"] = None
        params["skip_banknifty"] = False
        params["skip_sensex"] = False
    if session_ist_date and ((not write) or session_ist_date != now.date().isoformat()):
        params.pop("paper_book_epoch_ts", None)
    desk_total = float(
        desk_capital
        if desk_capital is not None
        else (params.get("desk_capital_inr") or DESK_CAPITAL_INR)
    )
    src = (source or "cache").strip().lower()
    tapes: dict[str, Any] = {}
    steps: dict[str, Any] = {}
    loaded: dict[str, list[Triple]] = {}

    for und in underlyings:
        u = und.upper()
        if triples_by_und is not None:
            triples = list(triples_by_und.get(u, []))
            tape = {"source": "caller", "aligned_triples": len(triples)}
            if session_day:
                triples = [t for t in triples if ist_calendar_date(int(t.ts)) == session_day]
                tape["session_ist_date"] = session_day
                tape["aligned_triples"] = len(triples)
        elif src in {"dual-tape", "dual_tape"}:
            triples, tape = load_dual_tape_triples(u, root=base, session_ist_date=session_day)
        else:
            triples, tape = load_triples(u, root=base)
            if session_day:
                triples = [t for t in triples if ist_calendar_date(int(t.ts)) == session_day]
                tape = {**tape, "session_ist_date": session_day, "aligned_triples": len(triples)}
        tapes[u] = tape
        loaded[u] = triples

    sod_on = True if sod_one_ticket is None else bool(sod_one_ticket)
    picker_on = True if picker_majority is None else bool(picker_majority)
    if sod_on:
        picker_on = True
    has_greeks = any(tape_has_dhan_greeks(loaded[u]) for u in loaded)
    tradable = tradable_fill_books(has_greeks=has_greeks, sod_one_ticket=sod_on)
    plan = allocate_desk_capital(total=desk_total, tradable=tradable)

    engine = BookEngine(
        root=base,
        deny_model_signals=deny_model_signals,
        starting_capital=STARTING_CAPITAL_INR,
        paper_stop_frac=float(params.get("stop_frac") or STOP_FRAC),
        paper_target_frac=float(params.get("target_frac") or TARGET_FRAC),
        paper_hold_bars=int(
            paper_hold_bars if paper_hold_bars is not None else (params.get("scalp_hold_bars") or SCALP_HOLD_BARS)
        ),
        paper_give_up_frac=float(params.get("give_up_frac") or GIVE_UP_FRAC),
        skip_new_when_sideways=bool(params.get("skip_sideways", True)),
        skip_trend_against=bool(params.get("skip_trend_against", True)),
        limit_discount_frac=float(params.get("limit_discount_frac") or LIMIT_DISCOUNT_FRAC),
        capital_by_book=dict(plan["per_book"]),
        capital_plan=plan,
        regime_lookback=int(params.get("regime_lookback") or REGIME_LOOKBACK),
        regime_er_max=float(params.get("regime_er_max") or REGIME_ER_MAX),
        regime_flip_min=float(params.get("regime_flip_min") or REGIME_FLIP_MIN),
        regime_range_atr_max=float(params.get("regime_range_atr_max") or REGIME_RANGE_ATR_MAX),
        paper_add_lot=bool(params.get("paper_add_lot", False)),
        paper_min_lots=int(params.get("paper_min_lots") or PAPER_MIN_LOTS),
        paper_target_lots=int(params.get("paper_target_lots") or PAPER_TARGET_LOTS),
        paper_max_lots=int(params.get("paper_max_lots") or PAPER_MAX_LOTS),
        max_target_r=float(params.get("max_target_r") or MAX_TARGET_R),
        skip_bn_unless_last3=(
            bool(skip_bn_unless_last3)
            if skip_bn_unless_last3 is not None
            else bool(params.get("skip_bn_unless_last3", True))
        ),
        apply_impulse_pause=(
            bool(apply_impulse_pause)
            if apply_impulse_pause is not None
            else bool(params.get("apply_impulse_pause", True))
        ),
        apply_target_shift=(
            bool(apply_target_shift)
            if apply_target_shift is not None
            else bool(params.get("apply_target_shift", False))
        ),
        skip_banknifty=(
            bool(skip_banknifty)
            if skip_banknifty is not None
            else bool(params.get("skip_banknifty", False))
        ),
        skip_sensex=(
            bool(skip_sensex) if skip_sensex is not None else bool(params.get("skip_sensex", False))
        ),
        sensex_need_strength=(
            bool(sensex_need_strength)
            if sensex_need_strength is not None
            else bool(params.get("sensex_need_strength", True))
        ),
        sensex_no_pause_wait=(
            bool(sensex_no_pause_wait)
            if sensex_no_pause_wait is not None
            else bool(params.get("sensex_no_pause_wait", True))
        ),
        nifty_need_strength=(
            bool(nifty_need_strength)
            if nifty_need_strength is not None
            else bool(params.get("nifty_need_strength", False))
        ),
        nifty_bin_only=(
            bool(nifty_bin_only) if nifty_bin_only is not None else bool(params.get("nifty_bin_only", False))
        ),
        nifty_allow_sides=(
            _as_side_tuple(nifty_allow_sides)
            if nifty_allow_sides is not None
            else _as_side_tuple(params.get("nifty_allow_sides"))
        ),
        nifty_min_abs_delta=(
            float(nifty_min_abs_delta)
            if nifty_min_abs_delta is not None
            else (float(params["nifty_min_abs_delta"]) if params.get("nifty_min_abs_delta") is not None else None)
        ),
        no_new_after_minutes=(
            int(no_new_after_minutes)
            if no_new_after_minutes is not None
            else (int(params["no_new_after_minutes"]) if params.get("no_new_after_minutes") is not None else None)
        ),
        nifty_no_flip_minutes=(
            int(nifty_no_flip_minutes)
            if nifty_no_flip_minutes is not None
            else (int(params["nifty_no_flip_minutes"]) if params.get("nifty_no_flip_minutes") is not None else None)
        ),
        nifty_no_pause_wait=(
            bool(nifty_no_pause_wait)
            if nifty_no_pause_wait is not None
            else bool(params.get("nifty_no_pause_wait", False))
        ),
        nifty_align_impulse=(
            bool(nifty_align_impulse)
            if nifty_align_impulse is not None
            else bool(params.get("nifty_align_impulse", False))
        ),
        nifty_skip_side_after_stop=(
            bool(nifty_skip_side_after_stop)
            if nifty_skip_side_after_stop is not None
            else bool(params.get("nifty_skip_side_after_stop", False))
        ),
        nifty_skip_ce_after_stop=(
            bool(nifty_skip_ce_after_stop)
            if nifty_skip_ce_after_stop is not None
            else bool(params.get("nifty_skip_ce_after_stop", False))
        ),
        nifty_max_filled_per_book=(
            int(nifty_max_filled_per_book)
            if nifty_max_filled_per_book is not None
            else (
                int(params["nifty_max_filled_per_book"])
                if params.get("nifty_max_filled_per_book") is not None
                else None
            )
        ),
        nifty_halt_after_stops=(
            int(nifty_halt_after_stops)
            if nifty_halt_after_stops is not None
            else (
                int(params["nifty_halt_after_stops"])
                if params.get("nifty_halt_after_stops") is not None
                else None
            )
        ),
        nifty_session_lean=(
            bool(nifty_session_lean)
            if nifty_session_lean is not None
            else bool(params.get("nifty_session_lean", False))
        ),
        point_profile_overrides=dict(point_profile_overrides or params.get("point_profile_overrides") or {}),
        observer_veto_fills=(
            bool(observer_veto_fills)
            if observer_veto_fills is not None
            else bool(params.get("observer_veto_fills", True))
        ),
        sod_one_ticket=sod_on,
        picker_majority=picker_on,
        hold_trending_open_stall=bool(hold_trending_open_stall),
        nifty_cover_closed_1m=(
            bool(nifty_cover_closed_1m)
            if nifty_cover_closed_1m is not None
            else bool(params.get("nifty_cover_closed_1m", True))
        ),
    )
    for book_id in LIVE_BOOKS:
        engine.equity[book_id] = float(plan["per_book"].get(book_id) or 0.0)
    for und in ("NIFTY", "BANKNIFTY", "SENSEX"):
        engine.lot_by_und[und] = resolve_lot_size(und, root=base)

    for und in underlyings:
        u = und.upper()
        triples = loaded.get(u, [])
        tape = tapes.get(u) or {}
        if len(triples) < 8:
            steps[u] = {
                "status": "DATA_INSUFFICIENT",
                "reason": "need ≥8 aligned INDEX+ATM dual-tape prints (10s ticks count; do not fabricate bars)",
                "tape": tape,
            }
            continue
        ml001, ml002, gap, hold_meta = _hold_series(triples)
        idx_closes = load_index_closes(u, root=base)
        if triples_by_und is not None:
            idx_closes = {int(t.ts): float(t.idx_close) for t in triples}
        sr_closes = dict(load_index_closes(u, root=base))
        sr_closes.update({int(t.ts): float(t.idx_close) for t in triples})
        sr_day = session_day or (ist_calendar_date(int(triples[-1].ts)) if triples else None)
        if sr_day:
            engine.sr_levels[u] = build_sr_levels(sr_closes, session_ist_date=sr_day)
        logit_series, logit_meta = logit_side_series(triples, index_closes=idx_closes, xr=False)
        logit_xr_series, logit_xr_meta = logit_side_series(triples, index_closes=idx_closes, xr=True)
        thin_logit = {
            "side": None,
            "status": "DATA_INSUFFICIENT",
            "reason": "no logit series",
        }
        ml1 = ml1_meta_label([])
        idx_path: list[float] = []
        epoch_ts = None
        raw_epoch = params.get("paper_book_epoch_ts")
        if raw_epoch is not None:
            try:
                epoch_ts = int(raw_epoch)
            except (TypeError, ValueError):
                epoch_ts = None
        for i, tick in enumerate(triples):
            idx_path.append(tick.idx_close)
            if epoch_ts is not None and int(tick.ts) < epoch_ts:
                continue
            h1 = ml001[i] if i < len(ml001) else False
            h2 = ml002[i] if i < len(ml002) else False
            g = gap[i] if i < len(gap) else False
            tv = tv_ep_024_side(idx_path)
            logit = logit_series[i] if i < len(logit_series) else thin_logit
            logit_xr = logit_xr_series[i] if i < len(logit_xr_series) else thin_logit
            # Recompute ML-1 as closes accumulate (still DI until 30).
            ml1 = ml1_meta_label(engine.closed)
            step_underlying(
                engine,
                underlying=u,
                triples=triples,
                i=i,
                ml001_hold=h1,
                ml002_hold=h2,
                follow_gap=g,
                logit=logit,
                logit_xr=logit_xr,
                ml1=ml1,
                tv_side=tv,
                deny_model_signals=deny_model_signals,
            )
            if max_closes > 0 and len(engine.closed) >= max_closes:
                break
        if max_closes > 0 and len(engine.closed) >= max_closes:
            break
        # Live session keeps WORKING/OPEN only before 15:16 IST. After flatten, leftovers close.
        last = triples[-1]
        past_flat = minutes_ist(last.ts) >= FLATTEN_MINUTES_IST
        if (not live_session) or past_flat:
            last = triples[-1]
            for book_id in LIVE_BOOKS:
                pos = engine.opens.get((book_id, u))
                if pos is None:
                    continue
                ltp = last.ce_close if pos.side == "CE" else last.pe_close
                reason = "CANCEL_UNFILLED_FLAT" if not pos.filled else ("FLATTEN_1516" if past_flat else "REPLAY_END")
                _close(engine, pos, ltp=float(ltp), ts=last.ts, reason=reason, root=base)
        steps[u] = {
            "status": "REPLAY_OK",
            "n_triples": len(triples),
            "hold_meta": hold_meta,
            "logit": logit_meta,
            "logit_xr": logit_xr_meta,
            "ml1": ml1,
            "tape": tape,
            "index_regime": engine.last_regime.get(u),
            "span_ist": {
                "first": _ist_dt(triples[0].ts).isoformat(timespec="seconds"),
                "last": _ist_dt(triples[-1].ts).isoformat(timespec="seconds"),
            },
        }

    nudge_notes: list[str] = []
    if live_session and write:
        params, nudge_notes = nudge_paper_params(engine.closed, params)
        save_paper_params(base, params)
        engine.paper_stop_frac = float(params["stop_frac"])
        engine.paper_target_frac = float(params["target_frac"])
        engine.paper_hold_bars = int(params["scalp_hold_bars"])
        engine.paper_give_up_frac = float(params.get("give_up_frac") or GIVE_UP_FRAC)

    board = build_dashboard(
        engine,
        tapes=tapes,
        steps=steps,
        as_of_ist=now.isoformat(timespec="seconds"),
        source=src,
        root=base,
        live_session=live_session,
        session_ist_date=session_day,
        paper_params=params,
        paper_param_notes=nudge_notes,
    )
    if write:
        write_dashboard(board, root=base)
        _append_mistakes(base, board.get("mistakes") or [])
    return board


def list_fix_first_days(*, root: Optional[Path] = None, since: str = FIX_FIRST_SINCE_IST) -> list[str]:
    folder = (root or repo_root()) / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    if not folder.is_dir():
        return []
    days: list[str] = []
    for path in sorted(folder.glob("*.jsonl")):
        day = path.stem
        if len(day) == 10 and day[4] == "-" and day >= since:
            days.append(day)
    return days


def skill_from_closed(
    closed: Sequence[dict[str, Any]],
    skips: Sequence[dict[str, Any]] | None = None,
    skip_counts: Optional[dict[str, int]] = None,
) -> dict[str, Any]:
    """FIX-FIRST skill card: booking vs sitting. Not a promote wr."""
    unique = [
        r
        for r in closed
        if r.get("filled") and str(r.get("book_id") or "") in UNIQUE_PNL_BOOKS
    ]
    dealer = [r for r in unique if str(r.get("book_id")) == FIX_FIRST_SKILL_BOOK]
    rows = dealer or unique
    reasons = Counter(str(r.get("exit_reason") or "") for r in rows)
    nets = [_net_or_points(r) for r in rows]
    n_green = sum(1 for p in nets if p > 0)
    n_target = sum(1 for r in rows if str(r.get("exit_reason")) == "TARGET" or r.get("target_hit"))
    n_stall = (
        int(reasons.get("CANCEL_STALL", 0))
        + int(reasons.get("CANCEL_NO_PROGRESS", 0))
        + int(reasons.get("CANCEL_BOOK_NEAR", 0))
    )
    n_unwind = reasons.get("COVER_LONG_UNWIND", 0)
    n_time = reasons.get("TIME", 0)
    n_stop = sum(1 for r in rows if r.get("sl_hit") or str(r.get("exit_reason")) == "STOP")
    n_green_not_target = sum(
        1
        for r, p in zip(rows, nets)
        if p > 0 and str(r.get("exit_reason")) != "TARGET" and not r.get("target_hit")
    )
    skip_reasons = Counter(
        str(s.get("reason") or "")
        for s in (skips or [])
        if str(s.get("underlying") or "").upper() in {"NIFTY", ""}
    )
    if skip_counts:
        skip_reasons.update({str(k): int(v) for k, v in skip_counts.items()})
    lessons: list[str] = []
    if n_green_not_target:
        lessons.append(
            f"{n_green_not_target} green fill(s) never printed TARGET — book sooner in chop (STALL / cap)."
        )
    if reasons.get("CANCEL_AGAINST") and n_target == 0:
        lessons.append("CANCEL_AGAINST without TARGET: against-wing / last-3 flicker vs holding a runner.")
    if n_unwind:
        lessons.append("LONG_UNWIND printed — flatten the dying wing; do not wait T1 in chop.")
    if n_stop:
        lessons.append("STOP: side or noise stop — skip weak last-3, do not rebuy the same wing immediately.")
    if skip_reasons.get("NIFTY_MAX_FILLED"):
        lessons.append("Session cap consumed — no NEW until epoch/next day. Skill cannot print if the book is full.")
    if skip_reasons.get("NIFTY_WAIT_STRENGTH") and not n_target:
        lessons.append("WAIT_STRENGTH skipped NEW while last-3 was pause-wait — bin confirm should still fill.")
    if not lessons and rows:
        lessons.append("Keep: path SL then first TARGET; STALL in ER<0.35; against only if dead.")
    if not rows:
        lessons.append("DATA_INSUFFICIENT or no unique fills this day.")
    tagged: list[dict[str, Any]] = []
    kind_counts: Counter[str] = Counter()
    kind_exits: dict[str, Counter[str]] = {}
    open_exits: dict[str, Counter[str]] = {}
    n_stall_trending_open = 0
    for row in rows:
        open_kind = market_kind_from_row(row, at="open")
        close_kind = market_kind_from_row(row, at="close")
        reason = str(row.get("exit_reason") or "")
        tagged.append({**row, "market_kind": close_kind, "market_kind_open": open_kind, "market_kind_close": close_kind})
        kind_counts[open_kind] += 1
        kind_exits.setdefault(close_kind, Counter())[reason] += 1
        open_exits.setdefault(open_kind, Counter())[reason] += 1
        if open_kind == "TRENDING" and reason == "CANCEL_STALL":
            n_stall_trending_open += 1
    kind_notes = booking_vs_kind_notes(tagged)
    lessons = (kind_notes + lessons)[:8]
    return {
        "n_filled_unique": len(unique),
        "n_filled_dealer": len(dealer),
        "n_wins": n_green,
        "n_losses": sum(1 for p in nets if p <= 0),
        "win_rate_net_pct": paper_hit_rate_pct(nets) if nets else None,
        "net_pnl_inr": round(sum(nets), 2) if nets else 0.0,
        "n_target": n_target,
        "n_stall": n_stall,
        "n_against": int(reasons.get("CANCEL_AGAINST", 0)),
        "n_unwind": n_unwind,
        "n_time": n_time,
        "n_stop": n_stop,
        "n_green_not_target": n_green_not_target,
        "n_stall_trending_open": n_stall_trending_open,
        "exit_reasons": dict(reasons),
        "fills_by_kind": dict(kind_counts),
        "exits_by_kind": {k: dict(v) for k, v in kind_exits.items()},
        "exits_by_open_kind": {k: dict(v) for k, v in open_exits.items()},
        "nifty_skip_reasons": {k: v for k, v in skip_reasons.items() if k.startswith("NIFTY_")},
        "lessons": lessons[:8],
        "founder_bar": "70% day / worst 60% after Groww is the GOAL, not this board.",
        "promote": False,
    }


def signal_from_closed(
    closed: Sequence[dict[str, Any]],
    *,
    book_rank: Optional[Sequence[dict[str, Any]]] = None,
    skip_counts: Optional[dict[str, int]] = None,
) -> dict[str, Any]:
    """Signal desk card: dealer vs ML own-side. Booking overlay is not scored here."""
    ranks = list(book_rank or rank_books_net(closed))
    by = {str(r.get("book_id")): r for r in ranks}

    def _row(book_id: str) -> dict[str, Any]:
        r = by.get(book_id) or {}
        return {
            "book_id": book_id,
            "kind": r.get("kind"),
            "n_filled": int(r.get("n_filled") or 0),
            "n_wins": int(r.get("n_wins") or 0),
            "n_losses": int(r.get("n_losses") or 0),
            "win_rate_net_pct": r.get("win_rate_net_pct"),
            "net_pnl_inr": float(r.get("sum_pnl_inr") or 0.0),
        }

    dealer = _row("MIX-DEFAULT-BUY")
    logit = _row("MIX-ML-LOGIT")
    xr = _row("MIX-ML-LOGIT-XR")
    greeks = _row("MIX-ML-GREEKS")
    observe = [_row(b) for b in OBSERVE_ONLY_BOOKS]
    clone = (
        dealer["n_filled"] > 0
        and dealer["n_filled"] == logit["n_filled"]
        and abs(dealer["net_pnl_inr"] - logit["net_pnl_inr"]) < 1.0
    )
    notes: list[str] = []
    if clone:
        notes.append(
            "LOGIT cloned dealer this tape — same n and net. Improve dealer CE/PE first, "
            "or give logit a side that is not the dealer echo."
        )
    if xr["n_filled"] and xr["net_pnl_inr"] > dealer["net_pnl_inr"] + 1:
        notes.append(
            "XR beat dealer this tape — more sessions before XR is a customer default."
        )
    if greeks["n_filled"] == 0:
        notes.append("GREEKS 0 fills — need live chain greeks; do not invent IV.")
    if all(r["n_filled"] == 0 for r in observe):
        notes.append(
            "ML-001 / ML-002 / ML-1 / TV observe (no own CE/PE). Score what they vetoed; do not clone dealer."
        )
    skips = skip_counts or {}
    if skips.get("NIFTY_WAIT_STRENGTH"):
        notes.append(
            f"WAIT_STRENGTH {skips.get('NIFTY_WAIT_STRENGTH')} — dealer-only skip; logit may still fill."
        )
    if not notes:
        notes.append("Signal books printed distinct sides — keep scoring vs hour-kind before a recode.")
    fill_books = [dealer, logit, xr, greeks]
    best = max(fill_books, key=lambda r: (r["n_filled"] > 0, r["net_pnl_inr"]))
    return {
        "desk": "SIGNAL",
        "dealer": dealer,
        "logit": logit,
        "logit_xr": xr,
        "greeks": greeks,
        "observe": observe,
        "logit_cloned_dealer": clone,
        "best_fill_book": best["book_id"] if best["n_filled"] else None,
        "notes": notes[:8],
        "promote": False,
        "note": (
            "Dealer + ML own-side. Booking STALL/TARGET is FIX-FIRST, not this card. "
            "Do not recode a model from one day."
        ),
    }


def booking_vs_kind_notes(rows: Sequence[dict[str, Any]]) -> list[str]:
    """Replay observations. Suggestions only — do not recode overlay from this."""
    notes: list[str] = []
    n_trend_open_stall = 0
    by_close: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        open_k = str(row.get("market_kind_open") or market_kind_from_row(row, at="open"))
        close_k = str(row.get("market_kind_close") or row.get("market_kind") or market_kind_from_row(row, at="close"))
        reason = str(row.get("exit_reason") or "")
        by_close.setdefault(close_k, []).append(row)
        if open_k == "TRENDING" and reason == "CANCEL_STALL":
            n_trend_open_stall += 1
    if n_trend_open_stall:
        notes.append(
            f"WATCH: {n_trend_open_stall} STALL on TRENDING-at-open — retracement vs flip by exit; "
            "do not recode hold until that ticket path is reviewed."
        )
    for kind, group in by_close.items():
        reasons = Counter(str(r.get("exit_reason") or "") for r in group)
        if kind in {"SIDEWAYS", "CHOPPY"} and reasons.get("TIME") and not reasons.get("CANCEL_STALL"):
            notes.append(
                f"{kind} at exit: TIME without STALL — discuss sitting in quiet tape vs booking."
            )
        if kind == "VOLATILE" and reasons.get("STOP"):
            notes.append(
                f"{kind} at exit: {reasons.get('STOP')} STOP — more days before a VOLATILE-specific recode."
            )
        if kind == "CHOPPY" and reasons.get("CANCEL_STALL"):
            notes.append(f"{kind} at exit: STALL printed — chop booking is doing the hour job.")
    return notes[:8]


def categorize_tape_hours(
    *,
    root: Optional[Path] = None,
    session_ist_date: str,
    underlying: str = "NIFTY",
) -> dict[str, Any]:
    """1m INDEX walk → hour labels. write=false diagnostic. Does not change fills."""
    triples, tape = load_dual_tape_triples(
        underlying, root=root or repo_root(), session_ist_date=session_ist_date
    )
    ticks = [(int(t.ts), float(t.idx_close), getattr(t, "idx_volume", None)) for t in triples]
    bars, vols = index_1m_ohlcv_from_ticks(ticks)
    hour_counts: dict[str, Counter[str]] = {}
    closes: list[float] = []
    vol_win: list[Optional[float]] = []
    ohlc: list[dict[str, Any]] = []
    for i, bar in enumerate(bars):
        mins = minutes_ist(int(bar["ts"]))
        if mins < (9 * 60 + 15) or mins > (15 * 60 + 30):
            continue
        closes.append(float(bar["close"]))
        vol_win.append(vols[i] if i < len(vols) else None)
        ohlc.append(bar)
        hour = _ist_dt(int(bar["ts"])).strftime("%H:00")
        cl = classify_index_regime(closes, volumes=vol_win, ohlc=ohlc)
        kind = market_kind(cl)
        hour_counts.setdefault(hour, Counter())[kind] += 1
    hours: list[dict[str, Any]] = []
    day_counts: Counter[str] = Counter()
    for hour in sorted(hour_counts):
        c = hour_counts[hour]
        day_counts.update(c)
        top, n = c.most_common(1)[0]
        hours.append({"ist_hour": hour, "kind": top, "n_1m": int(sum(c.values())), "counts": dict(c)})
    dominant = day_counts.most_common(1)[0][0] if day_counts else "UNKNOWN"
    return {
        "ok": True,
        "session_ist_date": session_ist_date,
        "underlying": underlying.upper(),
        "n_1m": len(bars),
        "tape": {"aligned_triples": tape.get("aligned_triples") if isinstance(tape, dict) else None},
        "day_kind": dominant,
        "day_counts": dict(day_counts),
        "hours": hours,
        "promote": False,
        "note": (
            "Hour kind from INDEX 1m ER/flips/range drives booking review. "
            "day_kind is majority diagnostic only — mixed lunch vs afternoon is two tickets. "
            "itm_bin TREND is not tape trend. Overlay exits unchanged."
        ),
    }


def run_fix_first_drill(
    *,
    root: Optional[Path] = None,
    since: str = FIX_FIRST_SINCE_IST,
    persist: bool = True,
    underlyings: Sequence[str] = ("NIFTY",),
) -> dict[str, Any]:
    """Pre-open candle-by-candle paper replay from 17 Sep. write=false. Track booking skill."""
    base = root or repo_root()
    now = datetime.now(IST)
    days = list_fix_first_days(root=base, since=since)
    day_cards: list[dict[str, Any]] = []
    for day in days:
        board = replay_paper_scalp(
            root=base,
            underlyings=tuple(underlyings) or ("NIFTY",),
            source="dual-tape",
            write=False,
            deny_model_signals=True,
            live_session=True,
            session_ist_date=day,
        )
        skill = skill_from_closed(
            board.get("closed_trades") or [],
            skip_counts=board.get("skip_reason_counts") or {},
        )
        signal = signal_from_closed(
            board.get("closed_trades") or [],
            book_rank=board.get("book_rank") or [],
            skip_counts=board.get("skip_reason_counts") or {},
        )
        tape_kinds = categorize_tape_hours(
            root=base, session_ist_date=day, underlying="NIFTY"
        )
        n_triples = ((board.get("steps") or {}).get("NIFTY") or {}).get("n_triples")
        day_cards.append(
            {
                "ist_date": day,
                "ok": bool(board.get("ok")),
                "n_open": len(board.get("open_trades") or []),
                "n_triples": n_triples,
                "steps_status": ((board.get("steps") or {}).get("NIFTY") or {}).get("status"),
                "tape_kinds": {
                    "day_kind": tape_kinds.get("day_kind"),
                    "day_counts": tape_kinds.get("day_counts"),
                    "hours": tape_kinds.get("hours"),
                    "n_1m": tape_kinds.get("n_1m"),
                },
                "signal_desk": signal,
                **skill,
            }
        )
    deltas: list[dict[str, Any]] = []
    for i in range(1, len(day_cards)):
        prev, cur = day_cards[i - 1], day_cards[i]

        def _num(row: dict[str, Any], key: str) -> float:
            try:
                return float(row.get(key) if row.get(key) is not None else 0)
            except (TypeError, ValueError):
                return 0.0

        deltas.append(
            {
                "from": prev["ist_date"],
                "to": cur["ist_date"],
                "wr_pp": None
                if prev.get("win_rate_net_pct") is None or cur.get("win_rate_net_pct") is None
                else round(_num(cur, "win_rate_net_pct") - _num(prev, "win_rate_net_pct"), 2),
                "net_pnl_inr": round(_num(cur, "net_pnl_inr") - _num(prev, "net_pnl_inr"), 2),
                "n_target": int(_num(cur, "n_target") - _num(prev, "n_target")),
                "n_stall": int(_num(cur, "n_stall") - _num(prev, "n_stall")),
                "n_green_not_target": int(_num(cur, "n_green_not_target") - _num(prev, "n_green_not_target")),
            }
        )
    last = day_cards[-1] if day_cards else {}
    improve = list(last.get("lessons") or [])
    watch: list[str] = [
        "Hour kind drives booking; do not overlay the whole day from majority.",
        "itm_bin TREND is ignored — lunch ER ~0.05 is chop even if the bin says TREND.",
        "TRENDING-at-open STALL is the retracement ticket — more sessions before hold recode.",
        "VOLATILE-specific exits wait more days. Code only after pre/post drills agree.",
    ]
    for card in day_cards:
        n_watch = int(card.get("n_stall_trending_open") or 0)
        if n_watch:
            watch.insert(
                0,
                f"{card.get('ist_date')}: {n_watch} STALL on TRENDING-at-open — path review before hold change.",
            )
        sig = card.get("signal_desk") or {}
        if sig.get("logit_cloned_dealer"):
            watch.append(f"{card.get('ist_date')}: logit cloned dealer — signal-desk work, not booking.")
        best = sig.get("best_fill_book")
        if best and best not in {None, "MIX-DEFAULT-BUY"}:
            watch.append(f"{card.get('ist_date')}: best fill book {best} — more days before a default swap.")
    if not days:
        improve = [f"No dual-tape jsonl on/after {since}."]
    payload = {
        "ok": True,
        "job": "FIX_FIRST_DRILL",
        "as_of_ist": now.isoformat(timespec="seconds"),
        "since": since,
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "promote": False,
        "production_params_written": False,
        "write": False,
        "overlay_recode": False,
        "note": (
            "Pre/post-market write=false replay from 17 Sep IST. Same ship overlay. "
            "Fill market_kind = open ER (missing → UNKNOWN). Exit market_kind stamped too. "
            "Hour kind scores booking. signal_desk scores dealer vs ML. "
            "Recode only after more sessions agree. Not a wr claim."
        ),
        "days": day_cards,
        "day_over_day": deltas,
        "watch": watch[:8],
        "improve_next": (watch[:4] + improve)[:8],
        "cli": "python -m desk_ml fix-first",
        "pre_market": "python -m jobs pre-market",
        "post_market": "python -m jobs post-market",
    }
    if persist:
        recon = base / "data" / "recon"
        recon.mkdir(parents=True, exist_ok=True)
        path = recon / FIX_FIRST_PROGRESS_NAME
        history: list[dict[str, Any]] = []
        if path.is_file():
            try:
                prev = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                prev = {}
            if isinstance(prev, dict):
                history = list(prev.get("history") or [])
                prior_as_of = prev.get("as_of_ist")
                if prior_as_of and prior_as_of != payload.get("as_of_ist"):
                    history.append(
                        {
                            "as_of_ist": prior_as_of,
                            "day_over_day": prev.get("day_over_day"),
                            "improve_next": prev.get("improve_next"),
                            "watch": prev.get("watch"),
                            "days": [
                                {
                                    "ist_date": d.get("ist_date"),
                                    "n_target": d.get("n_target"),
                                    "n_stall": d.get("n_stall"),
                                    "n_stall_trending_open": d.get("n_stall_trending_open"),
                                    "net_pnl_inr": d.get("net_pnl_inr"),
                                    "win_rate_net_pct": d.get("win_rate_net_pct"),
                                    "fills_by_kind": d.get("fills_by_kind"),
                                    "exits_by_kind": d.get("exits_by_kind"),
                                }
                                for d in (prev.get("days") or [])
                            ],
                        }
                    )
        payload["history"] = history[-14:]
        path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
        payload["path"] = str(path)
    return payload


def stamp_paper_book_epoch(*, root: Optional[Path] = None) -> dict[str, Any]:
    """New paper book after this unix ts. Dual-tape JSONL stays. Does not wipe fills from disk history."""
    base = root or repo_root()
    now = datetime.now(IST)
    epoch_ts = int(now.timestamp())
    cur = load_paper_params(base)
    save_paper_params(
        base,
        {
            **cur,
            **OVERLAY_SHIP,
            "paper_book_epoch_ts": epoch_ts,
            "paper_book_epoch_ist": now.isoformat(timespec="seconds"),
        },
    )
    return {
        "ok": True,
        "paper_book_epoch_ts": epoch_ts,
        "paper_book_epoch_ist": now.isoformat(timespec="seconds"),
        "note": "NEW paper ignores dual-tape ticks before epoch. JSONL kept. NO_PROMOTE.",
    }


def _book_what(book_id: str) -> str:
    return {
        "MIX-DEFAULT-BUY": "Dealer CE/PE from INDEX vs ATM CE/PE deltas. Customer default ID; PAPER only.",
        "ML-001": "KMeans+IsolationForest overlay. SKIP if HOLD/FOLLOW-GAP. Does not invent CE/PE.",
        "ML-002": "OU residual |z|≥2 or FOLLOW-GAP SKIP. Windows 40/60/90. Does not invent CE/PE.",
        "ML-1": "Meta-label take/skip on closed paper labels. Else DATA_INSUFFICIENT.",
        "MIX-ML-LOGIT": "INDEX 3m walk-forward logit (ml_leans.py). Scan book. Not customer default.",
        "MIX-ML-LOGIT-XR": "Logit AND range-expansion. Scan book. Not customer default.",
        "MIX-TV-EP-024": "Factory SMA20 INDEX calibrator → ATM CE/PE. KEEP_ALL lab. Not a promote.",
        "MIX-ML-GREEKS": "TOKEN_ML ML-2 paper: Dhan delta/IV/theta/gamma. HOLD rich vol / late theta / missing greeks. Not customer default.",
    }.get(book_id, book_id)


def _net_or_points(row: dict[str, Any]) -> float:
    if row.get("realized_pnl_inr") is not None:
        return float(row["realized_pnl_inr"])
    return float(row.get("realized_pnl") or 0.0)


def _sum_opt(vals: Sequence[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in vals if v is not None]
    if not nums:
        return None
    return round(sum(nums), 2)


def leaderboard_closed(closed: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in closed:
        if str(row.get("result")) == "CANCELLED":
            continue
        key = (str(row["book_id"]), str(row["underlying"]))
        buckets.setdefault(key, []).append(row)
    out = []
    for (book, und), rows in sorted(buckets.items()):
        nets = [_net_or_points(r) for r in rows]
        pts = [float(r["realized_pnl"]) for r in rows]
        gross_vals = [float(r["gross_pnl_inr"]) for r in rows if r.get("gross_pnl_inr") is not None]
        if not gross_vals:
            gross_vals = pts
        chg = [r.get("charges_inr") for r in rows]
        out.append(
            {
                "book_id": book,
                "underlying": und,
                "n_closed": len(nets),
                "n_wins": sum(1 for p in nets if p > 0),
                "n_losses": sum(1 for p in nets if p <= 0),
                "n_wins_gross": sum(1 for p in gross_vals if p > 0),
                "n_losses_gross": sum(1 for p in gross_vals if p <= 0),
                "sum_premium_pnl": round(sum(pts), 4),
                "sum_gross_pnl_inr": _sum_opt([r.get("gross_pnl_inr") for r in rows]),
                "sum_charges_inr": _sum_opt(chg),
                "sum_pnl_inr": round(sum(nets), 2),
                "win_rate": paper_hit_rate(nets),
                "win_rate_pct": paper_hit_rate_pct(nets),
                "win_rate_net_pct": paper_hit_rate_pct(nets),
                "win_rate_gross": paper_hit_rate(gross_vals),
                "win_rate_gross_pct": paper_hit_rate_pct(gross_vals),
                "win_rate_kind": "paper_closed_net_inr_gt_0_after_groww_stt",
                "win_rate_gross_kind": "paper_closed_gross_inr_gt_0_before_groww_stt",
                "rank_metric": "closed_net_pnl_inr_after_groww_stt",
            }
        )
    out.sort(key=lambda r: r["sum_pnl_inr"], reverse=True)
    for i, row in enumerate(out, start=1):
        row["rank"] = i
    return out


def rank_books_net(closed: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    cancelled: dict[str, int] = {}
    for row in closed:
        book = str(row["book_id"])
        if str(row.get("result")) == "CANCELLED":
            cancelled[book] = cancelled.get(book, 0) + 1
            continue
        buckets.setdefault(book, []).append(row)
    out = []
    for book in LIVE_BOOKS:
        rows = buckets.get(book, [])
        nets = [_net_or_points(r) for r in rows]
        gross_vals = [float(r["gross_pnl_inr"]) for r in rows if r.get("gross_pnl_inr") is not None]
        out.append(
            {
                "rank": 0,
                "book_id": book,
                "kind": "ML" if book in ML_BOOK_IDS else ("DESK" if book == "MIX-DEFAULT-BUY" else "LAB"),
                "n_filled": len(rows),
                "n_cancelled": cancelled.get(book, 0),
                "n_wins": sum(1 for p in nets if p > 0),
                "n_losses": sum(1 for p in nets if p <= 0),
                "n_wins_gross": sum(1 for p in gross_vals if p > 0),
                "n_losses_gross": sum(1 for p in gross_vals if p <= 0),
                "sum_gross_pnl_inr": _sum_opt([r.get("gross_pnl_inr") for r in rows]),
                "sum_charges_inr": _sum_opt([r.get("charges_inr") for r in rows]),
                "sum_pnl_inr": round(sum(nets), 2) if nets else 0.0,
                "win_rate_pct": paper_hit_rate_pct(nets),
                "win_rate_net_pct": paper_hit_rate_pct(nets),
                "win_rate_gross_pct": paper_hit_rate_pct(gross_vals),
                "starting_capital_inr": None,
            }
        )
    out.sort(key=lambda r: (int(r["n_filled"]) > 0, r["sum_pnl_inr"]), reverse=True)
    for i, row in enumerate(out, start=1):
        row["rank"] = i
    return out


def today_picture(closed: Sequence[dict[str, Any]], book_rank: Sequence[dict[str, Any]]) -> dict[str, Any]:
    filled = [r for r in closed if _row_filled(r)]
    cancelled = [r for r in closed if str(r.get("result")) == "CANCELLED"]
    nets = [_net_or_points(r) for r in filled]
    gross_vals = [float(r["gross_pnl_inr"]) for r in filled if r.get("gross_pnl_inr") is not None]
    gross = _sum_opt([r.get("gross_pnl_inr") for r in filled]) or 0.0
    charges = _sum_opt([r.get("charges_inr") for r in filled]) or 0.0
    brokerage = _sum_opt([r.get("brokerage_inr") for r in filled]) or 0.0
    gst = _sum_opt([r.get("gst_inr") for r in filled]) or 0.0
    stt = _sum_opt([r.get("stt_inr") for r in filled]) or 0.0
    exchange = _sum_opt([r.get("exchange_inr") for r in filled]) or 0.0
    sebi = _sum_opt([r.get("sebi_inr") for r in filled]) or 0.0
    stamp = _sum_opt([r.get("stamp_inr") for r in filled]) or 0.0
    net = round(sum(nets), 2) if nets else 0.0
    by_und: dict[str, float] = {}
    for r in filled:
        u = str(r.get("underlying") or "?")
        by_und[u] = round(by_und.get(u, 0.0) + _net_or_points(r), 2)
    best_und = max(by_und, key=by_und.get) if by_und else None
    worst_und = min(by_und, key=by_und.get) if by_und else None
    best_book = book_rank[0] if book_rank else None
    worst_book = book_rank[-1] if book_rank else None
    ml_rows = [r for r in book_rank if r.get("kind") == "ML" and int(r.get("n_filled") or 0) > 0]
    if not ml_rows:
        ml_rows = [r for r in book_rank if r.get("kind") == "ML"]
    best_ml = ml_rows[0] if ml_rows else None
    unique_rows = [r for r in book_rank if r["book_id"] in UNIQUE_PNL_BOOKS]
    unique_net = round(sum(float(r.get("sum_pnl_inr") or 0) for r in unique_rows), 2)
    unique_by_und: dict[str, float] = {}
    for r in filled:
        if str(r.get("book_id")) not in UNIQUE_PNL_BOOKS:
            continue
        u = str(r.get("underlying") or "?")
        unique_by_und[u] = round(unique_by_und.get(u, 0.0) + _net_or_points(r), 2)
    n_sl_hit = sum(1 for r in filled if r.get("sl_hit"))
    n_target_hit = sum(1 for r in filled if r.get("target_hit") or str(r.get("exit_reason")) == "TARGET")
    n_time_exit = sum(1 for r in filled if str(r.get("exit_reason")) == "TIME")
    regime_counts: dict[str, int] = {}
    for r in filled:
        key = str(r.get("index_regime") or "UNKNOWN")
        regime_counts[key] = regime_counts.get(key, 0) + 1
    return {
        "n_tickets": len(closed),
        "n_filled": len(filled),
        "n_cancelled": len(cancelled),
        "n_wins": sum(1 for p in nets if p > 0),
        "n_losses": sum(1 for p in nets if p <= 0),
        "n_wins_gross": sum(1 for p in gross_vals if p > 0),
        "n_losses_gross": sum(1 for p in gross_vals if p <= 0),
        "win_rate_net_pct": paper_hit_rate_pct(nets),
        "win_rate_gross_pct": paper_hit_rate_pct(gross_vals),
        "gross_pnl_inr": round(gross, 2),
        "brokerage_inr": round(brokerage, 2),
        "gst_inr": round(gst, 2),
        "stt_inr": round(stt, 2),
        "exchange_inr": round(exchange, 2),
        "sebi_inr": round(sebi, 2),
        "stamp_inr": round(stamp, 2),
        "charges_inr": round(charges, 2),
        "net_pnl_inr": net,
        "net_by_index": by_und,
        "best_index": best_und,
        "worst_index": worst_und,
        "best_book": None if best_book is None else dict(best_book),
        "worst_book": None if worst_book is None else dict(worst_book),
        "best_ml_book": None if best_ml is None else dict(best_ml),
        "unique_books": list(UNIQUE_PNL_BOOKS),
        "unique_net_pnl_inr": unique_net,
        "unique_net_by_index": unique_by_und,
        "n_sl_hit": n_sl_hit,
        "n_target_hit": n_target_hit,
        "n_time_exit": n_time_exit,
        "filled_by_index_regime": regime_counts,
        "cost_model": groww_cost_meta(),
    }


def sod_ab_row(board: dict[str, Any]) -> dict[str, Any]:
    """OLD vs NEW replay card. Unique net = UNIQUE_PNL_BOOKS. Not founder wr."""
    closed = board.get("closed_trades") or []
    skips = board.get("skip_reason_counts") or {}
    filled = [r for r in closed if r.get("filled")]
    unique_filled = [r for r in filled if str(r.get("book_id") or "") in UNIQUE_PNL_BOOKS]
    unique_net = round(sum(_net_or_points(r) for r in unique_filled), 2)

    def _book(bid: str) -> tuple[float, int]:
        rows = [r for r in filled if str(r.get("book_id")) == bid]
        return round(sum(_net_or_points(r) for r in rows), 2), len(rows)

    dealer_net, dealer_n = _book("MIX-DEFAULT-BUY")
    logit_net, logit_n = _book("MIX-ML-LOGIT")
    nets = [_net_or_points(r) for r in unique_filled]
    return {
        "n_filled_all_books": len(filled),
        "n_filled": len(unique_filled),
        "unique_net_pnl_inr": unique_net,
        "dealer_net_pnl_inr": dealer_net,
        "dealer_n": dealer_n,
        "logit_net_pnl_inr": logit_net,
        "logit_n": logit_n,
        "paper_hit_rate_net_pct": paper_hit_rate_pct(nets),
        "n_skip_follow_gap": int(skips.get("FOLLOW_GAP") or 0),
        "n_skip_hold_majority": int(skips.get("HOLD_MAJORITY") or 0),
        "n_skip_one_open": int(skips.get("SOD_ONE_OPEN") or 0),
        "n_skip_lab_observe": int(skips.get("SOD_LAB_OBSERVE") or 0),
        "n_skip_max_filled": int(skips.get("NIFTY_MAX_FILLED") or 0),
        "promote": False,
        "research_ready_for_programming": False,
        "unique_books": list(UNIQUE_PNL_BOOKS),
    }


def index_adjustment_notes(
    closed: Sequence[dict[str, Any]],
    book_rank: Sequence[dict[str, Any]],
    leaderboard: Sequence[dict[str, Any]],
    net_by_index: Optional[dict[str, float]] = None,
) -> list[str]:
    notes: list[str] = []
    greeks = next((r for r in book_rank if r["book_id"] == "MIX-ML-GREEKS"), None)
    if greeks is not None and int(greeks.get("n_filled") or 0) == 0:
        notes.append(
            "MIX-ML-GREEKS: 0 filled tickets — Dhan greeks/IV missing most of the session. "
            "Adjustment: keep the book; require live chain from 09:15 IST. Do not retune ml001-v1."
        )
    clones = [
        r
        for r in book_rank
        if r["book_id"] in {"MIX-DEFAULT-BUY", "ML-001", "ML-002", "ML-1", "MIX-ML-LOGIT-XR"}
    ]
    if (
        len(clones) >= 4
        and all(int(r.get("n_filled") or 0) > 0 for r in clones)
        and len(set(round(float(r["sum_pnl_inr"]), 2) for r in clones)) == 1
    ):
        notes.append(
            "ML-001 / ML-002 / ML-1 / MIX-ML-LOGIT-XR matched MIX-DEFAULT-BUY net ₹ "
            "(deny_model_signals=false — overlay did not change CE/PE). XR cloned dealer "
            "because the 3m range-expansion filter skipped and the book fell back to dealer, "
            "not because XR equals a 1m SIDEWAYS detector. Do not retune KMeans from this day."
        )
    logit = next((r for r in book_rank if r["book_id"] == "MIX-ML-LOGIT"), None)
    dealer = next((r for r in book_rank if r["book_id"] == "MIX-DEFAULT-BUY"), None)
    if logit and dealer and logit["sum_pnl_inr"] != dealer["sum_pnl_inr"]:
        delta = round(float(logit["sum_pnl_inr"]) - float(dealer["sum_pnl_inr"]), 2)
        notes.append(
            f"MIX-ML-LOGIT vs dealer: {delta:+.2f} ₹ net. This is the ML book that actually scanned a different side. "
            "PAPER only — not a promote."
        )
    for und in ("NIFTY", "BANKNIFTY", "SENSEX"):
        rows = [r for r in leaderboard if r.get("underlying") == und]
        if not rows:
            notes.append(f"{und}: no filled paper tickets today.")
            continue
        best = rows[0]
        worst = rows[-1]
        notes.append(
            f"{und}: best `{best['book_id']}` ₹{best.get('sum_pnl_inr')} · "
            f"worst `{worst['book_id']}` ₹{worst.get('sum_pnl_inr')} "
            f"(n={best.get('n_closed')} vs {worst.get('n_closed')} filled)."
        )
        net_und = float((net_by_index or {}).get(und, 0.0))
        if und == "SENSEX" and net_und < 0:
            notes.append(
                "SENSEX paper: net negative after Groww+STT. HYPOTHESIS tweak only — "
                "no new SENSEX after 14:00 IST; keep |delta|≥0.40 unfilled cancel. Not a MIX write."
            )
        if und == "NIFTY" and net_und > 0:
            notes.append(
                "NIFTY paper: net green after costs on this tape. Keep ITM_100 + working-limit. Not a promote."
            )
        if und == "BANKNIFTY" and net_und > 0:
            notes.append(
                "BANKNIFTY paper: net green after costs on this tape. Keep as the liquidity book. Not a promote."
            )
    notes.append(
        "Rank is after Groww ₹20/order × 2 + GST 18% on brokerage + STT 0.15% sell premium (VERIFY). "
        "Cannot CANDIDATE. NO_PROMOTE. INDEX 1m SIDEWAYS_HOLD is HYPOTHESIS paper skip of NEW opens only."
    )
    return notes


def _append_mistakes(root: Path, mistakes: Sequence[dict[str, Any]]) -> None:
    if not mistakes:
        return
    recon = root / "data" / "recon"
    recon.mkdir(parents=True, exist_ok=True)
    path = recon / MISTAKES_NAME
    stamp = datetime.now(IST).isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"as_of_ist": stamp, "n": len(mistakes), "session_snapshot": True}, default=str) + "\n")


def _open_ticket_row(pos: OpenPaper) -> dict[str, Any]:
    row = asdict(pos)
    row.pop("premium_prints", None)
    row.pop("closed_wing_bars", None)
    row["status"] = agent_ticket_status(pos) if pos.filled or pos.cancel_eligible else "WORKING_LIMIT"
    if pos.filled and pos.target_step == 0 and not pos.cancel_eligible:
        row["status"] = "OPEN_PAPER"
        row["phase"] = "IN_TRADE"
    row["filled"] = bool(pos.filled)
    row["target_step"] = int(pos.target_step)
    row["result"] = None
    row["sl_hit"] = False
    row["sl_loss_inr"] = None
    row["realized_pnl_inr"] = None
    row["opened_ist"] = _ist_dt(pos.opened_ts).isoformat(timespec="seconds")
    updated = int(pos.last_updated_ts or pos.opened_ts)
    row["last_updated_ts"] = updated
    row["last_updated_ist"] = _ist_dt(updated).isoformat(timespec="seconds")
    return row


SKIP_WHY = {
    SIDEWAYS_HOLD: "15m INDEX path was chop — NEW paper held. Last-3 impulse can TREND; true last-3 chop still holds.",
    REGIME_UNKNOWN_WAIT: "1m path mixed / Kaufman ER not a TREND — wait, do not guess CE/PE.",
    VOL_NOT_EXPANDING: "Last-3 1m volume shrank vs prior-3 — skip only when there is no last-3 price impulse.",
    "TREND_UP_KILL_PE": "INDEX 1m TREND UP — PE confirm/kill, not a fill.",
    "TREND_DOWN_KILL_CE": "INDEX 1m TREND DOWN — CE confirm/kill, not a fill.",
    "NO_SIDE": "Book had no CE/PE of its own this tick.",
    "DEALER_HOLD": "FOLLOWS analyst HOLD (ATM last-tick vs INDEX) — not a fill price; MIX-DEFAULT-BUY does not open from this vote.",
    SOD_LAB_OBSERVE: "SOD product books MIX-DEFAULT-BUY only. LAB fill books observe-or-skip.",
    SOD_ONE_OPEN: "SOD one working ticket already open on this underlying.",
    "HOLD_MAJORITY": "Picker majority HOLD — no desk ticket.",
    "OPEN_SETTLE_35M": "No NEW paper before 09:30 IST Mon–Fri.",
    "NO_NEW_BEFORE_0950": "No NEW paper before 09:30 IST Mon–Fri.",
    "NO_NEW_BEFORE_0930": "No NEW paper before 09:30 IST Mon–Fri.",
    "WEEKEND_NO_MARKET": "No Sat/Sun India cash/F&O. Dual-tape and NEW paper are off.",
    "NO_NEW_AFTER_1516": "No NEW after 15:16 IST. Flatten leftover OPEN. Data ticks until 15:30.",
    "NO_NEW_AFTER_1515": "No NEW after 15:16 IST. Flatten leftover OPEN. Data ticks until 15:30.",
    "OBSERVE_NO_OWN_SIDE": "Observe clone — ₹0 capital, no own CE/PE fill.",
    "OBSERVE_NO_OWN_FILL": "Observe lab book — no fill.",
    "OBSERVER_PASS_NO_SIDE": "No fill-book CE/PE this bar — observer has nothing to review.",
    "OBSERVER_PASS_ATM_DAY": "ATM-era tape — observer does not assume ITM confirmation.",
    "OBSERVER_PASS_NO_ITM": "ITM LTP or kind missing — PASS, do not invent a veto.",
    "OBSERVER_PASS_STRIKE_ROLL": "ITM strike changed on this 1m — skip return, do not treat as dead wing.",
    "OBSERVER_PASS_WAIT_1M": "Need a closed 1m bar pair before observer ALLOW/VETO.",
    "OBSERVER_PASS_INDEX_FLAT": "Index 1m flat — no confirmation fact; do not guess.",
    "OBSERVER_ALLOW_ITM_CONFIRMS": "ITM wing moved with the signal's claimed index direction.",
    "FOLLOW_GAP": "Closed 1m INDEX moved; that ITM wing did not confirm. Veto the proposed CE/PE. ATM/missing ITM does not fire.",
    "OBSERVER_VETO_WING_DEAD": "Closed 1m INDEX moved; that ITM wing did not confirm (FOLLOW-GAP).",
    "OBSERVER_VETO_INDEX_AGAINST": "Signal CE while index 1m fell, or PE while index 1m rose.",
    "OBSERVER_VETO_SIGNAL_SELF_CONTRADICT": "Fill book side disagrees with its own last-3 / index direction.",
    "CAPITAL_SKIP_DATA_INSUFFICIENT": "Book capital ₹0 this session.",
    CANCEL_BIN_ROLL: "Booked ITM strike is now ATM/OTM — change the CE/PE bin.",
    "ITM_ONLY_NO_QUOTE": "ITM-only ticket: Dhan did not quote that wing — DATA_INSUFFICIENT, not ATM fallback.",
    "ITM_ONLY_NOT_ITM": "Chosen strike is ATM/OTM — paper waits for a fresh ITM bin.",
    BIN_SIDE_MISMATCH: "ITM CE/PE bin is the other side — do not buy CE into a PE bin (unless a confirmed last-3 impulse).",
    "LAST3_UNCONFIRMED": "Last-3 1m dump/rally was a trap (volume/wick/S-R/option absorb) — wait for ITM bin strength.",
    BIN_LONG_UNWIND: "ITM strike OI down with premium down — long unwind, skip new buy on that wing.",
    COVER_LONG_UNWIND: "Same-wing OI down + premium down — long unwind; flatten. Do not wait T1.",
    CANCEL_STALL: "Premium high went stale in low-ER chop without last-3 continuation — book; do not sit a 9m clock.",
    CANCEL_NO_PROGRESS: "Filled wing printed 3 closed 1m with almost no MFE — flatten the dead fill.",
    CANCEL_BOOK_NEAR: "Filled wing reached ~70% of the target span then a closed 1m reversed — book; do not wait TARGET/AGAINST.",
    CANCEL_AGAINST: "Filled wing is against INDEX last-3 raw / 15m TREND / opposite ITM flow — flatten; do not wait pause or FOLLOWS CONFIRM.",
    "FOCUS_NIFTY_SENSEX": "Paper focus is NIFTY and SENSEX. BANKNIFTY NEW skipped (separate later).",
    "FOCUS_NIFTY_ONLY": "This ship books NIFTY only. SENSEX NEW skipped so unique P/L is not mixed.",
    "SENSEX_WAIT_STRENGTH": "SENSEX uses a wider ATR stop; NEW only on pause-continue, last-3, or short-cover — not every ITM-bin tick.",
    "NIFTY_WAIT_STRENGTH": "Desk NEW only on last-3 / pause-continue / short-cover / itm_bin confirm / TREND ER≥0.35 same wing. FOLLOWS is the analyst vote, not this gate.",
    "NIFTY_IMPULSE_ALIGN": "Desk skips CE on last-3 DOWN / PE on last-3 UP.",
    "NIFTY_SIDE_FILTER": "NIFTY side filter (paper permutation, not a MIX).",
    "NIFTY_DELTA_BAND": "NIFTY |delta| below paper band (OpenAI counsel).",
    "NO_NEW_AFTER_CUTOFF": "No NEW after session cutoff minutes IST.",
    "NIFTY_NO_FLIP": "NIFTY: do not flip CE/PE immediately after a TARGET on the other wing.",
    "BN_WAIT_CONTINUATION": "BANKNIFTY waits for pause-then-volume continuation (or skip). First 3-bar spike is not enough.",
    "WIDE_WAIT_CONTINUATION": "BANKNIFTY/SENSEX wait for pause-then-volume continuation. First spike is not enough. NIFTY may still trade the ITM bin.",
    "GREEKS_NO_CLONE": "MIX-ML-GREEKS does not clone the same CE/PE fill as MIX-ML-LOGIT.",
}


def _skip_why(reason: str) -> str:
    text = str(reason or "")
    if text in SKIP_WHY:
        return SKIP_WHY[text]
    if "DEALER_BUY_CE_CONFIRM_VS_LOGIT_PE" in text:
        return "FOLLOWS saw CE; logit PE — analyst vs logit, no clone fill."
    if "DEALER_BUY_PE_CONFIRM_VS_LOGIT_CE" in text:
        return "FOLLOWS saw PE; logit CE — analyst vs logit, no clone fill."
    if "DEALER_HOLD_VS_LOGIT" in text:
        return "FOLLOWS HOLD vs logit side — product book does not fill from that vote."
    if text.startswith("XR filter"):
        return "MIX-ML-LOGIT-XR range-expansion filter skipped this side."
    if "lean_ml_logit SKIP" in text:
        return "Logit needs enough labeled 3m train rows — DATA_INSUFFICIENT, not a silent CE/PE."
    if "meta-label" in text:
        return "ML-1 meta-label needs ≥30 closed paper rows."
    return text or "skip"


def _index_observation(und: str, classified: dict[str, Any], step: Optional[dict[str, Any]]) -> str:
    dealer = (step or {}).get("dealer") or {}
    logit = (step or {}).get("logit") or {}
    impulse = classified.get("last3_impulse")
    last3 = classified.get("last3_closes")
    net = classified.get("last3_net")
    er15 = classified.get("er")
    regime = classified.get("regime")
    reason = classified.get("reason")
    verdict = dealer.get("verdict")
    logit_side = logit.get("side")
    bits = [f"{und}: 15m {regime} ({reason}, ER={er15})."]
    if last3 is not None:
        bits.append(f"Last-3 1m closes {last3} net={net} impulse={impulse or 'none'}.")
    if classified.get("last3_impulse_raw") in {"UP", "DOWN"} and not classified.get("last3_confirmed"):
        bits.append(
            f"Last-3 raw {classified.get('last3_impulse_raw')} unconfirmed trap={classified.get('last3_trap')} "
            f"candle={classified.get('candle_shape')} — ITM bin chooses the side, not the 1m spike."
        )
    if impulse == "DOWN":
        bits.append("PUT-side last-3 is real; paper PE is allowed only on TREND DOWN plus a fill book that owns PE.")
    elif impulse == "UP":
        bits.append("CALL-side last-3 is real; paper CE is allowed only on TREND UP plus a fill book that owns CE.")
    elif regime in {"SIDEWAYS", "UNKNOWN"}:
        bits.append("Last-3 was not an efficient impulse — 15m chop skip is required, not over-coded.")
    if verdict:
        bits.append(f"Dealer {verdict}; logit side={logit_side or 'SKIP'}.")
    itm_bin = classified.get("itm_bin") or {}
    if itm_bin:
        bits.append(
            f"ITM bin CE {itm_bin.get('ce', {}).get('strike') if isinstance(itm_bin.get('ce'), dict) else '—'} "
            f"votes={itm_bin.get('ce_votes') or []} vs PE {itm_bin.get('pe', {}).get('strike') if isinstance(itm_bin.get('pe'), dict) else '—'} "
            f"votes={itm_bin.get('pe_votes') or []} reason={itm_bin.get('reason') or '—'}. "
            "Two ITM-leg votes can TREND without three INDEX 1m bars."
        )
    return " ".join(bits)


def itm_bins_picture(engine: BookEngine) -> dict[str, Any]:
    """Trader three charts: INDEX + ITM CE + ITM PE. Watch this bin during paper trades."""
    rows: list[dict[str, Any]] = []
    for und in ("NIFTY", "BANKNIFTY", "SENSEX"):
        hist = engine.itm_bins.get(und) or {}
        last = hist.get("last") or {}
        ce = last.get("ce") if isinstance(last.get("ce"), dict) else {}
        pe = last.get("pe") if isinstance(last.get("pe"), dict) else {}
        rows.append(
            {
                "underlying": und,
                "index": last.get("index"),
                "ts": last.get("ts"),
                "side": last.get("side"),
                "reason": last.get("reason"),
                "wait_3_index_bars": False,
                "ce": {
                    "strike": ce.get("strike"),
                    "moneyness": ce.get("moneyness"),
                    "px": ce.get("px"),
                    "volume": ce.get("volume"),
                    "oi": ce.get("oi"),
                    "delta": ce.get("delta"),
                },
                "pe": {
                    "strike": pe.get("strike"),
                    "moneyness": pe.get("moneyness"),
                    "px": pe.get("px"),
                    "volume": pe.get("volume"),
                    "oi": pe.get("oi"),
                    "delta": pe.get("delta"),
                },
                "ce_votes": list(last.get("ce_votes") or []),
                "pe_votes": list(last.get("pe_votes") or []),
                "n_ce_votes": last.get("n_ce_votes") or 0,
                "n_pe_votes": last.get("n_pe_votes") or 0,
                "missing": list(last.get("missing") or []),
            }
        )
    return {
        "layer": "HYPOTHESIS",
        "note": (
            "Three charts: INDEX + ITM CE + ITM PE. Keep this bin during paper trades. "
            "ITM PE volume/delta/OI-up-with-premium + CE selling/premium down can TREND without three INDEX 1m bars. "
            "Missing OI/vol/delta is DATA_INSUFFICIENT, never invented. Roll the bin when booked ITM becomes ATM/OTM. "
            "NO_PROMOTE."
        ),
        "bins": rows,
    }


def seen_not_taken_picture(engine: BookEngine) -> dict[str, Any]:
    """Latest skip per book×index + cancelled tickets. Observation comments are HYPOTHESIS."""
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for skip in engine.skips:
        key = (str(skip.get("book_id") or ""), str(skip.get("underlying") or "").upper())
        if not key[0] or not key[1]:
            continue
        latest[key] = skip
    skipped_rows: list[dict[str, Any]] = []
    for (book, und), skip in sorted(
        latest.items(),
        key=lambda kv: (-int(kv[1].get("ts") or 0), kv[0][0], kv[0][1]),
    ):
        classified = engine.last_regime.get(und) or {}
        step = engine.last_step_by_und.get(und) or {}
        dealer = step.get("dealer") or {}
        logit = step.get("logit") or {}
        seen_side = skip.get("seen_side") or dealer.get("side") or logit.get("side")
        skip_ts = int(skip.get("ts") or 0)
        skipped_rows.append(
            {
                "book_id": book,
                "underlying": und,
                "seen_side": seen_side,
                "side": seen_side,
                "action": "SKIP",
                "reason": skip.get("reason"),
                "why": _skip_why(str(skip.get("reason") or "")),
                "index_regime": skip.get("index_regime") or classified.get("regime"),
                "regime_reason": classified.get("reason"),
                "last3_closes": classified.get("last3_closes"),
                "last3_net": classified.get("last3_net"),
                "last3_er": classified.get("last3_er"),
                "last3_impulse": classified.get("last3_impulse"),
                "dealer_verdict": dealer.get("verdict"),
                "observer_action": skip.get("observer_action") or (step.get("observer") or {}).get("action"),
                "logit_side": logit.get("side"),
                "observation": _index_observation(und, classified, step),
                "last_updated_ts": skip_ts or skip.get("ts"),
                "last_updated_ist": _ist_dt(skip_ts).isoformat(timespec="seconds") if skip_ts else None,
                "trade_id": skip.get("trade_id"),
                "atm_strike": skip.get("atm_strike") or skip.get("strike"),
                "expiry": skip.get("expiry") or skip.get("expiry_ist"),
                "lots": skip.get("lots"),
                "qty": skip.get("qty"),
                "lot_size": skip.get("lot_size"),
                "filled": False,
                "outcome": "NO_FILL",
                "status": "SKIPPED",
            }
        )
    cancelled_rows: list[dict[str, Any]] = []
    for row in engine.closed:
        reason = str(row.get("exit_reason") or "")
        result = str(row.get("result") or "")
        if result != "CANCELLED" and not reason.startswith("CANCEL"):
            continue
        filled = bool(row.get("filled"))
        cancelled_rows.append(
            {
                "book_id": row.get("book_id"),
                "underlying": row.get("underlying"),
                "seen_side": row.get("side"),
                "side": row.get("side"),
                "action": "CANCEL",
                "reason": reason,
                "why": (
                    _skip_why(reason)
                    if reason in SKIP_WHY
                    else (
                        "Unfilled working limit never booked."
                        if reason.startswith("CANCEL_UNFILLED")
                        else f"Ticket cancelled: {reason}."
                    )
                ),
                "status": row.get("status") or result,
                "result": result,
                "index_regime": row.get("index_regime"),
                "limit_price": row.get("limit_price"),
                "atm_strike": row.get("atm_strike"),
                "expiry": row.get("expiry") or row.get("expiry_ist"),
                "trade_id": row.get("trade_id"),
                "lots": row.get("lots"),
                "qty": row.get("qty"),
                "lot_size": row.get("lot_size"),
                "filled": filled,
                "outcome": "FILL_THEN_CANCEL" if filled else "NO_FILL_CANCEL",
                "last_updated_ist": row.get("last_updated_ist") or row.get("closed_ist"),
                "last_updated_ts": row.get("last_updated_ts") or row.get("closed_ts"),
                "observation": (
                    f"{row.get('underlying')} {row.get('side')} {reason}: "
                    "saw a trade, then cancelled — not a silent miss."
                ),
            }
        )
    cancelled_rows = order_tickets_last_updated(cancelled_rows)[:24]
    observations = [
        _index_observation(und, classified, engine.last_step_by_und.get(und))
        for und, classified in sorted((engine.last_regime or {}).items())
    ]
    return {
        "layer": "HYPOTHESIS",
        "note": (
            "Saw a CE/PE but did not OPEN, or OPENED then CANCELLED. "
            "Not live orders. Last-3 PUT/CE impulse can TREND; 15m chop skip stays when last-3 is also chop."
        ),
        "observations": observations,
        "skipped_latest": skipped_rows[:48],
        "cancelled": cancelled_rows,
        "n_skip_events": len(engine.skips),
        "n_cancelled": len(cancelled_rows),
    }


def model_signals_picture(engine: BookEngine) -> dict[str, Any]:
    """Analyst room vs picker. Kept when HOLD / VETO / desk ignore. Not fills."""
    log = list(getattr(engine, "signal_log", None) or [])
    counts = Counter((str(r.get("source") or ""), str(r.get("vs_picker") or "")) for r in log)
    latest: dict[str, dict[str, Any]] = {}
    for row in log:
        src = str(row.get("source") or "")
        if src:
            latest[src] = row
    prefer = ("follows", "logit", "xr", "greeks", "STRAT-003", "MIX-TV-EP-024", "ML-1")
    latest_rows = [latest[k] for k in prefer if k in latest]
    extra_latest = [latest[k] for k in latest if k not in prefer]
    return {
        "layer": "HYPOTHESIS",
        "promote": False,
        "note": (
            "Analyst room: FOLLOWS / logit / XR / greeks / STRAT (spoken) / TV lab. "
            "SOD fills MIX-DEFAULT-BUY only. MATCH / DISSENT / SPOKEN_PICKER_HOLD / SILENT "
            "even when picker HOLD, observer VETO, or desk ignores — shadow tape for later "
            "tune, not extra Monday capital. NO_PROMOTE."
        ),
        "n": len(log),
        "counts": [
            {"source": src, "vs_picker": vs, "n": n}
            for (src, vs), n in sorted(counts.items())
        ],
        "latest": latest_rows + extra_latest,
        "recent": log[-24:],
    }


def build_dashboard(
    engine: BookEngine,
    *,
    tapes: dict[str, Any],
    steps: dict[str, Any],
    as_of_ist: str,
    source: str,
    root: Path,
    live_session: bool = False,
    session_ist_date: Optional[str] = None,
    paper_params: Optional[dict[str, Any]] = None,
    paper_param_notes: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    inv = inventory_recon(root=root, calendar_days=21, underlyings=("NIFTY", "BANKNIFTY", "SENSEX"))
    index_gap = list(inv.get("data_gaps") or [])
    tv_inventory = []
    for mix in TV_EP_KEEP_ALL:
        bound = mix == "MIX-TV-EP-024"
        shortlist = mix in TV_EP_SHORTLIST
        tv_inventory.append(
            {
                "book_id": mix,
                "live_paper_scalp": bound,
                "paper_tune_shortlist": shortlist,
                "note": (
                    "SMA calibrator bound as scalp book"
                    if bound
                    else (
                        "Fired MOCK tickets in TV-EP paper-tune (INDEX proxy ≠ this board)"
                        if shortlist
                        else "KEEP_ALL catalog. Not a live scalp book this CLI."
                    )
                ),
            }
        )
    models = []
    for book_id in LIVE_BOOKS:
        closed_b = [c for c in engine.closed if c["book_id"] == book_id]
        scored_b = [c for c in closed_b if _row_filled(c)]
        nets = [_net_or_points(c) for c in scored_b]
        inrs = [float(c["realized_pnl_inr"]) for c in scored_b if c.get("realized_pnl_inr") is not None]
        open_b = [_open_ticket_row(p) for (b, _u), p in engine.opens.items() if b == book_id]
        models.append(
            {
                "model_id": book_id,
                "what": _book_what(book_id),
                "last_run_ist": as_of_ist,
                "open": open_b,
                "n_closed": len(closed_b),
                "n_open": len(open_b),
                "n_wins": sum(1 for p in nets if p > 0),
                "n_losses": sum(1 for p in nets if p <= 0),
                "sum_closed_premium_pnl": round(sum(float(c["realized_pnl"]) for c in scored_b), 4) if scored_b else 0.0,
                "sum_gross_pnl_inr": _sum_opt([c.get("gross_pnl_inr") for c in scored_b]),
                "sum_charges_inr": _sum_opt([c.get("charges_inr") for c in scored_b]),
                "sum_pnl_inr": round(sum(inrs), 2) if inrs else None,
                "starting_capital_inr": engine.book_capital(book_id),
                "equity_inr": engine.book_equity(book_id),
                "win_rate": paper_hit_rate(nets),
                "win_rate_pct": paper_hit_rate_pct(nets),
                "win_rate_net_pct": paper_hit_rate_pct(nets),
                "win_rate_gross": paper_hit_rate(
                    [float(c["gross_pnl_inr"]) for c in scored_b if c.get("gross_pnl_inr") is not None]
                ),
                "win_rate_gross_pct": paper_hit_rate_pct(
                    [float(c["gross_pnl_inr"]) for c in scored_b if c.get("gross_pnl_inr") is not None]
                ),
                "win_rate_kind": "paper_closed_net_inr_gt_0_after_groww_stt",
                "lot_by_und": {k: v[0] for k, v in engine.lot_by_und.items()},
            }
        )
    open_rows = order_tickets_last_updated(
        [_open_ticket_row(p) for p in engine.opens.values()]
    )
    closed_rows = order_tickets_last_updated(engine.closed)
    scored_all = [c for c in engine.closed if _row_filled(c)]
    all_nets = [_net_or_points(c) for c in scored_all]
    all_gross = [float(c["gross_pnl_inr"]) for c in scored_all if c.get("gross_pnl_inr") is not None]
    inrs_all = [float(c["realized_pnl_inr"]) for c in engine.closed if c.get("realized_pnl_inr") is not None]
    overall_pnl_inr = round(sum(inrs_all), 2) if inrs_all else 0.0
    money_lost_inr = round(sum(x for x in inrs_all if x < 0), 2)
    money_won_inr = round(sum(x for x in inrs_all if x > 0), 2)
    params = dict(paper_params or DEFAULT_PAPER_PARAMS)
    mistakes = mistakes_from_closed(engine.closed)
    successes = successes_from_closed(engine.closed)
    board_leaderboard = leaderboard_closed(engine.closed)
    board_book_rank = rank_books_net(engine.closed)
    for row in board_book_rank:
        row["starting_capital_inr"] = engine.book_capital(str(row["book_id"]))
    picture = today_picture(engine.closed, board_book_rank)
    side_skips = [s for s in engine.skips if str(s.get("reason")) == SIDEWAYS_HOLD]
    unk_skips = [s for s in engine.skips if str(s.get("reason")) == REGIME_UNKNOWN_WAIT]
    side_bars = {(s.get("ts"), s.get("underlying")) for s in side_skips}
    picture["n_skip_sideways"] = len(side_skips)
    picture["n_skip_regime_unknown"] = len(unk_skips)
    picture["n_sideways_bars"] = len(side_bars)
    picture["last_index_regime"] = dict(engine.last_regime)
    seen_not_taken = seen_not_taken_picture(engine)
    picture["seen_not_taken"] = seen_not_taken
    model_signals = model_signals_picture(engine)
    picture["model_signals"] = model_signals
    itm_bins = itm_bins_picture(engine)
    picture["itm_bins"] = itm_bins
    adj_notes = index_adjustment_notes(
        engine.closed,
        board_book_rank,
        board_leaderboard,
        net_by_index=picture.get("unique_net_by_index") or picture.get("net_by_index"),
    )
    skip_reason_counts = dict(Counter(str(s.get("reason") or "") for s in engine.skips))
    return {
        "ok": True,
        "job": "ML_PAPER_SCALP",
        "title": "LIVE SESSION" if live_session else "ML / paper scalper board",
        "live_session": live_session,
        "session_ist_date": session_ist_date,
        "as_of_ist": as_of_ist,
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "promote": False,
        "production_params_written": False,
        "research_ready_for_programming": False,
        "execution": "refused",
        "orders": "REFUSED",
        "llm": False,
        "win_rate": paper_hit_rate(all_nets),
        "win_rate_pct": paper_hit_rate_pct(all_nets),
        "win_rate_net_pct": paper_hit_rate_pct(all_nets),
        "win_rate_gross": paper_hit_rate(all_gross),
        "win_rate_gross_pct": paper_hit_rate_pct(all_gross),
        "win_rate_kind": "paper_closed_net_inr_gt_0_after_groww_stt",
        "win_rate_gross_kind": "paper_closed_gross_inr_gt_0_before_groww_stt",
        "n_closed": len(all_nets),
        "n_open": len(open_rows),
        "n_wins": sum(1 for p in all_nets if p > 0),
        "n_losses": sum(1 for p in all_nets if p <= 0),
        "n_wins_gross": sum(1 for p in all_gross if p > 0),
        "n_losses_gross": sum(1 for p in all_gross if p <= 0),
        "capital_per_book": dict(engine.capital_by_book)
        or {b: engine.book_capital(b) for b in LIVE_BOOKS},
        "starting_capital_inr_per_book": next(
            (v for v in (engine.capital_by_book or {}).values() if float(v) > 0),
            0.0,
        ),
        "n_books": len(LIVE_BOOKS),
        "starting_desk_inr": float((engine.capital_plan or {}).get("desk_capital_inr") or DESK_CAPITAL_INR),
        "capital_plan": engine.capital_plan or allocate_desk_capital(tradable=tradable_fill_books(has_greeks=False)),
        "overall_pnl_inr": overall_pnl_inr,
        "overall_gross_pnl_inr": picture["gross_pnl_inr"],
        "overall_charges_inr": picture["charges_inr"],
        "money_won_inr": money_won_inr,
        "money_lost_inr": money_lost_inr,
        "equity_sum_inr": round(sum(engine.book_equity(b) for b in LIVE_BOOKS), 2),
        "today": picture,
        "n_skip_sideways": picture.get("n_skip_sideways") or 0,
        "n_skip_regime_unknown": picture.get("n_skip_regime_unknown") or 0,
        "n_sideways_bars": picture.get("n_sideways_bars") or 0,
        "skip_reason_counts": skip_reason_counts,
        "n_sl_hit": picture.get("n_sl_hit") or 0,
        "n_target_hit": picture.get("n_target_hit") or 0,
        "n_time_exit": picture.get("n_time_exit") or 0,
        "last_index_regime": picture.get("last_index_regime") or {},
        "seen_not_taken": seen_not_taken,
        "model_signals": model_signals,
        "itm_bins": itm_bins,
        "exam_events": list(engine.exam_events[-80:]),
        "fill_contract": (engine.last_step or {}).get("exam"),
        "book_rank": board_book_rank,
        "index_notes": adj_notes,
        "cost_model": groww_cost_meta(),
        "paper_params": params,
        "nifty_overlay": {
            "allow_sides": list(engine.nifty_allow_sides or []),
            "need_strength": bool(engine.nifty_need_strength),
            "skip_ce_after_stop": bool(engine.nifty_skip_ce_after_stop),
            "skip_side_after_stop": bool(engine.nifty_skip_side_after_stop),
            "max_filled_per_book": engine.nifty_max_filled_per_book,
            "halt_after_stops": engine.nifty_halt_after_stops,
            "session_lean": bool(engine.nifty_session_lean),
            "skip_sensex": bool(engine.skip_sensex),
            "skip_banknifty": bool(engine.skip_banknifty),
            "note": "PAPER NIFTY CE or PE when strength prints. Not PE-locked. Not a promote.",
        },
        "paper_param_notes": list(paper_param_notes or []),
        "mistakes": mistakes[-40:],
        "successes": successes[-20:],
        "deny_model_signals": engine.deny_model_signals,
        "regime_book_counts": {
            "layer": "HYPOTHESIS",
            "note": "INDEX 1m regime × book OPEN/SKIP counts. KMeans is not a CE/PE model.",
            "counts": dict(engine.regime_book_counts),
        },
        "ticket_columns": [
            "book_id",
            "underlying",
            "side",
            "atm_strike",
            "limit_price",
            "target",
            "stop",
            "sl_hit",
            "sl_loss_inr",
            "realized_pnl",
            "gross_pnl_inr",
            "charges_inr",
            "realized_pnl_inr",
            "result",
            "index_regime",
            "justification",
        ],
        "source": source,
        "customer_mix": "MIX-DEFAULT-BUY is the only SOD fill. Analysts vote in their own room.",
        "sod_one_ticket": bool(getattr(engine, "sod_one_ticket", True)),
        "hold_trending_open_stall": bool(getattr(engine, "hold_trending_open_stall", False)),
        "nifty_cover_closed_1m": bool(getattr(engine, "nifty_cover_closed_1m", False)),
        "promote": False,
        "independent_books": not bool(getattr(engine, "sod_one_ticket", True)),
        "one_open_per": (
            "MIX-DEFAULT-BUY × underlying (SOD one ticket; analyst room observe)"
            if bool(getattr(engine, "sod_one_ticket", True))
            else "book_id × underlying (--sod-off A/B)"
        ),
        "scalper_exits": {
            "stop": f"long premium LTP <= entry - {engine.paper_stop_frac}×same-side path range",
            "target": f"LTP >= entry + {engine.paper_target_frac}×path range",
            "time": (
                f"STALL (stale premium high {int(STALL_HIGH_STALE_SEC)}s + ER≤{STALL_ER_MAX} "
                f"after {int(STALL_MIN_SEC)}s) or hard TIME {int(TIME_HARD_SEC)}s; "
                f"9m TIME only if stall state missing. Not a constant hold_bars clock."
            ),
            "cancel_stall": (
                "HYPOTHESIS: book when the ticket high is stale, Kaufman ER of last "
                "premium prints is chop, last-3 is not with the wing, and progress "
                f"to target < {STALL_TARGET_PROGRESS}. True TREND (ER≥{STALL_TREND_ER}) holds."
            ),
            "exit_overlay": (
                f"SOD MIX-DEFAULT-BUY booking: after {EXIT_NO_PROG_BARS} closed 1m if "
                f"MFE < {EXIT_NO_PROG_MFE} pts → CANCEL_NO_PROGRESS; if running MFE ≥ "
                f"{EXIT_BOOK_NEAR_FRAC:.0%} of (target−entry) and closed 1m reverses → "
                "CANCEL_BOOK_NEAR. Causal bars only. Before AGAINST. PAPER."
            ),
            "cancel_adverse": f"same-side low <= entry×(1-{engine.paper_give_up_frac})",
            "cancel_thesis": "opposite BUY_*_CONFIRM only if already underwater vs entry",
            "cancel_greeks": "|delta| too low / IV rich / theta late on live chain — cancel WORKING or OPEN",
            "limit_below_signal": f"working buy limit = signal × (1-{engine.limit_discount_frac})",
            "cancel_strike_roll": "ATM strike moved off the ticket and premium is below entry",
            "flatten_ist": "15:16",
            "feasibility": "warehouse.feasibility.evaluate_long_premium",
            "fantasy_lesson": "150/96/250 TARGET_FEASIBILITY_FAIL",
        },
        "models": models,
        "steps": steps,
        "data_pulled": tapes,
        "inventory": {
            "index_1m": inv.get("index_1m"),
            "premium_tape": inv.get("premium_tape"),
            "joins": inv.get("joins"),
            "data_gaps": index_gap,
        },
        "open_trades": open_rows,
        "closed_trades": closed_rows,
        "tickets": list(open_rows) + list(closed_rows),
        "leaderboard": board_leaderboard,
        "tv_ep_inventory": tv_inventory,
        "heartbeat": {
            "cli": "python -m desk_ml paper-scalp --replay",
            "loop": "python -m desk_ml paper-scalp --loop  (opt-in; writes this JSON)",
            "dual_tape": "python -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 2 --max-ticks 0",
            "stop": f"touch data/recon/{STOP_FLAG_NAME}",
            "dashboard_write_seconds": DASHBOARD_HEARTBEAT_SECONDS,
            "tick_seconds_default": 2,
            "tick_ne_dashboard_reason": TICK_NE_DASHBOARD_REASON,
            "does_not_start": ["paper_ops", "npm", "legacy LLM waiters"],
        },
        "honesty": [
            "Closed net ₹ after Groww brokerage + GST + option STT ranks. Open rows do not.",
            "win_rate_pct is paper filled hit rate (net ₹>0 / n_filled) × 100. win_rate_gross_pct is the same before Groww+STT. NO_PROMOTE.",
            "Groww F&O ₹20/executed order × 2 legs; GST 18% on that brokerage; STT 0.15% of sell premium (VERIFY, Budget 2026).",
            "Unfilled CANCELLED = ₹0 P/L and ₹0 charges. Exchange/SEBI/stamp omitted (UNKNOWN).",
            "SOD-on: desk capital sits on MIX-DEFAULT-BUY only. Analyst room (logit / XR / greeks / STRAT / TV) votes and is logged; lab books never OPEN. --sod-off tests may still split capital. Observe clones get ₹0. New fills target 25 lots (floor 20, cap 30). Skip if capital cannot buy 20 lots — never 1-lot paper.",
            "deny_model_signals default true. KMeans is not a CE/PE model. No STRAT-015. resolve_fill_intents is not the SOD fill router.",
            "SOD: one ticket + analyst room observe. MATCH/DISSENT/SPOKEN_PICKER_HOLD/SILENT even when picker HOLD / observer VETO / desk ignores. Not extra Monday capital. LLM allow-review is async, not a block.",
            "Two layers: (1) signal = dealer / logit / XR / greeks CE/PE. (2) after fill = STALL / AGAINST / TARGET / SL. WAIT_STRENGTH is dealer entry only — FIX-FIRST did not turn off ML BUY/SELL.",
            "FIX-FIRST drill (pre-market): write=false replay from 2026-09-17 jsonl. Session cap 4 filled/book + WAIT_STRENGTH can leave n_open=0 even when dealer CONFIRM. itm_bin confirm counts as NIFTY strength.",
            "INDEX 1m is warehouse∪JSON. ATM days without INDEX 1m stay DATA_INSUFFICIENT — never filled bars.",
            "Paper entries prefer ~100pt ITM (STRAT-006 wing) when chain LTP exists. ATM is fallback only.",
            "Working buy limit sits below signal LTP (session limit_discount_frac). Fill is not assumed at signal.",
            "Dhan POST /optionchain documents IV + greeks.delta/theta/gamma/vega. Paper uses them when parsed; never invents.",
            "MIX-ML-GREEKS is the ML-2 paper book: skip missing greeks, rich IV, late-session theta bleed. ml001-v1 unchanged.",
            "live_session=true walks TODAY IST dual-tape only. Cache-wide jsonl replay is not today's P/L. 16 Sep is not 17 Sep.",
            "Cancel dead tickets: unfilled limit walk-away, minute low, 12% give-up, strike roll, thesis flip, dead greeks. Do not sit to TIME.",
            "A signal is WORKING_LIMIT until booked-strike LTP or minute low <=limit. If the candle runs away, cancel with ₹0 — never assume a fill.",
            "OPEN_PAPER MTM uses the booked strike LTP (wing cell), not the rolled ATM pack. ATM LTP through the stop does not close a different strike.",
            "Once filled, STOP/CANCEL_ADVERSE/greeks-dead must close. A wick through limit then stop is CLOSED LOSS — it must not sit OPEN.",
            "Open rows stamp last_ltp / seen_low / quote_src so a 74300 CE is not confused with a later ATM 74400/74500 print.",
            "FOUNDER LOCK: Mon–Fri only. Data 09:00–15:30 IST. NEW paper 09:30–15:16. Flatten all books at 15:16. ITM option premium only (never ATM/OTM). No Sat/Sun dual-tape.",
            "No NEW after 15:16 IST. Flatten leftover OPEN. Data ticks may persist until 15:30. live_session does not keep dead tickets overnight.",
            "paper_params nudge is session-only overfit. production_params_written stays false.",
            "INDEX 1m regime TREND|SIDEWAYS|UNKNOWN is HYPOTHESIS. TREND = Kaufman 15m ER *or* last-3 1m impulse (PUT/CE) with volume not shrinking, plus VWAP/EMA/RSI when using the 15m path. itm_bin can label TREND at ER~0.05 — that is not a 9m hold. Filled stall: stale premium high + ER≤0.18 books CANCEL_STALL; ER≥0.35 / last-3 with the wing holds. Exit overlay (SOD MIX-DEFAULT-BUY booking): 3 closed 1m dead-fill CANCEL_NO_PROGRESS; 70% target MFE + closed-1m reverse CANCEL_BOOK_NEAR. SIDEWAYS skips NEW when last-3 is also chop. Feed stays live.",
            "Filled PE does not sit a CALL rally. CANCEL_AGAINST uses last3_impulse_raw and pre-bin INDEX direction — pause-wait / false-break / 10s PE bin must not keep the PUT. TREND ER≥0.35 continues only the same wing. A 10s itm_bin tick cannot overwrite INDEX TREND UP.",
            "TREND + direction UP kills new PE (confirm/kill overlay, not a STRAT). DOWN kills new CE. Last-3 price impulse is TREND even if INDEX volume shrinks (Dhan SENSEX vol spikes are not a skip). Dual-tape JSONL is kept on slate (not trimmed). Paper book epoch skips replaying old ticks as new trades. Not MIX-DEFAULT-BUY production.",
            "Founder ~57% wr during cash hours is an in-session PAPER observation, not this EOD Groww+STT filled hit rate. Not a promote.",
        ],
    }


def ticket_last_updated_ts(row: dict[str, Any]) -> int:
    try:
        return int(row.get("last_updated_ts") or row.get("closed_ts") or row.get("opened_ts") or 0)
    except (TypeError, ValueError):
        return 0


def coerce_close_result(row: dict[str, Any]) -> dict[str, Any]:
    """Old in-memory TIME green rows were stamped SUCCESS. Display TARGET-only SUCCESS."""
    reason = str(row.get("exit_reason") or "")
    result = str(row.get("result") or "")
    target_hit = bool(row.get("target_hit")) or reason == "TARGET"
    if reason == "TIME" and result == "SUCCESS":
        row = dict(row)
        row["result"] = "TIME"
        row["target_hit"] = False
    elif reason == "CANCEL_STALL" and result == "SUCCESS":
        row = dict(row)
        row["result"] = "STALL"
        row["target_hit"] = False
    elif reason in {"FLATTEN_1516", "FLATTEN_1515", "FLATTEN_1500"} and result == "SUCCESS":
        row = dict(row)
        row["result"] = "FLATTEN"
        row["target_hit"] = False
    else:
        row = dict(row)
        row["target_hit"] = target_hit
    return row


def order_tickets_last_updated(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Newest last_updated first. Closed rows stay a separate list (rendered last)."""
    out = []
    for row in rows:
        item = dict(row)
        if item.get("exit_reason") or item.get("result"):
            item = coerce_close_result(item)
        out.append(item)
    return sorted(out, key=ticket_last_updated_ts, reverse=True)


def recent_closed_first(closed: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Newest last_updated/closed first so the board does not bury them."""
    return order_tickets_last_updated(closed)


def wipe_today_paper_book(
    *,
    root: Optional[Path] = None,
    ist_date: Optional[str] = None,
    keep_jsonl: bool = True,
) -> dict[str, Any]:
    """Empty today's paper board. Dual-tape JSONL left in place when keep_jsonl. Not warehouse/sqlite."""
    base = root or repo_root()
    day = ist_date or datetime.now(IST).date().isoformat()
    recon = base / "data" / "recon"
    recon.mkdir(parents=True, exist_ok=True)
    archive = recon / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    tape_jsonl = recon / "paper_watch" / "DUAL-TAPE" / f"{day}.jsonl"
    jsonl_keep: dict[str, Any] = {"ok": True, "kept": "untouched" if keep_jsonl else 0, "path": str(tape_jsonl)}
    sources = [recon / "paper_ledger" / f"{day}.jsonl", recon / LOG_JSONL_NAME]
    if not keep_jsonl:
        sources = [tape_jsonl, *sources]
    for src in sources:
        if src.is_file():
            dest = archive / f"{src.name}.{day}.pre_slate"
            dest.write_bytes(src.read_bytes())
            src.unlink()
            moved.append(str(src))
    if not keep_jsonl:
        latest = recon / "paper_watch" / "DUAL-TAPE" / "latest.json"
        if latest.is_file():
            latest.unlink()
            moved.append(str(latest))
    now = datetime.now(IST)
    epoch_ts = int(now.timestamp())
    cur = load_paper_params(base)
    save_paper_params(
        base,
        {
            **cur,
            **OVERLAY_SHIP,
            "paper_book_epoch_ts": epoch_ts,
            "paper_book_epoch_ist": now.isoformat(timespec="seconds"),
        },
    )
    plan = allocate_desk_capital(tradable=tradable_fill_books(has_greeks=False))
    engine = BookEngine(
        deny_model_signals=True,
        capital_by_book=dict(plan["per_book"]),
        capital_plan=plan,
        skip_banknifty=False,
        skip_sensex=False,
        nifty_need_strength=True,
        nifty_allow_sides=("CE", "PE"),
        nifty_align_impulse=True,
        nifty_skip_ce_after_stop=True,
        nifty_max_filled_per_book=None,
        apply_target_shift=False,
    )
    for book_id in LIVE_BOOKS:
        engine.equity[book_id] = float(plan["per_book"].get(book_id) or 0.0)
    empty = build_dashboard(
        engine,
        tapes={},
        steps={},
        as_of_ist=now.isoformat(timespec="seconds"),
        source="dual-tape",
        root=base,
        live_session=True,
        session_ist_date=day,
        paper_params=load_paper_params(base),
        paper_param_notes=[
            "CLEAN SLATE: paper dashboard wiped. Dual-tape JSONL kept. Ship=NIFTY CE+PE+strength, no fill-count cap; founder START/STOP is the index gate. New paper book after epoch. Warehouse/sqlite kept. NO_PROMOTE."
        ],
    )
    empty["n_closed"] = 0
    empty["closed_trades"] = []
    empty["open_trades"] = []
    empty["tickets"] = []
    empty["clean_slate"] = True
    empty["promote"] = False
    empty["production_params_written"] = False
    paths = write_dashboard(empty, root=base)
    return {
        "ok": True,
        "session_ist_date": day,
        "archived": moved,
        "paths": paths,
        "jsonl_keep_seconds": None,
        "jsonl_keep": jsonl_keep,
        "paper_book_epoch_ts": epoch_ts,
        "warehouse_deleted": False,
        "sqlite_deleted": False,
        "production_params_written": False,
        "promote": False,
    }


def write_dashboard(board: dict[str, Any], *, root: Optional[Path] = None) -> dict[str, str]:
    base = root or repo_root()
    recon = base / "data" / "recon"
    recon.mkdir(parents=True, exist_ok=True)
    json_path = recon / DASH_JSON_NAME
    json_path.write_text(json.dumps(board, indent=2, default=str) + "\n", encoding="utf-8")
    md = render_markdown(board)
    md_path = base / DASH_MD_REL
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    mock = base / MOCK_JSON_REL
    mock.parent.mkdir(parents=True, exist_ok=True)
    compact = {
        k: board.get(k)
        for k in (
            "ok",
            "job",
            "as_of_ist",
            "gate",
            "promote",
            "win_rate",
            "win_rate_pct",
            "win_rate_net_pct",
            "win_rate_gross",
            "win_rate_gross_pct",
            "win_rate_kind",
            "n_closed",
            "n_wins",
            "n_losses",
            "starting_capital_inr_per_book",
            "capital_per_book",
            "capital_plan",
            "starting_desk_inr",
            "overall_pnl_inr",
            "overall_gross_pnl_inr",
            "overall_charges_inr",
            "money_lost_inr",
            "money_won_inr",
            "equity_sum_inr",
            "live_session",
            "session_ist_date",
            "title",
            "n_open",
            "n_skip_sideways",
            "n_skip_regime_unknown",
            "n_sideways_bars",
            "n_sl_hit",
            "last_index_regime",
            "seen_not_taken",
            "model_signals",
            "itm_bins",
            "paper_params",
            "paper_param_notes",
            "ticket_columns",
            "source",
            "independent_books",
            "sod_one_ticket",
            "scalper_exits",
            "models",
            "leaderboard",
            "book_rank",
            "today",
            "index_notes",
            "cost_model",
            "heartbeat",
            "honesty",
            "execution",
            "orders",
            "customer_mix",
        )
    }
    compact["inventory"] = {"data_gaps": (board.get("inventory") or {}).get("data_gaps")}
    compact["steps"] = {
            u: {kk: vv for kk, vv in (s or {}).items() if kk in {"status", "n_triples", "span_ist", "logit", "ml1", "index_regime", "itm_bin"}}
        for u, s in (board.get("steps") or {}).items()
    }
    compact["n_closed"] = len(board.get("closed_trades") or [])
    compact["n_open"] = len(board.get("open_trades") or [])
    compact["closed_trades_sample"] = (board.get("closed_trades") or [])[:20]
    compact["closed_trades"] = compact["closed_trades_sample"]
    compact["open_trades"] = board.get("open_trades") or []
    compact["nifty_overlay"] = board.get("nifty_overlay")
    compact["tickets"] = (board.get("open_trades") or []) + (board.get("closed_trades") or [])[:20]
    compact["mistakes"] = (board.get("mistakes") or [])[-20:]
    compact["successes"] = (board.get("successes") or [])[-12:]
    compact["note"] = "Compact mock. Full closed tape is data/recon/ml_paper_dashboard.json (gitignored)."
    mock.write_text(json.dumps(compact, indent=2, default=str) + "\n", encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path), "mock": str(mock)}


def render_markdown(board: dict[str, Any]) -> str:
    title = board.get("title") or "ML / paper scalper monitoring board"
    session = board.get("session_ist_date") or "—"
    lines = [
        f"# {title}",
        "",
        f"**As of (IST):** `{board.get('as_of_ist')}`  ",
        f"**Session (IST date):** `{session}` · live_session={board.get('live_session')}  ",
        f"**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE.** Orders refused. "
        f"paper wr net={board.get('win_rate_net_pct', board.get('win_rate_pct'))}% "
        f"gross={board.get('win_rate_gross_pct')}% "
        f"({board.get('n_wins')}/{board.get('n_closed')} filled net). "
        f"desk ₹{board.get('starting_desk_inr')} split across {(board.get('capital_plan') or {}).get('n_tradable', board.get('n_books'))} tradable fill books "
        f"(typical ₹{board.get('starting_capital_inr_per_book')}/tradable; observe books ₹0).  ",
        f"**Gross P/L:** ₹{board.get('overall_gross_pnl_inr')} · **charges:** ₹{board.get('overall_charges_inr')} "
        f"(Groww+statutory VERIFY) · **Net P/L:** ₹{board.get('overall_pnl_inr')} · won ₹{board.get('money_won_inr')} · "
        f"lost ₹{board.get('money_lost_inr')} · desk equity ₹{board.get('equity_sum_inr')}  "
        f"(start ₹{board.get('starting_desk_inr')}). Open {board.get('n_open')}.",
        "",
        (
            "SOD-on: one desk ticket (`MIX-DEFAULT-BUY`) + analyst room observe. "
            "Lab books never OPEN. Analyst CE/PE is logged MATCH/DISSENT/SPOKEN_PICKER_HOLD "
            "even when picker HOLD / observer VETO / desk ignores. A HOLD on ML-001 does "
            "**not** invent a wing."
            if board.get("sod_one_ticket", True) or not board.get("independent_books")
            else "A/B --sod-off: one OPEN per (`book_id` × underlying). Not the Monday path."
        ),
        "",
        "## Today at a glance (gross vs net after Groww + statutory)",
        "",
    ]
    pic = board.get("today") or {}
    plan = board.get("capital_plan") or {}
    lines.append(
        f"Filled {pic.get('n_filled', board.get('n_closed'))} · cancelled {pic.get('n_cancelled', 0)} · "
        f"W net {pic.get('n_wins', board.get('n_wins'))} / L {pic.get('n_losses', board.get('n_losses'))} · "
        f"W gross {pic.get('n_wins_gross', board.get('n_wins_gross'))} / L gross {pic.get('n_losses_gross')}. "
        f"TARGET hits {pic.get('n_target_hit', board.get('n_target_hit') or 0)} · "
        f"TIME exits {pic.get('n_time_exit', board.get('n_time_exit') or 0)} "
        f"(SUCCESS = TARGET only; TIME green is not SUCCESS)."
    )
    lines.append(
        f"wr **gross** {pic.get('win_rate_gross_pct', board.get('win_rate_gross_pct'))}% · "
        f"wr **net** {pic.get('win_rate_net_pct', board.get('win_rate_net_pct', board.get('win_rate_pct')))}% "
        f"(Groww+statutory VERIFY)."
    )
    alloc = plan.get("per_book") or board.get("capital_per_book") or {}
    if alloc:
        parts = [f"`{k}` ₹{v}" for k, v in alloc.items()]
        lines.append(
            "Capital split (₹"
            + str(plan.get("desk_capital_inr") or board.get("starting_desk_inr"))
            + " desk, SKIP/DI = ₹0 redistributed, min "
            + str(PAPER_MIN_LOTS)
            + " lots/fill): " + " · ".join(parts) + "."
        )
    lines.append(
        f"Gross ₹{pic.get('gross_pnl_inr', board.get('overall_gross_pnl_inr'))} − "
        f"brokerage ₹{pic.get('brokerage_inr')} − GST ₹{pic.get('gst_inr')} − STT ₹{pic.get('stt_inr')} "
        f"− exch ₹{pic.get('exchange_inr')} − SEBI ₹{pic.get('sebi_inr')} − stamp ₹{pic.get('stamp_inr')} "
        f"= **net ₹{pic.get('net_pnl_inr', board.get('overall_pnl_inr'))}**."
    )
    lines.append(
        f"SIDEWAYS skip (NEW opens only, HYPOTHESIS): n_skip_sideways={board.get('n_skip_sideways', pic.get('n_skip_sideways'))} "
        f"· REGIME_UNKNOWN_WAIT={board.get('n_skip_regime_unknown', pic.get('n_skip_regime_unknown'))} "
        f"· n_sideways_bars={board.get('n_sideways_bars', pic.get('n_sideways_bars'))} "
        f"· filled SL-hits={board.get('n_sl_hit', pic.get('n_sl_hit'))}."
    )
    by_idx = pic.get("net_by_index") or {}
    if by_idx:
        parts = [f"{k} ₹{v}" for k, v in by_idx.items()]
        lines.append("Index net (8 parallel books): " + " · ".join(parts) + ".")
    uniq = pic.get("unique_net_by_index") or {}
    if uniq:
        parts = [f"{k} ₹{v}" for k, v in uniq.items()]
        lines.append(
            f"Unique books only (`{'` `'.join(pic.get('unique_books') or UNIQUE_PNL_BOOKS)}`): "
            f"net ₹{pic.get('unique_net_pnl_inr')} · " + " · ".join(parts) + "."
        )
    best_ml = pic.get("best_ml_book") or {}
    if best_ml:
        lines.append(
            f"Best ML book: `{best_ml.get('book_id')}` rank {best_ml.get('rank')} net ₹{best_ml.get('sum_pnl_inr')} "
            f"(filled {best_ml.get('n_filled')})."
        )
    lines += [
        "",
        "## Ranked books (net ₹, all indices)",
        "",
        "| rank | book | kind | filled | cancel | W | L | wr% net | wr% gross | gross ₹ | charges ₹ | **net ₹** | capital ₹ |",
        "|------|------|------|--------|--------|---|---|--------|----------|---------|-----------|-----------|-----------|",
    ]
    for row in board.get("book_rank") or []:
        lines.append(
            f"| {row.get('rank')} | `{row['book_id']}` | {row.get('kind')} | {row.get('n_filled')} | "
            f"{row.get('n_cancelled')} | {row.get('n_wins')} | {row.get('n_losses')} | "
            f"{row.get('win_rate_net_pct', row.get('win_rate_pct'))} | {row.get('win_rate_gross_pct')} | "
            f"{row.get('sum_gross_pnl_inr')} | {row.get('sum_charges_inr')} | {row.get('sum_pnl_inr')} | "
            f"{row.get('starting_capital_inr')} |"
        )
    if not board.get("book_rank"):
        lines.append("| — | — | — | 0 | 0 | 0 | 0 | — | — | — | — | — | — |")
    lines += [
        "",
        "## Open tickets (last updated desc — strike / limit / target / SL / CE|PE / status)",
        "",
        "| model | und | CE/PE | strike | limit | **target** | stop | last_ltp | filled | status | regime | updated |",
        "|-------|-----|-------|--------|-------|-----------|------|----------|--------|--------|--------|---------|",
    ]
    for row in board.get("open_trades") or []:
        lines.append(
            f"| `{row.get('book_id')}` | {row.get('underlying')} | {row.get('side')} | "
            f"{row.get('atm_strike')} | {row.get('limit_price')} | {row.get('target')} | {row.get('stop')} | "
            f"{row.get('last_ltp')} | {row.get('filled')} | "
            f"{row.get('status') or 'OPEN_PAPER'} | {row.get('index_regime') or '—'} | "
            f"{row.get('last_updated_ist') or row.get('opened_ist') or '—'} |"
        )
    if not board.get("open_trades"):
        lines.append("| — | — | — | — | — | — | — | — | — | none | — | — |")
    if board.get("open_trades"):
        lines += ["", "### Open justification", ""]
        for row in board.get("open_trades") or []:
            lines.append(
                f"- `{row.get('book_id')}` {row.get('underlying')} {row.get('side')}: "
                f"{row.get('justification') or '—'}"
            )
    lines += [
        "",
        "## Closed tickets (last — last updated desc — strike / entry / **exit** / target / SL / reason)",
        "",
        "| model | und | side | strike | entry | **exit** | target | stop | reason | target_hit | pnl ₹ | result | regime | updated |",
        "|-------|-----|------|--------|-------|----------|--------|------|--------|------------|-------|--------|--------|---------|",
    ]
    for row in (board.get("closed_trades") or [])[:20]:
        lines.append(
            f"| `{row.get('book_id')}` | {row.get('underlying')} | {row.get('side')} | "
            f"{row.get('atm_strike')} | {row.get('entry') or row.get('limit_price')} | {row.get('exit')} | "
            f"{row.get('target')} | {row.get('stop')} | `{row.get('exit_reason')}` | {row.get('target_hit')} | "
            f"{row.get('realized_pnl_inr')} | {row.get('result')} | "
            f"{row.get('index_regime') or '—'} | {row.get('last_updated_ist') or row.get('closed_ist') or '—'} |"
        )
    if not board.get("closed_trades"):
        lines.append("| — | — | — | — | — | — | — | — | — | — | — | — | — | — |")
    if board.get("closed_trades"):
        lines += ["", "### Closed justification (SUCCESS=TARGET / TIME / LOSS / CANCEL)", ""]
        for row in (board.get("closed_trades") or [])[:20]:
            lines.append(
                f"- `{row.get('book_id')}` {row.get('underlying')} {row.get('side')} "
                f"{row.get('result')} `{row.get('exit_reason')}`: {row.get('justification') or '—'}"
            )
    seen = board.get("seen_not_taken") or (pic.get("seen_not_taken") if pic else {}) or {}
    lines += [
        "",
        "## Seen but not taken / cancelled (why)",
        "",
        str(seen.get("note") or "Saw a CE/PE but did not OPEN, or OPENED then CANCELLED."),
        "",
    ]
    for obs in seen.get("observations") or []:
        lines.append(f"- {obs}")
    if not seen.get("observations"):
        lines.append("- (no 1m regime observation yet)")
    lines += [
        "",
        "| kind | model | und | seen CE/PE | reason | why | regime | last-3 impulse | updated |",
        "|------|-------|-----|------------|--------|-----|--------|----------------|---------|",
    ]
    mixed = list(seen.get("cancelled") or []) + list(seen.get("skipped_latest") or [])
    for row in mixed[:40]:
        lines.append(
            f"| {row.get('action')} | `{row.get('book_id')}` | {row.get('underlying')} | "
            f"{row.get('seen_side') or '—'} | `{row.get('reason')}` | {row.get('why')} | "
            f"{row.get('index_regime') or '—'} | {row.get('last3_impulse') or '—'} | "
            f"{row.get('last_updated_ist') or '—'} |"
        )
    if not mixed:
        lines.append("| — | — | — | — | none | — | — | — | — |")
    bins = board.get("itm_bins") or (pic.get("itm_bins") if pic else {}) or {}
    lines += [
        "",
        "## ITM CE / PE bin (three charts)",
        "",
        str(
            bins.get("note")
            or "INDEX + ITM CE + ITM PE. Two votes TREND without three INDEX 1m bars. Roll when ITM→ATM/OTM."
        ),
        "",
        "| und | index | CE strike | CE $ | CE vol | CE OI | PE strike | PE $ | PE vol | PE OI | PE votes | CE votes | side | reason | missing |",
        "|-----|-------|-----------|------|--------|-------|-----------|------|--------|-------|----------|----------|------|--------|---------|",
    ]
    for row in bins.get("bins") or []:
        ce = row.get("ce") or {}
        pe = row.get("pe") or {}
        lines.append(
            f"| {row.get('underlying')} | {row.get('index')} | {ce.get('strike')} | {ce.get('px')} | "
            f"{ce.get('volume')} | {ce.get('oi')} | {pe.get('strike')} | {pe.get('px')} | "
            f"{pe.get('volume')} | {pe.get('oi')} | {','.join(row.get('pe_votes') or []) or '—'} | "
            f"{','.join(row.get('ce_votes') or []) or '—'} | {row.get('side') or '—'} | "
            f"`{row.get('reason') or '—'}` | {','.join(row.get('missing') or []) or '—'} |"
        )
    if not bins.get("bins"):
        lines.append("| — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |")
    if seen.get("observations"):
        lines.append("")
        lines.append("Comments (HYPOTHESIS, not a promote):")
        for row in (seen.get("skipped_latest") or [])[:8]:
            if row.get("observation"):
                lines.append(f"- `{row.get('book_id')}` {row.get('underlying')}: {row.get('observation')}")
    lines += [
        "",
        "## Leaderboard (book × index, ranked by net ₹)",
        "",
        "| rank | book | underlying | n | wins | losses | wr% net | wr% gross | pts | gross ₹ | charges ₹ | **net ₹** |",
        "|------|------|------------|---|------|--------|--------|----------|-----|---------|-----------|-----------|",
    ]
    for row in board.get("leaderboard") or []:
        lines.append(
            f"| {row.get('rank')} | `{row['book_id']}` | {row['underlying']} | {row['n_closed']} | "
            f"{row.get('n_wins')} | {row.get('n_losses')} | {row.get('win_rate_net_pct', row.get('win_rate_pct'))} | "
            f"{row.get('win_rate_gross_pct')} | "
            f"{row['sum_premium_pnl']} | {row.get('sum_gross_pnl_inr')} | {row.get('sum_charges_inr')} | "
            f"{row.get('sum_pnl_inr')} |"
        )
    if not board.get("leaderboard"):
        lines.append("| — | — | — | 0 | 0 | 0 | — | — | — | — | — | — |")
    tape_note = (
        "LIVE SESSION: dual-tape ticks for this IST date only. Not fills. Rank ≠ promote."
        if board.get("live_session")
        else "PAPER cache replay (aligned INDEX∩ATM 1m on disk). Not fills. Rank ≠ promote."
    )
    lines += [
        "",
        tape_note + " `MIX-ML-LOGIT*` trains on INDEX 3m before the ATM session. "
        "`win_rate` net = filled hit rate after Groww+STT; `win_rate_gross` is before charges. Not a promote. "
        "`MIX-TV-EP-024` SMA lab is KEEP_ALL, not customer default.",
        "",
        "## Index / ML notes (HYPOTHESIS paper only)",
        "",
    ]
    for note in board.get("index_notes") or []:
        lines.append(f"- {note}")
    if not board.get("index_notes"):
        lines.append("- (replay to fill)")
    sig = board.get("model_signals") or {}
    lines += [
        "",
        "## Analyst model signals (room vs picker — ignored votes still logged)",
        "",
        str(sig.get("note") or "Analyst votes stay even when the boss HOLDs. Not extra fills."),
        f"Logged rows: {sig.get('n', 0)}.",
        "",
        "| source | vs picker | n |",
        "|--------|-----------|---|",
    ]
    for row in sig.get("counts") or []:
        lines.append(f"| `{row.get('source')}` | {row.get('vs_picker')} | {row.get('n')} |")
    if not sig.get("counts"):
        lines.append("| — | — | 0 |")
    lines += [
        "",
        "Latest spoken (still analysts when observer VETO / picker HOLD):",
        "",
        "| source | side | vs picker | picker | observer | ignored |",
        "|--------|------|-----------|--------|----------|---------|",
    ]
    for row in sig.get("latest") or []:
        lines.append(
            f"| `{row.get('source')}` | {row.get('side') or 'SILENT'} | {row.get('vs_picker')} | "
            f"{row.get('picker_action')}/{row.get('picker_side') or '—'} | {row.get('observer_action') or '—'} | "
            f"{row.get('ignored_by_boss')} |"
        )
    if not sig.get("latest"):
        lines.append("| — | — | — | — | — | — |")
    lines += [
        "",
        "## Models / steps",
        "",
        "| id | closed | W | L | wr% net | wr% gross | equity ₹ | capital ₹ | last run |",
        "|----|--------|---|---|--------|----------|----------|-----------|----------|",
    ]
    for m in board.get("models") or []:
        lines.append(
            f"| `{m['model_id']}` | {m['n_closed']} | {m.get('n_wins')} | {m.get('n_losses')} | "
            f"{m.get('win_rate_net_pct', m.get('win_rate_pct'))} | {m.get('win_rate_gross_pct')} | "
            f"{m.get('equity_inr')} | {m.get('starting_capital_inr')} | `{m['last_run_ist']}` |"
        )
    lines += [
        "",
        "## Mistakes (paper-param nudge only; no MIX write)",
        "",
    ]
    notes = board.get("paper_param_notes") or []
    params = board.get("paper_params") or {}
    lines.append(
        f"Paper params: stop_frac={params.get('stop_frac')} target_frac={params.get('target_frac')} "
        f"hold_bars={params.get('scalp_hold_bars')} skip_sideways={params.get('skip_sideways')} "
        f"regime_er_max={params.get('regime_er_max')}. production_params_written=false."
    )
    for n in notes:
        lines.append(f"- {n}")
    for row in (board.get("mistakes") or [])[-12:]:
        lines.append(
            f"- `{row.get('book_id')}` {row.get('underlying')} {row.get('side')} strike={row.get('atm_strike')} "
            f"lost ₹{row.get('money_lost_inr')} ({row.get('exit_reason')}): {row.get('lesson')}"
        )
    if not board.get("mistakes") and not notes:
        lines.append("- (no closed losses this snapshot)")
    lines += ["", "## DATA_INSUFFICIENT", ""]
    gaps = (board.get("inventory") or {}).get("data_gaps") or []
    if not gaps:
        lines.append("- (none on this inventory pass)")
    for g in gaps:
        lines.append(f"- {g}")
    lines += [
        "",
        "## How to watch",
        "",
        "```bash",
        "python -m desk_ml paper-scalp --replay --source dual-tape --live-session",
        "python -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 2 --max-ticks 0",
        "touch data/recon/ml_paper_scalp_STOPPED.flag",
        "```",
        "",
        "Dashboard JSON/MD rewrite **every 2s** from the last tick. Dual-tape Dhan poll stays **45s** "
        "(optionchain rate-limit). Tick ≠ 2s on purpose.",
        "",
        "JSON: `data/recon/ml_paper_dashboard.json` (gitignored) · mock: `apps/web/public/mock/ml_paper_dashboard.json`  ",
        "UI: `/pm` and `/desk` (existing Vite; do not restart npm). API: `GET /paper/ml-books`.",
        "",
        "KEEP_ALL STRAT-001–014. No STRAT-015+.",
        "",
    ]
    return "\n".join(lines) + "\n"


def stop_requested(root: Path) -> bool:
    return (root / "data" / "recon" / STOP_FLAG_NAME).is_file()


def run_loop(
    *,
    root: Optional[Path] = None,
    tick_seconds: int = 2,
    max_ticks: int = 0,
    sleep_fn: Optional[Callable[[float], None]] = None,
    source: str = "dual-tape",
    live_session: bool = True,
) -> dict[str, Any]:
    """Opt-in. Writes heartbeat into dashboard JSON. Does not arm paper_ops."""
    import time

    sleep = sleep_fn or time.sleep
    base = root or repo_root()
    i = 0
    last: dict[str, Any] = {}
    while True:
        if stop_requested(base):
            last = replay_paper_scalp(
                root=base,
                source=source,
                write=True,
                deny_model_signals=True,
                live_session=live_session,
            )
            last["loop_stopped"] = "ml_paper_scalp_STOPPED.flag"
            write_dashboard(last, root=base)
            return last
        last = replay_paper_scalp(
            root=base,
            source=source,
            write=True,
            deny_model_signals=True,
            live_session=live_session,
        )
        last["heartbeat"] = {
            **(last.get("heartbeat") or {}),
            "tick_index": i,
            "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
            "alive": True,
            "dashboard_write_seconds": DASHBOARD_HEARTBEAT_SECONDS,
            "tick_seconds": int(tick_seconds),
            "tick_ne_dashboard_reason": TICK_NE_DASHBOARD_REASON,
        }
        write_dashboard(last, root=base)
        i += 1
        if max_ticks > 0 and i >= max_ticks:
            last["loop_stopped"] = "completed_max_ticks"
            return last

        def _beat(_remaining: float) -> None:
            refresh_dashboard_clock(last, tick_seconds=int(tick_seconds))
            write_dashboard(last, root=base)

        slept = sleep_with_beats(
            float(tick_seconds),
            beat_seconds=DASHBOARD_HEARTBEAT_SECONDS,
            sleep_fn=sleep,
            on_beat=_beat,
            stop_fn=lambda: stop_requested(base),
        )
        if slept == "stopped":
            last["loop_stopped"] = "ml_paper_scalp_STOPPED.flag"
            write_dashboard(last, root=base)
            return last
