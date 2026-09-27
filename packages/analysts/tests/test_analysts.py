"""Analyst registry: interface, config keys, timeout/crash -> ABSTAIN, lossless wrap of the paper room."""

import time
from pathlib import Path

import pytest

from analysts import ABSTAIN, BUY_CE, REGISTRY, Analyst, AnalystRoom, MarketContext, Vote, build, load_config, register
from analysts.legacy import LEGACY_SOURCES, from_legacy, to_legacy
from desk_ml.picker import collect_analyst_votes

REPO = Path(__file__).resolve().parents[3]

ROOM_INPUTS = dict(
    follows={"side": "CE", "verdict": "PE_WRITERS"},
    logit={"side": "PE", "status": "OK"},
    logit_xr={"status": "DATA_INSUFFICIENT", "reason": "thin"},
    greeks_side=None,
    greeks_skip="GREEKS_NO_CLONE",
    ml001_hold=True,
    ml002_hold=False,
    ml1={"side": None, "status": "DATA_INSUFFICIENT"},
    tv_side="CE",
    classified={"regime": "TREND", "direction": "UP"},
    extra=None,
)


def ctx(**over):
    return MarketContext(underlying="NIFTY", ts=1, i=1, inputs={**ROOM_INPUTS, **over})


class Fixed(Analyst):
    def __init__(self, aid, signal=BUY_CE, sleep=0.0, crash=False):
        self.analyst_id, self.signal, self.sleep, self.crash = aid, signal, sleep, crash

    def vote(self, context):
        if self.crash:
            raise RuntimeError("boom")
        time.sleep(self.sleep)
        return Vote(self.analyst_id, self.signal, 0.7, "fixed")


def test_vote_validates_and_round_trips():
    v = Vote("A", BUY_CE, 0.6, "why", {"k": 1})
    assert v.side == "CE" and Vote.from_payload(v.to_payload()) == v
    with pytest.raises(ValueError):
        Vote("A", "BUY", 0.5, "x")
    with pytest.raises(ValueError):
        Vote("A", BUY_CE, 1.5, "x")


def test_default_registry_is_the_paper_room_in_order():
    assert [a.analyst_id for a in build()] == list(LEGACY_SOURCES)
    cfg = load_config(REPO / "config" / "analysts.yaml")
    assert cfg["voting"] == list(LEGACY_SOURCES) and cfg["timeout_ms"] == 500
    assert "rng60_atr" in cfg["shadow"] and "gex" in cfg["shadow"]
    assert all(k not in cfg["voting"] for k in cfg["shadow"])
    with pytest.raises(ValueError):
        build(["follows", "NO-SUCH-ANALYST"])


def test_wrapped_room_is_lossless():
    room = AnalystRoom(build())
    legacy = collect_analyst_votes(**ROOM_INPUTS)
    votes = [v for v, _ms in room.collect(ctx())]
    assert [to_legacy(v) for v in votes] == legacy
    assert all(to_legacy(from_legacy(v)) == v for v in legacy)
    signals = {v.analyst_id: v.signal for v in votes}
    assert signals["follows"] == "BUY_CE" and signals["logit"] == "BUY_PE" and signals["ML-001"] == "HOLD"
    assert signals["STRAT-003"] == "BUY_CE" and signals["STRAT-001"] == ABSTAIN
    room.close()


def test_register_new_analyst_by_config_key():
    key = "TEST-FEATURE-ANALYST"

    @register(key)
    class Feature(Analyst):
        analyst_id = key

        def vote(self, context):
            val = context.features.get("breadth")
            if val is None:
                return Vote.abstain(self.analyst_id, "FEATURE_MISSING")
            return Vote(self.analyst_id, BUY_CE if val > 0 else "BUY_PE", min(1.0, abs(val)), f"breadth={val}")

    try:
        room = AnalystRoom(build(["follows", key]))
        c = MarketContext(underlying="NIFTY", ts=1, i=1, inputs=ROOM_INPUTS, features={"breadth": 0.4})
        got = {v.analyst_id: v for v, _ in room.collect(c)}
        assert got[key].signal == BUY_CE and got[key].confidence == 0.4
        assert to_legacy(got[key]).spoken()
        with pytest.raises(ValueError):
            register(key, Feature)
        room.close()
    finally:
        REGISTRY.pop(key, None)


def test_replay_wall_clock_timeout_does_not_stall_the_room():
    """A hung capped analyst abstains. The rest of the replay tick still returns, and the next tick does not wait."""
    import threading

    release = threading.Event()

    class Hung(Analyst):
        analyst_id = "hung"
        wall_clock = True

        def vote(self, context):
            release.wait(2)
            return Vote(self.analyst_id, BUY_CE, 0.7, "late")

    class Capped(Analyst):
        analyst_id = "capped"

        def vote(self, context):
            return Vote(self.analyst_id, BUY_CE, 0.7, "fast")

    room = AnalystRoom(
        [Fixed("ok"), Hung(), Capped()],
        timeout_s=0.05,
        timeouts_s={"capped": 1.0},
        deterministic=True,
    )
    try:
        t0 = time.perf_counter()
        out = {v.analyst_id: v for v, _ in room.collect(ctx())}
        assert time.perf_counter() - t0 < 0.5
        assert out["ok"].signal == BUY_CE and out["capped"].signal == BUY_CE
        assert out["hung"].signal == ABSTAIN and out["hung"].reasoning == "TIMEOUT"
        t1 = time.perf_counter()
        again = {v.analyst_id: v for v, _ in room.collect(ctx())}
        assert time.perf_counter() - t1 < 0.2
        assert again["ok"].signal == BUY_CE and again["capped"].signal == BUY_CE
        assert again["hung"].reasoning == "TIMEOUT"
        assert room.stats["timeouts"] >= 2
    finally:
        release.set()
        room.close()


def test_malformed_analyst_yaml_does_not_stop_the_event_bus(tmp_path, caplog):
    """A broken analysts.yaml is logged and replaced with the default room. The bus still runs."""
    import logging
    from types import SimpleNamespace

    from desk_ml.event_path import EventSession
    from events import MemoryBus

    bad = tmp_path / "analysts.yaml"
    bad.write_text("analysts: [\n  - {key: LLM-ANALYST\n")
    bus = MemoryBus()
    session = EventSession(bus=bus, analysts_config=bad, deterministic=True)
    with caplog.at_level(logging.ERROR, logger="analysts"):
        session.attach(SimpleNamespace())
    try:
        assert "follows" in session.room.analyst_ids
        assert any("analyst config" in rec.message for rec in caplog.records)
        bus.publish("FOUNDER_COMMAND", {"command": "PAUSE_ENTRIES"}, source="test")
        assert session.desk.paused is True and bus.errors == []
    finally:
        session.close()


def test_replay_mode_does_not_abstain_on_wall_clock():
    """Parity must not flake when an analyst is slow. deterministic=True ignores the timeout."""
    room = AnalystRoom([Fixed("slow", sleep=0.2)], timeout_s=0.01, deterministic=True)
    out = {v.analyst_id: v for v, _ in room.collect(ctx())}
    assert out["slow"].signal == BUY_CE and room.stats["timeouts"] == 0
    room.close()


def test_per_analyst_timeout_overrides_the_default():
    room = AnalystRoom(
        [Fixed("fast"), Fixed("slow", sleep=0.3)],
        timeout_s=2.0,
        timeouts_s={"slow": 0.05},
    )
    out = {v.analyst_id: v for v, _ in room.collect(ctx())}
    assert out["fast"].signal == BUY_CE
    assert out["slow"].signal == ABSTAIN and out["slow"].reasoning == "TIMEOUT"
    room.close()


def test_timeout_and_crash_abstain_without_breaking_others():
    room = AnalystRoom([Fixed("ok"), Fixed("slow", sleep=1.0), Fixed("bad", crash=True), Fixed("ok2")], timeout_s=0.1)
    t0 = time.perf_counter()
    out = {v.analyst_id: v for v, _ in room.collect(ctx())}
    assert time.perf_counter() - t0 < 0.5
    assert out["ok"].signal == BUY_CE and out["ok2"].signal == BUY_CE
    assert out["slow"].signal == ABSTAIN and out["slow"].reasoning == "TIMEOUT"
    assert out["bad"].signal == ABSTAIN and out["bad"].reasoning == "ERROR:RuntimeError"
    assert room.stats == {"votes": 4, "timeouts": 1, "errors": 1}
    room.close()


def test_analyst_returning_someone_elses_vote_abstains():
    class Liar(Analyst):
        analyst_id = "liar"

        def vote(self, context):
            return Vote("other", BUY_CE, 1.0, "x")

    room = AnalystRoom([Liar()])
    (vote, _), = room.collect(ctx())
    assert vote.signal == ABSTAIN and vote.reasoning == "ERROR:TypeError"
    room.close()


def test_room_answers_request_votes_over_the_bus():
    from events import MemoryBus

    bus, contexts, got = MemoryBus(), {}, []
    room = AnalystRoom([Fixed("a"), Fixed("b", crash=True)])
    room.attach(bus, contexts)
    bus.subscribe(["ANALYST_VOTE"], lambda e: got.append((e.source, e.payload["signal"])))
    contexts["r1"] = ctx()
    bus.publish("REQUEST_VOTES", {"request_id": "r1"}, source="boss")
    assert got == [("analyst:a", BUY_CE), ("analyst:b", ABSTAIN)] and not bus.errors
    room.close()
