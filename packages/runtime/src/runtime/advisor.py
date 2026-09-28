"""V2-19 llm-advisor: DECISION in, ADVICE out. Never on the engine hot path.

Subscribe callbacks only enqueue a copied payload. A hung provider cannot
change, delay, or veto a decision. Replay uses Advisor(replay=True).
"""

from __future__ import annotations

import copy
import json
import logging
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from queue import Empty, Full, Queue
from typing import Any

from contracts.clock import IST, Clock
from contracts.instruments import India
from desk_ml.llm_analyst import PROMPT_VERSION, Advisor, build_context, load_config
from events.bus import EventBus
from events.schema import Event, EventType

log = logging.getLogger("runtime.advisor")

STREAM_DECISIONS = "boss:decisions"
STREAM_ADVICE = "llm:advice"
VERDICTS = frozenset({"agree", "disagree", "abstain"})
_INDIA = India()


def context_from_decision(
    payload: Mapping[str, Any],
    *,
    tick_ts: int,
    ist_time: str | None = None,
    book: Mapping[str, Any] | None = None,
    brief: Any = None,
) -> dict[str, Any]:
    """Compact context. Scrub is inside build_context."""
    side: str | None = None
    strike: float | None = None
    inst = payload.get("instrument_id")
    if isinstance(inst, str) and inst:
        try:
            parsed = _INDIA.parse_instrument_id(inst)
            opt = parsed.get("option_type") or ""
            side = opt if opt in ("CE", "PE") else None
            raw = parsed.get("strike") or ""
            strike = float(raw) if raw else None
        except ValueError:
            side, strike = None, None
    shadow = payload.get("shadow") if isinstance(payload.get("shadow"), Mapping) else {}
    voters: dict[str, str] = {}
    ranks = shadow.get("ranks") if isinstance(shadow, Mapping) else None
    if isinstance(ranks, list):
        for row in ranks:
            if isinstance(row, Mapping) and row.get("side") in ("CE", "PE") and row.get("strategy_id"):
                voters[str(row["strategy_id"])] = str(row["side"])
        if side not in ("CE", "PE") and voters:
            side = next(iter(voters.values()))
    regime = None
    if isinstance(shadow, Mapping) and shadow.get("regime"):
        regime = {"regime": shadow.get("regime"), "direction": shadow.get("direction")}
    return build_context(
        underlying=str(payload.get("underlying") or "NIFTY"),
        tick_ts=tick_ts,
        ist_time=ist_time,
        signal={
            "side": side,
            "strike": strike,
            "confidence": 1.0 if payload.get("decision") == "ENTER" else 0.0,
            "voters": voters,
            "picker_detail": payload.get("decision"),
        },
        regime=regime,
        book=book,
        brief=brief,
    )


def _brief(path: Any) -> Any:
    p = Path(str(path)) if path else None
    if p is None or not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class LlmAdvisorService:
    """Queue-decoupled: engine publish returns after enqueue (or drop)."""

    STREAM_IN = STREAM_DECISIONS
    STREAM_OUT = STREAM_ADVICE

    def __init__(self, bus: EventBus, advisor: Advisor, clock: Clock, *, queue_size: int = 8) -> None:
        self.bus = bus
        self.advisor = advisor
        self.clock = clock
        self._queue: Queue[dict[str, Any]] = Queue(maxsize=queue_size)
        self._book: dict[str, dict[str, Any]] = {}
        self._stop = threading.Event()
        self._busy = False
        self._worker: threading.Thread | None = None
        self._subs: list[str] = []

    def start(self) -> None:
        self._subs.append(self.bus.subscribe(["DECISION"], self._enqueue_decision, priority=200))
        self._subs.append(self.bus.subscribe(["POSITION_UPDATE", "POSITION_CLOSED"], self._on_pos, priority=200))
        self._worker = threading.Thread(target=self._loop, name="llm-advisor", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()
        for sid in self._subs:
            self.bus.unsubscribe(sid)
        self._subs.clear()
        if self._worker is not None:
            self._worker.join(timeout=0.2)
        self.advisor.close()

    def drain(self, timeout_s: float = 1.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self._queue.empty() and not self._busy:
                return
            time.sleep(0.01)

    def _enqueue_decision(self, event: Event) -> None:
        try:
            self._queue.put_nowait({"payload": copy.deepcopy(event.payload)})
        except Full:
            log.warning("llm-advisor queue full; drop advice for %s", event.payload.get("decision_id"))

    def _on_pos(self, event: Event) -> None:
        pid = event.payload.get("position_id")
        if not isinstance(pid, str):
            return
        if event.event_type == EventType.POSITION_UPDATE.value:
            self._book[pid] = {"unrealized_inr": event.payload.get("unrealized_inr")}
        else:
            self._book.pop(pid, None)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.05)
            except Empty:
                continue
            self._busy = True
            try:
                self.advise(item["payload"])
            except Exception:
                log.exception("llm-advisor review failed")
            finally:
                self._busy = False

    def advise(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        now = self.clock.now()
        if now.tzinfo is None:
            raise ValueError("advisor clock must be IST-aware")
        ist = now.astimezone(IST)
        book = {
            "open_positions": len(self._book),
            "today_pnl_inr": round(sum(float(p.get("unrealized_inr") or 0.0) for p in self._book.values()), 2),
        }
        ctx = context_from_decision(
            payload,
            tick_ts=int(ist.timestamp()),
            ist_time=ist.strftime("%H:%M"),
            book=book,
            brief=_brief(self.advisor.cfg.get("premarket_brief_path")),
        )
        out = self.advisor.review(ctx)
        verdict = str(out.get("verdict") or "abstain")
        advice = {
            "decision_id": str(payload.get("decision_id") or ""),
            "verdict": verdict if verdict in VERDICTS else "abstain",
            "reasons": [str(r) for r in list(out.get("reasons") or [])],
            "provider": self.advisor.provider.name,
            "prompt_version": PROMPT_VERSION,
            "cost_usd": float(out.get("cost_usd") or 0.0),
            "context_hash": str(out.get("context_hash") or ""),
        }
        try:
            self.bus.publish(EventType.ADVICE, advice, source="llm-advisor")
        except Exception:
            log.exception("ADVICE publish failed")
        return advice


def make_replay_advisor(cfg: Mapping[str, Any] | None = None) -> Advisor:
    return Advisor(dict(cfg) if cfg is not None else load_config(), replay=True)
