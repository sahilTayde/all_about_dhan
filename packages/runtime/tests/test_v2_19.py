"""V2-19 acceptance: advisor cannot change, delay, or veto a decision."""

from __future__ import annotations

import json
import socket
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from contracts.clock import IST, SimClock
from contracts.envelope import Envelope
from contracts.validation import load_advice
from desk_ml.llm_analyst import Advisor, RecordedProvider, build_context, reset_advisors, scrub
from desk_ml.llm_analyst.providers import Provider, Reply
from events.bus import MemoryBus
from events.schema import EventType

from runtime.advisor import LlmAdvisorService, context_from_decision, make_replay_advisor
from runtime.kernel import Engine
from runtime.sources import EnvelopeSource
from runtime.store import InMemoryLedgerStore

TEN = datetime(2026, 9, 28, 10, 0, tzinfo=IST)
DECISION = {
    "decision_id": "dc_nifty_20260928_1000_1",
    "underlying": "NIFTY",
    "decision": "ENTER",
    "signal_ids": ["sg_a"],
    "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24400:CE",
    "lots": 5,
    "lot_size": 65,
    "holds": [],
    "shadow": {
        "regime": "TREND",
        "direction": "UP",
        "ranks": [{"strategy_id": "PAPER-A", "side": "CE", "weight": 1.0}],
    },
}


class _Fixed(Provider):
    offline = True

    def __init__(self, name: str, text: str, delay: float = 0.0) -> None:
        super().__init__()
        self.name, self.model, self.text, self.delay = name, name, text, delay

    def complete(self, system: str, user: str, *, context: Any, context_hash: str, timeout_s: float) -> Reply:
        if self.delay:
            time.sleep(self.delay)
        return Reply(text=self.text)


DISAGREE = '{"verdict":"disagree","confidence":0.9,"reasons":["event day"],"risk_flags":[]}'


def _cfg(tmp: Path, **over: Any) -> dict[str, Any]:
    return {
        "provider": "mock",
        "replay_provider": "mock",
        "model": "gpt-4o-mini",
        "weight": 0,
        "timeout_ms": 200,
        "max_calls_per_day": 200,
        "max_cost_usd_per_day": 1.0,
        "min_interval_s": 0.0,
        "max_tick_age_s": 180,
        "cache_size": 32,
        "reuse_window_s": 0,
        "max_output_tokens": 50,
        "price_usd_per_1m_tokens": {"input": 0.15, "output": 0.60},
        "log_path": str(tmp / "calls.jsonl"),
        "replay_log_path": str(tmp / "replay.jsonl"),
        "recorded_path": str(tmp / "recorded.jsonl"),
        "premarket_brief_path": None,
        **over,
    }


def _env(seq: int, payload: dict[str, Any]) -> Envelope:
    ts = TEN.isoformat()
    return Envelope(
        v=2,
        event_type="DECISION",
        event_id=f"evt_dec_{seq:03d}",
        stream="boss:decisions",
        source="boss",
        event_ts=ts,
        available_ts=ts,
        timestamp=ts,
        account_id=None,
        correlation_id=None,
        causation_id=None,
        payload=dict(payload),
    )


def _run(mode: str, tmp: Path) -> tuple[str, list[str], float, list[dict[str, Any]]]:
    reset_advisors()
    bus = MemoryBus()
    seen: list[dict[str, Any]] = []
    advice: list[dict[str, Any]] = []
    bus.subscribe(["DECISION"], lambda e: seen.append(dict(e.payload)), priority=10)
    bus.subscribe(["ADVICE"], lambda e: advice.append(dict(e.payload)), priority=10)
    svc: LlmAdvisorService | None = None
    if mode != "off":
        delay = 1.5 if mode == "hung" else 0.0
        adv = Advisor(_cfg(tmp / mode), replay=True, provider=_Fixed(mode, DISAGREE, delay))
        svc = LlmAdvisorService(bus, adv, SimClock(TEN))
        svc.start()
    t0 = time.perf_counter()
    summary = Engine(
        EnvelopeSource([_env(i, {**DECISION, "decision_id": f"dc_{i}"}) for i in range(5)]),
        SimClock(TEN),
        bus,
        [],
        InMemoryLedgerStore(),
    ).run()
    elapsed = time.perf_counter() - t0
    if svc is not None and mode == "on":
        svc.drain(timeout_s=1.0)
    if svc is not None:
        svc.stop()
    return summary.output_hash, [d["decision"] for d in seen], elapsed, advice


def test_v2_19_engine_decisions_and_timings_identical_advisor_on_off_or_hung(tmp_path: Path) -> None:
    off_h, off_d, off_t, off_a = _run("off", tmp_path)
    on_h, on_d, on_t, on_a = _run("on", tmp_path)
    hung_h, hung_d, hung_t, _ = _run("hung", tmp_path)
    assert off_h == on_h == hung_h
    assert off_d == on_d == hung_d == ["ENTER"] * 5
    assert off_t < 0.5 and on_t < 0.5 and hung_t < 0.5
    assert on_a and all(a["verdict"] == "disagree" for a in on_a) and not off_a
    load_advice(on_a[0])


def test_v2_19_no_provider_call_in_replay_or_ci_socket_guard(tmp_path: Path, monkeypatch: Any) -> None:
    def blocked(*_a: Any, **_k: Any) -> None:
        raise AssertionError("provider socket opened in replay/CI")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    (tmp_path / "recorded.jsonl").write_text("", encoding="utf-8")
    adv = make_replay_advisor(
        _cfg(tmp_path, provider="openai", replay_provider="recorded", recorded_path=str(tmp_path / "recorded.jsonl"))
    )
    assert adv.replay and adv.provider.offline and isinstance(adv.provider, RecordedProvider)
    bus, advice = MemoryBus(), []
    bus.subscribe(["ADVICE"], lambda e: advice.append(e.payload))
    svc = LlmAdvisorService(bus, adv, SimClock(TEN))
    svc.start()
    bus.publish(EventType.DECISION, dict(DECISION), source="boss")
    svc.drain(timeout_s=1.0)
    svc.stop()
    assert advice and advice[0]["verdict"] == "abstain" and advice[0]["provider"] == "recorded"


def test_v2_19_secrets_scrubbed_from_stored_context(tmp_path: Path, monkeypatch: Any) -> None:
    token = "hidden-token-value-zzzz"
    monkeypatch.setenv("OPENAI_API_KEY", token)
    raw = {"access_token": token, "account_id": "acct-hidden", "api_key": token, "spot": 24500.0}
    cleaned = scrub(raw)
    assert "access_token" not in cleaned and "account_id" not in cleaned
    assert cleaned["spot"] == 24500.0
    brief = {"premarket": {"regime_note": f"token {token}"}, "intermarket": {"USDINR": 83.0}}
    ctx = context_from_decision(DECISION, tick_ts=int(TEN.timestamp()), book=raw, brief=brief)
    assert token not in json.dumps(ctx) and "access_token" not in json.dumps(ctx)
    reused = build_context(
        underlying="NIFTY",
        tick_ts=int(TEN.timestamp()),
        signal={"side": "CE", "strike": 24400.0},
        book=raw,
        brief=brief,
    )
    assert token not in json.dumps(reused)
    cfg = _cfg(tmp_path)
    svc = LlmAdvisorService(MemoryBus(), Advisor(cfg, replay=True), SimClock(TEN))
    svc.advise(DECISION)
    log = Path(cfg["replay_log_path"])
    if log.is_file():
        assert token not in log.read_text(encoding="utf-8")
    svc.stop()
