"""Paper-only demo: open, add, partial, full close through the V2-09 manager."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from contracts.ids import order_id
from contracts.payloads import (
    CatastrophicStop,
    Decision,
    EntryPlan,
    ExitPlan,
    Level,
    Partial,
)
from events.bus import MemoryBus
from risk_engine import IST, V2RiskEngine

from oms import Account, MemoryLedger, OrderRouter, PositionManager, Veto

INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
START = datetime(2026, 9, 28, 10, 1, tzinfo=IST)


def _plan(signal_id: str, plan_id: str, decision_id: str, limit: float = 151.40) -> EntryPlan:
    return EntryPlan(
        plan_id=plan_id,
        decision_id=decision_id,
        signal_id=signal_id,
        account_id="founder",
        action="CHASE",
        shadow_actions=[],
        stretch={"zone_atr": 1.0, "ema20_atr": 1.0, "twap_atr": 1.0, "catastrophic_price": 140.0},
        zone="fvg",
        zone_price=24500.0,
        entry_distance_atr=1.0,
        signal_candle_atr=1.0,
        limit_price=limit,
        est_delta=0.66,
        expires_at="2026-09-28T10:04:01+05:30",
        client_order_id=order_id("founder", signal_id, "entry"),
    )


def _decision(decision_id: str, lots: int) -> Decision:
    return Decision(
        decision_id=decision_id,
        underlying="NIFTY",
        decision="ENTER",
        signal_ids=[],
        instrument_id=INST,
        lots=lots,
        lot_size=65,
        limit_price=151.40,
        shadow={"chosen": "ITM100"},
    )


def _exit_plan() -> ExitPlan:
    return ExitPlan(
        catastrophic=CatastrophicStop(level=Level(kind="premium", price=140.0)),
        partials=(Partial(at=Level(kind="premium", price=155.0), fraction=0.5),),
        flat_by_ist="15:15",
    )


def _print_book(label: str, pm: PositionManager) -> None:
    now = pm.clock.now().astimezone(IST).isoformat()
    print(f"\n== {label} @ {now} ==")
    opens = pm.open_book()
    if not opens:
        print("  open positions: (none)")
    for p in opens:
        print(
            f"  OPEN {p['instrument_id']} qty={p['net_qty']} avg={p['avg_price']:.2f} "
            f"mark={p.get('mark')} stop={p.get('stop_price')} "
            f"unreal={(float(p.get('mark') or p['avg_price']) - float(p['avg_price'])) * int(p['net_qty']):.2f} "
            f"realized={float(p.get('realized_pnl') or 0):.2f}"
        )
    for c in pm.store.closed:
        ts = c.get("last_exit_ts")
        stamp = ts.astimezone(IST).isoformat() if hasattr(ts, "astimezone") else ts
        print(
            f"  CLOSED {c.get('instrument_id')} exit={c.get('last_exit_price')} "
            f"qty={c.get('last_exit_qty')} realized={float(c.get('realized_pnl') or 0):.2f} "
            f"reason={c.get('exit_reason')} ts={stamp}"
        )


def run() -> None:
    with TemporaryDirectory() as raw:
        tmp = Path(raw)
        clock = SimClock(START)
        bus = MemoryBus()
        store = MemoryLedger()
        risk = V2RiskEngine(ledger=store, config_path=_risk(tmp), bus=bus)
        broker = make_broker(clock=clock)
        router = OrderRouter(clock=clock, risk=risk, broker=broker, store=store, bus=bus)
        pm = PositionManager(clock=clock, router=router, store=store, bus=bus)
        plan = _exit_plan()

        sig1 = "sg_demo_nifty_20260928_1001_0"
        a = router.submit(_plan(sig1, "ep_1", "dc_1"), _decision("dc_1", 2), Account("founder"), exit_plan=plan)
        assert not isinstance(a, Veto)
        clock.advance_by(timedelta(milliseconds=250))
        broker.on_depth(Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST))
        _print_book("opened 2 lots", pm)

        clock.advance_to(START + timedelta(minutes=4))
        sig2 = "sg_demo_nifty_20260928_1005_0"
        b = router.submit(_plan(sig2, "ep_2", "dc_2"), _decision("dc_2", 1), Account("founder"), exit_plan=plan)
        assert not isinstance(b, Veto)
        clock.advance_by(timedelta(milliseconds=250))
        broker.on_depth(Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST))
        _print_book("added 1 lot", pm)

        from contracts.envelope import Envelope

        clock.advance_to(START.replace(minute=20))
        iso = clock.now().isoformat()
        pm.on_market(
            Envelope(
                v=2,
                event_type="DEPTH_QUOTE",
                event_id="d1",
                stream="md",
                source="demo",
                event_ts=iso,
                available_ts=iso,
                timestamp=iso,
                account_id="founder",
                correlation_id=sig1,
                causation_id=None,
                payload={"instrument_id": INST, "bid": 155.00, "ask": 155.20, "ltp": 155.10},
            )
        )
        _print_book("partial at 155 (50% of original)", pm)

        clock.advance_to(START.replace(hour=10, minute=45))
        iso = clock.now().isoformat()
        pm.on_market(
            Envelope(
                v=2,
                event_type="FOUNDER_COMMAND",
                event_id="f1",
                stream="ctl",
                source="demo",
                event_ts=iso,
                available_ts=iso,
                timestamp=iso,
                account_id="founder",
                correlation_id=sig1,
                causation_id=None,
                payload={"kind": "CUT_LOSS", "instrument_id": INST},
            )
        )
        _print_book("fully closed (FOUNDER_COMMAND)", pm)
        print("\nIST clock end:", clock.now().isoformat())
        print("session_halts (in-memory, V2-10 durable later):", store.session_halts)
        print("realized_pnl_today:", store.realized_pnl_today)


def _risk(tmp: Path) -> Path:
    import yaml

    src = Path(__file__).resolve().parents[4] / "config" / "risk_limits.yaml"
    cfg = yaml.safe_load(src.read_text())
    cfg["kill_switch_file"] = str(tmp / "KILL_SWITCH")
    path = tmp / "risk_limits.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


if __name__ == "__main__":
    run()
