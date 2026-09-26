"""Boss (PR-007): asks analysts, runs the paper engine's decision rules, emits the entry decision.

On MARKET_TICK (after the desk's mark-to-market):
  1. analyst-room inputs for the tick (`paper_scalp.step_vote_inputs`)
  2. REQUEST_VOTES -> AnalystRoom -> one ANALYST_VOTE per analyst (timeout/crash = ABSTAIN)
  3. picker majority + observer + entry gates, unchanged (`paper_scalp.step_decide`)
  4. per ticket: ENTRY_APPROVED (sized ticket for the desk) or NO_ENTRY (the gate that skipped it)

The boss never calls the broker or the risk engine; the desk does.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict
from typing import Any, Optional, Sequence

from analysts import MarketContext, Vote
from analysts.legacy import to_legacy


class Boss:
    def __init__(
        self,
        bus: Any,
        engine: Any,
        *,
        steps: dict[str, Any],
        signals: dict[str, dict[str, Any]],
        contexts: dict[str, MarketContext],
        analyst_ids: Sequence[str],
    ) -> None:
        from desk_ml import paper_scalp as ps

        self._ps = ps
        self.bus = bus
        self.engine = engine
        self.steps = steps
        self.signals = signals
        self.contexts = contexts
        self.analyst_ids = list(analyst_ids)
        self._inbox: dict[str, list[Vote]] = {}
        self.latency_ms: dict[str, list[float]] = {"decision": []}
        self.subs = [
            bus.subscribe(["MARKET_TICK"], self.on_tick, priority=20),
            bus.subscribe(["ANALYST_VOTE"], self.on_vote, priority=10),
        ]

    def on_vote(self, event: Any) -> None:
        box = self._inbox.get(event.payload.get("request_id"))
        if box is not None:
            box.append(Vote.from_payload(event.payload))

    def on_tick(self, event: Any) -> None:
        key = event.payload["key"]
        s = self.steps[key]
        inputs = self._ps.step_vote_inputs(self.engine, s, **self.signals[key])
        t0 = time.perf_counter()
        rid = uuid.uuid4().hex
        self.contexts[rid] = MarketContext(underlying=s.und, ts=int(s.tick.ts), i=s.i, inputs=inputs)
        self._inbox[rid] = []
        try:
            self.bus.publish(
                "REQUEST_VOTES",
                {"request_id": rid, "underlying": s.und, "ts": int(s.tick.ts), "i": s.i, "analysts": self.analyst_ids},
                source="boss",
            )
            votes = self._inbox.get(rid) or []
        finally:
            self._inbox.pop(rid, None)
            self.contexts.pop(rid, None)
        self._ps.step_decide(self.engine, s, self.legacy_votes(votes, inputs), open_fn=self._plan_and_emit)
        self.latency_ms["decision"].append((time.perf_counter() - t0) * 1000.0)

    def legacy_votes(self, votes: Sequence[Vote], inputs: dict[str, Any]) -> list[Any]:
        """Votes in registry order as picker Votes; engine `extra` votes keep their legacy slot."""
        by_id = {v.analyst_id: v for v in votes}
        out = [to_legacy(by_id[a]) for a in self.analyst_ids if a in by_id]
        extra = [v for v in (inputs.get("extra") or [])
                 if not str(v.source).startswith("STRAT-") and v.source not in by_id]
        if extra:
            at = next((n for n, v in enumerate(out) if str(v.source).startswith("STRAT-")), len(out))
            out[at:at] = extra
        return out

    def _plan_and_emit(self, engine: Any, **kw: Any) -> None:
        n_skips = len(engine.skips)
        pos: Optional[Any] = self._ps._plan_open(engine, **kw)
        und, ts = kw["underlying"], int(kw["tick"].ts)
        if pos is None:
            reason = engine.skips[-1].get("reason") if len(engine.skips) > n_skips else "NO_TICKET"
            self.bus.publish(
                "NO_ENTRY",
                {"book_id": kw["book_id"], "underlying": und, "side": kw.get("side"), "ts": ts, "reason": reason},
                source="boss",
            )
            return
        self.bus.publish(
            "ENTRY_APPROVED",
            {
                "trade_id": pos.trade_id, "book_id": pos.book_id, "underlying": und, "side": pos.side,
                "strike": pos.atm_strike, "lots": pos.lots, "lot_size": pos.lot_size, "limit_price": pos.limit_price,
                "entry": pos.entry, "stop": pos.stop, "target": pos.target, "ts": ts,
                "reason": pos.justification, "analysts": list(pos.model_names), "ticket": asdict(pos),
            },
            source="boss",
        )
