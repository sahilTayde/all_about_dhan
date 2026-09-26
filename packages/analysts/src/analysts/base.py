"""Analyst interface: `vote(context) -> Vote(signal, confidence, reasoning)`. Analysts vote; the boss decides."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

BUY_CE, BUY_PE, HOLD, ABSTAIN = "BUY_CE", "BUY_PE", "HOLD", "ABSTAIN"
SIGNALS = (BUY_CE, BUY_PE, HOLD, ABSTAIN)
SIDE_OF = {BUY_CE: "CE", BUY_PE: "PE"}


@dataclass(frozen=True)
class Vote:
    analyst_id: str
    signal: str  # BUY_CE | BUY_PE | HOLD | ABSTAIN
    confidence: float  # 0..1
    reasoning: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.signal not in SIGNALS:
            raise ValueError(f"{self.analyst_id}: signal {self.signal!r} not in {SIGNALS}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(f"{self.analyst_id}: confidence {self.confidence} outside 0..1")

    @property
    def side(self) -> Optional[str]:
        return SIDE_OF.get(self.signal)

    @classmethod
    def abstain(cls, analyst_id: str, reasoning: str) -> "Vote":
        return cls(analyst_id, ABSTAIN, 0.0, reasoning, {"reason_class": ABSTAIN})

    def to_payload(self) -> dict[str, Any]:
        return {
            "analyst_id": self.analyst_id, "signal": self.signal, "confidence": float(self.confidence),
            "reasoning": self.reasoning, "metadata": dict(self.metadata),
        }

    @classmethod
    def from_payload(cls, p: dict[str, Any]) -> "Vote":
        return cls(p["analyst_id"], p["signal"], float(p["confidence"]), p["reasoning"], dict(p.get("metadata") or {}))


class MarketContext:
    """What analysts see for one REQUEST_VOTES. Built by the boss from the tick; read-only for analysts.

    `inputs` are the paper engine's analyst-room kwargs (`desk_ml.picker.collect_analyst_votes`).
    `features` is a free dict for new research features (name -> value), filled by whoever
    computes them before the vote; analysts must treat a missing feature as ABSTAIN.
    """

    def __init__(
        self, *, underlying: str, ts: int, i: int, inputs: dict[str, Any],
        features: Optional[dict[str, Any]] = None,
    ) -> None:
        self.underlying = underlying
        self.ts = ts
        self.i = i
        self.inputs = inputs
        self.features = features or {}
        self._legacy: Optional[list[Any]] = None
        self._lock = threading.Lock()

    def legacy_votes(self) -> list[Any]:
        """`collect_analyst_votes(**inputs)`, computed once per context (analysts run in threads)."""
        with self._lock:
            if self._legacy is None:
                from desk_ml.picker import collect_analyst_votes

                self._legacy = collect_analyst_votes(**self.inputs)
            return self._legacy


class Analyst(ABC):
    analyst_id: str = "base"

    @abstractmethod
    def vote(self, context: MarketContext) -> Vote: ...
