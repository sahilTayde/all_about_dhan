"""The paper engine's analyst room (`desk_ml.picker.collect_analyst_votes`) as registered analysts.

Logic is not copied: each analyst reads its own vote from the room's output for the context.
Conversion to and from `desk_ml.picker.Vote` is lossless so the picker sees exactly what it saw.
"""

from __future__ import annotations

from typing import Any

from analysts.base import ABSTAIN, BUY_CE, BUY_PE, HOLD, SIDE_OF, Analyst, MarketContext, Vote
from analysts.registry import register

STRAT_IDS = tuple(f"STRAT-{i:03d}" for i in range(1, 15))
# ML-001, ML-002 and ML-1 are retired from the vote room. On main they were always
# silent (no CE/PE), so dropping them does not change picker_majority.
LEGACY_SOURCES = ("follows", "logit", "xr", "greeks", "MIX-TV-EP-024", *STRAT_IDS)


def from_legacy(v: Any) -> Vote:
    if v.spoken():
        signal, confidence = (BUY_CE if v.side == "CE" else BUY_PE), 1.0
    else:
        signal, confidence = (HOLD if v.detail == "HOLD" else ABSTAIN), 0.0
    meta = {"legacy": True, "reason_class": v.reason_class, "silent": v.silent, "side": v.side}
    return Vote(str(v.source), signal, confidence, str(v.detail), meta)


def to_legacy(vote: Vote) -> Any:
    from desk_ml.picker import Vote as PickerVote

    meta = vote.metadata or {}
    if meta.get("legacy"):
        return PickerVote(
            source=vote.analyst_id, side=meta.get("side"), reason_class=str(meta["reason_class"]),
            silent=bool(meta["silent"]), detail=vote.reasoning,
        )
    side = SIDE_OF.get(vote.signal)
    return PickerVote(
        source=vote.analyst_id, side=side, reason_class=str(meta.get("reason_class") or ("CONFIRM" if side else vote.signal)),
        silent=side is None, detail=vote.reasoning,
    )


class LegacyRoomAnalyst(Analyst):
    def __init__(self, source: str) -> None:
        self.analyst_id = source

    def vote(self, context: MarketContext) -> Vote:
        for v in context.legacy_votes():
            if v.source == self.analyst_id:
                return from_legacy(v)
        return Vote.abstain(self.analyst_id, "NOT_IN_ROOM")


for _source in LEGACY_SOURCES:
    register(_source, lambda s=_source: LegacyRoomAnalyst(s))
