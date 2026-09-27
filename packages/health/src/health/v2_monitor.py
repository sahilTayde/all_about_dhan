"""V2-14 health monitor: snapshot checks, bus collector, alert rules of section 5.4.

The bus handler only copies envelope fields into memory and queues alerts.
A failing or slow sink cannot stall publish(). Paper only; no broker calls.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from contracts.clock import Clock, LiveClock
from contracts.envelope import Envelope
from contracts.instruments import India
from events.bus import EventBus
from events.schema import Event

from health.v2_alerts import (
    Alert,
    AlertSink,
    DedupeStore,
    FanoutSink,
    FileAlertSink,
    NullSink,
    QueuedAlertSink,
    TelegramSink,
    sanitize_alert_text,
)
from health.v2_metrics import MetricsRegistry

log = logging.getLogger("health.v2")

# Section 5.4 / V2-14 thresholds.
FEED_DOWN_S = 10.0
ENGINE_HEARTBEAT_S = 15.0
CONSUMER_LAG_S = 5.0
OUTBOX_BACKLOG_N = 100
ORDER_STUCK_S = 30.0
DISK_MIN_GB = 5.0
BACKUP_MAX_S = 26 * 3600.0
TOKEN_EXPIRY_S = 2 * 3600.0
CHECKPOINT_MAX_S = 60.0
DEPTH_STALE_S = 10.0
DEPTH_MIN_COVERAGE = 0.95

_INDIA = India()
_BUS_TYPES = ("POSITION_UPDATE", "POSITION_CLOSED", "ENTRY_VETOED", "HEALTH_ALERT")


@dataclass(frozen=True)
class OpenPosition:
    position_id: str
    net_qty: int
    protective_order: str | None = None
    stop: dict[str, Any] | None = None


@dataclass(frozen=True)
class StuckOrder:
    client_order_id: str
    state: str
    submitted_age_s: float


@dataclass
class HealthSnapshot:
    """Pure inputs for section 5.4. Never carries a token value."""

    feed_status: str | None = None  # UP | DOWN | STALE
    feed_down_s: float = 0.0
    engine_heartbeat_age_s: float | None = None
    consumer_lag_s: dict[str, float] = field(default_factory=dict)
    outbox_backlog: int = 0
    checkpoint_age_s: float | None = None
    positions: tuple[OpenPosition, ...] = ()
    breaker_open: bool = False
    backup_age_s: float | None = None
    token_expires_in_s: float | None = None
    disk_free_gb: float | None = None
    recon_ok: bool = True
    rehydrate_mismatch: bool = False
    critical_veto_codes: tuple[str, ...] = ()
    disabled_strategies: tuple[str, ...] = ()
    stuck_orders: tuple[StuckOrder, ...] = ()
    depth_age_s: dict[str, float] = field(default_factory=dict)
    depth_coverage: dict[str, float] = field(default_factory=dict)
    orders_by_state: dict[str, int] = field(default_factory=dict)
    pnl_realised_inr: float = 0.0
    pnl_unrealised_inr: float = 0.0
    llm_spend_usd: float = 0.0
    engine_rss_bytes: float = 0.0
    tick_to_bar_s: float | None = None
    bar_to_decision_s: float | None = None
    risk_check_s: float | None = None
    decision_to_paper_ack_s: float | None = None


def _has_stop(pos: OpenPosition) -> bool:
    if pos.net_qty == 0:
        return True
    if pos.protective_order:
        return True
    stop = pos.stop or {}
    return bool(stop.get("price") is not None or stop.get("kind"))


def failing_alerts(snap: HealthSnapshot, *, in_market: bool) -> dict[str, Alert]:
    """Evaluate every V2-14 / 5.4 rule. Return dedupe-key → ALERT (event filled later)."""
    out: dict[str, Alert] = {}

    def add(rule: str, key: str, severity: str, message: str) -> None:
        out[key] = Alert(
            rule=rule,
            event="ALERT",
            severity=severity,
            message=sanitize_alert_text(message),
            key=key,
            ts="",
        )

    if snap.feed_status == "DOWN" and snap.feed_down_s > FEED_DOWN_S:
        add(
            "FEED_DOWN",
            "FEED_DOWN",
            "CRITICAL",
            f"feed DOWN for {snap.feed_down_s:.0f}s (limit {FEED_DOWN_S:.0f}s)",
        )
    if snap.feed_status == "STALE" and in_market:
        add("FEED_STALE", "FEED_STALE", "CRITICAL", "feed STALE in market hours")

    age = snap.engine_heartbeat_age_s
    if age is None or age > ENGINE_HEARTBEAT_S:
        shown = "missing" if age is None else f"{age:.0f}s"
        add(
            "ENGINE_HEARTBEAT",
            "ENGINE_HEARTBEAT",
            "CRITICAL",
            f"engine heartbeat {shown} (limit {ENGINE_HEARTBEAT_S:.0f}s)",
        )

    for stream, lag in snap.consumer_lag_s.items():
        if lag > CONSUMER_LAG_S:
            add(
                "CONSUMER_LAG",
                f"CONSUMER_LAG:{stream}",
                "WARN",
                f"consumer lag {lag:.1f}s on {stream} (limit {CONSUMER_LAG_S:.0f}s)",
            )

    if snap.outbox_backlog > OUTBOX_BACKLOG_N:
        add(
            "OUTBOX_BACKLOG",
            "OUTBOX_BACKLOG",
            "WARN",
            f"outbox backlog {snap.outbox_backlog} (limit {OUTBOX_BACKLOG_N})",
        )

    if not snap.recon_ok:
        add("RECON_MISMATCH", "RECON_MISMATCH", "CRITICAL", "reconciliation mismatch")
    if snap.rehydrate_mismatch:
        add(
            "REHYDRATE_MISMATCH", "REHYDRATE_MISMATCH", "CRITICAL", "REHYDRATE_MISMATCH"
        )

    for code in snap.critical_veto_codes:
        add(
            "CRITICAL_VETO",
            f"CRITICAL_VETO:{code}",
            "CRITICAL",
            f"critical risk veto: {code}",
        )

    for sid in snap.disabled_strategies:
        add(
            "STRATEGY_DISABLED",
            f"STRATEGY_DISABLED:{sid}",
            "WARN",
            f"strategy disabled: {sid}",
        )

    for order in snap.stuck_orders:
        if order.state == "SUBMITTED" and order.submitted_age_s > ORDER_STUCK_S:
            add(
                "ORDER_STUCK",
                f"ORDER_STUCK:{order.client_order_id}",
                "CRITICAL",
                f"order {order.client_order_id} stuck in SUBMITTED for {order.submitted_age_s:.0f}s "
                f"(limit {ORDER_STUCK_S:.0f}s)",
            )

    for pos in snap.positions:
        if not _has_stop(pos):
            add(
                "PROTECTIVE_STOP",
                f"PROTECTIVE_STOP:{pos.position_id}",
                "CRITICAL",
                f"position {pos.position_id} has no protective stop",
            )

    if snap.disk_free_gb is not None and snap.disk_free_gb < DISK_MIN_GB:
        add(
            "DISK",
            "DISK",
            "WARN",
            f"only {snap.disk_free_gb:.1f} GB free (min {DISK_MIN_GB:.1f} GB)",
        )

    if snap.backup_age_s is not None and snap.backup_age_s > BACKUP_MAX_S:
        add(
            "BACKUP_AGE",
            "BACKUP_AGE",
            "WARN",
            f"backup age {snap.backup_age_s / 3600:.1f}h (limit {BACKUP_MAX_S / 3600:.0f}h)",
        )

    if snap.token_expires_in_s is not None and snap.token_expires_in_s < TOKEN_EXPIRY_S:
        mins = max(0, int(snap.token_expires_in_s // 60))
        add(
            "TOKEN_EXPIRY", "TOKEN_EXPIRY", "CRITICAL", f"Dhan token expires in {mins}m"
        )

    if snap.breaker_open:
        add(
            "RESTART_LOOP",
            "RESTART_LOOP",
            "CRITICAL",
            "RESTART_LOOP: service breaker is open",
        )

    if snap.checkpoint_age_s is not None and snap.checkpoint_age_s > CHECKPOINT_MAX_S:
        add(
            "CHECKPOINT_AGE",
            "CHECKPOINT_AGE",
            "WARN",
            f"checkpoint age {snap.checkpoint_age_s:.0f}s (limit {CHECKPOINT_MAX_S:.0f}s)",
        )

    if in_market:
        for strike, dage in snap.depth_age_s.items():
            if dage > DEPTH_STALE_S:
                add(
                    "DEPTH_COVERAGE",
                    f"DEPTH_COVERAGE:{strike}",
                    "WARN",
                    f"depth stale {dage:.0f}s on {strike} (limit {DEPTH_STALE_S:.0f}s)",
                )
        for strike, frac in snap.depth_coverage.items():
            if frac < DEPTH_MIN_COVERAGE:
                add(
                    "DEPTH_COVERAGE",
                    f"DEPTH_COVERAGE:{strike}",
                    "WARN",
                    f"depth coverage {frac:.2f} on {strike} (min {DEPTH_MIN_COVERAGE:.2f})",
                )

    return out


class BusHealthCollector:
    """Subscribe to the v2 bus. Handler copies fields only — no I/O, no sink."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._positions: dict[str, OpenPosition] = {}
        self._feed_status: str | None = None
        self._feed_since: datetime | None = None
        self._engine_seen: datetime | None = None
        self._vetoes: list[str] = []
        self._disabled: list[str] = []
        self._rehydrate = False

    def observe_event(self, event: Event) -> None:
        self.observe_envelope(Envelope.from_json(asdict(event)))

    def observe_envelope(self, env: Envelope) -> None:
        payload = env.payload
        kind = env.event_type
        with self._lock:
            if kind in {"POSITION_UPDATE", "pos:updates"} or kind == "POSITION_UPDATE":
                pid = str(payload.get("position_id") or "")
                if pid:
                    qty = int(payload.get("net_qty") or 0)
                    stop = payload.get("stop")
                    stop_d = stop if isinstance(stop, dict) else None
                    prot = payload.get("protective_order")
                    self._positions[pid] = OpenPosition(
                        position_id=pid,
                        net_qty=qty,
                        protective_order=str(prot) if prot else None,
                        stop=stop_d,
                    )
            elif kind == "POSITION_CLOSED":
                self._positions.pop(str(payload.get("position_id") or ""), None)
            elif kind in {"FEED_STATUS", "md:status"}:
                self._feed_status = str(payload.get("status") or "") or None
                since = payload.get("since")
                if isinstance(since, str):
                    try:
                        self._feed_since = datetime.fromisoformat(since)
                    except ValueError:
                        self._feed_since = None
            elif kind in {"ENGINE_STATUS", "health:engine"}:
                try:
                    self._engine_seen = datetime.fromisoformat(
                        env.event_ts or env.timestamp
                    )
                except ValueError:
                    self._engine_seen = None
            elif kind == "ENTRY_VETOED":
                code = str(payload.get("reason_code") or payload.get("code") or "VETO")
                if payload.get("critical") or payload.get("severity") == "CRITICAL":
                    self._vetoes.append(code)
            elif kind == "HEALTH_ALERT" and payload.get("rule") == "REHYDRATE_MISMATCH":
                self._rehydrate = True
            if payload.get("strategy_disabled"):
                self._disabled.append(str(payload["strategy_disabled"]))
            if payload.get("breaker_open") is True:
                pass  # breaker is snapshot-injected (V2-15 owns the file)

    def snapshot(
        self, now: datetime, base: HealthSnapshot | None = None
    ) -> HealthSnapshot:
        snap = base or HealthSnapshot()
        with self._lock:
            feed_down = 0.0
            if self._feed_status == "DOWN" and self._feed_since is not None:
                feed_down = max(0.0, (now - self._feed_since).total_seconds())
            engine_age = None
            if self._engine_seen is not None:
                engine_age = max(0.0, (now - self._engine_seen).total_seconds())
            return HealthSnapshot(
                feed_status=self._feed_status
                if self._feed_status is not None
                else snap.feed_status,
                feed_down_s=feed_down or snap.feed_down_s,
                engine_heartbeat_age_s=engine_age
                if engine_age is not None
                else snap.engine_heartbeat_age_s,
                consumer_lag_s=dict(snap.consumer_lag_s),
                outbox_backlog=snap.outbox_backlog,
                checkpoint_age_s=snap.checkpoint_age_s,
                positions=tuple(self._positions.values()) or snap.positions,
                breaker_open=snap.breaker_open,
                backup_age_s=snap.backup_age_s,
                token_expires_in_s=snap.token_expires_in_s,
                disk_free_gb=snap.disk_free_gb,
                recon_ok=snap.recon_ok,
                rehydrate_mismatch=self._rehydrate or snap.rehydrate_mismatch,
                critical_veto_codes=tuple(self._vetoes) or snap.critical_veto_codes,
                disabled_strategies=tuple(self._disabled) or snap.disabled_strategies,
                stuck_orders=snap.stuck_orders,
                depth_age_s=dict(snap.depth_age_s),
                depth_coverage=dict(snap.depth_coverage),
                orders_by_state=dict(snap.orders_by_state),
                pnl_realised_inr=snap.pnl_realised_inr,
                pnl_unrealised_inr=snap.pnl_unrealised_inr,
                llm_spend_usd=snap.llm_spend_usd,
                engine_rss_bytes=snap.engine_rss_bytes,
                tick_to_bar_s=snap.tick_to_bar_s,
                bar_to_decision_s=snap.bar_to_decision_s,
                risk_check_s=snap.risk_check_s,
                decision_to_paper_ack_s=snap.decision_to_paper_ack_s,
            )


class V2HealthMonitor:
    """Evaluate snapshots, persist dedupe, expose metrics. Never blocks the bus."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        sink: AlertSink | None = None,
        queue_sink: bool = True,
        state_path: Path | None = None,
        alerts_path: Path | None = None,
        metrics: MetricsRegistry | None = None,
        extra_sinks: list[AlertSink] | None = None,
        evaluate_on_event: bool = True,
    ) -> None:
        self.clock = clock or LiveClock()
        self.dedupe = DedupeStore(state_path)
        self.metrics = metrics or MetricsRegistry()
        self.collector = BusHealthCollector()
        self.evaluate_on_event = evaluate_on_event
        self.last_events: list[Alert] = []
        inners: list[AlertSink] = []
        if alerts_path is not None:
            inners.append(FileAlertSink(alerts_path))
        inners.append(TelegramSink())
        if extra_sinks:
            inners.extend(extra_sinks)
        if sink is not None:
            inners.append(sink)
        fanout: AlertSink = FanoutSink(inners) if inners else NullSink()
        self._queued = QueuedAlertSink(fanout) if queue_sink else None
        self._sink: AlertSink = self._queued if self._queued is not None else fanout
        self._sub_id: str | None = None

    def attach_bus(self, bus: EventBus) -> str:
        """Subscribe. The callback copies state and queues alerts; it must not I/O."""
        self._sub_id = bus.subscribe(_BUS_TYPES, self._on_bus_event, priority=1000)
        return self._sub_id

    def _on_bus_event(self, event: Event) -> None:
        self.collector.observe_event(event)
        if self.evaluate_on_event:
            self.run_once(self.collector.snapshot(self.clock.now()))

    def observe_envelope(self, env: Envelope) -> None:
        self.collector.observe_envelope(env)

    def run_once(self, snap: HealthSnapshot | None = None) -> list[Alert]:
        now = self.clock.now()
        if snap is None:
            snap = self.collector.snapshot(now)
        in_market = _INDIA.is_open(now)
        failing = failing_alerts(snap, in_market=in_market)
        events = self.dedupe.diff(failing, now)
        for alert in events:
            self._sink.emit(alert)
        self.last_events = events
        self._apply_metrics(snap)
        return events

    def flush(self, timeout: float = 2.0) -> None:
        if self._queued is not None:
            self._queued.flush(timeout)

    def _apply_metrics(self, snap: HealthSnapshot) -> None:
        self.metrics.observe_latencies(
            tick_to_bar_s=snap.tick_to_bar_s,
            bar_to_decision_s=snap.bar_to_decision_s,
            risk_check_s=snap.risk_check_s,
            decision_to_paper_ack_s=snap.decision_to_paper_ack_s,
        )
        self.metrics.apply_gauges(
            consumer_lag_s=snap.consumer_lag_s,
            outbox_backlog=snap.outbox_backlog,
            checkpoint_age_s=snap.checkpoint_age_s,
            orders_by_state=snap.orders_by_state,
            open_positions=sum(1 for p in snap.positions if p.net_qty != 0),
            pnl_realised_inr=snap.pnl_realised_inr,
            pnl_unrealised_inr=snap.pnl_unrealised_inr,
            llm_spend_usd=snap.llm_spend_usd,
            engine_rss_bytes=snap.engine_rss_bytes,
            depth_coverage=snap.depth_coverage,
        )
