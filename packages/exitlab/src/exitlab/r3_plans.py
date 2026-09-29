"""Exit rules mined from patterns plus the desk-lead extra ideas. Max 4 params."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from exitlab.clock import IST, ReplayClock, as_ist, in_feed_freeze
from exitlab.plans import (
    V2_FLAT,
    ExitPlanFn,
    PlanSpec,
    flatten_eod,
    hard_stop,
    plan_hold_to_1515,
    plan_v2_default,
    target_hit,
)
from exitlab.r3_core import clock_bucket
from exitlab.types import OpenState


def _age_min(state: OpenState, now: Any) -> float:
    return (as_ist(now) - as_ist(state.entry.ts)).total_seconds() / 60.0


def _feat(ctx: dict[str, Any]) -> dict[str, float | None]:
    raw = ctx.get("r3_feat")
    return raw if isinstance(raw, dict) else {}


def _f(feat: dict[str, float | None], name: str) -> float | None:
    v = feat.get(name)
    return None if v is None else float(v)


def plan_pattern(
    plan_id: str,
    checks: list[tuple[str, str, float]],
    *,
    trail_give: float = 0.0,
    partial: bool = False,
) -> ExitPlanFn:
    """Exit when all (feat, dir, thresh) hold. dir is 'le' or 'ge'. <=4 params in spec."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        feat = _feat(ctx)
        hit = True
        for name, direction, thr in checks:
            v = _f(feat, name)
            if v is None:
                hit = False
                break
            if direction == "le" and v > thr:
                hit = False
                break
            if direction == "ge" and v < thr:
                hit = False
                break
        can_partial = (
            hit
            and partial
            and state.partials_done < 1
            and state.remaining_qty >= 2 * state.entry.lot_size
        )
        if can_partial:
            return "PARTIAL"
        if hit and trail_give > 0:
            # ARM on the pattern; do not exit the same minute as the pair rule.
            armed = max(state.seen_high, mark) - trail_give
            state.trail_stop = max(state.trail_stop or 0.0, armed)
            return flatten_eod(clock.now, V2_FLAT) or hard_stop(state, mark)
        if hit:
            return "PATTERN"
        return flatten_eod(clock.now, V2_FLAT) or hard_stop(state, mark)

    params: dict[str, Any] = {f"c{i}": f"{n}:{d}:{t}" for i, (n, d, t) in enumerate(checks[:3])}
    if trail_give:
        params["trail"] = trail_give
    return ExitPlanFn(PlanSpec(plan_id, params, "r3_pattern"), _fn)


def plan_time_edge(n_min: float, x_pts: float) -> ExitPlanFn:
    """Exit if not up X pts by N minutes."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        if _age_min(state, clock.now) >= n_min and (mark - state.entry.entry_price) < x_pts:
            return "TIME_EDGE"
        return flatten_eod(clock.now, V2_FLAT)

    return ExitPlanFn(
        PlanSpec(f"time_edge_{n_min:.0f}_{x_pts:.2f}", {"n_min": n_min, "x_pts": x_pts}, "r3_time"),
        _fn,
    )


def plan_divergence(min_idx: float = 6.0, max_opt: float = 0.4) -> ExitPlanFn:
    """NIFTY still our way, option stopped rising (theta / IV)."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        feat = _feat(ctx)
        idx = _f(feat, "idx_5")
        mom = _f(feat, "mom_5")
        signed = float(ctx.get("index_signed") or 0.0)
        if idx is not None and mom is not None and abs(signed) >= min_idx:
            our_way = signed > 0
            if our_way and mom <= max_opt:
                return "DIVERGENCE"
        return flatten_eod(clock.now, V2_FLAT)

    return ExitPlanFn(
        PlanSpec("divergence", {"min_idx": min_idx, "max_opt": max_opt}, "r3_extra"), _fn
    )


def plan_other_side(turn: float = 0.8) -> ExitPlanFn:
    """Exit CE when same-strike PE stops falling and turns up (and reverse)."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        feat = _feat(ctx)
        opp = _f(feat, "opp_mom3")
        if opp is not None:
            if state.entry.side == "CE" and opp >= turn:
                return "OTHER_SIDE"
            if state.entry.side == "PE" and opp >= turn:
                return "OTHER_SIDE"
        return flatten_eod(clock.now, V2_FLAT)

    return ExitPlanFn(PlanSpec("other_side", {"turn": turn}, "r3_extra"), _fn)


def plan_theta_vs_move(n_min: float = 10.0, k: float = 1.0) -> ExitPlanFn:
    """Near expiry: expected N-min move < time decay + spread."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        feat = _feat(ctx)
        expiry = (_f(feat, "expiry") or 0) >= 0.5
        mins = _f(feat, "mins_to_1515")
        mom = _f(feat, "mom_10")
        spread = _f(feat, "spread") or 0.4
        if expiry and mins is not None and mins <= 90 and mom is not None:
            realized = abs(mom) / 10.0 * n_min
            decay = max(0.05, mark * 0.002 * n_min)  # crude theta proxy
            if realized < k * (decay + spread):
                return "THETA_GT_MOVE"
        return flatten_eod(clock.now, V2_FLAT)

    return ExitPlanFn(PlanSpec("theta_vs_move", {"n_min": n_min, "k": k}, "r3_extra"), _fn)


def plan_clock_window(bucket: str) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        expiry = bool(state.entry.extra.get("expiry_day") or "expiry" in state.entry.scenario)
        if clock_bucket(clock.now, expiry=expiry) == bucket:
            return "CLOCK_WINDOW"
        if bucket == "freeze_1515_1528" and in_feed_freeze(clock.now):
            return "CLOCK_WINDOW"
        stop = hard_stop(state, mark) if state.stop_premium else ""
        return flatten_eod(clock.now, V2_FLAT) or stop

    return ExitPlanFn(PlanSpec(f"clock_{bucket}", {"bucket": bucket}, "r3_clock"), _fn)


def plan_shape_exit(
    centers: list[list[float]], best_of: dict[int, str], need: int = 5
) -> ExitPlanFn:
    """Recognize 10-min shape by minute `need` using first `need` normalized returns."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        prints = [p for p in state.premium_prints if p]
        if len(prints) >= need and centers:
            p0 = prints[0] or 1.0
            row = [(prints[min(i, len(prints) - 1)] - p0) / (p0 or 1.0) for i in range(10)]
            # pad/truncate to center dim
            dim = len(centers[0])
            row = (row + [0.0] * dim)[:dim]
            best, bd = 0, 1e18
            for c, ctr in enumerate(centers):
                d = sum((row[j] - ctr[j]) ** 2 for j in range(dim))
                if d < bd:
                    best, bd = c, d
            action = best_of.get(best, "HOLD")
            if action == "EXIT_NOW":
                return "SHAPE"
            if action == "TRAIL":
                state.trail_stop = max(state.trail_stop or 0.0, state.seen_high - 1.5)
        return flatten_eod(clock.now, V2_FLAT) or hard_stop(state, mark)

    return ExitPlanFn(PlanSpec("shape_exit", {"need": need, "k": len(centers)}, "r3_shape"), _fn)


def plan_peak_model(
    kind: str, thresh: float, model: Any, names: list[str], *, tag: str = ""
) -> ExitPlanFn:
    def _row(feat: dict[str, float | None]) -> list[float | None]:
        return [feat.get(n) for n in names]

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        feat = _feat(ctx)
        row = _row(feat)
        from exitlab.r3_ml import predict_kind

        p = predict_kind(kind if kind != "hazard" else "logit", model, row)
        if p >= thresh:
            return "PEAK_MODEL"
        return flatten_eod(clock.now, V2_FLAT)

    pid = f"peak_{kind}_{tag}" if tag else f"peak_{kind}"
    return ExitPlanFn(PlanSpec(pid, {"thresh": thresh, "kind": kind}, "r3_model"), _fn)


def plan_clock_profit(t_before: float) -> ExitPlanFn:
    """Exit T minutes before 15:15 if in profit, else sit to 15:15."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        now = as_ist(clock.now)
        square = datetime.combine(now.date(), time(15, 15), tzinfo=IST)
        mins_left = (square - now).total_seconds() / 60.0
        if mins_left <= t_before and mark > state.entry.entry_price:
            return "CLOCK_PROFIT"
        return flatten_eod(clock.now, V2_FLAT)

    return ExitPlanFn(
        PlanSpec(f"clock_profit_{int(t_before)}", {"t_before": t_before}, "r3_clock"), _fn
    )


def plan_atr_stop(mult: float = 1.2) -> ExitPlanFn:
    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        prints = state.premium_prints[-12:]
        if len(prints) >= 4:
            n_p = len(prints) - 1
            atr = sum(abs(prints[i] - prints[i - 1]) for i in range(1, len(prints))) / n_p
            stop = state.entry.entry_price - mult * atr
            state.stop_premium = stop
            if mark <= stop:
                return "ATR_STOP"
        return flatten_eod(clock.now, V2_FLAT)

    return ExitPlanFn(PlanSpec(f"atr_opt_{mult:.1f}", {"mult": mult}, "r3_vol"), _fn)


def plan_ladder(steps: tuple[float, ...] = (0.4, 0.9)) -> ExitPlanFn:
    """Whole-lot scale-out at +steps * entry. 1-lot skips partials."""

    def _fn(state: OpenState, clock: ReplayClock, ctx: dict[str, Any]) -> str:
        mark = ctx["mark"]
        if state.entry.lots < 2:
            return flatten_eod(clock.now, V2_FLAT)
        gain = (mark - state.entry.entry_price) / max(state.entry.entry_price, 1e-9)
        need = steps[min(state.partials_done, len(steps) - 1)]
        if gain >= need and state.partials_done < len(steps):
            return "PARTIAL"
        if state.partials_done >= len(steps):
            state.trail_stop = max(state.trail_stop or 0.0, state.seen_high - 1.0)
        return flatten_eod(clock.now, V2_FLAT) or hard_stop(state, mark) or target_hit(state, mark)

    return ExitPlanFn(PlanSpec("ladder_2step", {"s0": steps[0], "s1": steps[-1]}, "r3_vol"), _fn)


def baselines() -> dict[str, ExitPlanFn]:
    return {
        "hold_to_1515": plan_hold_to_1515(),
        "v2_default": plan_v2_default(),
    }
