"""Paper cost model switch: ``legacy`` (today's numbers, byte-identical) or ``realistic``.

realistic (config/paper_costs.yaml; lab 5 cost_audit.md):

- D1 spread/slippage: marketable fills (impulse entries, non-target exits) pay
  ``slippage_pts_per_side`` or half the recorded bid/ask spread, per side. Stop, target and trail
  levels still come from the decision (signal) price, so the trade list does not move; only
  booked money does.
- D3 target: a resting sell limit books the target level, not the (higher) poll print.
- D4 stale quote: an exit is never booked on a quote older than ``exit_quote_max_age_s``. It
  waits for the first fresh print of the held strike (reason kept); at
  ``stale_exit_hard_flatten_ist`` it closes at the last good print as FLATTEN_STALE_QUOTE.
  The exit is never refused.
- D5/D6 fees: SENSEX/BANKEX at the BSE rate; charges come from ``ledger.charges`` per order, so
  engine and ledger agree to the paisa.
- D7/D8 working limits: tick-floored at creation; fill only when a print trades through by a
  tick, and then at the limit.

Paper only. Engines in ``legacy`` never reach the realistic branches below.
"""

from __future__ import annotations

import logging
import math
import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Optional

log = logging.getLogger("desk_ml.costs")

LEGACY = "legacy"
REALISTIC = "realistic"
COST_MODELS = (LEGACY, REALISTIC)
COST_MODEL_ENV = "PAPER_COST_MODEL"
_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"
PAPER_COSTS_PATH = _CONFIG_DIR / "paper_costs.yaml"
CHARGES_PATH = _CONFIG_DIR / "charges.yaml"

DEFAULTS: dict[str, Any] = {
    "cost_model": LEGACY,
    "slippage_pts_per_side": {"default": 0.20, "NIFTY": 0.20, "BANKNIFTY": 0.20, "SENSEX": 0.20},
    "use_recorded_spread": True,
    "tick_size": 0.05,
    "target_fill": "resting_limit",
    "exit_quote_max_age_s": 90,
    "stale_exit_hard_flatten_ist": "15:20",
    "limit_fill": "trade_through",
    "exchange_fees": "per_exchange",
    "entry_latency_ticks": 0,
}
_CHOICES = {
    "target_fill": ("resting_limit", "market_at_poll"),
    "limit_fill": ("trade_through", "touch"),
    "exchange_fees": ("per_exchange", "nse_flat"),
}
STALE_SRCS = frozenset({"LAST_PRINT", "ENTRY_PRINT"})
FLATTEN_STALE_QUOTE = "FLATTEN_STALE_QUOTE"
EXIT_PENDING_NO_QUOTE = "EXIT_PENDING_NO_QUOTE"
_OVERRIDES: ContextVar[dict[str, Any]] = ContextVar("paper_cost_overrides", default={})


# ------------------------------------------------------------------ config


def load_config(path: Optional[Path] = None) -> dict[str, Any]:
    """DEFAULTS < config/paper_costs.yaml < `overrides(...)`. A malformed file raises (money must not
    silently change); a missing file (non-editable install) means DEFAULTS."""
    cfg = {**DEFAULTS, "slippage_pts_per_side": dict(DEFAULTS["slippage_pts_per_side"])}
    p = Path(path) if path is not None else PAPER_COSTS_PATH
    if p.is_file():
        import yaml

        blob = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(blob, dict):
            raise ValueError(f"{p}: expected a mapping")
        cfg.update(blob)
    cfg.update(_OVERRIDES.get())
    if str(cfg["cost_model"]).lower() not in COST_MODELS:
        raise ValueError(f"cost_model must be one of {COST_MODELS}, got {cfg['cost_model']!r}")
    for key, allowed in _CHOICES.items():
        if cfg[key] not in allowed:
            raise ValueError(f"{key} must be one of {allowed}, got {cfg[key]!r}")
    if float(cfg["tick_size"]) <= 0:
        raise ValueError("tick_size must be > 0")
    return cfg


def resolve_cost_model(explicit: Optional[str] = None) -> str:
    """Caller (ReplayContext / replay kwarg) > env PAPER_COST_MODEL > config/paper_costs.yaml."""
    raw = explicit or os.environ.get(COST_MODEL_ENV) or load_config()["cost_model"]
    model = str(raw).strip().lower()
    if model not in COST_MODELS:
        raise ValueError(f"cost_model must be one of {COST_MODELS}, got {raw!r}")
    return model


@contextmanager
def overrides(**kw: Any) -> Iterator[None]:
    """Temporarily override config keys (ablation steps, tests). Unknown keys raise."""
    bad = sorted(set(kw) - set(DEFAULTS))
    if bad:
        raise KeyError(f"unknown cost config keys {bad}")
    token = _OVERRIDES.set({**_OVERRIDES.get(), **kw})
    try:
        yield
    finally:
        _OVERRIDES.reset(token)


def is_realistic(engine: Any) -> bool:
    return getattr(engine, "cost_model", LEGACY) == REALISTIC


def _cs(engine: Any) -> dict[str, Any]:
    """Per-engine realistic state: config snapshot (read once per replay), per-trade fills, alerts."""
    st = engine.cost_state
    if "cfg" not in st:
        st["cfg"] = load_config()
        st["trades"] = {}
        st["alerts"] = []
    return st


def config(engine: Any) -> dict[str, Any]:
    return _cs(engine)["cfg"]


def _trade(engine: Any, pos: Any) -> dict[str, Any]:
    return _cs(engine)["trades"].setdefault(str(pos.trade_id), {})


# ---------------------------------------------------------- ticks and fills


def _ticks(x: float, tick: float) -> float:
    return round(float(x) / tick, 6)  # 230.05 / 0.05 = 4600.999999... must count as 4601


def ceil_tick(x: float, tick: float = 0.05) -> float:
    return round(math.ceil(_ticks(x, tick)) * tick, 2)


def floor_tick(x: float, tick: float = 0.05) -> float:
    return round(math.floor(_ticks(x, tick)) * tick, 2)


def slip_points(underlying: str, cfg: dict[str, Any], spread: Optional[tuple[float, float]] = None) -> float:
    """Adverse points per side: half the recorded spread when present, else the configured table."""
    if spread is not None and cfg.get("use_recorded_spread", True):
        bid, ask = spread
        return max(0.0, (float(ask) - float(bid)) / 2.0)
    table = cfg.get("slippage_pts_per_side") or 0.0
    if not isinstance(table, dict):
        return float(table)
    return float(table.get(str(underlying).upper(), table.get("default", 0.0)))


def entry_fill_price(decision_px: float, slip: float, tick: float = 0.05) -> float:
    """Marketable buy: decision price + slippage, rounded up to the tick (never better)."""
    return ceil_tick(float(decision_px) + float(slip), tick)


def exit_fill_price(decision_px: float, slip: float, tick: float = 0.05) -> float:
    """Marketable sell: decision price - slippage, rounded down to the tick, at least one tick."""
    return floor_tick(max(tick, float(decision_px) - float(slip)), tick)


def _num(raw: Any) -> Optional[float]:
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if math.isfinite(val) else None


def recorded_spread(tick_row: Any, side: str, strike: Any) -> Optional[tuple[float, float]]:
    """(bid, ask) for the held strike from the tape's wing_quotes, when the recorder saved them."""
    wings = getattr(tick_row, "wing_quotes", None)
    k = _num(strike)
    if not isinstance(wings, dict) or k is None:
        return None
    cell = wings.get(str(int(k))) if k == int(k) else None
    cell = cell or wings.get(str(k))
    if not isinstance(cell, dict):
        return None
    key = "ce" if str(side).upper() == "CE" else "pe"
    bid, ask = _num(cell.get(f"{key}_bid")), _num(cell.get(f"{key}_ask"))
    if bid is None or ask is None or bid <= 0 or ask < bid:
        return None
    return bid, ask


def limit_fill_below(engine: Any) -> float:
    """How far below a working buy limit a print must trade to fill it (0 = legacy touch)."""
    if not is_realistic(engine):
        return 0.0
    cfg = config(engine)
    return float(cfg["tick_size"]) if cfg["limit_fill"] == "trade_through" else 0.0


def _minutes_ist(ts: int) -> int:
    return ((int(ts) + 19800) % 86400) // 60


def _hhmm(raw: Any) -> int:
    hh, mm = str(raw).split(":")
    return int(hh) * 60 + int(mm)


# ------------------------------------------------------------ engine hooks


def on_plan_open(engine: Any, pos: Any, tick_row: Any, *, impulse: bool) -> None:
    """New ticket: tick-floor a working buy limit, remember the entry-side cost and the fresh quote."""
    cfg = config(engine)
    tick = float(cfg["tick_size"])
    if not impulse and cfg["limit_fill"] == "trade_through" and pos.limit_price:
        pos.limit_price = floor_tick(pos.limit_price, tick)
    _cs(engine)["trades"][str(pos.trade_id)] = {
        "entry_kind": "market" if impulse else "limit",
        "entry_slip": slip_points(pos.underlying, cfg, recorded_spread(tick_row, pos.side, pos.atm_strike)),
        "fresh_ts": int(tick_row.ts),
        "fresh_px": float(pos.entry),
    }


def on_limit_fill(engine: Any, pos: Any) -> None:
    """Resting buy limit filled on a trade-through: at the limit, never at a better print."""
    pos.entry = float(pos.limit_price or pos.entry)


def on_quote(engine: Any, pos: Any, tick_row: Any, ltp: Optional[float], src: str) -> Optional[str]:
    """Every MTM tick. Returns a reason when a pending exit must close now (fresh print is back, or
    the hard-flatten time passed with the quote still stale)."""
    st = _trade(engine, pos)
    ts = int(tick_row.ts)
    if ltp is not None and src not in STALE_SRCS:
        st["fresh_ts"], st["fresh_px"] = ts, float(ltp)
        st["exit_spread"] = recorded_spread(tick_row, pos.side, pos.atm_strike)
        return st.get("pending")
    if st.get("pending") and _minutes_ist(ts) >= _hhmm(config(engine)["stale_exit_hard_flatten_ist"]):
        return FLATTEN_STALE_QUOTE
    return None


def booked_entry(engine: Any, pos: Any) -> float:
    """Entry price the book (and the desk's ledger) records for this ticket."""
    if not is_realistic(engine):
        return float(pos.entry)
    cfg = config(engine)
    st = _trade(engine, pos)
    if st.get("entry_kind") == "limit":
        return float(pos.entry)
    slip = st.get("entry_slip")
    if slip is None:
        slip = slip_points(pos.underlying, cfg)
    return entry_fill_price(float(pos.entry), float(slip), float(cfg["tick_size"]))


def _alert(engine: Any, kind: str, pos: Any, ts: int, **extra: Any) -> None:
    row = {"kind": kind, "trade_id": pos.trade_id, "underlying": pos.underlying, "side": pos.side,
           "strike": pos.atm_strike, "ts": int(ts), **extra}
    _cs(engine)["alerts"].append(row)
    # ponytail: the board carries the alerts (rewritten, not appended, each live cycle). A persisted
    # once-per-incident HEALTH_ALERT sink is PR-A's AlertSink; route these through it when it lands.
    log.info("paper cost %s %s", kind, row)


@lru_cache(maxsize=4)
def _rates(path: str) -> dict[str, Any]:
    from ledger.charges import load_rates

    return load_rates(Path(path), by_exchange=True)


def ledger_rates(engine: Any) -> Optional[dict[str, Any]]:
    """Per-exchange rates for the event path's in-memory ledger; None keeps its legacy flat rates."""
    if not is_realistic(engine) or config(engine)["exchange_fees"] != "per_exchange":
        return None
    return _rates(str(CHARGES_PATH))


def realistic_charges(underlying: str, qty: Optional[int], buy_px: float, sell_px: float,
                      cfg: dict[str, Any]) -> dict[str, Any]:
    """Round trip = one BUY + one SELL order through ledger.charges (paise per order line)."""
    from ledger.charges import exchange_for, order_charges

    rates = _rates(str(CHARGES_PATH))
    exchange = exchange_for(underlying, rates) if cfg["exchange_fees"] == "per_exchange" else None
    units = int(qty) if qty is not None and int(qty) > 0 else 0
    legs = (order_charges("BUY", units, buy_px, rates, exchange=exchange),
            order_charges("SELL", units, sell_px, rates, exchange=exchange))
    total = {k: round(sum(leg[k] for leg in legs), 2) for k in legs[0]}
    return {
        "brokerage_inr": total["brokerage"],
        "gst_inr": total["gst"],
        "stt_inr": total["stt"],
        "exchange_inr": total["exchange"],
        "sebi_inr": total["sebi"],
        "stamp_inr": total["stamp"],
        "charges_inr": total["total"],
        "n_executed_orders": 2,
        "stt_status": "VERIFY",
        "exchange": exchange or "NSE_FLAT",
    }


def realistic_close(engine: Any, pos: Any, *, ltp: float, ts: int, reason: str, qty: Optional[int],
                    unfilled: bool) -> dict[str, Any]:
    """Booked prices for `_close`. ``{"defer": True}`` = keep the ticket open (EXIT_PENDING_NO_QUOTE).

    Otherwise: ``entry``/``exit`` fill prices, the (possibly rewritten) ``reason``, ``charges``
    (None = the legacy zero-charge row for unfilled tickets) and ``extra`` closed-row keys.
    """
    if unfilled:
        return {"entry": pos.entry, "exit": float(ltp), "reason": reason, "charges": None,
                "extra": {"cost_model": REALISTIC}}
    cfg = config(engine)
    tick = float(cfg["tick_size"])
    st = _trade(engine, pos)
    fresh_ts = int(st.get("fresh_ts", pos.opened_ts))
    fresh_px = st.get("fresh_px")
    age = max(0, int(ts) - fresh_ts)
    max_age = cfg["exit_quote_max_age_s"]
    stale = max_age is not None and age > float(max_age)
    px, src = float(ltp), "PRINT"
    if max_age is not None and reason in ("REPLAY_END", "FLATTEN_1516") and fresh_px is not None:
        px = float(fresh_px)  # held strike's own print, never the tape's ATM column (replay-end leftovers)
    if stale or reason == FLATTEN_STALE_QUOTE:
        hard = _minutes_ist(ts) >= _hhmm(cfg["stale_exit_hard_flatten_ist"])
        if reason not in (FLATTEN_STALE_QUOTE, "REPLAY_END") and not hard:
            if not st.get("pending"):
                st["pending"], st["pending_ts"] = str(reason), int(ts)
                _alert(engine, EXIT_PENDING_NO_QUOTE, pos, ts, reason=str(reason), quote_age_s=age)
            return {"defer": True}
        _alert(engine, FLATTEN_STALE_QUOTE, pos, ts, reason=str(st.get("pending") or reason), quote_age_s=age)
        reason, src = FLATTEN_STALE_QUOTE, "LAST_GOOD_PRINT"
        px = float(fresh_px) if fresh_px is not None else px
    entry = booked_entry(engine, pos)
    if reason == "TARGET" and cfg["target_fill"] == "resting_limit":
        decision_exit = exit_px = min(ceil_tick(float(pos.target), tick), floor_tick(px, tick))
        src = "TARGET_LIMIT"
    else:
        decision_exit = px
        exit_px = exit_fill_price(px, slip_points(pos.underlying, cfg, st.get("exit_spread")), tick)
    units = int(qty) if qty is not None and int(qty) > 0 else 0
    slippage = round(((entry - float(pos.entry)) + (decision_exit - exit_px)) * units, 2)
    extra = {
        "cost_model": REALISTIC,
        "decision_entry": float(pos.entry),
        "decision_exit": round(decision_exit, 4),
        "slippage_inr": slippage,
        "quote_src": src,
        "quote_age_s": age,
    }
    if st.get("pending_ts") is not None:
        extra["exit_pending_since_ts"] = int(st["pending_ts"])
    _cs(engine)["trades"].pop(str(pos.trade_id), None)
    return {"entry": entry, "exit": exit_px, "reason": reason, "extra": extra,
            "charges": realistic_charges(pos.underlying, qty, entry, exit_px, cfg)}


def board_meta(engine: Any) -> dict[str, Any]:
    """The board's `cost_model` block. Legacy: exactly today's Groww overlay description."""
    from desk_ml.groww_costs import as_dict

    meta = as_dict()
    if not is_realistic(engine):
        return meta
    st = _cs(engine)
    cfg = {k: v for k, v in st["cfg"].items() if k != "cost_model"}
    return {**meta, "mode": REALISTIC, "config": cfg, "n_alerts": len(st["alerts"]),
            "alerts": list(st["alerts"][-50:]), "omitted": ["ipf_bse", "clearing", "partial_fills"]}
