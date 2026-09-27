"""V2-14 prometheus-client registry and 127.0.0.1 /metrics endpoint.

Section 5.4 budget metrics. No Prometheus server is required: health scrapes
``generate()`` itself. Bind is loopback-only.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from prometheus_client.exposition import CONTENT_TYPE_LATEST

# Names that MUST appear on /metrics (acceptance: every budget metric).
BUDGET_METRIC_NAMES: tuple[str, ...] = (
    "aad_tick_to_bar_latency_seconds",
    "aad_bar_to_decision_latency_seconds",
    "aad_risk_check_latency_seconds",
    "aad_decision_to_paper_ack_latency_seconds",
    "aad_consumer_lag_seconds",
    "aad_outbox_backlog",
    "aad_checkpoint_age_seconds",
    "aad_vetoes_total",
    "aad_orders",
    "aad_open_positions",
    "aad_pnl_realised_inr",
    "aad_pnl_unrealised_inr",
    "aad_strategy_exceptions_total",
    "aad_feed_reconnects_total",
    "aad_late_ticks_total",
    "aad_llm_spend_usd",
    "aad_engine_rss_bytes",
    "aad_depth_coverage",
)

_LATENCY_BUCKETS = (0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0)


class MetricsRegistry:
    """One registry per process. Other v2 services can construct their own on 91xx."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry()
        self.tick_to_bar = Histogram(
            "aad_tick_to_bar_latency_seconds",
            "Last tick to BAR_CLOSED publish",
            registry=self.registry,
            buckets=_LATENCY_BUCKETS,
        )
        self.bar_to_decision = Histogram(
            "aad_bar_to_decision_latency_seconds",
            "BAR_CLOSED to DECISION",
            registry=self.registry,
            buckets=_LATENCY_BUCKETS,
        )
        self.risk_check = Histogram(
            "aad_risk_check_latency_seconds",
            "Risk check latency",
            registry=self.registry,
            buckets=_LATENCY_BUCKETS,
        )
        self.decision_to_paper_ack = Histogram(
            "aad_decision_to_paper_ack_latency_seconds",
            "DECISION to paper ack",
            registry=self.registry,
            buckets=_LATENCY_BUCKETS,
        )
        self.consumer_lag = Gauge(
            "aad_consumer_lag_seconds", "Consumer-group lag per stream", ["stream"], registry=self.registry
        )
        self.outbox_backlog = Gauge("aad_outbox_backlog", "Unpublished outbox rows", registry=self.registry)
        self.checkpoint_age = Gauge(
            "aad_checkpoint_age_seconds", "Engine checkpoint age", registry=self.registry
        )
        self.vetoes = Counter("aad_vetoes_total", "Risk vetoes by code", ["code"], registry=self.registry)
        self.orders = Gauge("aad_orders", "Open orders by state", ["state"], registry=self.registry)
        self.open_positions = Gauge("aad_open_positions", "Open positions", registry=self.registry)
        self.pnl_realised = Gauge("aad_pnl_realised_inr", "Realised P&L INR", registry=self.registry)
        self.pnl_unrealised = Gauge("aad_pnl_unrealised_inr", "Unrealised P&L INR", registry=self.registry)
        self.strategy_exceptions = Counter(
            "aad_strategy_exceptions_total", "Strategy exceptions", registry=self.registry
        )
        self.feed_reconnects = Counter(
            "aad_feed_reconnects_total", "Feed reconnects", registry=self.registry
        )
        self.late_ticks = Counter("aad_late_ticks_total", "Late ticks for a closed bar", registry=self.registry)
        self.llm_spend = Gauge("aad_llm_spend_usd", "LLM spend USD", registry=self.registry)
        self.engine_rss = Gauge("aad_engine_rss_bytes", "Engine RSS bytes", registry=self.registry)
        self.depth_coverage = Gauge(
            "aad_depth_coverage", "Depth coverage fraction per traded strike", ["strike"], registry=self.registry
        )
        # Seed labelled series so /metrics lists every budget name even before samples.
        self.consumer_lag.labels(stream="_").set(0)
        self.vetoes.labels(code="_").inc(0)
        self.orders.labels(state="_").set(0)
        self.depth_coverage.labels(strike="_").set(0)

    def observe_latencies(
        self,
        *,
        tick_to_bar_s: float | None = None,
        bar_to_decision_s: float | None = None,
        risk_check_s: float | None = None,
        decision_to_paper_ack_s: float | None = None,
    ) -> None:
        if tick_to_bar_s is not None:
            self.tick_to_bar.observe(tick_to_bar_s)
        if bar_to_decision_s is not None:
            self.bar_to_decision.observe(bar_to_decision_s)
        if risk_check_s is not None:
            self.risk_check.observe(risk_check_s)
        if decision_to_paper_ack_s is not None:
            self.decision_to_paper_ack.observe(decision_to_paper_ack_s)

    def apply_gauges(
        self,
        *,
        consumer_lag_s: dict[str, float] | None = None,
        outbox_backlog: int | None = None,
        checkpoint_age_s: float | None = None,
        orders_by_state: dict[str, int] | None = None,
        open_positions: int | None = None,
        pnl_realised_inr: float | None = None,
        pnl_unrealised_inr: float | None = None,
        llm_spend_usd: float | None = None,
        engine_rss_bytes: float | None = None,
        depth_coverage: dict[str, float] | None = None,
    ) -> None:
        if consumer_lag_s is not None:
            for stream, lag in consumer_lag_s.items():
                self.consumer_lag.labels(stream=stream).set(lag)
        if outbox_backlog is not None:
            self.outbox_backlog.set(outbox_backlog)
        if checkpoint_age_s is not None:
            self.checkpoint_age.set(checkpoint_age_s)
        if orders_by_state is not None:
            for state, n in orders_by_state.items():
                self.orders.labels(state=state).set(n)
        if open_positions is not None:
            self.open_positions.set(open_positions)
        if pnl_realised_inr is not None:
            self.pnl_realised.set(pnl_realised_inr)
        if pnl_unrealised_inr is not None:
            self.pnl_unrealised.set(pnl_unrealised_inr)
        if llm_spend_usd is not None:
            self.llm_spend.set(llm_spend_usd)
        if engine_rss_bytes is not None:
            self.engine_rss.set(engine_rss_bytes)
        if depth_coverage is not None:
            for strike, frac in depth_coverage.items():
                self.depth_coverage.labels(strike=strike).set(frac)

    def generate(self) -> bytes:
        return generate_latest(self.registry)


class MetricsEndpoint:
    """Loopback HTTP /metrics. Bind 127.0.0.1 only (paper-live scrapes itself)."""

    def __init__(self, metrics: MetricsRegistry, host: str = "127.0.0.1", port: int = 0) -> None:
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("metrics endpoint must bind loopback")
        self._metrics = metrics
        self._host = host
        self._port = port
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> tuple[str, int]:
        metrics = self._metrics

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                path = self.path.split("?", 1)[0]
                if path != "/metrics":
                    self.send_error(404)
                    return
                body = metrics.generate()
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE_LATEST)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt: str, *args: Any) -> None:
                return

        httpd = ThreadingHTTPServer((self._host, self._port), Handler)
        self._httpd = httpd
        self._thread = threading.Thread(target=httpd.serve_forever, name="health-v2-metrics", daemon=True)
        self._thread.start()
        host, port = httpd.server_address[:2]
        return str(host), int(port)

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
