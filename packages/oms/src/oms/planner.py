"""V2-08b order planner: chase default, never a MARKET entry. Paper only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any, Protocol

import yaml  # type: ignore[import-untyped]
from brokers.fills import TICK, Quote  # type: ignore[import-untyped, unused-ignore]
from contracts.ids import order_id
from contracts.payloads import Decision, EntryPlan, EntryPlanResult
from events.bus import MemoryBus
from risk_engine.last_good import ConfigInvalid  # type: ignore[import-untyped, unused-ignore]

from oms.router import Account, OrderRouter, Veto


class PlanStore(Protocol):
    """MemoryLedger or SqliteLedgerStore. One plan API; no second ledger."""

    def get_plan(self, plan_id: str) -> dict[str, Any] | None: ...

    def upsert_plan(self, row: dict[str, Any]) -> dict[str, Any]: ...

    def pending_plans(self) -> list[dict[str, Any]]: ...

CHASE_LOOKAHEAD_S = 5.0
SHADOW_ACTIONS = ("LIMIT:fvg", "WAIT")
_MAX_LIVE_QUOTES = 2
_DONE = frozenset({"FILLED", "VETOED", "MISSED"})
_TICK_D = Decimal(str(TICK))


def _repo_root() -> Path:
    """Resolve the checkout from this package, not cwd."""
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "config" / "v2").is_dir() and (candidate / "AGENT.md").is_file():
            return candidate
    return Path.cwd()


def _v2_yaml(*parts: str) -> Path:
    return _repo_root().joinpath("config", "v2", *parts)


ENTRY_YAML = _v2_yaml("entry_location.yaml")
CHASE_YAML = _v2_yaml("entry", "chase_defaults.yaml")


@dataclass(frozen=True)
class CardPolicy:
    """Per-strategy entry card. Defaults come from chase_defaults.yaml (K20)."""

    mode: str = "chase"
    max_chase_ticks: int = 2
    chase_timeout_s: float = 2.0
    zones: tuple[str, ...] = ("fvg", "candle_50")
    chase_calibration: str = ""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entry_config_hash(entry: dict[str, Any], chase: dict[str, Any]) -> str:
    blob = json.dumps({"entry": entry, "chase": chase}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def policy_params_hash(policy: CardPolicy, chase_hash: str) -> str:
    blob = json.dumps(
        {
            "max_chase_ticks": policy.max_chase_ticks,
            "chase_timeout_s": policy.chase_timeout_s,
            "mode": policy.mode,
            "chase_calibration": chase_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def plan_id(account_id: str, decision_id: str, signal_id: str) -> str:
    digest = hashlib.sha256(f"{account_id}|{decision_id}|{signal_id}".encode()).hexdigest()[:20]
    return f"ep_{digest}"


def _as_map(raw: object) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def validate_entry_location(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigInvalid("entry", "entry_location.yaml must be a mapping")
    if raw.get("boss_stretch") != "record_only":
        raise ConfigInvalid("entry", "boss_stretch must be record_only")
    pullback = _as_map(raw.get("pullback_limit"))
    if pullback.get("enabled") and pullback.get("limit_timeout_s") is None:
        raise ConfigInvalid("entry", "pullback_limit.enabled with a null parameter")
    wait = _as_map(raw.get("wait_consolidation"))
    if wait.get("enabled") and (
        wait.get("wait_max_bars") is None or wait.get("consol_max_atr") is None
    ):
        raise ConfigInvalid("entry", "wait_consolidation.enabled with a null parameter")
    return dict(raw)


def validate_chase_defaults(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigInvalid("entry", "chase_defaults.yaml must be a mapping")
    ticks = int(raw.get("max_chase_ticks") or 0)
    timeout = float(raw.get("chase_timeout_s") or 0)
    if ticks < 1 or timeout <= 0:
        raise ConfigInvalid("entry", "chase_defaults ticks/timeout invalid")
    return dict(raw)


class EntryLocationConfig:
    """Last-good loader for entry_location.yaml + chase_defaults.yaml (REG-07, K20)."""

    def __init__(
        self,
        path: Path | None = None,
        chase_path: Path | None = None,
        *,
        bus: MemoryBus | None = None,
    ) -> None:
        self.path = path if path is not None else ENTRY_YAML
        self.chase_path = chase_path if chase_path is not None else CHASE_YAML
        self.bus = bus
        self.last: dict[str, Any] | None = None
        self.chase_last: dict[str, Any] | None = None
        self.chase_hash = ""
        self.config_hash = ""
        self.reload()

    def get(self) -> dict[str, Any]:
        if self.last is None:
            raise ConfigInvalid("entry", "no last-good entry config")
        return self.last

    def chase(self) -> dict[str, Any]:
        if self.chase_last is None:
            raise ConfigInvalid("entry", "no last-good chase defaults")
        return self.chase_last

    def reload(self) -> dict[str, Any]:
        try:
            entry = validate_entry_location(yaml.safe_load(self.path.read_text(encoding="utf-8")))
            chase = validate_chase_defaults(
                yaml.safe_load(self.chase_path.read_text(encoding="utf-8"))
            )
        except ConfigInvalid:
            self._alert("CONFIG_INVALID")
            raise
        except (OSError, yaml.YAMLError, TypeError, ValueError) as exc:
            self._alert(str(exc))
            raise ConfigInvalid("entry", str(exc)) from exc
        self.last = entry
        self.chase_last = chase
        self.chase_hash = file_sha256(self.chase_path)
        self.config_hash = entry_config_hash(entry, chase)
        return entry

    def _alert(self, detail: str) -> None:
        if self.bus is None:
            return
        self.bus.publish(
            "HEALTH_ALERT",
            {"reason_code": "CONFIG_INVALID", "component": "entry", "detail": detail},
            source="oms",
        )


def load_entry_config(
    path: Path | None = None,
    chase_path: Path | None = None,
    *,
    bus: MemoryBus | None = None,
) -> EntryLocationConfig:
    return EntryLocationConfig(path, chase_path, bus=bus)


def snap_ask_up(ask: float | Decimal, tick: Decimal | None = None) -> Decimal:
    """Snap an ask UP onto the tick grid (0.05). Already-on-tick stays."""
    tick_d = tick if tick is not None else _TICK_D
    raw = ask if isinstance(ask, Decimal) else Decimal(str(ask))
    units = (raw / tick_d).to_integral_value(rounding=ROUND_CEILING)
    return units * tick_d


def marketable_limit(ask: float, max_chase_ticks: int, tick: float = TICK) -> float:
    """Ask snapped up to `tick`, plus `max_chase_ticks` ticks. Never above that cap."""
    tick_d = Decimal(str(tick))
    snapped = snap_ask_up(ask, tick_d)
    cap = snapped + Decimal(int(max_chase_ticks)) * tick_d
    priced = min(cap, snapped + Decimal(int(max_chase_ticks)) * tick_d)
    return float(priced)


def stretch_floats(stretch: dict[str, Any] | None) -> dict[str, float]:
    block = stretch or {}
    out: dict[str, float] = {}
    for key in ("zone_atr", "ema20_atr", "twap_atr"):
        raw = block.get(key)
        if raw is not None:
            out[key] = float(raw)
    return out


class OrderPlanner:
    """One marketable LIMIT per ENTER, sent on the first quote after the bar close."""

    def __init__(
        self,
        *,
        clock: Any,
        router: OrderRouter,
        config: EntryLocationConfig,
        store: PlanStore | None = None,
        bus: MemoryBus | None = None,
    ) -> None:
        self.clock = clock
        self.router = router
        self.config = config
        self.store = store if store is not None else router.store
        self.bus = bus if bus is not None else router.bus
        self._live: dict[str, dict[str, Any]] = {}

    def resolve_policy(self, card: CardPolicy | None) -> CardPolicy:
        chase = self.config.chase()
        if card is None:
            return CardPolicy(
                max_chase_ticks=int(chase["max_chase_ticks"]),
                chase_timeout_s=float(chase["chase_timeout_s"]),
                chase_calibration=f"chase_defaults@{self.config.chase_hash[:16]}",
            )
        return card

    def effective_mode(self, policy: CardPolicy) -> str:
        cfg = self.config.get()
        pullback = _as_map(cfg.get("pullback_limit"))
        wait = _as_map(cfg.get("wait_consolidation"))
        if policy.mode == "pullback_limit" and pullback.get("enabled"):
            return "pullback_limit"
        if policy.mode == "wait_consolidation" and wait.get("enabled"):
            return "wait_consolidation"
        return "chase"

    def on_decision(
        self,
        decision: Decision,
        *,
        account: Account,
        signal_id: str,
        bar_close_ts: datetime,
        policy: CardPolicy | None = None,
        zone_price: float | None = None,
        est_delta: float | None = None,
    ) -> dict[str, Any] | None:
        if decision.decision != "ENTER" or not decision.instrument_id:
            return None
        pid = plan_id(account.account_id, decision.decision_id, signal_id)
        held = self.store.get_plan(pid) or self._live.get(pid)
        if held is not None:
            return held
        resolved = self.resolve_policy(policy)
        mode = self.effective_mode(resolved)
        action = {"chase": "CHASE", "pullback_limit": "LIMIT", "wait_consolidation": "WAIT"}[mode]
        loc = decision.entry_location or {}
        nearest = _as_map(loc.get("nearest"))
        zone = nearest.get("zone") if nearest else None
        zprice = zone_price if zone_price is not None else nearest.get("price")
        row: dict[str, Any] = {
            "plan_id": pid,
            "account_id": account.account_id,
            "decision_id": decision.decision_id,
            "signal_id": signal_id,
            "mode": mode,
            "action": action,
            "status": "PENDING",
            "instrument_id": decision.instrument_id,
            "lots": decision.lots,
            "lot_size": decision.lot_size,
            "bar_close_ts": bar_close_ts,
            "policy": resolved,
            "decision": decision,
            "account": account,
            "limit_price": float(zprice)
            if mode == "pullback_limit" and zprice is not None
            else 0.0,
            "zone": zone,
            "zone_price": float(zprice) if zprice is not None else None,
            "entry_distance_atr": loc.get("entry_distance_atr"),
            "signal_candle_atr": loc.get("signal_candle_atr") or 0.0,
            "stretch": decision.stretch or {},
            "est_delta": est_delta,
            "client_order_id": None,
            "sent_at": None,
            "quotes": [],
            "bars_seen": 0,
            "created_at": self.clock.now(),
        }
        self._live[pid] = row
        self.store.upsert_plan(self._persistable(row))
        return row

    def on_quote(self, quote: Quote) -> None:
        now = self.clock.now()
        if quote.available_ts > now:
            return
        sent_now = False
        for row in list(self._live.values()):
            if row["status"] not in ("PENDING", "WORKING", "MISSED_CHASE"):
                continue
            if quote.instrument_id and row["instrument_id"] != quote.instrument_id:
                continue
            if quote.available_ts < row["bar_close_ts"]:
                continue
            held = list(row.get("quotes") or ())
            held.append(quote)
            row["quotes"] = held[-_MAX_LIVE_QUOTES:]
            if quote.ask is not None:
                row["last_ask"] = quote.ask
            if row["status"] == "PENDING" and row["mode"] in ("chase", "pullback_limit"):
                self._send(row, quote)
                sent_now = True
            if row["status"] == "MISSED_CHASE":
                self._note_shadow_ask(row, quote)
        # The send quote prices the limit; later quotes (or a second print) fill.
        # That lets a blown-out book time out instead of always self-filling.
        if not sent_now:
            broker = self.router.broker
            on_depth = getattr(broker, "on_depth", None)
            if callable(on_depth):
                on_depth(quote)
        self._collect_fills()
        self._prune_live()

    def on_bar_close(self) -> None:
        for row in self._live.values():
            if row["status"] == "PENDING" and row["mode"] == "wait_consolidation":
                row["bars_seen"] = int(row["bars_seen"]) + 1

    def on_clock(self) -> None:
        now = self.clock.now()
        cfg = self.config.get()
        for row in list(self._live.values()):
            if row["status"] == "WORKING" and row["mode"] == "chase":
                sent = row.get("sent_at")
                timeout = float(row["policy"].chase_timeout_s)
                if sent is not None and now >= sent + timedelta(seconds=timeout):
                    self._timeout_chase(row)
            if row["status"] == "WORKING" and row["mode"] == "pullback_limit":
                pullback = cfg.get("pullback_limit") or {}
                timeout_s = pullback.get("limit_timeout_s")
                sent = row.get("sent_at") or row["created_at"]
                if timeout_s is not None and now >= sent + timedelta(seconds=float(timeout_s)):
                    self._timeout_limit(row)
            if row["status"] == "PENDING" and row["mode"] == "wait_consolidation":
                wait = cfg.get("wait_consolidation") or {}
                max_bars = wait.get("wait_max_bars")
                if max_bars is not None and int(row["bars_seen"]) >= int(max_bars):
                    self._missed(row, "MISSED")
            if (
                row["status"] == "MISSED_CHASE"
                and row.get("shadow_until") is not None
                and now >= row["shadow_until"]
            ):
                self._finalize_missed_chase(row)
        self._collect_fills()
        self._prune_live()

    def rebuild(self) -> None:
        """REG-04: restore pending plans; never duplicate a live order."""
        for row in self.store.pending_plans():
            pid = str(row["plan_id"])
            if pid in self._live:
                continue
            restored = dict(row)
            restored.setdefault("quotes", [])
            restored.setdefault("bars_seen", 0)
            self._live[pid] = restored

    def _send(self, row: dict[str, Any], quote: Quote) -> None:
        policy: CardPolicy = row["policy"]
        if row["mode"] == "chase":
            if quote.ask is None:
                return
            row["limit_price"] = marketable_limit(quote.ask, policy.max_chase_ticks)
        elif row["limit_price"] <= 0:
            return
        expires = self.clock.now() + timedelta(seconds=float(policy.chase_timeout_s))
        if row["mode"] == "pullback_limit":
            timeout_s = (self.config.get().get("pullback_limit") or {}).get("limit_timeout_s") or 0
            expires = self.clock.now() + timedelta(seconds=float(timeout_s))
        oid = order_id(row["account_id"], row["signal_id"], "entry")
        stretch = stretch_floats(row.get("stretch"))
        plan = EntryPlan(
            plan_id=row["plan_id"],
            decision_id=row["decision_id"],
            signal_id=row["signal_id"],
            account_id=row["account_id"],
            action=row["action"],
            shadow_actions=list(SHADOW_ACTIONS),
            stretch=stretch,
            zone=row.get("zone"),
            zone_price=row.get("zone_price"),
            entry_distance_atr=row.get("entry_distance_atr"),
            signal_candle_atr=float(row.get("signal_candle_atr") or 0.0),
            limit_price=float(row["limit_price"]),
            est_delta=row.get("est_delta"),
            expires_at=expires.isoformat(),
            client_order_id=oid,
        )
        out = self.router.submit(plan, row["decision"], row["account"])
        if isinstance(out, Veto):
            row["status"] = "VETOED"
            row["veto"] = out.reason_code
            self.store.upsert_plan(self._persistable(row))
            self._prune_live()
            return
        row["client_order_id"] = oid
        row["sent_at"] = self.clock.now()
        row["status"] = "WORKING"
        row["expires_at"] = expires
        self.store.upsert_plan(self._persistable(row))
        self.bus.publish("ENTRY_PLAN", plan.__dict__, source="oms")

    def _timeout_chase(self, row: dict[str, Any]) -> None:
        oid = row.get("client_order_id")
        if oid:
            self.router.cancel(str(oid), "TIMEOUT_UNFILLED")
        row["status"] = "MISSED_CHASE"
        row["ask_at_cancel"] = row.get("last_ask")
        row["shadow_until"] = self.clock.now() + timedelta(seconds=CHASE_LOOKAHEAD_S)
        self.store.upsert_plan(self._persistable(row))

    def _timeout_limit(self, row: dict[str, Any]) -> None:
        oid = row.get("client_order_id")
        if oid:
            self.router.cancel(str(oid), "TIMEOUT_UNFILLED")
        self._missed(row, "MISSED")

    def _missed(self, row: dict[str, Any], status: str) -> None:
        row["status"] = status
        chase_px = self._shadow_chase_price(row)
        result = EntryPlanResult(
            plan_id=row["plan_id"],
            status=status,
            shadow={
                "CHASE": {
                    "status": "SHADOW",
                    "fill_price": chase_px,
                    "ask_at_cancel": row.get("last_ask") or row.get("ask_at_cancel"),
                    "pnl_pts": self._shadow_pnl_pts(row, chase_px),
                }
            },
        )
        row["result"] = result
        self.store.upsert_plan(self._persistable(row))
        self.bus.publish("ENTRY_PLAN_RESULT", result.__dict__, source="oms")

    def _note_shadow_ask(self, row: dict[str, Any], quote: Quote) -> None:
        if quote.ask is None or row.get("first_fillable_ask") is not None:
            return
        limit = float(row.get("limit_price") or 0)
        if limit and quote.ask <= limit + 1e-9:
            row["first_fillable_ask"] = quote.ask

    def _finalize_missed_chase(self, row: dict[str, Any]) -> None:
        chase_px = self._shadow_chase_price(row)
        result = EntryPlanResult(
            plan_id=row["plan_id"],
            status="MISSED_CHASE",
            shadow={
                "ask_at_cancel": row.get("ask_at_cancel"),
                "first_fillable_ask_5s": row.get("first_fillable_ask"),
                "chase_price": chase_px,
                "pnl_pts": self._shadow_pnl_pts(row, chase_px),
            },
        )
        row["result"] = result
        row["shadow_until"] = None
        self.store.upsert_plan(self._persistable(row))
        self.bus.publish("ENTRY_PLAN_RESULT", result.__dict__, source="oms")

    def _shadow_chase_price(self, row: dict[str, Any]) -> float | None:
        if row.get("first_fillable_ask") is not None:
            return float(row["first_fillable_ask"])
        if row.get("ask_at_cancel") is not None:
            return float(row["ask_at_cancel"])
        last = row.get("last_ask")
        return float(last) if last is not None else None

    def _shadow_pnl_pts(self, row: dict[str, Any], chase_px: float | None) -> float | None:
        if chase_px is None:
            return None
        mark = row.get("last_ask")
        if mark is None:
            return 0.0
        return round(float(mark) - chase_px, 4)

    def _collect_fills(self) -> None:
        for row in self._live.values():
            oid = row.get("client_order_id")
            if not oid or row["status"] != "WORKING":
                continue
            order = self.router.broker.orders.get(str(oid))
            if order is None:
                continue
            state = getattr(order.state, "value", order.state)
            if state == "FILLED":
                waited = 0.0
                if row.get("sent_at") is not None:
                    waited = (self.clock.now() - row["sent_at"]).total_seconds()
                result = EntryPlanResult(
                    plan_id=row["plan_id"],
                    status="FILLED",
                    fill_price=order.avg_fill_price,
                    filled_at=self.clock.now().isoformat(),
                    waited_s=waited,
                    giveback_5m_pts=None,
                    giveback_5m_atr=None,
                )
                row["status"] = "FILLED"
                row["result"] = result
                self.store.upsert_plan(self._persistable(row))
                self.bus.publish("ENTRY_PLAN_RESULT", result.__dict__, source="oms")

    def _prune_live(self) -> None:
        for pid, row in list(self._live.items()):
            status = str(row.get("status") or "")
            if status in _DONE or (
                status == "MISSED_CHASE"
                and row.get("result") is not None
                and row.get("shadow_until") is None
            ):
                del self._live[pid]

    def _persistable(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "plan_id": row["plan_id"],
            "account_id": row["account_id"],
            "decision_id": row["decision_id"],
            "signal_id": row["signal_id"],
            "mode": row["mode"],
            "action": row["action"],
            "status": row["status"],
            "instrument_id": row.get("instrument_id"),
            "limit_price": row.get("limit_price"),
            "client_order_id": row.get("client_order_id"),
            "created_at": row.get("created_at"),
            "bar_close_ts": row.get("bar_close_ts"),
            "policy": row.get("policy"),
            "decision": row.get("decision"),
            "account": row.get("account"),
            "stretch": row.get("stretch"),
            "zone": row.get("zone"),
            "zone_price": row.get("zone_price"),
            "entry_distance_atr": row.get("entry_distance_atr"),
            "signal_candle_atr": row.get("signal_candle_atr"),
            "est_delta": row.get("est_delta"),
            "lots": row.get("lots"),
            "lot_size": row.get("lot_size"),
            "ask_at_cancel": row.get("ask_at_cancel"),
            "first_fillable_ask": row.get("first_fillable_ask"),
            "sent_at": row.get("sent_at"),
            "bars_seen": row.get("bars_seen", 0),
            "last_ask": row.get("last_ask"),
            "shadow_until": row.get("shadow_until"),
            "result": row.get("result"),
            "veto": row.get("veto"),
        }


# Re-export for tests / boss.
__all__ = [
    "CHASE_LOOKAHEAD_S",
    "CardPolicy",
    "EntryLocationConfig",
    "OrderPlanner",
    "entry_config_hash",
    "file_sha256",
    "load_entry_config",
    "marketable_limit",
    "plan_id",
    "policy_params_hash",
    "snap_ask_up",
    "validate_entry_location",
]
