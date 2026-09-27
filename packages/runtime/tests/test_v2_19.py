"""V2-19 llm-advisor: sidecar advice only. One test per acceptance bullet."""

from __future__ import annotations

import json
import socket
import time
import urllib.request
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from boss.selector import (  # type: ignore[import-untyped]
    BarContext,
    BossSelector,
    SessionBasketGate,
    load_engine_config,
)
from contracts.clock import IST, SimClock
from contracts.envelope import Envelope
from contracts.payloads import CatastrophicStop, ExitPlan, Level, StrikeChoice, StrikeQuote
from contracts.validation import load_advice
from desk_ml.llm_analyst import MockProvider, Provider, RecordedProvider, Reply, build_context, scrub
from desk_ml.llm_analyst.advisor import DEFAULTS, reset_advisors
from events.bus import MemoryBus
from strategies.api import Signal
from strategies.registry import Basket, BasketEntry

from runtime.kernel import Engine
from runtime.services import ADVICE_STREAM, DECISION_STREAM, LlmAdvisorService, run_llm_advisor
from runtime.sources import EnvelopeSource
from runtime.store import InMemoryLedgerStore

NOW = datetime(2026, 9, 28, 10, 5, tzinfo=IST)
ENGINE_YAML = Path("config/v2/engine.yaml")


def _cfg(tmp_path: Path, **over: object) -> dict[str, Any]:
    return {
        **DEFAULTS,
        "log_path": str(tmp_path / "calls.jsonl"),
        "recorded_path": str(tmp_path / "recorded.jsonl"),
        "replay_log_path": str(tmp_path / "replay.jsonl"),
        "min_interval_s": 0.0,
        "reuse_window_s": 0,
        **over,
    }


def _envelope(seq: int) -> Envelope:
    event_ts = NOW + timedelta(seconds=seq)
    available_ts = event_ts + timedelta(milliseconds=10)
    return Envelope(
        v=2,
        event_type="MARKET_TICK",
        event_id=f"evt_{seq:06d}",
        stream="test:events",
        source="test",
        event_ts=event_ts.isoformat(),
        available_ts=available_ts.isoformat(),
        timestamp=available_ts.isoformat(),
        account_id=None,
        correlation_id=None,
        causation_id=None,
        payload={"seq": seq},
    )


def _choice() -> StrikeChoice:
    quote = StrikeQuote(
        rule="ITM100",
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        bid=140.0,
        ask=141.0,
        mid=140.5,
        spread=1.0,
        quote_age_ms=200,
        est_delta=0.65,
        est_round_trip_pts=2.0,
    )
    return StrikeChoice(chosen="ITM100", reason="TEST", rule_version="t", alternatives=(quote,))


def _signal() -> Signal:
    return Signal(
        signal_id="sg_a",
        strategy_id="PAPER-A",
        underlying="NIFTY",
        side="CE",
        strike_rule="ROUTER",
        strike_choice=_choice(),
        decision_ts=NOW.isoformat(),
        confidence=0.6,
        exit_plan=ExitPlan(catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0))),
        reasons=("TEST",),
        features={"ema_5": 1.0},
    )


def _selector(clock: SimClock) -> BossSelector:
    basket = SessionBasketGate(
        Basket(
            session="2026-09-28",
            market="IN_INDEX_OPT",
            entries=(BasketEntry("PAPER-A", ("NIFTY",), 1.0, 25, "paper"),),
            source="test",
            basket_hash="testhash19",
        )
    )
    return BossSelector(clock=clock, config=load_engine_config(ENGINE_YAML), basket=basket)


def _bar(now: datetime) -> BarContext:
    return BarContext(
        underlying="NIFTY",
        bar_ts=now,
        available_ts=now,
        feed_status="UP",
        em30=40.294117647058826,
        delta=0.5,
        stop=50.0,
        regime_label="trend_up",
        signal_stages={"PAPER-A": "paper"},
    )


def _engine_pass() -> tuple[tuple[Any, ...], float, str]:
    """Boss decisions + kernel hash. Advisor is never a handler."""
    clock = SimClock(NOW)
    t0 = time.perf_counter()
    out = _selector(clock).decide([_signal()], _bar(clock.now()))
    decide_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    summary = Engine(
        EnvelopeSource([_envelope(i) for i in range(20)]),
        SimClock(NOW),
        MemoryBus(),
        [],
        InMemoryLedgerStore(),
    ).run()
    return out.decisions, decide_s + (time.perf_counter() - t1), summary.output_hash


class HungProvider(Provider):
    name, offline, model = "hung", True, "hung"

    def complete(self, system: str, user: str, *, context: object, context_hash: str, timeout_s: float) -> Reply:
        time.sleep(1.0)
        return Reply(text='{"verdict":"agree","confidence":1,"reasons":["late"],"risk_flags":[]}')


def test_engine_decisions_and_timings_identical_with_advisor_on_off_or_hung(tmp_path: Path) -> None:
    """Fault: engine decisions and timings match with advisor on, off, or hung."""
    reset_advisors()
    _engine_pass()  # warmup imports
    off_decisions, off_t, off_hash = _engine_pass()

    advice: list[dict[str, Any]] = []
    on = LlmAdvisorService(
        replay=True, clock=SimClock(NOW), cfg=_cfg(tmp_path), provider=MockProvider(), sink=advice.append
    )
    on_decisions, on_t, on_hash = _engine_pass()
    t_submit = time.perf_counter()
    for row in on_decisions:
        on.consume(DECISION_STREAM, asdict(row))
    assert time.perf_counter() - t_submit < 0.05
    on.wait_idle(timeout_s=2.0)
    assert advice and advice[0]["decision_id"] == on_decisions[0].decision_id
    load_advice(advice[0])
    assert advice[0]["verdict"] in {"agree", "disagree", "abstain"}
    assert ADVICE_STREAM == "llm:advice"

    hung = LlmAdvisorService(
        replay=True,
        clock=SimClock(NOW),
        cfg=_cfg(tmp_path / "h"),
        provider=HungProvider(),
        sink=lambda _p: None,
    )
    hung_decisions, hung_t, hung_hash = _engine_pass()
    t_hung = time.perf_counter()
    hung.on_decision(asdict(hung_decisions[0]))
    assert time.perf_counter() - t_hung < 0.05

    off_rows = [asdict(d) for d in off_decisions]
    assert off_rows == [asdict(d) for d in on_decisions] == [asdict(d) for d in hung_decisions]
    assert off_hash == on_hash == hung_hash
    assert max(off_t, on_t, hung_t) < 2.0
    assert abs(off_t - on_t) < 1.0 and abs(off_t - hung_t) < 1.0
    on.close()
    hung.close()
    reset_advisors()


def test_no_provider_call_in_replay_or_ci_socket_guard(tmp_path: Path, monkeypatch: Any) -> None:
    """Replay / CI: RecordedProvider only; any socket or urlopen is a failure."""
    reset_advisors()

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("provider socket used in replay/CI")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    monkeypatch.setattr(urllib.request, "urlopen", _boom)

    cfg = _cfg(tmp_path, provider="openai", replay_provider="openai")
    svc = LlmAdvisorService(replay=True, clock=SimClock(NOW), cfg=cfg, state_dir=tmp_path)
    assert isinstance(svc.advisor.provider, RecordedProvider)
    clock = SimClock(NOW)
    svc.on_decision(asdict(_selector(clock).decide([_signal()], _bar(clock.now())).decisions[0]))
    svc.wait_idle(timeout_s=2.0)
    svc.close()
    ready = run_llm_advisor(tmp_path / "cli", SimClock(NOW), once=True, replay=True)
    assert (tmp_path / "cli" / "llm-advisor.ready").is_file()
    assert isinstance(ready.advisor.provider, RecordedProvider)
    ready.close()
    reset_advisors()


def test_secrets_scrubbed_from_stored_context(tmp_path: Path, monkeypatch: Any) -> None:
    """Reuse desk_ml scrub/build_context: secrets never reach stored context."""
    reset_advisors()
    key = "sk-test-" + "A" * 30
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.c2lnbmF0dXJlZm9v"
    monkeypatch.setenv("OPENAI_API_KEY", key)
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "tok_" + "z" * 20)
    stored = build_context(
        underlying="NIFTY",
        tick_ts=int(NOW.timestamp()),
        ist_time="10:05",
        signal={"side": "CE", "strike": 24400.0},
        brief={
            "premarket": {"regime_note": f"client 1100223344 token {jwt} key {key}"},
            "intermarket": {"api_key": key, "dhan_client_id": "1100223344", "USDINR": 83.0},
        },
        book={"today_pnl_inr": -500.0, "account_id": "1100223344", "access_token": jwt},
    )
    blob = json.dumps(stored) + json.dumps(scrub({"access_token": jwt, "session_high": 1.0}))
    for secret in (key, jwt, "1100223344", "account_id", "access_token", "api_key", "dhan_client_id"):
        assert secret not in blob

    advice: list[dict[str, Any]] = []
    svc = LlmAdvisorService(
        replay=True, clock=SimClock(NOW), cfg=_cfg(tmp_path), provider=MockProvider(), sink=advice.append
    )
    dirty = asdict(_selector(SimClock(NOW)).decide([_signal()], _bar(NOW)).decisions[0])
    dirty["shadow"] = {**(dirty.get("shadow") or {}), "note": key}
    svc.on_decision(dirty)
    svc.wait_idle(timeout_s=2.0)
    log_text = (tmp_path / "replay.jsonl").read_text(encoding="utf-8") if (tmp_path / "replay.jsonl").is_file() else ""
    assert key not in log_text and key not in json.dumps(advice)
    svc.close()
    reset_advisors()
