"""V2-14: /metrics exposes every section 5.4 budget metric."""

from __future__ import annotations

import urllib.request

from contracts.clock import IST, SimClock
from health.v2_metrics import BUDGET_METRIC_NAMES, MetricsEndpoint, MetricsRegistry
from health.v2_monitor import HealthSnapshot, OpenPosition, V2HealthMonitor

MON = __import__("datetime").datetime(2026, 9, 28, 10, 30, tzinfo=IST)


def test_metrics_registry_lists_every_budget_name() -> None:
    reg = MetricsRegistry()
    text = reg.generate().decode("utf-8")
    missing = [n for n in BUDGET_METRIC_NAMES if n not in text]
    assert missing == []


def test_metrics_endpoint_loopback_http() -> None:
    reg = MetricsRegistry()
    reg.observe_latencies(
        tick_to_bar_s=0.01,
        bar_to_decision_s=0.02,
        risk_check_s=0.003,
        decision_to_paper_ack_s=0.01,
    )
    reg.apply_gauges(
        outbox_backlog=3, checkpoint_age_s=4.0, open_positions=1, engine_rss_bytes=1000
    )
    ep = MetricsEndpoint(reg, host="127.0.0.1", port=0)
    host, port = ep.start()
    try:
        assert host == "127.0.0.1" and port > 0
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/metrics", timeout=2
        ) as resp:
            body = resp.read().decode("utf-8")
            assert resp.status == 200
        missing = [n for n in BUDGET_METRIC_NAMES if n not in body]
        assert missing == []
        assert "aad_outbox_backlog" in body
    finally:
        ep.stop()


def test_metrics_endpoint_refuses_non_loopback() -> None:
    try:
        MetricsEndpoint(MetricsRegistry(), host="0.0.0.0", port=0)
    except ValueError as exc:
        assert "loopback" in str(exc)
    else:
        raise AssertionError("expected loopback bind guard")


def test_monitor_applies_snapshot_to_metrics(tmp_path: object) -> None:
    from pathlib import Path

    clock = SimClock(MON)
    metrics = MetricsRegistry()
    mon = V2HealthMonitor(
        clock=clock,
        queue_sink=False,
        state_path=Path(tmp_path) / "d.json",  # type: ignore[arg-type]
        metrics=metrics,
    )
    mon.run_once(
        HealthSnapshot(
            feed_status="UP",
            engine_heartbeat_age_s=1,
            consumer_lag_s={"md:ticks": 0.2},
            outbox_backlog=7,
            checkpoint_age_s=3,
            positions=(OpenPosition("p1", 65, "s", {"price": 1.0}),),
            pnl_realised_inr=10.0,
            pnl_unrealised_inr=2.0,
            llm_spend_usd=0.001,
            engine_rss_bytes=50_000,
            depth_coverage={"NIFTY:24400:CE": 0.99},
            tick_to_bar_s=0.01,
            bar_to_decision_s=0.02,
            risk_check_s=0.004,
            decision_to_paper_ack_s=0.01,
            orders_by_state={"SUBMITTED": 0},
        )
    )
    text = metrics.generate().decode("utf-8")
    assert "aad_outbox_backlog 7" in text
    assert all(n in text for n in BUDGET_METRIC_NAMES)
