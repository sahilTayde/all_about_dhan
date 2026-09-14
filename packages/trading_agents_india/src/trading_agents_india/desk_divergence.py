"""Deterministic dealer: INDEX Δ vs ATM CE Δ vs ATM PE Δ.

No LLM. No orders. Does not rewrite MIX-DEFAULT-BUY or production params.
PREMIUM_DIVERGENCE → HOLD / no new paper CE/PE.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# Index points: ignore microstructure noise on NIFTY/BN/SENSEX.
INDEX_EPS = 1.0
# Premium rupees: ATM weeklies often print 0.05–0.25 ticks.
PREMIUM_EPS = 0.25


@dataclass(frozen=True)
class DivergenceNote:
    underlying: str
    verdict: str  # HOLD | BUY_CE_CONFIRM | BUY_PE_CONFIRM | DATA_INSUFFICIENT
    case: str  # PREMIUM_DIVERGENCE | CE_FOLLOWS | PE_FOLLOWS | FLAT | STALE | ...
    reason_code: str
    dealer_note: str
    allow_new_paper_ce_pe: bool
    index_delta: Optional[float]
    ce_delta: Optional[float]
    pe_delta: Optional[float]
    layer: str = "VALIDATION"
    execution: str = "refused"
    promote: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sign(delta: Optional[float], eps: float) -> Optional[int]:
    if delta is None:
        return None
    if abs(delta) <= eps:
        return 0
    return 1 if delta > 0 else -1


def judge_tick(
    *,
    underlying: str,
    index_delta: Optional[float],
    ce_delta: Optional[float],
    pe_delta: Optional[float],
    stale: bool = False,
    wrong_strike: bool = False,
    event_hold: bool = False,
    iv_shock_hint: bool = False,
    data_gaps: Optional[list[str]] = None,
) -> DivergenceNote:
    """Compare last-tick deltas. Missing numbers → DATA_INSUFFICIENT, not invented greeks."""
    gaps = list(data_gaps or [])
    extra = {"data_gaps": gaps}

    if wrong_strike:
        return DivergenceNote(
            underlying=underlying,
            verdict="HOLD",
            case="WRONG_STRIKE",
            reason_code="WRONG_STRIKE",
            dealer_note=(
                f"{underlying}: ATM strike missing or jumped vs last tick — "
                "do not open new paper CE/PE on a mismatched sheet."
            ),
            allow_new_paper_ce_pe=False,
            index_delta=index_delta,
            ce_delta=ce_delta,
            pe_delta=pe_delta,
            extra=extra,
        )
    if stale:
        return DivergenceNote(
            underlying=underlying,
            verdict="HOLD",
            case="STALE",
            reason_code="STALE",
            dealer_note=(
                f"{underlying}: tape looks stale (after-hours or frozen LTP). "
                "Hold; next session 09:15 IST is the real load."
            ),
            allow_new_paper_ce_pe=False,
            index_delta=index_delta,
            ce_delta=ce_delta,
            pe_delta=pe_delta,
            extra=extra,
        )
    if event_hold:
        return DivergenceNote(
            underlying=underlying,
            verdict="HOLD",
            case="EVENT_HOLD",
            reason_code="EVENT",
            dealer_note=(
                f"{underlying}: event / news overlay — hold the customer ticket. "
                "Not alpha. Not a catalog delete."
            ),
            allow_new_paper_ce_pe=False,
            index_delta=index_delta,
            ce_delta=ce_delta,
            pe_delta=pe_delta,
            extra=extra,
        )

    i = _sign(index_delta, INDEX_EPS)
    c = _sign(ce_delta, PREMIUM_EPS)
    p = _sign(pe_delta, PREMIUM_EPS)
    if i is None or c is None or p is None:
        return DivergenceNote(
            underlying=underlying,
            verdict="DATA_INSUFFICIENT",
            case="DATA_INSUFFICIENT",
            reason_code="DATA_INSUFFICIENT",
            dealer_note=(
                f"{underlying}: missing INDEX or ATM CE/PE print — cannot judge "
                "premium vs spot. No new paper CE/PE."
            ),
            allow_new_paper_ce_pe=False,
            index_delta=index_delta,
            ce_delta=ce_delta,
            pe_delta=pe_delta,
            extra=extra,
        )

    if i == 0 and c == 0 and p == 0:
        return DivergenceNote(
            underlying=underlying,
            verdict="HOLD",
            case="FLAT",
            reason_code="FLAT",
            dealer_note=f"{underlying}: index and ATM premiums flat vs last tick — no lean.",
            allow_new_paper_ce_pe=False,
            index_delta=index_delta,
            ce_delta=ce_delta,
            pe_delta=pe_delta,
            extra=extra,
        )

    # Index down: PE should rise, CE should fall. Either side failing = divergence.
    if i < 0:
        pe_ok = p > 0
        ce_ok = c < 0
        if not pe_ok or not ce_ok:
            iv_bit = " IV may be crushing the PE bid," if iv_shock_hint or (not pe_ok) else ""
            return DivergenceNote(
                underlying=underlying,
                verdict="HOLD",
                case="PREMIUM_DIVERGENCE",
                reason_code="IV" if (iv_shock_hint or not pe_ok) else "PREMIUM_DIVERGENCE",
                dealer_note=(
                    f"{underlying}: index down ({index_delta:+.2f}) but "
                    f"PE Δ={pe_delta} (want up) / CE Δ={ce_delta} (want down)."
                    f"{iv_bit} Dealer HOLD — no new paper CE/PE."
                ),
                allow_new_paper_ce_pe=False,
                index_delta=index_delta,
                ce_delta=ce_delta,
                pe_delta=pe_delta,
                extra=extra,
            )
        return DivergenceNote(
            underlying=underlying,
            verdict="BUY_PE_CONFIRM",
            case="PE_FOLLOWS",
            reason_code="PE_FOLLOWS",
            dealer_note=(
                f"{underlying}: index down and PE up / CE down — lean BUY_PE confirm "
                "(paper note only; MIX-DEFAULT-BUY unchanged)."
            ),
            allow_new_paper_ce_pe=True,
            index_delta=index_delta,
            ce_delta=ce_delta,
            pe_delta=pe_delta,
            extra=extra,
        )

    # Index up: CE should follow up.
    if i > 0:
        if c > 0:
            return DivergenceNote(
                underlying=underlying,
                verdict="BUY_CE_CONFIRM",
                case="CE_FOLLOWS",
                reason_code="CE_FOLLOWS",
                dealer_note=(
                    f"{underlying}: index up ({index_delta:+.2f}) and ATM CE followed "
                    f"({ce_delta:+.2f}) — lean BUY_CE confirm (paper note only)."
                ),
                allow_new_paper_ce_pe=True,
                index_delta=index_delta,
                ce_delta=ce_delta,
                pe_delta=pe_delta,
                extra=extra,
            )
        return DivergenceNote(
            underlying=underlying,
            verdict="HOLD",
            case="PREMIUM_DIVERGENCE",
            reason_code="IV" if iv_shock_hint else "PREMIUM_DIVERGENCE",
            dealer_note=(
                f"{underlying}: index up but ATM CE did not follow "
                f"(CE Δ={ce_delta}). Possible IV crush / wrong strike / stale quote. "
                "HOLD — no new paper CE."
            ),
            allow_new_paper_ce_pe=False,
            index_delta=index_delta,
            ce_delta=ce_delta,
            pe_delta=pe_delta,
            extra=extra,
        )

    # Index flat, premiums moving — do not chase.
    return DivergenceNote(
        underlying=underlying,
        verdict="HOLD",
        case="PREMIUM_DIVERGENCE",
        reason_code="PREMIUM_DIVERGENCE",
        dealer_note=(
            f"{underlying}: index flat but premiums moved (CE {ce_delta}, PE {pe_delta}) "
            "— treat as IV/event, not a new paper ticket."
        ),
        allow_new_paper_ce_pe=False,
        index_delta=index_delta,
        ce_delta=ce_delta,
        pe_delta=pe_delta,
        extra=extra,
    )
