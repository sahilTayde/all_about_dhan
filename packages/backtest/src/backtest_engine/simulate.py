"""Next-bar-open fills. Proxy P/L is underlying points, not option premium."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from backtest_engine.clocks import flatten_009, session_date_ist, skip_open_009
from backtest_engine.indicators import Bar


@dataclass
class Trade:
    strategy_id: str
    underlying: str
    side: str  # CE | PE
    entry_ts: int
    exit_ts: int
    entry_px: float
    exit_px: float
    points: float
    reason: str
    session: str

    @property
    def win(self) -> bool:
        return self.points > 0


def _fill_open(bars: list[Bar], i: int) -> Optional[tuple[int, float]]:
    if i + 1 >= len(bars):
        return None
    nxt = bars[i + 1]
    return nxt.ts, nxt.open


def simulate_leans(
    bars: list[Bar],
    leans: list[str],
    *,
    strategy_id: str,
    underlying: str,
    use_009: bool = True,
    veto_sessions: Optional[set[str]] = None,
    allow_entry: Optional[list[bool]] = None,
) -> list[Trade]:
    """Enter on first CE/PE lean; exit on opposite, SKIP (ST/VWAP disagree), or flatten.

    Fill = next bar open (no look-ahead on the signal close).
    """
    veto_sessions = veto_sessions or set()
    trades: list[Trade] = []
    pos: Optional[str] = None
    entry_px = 0.0
    entry_ts = 0
    n = min(len(bars), len(leans))
    for i in range(n):
        bar = bars[i]
        lean = leans[i]
        session = session_date_ist(bar.ts)
        if use_009 and flatten_009(bar.ts) and pos is not None:
            trades.append(
                Trade(
                    strategy_id=strategy_id,
                    underlying=underlying,
                    side=pos,
                    entry_ts=entry_ts,
                    exit_ts=bar.ts,
                    entry_px=entry_px,
                    exit_px=bar.close,
                    points=(bar.close - entry_px) if pos == "CE" else (entry_px - bar.close),
                    reason="flatten_009",
                    session=session,
                )
            )
            pos = None
            continue
        if pos is not None:
            if lean != pos:
                fill = _fill_open(bars, i)
                if fill is None:
                    trades.append(
                        Trade(
                            strategy_id=strategy_id,
                            underlying=underlying,
                            side=pos,
                            entry_ts=entry_ts,
                            exit_ts=bar.ts,
                            entry_px=entry_px,
                            exit_px=bar.close,
                            points=(bar.close - entry_px) if pos == "CE" else (entry_px - bar.close),
                            reason="eod_close",
                            session=session,
                        )
                    )
                    pos = None
                    break
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
                        points=(xpx - entry_px) if pos == "CE" else (entry_px - xpx),
                        reason="stack_exit",
                        session=session,
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
        fill = _fill_open(bars, i)
        if fill is None:
            break
        entry_ts, entry_px = fill
        pos = lean
    if pos is not None and bars:
        last = bars[-1]
        trades.append(
            Trade(
                strategy_id=strategy_id,
                underlying=underlying,
                side=pos,
                entry_ts=entry_ts,
                exit_ts=last.ts,
                entry_px=entry_px,
                exit_px=last.close,
                points=(last.close - entry_px) if pos == "CE" else (entry_px - last.close),
                reason="series_end",
                session=session_date_ist(last.ts),
            )
        )
    return trades


def trades_as_dicts(trades: list[Trade]) -> list[dict]:
    return [asdict(t) for t in trades]
