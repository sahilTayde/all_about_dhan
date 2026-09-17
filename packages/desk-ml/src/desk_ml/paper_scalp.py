"""Parallel PAPER scalper books on INDEX+ATM tape. No live Dhan. No MIX-DEFAULT-BUY write.

Each book_id × underlying has at most one OPEN. Books never veto each other.
Default paper path: do **not** deny a model's CE/PE signal (founder paper). Overlay HOLD
is logged, not a skip. MIX-ML-LOGIT is an INDEX scan book, not the customer default.
Desk capital ₹70,000 split across LIVE_BOOKS (not 10k×8). Lot size from instrument master when available.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from desk_ml.features import Triple, build_feature_rows
from desk_ml.fit import fit_from_rows, score_features_dict
from desk_ml.inventory import inventory_recon
from desk_ml.model import OVERLAY_HOLD, premium_divergence_pattern
from desk_ml.mrr import Z_HOLD, ols_beta, rolling_z
from desk_ml.persist import pack_estimators, repo_root
from desk_ml.paper_lots import (
    STARTING_CAPITAL_INR,
    pnl_inr,
    resolve_lot_size,
    size_lots,
)

DESK_CAPITAL_INR = 70000.0
DASHBOARD_HEARTBEAT_SECONDS = 5
TICK_NE_DASHBOARD_REASON = (
    "Dhan POST /optionchain rate-limit: dual-tape poll stays ~45s (clamp ≥30). "
    "Dashboard JSON/MD rewrite every 5s from the last tick — not a new Dhan poll."
)
LIMIT_DISCOUNT_FRAC = 0.012  # working buy limit below signal LTP; fill is not assumed at signal
from desk_ml.groww_costs import as_dict as groww_cost_meta
from desk_ml.groww_costs import groww_round_trip_charges, net_pnl_inr
from desk_ml.greeks_ml import score_greeks_ticket, session_iv_median, wing_ivs
from desk_ml.tape import ist_calendar_date, load_dual_tape_triples, load_index_closes, load_triples

try:
    from warehouse.feasibility import evaluate_long_premium
except ImportError:  # pragma: no cover
    evaluate_long_premium = None  # type: ignore[assignment]

try:
    from trading_agents_india.desk_divergence import judge_tick
except ImportError:  # pragma: no cover
    judge_tick = None  # type: ignore[assignment]

IST = timezone(timedelta(hours=5, minutes=30))
FLATTEN_MINUTES_IST = 15 * 60  # 15:00 IST
NO_NEW_MINUTES_IST = 14 * 60 + 45  # do not arm a new limit into flatten
FILL_AWAY_FRAC = 0.03  # unfilled buy: LTP ran this far above limit
UNFILLED_BARS = 2
UNFILLED_SECONDS = 120
SCALP_HOLD_BARS = 8  # 1m tape ≈ 8 minutes
RANGE_LOOKBACK = 20
# INDEX 1m regime (HYPOTHESIS paper overlay). Not option L2. Not a MIX rewrite.
REGIME_LOOKBACK = 20
REGIME_MIN_BARS = 12
REGIME_ER_MAX = 0.30  # Kaufman efficiency |net|/path; at or below → chop
REGIME_FLIP_MIN = 0.38
REGIME_RANGE_ATR_MAX = 4.0  # window high-low / mean |1m close change|
SIDEWAYS_HOLD = "SIDEWAYS_HOLD"
STOP_FRAC = 0.40
TARGET_FRAC = 0.55
STRIKE_STEP = {"NIFTY": 50.0, "BANKNIFTY": 100.0, "SENSEX": 100.0}
# STRAT-006 paper wing: ~100 pts ITM, not ATM, not deep ITM. Not a promote.
ITM_POINTS = {"NIFTY": 100.0, "BANKNIFTY": 100.0, "SENSEX": 100.0}
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
# Overlay clones of dealer when deny_model_signals=false. Desk "earned" uses unique books.
UNIQUE_PNL_BOOKS = (
    "MIX-DEFAULT-BUY",
    "MIX-ML-LOGIT",
    "MIX-TV-EP-024",
    "MIX-ML-GREEKS",
)

TV_EP_KEEP_ALL = tuple(f"MIX-TV-EP-{i:03d}" for i in range(1, 26))
TV_EP_SHORTLIST = ("MIX-TV-EP-018", "MIX-TV-EP-010", "MIX-TV-EP-009")

STOP_FLAG_NAME = "ml_paper_scalp_STOPPED.flag"
DASH_JSON_NAME = "ml_paper_dashboard.json"
LOG_JSONL_NAME = "ml_paper_model_logs.jsonl"
PAPER_PARAMS_NAME = "ml_paper_session_params.json"
MISTAKES_NAME = "ml_paper_mistakes.jsonl"
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
    "dashboard_heartbeat_seconds": DASHBOARD_HEARTBEAT_SECONDS,
    "regime_lookback": REGIME_LOOKBACK,
    "regime_er_max": REGIME_ER_MAX,
    "regime_flip_min": REGIME_FLIP_MIN,
    "regime_range_atr_max": REGIME_RANGE_ATR_MAX,
    "production_params_written": False,
    "note": "PAPER session only. Never writes MIX-DEFAULT-BUY.",
}


def _ist_dt(ts: int) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=IST)


def minutes_ist(ts: int) -> int:
    dt = _ist_dt(ts)
    return dt.hour * 60 + dt.minute


def classify_index_regime(
    closes: Sequence[float],
    *,
    lookback: int = REGIME_LOOKBACK,
    er_max: float = REGIME_ER_MAX,
    flip_min: float = REGIME_FLIP_MIN,
    range_atr_max: float = REGIME_RANGE_ATR_MAX,
) -> dict[str, Any]:
    """TREND | SIDEWAYS | UNKNOWN from INDEX 1m closes only. HYPOTHESIS. No option L2."""
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
        "reason": "short_index_path",
    }
    if n < REGIME_MIN_BARS:
        return base
    window = vals[-max(REGIME_MIN_BARS, int(lookback)) :]
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
    chop = er <= float(er_max) and (
        flip_frac >= float(flip_min) or range_over_atr <= float(range_atr_max)
    )
    tight_mr = er <= float(er_max) and mid_dev_atr < 1.25 and range_over_atr <= float(range_atr_max)
    if chop or tight_mr:
        regime = "SIDEWAYS"
        reason = "low_er_flips_or_tight_band"
    elif er >= 0.45 or (er >= 0.35 and range_over_atr >= 5.0):
        regime = "TREND"
        reason = "directional_index_path"
    else:
        regime = "UNKNOWN"
        reason = "mixed_index_path"
    net_signed = window[-1] - window[0]
    if net_signed > 0:
        direction = "UP"
    elif net_signed < 0:
        direction = "DOWN"
    else:
        direction = "FLAT"
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
        "reason": reason,
    }


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
        "note": "Equal split of ₹70,000. SKIP/DI books do not keep a 10k seat. Not 10k×8.",
        "production_params_written": False,
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


def itm_wing_strikes(underlying: str, atm: float) -> dict[str, float]:
    """Buy-side ITM: CE below ATM, PE above ATM. ~100 index points."""
    und = underlying.upper()
    step = STRIKE_STEP.get(und, 50.0)
    points = ITM_POINTS.get(und, 100.0)
    n = max(1, int(round(float(points) / step)))
    atm_f = float(atm)
    return {"CE": atm_f - n * step, "PE": atm_f + n * step}


def _opt_px(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def quote_for_side(tick: Triple, side: str, *, strike: Optional[float] = None) -> tuple[Optional[float], Optional[float], str]:
    """Return (ltp, low, source). Booked strike never silently uses a rolled ATM/ITM print."""
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
            if side == "CE":
                atm = _opt_px(tick.ce_close)
                return atm, (_opt_px(tick.ce_low) or atm) if atm is not None else None, "ATM"
            atm = _opt_px(tick.pe_close)
            return atm, (_opt_px(tick.pe_low) or atm) if atm is not None else None, "ATM"
        if not wings and tick.atm_strike is None:
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
        atm = _opt_px(tick.ce_close)
        return atm, _opt_px(tick.ce_low) or atm, "ATM"
    itm = _opt_px(tick.itm_pe_close)
    if itm is not None:
        return itm, _opt_px(tick.itm_pe_low) or itm, "ITM_100"
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
    """ITM_100 default; if Dhan delta exists, prefer |delta| in 0.45–0.70 (not OTM)."""
    default = itm_wing_strikes(underlying, atm)[side]
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
        ad = abs(delta)
        if ad < DELTA_BAND[0] or ad > DELTA_BAND[1]:
            continue
        if side == "CE" and strike > float(atm) + 1e-6:
            continue
        if side == "PE" and strike < float(atm) - 1e-6:
            continue
        dist = abs(ad - DELTA_PREF)
        if dist < best_dist:
            best_dist = dist
            best = strike
    return float(best) if best is not None else default


def greeks_paper_adjust(
    *,
    entry: float,
    stop_frac: float,
    target_frac: float,
    delta: Optional[float] = None,
    gamma: Optional[float] = None,
    theta: Optional[float] = None,
    iv: Optional[float] = None,
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
    sf = float(stop_frac)
    tf = float(target_frac)
    if iv is not None and float(iv) >= 25.0:
        sf = min(0.55, sf * 1.15)
        notes.append(f"IV={iv}: wider paper stop (event/rich vol)")
    if theta is not None and entry > 0 and abs(float(theta)) / float(entry) >= 0.05:
        tf = max(0.28, tf * 0.85)
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


def propose_levels(
    entry: float,
    premiums: Sequence[float],
    *,
    stop_frac: float = STOP_FRAC,
    target_frac: float = TARGET_FRAC,
    limit_discount_frac: float = LIMIT_DISCOUNT_FRAC,
) -> dict[str, Any]:
    """Scalp stop/target from same-side premium path. Kills fantasy 150/96/250.

    Working limit sits below signal LTP so a fill is a cheaper buy — never assumed at signal.
    """
    if entry is None or entry <= 0:
        return {"ok": False, "reason_code": "DATA_INSUFFICIENT", "data_gaps": ["entry missing"]}
    path = [float(x) for x in premiums if x is not None]
    if len(path) < 2:
        path = [entry, entry * 1.01]
    typical = max(path) - min(path)
    if typical <= 0:
        typical = max(0.5, entry * 0.04)
    stop = entry - float(stop_frac) * typical
    target = entry + float(target_frac) * typical
    if stop <= 0:
        stop = max(0.05, entry * 0.85)
    feas = feasibility_long(entry=entry, stop=stop, target=target, typical_range=typical)
    if not feas.get("ok"):
        # Paper: still book with a tighter target (no 150/96/250). Do not deny the signal.
        stop = max(0.05, entry - min(float(stop_frac) * typical, entry * 0.12))
        target = entry + min(float(target_frac) * typical, entry * 0.18)
        feas = feasibility_long(entry=entry, stop=stop, target=target, typical_range=typical)
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
        "reason_code": feas.get("reason_code") if feas.get("ok") else "CLAMPED_PAPER_LEVELS",
        "scalp_hold_bars": SCALP_HOLD_BARS,
        "flatten_ist": "15:00",
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


@dataclass
class BookEngine:
    opens: dict[tuple[str, str], OpenPaper] = field(default_factory=dict)
    closed: list[dict[str, Any]] = field(default_factory=list)
    skips: list[dict[str, Any]] = field(default_factory=list)
    last_step: dict[str, Any] = field(default_factory=dict)
    equity: dict[str, float] = field(default_factory=dict)
    lot_by_und: dict[str, tuple[Optional[int], str]] = field(default_factory=dict)
    root: Optional[Path] = None
    deny_model_signals: bool = False
    starting_capital: float = STARTING_CAPITAL_INR
    paper_stop_frac: float = STOP_FRAC
    paper_target_frac: float = TARGET_FRAC
    paper_hold_bars: int = SCALP_HOLD_BARS
    paper_give_up_frac: float = GIVE_UP_FRAC
    skip_new_when_sideways: bool = True
    skip_trend_against: bool = True
    limit_discount_frac: float = LIMIT_DISCOUNT_FRAC
    capital_by_book: dict[str, float] = field(default_factory=dict)
    capital_plan: dict[str, Any] = field(default_factory=dict)
    regime_lookback: int = REGIME_LOOKBACK
    regime_er_max: float = REGIME_ER_MAX
    regime_flip_min: float = REGIME_FLIP_MIN
    regime_range_atr_max: float = REGIME_RANGE_ATR_MAX
    last_regime: dict[str, dict[str, Any]] = field(default_factory=dict)

    def book_capital(self, book_id: str) -> float:
        if book_id in self.capital_by_book:
            return float(self.capital_by_book[book_id])
        return float(self.starting_capital)

    def book_equity(self, book_id: str) -> float:
        return float(self.equity.setdefault(book_id, self.book_capital(book_id)))

    def has_open(self, book_id: str, underlying: str) -> bool:
        return (book_id, underlying) in self.opens

    def mark_skip(self, book_id: str, underlying: str, reason: str, **extra: Any) -> None:
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
    if judge_tick is None:
        return {"side": None, "verdict": "DATA_INSUFFICIENT", "case": "NO_DEALER"}
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
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")


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
    bi = 0
    for t in triples:
        while bi < len(bars) and bars[bi].ts <= int(t.ts):
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
    if bar_i - pos.opened_bar >= UNFILLED_BARS:
        return "CANCEL_UNFILLED_TIMEOUT"
    verdict = str(dealer_verdict or "")
    if pos.side == "CE" and verdict == "BUY_PE_CONFIRM":
        return "CANCEL_UNFILLED_THESIS"
    if pos.side == "PE" and verdict == "BUY_CE_CONFIRM":
        return "CANCEL_UNFILLED_THESIS"
    if live_delta is not None and abs(float(live_delta)) < DELTA_SKIP_BELOW:
        return "CANCEL_UNFILLED_DELTA"
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
) -> Optional[str]:
    """Exit a stuck long premium. Minute low counts. Do not wait out a dead contract."""
    px = float(ltp)
    low = float(side_low) if side_low is not None else px
    seen = float(pos.seen_low) if pos.seen_low is not None else px
    stop_px = min(px, low, seen)
    step = STRIKE_STEP.get(pos.underlying.upper(), 50.0)
    if stop_px <= pos.stop:
        return "STOP"
    if px >= pos.target:
        return "TARGET"
    if (
        pos.atm_strike is not None
        and atm_strike is not None
        and abs(float(atm_strike) - float(pos.atm_strike)) >= step - 1e-9
        and min(px, float(side_low) if side_low is not None else px) < float(pos.entry)
    ):
        return "CANCEL_STRIKE_ROLL"
    give_up = float(pos.entry) * (1.0 - float(give_up_frac))
    if stop_px <= give_up:
        return "CANCEL_ADVERSE"
    underwater = stop_px < float(pos.entry)
    verdict = str(dealer_verdict or "")
    if underwater and pos.side == "CE" and verdict == "BUY_PE_CONFIRM":
        return "CANCEL_THESIS"
    if underwater and pos.side == "PE" and verdict == "BUY_CE_CONFIRM":
        return "CANCEL_THESIS"
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
    if int(ts) - int(pos.opened_ts) >= int(hold_bars) * 60:
        return "TIME"
    if bar_i - pos.opened_bar >= int(hold_bars):
        return "TIME"
    if minutes_ist(ts) >= FLATTEN_MINUTES_IST:
        return "FLATTEN_1500"
    return None


def _close(engine: BookEngine, pos: OpenPaper, *, ltp: float, ts: int, reason: str, root: Optional[Path] = None) -> None:
    unfilled = (not pos.filled) or str(reason).startswith("CANCEL_UNFILLED")
    qty = pos.qty
    if qty is None and pos.lot_size is not None and int(pos.lot_size) > 0:
        qty = int(pos.lot_size) * int(pos.lots)
    charges = groww_round_trip_charges(
        exit_premium=float(ltp),
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
        result = "SUCCESS" if won else "LOSS"
    sl_hit = (not unfilled) and reason in {"STOP", "CANCEL_ADVERSE"}
    sl_loss_inr = inr if sl_hit and inr is not None and inr < 0 else (0.0 if sl_hit and inr is None else None)
    if sl_hit and inr is None:
        sl_loss_inr = round(points, 4)
    if sl_hit and inr is not None:
        sl_loss_inr = inr if inr < 0 else 0.0
    engine.closed.append(
        {
            "book_id": pos.book_id,
            "underlying": pos.underlying,
            "side": pos.side,
            "trade_id": pos.trade_id,
            "status": "CLOSED_PAPER",
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
            "regime_er": pos.regime_er,
            "regime_flip_frac": pos.regime_flip_frac,
            "regime_reason": pos.regime_reason,
            "opened_ts": pos.opened_ts,
            "closed_ts": ts,
            "opened_ist": _ist_dt(pos.opened_ts).isoformat(timespec="seconds"),
            "closed_ist": _ist_dt(ts).isoformat(timespec="seconds"),
            "shadow": True,
            "execution": "refused",
            "promote": False,
            "won": won,
            "result": result,
            "filled": (not unfilled),
        }
    )
    if inr is not None:
        engine.equity[pos.book_id] = engine.book_equity(pos.book_id) + inr
    engine.opens.pop((pos.book_id, pos.underlying), None)
    if root is not None:
        append_model_log(
            root,
            {
                "event": "CLOSE",
                "model": pos.book_id,
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
    if minutes_ist(tick.ts) >= NO_NEW_MINUTES_IST:
        engine.mark_skip(book_id, underlying, "NO_NEW_AFTER_1445", ts=tick.ts)
        return
    if engine.has_open(book_id, underlying):
        return
    capital = engine.book_capital(book_id)
    if capital <= 0:
        engine.mark_skip(
            book_id,
            underlying,
            "CAPITAL_SKIP_DATA_INSUFFICIENT",
            ts=tick.ts,
        )
        return
    classified = engine.last_regime.get(underlying.upper()) or {}
    regime = str(classified.get("regime") or "UNKNOWN")
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
    if skip_reason:
        engine.mark_skip(book_id, underlying, skip_reason, ts=tick.ts)
        if engine.root is not None:
            append_model_log(
                engine.root,
                {"event": "SKIP", "model": book_id, "underlying": underlying, "reason": skip_reason},
            )
        return
    if side not in {"CE", "PE"}:
        engine.mark_skip(book_id, underlying, "NO_SIDE", ts=tick.ts)
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
            )
            return
    atm = strike if strike is not None else round_atm_strike(underlying, tick.idx_close)
    want = pick_paper_strike(tick, side, atm, underlying)
    greeks = leg_greeks(tick, side, want)
    itm_px, _itm_low, itm_src = quote_for_side(tick, side, strike=want)
    booked_src = str(itm_src or "")
    if itm_px is not None and (booked_src.startswith("ITM") or booked_src.startswith("STRIKE_")):
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
    else:
        entry = tick.ce_close if side == "CE" else tick.pe_close
        booked = atm
        source = "ATM"
        path = list(ce_path if side == "CE" else pe_path)
    adj = greeks_paper_adjust(
        entry=float(entry),
        stop_frac=engine.paper_stop_frac,
        target_frac=engine.paper_target_frac,
        delta=greeks.get("delta"),
        gamma=greeks.get("gamma"),
        theta=greeks.get("theta"),
        iv=greeks.get("iv"),
    )
    if adj.get("skip"):
        engine.mark_skip(book_id, underlying, str(adj.get("reason") or "GREEKS_SKIP"), ts=tick.ts, **{k: greeks.get(k) for k in ("delta", "theta", "iv")})
        return
    levels = propose_levels(
        float(entry),
        path,
        stop_frac=float(adj["stop_frac"]),
        target_frac=float(adj["target_frac"]),
        limit_discount_frac=float(engine.limit_discount_frac),
    )
    lot_size, lot_src = engine.lot_by_und.get(underlying.upper(), (None, "unset"))
    sized = size_lots(entry=float(levels["limit_price"] or levels["entry"]), lot_size=lot_size, capital_inr=capital)
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
        lots=int(sized.get("lots") or 1),
        qty=sized.get("qty"),
        notional_inr=sized.get("notional_inr"),
        capital_inr=capital,
        lot_status=str(sized.get("lot_status") or lot_src),
        filled=False,
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
    )
    engine.opens[(book_id, underlying)] = pos
    if engine.root is not None:
        append_model_log(
            engine.root,
            {
                "event": "OPEN",
                "model": book_id,
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
            },
        )


def mark_to_market(
    engine: BookEngine,
    tick: Triple,
    underlying: str,
    bar_i: int,
    *,
    dealer_verdict: Optional[str] = None,
    atm_strike: Optional[float] = None,
) -> None:
    """Flatten/cancel OPEN tickets every bar. SIDEWAYS must not freeze an already-open book."""
    for book_id in list(LIVE_BOOKS):
        pos = engine.opens.get((book_id, underlying))
        if pos is None:
            continue
        ltp, side_low, src = quote_for_side(tick, pos.side, strike=pos.atm_strike)
        if ltp is None and pos.last_ltp is not None:
            ltp = float(pos.last_ltp)
            side_low = pos.seen_low if pos.seen_low is not None else ltp
            src = "LAST_PRINT"
        if ltp is None:
            if minutes_ist(tick.ts) >= FLATTEN_MINUTES_IST:
                _close(
                    engine,
                    pos,
                    ltp=float(pos.entry),
                    ts=tick.ts,
                    reason="CANCEL_UNFILLED_FLAT" if not pos.filled else "FLATTEN_1500",
                    root=engine.root,
                )
            continue
        if side_low is None:
            side_low = ltp
        pos.last_ltp = float(ltp)
        pos.quote_src = src
        low_v = float(side_low)
        pos.seen_low = min(pos.seen_low if pos.seen_low is not None else low_v, low_v, float(ltp))
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
            )
            if u_reason == "FILL":
                pos.filled = True
                limit = float(pos.limit_price or pos.entry)
                if float(ltp) <= limit + 1e-9:
                    pos.entry = min(float(ltp), limit)
                else:
                    pos.entry = limit
            elif u_reason:
                _close(engine, pos, ltp=float(ltp), ts=tick.ts, reason=u_reason, root=engine.root)
                continue
            else:
                continue
        live_atm = atm_strike if atm_strike is not None else tick.atm_strike
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
        )
        if reason:
            exit_px = float(ltp)
            if reason in {"STOP", "CANCEL_ADVERSE"}:
                exit_px = min(exit_px, low_v, float(pos.seen_low or exit_px))
            _close(engine, pos, ltp=exit_px, ts=tick.ts, reason=reason, root=engine.root)


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
    deny_model_signals: bool = False,
) -> None:
    if i < 1:
        return
    und = underlying.upper()
    tick = triples[i]
    prev = triples[i - 1]
    idx_d = tick.idx_close - prev.idx_close
    classified = classify_index_regime(
        [float(t.idx_close) for t in triples[: i + 1]],
        lookback=engine.regime_lookback,
        er_max=engine.regime_er_max,
        flip_min=engine.regime_flip_min,
        range_atr_max=engine.regime_range_atr_max,
    )
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

    dealer_proposal = dealer.get("side") if dealer.get("allow_new_paper_ce_pe") else None
    extra = dealer.get("extra") if isinstance(dealer.get("extra"), dict) else {}
    train_side = extra.get("train_side") if extra else None
    fallback = dealer_proposal or train_side or tv_side
    if fallback not in {"CE", "PE"}:
        if idx_d > 1.0:
            fallback = "CE"
        elif idx_d < -1.0:
            fallback = "PE"
    window = triples[max(0, i - RANGE_LOOKBACK) : i + 1]
    ce_path = [
        float(t.itm_ce_close if t.itm_ce_close is not None else t.ce_close) for t in window
    ]
    pe_path = [
        float(t.itm_pe_close if t.itm_pe_close is not None else t.pe_close) for t in window
    ]
    deny = bool(deny_model_signals or engine.deny_model_signals)

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

    dealer_skip = None if dealer_proposal else f"DEALER_{dealer.get('verdict')}"
    if not deny and fallback in {"CE", "PE"}:
        dealer_skip = None
        dealer_proposal = dealer_proposal or fallback
    _open("MIX-DEFAULT-BUY", dealer_proposal, dealer_skip)

    ml001_skip = None
    ml001_side = dealer_proposal or fallback
    if deny and (ml001_hold or follow_gap):
        ml001_skip = "ML-001_HOLD"
    elif ml001_side not in {"CE", "PE"}:
        ml001_skip = "NO_SIDE"
    _open("ML-001", ml001_side, ml001_skip)

    ml002_skip = None
    ml002_side = dealer_proposal or fallback
    if deny and (ml002_hold or follow_gap):
        ml002_skip = "ML-002_HOLD"
    elif ml002_side not in {"CE", "PE"}:
        ml002_skip = "NO_SIDE"
    _open("ML-002", ml002_side, ml002_skip)

    ml1_skip = None
    ml1_side = dealer_proposal or fallback
    if deny:
        if ml1.get("status") != "OK":
            ml1_skip = str(ml1.get("reason") or "ML-1_DATA_INSUFFICIENT")
        elif ml1.get("take") is False:
            ml1_skip = "ML-1_SKIP"
        elif ml1_side not in {"CE", "PE"}:
            ml1_skip = "NO_DEALER_TICKET"
    elif ml1_side not in {"CE", "PE"}:
        ml1_skip = "NO_SIDE"
    _open("ML-1", ml1_side, ml1_skip)

    logit_side = logit.get("side") if logit.get("side") in {"CE", "PE"} else (None if deny else fallback)
    logit_skip = None if logit_side in {"CE", "PE"} else str(logit.get("reason") or logit.get("status") or "NO_SIDE")
    _open("MIX-ML-LOGIT", logit_side, logit_skip)

    xr_side = logit_xr.get("side") if logit_xr.get("side") in {"CE", "PE"} else (None if deny else fallback)
    xr_skip = None if xr_side in {"CE", "PE"} else str(logit_xr.get("reason") or logit_xr.get("status") or "NO_SIDE")
    _open("MIX-ML-LOGIT-XR", xr_side, xr_skip)

    tv = tv_side if tv_side in {"CE", "PE"} else (None if deny else fallback)
    _open("MIX-TV-EP-024", tv, None if tv in {"CE", "PE"} else "TV-EP-024 SMA20 flat or warmup")

    greeks_side = dealer_proposal or fallback
    greeks_skip = None
    if greeks_side not in {"CE", "PE"}:
        greeks_skip = "NO_SIDE"
    else:
        want = pick_paper_strike(tick, greeks_side, float(strike or round_atm_strike(und, tick.idx_close)), und)
        greeks = leg_greeks(tick, greeks_side, want)
        px, _, _src = quote_for_side(tick, greeks_side, strike=want)
        entry = float(px) if px is not None else (tick.ce_close if greeks_side == "CE" else tick.pe_close)
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
    _open("MIX-ML-GREEKS", greeks_side, greeks_skip)

    engine.last_step = {
        "underlying": und,
        "ts": tick.ts,
        "dealer": dealer,
        "ml001_hold": ml001_hold,
        "ml002_hold": ml002_hold,
        "follow_gap": follow_gap,
        "logit": logit,
        "logit_xr": logit_xr,
        "ml1": ml1,
        "tv_ep_024": tv_side,
        "mix_ml_greeks_skip": greeks_skip,
        "index_regime": classified,
        "independent": True,
        "note": "HOLD on one book does not veto another. SIDEWAYS skips NEW opens only. TREND direction confirm/kill PE vs CE. Feed stays live.",
    }


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
    gap: list[bool] = []
    row_i = -1
    for t in triples:
        feat_row = by_ts.get(int(t.ts))
        if feat_row is None:
            ml001.append(False)
            ml002.append(False)
            gap.append(False)
            continue
        row_i += 1
        feat = {name: float(feat_row[name]) for name in names}
        scored = score_features_dict(feat, bundle)
        g = premium_divergence_pattern(feat_row["idx_ret"], feat_row["ce_ret"], feat_row["pe_ret"])
        z_hold = False
        if row_i < len(zs) and zs[row_i] is not None:
            z_hold = abs(float(zs[row_i])) >= Z_HOLD
        ml001.append(scored.get("overlay") == OVERLAY_HOLD)
        ml002.append(z_hold)
        gap.append(g)
    meta["status"] = "OK"
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
        "dashboard_heartbeat_seconds",
        "regime_lookback",
        "regime_er_max",
        "regime_flip_min",
        "regime_range_atr_max",
    ):
        if key in blob and blob[key] is not None:
            out[key] = blob[key]
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
        elif reason in {"CANCEL_ADVERSE", "CANCEL_THESIS", "CANCEL_STRIKE_ROLL"}:
            lesson = f"{reason}: ticket was dead; cancel instead of sitting to TIME"
            tweak = "give-up / thesis-flip / strike-roll cancel is the paper rule"
        elif reason.startswith("CANCEL_UNFILLED"):
            lesson = f"{reason}: limit never filled — candle walked away or thesis/greeks died"
            tweak = "do not assume fill at signal print; cancel unfilled limits"
        elif reason == "FLATTEN_1500":
            lesson = "FLATTEN_LOSS: still open into 15:00 IST"
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
                "lesson": "KEEP: same-side path reached target or time-exit still green",
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
    wins = sum(1 for c in closed if c.get("result") == "SUCCESS")
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
        target_frac = min(0.70, round(target_frac + 0.02, 4))
        notes.append(f"many TARGET wins → paper target_frac={target_frac}")
    params["stop_frac"] = stop_frac
    params["target_frac"] = target_frac
    params["scalp_hold_bars"] = hold
    params["nudge_n_closed"] = n
    if not notes:
        notes.append("session mix inside band; keep paper params")
    return params, notes


def replay_paper_scalp(
    *,
    root: Optional[Path] = None,
    underlyings: Sequence[str] = ("NIFTY", "BANKNIFTY", "SENSEX"),
    source: str = "cache",
    triples_by_und: Optional[dict[str, list[Triple]]] = None,
    write: bool = False,
    max_closes: int = 0,
    deny_model_signals: bool = False,
    starting_capital: Optional[float] = None,
    live_session: bool = False,
    session_ist_date: Optional[str] = None,
    desk_capital: Optional[float] = None,
) -> dict[str, Any]:
    base = root or repo_root()
    now = datetime.now(IST)
    session_day = session_ist_date or (now.date().isoformat() if live_session else None)
    params = load_paper_params(base) if live_session else dict(DEFAULT_PAPER_PARAMS)
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

    tradable = list(LIVE_BOOKS)
    has_greeks = any(tape_has_dhan_greeks(loaded[u]) for u in loaded)
    if not has_greeks:
        tradable = [b for b in LIVE_BOOKS if b != "MIX-ML-GREEKS"]
    plan = allocate_desk_capital(total=desk_total, tradable=tradable)

    engine = BookEngine(
        root=base,
        deny_model_signals=deny_model_signals,
        starting_capital=STARTING_CAPITAL_INR,
        paper_stop_frac=float(params.get("stop_frac") or STOP_FRAC),
        paper_target_frac=float(params.get("target_frac") or TARGET_FRAC),
        paper_hold_bars=int(params.get("scalp_hold_bars") or SCALP_HOLD_BARS),
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
                "reason": "need ≥8 aligned INDEX+ATM 1m triples; do not fabricate bars",
                "tape": tape,
            }
            continue
        ml001, ml002, gap, hold_meta = _hold_series(triples)
        idx_closes = load_index_closes(u, root=base)
        if triples_by_und is not None:
            idx_closes = {int(t.ts): float(t.idx_close) for t in triples}
        logit_series, logit_meta = logit_side_series(triples, index_closes=idx_closes, xr=False)
        logit_xr_series, logit_xr_meta = logit_side_series(triples, index_closes=idx_closes, xr=True)
        thin_logit = {
            "side": None,
            "status": "DATA_INSUFFICIENT",
            "reason": "no logit series",
        }
        idx_path: list[float] = []
        for i, tick in enumerate(triples):
            idx_path.append(tick.idx_close)
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
        # Live session keeps WORKING/OPEN only before 15:00 IST. After flatten, leftovers close.
        last = triples[-1]
        past_flat = minutes_ist(last.ts) >= FLATTEN_MINUTES_IST
        if (not live_session) or past_flat:
            last = triples[-1]
            for book_id in LIVE_BOOKS:
                pos = engine.opens.get((book_id, u))
                if pos is None:
                    continue
                ltp = last.ce_close if pos.side == "CE" else last.pe_close
                reason = "CANCEL_UNFILLED_FLAT" if not pos.filled else ("FLATTEN_1500" if past_flat else "REPLAY_END")
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
    if live_session:
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
                "kind": "ML" if book in ML_BOOK_IDS else ("DEALER" if book == "MIX-DEFAULT-BUY" else "LAB"),
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
    filled = [r for r in closed if str(r.get("result")) in {"SUCCESS", "LOSS"}]
    cancelled = [r for r in closed if str(r.get("result")) == "CANCELLED"]
    nets = [_net_or_points(r) for r in filled]
    gross_vals = [float(r["gross_pnl_inr"]) for r in filled if r.get("gross_pnl_inr") is not None]
    gross = _sum_opt([r.get("gross_pnl_inr") for r in filled]) or 0.0
    charges = _sum_opt([r.get("charges_inr") for r in filled]) or 0.0
    brokerage = _sum_opt([r.get("brokerage_inr") for r in filled]) or 0.0
    gst = _sum_opt([r.get("gst_inr") for r in filled]) or 0.0
    stt = _sum_opt([r.get("stt_inr") for r in filled]) or 0.0
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
        "filled_by_index_regime": regime_counts,
        "cost_model": groww_cost_meta(),
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
    row["status"] = "OPEN_PAPER" if pos.filled else "WORKING_LIMIT"
    row["filled"] = bool(pos.filled)
    row["result"] = None
    row["sl_hit"] = False
    row["sl_loss_inr"] = None
    row["realized_pnl_inr"] = None
    row["opened_ist"] = _ist_dt(pos.opened_ts).isoformat(timespec="seconds")
    return row


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
        scored_b = [c for c in closed_b if c.get("result") in {"SUCCESS", "LOSS"}]
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
    open_rows = [_open_ticket_row(p) for p in engine.opens.values()]
    scored_all = [c for c in engine.closed if c.get("result") in {"SUCCESS", "LOSS"}]
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
    side_bars = {(s.get("ts"), s.get("underlying")) for s in side_skips}
    picture["n_skip_sideways"] = len(side_skips)
    picture["n_sideways_bars"] = len(side_bars)
    picture["last_index_regime"] = dict(engine.last_regime)
    adj_notes = index_adjustment_notes(
        engine.closed,
        board_book_rank,
        board_leaderboard,
        net_by_index=picture.get("unique_net_by_index") or picture.get("net_by_index"),
    )
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
        "capital_plan": engine.capital_plan or allocate_desk_capital(tradable=list(LIVE_BOOKS)),
        "overall_pnl_inr": overall_pnl_inr,
        "overall_gross_pnl_inr": picture["gross_pnl_inr"],
        "overall_charges_inr": picture["charges_inr"],
        "money_won_inr": money_won_inr,
        "money_lost_inr": money_lost_inr,
        "equity_sum_inr": round(sum(engine.book_equity(b) for b in LIVE_BOOKS), 2),
        "today": picture,
        "n_skip_sideways": picture.get("n_skip_sideways") or 0,
        "n_sideways_bars": picture.get("n_sideways_bars") or 0,
        "n_sl_hit": picture.get("n_sl_hit") or 0,
        "last_index_regime": picture.get("last_index_regime") or {},
        "book_rank": board_book_rank,
        "index_notes": adj_notes,
        "cost_model": groww_cost_meta(),
        "paper_params": params,
        "paper_param_notes": list(paper_param_notes or []),
        "mistakes": mistakes[-40:],
        "successes": successes[-20:],
        "deny_model_signals": engine.deny_model_signals,
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
        ],
        "source": source,
        "customer_mix": "MIX-DEFAULT-BUY unchanged (dealer book is PAPER parallel, not a live rewrite)",
        "independent_books": True,
        "one_open_per": "book_id × underlying",
        "scalper_exits": {
            "stop": f"long premium LTP <= entry - {engine.paper_stop_frac}×same-side path range",
            "target": f"LTP >= entry + {engine.paper_target_frac}×path range",
            "time": f"{engine.paper_hold_bars} 1m bars or wall-clock",
            "cancel_adverse": f"same-side low <= entry×(1-{engine.paper_give_up_frac})",
            "cancel_thesis": "opposite BUY_*_CONFIRM only if already underwater vs entry",
            "cancel_greeks": "|delta| too low / IV rich / theta late on live chain — cancel WORKING or OPEN",
            "limit_below_signal": f"working buy limit = signal × (1-{engine.limit_discount_frac})",
            "cancel_strike_roll": "ATM strike moved off the ticket and premium is below entry",
            "flatten_ist": "15:00",
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
        "closed_trades": engine.closed,
        "leaderboard": board_leaderboard,
        "tv_ep_inventory": tv_inventory,
        "heartbeat": {
            "cli": "python -m desk_ml paper-scalp --replay",
            "loop": "python -m desk_ml paper-scalp --loop  (opt-in; writes this JSON)",
            "dual_tape": "python -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 45 --max-ticks 0",
            "stop": f"touch data/recon/{STOP_FLAG_NAME}",
            "dashboard_write_seconds": DASHBOARD_HEARTBEAT_SECONDS,
            "tick_seconds_default": 45,
            "tick_ne_dashboard_reason": TICK_NE_DASHBOARD_REASON,
            "does_not_start": ["paper_ops", "npm", "legacy LLM waiters"],
        },
        "honesty": [
            "Closed net ₹ after Groww brokerage + GST + option STT ranks. Open rows do not.",
            "win_rate_pct is paper filled hit rate (net ₹>0 / n_filled) × 100. win_rate_gross_pct is the same before Groww+STT. NO_PROMOTE.",
            "Groww F&O ₹20/executed order × 2 legs; GST 18% on that brokerage; STT 0.15% of sell premium (VERIFY, Budget 2026).",
            "Unfilled CANCELLED = ₹0 P/L and ₹0 charges. Exchange/SEBI/stamp omitted (UNKNOWN).",
            "Desk starts at ₹70,000 split equally across tradable LIVE_BOOKS. SKIP/DI books get ₹0 and the rest is redistributed. Not 10k×8=80k.",
            "Paper does not deny model CE/PE signals (deny_model_signals default false).",
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
            "No new paper after 14:45 IST. 15:00 flattens leftover OPEN. live_session does not keep dead tickets overnight.",
            "paper_params nudge is session-only overfit. production_params_written stays false.",
            "INDEX 1m regime TREND|SIDEWAYS|UNKNOWN is HYPOTHESIS. SIDEWAYS skips NEW paper opens; flatten/cancel still run. Feed stays live.",
            "TREND + direction UP kills new PE (confirm/kill overlay, not a STRAT). DOWN kills new CE. Not MIX-DEFAULT-BUY production.",
            "Founder ~57% wr during cash hours is an in-session PAPER observation, not this EOD Groww+STT filled hit rate. Not a promote.",
        ],
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
            "n_sideways_bars",
            "n_sl_hit",
            "last_index_regime",
            "paper_params",
            "paper_param_notes",
            "ticket_columns",
            "source",
            "independent_books",
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
        u: {kk: vv for kk, vv in (s or {}).items() if kk in {"status", "n_triples", "span_ist", "logit", "ml1", "index_regime"}}
        for u, s in (board.get("steps") or {}).items()
    }
    compact["n_closed"] = len(board.get("closed_trades") or [])
    compact["n_open"] = len(board.get("open_trades") or [])
    compact["closed_trades_sample"] = (board.get("closed_trades") or [])[-20:]
    compact["open_trades"] = board.get("open_trades") or []
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
        f"desk ₹{board.get('starting_desk_inr')} split across {board.get('n_books')} books "
        f"(typical ₹{board.get('starting_capital_inr_per_book')}/tradable).  ",
        f"**Gross P/L:** ₹{board.get('overall_gross_pnl_inr')} · **charges:** ₹{board.get('overall_charges_inr')} "
        f"(Groww+GST+STT VERIFY) · **Net P/L:** ₹{board.get('overall_pnl_inr')} · won ₹{board.get('money_won_inr')} · "
        f"lost ₹{board.get('money_lost_inr')} · desk equity ₹{board.get('equity_sum_inr')}  "
        f"(start ₹{board.get('starting_desk_inr')}). Open {board.get('n_open')}.",
        "",
        "Parallel independent books: one OPEN per (`book_id` × underlying). A HOLD on ML-001 does **not** block MIX-DEFAULT-BUY.",
        "",
        "## Today at a glance (gross vs net after Groww + STT)",
        "",
    ]
    pic = board.get("today") or {}
    plan = board.get("capital_plan") or {}
    lines.append(
        f"Filled {pic.get('n_filled', board.get('n_closed'))} · cancelled {pic.get('n_cancelled', 0)} · "
        f"W net {pic.get('n_wins', board.get('n_wins'))} / L {pic.get('n_losses', board.get('n_losses'))} · "
        f"W gross {pic.get('n_wins_gross', board.get('n_wins_gross'))} / L gross {pic.get('n_losses_gross')}."
    )
    lines.append(
        f"wr **gross** {pic.get('win_rate_gross_pct', board.get('win_rate_gross_pct'))}% · "
        f"wr **net** {pic.get('win_rate_net_pct', board.get('win_rate_net_pct', board.get('win_rate_pct')))}% "
        f"(Groww+GST+STT VERIFY)."
    )
    alloc = plan.get("per_book") or board.get("capital_per_book") or {}
    if alloc:
        parts = [f"`{k}` ₹{v}" for k, v in alloc.items()]
        lines.append(
            "Capital split (₹70k desk, SKIP/DI = ₹0 redistributed): " + " · ".join(parts) + "."
        )
    lines.append(
        f"Gross ₹{pic.get('gross_pnl_inr', board.get('overall_gross_pnl_inr'))} − "
        f"brokerage ₹{pic.get('brokerage_inr')} − GST ₹{pic.get('gst_inr')} − STT ₹{pic.get('stt_inr')} "
        f"= **net ₹{pic.get('net_pnl_inr', board.get('overall_pnl_inr'))}**."
    )
    lines.append(
        f"SIDEWAYS skip (NEW opens only, HYPOTHESIS): n_skip_sideways={board.get('n_skip_sideways', pic.get('n_skip_sideways'))} "
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
        "## Open tickets (strike / limit / SL / CE|PE / status)",
        "",
        "| model | und | CE/PE | strike | limit | stop | last_ltp | filled | status | regime |",
        "|-------|-----|-------|--------|-------|------|----------|--------|--------|--------|",
    ]
    for row in board.get("open_trades") or []:
        lines.append(
            f"| `{row.get('book_id')}` | {row.get('underlying')} | {row.get('side')} | "
            f"{row.get('atm_strike')} | {row.get('limit_price')} | {row.get('stop')} | "
            f"{row.get('last_ltp')} | {row.get('filled')} | "
            f"{row.get('status') or 'OPEN_PAPER'} | {row.get('index_regime') or '—'} |"
        )
    if not board.get("open_trades"):
        lines.append("| — | — | — | — | — | — | — | — | none | — |")
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
        "## Closed tickets (strike / limit / target / SL / WIN|LOSS / money)",
        "",
        "| model | und | side | strike | limit | target | stop | status | sl_hit | money lost ₹ | pnl ₹ | WIN/LOSS | regime |",
        "|-------|-----|------|--------|-------|--------|------|--------|--------|--------------|-------|----------|--------|",
    ]
    for row in (board.get("closed_trades") or [])[-20:]:
        lost = row.get("sl_loss_inr")
        if lost is None and row.get("result") == "LOSS":
            lost = row.get("realized_pnl_inr")
        lines.append(
            f"| `{row.get('book_id')}` | {row.get('underlying')} | {row.get('side')} | "
            f"{row.get('atm_strike')} | {row.get('limit_price')} | {row.get('target')} | {row.get('stop')} | "
            f"{row.get('status')} | {row.get('sl_hit')} | {lost} | {row.get('realized_pnl_inr')} | {row.get('result')} | "
            f"{row.get('index_regime') or '—'} |"
        )
    if not board.get("closed_trades"):
        lines.append("| — | — | — | — | — | — | — | — | — | — | — | — | — |")
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
        "python -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 45 --max-ticks 0",
        "touch data/recon/ml_paper_scalp_STOPPED.flag",
        "```",
        "",
        "Dashboard JSON/MD rewrite **every 5s** from the last tick. Dual-tape Dhan poll stays **45s** "
        "(optionchain rate-limit). Tick ≠ 5s on purpose.",
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
    tick_seconds: int = 45,
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
                deny_model_signals=False,
                live_session=live_session,
            )
            last["loop_stopped"] = "ml_paper_scalp_STOPPED.flag"
            write_dashboard(last, root=base)
            return last
        last = replay_paper_scalp(
            root=base,
            source=source,
            write=True,
            deny_model_signals=False,
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
