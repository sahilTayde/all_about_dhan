"""Structure CF India overnight grid helpers — ATR risk + regime + robust WR.

Reuse Okala regime/risk/outlier protocol so families are comparable.
HYPOTHESIS / NO_PROMOTE. INDEX points proxy ≠ option premium.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional, Sequence

from backtest_engine.clocks import flatten_009, minutes_ist, session_date_ist, skip_open_009
from backtest_engine.indicators import Bar, _wilder_atr
from backtest_engine.okala_in_proxy import (
    OUTLIER_TRIM,
    REGIMES,
    SL_ATR_MULT,
    TP_SL_RATIO,
    classify_regimes,
    wr_stats,
)

MIN_SL_PTS = {"NIFTY": 8.0, "BANKNIFTY": 20.0, "SENSEX": 40.0}


@dataclass
class StructureTrade:
    strategy_id: str
    underlying: str
    side: str
    entry_ts: int
    exit_ts: int
    entry_px: float
    exit_px: float
    points: float
    reason: str
    session: str
    regime: str
    setup: str
    tf_min: int
    params: dict[str, Any]

    @property
    def win(self) -> bool:
        return self.points > 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sl_tp_dist(underlying: str, atr: float) -> tuple[float, float]:
    floor = MIN_SL_PTS.get(underlying, 10.0)
    sl = max(SL_ATR_MULT * atr, floor)
    return sl, sl * TP_SL_RATIO


def _in_session(ts: int) -> bool:
    m = minutes_ist(ts)
    return (9 * 60 + 15) <= m < (15 * 60 + 15)


def simulate_structure(
    bars: list[Bar],
    leans: list[str],
    regimes: list[str],
    atrs: list[float | None],
    *,
    strategy_id: str,
    underlying: str,
    setup: str,
    tf_min: int,
    params: dict[str, Any],
    use_009: bool = True,
) -> list[StructureTrade]:
    """Next-open entry; ATR-scaled SL/TP (same spirit as Okala India port)."""
    trades: list[StructureTrade] = []
    pos: Optional[str] = None
    entry_px = 0.0
    entry_ts = 0
    entry_i = 0
    stop_px = 0.0
    target_px = 0.0
    entry_regime = "choppy"
    n = min(len(bars), len(leans), len(regimes), len(atrs))

    def _fill_open(i: int) -> Optional[tuple[int, float]]:
        if i + 1 >= n:
            return None
        nxt = bars[i + 1]
        return nxt.ts, nxt.open

    for i in range(n):
        bar = bars[i]
        session = session_date_ist(bar.ts)
        if use_009 and flatten_009(bar.ts) and pos is not None:
            pts = (bar.close - entry_px) if pos == "CE" else (entry_px - bar.close)
            trades.append(
                StructureTrade(
                    strategy_id=strategy_id,
                    underlying=underlying,
                    side=pos,
                    entry_ts=entry_ts,
                    exit_ts=bar.ts,
                    entry_px=entry_px,
                    exit_px=bar.close,
                    points=pts,
                    reason="flatten_009",
                    session=session,
                    regime=entry_regime,
                    setup=setup,
                    tf_min=tf_min,
                    params=dict(params),
                )
            )
            pos = None
            continue

        if pos is not None:
            hit: Optional[tuple[str, float]] = None
            if pos == "CE":
                if bar.low <= stop_px:
                    hit = ("sl", stop_px)
                elif bar.high >= target_px:
                    hit = ("tp1", target_px)
            else:
                if bar.high >= stop_px:
                    hit = ("sl", stop_px)
                elif bar.low <= target_px:
                    hit = ("tp1", target_px)
            if hit is not None:
                reason, xpx = hit
                pts = (xpx - entry_px) if pos == "CE" else (entry_px - xpx)
                trades.append(
                    StructureTrade(
                        strategy_id=strategy_id,
                        underlying=underlying,
                        side=pos,
                        entry_ts=entry_ts,
                        exit_ts=bar.ts,
                        entry_px=entry_px,
                        exit_px=xpx,
                        points=pts,
                        reason=reason,
                        session=session,
                        regime=entry_regime,
                        setup=setup,
                        tf_min=tf_min,
                        params=dict(params),
                    )
                )
                pos = None
                continue
            continue

        lean = leans[i]
        if lean not in ("CE", "PE"):
            continue
        if use_009 and skip_open_009(bar.ts):
            continue
        if not _in_session(bar.ts):
            continue
        atr = atrs[i]
        if atr is None or atr <= 0:
            continue
        fill = _fill_open(i)
        if fill is None:
            continue
        ets, epx = fill
        sl_d, tp_d = _sl_tp_dist(underlying, atr)
        if lean == "CE":
            stop_px = epx - sl_d
            target_px = epx + tp_d
        else:
            stop_px = epx + sl_d
            target_px = epx - tp_d
        pos = lean
        entry_px = epx
        entry_ts = ets
        entry_i = i + 1
        entry_regime = regimes[i] if i < len(regimes) else "choppy"

    if pos is not None and entry_i < n:
        bar = bars[-1]
        pts = (bar.close - entry_px) if pos == "CE" else (entry_px - bar.close)
        trades.append(
            StructureTrade(
                strategy_id=strategy_id,
                underlying=underlying,
                side=pos,
                entry_ts=entry_ts,
                exit_ts=bar.ts,
                entry_px=entry_px,
                exit_px=bar.close,
                points=pts,
                reason="eod_close",
                session=session_date_ist(bar.ts),
                regime=entry_regime,
                setup=setup,
                tf_min=tf_min,
                params=dict(params),
            )
        )
    return trades


def score_by_regime(
    trades: Sequence[StructureTrade],
    *,
    trim: float = OUTLIER_TRIM,
) -> dict[str, dict[str, Any]]:
    """wr_stats per entry-regime bucket."""
    out: dict[str, dict[str, Any]] = {}
    for regime in REGIMES:
        bucket = [t for t in trades if t.regime == regime]
        # wr_stats expects objects with .win / .points — StructureTrade matches
        out[regime] = wr_stats(bucket, trim=trim)  # type: ignore[arg-type]
    return out


def prep_series(bars: list[Bar]) -> tuple[list[str], list[float | None]]:
    return classify_regimes(bars), _wilder_atr(bars, 14)
