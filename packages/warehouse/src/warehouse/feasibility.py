"""DEALER-001 — deterministic long-premium feasibility. No LLM. No fills."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# Engineering TTL (seconds) by stage. Not a measured SLA. HYPOTHESIS.
STAGE_TTL_SEC = {
    "WATCH": 1800,
    "EARLY": 600,
    "CONFIRMED": 180,
    "IN_PROGRESS": 120,
    "IN-PROGRESS": 120,
}

REASON_CODES = (
    "OK",
    "TARGET_FEASIBILITY_FAIL",
    "STOP_FEASIBILITY_FAIL",
    "STALE_TAPE",
    "DATA_INSUFFICIENT",
    "COUNSEL_SPLIT",
    "OI_REVERSAL_REVIEW",
    "PARTIAL_BOOK_REVIEW",
    "EXIT_REVIEW",
    "NEWS_HOLD",
    "CHAIN_DATA_INSUFFICIENT",
)

# Founder lesson: 150 / 96 / 250 is a fantasy R vs same-session premium path.
DEFAULT_MAX_R = 3.0


@dataclass
class FeasibilityDecision:
    ok: bool
    action: str  # HOLD | PUBLISH | KILL
    reason_code: str
    new_state: str
    data_gaps: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_long_premium(
    *,
    entry: Optional[float],
    stop: Optional[float],
    target: Optional[float],
    stage: str = "WATCH",
    tape_age_sec: Optional[float] = None,
    typical_premium_range: Optional[float] = None,
    kill_requested: bool = False,
    news_hold: bool = False,
    chain_fresh: Optional[bool] = None,
) -> FeasibilityDecision:
    """Long CE/PE ticket: target > entry > stop. Kill/expire beats new entry."""
    stage_u = (stage or "WATCH").strip().upper().replace("-", "_")
    if stage_u == "IN_PROGRESS":
        stage_key = "IN_PROGRESS"
    else:
        stage_key = stage_u

    if kill_requested:
        return FeasibilityDecision(
            ok=False,
            action="KILL",
            reason_code="EXIT_REVIEW",
            new_state="DEALER_KILLED",
            note="exit/kill/expire has priority over new entry",
        )
    if news_hold:
        return FeasibilityDecision(
            ok=False,
            action="HOLD",
            reason_code="NEWS_HOLD",
            new_state="VETOED",
            note="cited event — hold the customer ticket",
        )
    if chain_fresh is False:
        return FeasibilityDecision(
            ok=False,
            action="HOLD",
            reason_code="CHAIN_DATA_INSUFFICIENT",
            new_state="WATCH",
            data_gaps=["3m chain not fresh"],
        )

    ttl = STAGE_TTL_SEC.get(stage_key, STAGE_TTL_SEC["WATCH"])
    if tape_age_sec is not None and tape_age_sec > ttl:
        return FeasibilityDecision(
            ok=False,
            action="KILL" if stage_key in {"CONFIRMED", "IN_PROGRESS"} else "HOLD",
            reason_code="STALE_TAPE",
            new_state="DEALER_KILLED" if stage_key in {"CONFIRMED", "IN_PROGRESS"} else "WATCH",
            note=f"tape age {tape_age_sec}s > TTL {ttl}s for {stage_key}",
        )

    gaps: list[str] = []
    if entry is None or stop is None or target is None:
        return FeasibilityDecision(
            ok=False,
            action="HOLD",
            reason_code="DATA_INSUFFICIENT",
            new_state="WATCH",
            data_gaps=["entry/stop/target missing"],
            note="do not invent levels",
        )

    if stop >= entry:
        return FeasibilityDecision(
            ok=False,
            action="KILL",
            reason_code="STOP_FEASIBILITY_FAIL",
            new_state="FEASIBILITY_REJECTED",
            note="stop must sit below entry for long premium",
        )
    if target <= entry:
        return FeasibilityDecision(
            ok=False,
            action="KILL",
            reason_code="TARGET_FEASIBILITY_FAIL",
            new_state="FEASIBILITY_REJECTED",
            note="target must sit above entry for long premium",
        )

    risk = entry - stop
    reward = target - entry
    if risk <= 0:
        return FeasibilityDecision(
            ok=False,
            action="KILL",
            reason_code="STOP_FEASIBILITY_FAIL",
            new_state="FEASIBILITY_REJECTED",
        )
    r_mult = reward / risk
    if typical_premium_range is None or typical_premium_range <= 0:
        return FeasibilityDecision(
            ok=False,
            action="HOLD",
            reason_code="DATA_INSUFFICIENT",
            new_state="WATCH",
            data_gaps=["typical_premium_range missing — HOLD not hero target"],
            note=f"R={r_mult:.2f} without a same-session premium path",
        )
    elif reward > typical_premium_range * DEFAULT_MAX_R:
        return FeasibilityDecision(
            ok=False,
            action="KILL",
            reason_code="TARGET_FEASIBILITY_FAIL",
            new_state="FEASIBILITY_REJECTED",
            note="target farther than 3x typical same-session premium range",
        )

    return FeasibilityDecision(
        ok=True,
        action="PUBLISH",
        reason_code="OK",
        new_state=stage_key if stage_key != "IN_PROGRESS" else "IN_PROGRESS",
        data_gaps=gaps,
    )
