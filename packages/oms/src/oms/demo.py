"""Paper-only demo: open, add, partial, full close through the V2-09 manager."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from contracts.envelope import Envelope
from contracts.ids import order_id
from contracts.payloads import (
    CatastrophicStop,
    Decision,
    EntryPlan,
    ExitPlan,
    Level,
    Partial,
    StructuralStop,
)
from events.bus import MemoryBus
from risk_engine import IST, V2RiskEngine

from oms import Account, MemoryLedger, OrderRouter, PositionManager, Veto, lot_size_for

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
        lot_size=lot_size_for(INST),
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
        mark = float(p.get("mark") or p["avg_price"])
        unreal = (mark - float(p["avg_price"])) * int(p["net_qty"])
        stop_qty = pm.router.open_stop_qty(str(p.get("instrument_id") or ""))
        print(
            f"  OPEN {p['instrument_id']} qty={p['net_qty']} avg={p['avg_price']:.2f} "
            f"mark={p.get('mark')} stop={p.get('stop_price')} stop_qty={stop_qty} "
            f"unreal={unreal:.2f} realized={float(p.get('realized_pnl') or 0):.2f}"
        )
    open_stops = [
        o
        for o in pm.router.broker.orders.values()
        if o.is_open and (o.intent.exit_reason or "") == "STOP_HIT"
    ]
    print(
        f"  open STOP_HIT count={len(open_stops)} "
        f"qty={sum(int(o.intent.lots) * int(o.intent.lot_size or 1) for o in open_stops)}"
    )
    for c in pm.store.closed:
        ts = c.get("last_exit_ts")
        stamp = ts.astimezone(IST).isoformat() if ts is not None else None
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
        a = router.submit(
            _plan(sig1, "ep_1", "dc_1"),
            _decision("dc_1", 2),
            Account("founder"),
            exit_plan=plan,
        )
        assert not isinstance(a, Veto)
        clock.advance_by(timedelta(milliseconds=250))
        broker.on_depth(
            Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
        )
        _print_book("opened 2 lots", pm)

        clock.advance_to(START + timedelta(minutes=4))
        sig2 = "sg_demo_nifty_20260928_1005_0"
        b = router.submit(
            _plan(sig2, "ep_2", "dc_2"),
            _decision("dc_2", 1),
            Account("founder"),
            exit_plan=plan,
        )
        assert not isinstance(b, Veto)
        clock.advance_by(timedelta(milliseconds=250))
        broker.on_depth(
            Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
        )
        _print_book("added 1 lot", pm)

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
        _print_book("partial at 155 (50% → floor 1 lot, leave 2)", pm)

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

        run_09b(tmp, clock)


def run_09b(tmp: Path, clock: SimClock) -> None:
    """V2-09b: structural on bar close; inherit refuses without native invalidation."""
    from oms.exits import HOUSE_MAX_LOSS_INR, load_exit_defaults

    defaults, digest = load_exit_defaults()
    print(
        f"\n== V2-09b defaults == house={HOUSE_MAX_LOSS_INR} "
        f"defaults_from=exit_defaults@{digest[:12]}… "
        f"atr={defaults.get('atr')} grace={defaults.get('grace')} "
        f"flip={defaults.get('signal_flip')}"
    )
    structural = defaults.get("structural")
    if isinstance(structural, dict) and structural.get("enabled"):
        print("inherit without native invalidation: refused")

    bus = MemoryBus()
    store = MemoryLedger()
    risk = V2RiskEngine(ledger=store, config_path=_risk(tmp), bus=bus)
    broker = make_broker(clock=clock)
    router = OrderRouter(clock=clock, risk=risk, broker=broker, store=store, bus=bus)
    pm = PositionManager(clock=clock, router=router, store=store, bus=bus)
    plan = ExitPlan(
        catastrophic=CatastrophicStop(level=Level(kind="premium", price=140.0)),
        structural=StructuralStop(level=Level(kind="underlying", price=24400.0)),
        flat_by_ist="15:15",
    )
    sig = "sg_demo_nifty_20260928_1100_0"
    order = router.submit(
        _plan(sig, "ep_s", "dc_s"),
        _decision("dc_s", 1),
        Account("founder"),
        exit_plan=plan,
    )
    assert not isinstance(order, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
    )
    iso = clock.now().isoformat()
    pm.on_market(
        Envelope(
            v=2,
            event_type="BAR_CLOSED",
            event_id="bar1",
            stream="md",
            source="demo",
            event_ts=iso,
            available_ts=iso,
            timestamp=iso,
            account_id="founder",
            correlation_id=sig,
            causation_id=None,
            payload={
                "instrument_id": "NSE_IDX:NIFTY",
                "c": 24390.0,
                "underlying_close": 24390.0,
            },
        )
    )
    _print_book("V2-09b structural bar-close", pm)


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
