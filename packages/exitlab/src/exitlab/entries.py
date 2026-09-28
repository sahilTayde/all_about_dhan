"""Entry sets independent of exit skill. Legacy replay, V2 selector proxy, random."""

from __future__ import annotations

import json
import random
import tempfile
from datetime import datetime, time
from pathlib import Path
from typing import Any

from exitlab.clock import IST, as_ist
from exitlab.fills import SlippageModel
from exitlab.tapes import premium_quote, wing_ltp
from exitlab.types import Bar, Entry

LOT_SIZE = 65
NO_NEW_BEFORE = time(9, 50)
NO_NEW_AFTER = time(14, 45)


def _snap_to_50(px: float) -> float:
    return round(px / 50.0) * 50.0


def random_entries(
    ticks: list[dict[str, Any]],
    *,
    session: str,
    scenario: str,
    seed: int,
    n: int = 24,
    expiry: str | None = None,
) -> list[Entry]:
    """CE and PE at random in-window times, ATM and 100/200 ITM."""
    rng = random.Random(seed)
    usable = [
        t
        for t in ticks
        if t.get("index")
        and t.get("atm_strike")
        and NO_NEW_BEFORE <= as_ist(t["available_ts"]).time() < NO_NEW_AFTER
        and (t.get("atm_ce") or t.get("itm_ce"))
    ]
    if not usable:
        return []
    out: list[Entry] = []
    moneyness = ("ATM", "ITM100", "ITM200")
    k = 0
    while len(out) < n and k < n * 8:
        k += 1
        tick = usable[rng.randrange(len(usable))]
        side = rng.choice(("CE", "PE"))
        kind = moneyness[len(out) % 3]
        atm = float(tick["atm_strike"])
        if kind == "ATM":
            strike = atm
            ltp = tick["atm_ce"] if side == "CE" else tick["atm_pe"]
            iv = tick.get("atm_ce_iv") if side == "CE" else tick.get("atm_pe_iv")
        else:
            pts = 100.0 if kind == "ITM100" else 200.0
            strike = atm - pts if side == "CE" else atm + pts
            ltp = wing_ltp(tick, side=side, strike=strike)
            if ltp is None:
                ltp = tick["itm_ce"] if side == "CE" else tick["itm_pe"]
                raw_strike = (
                    tick.get("itm_ce_strike") if side == "CE" else tick.get("itm_pe_strike")
                )
                if ltp is None or raw_strike is None:
                    continue
                strike = float(raw_strike)
            iv = tick.get("itm_ce_iv") if side == "CE" else tick.get("itm_pe_iv")
        if ltp is None or ltp <= 0:
            continue
        model = SlippageModel()
        q = premium_quote(tick, side=side, moneyness="ITM" if kind != "ATM" else "ATM")
        clock_ts = tick["available_ts"]
        from exitlab.clock import ReplayClock

        px = model.entry_px(q, None, ReplayClock(clock_ts))
        out.append(
            Entry(
                entry_id=f"rnd-{session}-{seed}-{len(out)}",
                ts=clock_ts,
                side=side,
                strike=float(strike),
                entry_price=px,
                lots=1,
                lot_size=LOT_SIZE,
                entry_set="random",
                session=session,
                index_at_entry=tick.get("index"),
                iv_at_entry=iv,
                atm_strike=atm,
                expiry=expiry or tick.get("expiry"),
                moneyness=kind,
                scenario=scenario,
                seed=seed,
                extra={"regime_at_entry": scenario},
            )
        )
    return out


def history_random_entries(
    index_bars: list[Bar],
    option_bars: list[Bar],
    *,
    session: str,
    scenario: str,
    seed: int,
    n: int = 20,
    expiry: str | None,
) -> list[Entry]:
    rng = random.Random(seed)
    idx = [b for b in index_bars if NO_NEW_BEFORE <= as_ist(b.ts).time() < NO_NEW_AFTER]
    if not idx:
        return []
    by_key: dict[tuple[str, float, str], list[Bar]] = {}
    for b in option_bars:
        if b.side and b.strike is not None:
            by_key.setdefault(
                (as_ist(b.ts).date().isoformat(), float(b.strike), b.side), []
            ).append(b)
    out: list[Entry] = []
    tries = 0
    while len(out) < n and tries < n * 20:
        tries += 1
        ib = idx[rng.randrange(len(idx))]
        side = rng.choice(("CE", "PE"))
        kind = ("ATM", "ITM100", "ITM200")[len(out) % 3]
        atm = _snap_to_50(ib.close)
        pts = {"ATM": 0.0, "ITM100": 100.0, "ITM200": 200.0}[kind]
        strike = atm - pts if side == "CE" else atm + pts
        path = by_key.get((session, float(strike), side)) or []
        bar = next((x for x in path if as_ist(x.available_ts) >= as_ist(ib.available_ts)), None)
        if bar is None or bar.close <= 0:
            continue
        from exitlab.clock import ReplayClock
        from exitlab.fills import SlippageModel

        px = SlippageModel().entry_px(None, bar, ReplayClock(bar.available_ts))
        out.append(
            Entry(
                entry_id=f"hist-{session}-{seed}-{len(out)}",
                ts=bar.available_ts,
                side=side,
                strike=float(strike),
                entry_price=px,
                lots=1,
                lot_size=LOT_SIZE,
                entry_set="random_hist",
                session=session,
                index_at_entry=ib.close,
                atm_strike=atm,
                expiry=expiry,
                moneyness=kind,
                scenario=scenario,
                seed=seed,
                extra={"regime_at_entry": scenario, "history": True},
            )
        )
    return out


def v2_selector_entries(
    ticks: list[dict[str, Any]],
    *,
    session: str,
    scenario: str,
    expiry: str | None = None,
) -> list[Entry]:
    """Replay BossSelector holds + 1m close direction. Documented proxy, not live alpha."""
    from boss.selector import (  # type: ignore[import-untyped]
        BarContext,
        BossSelector,
        SessionBasketGate,
        load_engine_config,
    )
    from contracts.clock import SimClock
    from contracts.payloads import CatastrophicStop, ExitPlan, Level, StrikeChoice, StrikeQuote
    from strategies.api import Signal
    from strategies.registry import Basket, BasketEntry

    usable = [t for t in ticks if t.get("index") and t.get("index_1m")]
    if not usable:
        return []
    # One decision per closed 1m bar, first tick that carries a new bar.
    seen: set[int] = set()
    bars: list[dict[str, Any]] = []
    for t in usable:
        raw = t.get("index_1m") or {}
        key = raw.get("ts")
        if key is None or int(key) in seen:
            continue
        seen.add(int(key))
        bars.append(t)
    cfg = load_engine_config()
    basket = SessionBasketGate(
        Basket(
            session=session,
            market="IN_INDEX_OPT",
            entries=(
                BasketEntry(
                    strategy_id="EXITLAB-PROXY",
                    underlyings=("NIFTY",),
                    weight=1.0,
                    max_lots=2,
                    stage="paper",
                ),
            ),
            source="exitlab",
            basket_hash="exitlab-v2-proxy",
        )
    )
    out: list[Entry] = []
    prev_close: float | None = None
    last_entry_ts: datetime | None = None
    sel = BossSelector(clock=SimClock(bars[0]["available_ts"]), config=cfg, basket=basket)
    for i, tick in enumerate(bars):
        raw = tick["index_1m"]
        close = float(raw["close"])
        avail = tick["available_ts"]
        if as_ist(avail).time() < NO_NEW_BEFORE or as_ist(avail).time() >= NO_NEW_AFTER:
            prev_close = close
            continue
        if prev_close is None:
            prev_close = close
            continue
        gap_s = (as_ist(avail) - as_ist(last_entry_ts)).total_seconds() if last_entry_ts else 1e9
        if gap_s < 30 * 60:
            prev_close = close
            continue
        if len(out) >= 8:
            break
        side = "CE" if close >= prev_close else "PE"
        prev_close = close
        clock = SimClock(avail)
        sel.clock = clock
        plan = ExitPlan(catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0)))
        quote = StrikeQuote(
            rule="ITM100",
            instrument_id=f"NSE_FNO:NIFTY:{expiry or session}:0:{side}",
            bid=tick.get("itm_ce") if side == "CE" else tick.get("itm_pe"),
            ask=tick.get("itm_ce") if side == "CE" else tick.get("itm_pe"),
            mid=tick.get("itm_ce") if side == "CE" else tick.get("itm_pe"),
            spread=None,
            quote_age_ms=200,
            est_delta=0.6,
            est_round_trip_pts=2.0,
        )
        choice = StrikeChoice(
            chosen="ITM100", reason="EXITLAB_PROXY", rule_version="lab", alternatives=(quote,)
        )
        sig = Signal(
            signal_id=f"el-{session}-{i}",
            strategy_id="EXITLAB-PROXY",
            underlying="NIFTY",
            side=side,
            strike_rule="ITM100",
            strike_choice=choice,
            decision_ts=avail.isoformat(),
            confidence=0.55,
            exit_plan=plan,
            reasons=("INDEX_1M_DIR",),
            features={"close": close},
        )
        ctx = BarContext(
            underlying="NIFTY",
            bar_ts=avail,
            available_ts=avail,
            feed_status="STALE" if tick.get("stale") else "UP",
            em30=40.0,
            delta=0.55,
            stop=50.0,
            regime_label=scenario,
            is_expiry=scenario.startswith("expiry"),
            signal_stages={"EXITLAB-PROXY": "paper"},
        )
        result = sel.decide([sig], ctx)
        if not result.decisions or result.decisions[0].decision != "ENTER":
            continue
        dec = result.decisions[0]
        ltp = tick.get("itm_ce") if side == "CE" else tick.get("itm_pe")
        strike = tick.get("itm_ce_strike") if side == "CE" else tick.get("itm_pe_strike")
        if ltp is None or strike is None:
            continue
        from exitlab.clock import ReplayClock

        q = premium_quote(tick, side=side, moneyness="ITM")
        px = SlippageModel().entry_px(q, None, ReplayClock(avail))
        lots = max(1, int(dec.lots or 2))
        out.append(
            Entry(
                entry_id=f"v2-{session}-{i}",
                ts=avail,
                side=side,
                strike=float(strike),
                entry_price=px,
                lots=min(lots, 2),
                lot_size=LOT_SIZE,
                entry_set="v2_boss",
                session=session,
                index_at_entry=tick.get("index"),
                iv_at_entry=tick.get("itm_ce_iv") if side == "CE" else tick.get("itm_pe_iv"),
                atm_strike=tick.get("atm_strike"),
                expiry=expiry or tick.get("expiry"),
                moneyness="ITM100",
                scenario=scenario,
                extra={"regime_at_entry": scenario, "holds": list(getattr(dec, "holds", ()) or ())},
            )
        )
        last_entry_ts = avail
    return out


def legacy_entries_from_replay(
    tape_path: Path,
    *,
    session: str,
    scenario: str,
) -> tuple[list[Entry], dict[str, Any]]:
    """Run frozen replay_paper_scalp write=False on a copy of the dual-tape day."""
    from desk_ml.paper_scalp import replay_paper_scalp

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dest = root / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
        dest.mkdir(parents=True)
        (dest / f"{session}.jsonl").write_bytes(tape_path.read_bytes())
        recon = root / "data" / "recon"
        (recon / "founder_trade_underlyings.json").write_text(
            json.dumps({"trade_underlyings": ["NIFTY"]})
        )
        (recon / "ml_paper_session_params.json").write_text(
            json.dumps({"stop_frac": 0.38, "scalp_hold_bars": 9, "nudge_n_closed": 494})
        )
        (recon / "optidx_lot_cache.json").write_text(
            json.dumps({"NIFTY": {"lot_size": LOT_SIZE, "source": "exitlab"}})
        )
        try:
            board = replay_paper_scalp(
                root=root,
                underlyings=("NIFTY",),
                source="dual-tape",
                write=False,
                live_session=True,
                session_ist_date=session,
                use_event_bus=False,
            )
        except Exception as exc:
            return [], {"ok": False, "error": str(exc), "session": session}
    closed = [t for t in (board.get("closed_trades") or []) if t.get("filled")]
    out: list[Entry] = []
    for i, row in enumerate(closed):
        ts = row.get("opened_ts")
        if ts is None:
            continue
        when = datetime.fromtimestamp(int(ts), tz=IST)
        side = str(row.get("side") or "").upper()
        if side not in {"CE", "PE"}:
            continue
        try:
            px = float(row["entry"])
            strike = float(row.get("atm_strike") or row.get("strike") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if px <= 0:
            continue
        lots = int(row.get("lots") or 1)
        out.append(
            Entry(
                entry_id=str(row.get("trade_id") or f"leg-{session}-{i}"),
                ts=when,
                side=side,
                strike=strike,
                entry_price=px,
                lots=max(1, lots),
                lot_size=int(row.get("lot_size") or LOT_SIZE),
                entry_set="legacy",
                session=session,
                index_at_entry=_f(row.get("idx_at_open")),
                atm_strike=_f(row.get("atm_strike")),
                expiry=row.get("expiry"),
                moneyness="ITM200",
                scenario=scenario,
                extra={
                    "legacy_exit_reason": row.get("exit_reason"),
                    "legacy_net": row.get("realized_pnl_inr"),
                    "legacy_gross": row.get("gross_pnl_inr"),
                    "legacy_charges": row.get("charges_inr"),
                    "legacy_exit": row.get("exit"),
                    "legacy_closed_ts": row.get("closed_ts"),
                    "regime_at_entry": scenario,
                },
            )
        )
    meta = {
        "ok": True,
        "session": session,
        "n_closed_filled": len(closed),
        "n_entries": len(out),
        "skip_reason_counts": board.get("skip_reason_counts") or {},
    }
    return out, meta


def _f(raw: Any) -> float | None:
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
