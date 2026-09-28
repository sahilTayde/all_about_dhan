"""Composable, parameterised exit rules. Each plan is opt-in and named."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

from exitlab.clock import ReplayClock, as_ist, in_feed_freeze, past_square_off
from exitlab.scenarios import kaufman_er
from exitlab.types import OpenState

# Faithful constants copied from paper_scalp.py (reference only; not imported).
LEGACY_STOP_FRAC = 0.40
LEGACY_TARGET_FRAC = 0.55
LEGACY_NO_PROG_BARS = 3
LEGACY_NO_PROG_MFE = 2.0
LEGACY_BOOK_NEAR_FRAC = 0.70
LEGACY_STALL_MIN_SEC = 20 * 60
LEGACY_STALL_HIGH_STALE_SEC = 8 * 60
LEGACY_STALL_MIN_SEC_CHOP = 8 * 60
LEGACY_STALL_HIGH_STALE_CHOP = 3 * 60
LEGACY_STALL_ER_MAX = 0.18
LEGACY_STALL_TREND_ER = 0.35
LEGACY_STALL_CHOP_PROGRESS = 0.40
LEGACY_TIME_HARD_SEC = 45 * 60
LEGACY_GIVE_UP_FRAC = 0.12
LEGACY_FLATTEN = time(15, 16)
V2_FLAT = time(15, 15)
HOUSE_MAX_LOSS_INR = 30000.0


@dataclass(frozen=True)
class PlanSpec:
    plan_id: str
    params: dict[str, Any] = field(default_factory=dict)
    family: str = "lab"


Decision = str  # exit reason or ""


def _age_s(state: OpenState, now: datetime) -> float:
    return (as_ist(now) - as_ist(state.entry.ts)).total_seconds()


def _progress(state: OpenState) -> float:
    entry = state.entry.entry_price
    tgt = state.target_premium
    if tgt is None or tgt <= entry:
        return 0.0
    return (state.seen_high - entry) / (tgt - entry)


def pretrade_skip(
    state: OpenState, *, now: datetime, index: float | None, iv: float | None
) -> str | None:
    """Skip/no-trade conditions known at or before entry."""
    extra = state.entry.extra
    spread = extra.get("spread")
    max_spread = extra.get("max_spread", 4.0)
    if spread is not None and float(spread) > float(max_spread):
        return "SKIP_WIDE_SPREAD"
    if extra.get("too_close_to_square"):
        return "SKIP_NEAR_SQUARE"
    if extra.get("event_window"):
        return "SKIP_EVENT_WINDOW"
    if extra.get("iv_rich"):
        return "SKIP_IV_RICH"
    _ = now, index, iv
    return None


def hard_stop(state: OpenState, mark: float) -> Decision:
    stop = state.trail_stop if state.trail_stop is not None else state.stop_premium
    if stop is not None and mark <= stop + 1e-9:
        return "HARD_STOP"
    return ""


def target_hit(state: OpenState, mark: float) -> Decision:
    if state.target_premium is not None and mark + 1e-9 >= state.target_premium:
        return "TARGET"
    return ""


def time_stop(
    state: OpenState, now: datetime, after_s: float, unless_profit: float = 0.0
) -> Decision:
    if _age_s(state, now) < after_s:
        return ""
    if unless_profit > 0 and (state.last_bid or 0) - state.entry.entry_price >= unless_profit:
        return ""
    return "TIME"


def no_progress(state: OpenState, bars: int, mfe_pts: float) -> Decision:
    if len(state.closed_bars) < bars:
        return ""
    if (state.mfe - state.entry.entry_price) < mfe_pts:
        return "NO_PROGRESS"
    return ""


def stall(state: OpenState, now: datetime, *, chop: bool) -> Decision:
    min_sec = LEGACY_STALL_MIN_SEC_CHOP if chop else LEGACY_STALL_MIN_SEC
    stale_sec = LEGACY_STALL_HIGH_STALE_CHOP if chop else LEGACY_STALL_HIGH_STALE_SEC
    if _age_s(state, now) < min_sec:
        return ""
    er = kaufman_er(state.premium_prints, 15)
    if er is None or er > LEGACY_STALL_ER_MAX:
        return ""
    if state.seen_high_ts is None or state.last_bid is None:
        return ""
    stale = (as_ist(now) - as_ist(state.seen_high_ts)).total_seconds() >= stale_sec
    px = state.last_bid
    peak = state.seen_high
    at_failed = abs(px - peak) <= 0.6 and _age_s(state, now) >= min_sec + 5 * 60
    stale_scratch = stale and px + 1e-9 >= state.entry.entry_price and px <= peak - 0.15
    chop_near = (
        chop
        and px + 1e-9 >= state.entry.entry_price
        and _progress(state) >= LEGACY_STALL_CHOP_PROGRESS
        and (stale_scratch or at_failed or px <= peak - 0.15)
    )
    if at_failed or stale_scratch or chop_near:
        return "STALL"
    return ""


def book_near(state: OpenState) -> Decision:
    if len(state.closed_bars) < 2:
        return ""
    span = None
    if state.target_premium and state.target_premium > state.entry.entry_price:
        span = state.target_premium - state.entry.entry_price
    if not span:
        return ""
    if (state.mfe - state.entry.entry_price) < LEGACY_BOOK_NEAR_FRAC * span:
        return ""
    prev, last = state.closed_bars[-2], state.closed_bars[-1]
    if last.close < prev.close:
        return "BOOK_NEAR"
    return ""


def flatten_eod(now: datetime, flat: time) -> Decision:
    return "FLATTEN_EOD" if past_square_off(now, flat) else ""


def stale_feed(state: OpenState, now: datetime, max_age_s: float = 90.0) -> Decision:
    if state.last_quote_ts is None:
        return "STALE_FEED"
    if (as_ist(now) - as_ist(state.last_quote_ts)).total_seconds() > max_age_s:
        return "STALE_FEED"
    return ""


def theta_bleed(
    state: OpenState,
    *,
    index_move_pts: float,
    premium_change: float,
    flat_index_pts: float,
    min_age_s: float,
    now: datetime,
) -> Decision:
    if _age_s(state, now) < min_age_s:
        return ""
    if abs(index_move_pts) > flat_index_pts:
        return ""
    if premium_change < 0:
        return "THETA_BLEED"
    return ""


def mfe_giveback(state: OpenState, mark: float, give_frac: float, activate: float) -> Decision:
    run = state.mfe - state.entry.entry_price
    if run < activate:
        return ""
    if mark <= state.mfe - give_frac * run:
        return "MFE_GIVEBACK"
    return ""


def chandelier_trail(state: OpenState, mark: float, atr_k: float, atr: float | None) -> None:
    if atr is None or atr <= 0:
        return
    proposed = state.seen_high - atr_k * atr
    if state.trail_stop is None or proposed > state.trail_stop:
        state.trail_stop = proposed
    _ = mark


def vol_crush(state: OpenState, iv_now: float | None, drop_frac: float) -> Decision:
    iv0 = state.entry.iv_at_entry
    if iv0 is None or iv_now is None or iv0 <= 0:
        return ""
    if iv_now <= iv0 * (1.0 - drop_frac):
        return "IV_CRUSH"
    return ""


def lunch_chop(state: OpenState, now: datetime, er: float | None) -> Decision:
    t = as_ist(now).time()
    if not (time(12, 0) <= t < time(13, 30)):
        return ""
    if er is not None and er < 0.20 and _age_s(state, now) >= 12 * 60:
        return "LUNCH_CHOP"
    return ""


def index_vwap_loss(
    state: OpenState, index: float | None, vwap: float | None, side: str
) -> Decision:
    if index is None or vwap is None:
        return ""
    if side == "CE" and index < vwap:
        return "VWAP_LOSS"
    if side == "PE" and index > vwap:
        return "VWAP_LOSS"
    return ""


def freeze_window(now: datetime) -> Decision:
    return "FEED_FREEZE_FLAT" if in_feed_freeze(now) else ""


class ExitPlanFn:
    """A named plan that inspects only clock-visible state."""

    def __init__(
        self, spec: PlanSpec, fn: Callable[[OpenState, ReplayClock, dict[str, Any]], str]
    ) -> None:
        self.spec = spec
        self._fn = fn

    @property
    def plan_id(self) -> str:
        return self.spec.plan_id

    def decide(self, state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        return self._fn(state, clock, ctx)


def _init_stop_target(state: OpenState, stop_frac: float, target_frac: float) -> None:
    entry = state.entry.entry_price
    state.stop_premium = entry * (1.0 - stop_frac)
    state.target_premium = entry * (1.0 + target_frac)


def plan_hold_to_1515() -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        _ = state, ctx
        return flatten_eod(clock.now, V2_FLAT)

    return ExitPlanFn(PlanSpec("hold_to_1515", family="baseline"), _fn)


def plan_fixed_stop_target(stop_frac: float = 0.25, target_frac: float = 0.40) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        if state.stop_premium is None:
            _init_stop_target(state, stop_frac, target_frac)
        mark = ctx["mark"]
        return flatten_eod(clock.now, V2_FLAT) or hard_stop(state, mark) or target_hit(state, mark)

    return ExitPlanFn(
        PlanSpec(
            "fixed_stop_target", {"stop_frac": stop_frac, "target_frac": target_frac}, "baseline"
        ),
        _fn,
    )


def plan_v2_default(max_loss_inr: float = HOUSE_MAX_LOSS_INR) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        qty = state.remaining_qty
        if state.stop_premium is None and qty > 0:
            state.stop_premium = max(0.05, state.entry.entry_price - max_loss_inr / qty)
        mark = ctx["mark"]
        if mark <= (state.stop_premium or 0) + 1e-9:
            return "CATASTROPHIC_STOP"
        return flatten_eod(clock.now, V2_FLAT)

    return ExitPlanFn(PlanSpec("v2_default", {"max_loss_inr": max_loss_inr}, "baseline"), _fn)


def plan_legacy_overlay() -> ExitPlanFn:
    """Faithful reference of paper_scalp overlay constants. Not a promote."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        if state.stop_premium is None:
            _init_stop_target(state, LEGACY_STOP_FRAC, LEGACY_TARGET_FRAC)
        mark = ctx["mark"]
        chop = bool(ctx.get("chop"))
        if flatten_eod(clock.now, LEGACY_FLATTEN):
            return "FLATTEN_1516"
        if hard_stop(state, mark):
            return "STOP"
        if target_hit(state, mark):
            return "TARGET"
        if no_progress(state, LEGACY_NO_PROG_BARS, LEGACY_NO_PROG_MFE):
            return "CANCEL_NO_PROGRESS"
        if book_near(state):
            return "CANCEL_BOOK_NEAR"
        give = state.entry.entry_price * (1.0 - LEGACY_GIVE_UP_FRAC)
        if mark <= give:
            return "CANCEL_ADVERSE"
        if stall(state, clock.now, chop=chop):
            return "CANCEL_STALL"
        if time_stop(state, clock.now, LEGACY_TIME_HARD_SEC):
            return "TIME"
        return ""

    return ExitPlanFn(PlanSpec("legacy_overlay", family="baseline"), _fn)


def plan_atr_stop(k: float = 1.5) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        atr = ctx.get("atr")
        mark = ctx["mark"]
        if state.stop_premium is None and atr:
            state.stop_premium = state.entry.entry_price - float(k) * float(atr) * (
                state.entry.entry_price / max(state.entry.index_at_entry or 1.0, 1.0)
            )
        return flatten_eod(clock.now, V2_FLAT) or hard_stop(state, mark)

    return ExitPlanFn(PlanSpec("atr_stop", {"k": k}, "stop"), _fn)


def plan_noise_band(mult: float = 1.6, target_frac: float = 0.45) -> ExitPlanFn:
    """Stop outside the measured time-of-day MAE band (own idea 1)."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        band = float(ctx.get("tod_mae") or 8.0)
        if state.stop_premium is None:
            state.stop_premium = state.entry.entry_price - mult * band
            state.target_premium = state.entry.entry_price + target_frac * state.entry.entry_price
        mark = ctx["mark"]
        return flatten_eod(clock.now, V2_FLAT) or hard_stop(state, mark) or target_hit(state, mark)

    return ExitPlanFn(
        PlanSpec("noise_band", {"mult": mult, "target_frac": target_frac}, "own"), _fn
    )


def plan_theta_budget(min_age_s: float = 20 * 60, flat_pts: float = 12.0) -> ExitPlanFn:
    """Own idea 2: premium decaying while index is flat."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        idx0 = state.entry.index_at_entry
        idx = ctx.get("index")
        move = 0.0 if idx0 is None or idx is None else float(idx) - float(idx0)
        bleed = mark - state.entry.entry_price
        return flatten_eod(clock.now, V2_FLAT) or theta_bleed(
            state,
            index_move_pts=move,
            premium_change=bleed,
            flat_index_pts=flat_pts,
            min_age_s=min_age_s,
            now=clock.now,
        )

    return ExitPlanFn(
        PlanSpec("theta_budget", {"min_age_s": min_age_s, "flat_pts": flat_pts}, "own"), _fn
    )


def plan_regime_router() -> ExitPlanFn:
    """Own idea 3: pick the live-known regime plan at entry, freeze it."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        regime = str(state.entry.extra.get("regime_at_entry") or ctx.get("regime") or "mixed")
        if regime.startswith("trend"):
            return plan_mfe_trail(0.40, 6.0).decide(state, clock, ctx)
        if "expiry" in regime:
            return plan_fixed_stop_target(0.18, 0.28).decide(state, clock, ctx)
        if regime == "chop":
            return plan_time_and_stop(18 * 60, 0.16).decide(state, clock, ctx)
        return plan_noise_band(1.4, 0.35).decide(state, clock, ctx)

    return ExitPlanFn(PlanSpec("regime_router", family="own"), _fn)


def plan_mfe_trail(give_frac: float = 0.35, activate: float = 8.0) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        if state.stop_premium is None:
            state.stop_premium = state.entry.entry_price * 0.80
        return (
            flatten_eod(clock.now, V2_FLAT)
            or hard_stop(state, mark)
            or mfe_giveback(state, mark, give_frac, activate)
        )

    return ExitPlanFn(
        PlanSpec("mfe_trail", {"give_frac": give_frac, "activate": activate}, "trail"), _fn
    )


def plan_time_and_stop(after_s: float, stop_frac: float) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        if state.stop_premium is None:
            _init_stop_target(state, stop_frac, 0.50)
        mark = ctx["mark"]
        return (
            flatten_eod(clock.now, V2_FLAT)
            or hard_stop(state, mark)
            or target_hit(state, mark)
            or time_stop(state, clock.now, after_s, unless_profit=6.0)
        )

    return ExitPlanFn(
        PlanSpec("time_and_stop", {"after_s": after_s, "stop_frac": stop_frac}, "time"), _fn
    )


def plan_scale_out(first_frac: float = 0.50, first_r: float = 1.0) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        if state.stop_premium is None:
            _init_stop_target(state, 0.22, 0.55)
        mark = ctx["mark"]
        risk = state.entry.entry_price - (state.stop_premium or 0)
        if (
            state.partials_done == 0
            and risk > 0
            and mark >= state.entry.entry_price + first_r * risk
        ):
            return "PARTIAL"
        if state.partials_done and state.trail_stop is None:
            state.trail_stop = state.entry.entry_price  # breakeven after first scale
        return flatten_eod(clock.now, V2_FLAT) or hard_stop(state, mark) or target_hit(state, mark)

    return ExitPlanFn(
        PlanSpec("scale_out", {"first_frac": first_frac, "first_r": first_r}, "scale"), _fn
    )


def plan_breakeven_move(activate_frac: float = 0.20) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        if state.stop_premium is None:
            _init_stop_target(state, 0.22, 0.45)
        mark = ctx["mark"]
        run = state.mfe - state.entry.entry_price
        span = (state.target_premium or 0) - state.entry.entry_price
        if span > 0 and run >= activate_frac * span:
            state.trail_stop = max(state.trail_stop or 0, state.entry.entry_price)
        return flatten_eod(clock.now, V2_FLAT) or hard_stop(state, mark) or target_hit(state, mark)

    return ExitPlanFn(PlanSpec("breakeven_move", {"activate_frac": activate_frac}, "trail"), _fn)


def plan_iv_crush(drop_frac: float = 0.20) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        if state.stop_premium is None:
            _init_stop_target(state, 0.25, 0.40)
        return (
            flatten_eod(clock.now, V2_FLAT)
            or vol_crush(state, ctx.get("iv"), drop_frac)
            or hard_stop(state, mark)
            or target_hit(state, mark)
        )

    return ExitPlanFn(PlanSpec("iv_crush", {"drop_frac": drop_frac}, "vol"), _fn)


def plan_stale_and_flat(max_age_s: float = 90.0) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        if state.stop_premium is None:
            _init_stop_target(state, 0.30, 0.40)
        return (
            flatten_eod(clock.now, V2_FLAT)
            or stale_feed(state, clock.now, max_age_s)
            or freeze_window(clock.now)
            or hard_stop(state, mark)
        )

    return ExitPlanFn(PlanSpec("stale_and_flat", {"max_age_s": max_age_s}, "ops"), _fn)


def plan_asymmetric_ce_pe() -> ExitPlanFn:
    """Own extra: PE trails tighter in the morning; CE wider on trend days."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        hour = as_ist(clock.now).hour
        if state.entry.side == "PE" and hour < 12:
            return plan_mfe_trail(0.25, 5.0).decide(state, clock, ctx)
        if state.entry.side == "CE" and str(ctx.get("regime") or "").startswith("trend"):
            return plan_mfe_trail(0.50, 10.0).decide(state, clock, ctx)
        return plan_fixed_stop_target(0.22, 0.40).decide(state, clock, ctx)

    return ExitPlanFn(PlanSpec("asymmetric_ce_pe", family="own"), _fn)


def library() -> dict[str, ExitPlanFn]:
    plans = [
        plan_hold_to_1515(),
        plan_fixed_stop_target(),
        plan_v2_default(),
        plan_legacy_overlay(),
        plan_atr_stop(),
        plan_noise_band(),
        plan_theta_budget(),
        plan_regime_router(),
        plan_mfe_trail(),
        plan_time_and_stop(25 * 60, 0.20),
        plan_scale_out(),
        plan_breakeven_move(),
        plan_iv_crush(),
        plan_stale_and_flat(),
        plan_asymmetric_ce_pe(),
    ]
    return {p.plan_id: p for p in plans}


def sweep_specs() -> list[PlanSpec]:
    """Parameter variants. Count is reported for multiple-testing correction."""
    specs: list[PlanSpec] = []
    for stop in (0.15, 0.20, 0.25, 0.30, 0.40):
        for tgt in (0.25, 0.35, 0.45, 0.55):
            specs.append(
                PlanSpec(
                    f"fixed_{stop:.2f}_{tgt:.2f}", {"stop_frac": stop, "target_frac": tgt}, "sweep"
                )
            )
    for give in (0.25, 0.35, 0.50):
        for act in (4.0, 8.0, 12.0):
            specs.append(
                PlanSpec(
                    f"trail_{give:.2f}_{act:.0f}", {"give_frac": give, "activate": act}, "sweep"
                )
            )
    for sec in (12 * 60, 20 * 60, 30 * 60, 45 * 60):
        specs.append(PlanSpec(f"time_{sec}", {"after_s": sec, "stop_frac": 0.22}, "sweep"))
    for mult in (1.2, 1.6, 2.2):
        specs.append(PlanSpec(f"noise_{mult:.1f}", {"mult": mult, "target_frac": 0.40}, "sweep"))
    return specs


def build_plan(spec: PlanSpec) -> ExitPlanFn:
    fam = spec.family
    p = spec.params
    if spec.plan_id == "hold_to_1515" or spec.plan_id.startswith("hold"):
        return plan_hold_to_1515()
    if spec.plan_id == "legacy_overlay":
        return plan_legacy_overlay()
    if spec.plan_id == "v2_default":
        return plan_v2_default()
    if spec.plan_id == "regime_router":
        return plan_regime_router()
    if spec.plan_id == "asymmetric_ce_pe":
        return plan_asymmetric_ce_pe()
    if spec.plan_id.startswith("fixed") or (
        fam in {"baseline", "sweep"} and "stop_frac" in p and "target_frac" in p
    ):
        return plan_fixed_stop_target(
            float(p.get("stop_frac", 0.25)), float(p.get("target_frac", 0.40))
        )
    if spec.plan_id.startswith("trail") or "give_frac" in p:
        return plan_mfe_trail(float(p.get("give_frac", 0.35)), float(p.get("activate", 8.0)))
    if spec.plan_id.startswith("time") or "after_s" in p:
        return plan_time_and_stop(float(p.get("after_s", 1500)), float(p.get("stop_frac", 0.20)))
    if spec.plan_id.startswith("noise") or "mult" in p:
        return plan_noise_band(float(p.get("mult", 1.6)), float(p.get("target_frac", 0.40)))
    if spec.plan_id in library():
        return library()[spec.plan_id]
    return plan_fixed_stop_target()
