"""V2-14 alert sinks, durable dedupe, and token-safe text.

Sinks never run on the event-bus thread. Alert text is sanitised so tokens
cannot leak into Telegram, logs, or the founder jsonl.
"""

from __future__ import annotations

import json
import logging
import queue
import re
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from health.monitor import send_telegram

log = logging.getLogger("health.v2")

# Telegram bot tokens, Dhan credential assignments, and bot-URL leftovers.
# Patterns are source regexes, not live values.
_SECRET_RX = re.compile(
    r"\d{8,10}:AA[A-Za-z0-9_-]{33}"
    r"|DHAN_(?:ACCESS_TOKEN|CLIENT_SECRET|REFRESH_TOKEN|API_SECRET)\s*[=:]\s*\S+"
    r"|/bot[^/\s]+/"
    r"|Bearer\s+[A-Za-z0-9._\-]{16,}",
    re.IGNORECASE,
)


def sanitize_alert_text(text: str) -> str:
    """Strip credential-shaped substrings from any alert or log line."""
    return _SECRET_RX.sub("[redacted]", text)


@dataclass(frozen=True)
class Alert:
    """One firing or recovered rule (section 5.4)."""

    rule: str
    event: str  # ALERT | RECOVERED
    severity: str
    message: str
    key: str
    ts: str

    def as_record(self) -> dict[str, str]:
        return asdict(self)


class AlertSink(Protocol):
    def emit(self, alert: Alert) -> None:
        """Deliver one alert. Must not be invoked on the trading-bus thread."""


class NullSink:
    def emit(self, alert: Alert) -> None:
        return


class FileAlertSink:
    """Append-only jsonl for the founder page. A full disk must not raise."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def emit(self, alert: Alert) -> None:
        rec = json.dumps(alert.as_record(), separators=(",", ":"))
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(rec + "\n")
        except OSError as exc:
            log.error("v2 alerts.jsonl unwritable (%s): %s", type(exc).__name__, rec)


class TelegramSink:
    """Optional Telegram. Never logs the request URL (it contains the bot token)."""

    def emit(self, alert: Alert) -> None:
        text = sanitize_alert_text(
            f"all_about_dhan {alert.event} {alert.rule} ({alert.severity}): {alert.message}"
        )
        send_telegram(text)


class FanoutSink:
    """Deliver to every inner sink; one failure does not skip the rest."""

    def __init__(self, sinks: list[AlertSink]) -> None:
        self._sinks = list(sinks)

    def emit(self, alert: Alert) -> None:
        for sink in self._sinks:
            try:
                sink.emit(alert)
            except Exception:
                log.exception("alert sink failed (%s)", type(sink).__name__)


class QueuedAlertSink:
    """Non-blocking wrapper. ``emit`` is put_nowait; a slow/dead inner sink cannot stall the bus."""

    def __init__(self, inner: AlertSink, *, maxsize: int = 256) -> None:
        self._inner = inner
        self._q: queue.Queue[Alert | object] = queue.Queue(maxsize=maxsize)
        self._sentinel = object()
        self._busy = threading.Event()
        self._thread = threading.Thread(target=self._run, name="health-v2-alerts", daemon=True)
        self._thread.start()

    def emit(self, alert: Alert) -> None:
        try:
            self._q.put_nowait(alert)
        except queue.Full:
            log.warning("alert queue full; dropping %s", alert.rule)

    def flush(self, timeout: float = 2.0) -> None:
        """Wait until the worker has drained (tests). Does not stop the worker."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self._q.empty() and not self._busy.is_set():
                return
            time.sleep(0.01)

    def _run(self) -> None:
        while True:
            item = self._q.get()
            if item is self._sentinel:
                return
            assert isinstance(item, Alert)
            self._busy.set()
            try:
                self._inner.emit(item)
            except Exception:
                log.exception("alert sink failed (%s)", type(self._inner).__name__)
            finally:
                self._busy.clear()


class DedupeStore:
    """Persist active alerts so a monitor restart does not re-page Telegram."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self._active: dict[str, str] = {}  # key -> fingerprint
        self._load()

    def _load(self) -> None:
        if self.path is None:
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        for key, row in raw.items():
            if isinstance(row, dict) and row.get("active") and isinstance(row.get("fingerprint"), str):
                self._active[str(key)] = str(row["fingerprint"])

    def _save(self) -> None:
        if self.path is None:
            return
        payload = {k: {"active": True, "fingerprint": fp} for k, fp in self._active.items()}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            log.warning("dedupe state unwritable (%s)", type(exc).__name__)

    def diff(self, failing: dict[str, Alert], now: datetime) -> list[Alert]:
        """Emit ALERT for new keys and RECOVERED for keys that cleared. Same fingerprint is a no-op."""
        events: list[Alert] = []
        ts = now.isoformat(timespec="seconds")
        incoming = {k: a for k, a in failing.items()}
        for key, alert in incoming.items():
            fp = alert.message
            if self._active.get(key) == fp:
                continue
            self._active[key] = fp
            events.append(
                Alert(
                    rule=alert.rule,
                    event="ALERT",
                    severity=alert.severity,
                    message=sanitize_alert_text(alert.message),
                    key=key,
                    ts=ts,
                )
            )
        for key in list(self._active):
            if key in incoming:
                continue
            rule = key.split(":", 1)[0]
            events.append(
                Alert(
                    rule=rule,
                    event="RECOVERED",
                    severity="OK",
                    message=f"{rule} recovered",
                    key=key,
                    ts=ts,
                )
            )
            del self._active[key]
        if events:
            self._save()
        return events
