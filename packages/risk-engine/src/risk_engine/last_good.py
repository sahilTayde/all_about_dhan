"""Last-good YAML/rates for V2 risk and cost configs. Fail closed; never crash."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from risk_engine.engine import (
    LIVE_MODES,
    RiskDecision,
    RiskEngine,
    TradeIntent,
    load_limits,
)

log = logging.getLogger("risk_engine.v2")

Loader = Callable[[Path], dict[str, Any]]


class ConfigInvalid(Exception):
    """Raised when no valid config exists (start-up) or to signal CONFIG_INVALID."""

    def __init__(self, component: str, detail: str) -> None:
        self.component = component
        self.detail = detail
        super().__init__(f"CONFIG_INVALID({component}): {detail}")


class LastGood:
    """Keep the last file that validated. Bad YAML blocks entries; exits use last-good."""

    def __init__(
        self,
        path: Path,
        loader: Loader,
        *,
        component: str,
        bus: Any | None = None,
    ) -> None:
        self.path = Path(path)
        self.loader = loader
        self.component = component
        self.bus = bus
        self.last: dict[str, Any] | None = None
        self.entries_blocked = False
        self.exits_only = False
        self._alerted = False

    def _alert(self, detail: str) -> None:
        if self._alerted:
            return
        self._alerted = True
        log.critical("CONFIG_INVALID(%s): %s", self.component, detail)
        if self.bus is not None:
            self.bus.publish(
                "HEALTH_ALERT",
                {
                    "reason_code": "CONFIG_INVALID",
                    "component": self.component,
                    "detail": detail,
                },
                source="risk",
            )

    def get(self) -> dict[str, Any] | None:
        try:
            cfg = self.loader(self.path)
        except (ValueError, OSError, TypeError, KeyError, yaml.YAMLError) as exc:
            detail = f"{type(exc).__name__}: {exc}"
            self._alert(detail)
            if self.last is not None:
                self.entries_blocked = True
                return self.last
            self.exits_only = True
            self.entries_blocked = True
            return None
        self.last = cfg
        self.entries_blocked = False
        self.exits_only = False
        self._alerted = False
        return cfg


class V2RiskEngine:
    """Risk wrap: engine clock, last-good YAML, paper-only (live modes always vetoed)."""

    def __init__(
        self,
        ledger: Any = None,
        config_path: Path | None = None,
        *,
        bus: Any | None = None,
        root: Path | None = None,
    ) -> None:
        from risk_engine.engine import DEFAULT_CONFIG_PATH

        path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
        self.inner = RiskEngine(ledger=ledger, config_path=path, root=root)
        self.limits = LastGood(path, load_limits, component="risk", bus=bus)
        self.bus = bus
        self.limits.get()  # prime last-good; None means exits-only

    def check_entry(
        self, intent: TradeIntent, now: Any = None, state: Any = None
    ) -> RiskDecision:
        from datetime import datetime

        from risk_engine.engine import IST

        ts = now if now is not None else datetime.now(IST)
        cfg = self.limits.get()
        if cfg is None or self.limits.entries_blocked or self.limits.exits_only:
            return RiskDecision(
                False,
                intent.client_order_id,
                "ENTRY",
                "CONFIG_INVALID",
                "risk config invalid; entries blocked (last-good/exits-only)",
                ts,
                True,
            )
        if cfg.get("mode") in LIVE_MODES:
            return RiskDecision(
                False,
                intent.client_order_id,
                "ENTRY",
                "MODE_NOT_ENABLED",
                "V2 paper-only: live modes cannot be enabled from tests or default config",
                ts,
                True,
            )
        return self.inner.check_entry(intent, now=ts, state=state)

    def check_exit(
        self, intent: TradeIntent, action: str = "EXIT", now: Any = None
    ) -> RiskDecision:
        self.limits.get()  # refresh; ignore failure — last-good or inner degraded path
        return self.inner.check_exit(intent, action, now)

    def check_flatten(self, now: Any = None) -> RiskDecision:
        self.limits.get()
        return self.inner.check_flatten(now)
