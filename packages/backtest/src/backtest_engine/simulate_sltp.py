"""Simulate lean entries with named SL/TP overlays (ATR+R2, etc.).

Entry lean ≠ exit recipe. Proxy P/L = underlying points unless noted.
"""

from __future__ import annotations

from typing import Optional, Sequence

from backtest_engine.clocks import flatten_009, session_date_ist, skip_open_009
from backtest_engine.indicators import Bar, _wilder_atr
from backtest_engine.levels import DEFAULT_ATR_MULT, DEFAULT_ATR_PERIOD, DEFAULT_RR
from backtest_engine.simulate import Trade, _fill_open


def simulate_leans_sltp(
    bars: list[Bar],
    leans: list[str],
    *,
    strategy_id: str,
    underlying: str,
    method_id: str = "MIX-SLTP-ATR-R2",
    atr_period: int = DEFAULT_ATR_PERIOD,
    atr_mult: float = DEFAULT_ATR_MULT,
    rr: float = DEFAULT_RR,
    use_009: bool = True,
    veto_sessions: Optional[set[str]] = None,
    allow_entry: Optional[list[bool]] = None,
) -> list[Trade]:
    """Enter on CE/PE lean (next open); exit on ATR stop, R-target, lean flip, or flatten.

    ATR distance frozen at entry bar (no look-ahead on future ATR).
    """
    veto_sessions = veto_sessions or set()
    atrs = _wilder_atr(bars, atr_period)
    trades: list[Trade] = []
    pos: Optional[str] = None
    entry_px = 0.0
    entry_ts = 0
    stop_px = 0.0
    target_px = 0.0
    n = min(len(bars), len(leans))

    for i in range(n):
        bar = bars[i]
        lean = leans[i]
        session = session_date_ist(bar.ts)

        if use_009 and flatten_009(bar.ts) and pos is not None:
            trades.append(
                _trade(
                    strategy_id,
                    underlying,
                    pos,
                    entry_ts,
                    bar.ts,
                    entry_px,
                    bar.close,
                    "flatten_009",
                    session,
                )
            )
            pos = None
            continue

        if pos is not None:
            hit = _hit_levels(pos, bar, stop_px, target_px)
            if hit is not None:
                reason, xpx = hit
                trades.append(
                    _trade(
                        strategy_id,
                        underlying,
                        pos,
                        entry_ts,
                        bar.ts,
                        entry_px,
                        xpx,
                        reason,
                        session,
                    )
                )
                pos = None
                continue
            if lean != pos:
                fill = _fill_open(bars, i)
                if fill is None:
                    trades.append(
                        _trade(
                            strategy_id,
                            underlying,
                            pos,
                            entry_ts,
                            bar.ts,
                            entry_px,
                            bar.close,
                            "eod_close",
                            session,
                        )
                    )
                    pos = None
                    break
                xts, xpx = fill
                trades.append(
                    _trade(
                        strategy_id,
                        underlying,
                        pos,
                        entry_ts,
                        xts,
                        entry_px,
                        xpx,
                        "stack_exit",
                        session,
                    )
                )
                pos = None
            continue

        if use_009 and skip_open_009(bar.ts):
            continue
        if session in veto_sessions:
            continue
        if allow_entry is not None and (i >= len(allow_entry) or not allow_entry[i]):
            continue
        if lean not in ("CE", "PE"):
            continue
        atr = atrs[i]
        if atr is None or atr <= 0:
            continue
        fill = _fill_open(bars, i)
        if fill is None:
            break
        entry_ts, entry_px = fill
        stop_d = float(atr) * float(atr_mult)
        target_d = stop_d * float(rr)
        if lean == "CE":
            stop_px = entry_px - stop_d
            target_px = entry_px + target_d
        else:
            stop_px = entry_px + stop_d
            target_px = entry_px - target_d
        pos = lean

    if pos is not None and bars:
        last = bars[-1]
        trades.append(
            _trade(
                strategy_id,
                underlying,
                pos,
                entry_ts,
                last.ts,
                entry_px,
                last.close,
                "series_end",
                session_date_ist(last.ts),
            )
        )
    # annotate method on strategy_id already; reason carries stop/target
    _ = method_id
    return trades


def _hit_levels(
    pos: str, bar: Bar, stop_px: float, target_px: float
) -> Optional[tuple[str, float]]:
    """Intrabar stop-first (conservative). Touch fill = level price."""
    if pos == "CE":
        if bar.low <= stop_px:
            return "atr_stop", stop_px
        if bar.high >= target_px:
            return "rr_target", target_px
    else:
        if bar.high >= stop_px:
            return "atr_stop", stop_px
        if bar.low <= target_px:
            return "rr_target", target_px
    return None


def _trade(
    strategy_id: str,
    underlying: str,
    side: str,
    entry_ts: int,
    exit_ts: int,
    entry_px: float,
    exit_px: float,
    reason: str,
    session: str,
) -> Trade:
    pts = (exit_px - entry_px) if side == "CE" else (entry_px - exit_px)
    return Trade(
        strategy_id=strategy_id,
        underlying=underlying,
        side=side,
        entry_ts=entry_ts,
        exit_ts=exit_ts,
        entry_px=entry_px,
        exit_px=exit_px,
        points=pts,
        reason=reason,
        session=session,
    )


def simulate_st_flip_exit(
    bars: list[Bar],
    leans: list[str],
    st_line: Sequence[Optional[float]],
    *,
    strategy_id: str = "MIX-SLTP-ST-FLIP",
    underlying: str,
    use_009: bool = True,
) -> list[Trade]:
    """Enter on lean; exit when close crosses through Supertrend (003-faithful)."""
    trades: list[Trade] = []
    pos: Optional[str] = None
    entry_px = 0.0
    entry_ts = 0
    n = min(len(bars), len(leans), len(st_line))
    for i in range(n):
        bar = bars[i]
        lean = leans[i]
        st = st_line[i]
        session = session_date_ist(bar.ts)
        if use_009 and flatten_009(bar.ts) and pos is not None:
            trades.append(
                _trade(
                    strategy_id,
                    underlying,
                    pos,
                    entry_ts,
                    bar.ts,
                    entry_px,
                    bar.close,
                    "flatten_009",
                    session,
                )
            )
            pos = None
            continue
        if pos is not None and st is not None:
            flipped = (pos == "CE" and bar.close < st) or (pos == "PE" and bar.close > st)
            if flipped:
                fill = _fill_open(bars, i)
                if fill is None:
                    trades.append(
                        _trade(
                            strategy_id,
                            underlying,
                            pos,
                            entry_ts,
                            bar.ts,
                            entry_px,
                            bar.close,
                            "st_flip_eod",
                            session,
                        )
                    )
                    pos = None
                    break
                xts, xpx = fill
                trades.append(
                    _trade(
                        strategy_id,
                        underlying,
                        pos,
                        entry_ts,
                        xts,
                        entry_px,
                        xpx,
                        "st_flip",
                        session,
                    )
                )
                pos = None
                continue
        if pos is not None:
            continue
        if use_009 and skip_open_009(bar.ts):
            continue
        if lean not in ("CE", "PE") or st is None:
            continue
        fill = _fill_open(bars, i)
        if fill is None:
            break
        entry_ts, entry_px = fill
        pos = lean
    if pos is not None and bars:
        last = bars[-1]
        trades.append(
            _trade(
                strategy_id,
                underlying,
                pos,
                entry_ts,
                last.ts,
                entry_px,
                last.close,
                "series_end",
                session_date_ist(last.ts),
            )
        )
    return trades
