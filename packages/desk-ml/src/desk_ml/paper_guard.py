"""Entry guard for the paper engine. Runs inside ``_plan_open``, so flag-off and flag-on both get it.

1. Time-bounded live blocks (``ReplayContext.entry_blocks``): kill switch, halt, corrupt control
   files, history rewrite, a failing engine. Each applies from the moment the live loop first saw
   it, so re-replaying the day reproduces every trade booked before the block.
2. The same ``RiskEngine`` entry rules the event path uses (one implementation), with the
   session's frozen risk limits and state rebuilt as of the ticket's tick across every index.
   The replay walks one index at a time; state as of the tick keeps SENSEX at 10:00 from seeing
   NIFTY's 14:49 losses.

Offline replays have no blocks and no risk config here, so their trades are unchanged.
Exits never pass through this module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

IST = timezone(timedelta(hours=5, minutes=30))
RISK_VETO = "RISK_VETO"


def entry_block(engine: Any, ts: int) -> Optional[tuple[str, str]]:
    ctx = getattr(engine, "ctx", None)
    if ctx is None:
        return None
    hit = ctx.block_at(int(ts))
    if hit is None:
        return None
    kind, from_ts = hit
    since = datetime.fromtimestamp(float(from_ts), IST).isoformat(timespec="seconds")
    return kind, f"new entries blocked since {since} ({kind}); open tickets are still managed"


def state_at(engine: Any, ts: int) -> dict[str, Any]:
    """Open filled positions, today's realized net and last losing exit, as of unix ``ts``."""
    day = datetime.fromtimestamp(int(ts), IST).date()
    open_n, realized, last_loss = 0, 0.0, None
    for row in engine.closed:
        if not row.get("filled"):
            continue
        opened, closed = int(row.get("opened_ts") or 0), int(row.get("closed_ts") or 0)
        if opened <= ts < closed:
            open_n += 1
        if closed <= ts and datetime.fromtimestamp(closed, IST).date() == day:
            net = float(row.get("realized_pnl_inr") or 0.0)
            realized += net
            if net < 0 and (last_loss is None or closed > last_loss):
                last_loss = closed
    for pos in engine.opens.values():
        if pos.filled and int(pos.opened_ts) <= ts:
            open_n += 1
    return {
        "open_positions": open_n,
        "realized_pnl_today": round(realized, 2),
        "last_loss_exit_at": datetime.fromtimestamp(last_loss, IST) if last_loss is not None else None,
    }


def risk_veto(engine: Any, pos: Any) -> Optional[dict[str, Any]]:
    """None when the ticket passes the risk rules; otherwise the veto detail (fail closed)."""
    ctx = getattr(engine, "ctx", None)
    if ctx is None or ctx.risk_config is None:
        return None
    try:
        from risk_engine import RiskEngine, RiskState, TradeIntent

        ts = int(pos.opened_ts)
        intent = TradeIntent(
            symbol=f"{pos.underlying} {pos.atm_strike} {pos.side}", side="BUY", lots=int(pos.lots),
            lot_size=int(pos.lot_size or 0), order_type="LIMIT", price=float(pos.limit_price or pos.entry),
            decision_price=float(pos.entry), stop_loss=float(pos.stop), target=float(pos.target),
            purpose="ENTRY", trade_id=pos.trade_id, client_order_id=f"guard{ts}",
        )
        decision = RiskEngine(None, config_path=ctx.risk_config, root=ctx.root).check_entry(
            intent, now=datetime.fromtimestamp(ts, IST), state=RiskState(**state_at(engine, ts))
        )
    except Exception as exc:  # cannot check -> no trade
        return {"reason_code": "ENGINE_ERROR", "reason_text": f"{type(exc).__name__}: {exc}", "critical": True}
    if decision.approved:
        return None
    return {"reason_code": decision.reason_code, "reason_text": decision.reason, "critical": bool(decision.critical)}
