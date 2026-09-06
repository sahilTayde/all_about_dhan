"""Signal outcomes on top of WATCH → EARLY → CONFIRMED → IN-PROGRESS.

A customer back from lunch must not see a stale CONFIRMED as still valid
after target, SL, reversal, or time expiry. While a ticket is live after
CONFIRMED, the stage is IN-PROGRESS, then ACHIEVED / STOPPED / INVALIDATED.

Shadow paper = learning ledger. Never live orders.
"""

from __future__ import annotations

from typing import Any, Optional

from desk_intel.schema import (
    ACTIVE_STAGES,
    TERMINAL_OUTCOMES,
    LifecycleRecord,
    MarketSignal,
    ShadowPaper,
    SignalOutcome,
    SignalStage,
    UserFill,
)
from desk_intel.time_ist import now_ist_iso

OUTCOME_HELP = {
    "ACHIEVED": "Target hit (paper or reported).",
    "STOPPED": "Stop-loss hit.",
    "INVALIDATED": "Structure / reversal — signal withdrawn. Not still valid.",
    "EXPIRED": "Time window closed (session clock / lead spent).",
    "LOST": "Adverse vs entry without a clean SL print.",
    "COMPLETED": "User booked (took the trade and closed).",
    "SHADOW_CLOSED": "User skipped; platform shadow-papered to target/SL/invalidation.",
}


def still_valid(stage: SignalStage, outcome: Optional[SignalOutcome]) -> bool:
    if outcome in TERMINAL_OUTCOMES:
        return False
    return stage in ACTIVE_STAGES


def promote_live_stage(
    stage: SignalStage,
    *,
    outcome: Optional[SignalOutcome],
    user_took: bool,
    shadow_active: bool,
) -> SignalStage:
    """CONFIRMED + live ticket/shadow → IN-PROGRESS. Terminal outcomes stay terminal."""
    if outcome is not None:
        return stage
    if stage == "CONFIRMED" and (user_took or shadow_active):
        return "IN_PROGRESS"
    return stage


def initial_stage(signal: MarketSignal) -> SignalStage:
    """Fusion has no 5m Supertrend/MACD yet — directional lean is EARLY at most."""
    blocking = any(
        v.startswith(("event_window", "news_regime", "opening_drive", "tape_vs_headline"))
        for v in (signal.vetoes or [])
    )
    if signal.lean == "NO_TRADE" or blocking:
        return "VETOED"
    if signal.lean in ("BUY_CE", "BUY_PE"):
        return "EARLY"
    return "WATCH"


def _premium_path(entry: Optional[float], stop: Optional[float], target: Optional[float]) -> bool:
    return entry is not None and stop is not None and target is not None and target > entry > stop


def resolve_outcome(
    *,
    stage: SignalStage,
    lean: str,
    entry: Optional[float],
    stop: Optional[float],
    target: Optional[float],
    mark: Optional[float],
    invalidated: bool,
    session_expired: bool,
    user_took: bool,
    user_booked: bool = False,
    user_reported_pnl: Optional[float] = None,
) -> tuple[Optional[SignalOutcome], list[str]]:
    """Priority: withdrawn → booked → target → SL → time → adverse.

    Marks are paper/fixture. Does not place orders.
    """
    reasons: list[str] = []
    if invalidated:
        return "INVALIDATED", ["structure/reversal — signal withdrawn"]
    if user_booked:
        return "COMPLETED", ["user booked"]
    if mark is not None and _premium_path(entry, stop, target):
        assert entry is not None and stop is not None and target is not None
        if mark >= target:
            return "ACHIEVED", ["premium mark >= target"]
        if mark <= stop:
            return "STOPPED", ["premium mark <= stop"]
    if session_expired:
        reasons.append("session clock / flatten — VERIFY 15:30 vs 15:40")
        if user_took and user_reported_pnl is not None and user_reported_pnl < 0:
            return "LOST", reasons + ["user reported adverse P/L at session end"]
        return "EXPIRED", reasons
    if user_took and user_reported_pnl is not None and user_reported_pnl < 0:
        return "LOST", ["user reported adverse P/L vs entry"]
    if mark is not None and entry is not None and session_expired is False:
        if user_took and user_reported_pnl is None and mark < entry:
            # Intraday adverse without SL — not terminal yet.
            return None, ["adverse vs entry but SL not tagged — still open"]
    if stage in ACTIVE_STAGES:
        return None, ["still open — no terminal event yet"]
    return "EXPIRED", ["non-active stage without a richer outcome"]


def shadow_pnl(entry: Optional[float], mark: Optional[float]) -> Optional[float]:
    if entry is None or mark is None:
        return None
    return round(mark - entry, 4)


def close_shadow(
    outcome: SignalOutcome,
    entry: Optional[float],
    stop: Optional[float],
    target: Optional[float],
    mark: Optional[float],
) -> ShadowPaper:
    last = mark
    if outcome == "ACHIEVED" and target is not None:
        last = target
    elif outcome == "STOPPED" and stop is not None:
        last = stop
    closed: SignalOutcome = "SHADOW_CLOSED" if outcome == "COMPLETED" else outcome
    return ShadowPaper(
        active=False,
        entry=entry,
        stop=stop,
        target=target,
        last_mark=last,
        pnl_pts=shadow_pnl(entry, last),
        closed_as=closed,
        note="Shadow paper ledger only. Execution refused.",
    )


def apply_to_signal(signal: MarketSignal, record: LifecycleRecord) -> MarketSignal:
    signal.stage = record.stage
    signal.outcome = record.outcome
    signal.still_valid = record.still_valid
    return signal


def _stage_after_outcome(stage: SignalStage, outcome: Optional[SignalOutcome]) -> SignalStage:
    if outcome == "INVALIDATED":
        return "VETOED"
    if outcome == "EXPIRED":
        return "EXPIRED"
    return stage


def build_record(
    signal: MarketSignal,
    *,
    user: Optional[UserFill] = None,
    entry: Optional[float] = None,
    stop: Optional[float] = None,
    target: Optional[float] = None,
    mark: Optional[float] = None,
    invalidated: bool = False,
    session_expired: bool = False,
    user_booked: bool = False,
    lagging_late: Optional[list[str]] = None,
) -> LifecycleRecord:
    paper = signal.paper_signal or {}
    entry = entry if entry is not None else paper.get("entry")
    stop = stop if stop is not None else paper.get("stop")
    target = target if target is not None else paper.get("target")
    user = user or UserFill(took_trade=False)
    stage = signal.stage or initial_stage(signal)
    outcome, reasons = resolve_outcome(
        stage=stage,
        lean=signal.lean,
        entry=entry,
        stop=stop,
        target=target,
        mark=mark,
        invalidated=invalidated,
        session_expired=session_expired,
        user_took=user.took_trade,
        user_booked=user_booked,
        user_reported_pnl=user.reported_pnl,
    )
    if outcome is None and session_expired:
        outcome = "EXPIRED"
        reasons.append("forced EXPIRED at post-market — never leave still valid overnight")

    display_outcome = outcome
    if not user.took_trade and outcome is not None:
        reasons.append("user skipped — shadow paper closed for learning")
        shadow = close_shadow(outcome, entry, stop, target, mark)
        if outcome not in ("ACHIEVED", "STOPPED", "INVALIDATED", "EXPIRED", "LOST"):
            display_outcome = "SHADOW_CLOSED"
    elif not user.took_trade:
        shadow = ShadowPaper(
            active=True,
            entry=entry,
            stop=stop,
            target=target,
            last_mark=mark,
            pnl_pts=shadow_pnl(entry, mark),
        )
    else:
        shadow = ShadowPaper(
            active=False,
            entry=entry,
            stop=stop,
            target=target,
            last_mark=mark,
            pnl_pts=user.reported_pnl if user.reported_pnl is not None else shadow_pnl(entry, mark),
            closed_as=outcome,
            note="User took the trade — lots/spot/reported P/L on user fill. Not a live order.",
        )

    stage = _stage_after_outcome(stage, display_outcome)
    if display_outcome is None:
        next_stage = promote_live_stage(
            stage,
            outcome=display_outcome,
            user_took=user.took_trade,
            shadow_active=shadow.active,
        )
        if next_stage != stage:
            reasons.append(
                "IN-PROGRESS — trade or shadow is live after CONFIRMED; "
                "not a terminal outcome"
            )
            stage = next_stage
    valid = still_valid(stage, display_outcome)
    return LifecycleRecord(
        signal_id=signal.id,
        underlying=signal.underlying,
        lean=signal.lean,
        stage=stage,
        outcome=display_outcome,
        still_valid=valid,
        user=user,
        shadow=shadow,
        reasons=reasons,
        lagging_late=list(lagging_late or []),
        as_of_ist=now_ist_iso(),
    )


def records_from_payloads(
    signals: list[MarketSignal],
    *,
    users: dict[str, UserFill],
    marks: dict[str, float],
    session_expired: bool,
    invalidated_ids: Optional[set[str]] = None,
) -> list[LifecycleRecord]:
    invalidated_ids = invalidated_ids or set()
    out: list[LifecycleRecord] = []
    for signal in signals:
        paper = signal.paper_signal or {}
        rec = build_record(
            signal,
            user=users.get(signal.id) or users.get(signal.underlying),
            entry=paper.get("entry"),
            stop=paper.get("stop"),
            target=paper.get("target"),
            mark=marks.get(signal.underlying) or marks.get(signal.id),
            invalidated=signal.id in invalidated_ids,
            session_expired=session_expired,
            lagging_late=_lagging_guess(signal),
        )
        apply_to_signal(signal, rec)
        out.append(rec)
    return out


def _lagging_guess(signal: MarketSignal) -> list[str]:
    """UNVALIDATED hints for PhD — not measured lateness."""
    blob = " ".join(signal.reasons + signal.vetoes).lower()
    late: list[str] = []
    if "supertrend" in blob or signal.stage == "CONFIRMED":
        late.append("Supertrend (5m) — confirmation/kill only; UNVALIDATED if it printed after impulse")
    if "macd" in blob:
        late.append("MACD (5m) — confirmation/kill only; UNVALIDATED if cross after the move")
    if not late and signal.lean in ("BUY_CE", "BUY_PE"):
        late.append(
            "Lagging stack not on this MARKET_SIGNAL — fusion is news+chain. "
            "Review Supertrend/MACD only after OHLC VALIDATION (packages/indicators empty)."
        )
    return late


def outcome_counts(records: list[LifecycleRecord]) -> dict[str, Any]:
    counts = {key: 0 for key in sorted(TERMINAL_OUTCOMES)}
    counts["OPEN"] = 0
    taken = 0
    skipped = 0
    still = 0
    shadow_pnl_sum = 0.0
    user_pnl_sum = 0.0
    in_profit_open = 0
    for rec in records:
        if rec.user.took_trade:
            taken += 1
            if rec.user.reported_pnl is not None:
                user_pnl_sum += rec.user.reported_pnl
        else:
            skipped += 1
        if rec.shadow.pnl_pts is not None:
            shadow_pnl_sum += rec.shadow.pnl_pts
        if rec.still_valid:
            still += 1
            counts["OPEN"] += 1
            if rec.shadow.pnl_pts is not None and rec.shadow.pnl_pts > 0:
                in_profit_open += 1
        elif rec.outcome:
            counts[rec.outcome] = counts.get(rec.outcome, 0) + 1
    return {
        "by_outcome": counts,
        "user_taken": taken,
        "user_skipped": skipped,
        "still_valid": still,
        "hit_target": counts.get("ACHIEVED", 0),
        "missed_sl": counts.get("STOPPED", 0),
        "in_profit_open": in_profit_open,
        "invalidated": counts.get("INVALIDATED", 0),
        "shadow_pnl_pts_sum": round(shadow_pnl_sum, 4),
        "user_pnl_pts_sum": round(user_pnl_sum, 4),
    }
