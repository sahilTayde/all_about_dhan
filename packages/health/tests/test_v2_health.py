"""V2-14: section 5.4 alerts fire and clear; REG-02d; REG-09a; no token leaks."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from contracts.clock import IST, SimClock
from health.v2_alerts import Alert, DedupeStore, sanitize_alert_text
from health.v2_monitor import (
    HealthSnapshot,
    OpenPosition,
    StuckOrder,
    V2HealthMonitor,
    failing_alerts,
)

MON = datetime(2026, 9, 28, 10, 30, tzinfo=IST)  # Monday, market open
SAT = datetime(2026, 9, 26, 10, 30, tzinfo=IST)


class RecordingSink:
    def __init__(self) -> None:
        self.alerts: list[Alert] = []

    def emit(self, alert: Alert) -> None:
        self.alerts.append(alert)


def healthy(**kw: object) -> HealthSnapshot:
    base = {
        "feed_status": "UP",
        "engine_heartbeat_age_s": 1.0,
        "outbox_backlog": 0,
        "recon_ok": True,
        "breaker_open": False,
    }
    base.update(kw)
    return HealthSnapshot(**base)  # type: ignore[arg-type]


def _monitor(tmp_path: Path, clock: SimClock, sink: RecordingSink) -> V2HealthMonitor:
    return V2HealthMonitor(
        clock=clock,
        sink=sink,
        queue_sink=False,
        state_path=tmp_path / "dedupe.json",
        alerts_path=tmp_path / "alerts.jsonl",
        extra_sinks=[],
        evaluate_on_event=False,
    )


def test_each_alert_fires_within_threshold_and_clears_on_recovery(tmp_path: Path) -> None:
    clock = SimClock(MON)
    cases: list[tuple[str, HealthSnapshot, HealthSnapshot]] = [
        (
            "FEED_DOWN",
            healthy(feed_status="DOWN", feed_down_s=11),
            healthy(feed_status="UP", feed_down_s=0),
        ),
        (
            "FEED_STALE",
            healthy(feed_status="STALE"),
            healthy(feed_status="UP"),
        ),
        (
            "ENGINE_HEARTBEAT",
            healthy(engine_heartbeat_age_s=16),
            healthy(engine_heartbeat_age_s=1),
        ),
        (
            "CONSUMER_LAG",
            healthy(consumer_lag_s={"md:ticks": 6.0}),
            healthy(consumer_lag_s={"md:ticks": 1.0}),
        ),
        (
            "OUTBOX_BACKLOG",
            healthy(outbox_backlog=101),
            healthy(outbox_backlog=0),
        ),
        (
            "RECON_MISMATCH",
            healthy(recon_ok=False),
            healthy(recon_ok=True),
        ),
        (
            "REHYDRATE_MISMATCH",
            healthy(rehydrate_mismatch=True),
            healthy(rehydrate_mismatch=False),
        ),
        (
            "CRITICAL_VETO",
            healthy(critical_veto_codes=("KILL_SWITCH",)),
            healthy(critical_veto_codes=()),
        ),
        (
            "STRATEGY_DISABLED",
            healthy(disabled_strategies=("R8-E1",)),
            healthy(disabled_strategies=()),
        ),
        (
            "ORDER_STUCK",
            healthy(stuck_orders=(StuckOrder("o1", "SUBMITTED", 31),)),
            healthy(stuck_orders=()),
        ),
        (
            "PROTECTIVE_STOP",
            healthy(positions=(OpenPosition("p1", 65, None, None),)),
            healthy(positions=(OpenPosition("p1", 65, "aad-S", {"kind": "underlying", "price": 1.0}),)),
        ),
        ("DISK", healthy(disk_free_gb=3.0), healthy(disk_free_gb=12.0)),
        ("BACKUP_AGE", healthy(backup_age_s=27 * 3600), healthy(backup_age_s=3600)),
        ("TOKEN_EXPIRY", healthy(token_expires_in_s=30 * 60), healthy(token_expires_in_s=8 * 3600)),
        ("RESTART_LOOP", healthy(breaker_open=True), healthy(breaker_open=False)),
        ("CHECKPOINT_AGE", healthy(checkpoint_age_s=90), healthy(checkpoint_age_s=5)),
        (
            "DEPTH_COVERAGE",
            healthy(depth_age_s={"NIFTY:24400:CE": 12}),
            healthy(depth_age_s={"NIFTY:24400:CE": 0.2}),
        ),
    ]
    for rule, bad, good in cases:
        sink = RecordingSink()
        mon = _monitor(tmp_path / rule, clock, sink)
        fired = mon.run_once(bad)
        assert any(a.event == "ALERT" and a.rule == rule for a in fired), rule
        assert mon.run_once(bad) == []  # still failing: no duplicate
        recovered = mon.run_once(good)
        assert any(a.event == "RECOVERED" and a.rule == rule for a in recovered), rule


def test_thresholds_not_fired_just_inside(tmp_path: Path) -> None:
    clock = SimClock(MON)
    sink = RecordingSink()
    mon = _monitor(tmp_path, clock, sink)
    inside = healthy(
        feed_status="DOWN",
        feed_down_s=10.0,
        engine_heartbeat_age_s=15.0,
        consumer_lag_s={"md:ticks": 5.0},
        outbox_backlog=100,
        stuck_orders=(StuckOrder("o1", "SUBMITTED", 30),),
        disk_free_gb=5.0,
        backup_age_s=26 * 3600,
        token_expires_in_s=2 * 3600,
        checkpoint_age_s=60,
        depth_age_s={"NIFTY:24400:CE": 10.0},
        depth_coverage={"NIFTY:24400:CE": 0.95},
    )
    assert mon.run_once(inside) == []


def test_feed_stale_outside_market_hours_is_not_an_alarm() -> None:
    failing = failing_alerts(healthy(feed_status="STALE"), in_market=False)
    assert "FEED_STALE" not in failing


def test_feed_stale_uses_india_session(tmp_path: Path) -> None:
    sink = RecordingSink()
    mon = V2HealthMonitor(clock=SimClock(SAT), sink=sink, queue_sink=False, state_path=tmp_path / "d.json")
    assert mon.run_once(healthy(feed_status="STALE")) == []


def test_reg_02d_position_without_protective_stop_is_critical(tmp_path: Path) -> None:
    clock = SimClock(MON)
    sink = RecordingSink()
    mon = _monitor(tmp_path, clock, sink)
    bad = healthy(positions=(OpenPosition("ps_bare", 65, None, {}),))
    events = mon.run_once(bad)
    hit = [a for a in events if a.rule == "PROTECTIVE_STOP"]
    assert len(hit) == 1 and hit[0].severity == "CRITICAL" and "ps_bare" in hit[0].message
    ok = healthy(positions=(OpenPosition("ps_bare", 65, "aad-S", {"kind": "underlying", "price": 24400.0}),))
    assert any(a.event == "RECOVERED" and a.rule == "PROTECTIVE_STOP" for a in mon.run_once(ok))


def test_reg_09a_open_breaker_raises_restart_loop_once(tmp_path: Path) -> None:
    clock = SimClock(MON)
    sink = RecordingSink()
    mon = _monitor(tmp_path, clock, sink)
    first = mon.run_once(healthy(breaker_open=True))
    assert [a.rule for a in first] == ["RESTART_LOOP"] and first[0].severity == "CRITICAL"
    assert mon.run_once(healthy(breaker_open=True)) == []
    assert any(a.event == "RECOVERED" for a in mon.run_once(healthy(breaker_open=False)))


def test_no_duplicate_telegram_across_monitor_restart(tmp_path: Path) -> None:
    state = tmp_path / "dedupe.json"
    clock = SimClock(MON)
    sink = RecordingSink()
    m1 = V2HealthMonitor(clock=clock, sink=sink, queue_sink=False, state_path=state)
    assert any(a.rule == "RESTART_LOOP" for a in m1.run_once(healthy(breaker_open=True)))
    m2 = V2HealthMonitor(clock=clock, sink=sink, queue_sink=False, state_path=state)
    assert m2.run_once(healthy(breaker_open=True)) == []
    assert sum(1 for a in sink.alerts if a.rule == "RESTART_LOOP" and a.event == "ALERT") == 1


def test_alert_text_never_includes_tokens() -> None:
    fake = "123456789:AA" + ("x" * 33)
    cred_name = "DHAN_" + "ACCESS_TOKEN"
    leaked = f"bot said {fake} and {cred_name}=" + "notarealtokenvalue"
    cleaned = sanitize_alert_text(leaked)
    assert fake not in cleaned and "notarealtokenvalue" not in cleaned
    assert "[redacted]" in cleaned
    snap = healthy(token_expires_in_s=90 * 60)
    msg = failing_alerts(snap, in_market=True)["TOKEN_EXPIRY"].message
    assert "expires in 90m" in msg
    assert "DHAN_" not in msg and ":" not in msg.split("expires")[0]


def test_dedupe_store_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = DedupeStore(path)
    now = MON
    alert = Alert("DISK", "ALERT", "WARN", "only 1.0 GB free (min 5.0 GB)", "DISK", now.isoformat())
    first = store.diff({"DISK": alert}, now)
    assert first[0].event == "ALERT"
    store2 = DedupeStore(path)
    assert store2.diff({"DISK": alert}, now + timedelta(minutes=1)) == []


@pytest.fixture(autouse=True)
def no_telegram(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
