"""Long option premium: both CE and PE score as exit - entry."""

from __future__ import annotations

import bisect
from typing import Optional

from backtest_engine.clocks import flatten_009, session_date_ist, skip_open_009
from backtest_engine.indicators import Bar
from backtest_engine.simulate import Trade


def _next_open(
    opt: list[Bar], ts_list: list[int], after_ts: int
) -> Optional[tuple[int, float]]:
    i = bisect.bisect_right(ts_list, after_ts)
    if i >= len(opt):
        return None
    bar = opt[i]
    return bar.ts, bar.open


def _bar_at_or_after(opt: list[Bar], ts_list: list[int], ts: int) -> Optional[Bar]:
    if not opt:
        return None
    i = bisect.bisect_left(ts_list, ts)
    if i < len(opt):
        return opt[i]
    return opt[-1]


def simulate_option_premium(
    signal_bars: list[Bar],
    leans: list[str],
    opt_ce: list[Bar],
    opt_pe: list[Bar],
    *,
    strategy_id: str,
    underlying: str,
    use_009: bool = True,
    use_007_allow: Optional[list[bool]] = None,
    veto_sessions: Optional[set[str]] = None,
    skip_open: Optional[bool] = None,
    session_end_flatten: bool = False,
) -> list[Trade]:
    """Buy CE or PE premium. Win if option points > 0. No look-ahead on signal close."""
    veto_sessions = veto_sessions or set()
    skip_open_entries = use_009 if skip_open is None else skip_open
    ce_ts = [b.ts for b in opt_ce]
    pe_ts = [b.ts for b in opt_pe]
    trades: list[Trade] = []
    pos: Optional[str] = None
    entry_px = 0.0
    entry_ts = 0
    n = min(len(signal_bars), len(leans))
    for i in range(n):
        bar = signal_bars[i]
        lean = leans[i]
        session = session_date_ist(bar.ts)
        if pos == "CE":
            book, book_ts = opt_ce, ce_ts
        else:
            book, book_ts = opt_pe, pe_ts
        next_session = (
            session_date_ist(signal_bars[i + 1].ts) if i + 1 < n else None
        )
        leave_session = session_end_flatten and (
            next_session is None or next_session != session
        )
        if pos is not None and (
            (use_009 and flatten_009(bar.ts)) or leave_session
        ):
            xb = _bar_at_or_after(book, book_ts, bar.ts)
            if xb is not None:
                trades.append(
                    Trade(
                        strategy_id=strategy_id,
                        underlying=underlying,
                        side=pos,
                        entry_ts=entry_ts,
                        exit_ts=xb.ts,
                        entry_px=entry_px,
                        exit_px=xb.close,
                        points=xb.close - entry_px,
                        reason=(
                            "flatten_009"
                            if use_009 and flatten_009(bar.ts)
                            else "session_end"
                        ),
                        session=session,
                    )
                )
            pos = None
            continue
        if pos is not None and lean != pos:
            fill = _next_open(book, book_ts, bar.ts)
            if fill is None:
                xb = _bar_at_or_after(book, book_ts, bar.ts)
                if xb is not None:
                    trades.append(
                        Trade(
                            strategy_id=strategy_id,
                            underlying=underlying,
                            side=pos,
                            entry_ts=entry_ts,
                            exit_ts=xb.ts,
                            entry_px=entry_px,
                            exit_px=xb.close,
                            points=xb.close - entry_px,
                            reason="eod_close",
                            session=session,
                        )
                    )
                pos = None
                continue
            xts, xpx = fill
            trades.append(
                Trade(
                    strategy_id=strategy_id,
                    underlying=underlying,
                    side=pos,
                    entry_ts=entry_ts,
                    exit_ts=xts,
                    entry_px=entry_px,
                    exit_px=xpx,
                    points=xpx - entry_px,
                    reason="stack_exit",
                    session=session,
                )
            )
            pos = None
            continue
        if pos is not None:
            continue
        if skip_open_entries and skip_open_009(bar.ts):
            continue
        if session in veto_sessions:
            continue
        if use_007_allow is not None and (i >= len(use_007_allow) or not use_007_allow[i]):
            continue
        if lean not in ("CE", "PE"):
            continue
        if lean == "CE":
            book_in, book_in_ts = opt_ce, ce_ts
        else:
            book_in, book_in_ts = opt_pe, pe_ts
        fill = _next_open(book_in, book_in_ts, bar.ts)
        if fill is None:
            continue
        entry_ts, entry_px = fill
        pos = lean
    if pos is not None:
        book = opt_ce if pos == "CE" else opt_pe
        last = book[-1] if book else None
        if last is not None:
            trades.append(
                Trade(
                    strategy_id=strategy_id,
                    underlying=underlying,
                    side=pos,
                    entry_ts=entry_ts,
                    exit_ts=last.ts,
                    entry_px=entry_px,
                    exit_px=last.close,
                    points=last.close - entry_px,
                    reason="series_end",
                    session=session_date_ist(last.ts),
                )
            )
    return trades
