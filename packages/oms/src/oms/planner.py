"""V2-08b order planner: chase default, never a MARKET entry. Paper only.

Marketable limit = best ask + max_chase_ticks at the first quote after the
signal bar closes. Unfilled after chase_timeout_s -> TIMEOUT_UNFILLED and
MISSED_CHASE with shadow P&L. pullback_limit / wait_consolidation are
implemented but globally disabled. Risk is re-checked at send time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from brokers.fills import Quote
from brokers.orders import Order, OrderState
from contracts.clock import IST
from contracts.ids import order_id
from contracts.payloads import Decision, EntryPlan, EntryPlanResult
from events.bus import MemoryBus
from risk_engine.last_good import ConfigInvalid

from oms.ledger_stub import MemoryLedger
from oms.router import Account, OrderRouter, Veto

ENTRY_ORDER_TYPE = "LIMIT"
CHASE_LOOKAHEAD_S = 5.0
GIVEBACK_S = 300.0
TICK = 0.05
REPO_ENTRY_YAML = Path("config/v2/entry_location.yaml")
REPO_CHASE_YAML = Path("config/v2/entry/chase_defaults.yaml")


def _aware(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("planner timestamps must be timezone-aware IST")
    return ts.astimezone(IST)


def _iso(ts: datetime) -> str:
    return _aware(ts).isoformat()


def _sha16(payload: object) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def marketable_limit(ask: float, max_chase_ticks: int, tick_size: float = TICK) -> float:
    """Best ask + max_chase_ticks. Never a market order."""
    return round(float(ask) + int(max_chase_ticks) * float(tick_size), 2)


def policy_params_hash(
    *,
    max_chase_ticks: int,
    chase_timeout_s: float,
    chase_calibration: str,
    mode: str,
) -> str:
    """Resolved entry-policy hash (REG-13). A per-card override changes this."""
    return _sha16(
        {
            "max_chase_ticks": int(max_chase_ticks),
            "chase_timeout_s": float(chase_timeout_s),
            "chase_calibration": chase_calibration,
            "mode": mode,
        }
    )


def plan_id(decision_id: str, signal_id: str) -> str:
    if "|" in decision_id or "|" in signal_id:
        raise ValueError("plan_id inputs must not contain '|'")
    digest = hashlib.sha256(f"{decision_id}|{signal_id}|plan".encode()).hexdigest()[:16]
    return f"ep_{digest}"


def shadow_pnl_pts(fill_price: float, mark: float) -> float:
    """Long-option shadow P&L in premium points (mark − fill)."""
    return round(float(mark) - float(fill_price), 4)


@dataclass(frozen=True)
class ChaseDefaults:
    """Hashed `chase_defaults.yaml` (K20)."""

    version: str
    max_chase_ticks: int
    chase_timeout_s: float
    tick_size: float
    file_sha256: str

    @property
    def calibration(self) -> str:
        return f"chase_defaults@{self.file_sha256}"


@dataclass(frozen=True)
class EntryLocationConfig:
    """Validated `entry_location.yaml` plus hashed chase defaults."""

    boss_stretch: str
    default_entry_policy: str
    chase: ChaseDefaults
    pullback_enabled: bool
    limit_timeout_s: float | None
    wait_enabled: bool
    consol_max_atr: float | None
    wait_max_bars: int | None
    zones: tuple[str, ...]
    raw: dict[str, Any]
    config_hash: str


@dataclass(frozen=True)
class CardPolicy:
    """Per-strategy-card entry policy. None fields inherit chase defaults."""

    mode: str = "chase"
    max_chase_ticks: int | None = None
    chase_timeout_s: float | None = None
    zones: tuple[str, ...] = ("fvg", "candle_50")


@dataclass(frozen=True)
class ResolvedPolicy:
    """Desk entry mode after global enables + per-card overrides."""

    mode: str
    max_chase_ticks: int
    chase_timeout_s: float
    chase_calibration: str
    tick_size: float
    limit_timeout_s: float | None
    wait_max_bars: int | None
    consol_max_atr: float | None
    zones: tuple[str, ...]
    params_hash: str


def load_chase_defaults(path: Path | None = None) -> ChaseDefaults:
    target = path if path is not None else REPO_CHASE_YAML
    raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigInvalid("entry", "chase_defaults.yaml must be a mapping")
    return ChaseDefaults(
        version=str(raw.get("version") or "1.0.0"),
        max_chase_ticks=int(raw["max_chase_ticks"]),
        chase_timeout_s=float(raw["chase_timeout_s"]),
        tick_size=float(raw.get("tick_size") or TICK),
        file_sha256=file_sha256(target),
    )


def _require_mode_params(name: str, enabled: bool, params: dict[str, Any]) -> None:
    if not enabled:
        return
    missing = [k for k, v in params.items() if v is None]
    if missing:
        raise ConfigInvalid(
            "entry", f"{name} enabled with null parameter(s): {', '.join(missing)}"
        )


def load_entry_location(
    path: Path | None = None, *, chase_path: Path | None = None
) -> EntryLocationConfig:
    """Load and validate entry-location YAML. Invalid → ConfigInvalid (REG-07)."""
    target = path if path is not None else REPO_ENTRY_YAML
    raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigInvalid("entry", "entry_location.yaml must be a mapping")
    stretch = str(raw.get("boss_stretch") or "")
    if stretch != "record_only":
        raise ConfigInvalid("entry", f"boss_stretch must be record_only, got {stretch!r}")
    pull = dict(raw.get("pullback_limit") or {})
    wait = dict(raw.get("wait_consolidation") or {})
    pull_on = bool(pull.get("enabled", False))
    wait_on = bool(wait.get("enabled", False))
    _require_mode_params("pullback_limit", pull_on, {"limit_timeout_s": pull.get("limit_timeout_s")})
    _require_mode_params(
        "wait_consolidation",
        wait_on,
        {"consol_max_atr": wait.get("consol_max_atr"), "wait_max_bars": wait.get("wait_max_bars")},
    )
    chase_src = chase_path
    if chase_src is None:
        listed = raw.get("chase_defaults")
        chase_src = Path(str(listed)) if listed else REPO_CHASE_YAML
    chase = load_chase_defaults(chase_src)
    policy = str(raw.get("default_entry_policy") or "chase")
    zones = tuple(str(z) for z in (raw.get("zones") or ("fvg", "candle_50")))
    cfg_hash = _sha16({"entry_location": raw, "chase_defaults": asdict(chase)})
    return EntryLocationConfig(
        boss_stretch=stretch,
        default_entry_policy=policy,
        chase=chase,
        pullback_enabled=pull_on,
        limit_timeout_s=float(pull["limit_timeout_s"]) if pull_on else None,
        wait_enabled=wait_on,
        consol_max_atr=float(wait["consol_max_atr"]) if wait_on else None,
        wait_max_bars=int(wait["wait_max_bars"]) if wait_on else None,
        zones=zones,
        raw=raw,
        config_hash=cfg_hash,
    )


class EntryConfigStore:
    """Last-good entry-location config. Bad YAML raises CONFIG_INVALID (REG-07)."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        chase_path: Path | None = None,
        bus: MemoryBus | None = None,
    ) -> None:
        self.path = path if path is not None else REPO_ENTRY_YAML
        self.chase_path = chase_path
        self.bus = bus
        self.last: EntryLocationConfig | None = None

    def get(self) -> EntryLocationConfig:
        try:
            cfg = load_entry_location(self.path, chase_path=self.chase_path)
        except (ConfigInvalid, OSError, TypeError, KeyError, ValueError, yaml.YAMLError) as exc:
            detail = f"{type(exc).__name__}: {exc}"
            if self.bus is not None:
                self.bus.publish(
                    "HEALTH_ALERT",
                    {"reason_code": "CONFIG_INVALID", "component": "entry", "detail": detail},
                    source="oms",
                )
            if isinstance(exc, ConfigInvalid):
                raise
            raise ConfigInvalid("entry", detail) from exc
        self.last = cfg
        return cfg


def resolve_policy(cfg: EntryLocationConfig, card: CardPolicy | None = None) -> ResolvedPolicy:
    """Global disable wins: pullback/wait stay chase unless the test config enables them."""
    requested = (card.mode if card is not None else cfg.default_entry_policy) or "chase"
    if requested == "pullback_limit" and cfg.pullback_enabled:
        mode = "pullback_limit"
    elif requested == "wait_consolidation" and cfg.wait_enabled:
        mode = "wait_consolidation"
    else:
        mode = "chase"
    if cfg.default_entry_policy == "pullback_limit" and cfg.pullback_enabled and card is None:
        mode = "pullback_limit"
    if cfg.default_entry_policy == "wait_consolidation" and cfg.wait_enabled and card is None:
        mode = "wait_consolidation"
    ticks = cfg.chase.max_chase_ticks
    timeout = cfg.chase.chase_timeout_s
    if card is not None and card.max_chase_ticks is not None:
        ticks = int(card.max_chase_ticks)
    if card is not None and card.chase_timeout_s is not None:
        timeout = float(card.chase_timeout_s)
    zones = card.zones if card is not None else cfg.zones
    return ResolvedPolicy(
        mode=mode,
        max_chase_ticks=ticks,
        chase_timeout_s=timeout,
        chase_calibration=cfg.chase.calibration,
        tick_size=cfg.chase.tick_size,
        limit_timeout_s=cfg.limit_timeout_s,
        wait_max_bars=cfg.wait_max_bars,
        consol_max_atr=cfg.consol_max_atr,
        zones=zones,
        params_hash=policy_params_hash(
            max_chase_ticks=ticks,
            chase_timeout_s=timeout,
            chase_calibration=cfg.chase.calibration,
            mode=mode,
        ),
    )


def _zone_name(nearest: dict[str, Any], stretch: dict[str, Any]) -> str | None:
    if nearest.get("zone"):
        return str(nearest["zone"])
    zone = stretch.get("zone")
    return str(zone) if isinstance(zone, str) else None


def _opt_float(value: object) -> float | None:
    return float(value) if value is not None else None


def _action_name(mode: str) -> str:
    if mode == "pullback_limit":
        return "LIMIT"
    if mode == "wait_consolidation":
        return "WAIT"
    return "CHASE"


def _shadow_actions(mode: str) -> list[str]:
    taken = _action_name(mode)
    catalog = ("CHASE", "LIMIT:fvg", "WAIT")
    skip = "LIMIT:fvg" if taken == "LIMIT" else taken
    return [name for name in catalog if name != skip]


@dataclass
class LivePlan:
    """In-flight entry plan. Rebuilt from the ledger after restart (REG-04)."""

    plan: EntryPlan
    policy: ResolvedPolicy
    decision: Decision
    account_id: str
    bar_close_ts: datetime
    status: str
    client_order_id: str
    sent_at: datetime | None = None
    ask_at_send: float | None = None
    ask_at_cancel: float | None = None
    asks_after_cancel: list[tuple[datetime, float]] = field(default_factory=list)
    bars_waited: int = 0
    fill_price: float | None = None
    filled_at: datetime | None = None
    result: EntryPlanResult | None = None
    last_quote_ask: float | None = None

    def to_row(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan.plan_id,
            "status": self.status,
            "signal_id": self.plan.signal_id,
            "decision": asdict(self.decision),
            "policy": asdict(self.policy),
            "bar_close_ts": _iso(self.bar_close_ts),
            "account_id": self.account_id,
            "client_order_id": self.client_order_id,
            "sent_at": _iso(self.sent_at) if self.sent_at else None,
            "bars_waited": self.bars_waited,
            "plan": asdict(self.plan),
            "ask_at_send": self.ask_at_send,
            "ask_at_cancel": self.ask_at_cancel,
        }


class OrderPlanner:
    """One marketable LIMIT entry per ENTER signal. Risk at send. Paper only."""

    def __init__(
        self,
        *,
        clock: Any,
        router: OrderRouter,
        store: MemoryLedger | None = None,
        bus: MemoryBus | None = None,
        config: EntryLocationConfig | None = None,
        config_store: EntryConfigStore | None = None,
        account_id: str = "founder",
    ) -> None:
        self.clock = clock
        self.router = router
        self.store = store if store is not None else router.store
        self.bus = bus if bus is not None else router.bus
        self.config_store = config_store
        self.config = config if config is not None else (
            config_store.get() if config_store is not None else load_entry_location()
        )
        self.account_id = account_id
        self._plans: dict[str, LivePlan] = {}
        self._by_signal: dict[str, str] = {}

    def rebuild(self) -> int:
        """Restore pending/sent plans from the ledger. Never duplicates (REG-04)."""
        restored = 0
        for row in self.store.pending_plans():
            pid = str(row["plan_id"])
            if pid in self._plans:
                continue
            live = _live_from_row(row)
            self._plans[pid] = live
            self._by_signal[live.plan.signal_id] = pid
            restored += 1
        return restored

    def accept(
        self,
        decision: Decision,
        *,
        card: CardPolicy | None = None,
        bar_close_ts: datetime | None = None,
    ) -> EntryPlan | None:
        """Register one plan per signal. HOLD is ignored. Duplicate signal is a no-op."""
        if decision.decision != "ENTER":
            return None
        if not decision.signal_ids:
            return None
        signal_id = decision.signal_ids[0]
        existing = self._by_signal.get(signal_id)
        if existing is not None:
            return self._plans[existing].plan
        cfg = self.config_store.get() if self.config_store is not None else self.config
        if self.config_store is not None:
            self.config = cfg
        policy = resolve_policy(cfg, card)
        now = _aware(self.clock.now())
        close_ts = _aware(bar_close_ts) if bar_close_ts is not None else now
        oid = order_id(self.account_id, signal_id, "entry")
        loc = decision.entry_location or {}
        nearest = loc.get("nearest") if isinstance(loc.get("nearest"), dict) else {}
        stretch = decision.stretch or {}
        stretch_floats = {
            key: float(stretch[key])
            for key in ("zone_atr", "ema20_atr", "twap_atr")
            if stretch.get(key) is not None
        }
        timeout = policy.chase_timeout_s
        if policy.mode == "pullback_limit" and policy.limit_timeout_s is not None:
            timeout = policy.limit_timeout_s
        expires = now + timedelta(seconds=float(timeout))
        plan = EntryPlan(
            plan_id=plan_id(decision.decision_id, signal_id),
            decision_id=decision.decision_id,
            signal_id=signal_id,
            account_id=self.account_id,
            action=_action_name(policy.mode),
            shadow_actions=_shadow_actions(policy.mode),
            stretch=stretch_floats,
            zone=_zone_name(nearest, stretch),
            zone_price=float(nearest["price"]) if nearest.get("price") is not None else None,
            entry_distance_atr=_opt_float(loc.get("entry_distance_atr")),
            signal_candle_atr=float(loc.get("signal_candle_atr") or 0.0),
            limit_price=float(decision.limit_price or 0.0),
            est_delta=None,
            expires_at=_iso(expires),
            client_order_id=oid,
        )
        status = "WAITING" if policy.mode == "wait_consolidation" else "PENDING"
        live = LivePlan(
            plan=plan,
            policy=policy,
            decision=decision,
            account_id=self.account_id,
            bar_close_ts=close_ts,
            status=status,
            client_order_id=oid,
        )
        self._plans[plan.plan_id] = live
        self._by_signal[signal_id] = plan.plan_id
        self.store.upsert_plan(live.to_row())
        self.bus.publish("ENTRY_PLAN", asdict(plan), source="oms")
        return plan

    def on_quote(self, quote: Quote) -> list[EntryPlanResult]:
        """First post-close quote sends the chase/limit. Later quotes fill, shadow, give-back."""
        now = _aware(self.clock.now())
        qts = _aware(quote.available_ts)
        if qts > now:
            return []
        results: list[EntryPlanResult] = []
        if quote.ask is not None:
            for live in self._plans.values():
                live.last_quote_ask = float(quote.ask)
                if live.status in {"MISSED_CHASE", "MISSED"} and live.ask_at_cancel is not None:
                    elapsed = (qts - (live.sent_at or qts)).total_seconds()
                    if elapsed <= live.policy.chase_timeout_s + CHASE_LOOKAHEAD_S:
                        live.asks_after_cancel.append((qts, float(quote.ask)))
                        self._refresh_missed_shadow(live)
        for live in list(self._plans.values()):
            if live.status == "PENDING" and qts >= live.bar_close_ts:
                sent = self._send(live, quote)
                if sent is not None:
                    results.append(sent)
            if live.status == "SENT":
                filled = self._check_fill(live)
                if filled is not None:
                    results.append(filled)
            if live.status == "FILLED" and live.filled_at is not None:
                self._maybe_giveback(live, quote, now)
        self._feed_quote(quote)
        for live in list(self._plans.values()):
            if live.status == "SENT":
                filled = self._check_fill(live)
                if filled is not None:
                    results.append(filled)
        return results

    def on_clock(self) -> list[EntryPlanResult]:
        """Chase / pullback timeouts. Cancel TIMEOUT_UNFILLED; record MISSED_*."""
        now = _aware(self.clock.now())
        results: list[EntryPlanResult] = []
        for live in list(self._plans.values()):
            if live.status != "SENT" or live.sent_at is None:
                continue
            limit_s = (
                live.policy.limit_timeout_s
                if live.policy.mode == "pullback_limit"
                else live.policy.chase_timeout_s
            )
            if limit_s is None:
                continue
            if (now - live.sent_at).total_seconds() + 1e-9 >= float(limit_s):
                got = self._timeout(live, now)
                if got is not None:
                    results.append(got)
        return results

    def on_bar(self) -> list[EntryPlanResult]:
        """wait_consolidation: one closed bar. Expiry after wait_max_bars is MISSED."""
        results: list[EntryPlanResult] = []
        for live in list(self._plans.values()):
            if live.status != "WAITING":
                continue
            live.bars_waited += 1
            max_bars = live.policy.wait_max_bars or 0
            if live.bars_waited >= max_bars:
                results.append(self._miss(live, "MISSED", extra={"reason": "WAIT_EXPIRED"}))
            else:
                self.store.upsert_plan(live.to_row())
        return results

    def _send(self, live: LivePlan, quote: Quote) -> EntryPlanResult | None:
        if live.policy.mode == "wait_consolidation":
            return None
        ask = quote.ask
        if live.policy.mode == "chase":
            if ask is None:
                return None
            limit = marketable_limit(ask, live.policy.max_chase_ticks, live.policy.tick_size)
            live.ask_at_send = float(ask)
        else:
            limit = float(live.decision.limit_price or live.plan.limit_price)
        live.plan = replace(live.plan, limit_price=limit)
        if ENTRY_ORDER_TYPE != "LIMIT":  # pragma: no cover — guard against edits
            raise RuntimeError("V2-08b: entry orders must be LIMIT, never MARKET")
        out = self.router.submit(live.plan, live.decision, Account(live.account_id))
        live.sent_at = _aware(self.clock.now())
        if isinstance(out, Veto):
            return self._miss(
                live,
                "CANCELLED",
                extra={"reason": out.reason_code, "veto": out.reason},
            )
        live.status = "SENT"
        self.store.upsert_plan(live.to_row())
        self._feed_quote(quote)
        return self._check_fill(live)

    def _check_fill(self, live: LivePlan) -> EntryPlanResult | None:
        order = self.router.broker.orders.get(live.client_order_id)
        if order is None or order.state != OrderState.FILLED:
            return None
        price = float(order.avg_price or live.plan.limit_price)
        ts = _aware(self.clock.now())
        live.status = "FILLED"
        live.fill_price = price
        live.filled_at = ts
        waited = (ts - live.sent_at).total_seconds() if live.sent_at else 0.0
        result = EntryPlanResult(
            plan_id=live.plan.plan_id,
            status="FILLED",
            fill_price=price,
            filled_at=_iso(ts),
            waited_s=waited,
            shadow=None,
        )
        live.result = result
        self.store.upsert_plan(live.to_row())
        self.bus.publish("ENTRY_PLAN_RESULT", asdict(result), source="oms")
        return result

    def _timeout(self, live: LivePlan, now: datetime) -> EntryPlanResult:
        self.router.cancel(live.client_order_id, "TIMEOUT_UNFILLED")
        live.ask_at_cancel = live.last_quote_ask
        status = "MISSED_CHASE" if live.policy.mode == "chase" else "MISSED"
        extra: dict[str, Any] = {
            "cancel_reason": "TIMEOUT_UNFILLED",
            "best_ask_at_cancel": live.ask_at_cancel,
        }
        if status == "MISSED":
            extra["shadow_chase"] = self._chase_shadow(live)
        return self._miss(live, status, extra=extra, now=now)

    def _chase_shadow(self, live: LivePlan) -> dict[str, Any]:
        ask = live.ask_at_send if live.ask_at_send is not None else live.last_quote_ask
        if ask is None:
            return {}
        fill = marketable_limit(ask, live.policy.max_chase_ticks, live.policy.tick_size)
        mark = live.last_quote_ask if live.last_quote_ask is not None else fill
        return {
            "shadow_fill_price": fill,
            "shadow_pnl_pts": shadow_pnl_pts(fill, mark),
        }

    def _refresh_missed_shadow(self, live: LivePlan) -> None:
        if live.result is None or not live.asks_after_cancel:
            return
        first_ask = live.asks_after_cancel[0][1]
        last_ask = live.asks_after_cancel[-1][1]
        shadow = dict(live.result.shadow or {})
        shadow["first_fillable_ask_5s"] = first_ask
        shadow["shadow_fill_price"] = first_ask
        shadow["shadow_pnl_pts"] = shadow_pnl_pts(first_ask, last_ask)
        live.result = replace(live.result, shadow=shadow)

    def _miss(
        self,
        live: LivePlan,
        status: str,
        *,
        extra: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> EntryPlanResult:
        ts = _aware(now or self.clock.now())
        live.status = status
        shadow = dict(extra or {})
        if status == "MISSED_CHASE":
            first = live.asks_after_cancel[0][1] if live.asks_after_cancel else None
            mark = live.asks_after_cancel[-1][1] if live.asks_after_cancel else live.ask_at_cancel
            fill = first if first is not None else live.ask_at_cancel
            pnl = (
                shadow_pnl_pts(fill, mark)
                if fill is not None and mark is not None
                else None
            )
            shadow.update(
                {
                    "best_ask_at_cancel": live.ask_at_cancel,
                    "first_fillable_ask_5s": first,
                    "shadow_fill_price": fill,
                    "shadow_pnl_pts": pnl,
                }
            )
        elif status == "MISSED" and "shadow_chase" not in shadow:
            shadow["shadow_chase"] = self._chase_shadow(live)
        waited = (ts - live.sent_at).total_seconds() if live.sent_at else None
        result = EntryPlanResult(
            plan_id=live.plan.plan_id,
            status=status,
            fill_price=None,
            filled_at=None,
            waited_s=waited,
            shadow=shadow,
        )
        live.result = result
        self.store.upsert_plan(live.to_row())
        self.bus.publish("ENTRY_PLAN_RESULT", asdict(result), source="oms")
        return result

    def _maybe_giveback(self, live: LivePlan, quote: Quote, now: datetime) -> None:
        if live.filled_at is None or live.result is None or live.fill_price is None:
            return
        if (now - live.filled_at).total_seconds() < GIVEBACK_S:
            return
        mark = quote.bid if quote.bid is not None else quote.ask
        if mark is None:
            return
        pts = round(live.fill_price - float(mark), 4)
        loc = live.decision.entry_location or {}
        atr = float(loc["atr"]) if loc.get("atr") else None
        live.result = replace(
            live.result,
            giveback_5m_pts=pts,
            giveback_5m_atr=round(pts / atr, 4) if atr else None,
        )

    def _feed_quote(self, quote: Quote) -> None:
        on_depth = getattr(self.router.broker, "on_depth", None)
        if callable(on_depth):
            on_depth(quote)

    def plan(self, signal_id: str) -> LivePlan | None:
        pid = self._by_signal.get(signal_id)
        return self._plans.get(pid) if pid else None

    def results(self) -> list[EntryPlanResult]:
        return [p.result for p in self._plans.values() if p.result is not None]


def _live_from_row(row: dict[str, Any]) -> LivePlan:
    plan_raw = dict(row["plan"])
    dec_raw = dict(row["decision"])
    pol_raw = dict(row["policy"])
    if isinstance(pol_raw.get("zones"), list):
        pol_raw["zones"] = tuple(pol_raw["zones"])
    plan = EntryPlan(**plan_raw)
    decision = Decision(**dec_raw)
    policy = ResolvedPolicy(**pol_raw)
    bar_close = datetime.fromisoformat(str(row["bar_close_ts"]))
    sent_raw = row.get("sent_at")
    return LivePlan(
        plan=plan,
        policy=policy,
        decision=decision,
        account_id=str(row.get("account_id") or plan.account_id),
        bar_close_ts=bar_close,
        status=str(row["status"]),
        client_order_id=str(row.get("client_order_id") or plan.client_order_id),
        sent_at=datetime.fromisoformat(str(sent_raw)) if sent_raw else None,
        bars_waited=int(row.get("bars_waited") or 0),
        ask_at_send=float(row["ask_at_send"]) if row.get("ask_at_send") is not None else None,
        ask_at_cancel=float(row["ask_at_cancel"]) if row.get("ask_at_cancel") is not None else None,
    )
