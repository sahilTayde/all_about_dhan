"""Hypothesis option round-trip haircut. Not NSE/Dhan circular rates.

02 forbids inventing brokerage / STT / half-spread then ranking as CANDIDATE.
This overlay is a named HYPOTHESIS sensitivity — statutory stays UNKNOWN.
Do not retune mixes after applying it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from backtest_engine.simulate import Trade

# 1% of premium each side is a conservative slippage band, not a tick table.
# Statutory (STT / brokerage / GST) is not in repo circulars — leave 0 and label UNKNOWN.
HYPOTHESIS_OPTION_RT_1PCT = "HYPOTHESIS_OPTION_RT_1PCT"


@dataclass(frozen=True)
class CostModel:
    name: str = HYPOTHESIS_OPTION_RT_1PCT
    layer: str = "HYPOTHESIS"
    slippage_frac_each_way: float = 0.01
    statutory_frac_round_trip: float = 0.0
    statutory_status: str = "UNKNOWN"
    note: str = (
        "Round-trip haircut = slip_in + slip_out on premium. "
        "Not a Dhan REST field. Not an NSE circular. Cannot CANDIDATE."
    )

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "layer": self.layer,
            "slippage_frac_each_way": self.slippage_frac_each_way,
            "statutory_frac_round_trip": self.statutory_frac_round_trip,
            "statutory_status": self.statutory_status,
            "note": self.note,
        }


DEFAULT_COST = CostModel()


def round_trip_cost_pts(trade: Trade, model: CostModel = DEFAULT_COST) -> float:
    slip = model.slippage_frac_each_way * (trade.entry_px + trade.exit_px)
    mid = 0.5 * (trade.entry_px + trade.exit_px)
    statutory = model.statutory_frac_round_trip * mid
    return slip + statutory


def apply_round_trip(trade: Trade, model: CostModel = DEFAULT_COST) -> Trade:
    cost = round_trip_cost_pts(trade, model)
    return replace(trade, points=trade.points - cost)


def apply_round_trip_many(
    trades: list[Trade], model: CostModel = DEFAULT_COST
) -> list[Trade]:
    return [apply_round_trip(t, model) for t in trades]
