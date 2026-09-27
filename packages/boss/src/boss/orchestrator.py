"""Boss (PR-007): asks analysts, runs the paper engine's decision rules, emits the entry decision.

On MARKET_TICK (after the desk's mark-to-market):
  1. analyst-room inputs for the tick (`paper_scalp.step_vote_inputs`)
  2. REQUEST_VOTES -> AnalystRoom -> one ANALYST_VOTE per analyst (timeout/crash = ABSTAIN)
  3. picker majority + observer + entry gates, unchanged (`paper_scalp.step_decide`)
  4. per ticket: ENTRY_APPROVED (sized ticket for the desk) or NO_ENTRY (the gate that skipped it)

The boss never calls the broker or the risk engine; the desk does.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict
from typing import Any, Optional, Sequence

from analysts import MarketContext, Vote
from analysts.legacy import to_legacy

log = logging.getLogger("boss")
LLM_KEY = "LLM-ANALYST"


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
        shadow_ids: Optional[Sequence[str]] = None,
        shadow_cfg: Optional[dict[str, Any]] = None,
    ) -> None:
        from desk_ml import paper_scalp as ps

        self._ps = ps
        self.bus = bus
        self.engine = engine
        self.steps = steps
        self.signals = signals
        self.contexts = contexts
        self.analyst_ids = list(analyst_ids)
        self.shadow_ids = set(shadow_ids or [])
        self.shadow_cfg = dict(shadow_cfg or {})
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
        self.contexts[rid] = MarketContext(
            underlying=s.und, ts=int(s.tick.ts), i=s.i, inputs=inputs, features=self._shadow_features(s),
        )
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

    def _shadow_features(self, step: Any) -> Optional[dict[str, Any]]:
        llm_on = LLM_KEY in self.analyst_ids  # PR-016: the LLM analyst reads the shadow pack + its own
        if not self.shadow_ids and not llm_on:
            return None
        try:
            from analysts.shadow import build_shadow_snapshot

            out = {"shadow": build_shadow_snapshot(self.engine, step, self.shadow_cfg)}
        except Exception:
            log.exception("shadow snapshot failed; shadow analysts abstain")
            out = {"shadow": {}}
        if llm_on:
            from analysts.llm import llm_snapshot

            out["llm"] = llm_snapshot(self.engine, step)
        return out

    def _ignored(self, vote: Vote) -> bool:
        return vote.analyst_id in self.shadow_ids or bool((vote.metadata or {}).get("shadow"))

    def legacy_votes(self, votes: Sequence[Vote], inputs: dict[str, Any]) -> list[Any]:
        """Votes in registry order as picker Votes; shadow analysts are not included."""
        by_id = {v.analyst_id: v for v in votes}
        out = [to_legacy(by_id[a]) for a in self.analyst_ids if a in by_id and not self._ignored(by_id[a])]
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
