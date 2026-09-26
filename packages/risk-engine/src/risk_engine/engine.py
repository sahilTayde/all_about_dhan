"""Deterministic pre-trade risk engine. Fail closed: any exception is a veto.

Limits come from config/risk_limits.yaml, re-read on every check so a founder edit (or the
kill switch) applies to the very next order. State (open positions, today's net P&L, last
losing exit, recent approvals, last reconciliation) is rebuilt from the ledger on every
entry check, so a restart loses nothing.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

log = logging.getLogger("risk_engine")

IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_CONFIG_PATH = Path("config/risk_limits.yaml")
MODES = ("paper", "shadow", "limited_live", "live")
LIVE_MODES = ("limited_live", "live")
LIVE_CONFIRM_ENV = "ALL_ABOUT_DHAN_LIVE_CONFIRM"
LIVE_CONFIRM_VALUE = "I_UNDERSTAND_REAL_MONEY"
LIMIT_KEYS = ("max_lots_per_trade", "max_open_positions", "max_daily_loss", "max_loss_per_trade")
TOP_KEYS = ("entry_start_ist", "entry_cutoff_ist", "cooldown_after_loss_minutes", "idempotency_seconds")
ADJUST_ACTIONS = ("EXIT", "MODIFY", "CANCEL", "FLATTEN")


def live_confirmed() -> bool:
    return os.environ.get(LIVE_CONFIRM_ENV) == LIVE_CONFIRM_VALUE


def new_client_order_id() -> str:
    """27 chars of [a-z0-9]; fits Dhan's correlationId (max 30, [a-zA-Z0-9 _-])."""
    return "aad" + uuid.uuid4().hex[:24]


def load_limits(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise ValueError(f"{path}: not a mapping")
    if cfg.get("mode") not in MODES:
        raise ValueError(f"{path}: mode must be one of {MODES}, got {cfg.get('mode')!r}")
    limits = (cfg.get("modes") or {}).get(cfg["mode"]) or {}
    missing = [k for k in LIMIT_KEYS if k not in limits] + [k for k in TOP_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"{path}: missing {missing}")
    return cfg


@dataclass(frozen=True)
class TradeIntent:
    """One order the desk wants to send. Broker-agnostic; instrument_id/exchange are broker ids."""

    symbol: str
    side: str  # BUY | SELL
    lots: int
    lot_size: int
    order_type: str = "MARKET"  # MARKET | LIMIT | SL | SL-M
    price: Optional[float] = None  # limit price (LIMIT, SL, super-order LIMIT entry)
    trigger_price: Optional[float] = None  # SL / SL-M trigger
    decision_price: Optional[float] = None  # LTP when the desk decided (slippage reference)
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_jump: Optional[float] = None
    purpose: str = "ENTRY"  # ENTRY | EXIT
    exit_reason: Optional[str] = None
    instrument_id: str = ""
    exchange: str = "NSE_FNO"
    product_type: str = "INTRADAY"
    trade_id: Optional[str] = None
    client_order_id: str = field(default_factory=new_client_order_id)

    @property
    def qty(self) -> int:
        return self.lots * self.lot_size

    @property
    def fingerprint(self) -> str:
        return f"{self.symbol}|{self.side}|{self.lots}"

    def worst_case_loss(self) -> float:
        """Rupees lost if the stop is hit (BUY without a stop: premium goes to zero)."""
        ref = self.price if self.order_type in ("LIMIT", "SL") and self.price else self.decision_price
        if ref is None or ref <= 0:
            raise ValueError("need price or decision_price to size the risk")
        if self.side == "BUY":
            stop = self.stop_loss if self.stop_loss is not None else 0.0
            if stop >= ref:
                raise ValueError(f"BUY stop_loss {stop} must be below entry {ref}")
            return (ref - stop) * self.qty
        if self.stop_loss is None or self.stop_loss <= ref:
            raise ValueError("SELL entry needs a stop_loss above entry")
        return (self.stop_loss - ref) * self.qty


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    client_order_id: str
    action: str  # ENTRY | EXIT | MODIFY | CANCEL | FLATTEN
    reason_code: str  # OK or the veto code
    reason: str
    ts: datetime
    critical: bool = False


@dataclass
class RiskState:
    open_positions: int = 0
    realized_pnl_today: float = 0.0
    last_loss_exit_at: Optional[datetime] = None
    recent_fingerprints: list[tuple[datetime, str]] = field(default_factory=list)
    used_client_order_ids: set[str] = field(default_factory=set)
    recon_ok: bool = True


class RiskEngine:
    def __init__(self, ledger: Any = None, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.ledger = ledger
        self.config_path = Path(config_path)

    def check_entry(
        self, intent: TradeIntent, now: Optional[datetime] = None, state: Optional[RiskState] = None
    ) -> RiskDecision:
        return self._decide(intent, "ENTRY", now, state)

    def check_exit(self, intent: TradeIntent, action: str = "EXIT", now: Optional[datetime] = None) -> RiskDecision:
        """Exit, modify (price fields only) or cancel. Allowed under kill switch and outside entry hours."""
        return self._decide(intent, action, now, None)

    def check_flatten(self, now: Optional[datetime] = None) -> RiskDecision:
        return self._decide(None, "FLATTEN", now, None)

    def _decide(
        self, intent: Optional[TradeIntent], action: str, now: Optional[datetime], state: Optional[RiskState]
    ) -> RiskDecision:
        now = (now or datetime.now(IST)).astimezone(IST)
        cid = intent.client_order_id if intent else "FLATTEN_ALL"
        try:
            cfg = load_limits(self.config_path)
            if action == "ENTRY":
                code, reason, critical = self._entry_veto(intent, now, cfg, state or self._state(now, cfg))
            else:
                code, reason, critical = self._adjust_veto(intent, action, now, cfg)
        except Exception as exc:  # fail closed
            code, reason, critical = "ENGINE_ERROR", f"{type(exc).__name__}: {exc}", True
        return self._record(RiskDecision(code == "OK", cid, action, code, reason, now, critical), intent)

    def _state(self, now: datetime, cfg: dict[str, Any]) -> RiskState:
        if self.ledger is None:
            raise RuntimeError("no ledger: cannot know open positions or today's P&L")
        return RiskState(**self.ledger.risk_snapshot(now, int(cfg["idempotency_seconds"])))

    @staticmethod
    def _mode_veto(cfg: dict[str, Any]) -> Optional[tuple[str, str, bool]]:
        if cfg["mode"] in LIVE_MODES and not live_confirmed():
            return "MODE_NOT_ENABLED", f"mode {cfg['mode']} is not enabled by the founder ({LIVE_CONFIRM_ENV})", False
        return None

    def _entry_veto(
        self, intent: TradeIntent, now: datetime, cfg: dict[str, Any], st: RiskState
    ) -> tuple[str, str, bool]:
        limits = cfg["modes"][cfg["mode"]]
        mode_veto = self._mode_veto(cfg)
        if mode_veto:
            return mode_veto
        if cfg.get("kill_switch") or (cfg.get("kill_switch_file") and Path(cfg["kill_switch_file"]).exists()):
            return "KILL_SWITCH", "founder kill switch is on", True
        if not st.recon_ok:
            return "RECON_MISMATCH", "last broker reconciliation found a mismatch; resolve it first", True
        if intent.purpose != "ENTRY" or intent.side not in ("BUY", "SELL") or intent.lots <= 0 or intent.lot_size <= 0:
            return "INVALID_INTENT", f"bad entry intent {intent.purpose} {intent.side} {intent.lots}x{intent.lot_size}", False
        start, cutoff = time.fromisoformat(cfg["entry_start_ist"]), time.fromisoformat(cfg["entry_cutoff_ist"])
        if not start <= now.time() < cutoff:
            return "TIME_GATE", f"entries only {start:%H:%M}-{cutoff:%H:%M} IST, now {now:%H:%M:%S}", False
        window = timedelta(seconds=int(cfg["idempotency_seconds"]))
        if intent.client_order_id in st.used_client_order_ids or any(
            fp == intent.fingerprint and now - ts < window for ts, fp in st.recent_fingerprints
        ):
            return "DUPLICATE", f"duplicate of an intent approved in the last {window.seconds}s", False
        if intent.lots > limits["max_lots_per_trade"]:
            return "MAX_LOTS", f"{intent.lots} lots exceeds max_lots_per_trade ({limits['max_lots_per_trade']})", False
        if st.open_positions >= limits["max_open_positions"]:
            return "MAX_OPEN_POSITIONS", f"{st.open_positions} open, max_open_positions {limits['max_open_positions']}", False
        try:
            risk = intent.worst_case_loss()
        except ValueError as exc:
            return "INVALID_INTENT", str(exc), False
        per_trade = abs(float(limits["max_loss_per_trade"]))
        if risk > per_trade:
            return "MAX_LOSS_PER_TRADE", f"risk ₹{risk:,.0f} exceeds max_loss_per_trade ₹{per_trade:,.0f}", False
        daily = abs(float(limits["max_daily_loss"]))
        if st.realized_pnl_today <= -daily:
            return "MAX_DAILY_LOSS", f"daily loss limit hit (₹{st.realized_pnl_today:,.0f} <= -₹{daily:,.0f})", True
        if st.realized_pnl_today - risk < -daily:
            return "MAX_DAILY_LOSS", (
                f"would exceed max_daily_loss: ₹{st.realized_pnl_today:,.0f} - ₹{risk:,.0f} < -₹{daily:,.0f}"
            ), False
        cooldown = timedelta(minutes=float(cfg["cooldown_after_loss_minutes"]))
        if st.last_loss_exit_at and now - st.last_loss_exit_at < cooldown:
            return "COOLDOWN", f"losing exit at {st.last_loss_exit_at:%H:%M:%S}; cooldown {cooldown}", False
        return "OK", "all checks passed", False

    def _adjust_veto(
        self, intent: Optional[TradeIntent], action: str, now: datetime, cfg: dict[str, Any]
    ) -> tuple[str, str, bool]:
        if action not in ADJUST_ACTIONS:
            raise ValueError(f"unknown action {action!r}")
        mode_veto = self._mode_veto(cfg)
        if mode_veto:
            return mode_veto
        if action == "EXIT":
            if intent is None or intent.purpose != "EXIT":
                return "INVALID_INTENT", "exit needs an intent with purpose EXIT", False
            if self.ledger is not None:
                used = self.ledger.risk_snapshot(now, int(cfg["idempotency_seconds"]))["used_client_order_ids"]
                if intent.client_order_id in used:
                    return "DUPLICATE", "exit intent already approved", False
        return "OK", f"{action.lower()} does not add risk", False

    def _record(self, d: RiskDecision, intent: Optional[TradeIntent]) -> RiskDecision:
        level = logging.INFO if d.approved else logging.ERROR if d.critical else logging.WARNING
        log.log(level, "risk %s %s -> %s: %s", d.action, d.client_order_id, d.reason_code, d.reason)
        if self.ledger is None:
            return d
        try:
            self.ledger.record_decision(
                {**asdict(d), "fingerprint": intent.fingerprint if intent else None,
                 "intent": asdict(intent) if intent else None}
            )
        except Exception as exc:  # cannot audit -> cannot approve
            log.error("risk decision not recorded (%s: %s); vetoing", type(exc).__name__, exc)
            return replace(d, approved=False, reason_code="ENGINE_ERROR", reason=f"ledger write failed: {exc}", critical=True)
        return d
