"""Deterministic exit replay. No look-ahead. Buyer: ask in, bid out."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from exitlab.clock import LookAheadError, ReplayClock, as_ist
from exitlab.costs import fill_charges, load_cost_rates
from exitlab.fills import SlippageModel, mark_long
from exitlab.plans import ExitPlanFn, pretrade_skip
from exitlab.types import Bar, Entry, Fill, OpenState, Quote, TradeResult


def _update_excursions(state: OpenState, mark: float, index: float | None, now: datetime) -> None:
    entry = state.entry.entry_price
    state.mfe = max(state.mfe, mark)
    state.mae = min(state.mae, mark)
    if mark >= state.seen_high:
        state.seen_high = mark
        state.seen_high_ts = now
    state.seen_low = min(state.seen_low, mark)
    state.premium_prints.append(mark)
    if len(state.premium_prints) > 64:
        state.premium_prints = state.premium_prints[-64:]
    if index is not None and state.entry.index_at_entry is not None:
        signed = index - state.entry.index_at_entry
        if state.entry.side == "PE":
            signed = -signed
        state.mfe_index = max(state.mfe_index, signed)
        state.mae_index = min(state.mae_index, signed)
    _ = entry


def replay_trade(
    entry: Entry,
    plan: ExitPlanFn,
    *,
    quotes: Sequence[Quote] = (),
    bars: Sequence[Bar] = (),
    index_bars: Sequence[Bar] = (),
    slippage: SlippageModel | None = None,
    cost_rates: dict[str, Any] | None = None,
    ctx_extra: dict[str, Any] | None = None,
    data_source: str = "synthetic",
    reject_prob: float = 0.0,
    partial_fill_frac: float = 1.0,
    seed: int = 0,
) -> TradeResult:
    """Replay one entry. Bars are only visible after available_ts. Quotes by available_ts."""
    _ = seed, reject_prob
    model = slippage or SlippageModel()
    rates = cost_rates if cost_rates is not None else load_cost_rates()
    clock = ReplayClock(entry.ts)
    qty = entry.qty
    if partial_fill_frac < 1.0:
        qty = max(entry.lot_size, int(entry.lot_size * int(entry.lots * partial_fill_frac)))
        qty = (qty // entry.lot_size) * entry.lot_size
    if qty <= 0:
        return _empty(entry, plan.plan_id, data_source, skipped="REJECT")
    state = OpenState(
        entry=entry,
        remaining_qty=qty,
        mfe=entry.entry_price,
        mae=entry.entry_price,
        seen_high=entry.entry_price,
        seen_low=entry.entry_price,
        seen_high_ts=entry.ts,
        last_ltp=entry.entry_price,
    )
    skip = pretrade_skip(state, now=entry.ts, index=entry.index_at_entry, iv=entry.iv_at_entry)
    if skip:
        return _empty(entry, plan.plan_id, data_source, skipped=skip)

    events: list[tuple[datetime, str, Quote | Bar]] = []
    for q in quotes:
        if as_ist(q.available_ts) < as_ist(entry.ts):
            continue
        events.append((as_ist(q.available_ts), "q", q))
    for b in bars:
        if as_ist(b.available_ts) < as_ist(entry.ts):
            continue
        events.append((as_ist(b.available_ts), "b", b))
    events.sort(key=lambda e: (e[0], 0 if e[1] == "q" else 1))

    index_by_ts = {as_ist(b.available_ts): b for b in index_bars}
    last_quote: Quote | None = None
    last_bar: Bar | None = None
    exit_reason = "FLATTEN_EOD"
    exit_ts = entry.ts
    exit_px = entry.entry_price

    for ts, kind, obj in events:
        clock.advance_to(ts)
        if kind == "q":
            q = obj  # type: ignore[assignment]
            assert isinstance(q, Quote)
            clock.visible(q.available_ts, label="quote")
            last_quote = q
            state.last_quote_ts = q.available_ts
            state.last_bid, state.last_ask, state.last_ltp = q.bid, q.ask, q.ltp
            if q.index is not None:
                state.last_index = q.index
            if q.iv is not None:
                state.last_iv = q.iv
        else:
            assert isinstance(obj, Bar)
            b = obj
            clock.visible(b.available_ts, label="bar")
            last_bar = b
            state.closed_bars.append(b)
            if len(state.closed_bars) > 32:
                state.closed_bars = state.closed_bars[-32:]
            state.last_ltp = b.close

        mark = mark_long(last_quote, last_bar, clock)
        if mark is None:
            continue
        idx = state.last_index
        if idx is None and last_bar is not None:
            idx = last_bar.index_close
        ib = index_by_ts.get(ts)
        if ib is not None:
            idx = ib.close
            clock.visible(ib.available_ts, label="index_bar")
        _update_excursions(state, mark, idx, clock.now)
        ctx = {
            "mark": mark,
            "index": idx,
            "iv": state.last_iv,
            "atr": (ctx_extra or {}).get("atr"),
            "tod_mae": (ctx_extra or {}).get("tod_mae"),
            "chop": (ctx_extra or {}).get("chop", False),
            "regime": (ctx_extra or {}).get("regime") or entry.scenario,
            "vwap": (ctx_extra or {}).get("vwap"),
        }
        reason = plan.decide(state, clock, ctx)
        if not reason:
            continue
        if reason == "PARTIAL":
            close_qty = (state.remaining_qty // entry.lot_size) // 2 * entry.lot_size
            if close_qty < entry.lot_size:
                continue
            px = model.exit_px(last_quote, last_bar, clock)
            fill = Fill("SELL", clock.now, close_qty, px, model.name, reason)
            ch = fill_charges(fill, rates)
            state.realized_gross += (px - entry.entry_price) * close_qty
            state.realized_charges += ch["total"]
            state.remaining_qty -= close_qty
            state.partials_done += 1
            state.legs.append(
                {"reason": reason, "qty": close_qty, "px": px, "ts": clock.now.isoformat()}
            )
            continue
        px = model.exit_px(last_quote, last_bar, clock)
        fill = Fill("SELL", clock.now, state.remaining_qty, px, model.name, reason)
        ch = fill_charges(fill, rates)
        buy = Fill("BUY", entry.ts, state.remaining_qty, entry.entry_price, model.name, "ENTRY")
        buy_ch = fill_charges(buy, rates)
        state.realized_gross += (px - entry.entry_price) * state.remaining_qty
        state.realized_charges += ch["total"] + buy_ch["total"]
        state.legs.append(
            {"reason": reason, "qty": state.remaining_qty, "px": px, "ts": clock.now.isoformat()}
        )
        exit_reason, exit_ts, exit_px = reason, clock.now, px
        state.remaining_qty = 0
        break

    if state.remaining_qty > 0:
        # Forced square-off at last visible mark / model exit.
        px = (
            model.exit_px(last_quote, last_bar, clock)
            if (last_quote or last_bar)
            else entry.entry_price
        )
        fill = Fill("SELL", clock.now, state.remaining_qty, px, model.name, "FLATTEN_EOD")
        ch = fill_charges(fill, rates)
        buy = Fill("BUY", entry.ts, state.remaining_qty, entry.entry_price, model.name, "ENTRY")
        buy_ch = fill_charges(buy, rates)
        state.realized_gross += (px - entry.entry_price) * state.remaining_qty
        state.realized_charges += ch["total"] + buy_ch["total"]
        exit_reason, exit_ts, exit_px = "FLATTEN_EOD", clock.now, px
        state.remaining_qty = 0

    qty0 = entry.qty
    return TradeResult(
        entry_id=entry.entry_id,
        entry_set=entry.entry_set,
        session=entry.session,
        scenario=entry.scenario,
        side=entry.side,
        strike=entry.strike,
        lots=entry.lots,
        qty=qty0,
        entry_ts=entry.ts.isoformat(),
        exit_ts=exit_ts.isoformat(),
        entry_price=entry.entry_price,
        exit_price=exit_px,
        exit_reason=exit_reason,
        time_in_trade_s=(as_ist(exit_ts) - as_ist(entry.ts)).total_seconds(),
        mfe=state.mfe,
        mae=state.mae,
        mfe_inr=(state.mfe - entry.entry_price) * qty0,
        mae_inr=(state.mae - entry.entry_price) * qty0,
        gross_inr=round(state.realized_gross, 2),
        charges_inr=round(state.realized_charges, 2),
        net_inr=round(state.realized_gross - state.realized_charges, 2),
        plan_id=plan.plan_id,
        data_source=data_source,
        extra={"legs": state.legs, "fill_model": model.name},
    )


def _empty(entry: Entry, plan_id: str, data_source: str, *, skipped: str) -> TradeResult:
    return TradeResult(
        entry_id=entry.entry_id,
        entry_set=entry.entry_set,
        session=entry.session,
        scenario=entry.scenario,
        side=entry.side,
        strike=entry.strike,
        lots=entry.lots,
        qty=entry.qty,
        entry_ts=entry.ts.isoformat(),
        exit_ts=None,
        entry_price=entry.entry_price,
        exit_price=None,
        exit_reason=skipped,
        time_in_trade_s=0.0,
        mfe=entry.entry_price,
        mae=entry.entry_price,
        mfe_inr=0.0,
        mae_inr=0.0,
        gross_inr=0.0,
        charges_inr=0.0,
        net_inr=0.0,
        plan_id=plan_id,
        data_source=data_source,
        skipped=skipped,
    )


def assert_no_lookahead(entry: Entry, future: Quote | Bar, plan: ExitPlanFn) -> None:
    """Plant a future print. Any read of it must raise LookAheadError."""
    clock = ReplayClock(entry.ts)
    try:
        clock.visible(future.available_ts, label="planted")
    except LookAheadError:
        return
    raise AssertionError("planted future stamp was treated as visible")


def replay_many(
    entries: Iterable[Entry],
    plan: ExitPlanFn,
    series_for: Any,
    **kwargs: Any,
) -> list[TradeResult]:
    out: list[TradeResult] = []
    for entry in entries:
        quotes, bars, index_bars = series_for(entry)
        out.append(
            replay_trade(
                entry,
                plan,
                quotes=quotes,
                bars=bars,
                index_bars=index_bars,
                **kwargs,
            )
        )
    return out
