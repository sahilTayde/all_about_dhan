"""USE_EVENT_BUS path for `replay_paper_scalp`: feed -> desk MTM -> boss -> analysts -> desk -> broker -> ledger.

One `EventSession` per replay. Per tick:

    feed   step_context (1m bars, regime, ITM bin, FOLLOWS)  ->  MARKET_TICK
    desk   (priority 10) mark-to-market: fills / stops / targets / overlay exits -> broker + ledger
    boss   (priority 20) REQUEST_VOTES -> ANALYST_VOTE x N -> picker/observer/gates
           -> ENTRY_APPROVED -> desk: founder pause? -> risk engine -> PaperBroker -> ledger
           -> or NO_ENTRY (the gate that skipped)

Needs the synchronous in-memory bus: handlers share this process's engine state and the boss's
decision must see the desk's booking before the next ticket (same as the monolith).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional, Sequence

from desk_ml.persist import code_root

REPLAY_RISK_CONFIG = Path("config") / "risk_limits_replay.yaml"
LIVE_RISK_CONFIG = Path("config") / "risk_limits.yaml"
EVENT_PATH_CONFIG = Path("config") / "event_path.yaml"
ANALYSTS_CONFIG = Path("config") / "analysts.yaml"
CHARGES_CONFIG = Path("config") / "charges.yaml"

# Import names the live loop checks once at startup when USE_EVENT_BUS is on.
EVENT_BUS_PACKAGES = (
    ("ledger", "packages/ledger"),
    ("risk_engine", "packages/risk-engine"),
    ("brokers", "packages/brokers"),
    ("trading_agents_india", "packages/trading_agents_india"),
    ("desk_ml", "packages/desk-ml"),
    ("events", "packages/events"),
    ("analysts", "packages/analysts"),
    ("boss", "packages/boss"),
    ("desk", "packages/desk"),
)
# One command. pip resolves these against each other only when they are installed together.
EVENT_BUS_INSTALL = (
    "pip install -e packages/ledger -e packages/risk-engine -e packages/brokers "
    "-e packages/trading_agents_india -e packages/events -e packages/desk-ml "
    "-e packages/analysts -e packages/boss -e packages/desk"
)


class EventBusStartupError(RuntimeError):
    """USE_EVENT_BUS is on and a Phase 2 package cannot be imported. Raised once, before replay."""


def require_event_packages() -> None:
    """Fail at startup with a readable message if events/boss/desk/analysts are not importable.

    A missing package must not raise ImportError on every replay of the live paper loop.
    """
    missing: list[str] = []
    for name, rel in EVENT_BUS_PACKAGES:
        try:
            __import__(name)
        except ImportError as exc:
            missing.append(f"{name} ({rel}): {exc}")
    if not missing:
        return
    install = EVENT_BUS_INSTALL
    lines = [
        "USE_EVENT_BUS is on but these packages are not installed:",
        *[f"  - {line}" for line in missing],
        "Install them the same way as the other repo packages:",
        f"  {install}",
        "The paper loop stops here instead of crashing on every replay.",
    ]
    raise EventBusStartupError("\n".join(lines))


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def resolve_risk_config(
    *,
    live_session: bool,
    root: Optional[Path] = None,
    settings: Optional[dict[str, Any]] = None,
) -> tuple[Path, bool]:
    """Which risk file this event-bus run uses.

    Replay and parity stay on ``config/risk_limits_replay.yaml``.
    The live paper loop uses ``live_risk_config`` from ``config/event_path.yaml`` when that
    key is set, otherwise the stricter ``config/risk_limits.yaml``. It never falls through
    to the looser replay file unless the key names that file explicitly.

    Returns ``(path, explicit)``. ``explicit`` is true when the live key was present.
    """
    base = code_root() if root is None else Path(root)
    if settings is None:
        path = base / EVENT_PATH_CONFIG
        if not path.is_file():
            path = code_root() / EVENT_PATH_CONFIG
        settings = _read_yaml(path)
    explicit = live_session and "live_risk_config" in settings
    if live_session:
        raw = settings.get("live_risk_config") or str(LIVE_RISK_CONFIG)
    else:
        raw = settings.get("replay_risk_config") or str(REPLAY_RISK_CONFIG)
    chosen = Path(str(raw))
    if not chosen.is_absolute():
        chosen = code_root() / chosen
    return chosen, explicit


def p99(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, math.ceil(0.99 * len(ordered)) - 1)], 3)


class EventSession:
    def __init__(
        self,
        *,
        ledger: Any = None,
        audit: Any = None,
        risk_config: Optional[Path] = None,
        analysts_config: Optional[Path] = None,
        room: Any = None,
        bus: Any = None,
        deterministic: bool = True,
        live_loop: bool = False,
    ) -> None:
        from events import EventAuditLog, MemoryBus

        self._ledger = ledger
        self.audit = audit if audit is not None else EventAuditLog(ledger.conn if ledger is not None else ":memory:")
        self.bus = bus if bus is not None else MemoryBus(self.audit)
        if self.bus.backend != "memory":
            raise ValueError("EventSession needs the synchronous memory bus (see module doc)")
        self.risk_config = Path(risk_config) if risk_config else code_root() / REPLAY_RISK_CONFIG
        self.analysts_config = Path(analysts_config) if analysts_config else code_root() / ANALYSTS_CONFIG
        # Default True: replay and parity do not abstain on wall-clock timeouts.
        # The live paper loop passes deterministic=False.
        self.deterministic = bool(deterministic)
        # True only for the live paper loop. Replays, lab, and parity leave this off
        # so a halt file from today's loop cannot block them.
        self.live_loop = bool(live_loop)
        self._room = room
        self.prior_daily: dict[str, list[dict[str, Any]]] = {}
        self.engine: Any = None
        self.steps: dict[str, Any] = {}
        self.signals: dict[str, dict[str, Any]] = {}
        self.contexts: dict[str, Any] = {}
        self.stacks: dict[str, tuple[Any, Any, Any]] = {}  # underlying -> (ledger, risk engine, broker)

    def attach(self, engine: Any) -> "EventSession":
        from analysts import AnalystRoom
        from boss import Boss
        from desk import Desk

        self.engine = engine
        self.room = self._room if self._room is not None else AnalystRoom.from_config(
            self.analysts_config, deterministic=self.deterministic
        )
        self.desk = Desk(
            self.bus, engine, risk=None, broker=None, steps=self.steps, live_loop=self.live_loop,
        )
        engine._pin_hook = self.desk.adopt_booked  # tickets the live loop carries from an earlier cycle
        self.room.attach(self.bus, self.contexts)
        self.boss = Boss(
            self.bus, engine, steps=self.steps, signals=self.signals, contexts=self.contexts,
            analyst_ids=self.room.analyst_ids, shadow_ids=getattr(self.room, "shadow_ids", ()),
            shadow_cfg=getattr(self.room, "shadow_cfg", None),
        )
        return self

    def use_underlying(self, und: str) -> None:
        """Point the desk at this index's ledger, risk engine and broker.

        ponytail: replay walks one index at a time (all of NIFTY, then SENSEX from 09:15 again),
        so one shared ledger would show SENSEX's 10:00 risk check NIFTY's 14:49 losses (a
        look-ahead in risk state). Each index walk gets its own execution stack; account-wide
        limits across indices need a time-merged multi-index walk (later PR).
        """
        from brokers import attach_ledger
        from desk import ClockedPaperBroker
        from ledger import Ledger
        from risk_engine import RiskEngine

        if self.engine is not None:
            self.engine.shadow_prior_daily = self.prior_daily
        if und not in self.stacks:
            led = self._ledger if self._ledger is not None else Ledger(":memory:", charges_path=code_root() / CHARGES_CONFIG)
            broker = ClockedPaperBroker(clock=lambda: self.desk.clock(), slippage_ticks=0)
            attach_ledger(broker, led)
            root = getattr(self.engine, "root", None) if self.engine is not None else None
            self.stacks[und] = (led, RiskEngine(led, config_path=self.risk_config, root=root), broker)
        _led, self.desk.risk, self.desk.broker = self.stacks[und]

    def set_prior_closes(self, und: str, closes_by_ts: dict[Any, Any]) -> None:
        """Daily bars from sessions before today. Used only by shadow features (ATR14)."""
        from analysts.shadow import daily_ohlc_from_closes

        self.prior_daily[str(und).upper()] = daily_ohlc_from_closes(closes_by_ts or {})

    def ledger_trades(self) -> list[dict[str, Any]]:
        ledgers = {id(led): led for led, _r, _b in self.stacks.values()}
        return [t for led in ledgers.values() for t in led.trades()]

    def step(
        self,
        *,
        underlying: str,
        triples: Sequence[Any],
        i: int,
        ml001_hold: bool,
        ml002_hold: bool,
        follow_gap: bool,
        logit: dict[str, Any],
        logit_xr: dict[str, Any],
        ml1: dict[str, Any],
        tv_side: Optional[str],
        deny_model_signals: bool = True,
    ) -> None:
        """Event-driven twin of `paper_scalp.step_underlying` (same arguments, same engine effects)."""
        from desk_ml.paper_scalp import step_context

        s = step_context(self.engine, underlying=underlying, triples=triples, i=i)
        if s is None:
            return
        self.use_underlying(s.und)
        key = f"{s.und}:{i}"
        self.steps[key] = s
        self.signals[key] = dict(
            ml001_hold=ml001_hold, ml002_hold=ml002_hold, follow_gap=follow_gap, logit=logit, logit_xr=logit_xr,
            ml1=ml1, tv_side=tv_side, deny_model_signals=deny_model_signals,
        )
        try:
            self.bus.publish(
                "MARKET_TICK",
                {"key": key, "underlying": s.und, "i": i, "ts": int(s.tick.ts), "idx_close": float(s.tick.idx_close),
                 "regime": s.classified.get("regime"), "strike": s.strike},
                source="feed",
            )
        finally:
            self.steps.pop(key, None)
            self.signals.pop(key, None)

    def close_leftover(self, pos: Any, *, ltp: float, ts: int, reason: str) -> None:
        from desk.executor import ist

        self.use_underlying(str(pos.underlying).upper())
        self.desk.now_ts, self.desk.now = int(ts), ist(ts)
        self.desk.close(pos, ltp=ltp, ts=ts, reason=reason)

    def founder(self, command: str, underlying: Optional[str] = None) -> str:
        return self.bus.publish("FOUNDER_COMMAND", {"command": command, "underlying": underlying}, source="founder")

    def summary(self) -> dict[str, Any]:
        trades = self.ledger_trades()
        return {
            "backend": self.bus.backend,
            "risk_config": str(self.risk_config),
            "deterministic_analysts": self.deterministic,
            "events": self.audit.counts(),
            "handler_errors": list(self.bus.errors),
            "analysts": self.room.analyst_ids,
            "analyst_stats": dict(self.room.stats),
            "vetoes": list(self.desk.vetoes),
            "ledger_trades_closed": sum(1 for t in trades if t["status"] == "CLOSED"),
            "ledger_trades_cancelled": sum(1 for t in trades if t["status"] == "CANCELLED"),
            "ledger_gross_pnl": round(sum(t["gross_pnl"] for t in trades if t["status"] == "CLOSED"), 2),
            "latency_p99_ms": {
                "boss_decision": p99(self.boss.latency_ms["decision"]),
                "desk_entry": p99(self.desk.latency_ms["entry"]),
                "desk_tick": p99(self.desk.latency_ms["tick"]),
            },
        }

    def close(self) -> None:
        self.room.close()
