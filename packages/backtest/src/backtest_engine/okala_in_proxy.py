"""India adaptation proxies for Chart Fanatics Okala (MIX-CF-OKALA-IN-*).

HYPOTHESIS / PROJECT-DERIVED adaptation of NQ teacher book — not NQ identity.
NO_PROMOTE. win_rate is VALIDATION output only. No OF / indicator-entry soup.
Teacher 65%/70% claims stay claims.
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from typing import Any, Optional, Sequence

from backtest_engine.clocks import flatten_009, minutes_ist, session_date_ist, skip_open_009
from backtest_engine.indicators import Bar, _wilder_atr, sma

# Reproducible magnet-pair draw (locked for reports / JSON seed).
MAGNET_SEED = 20260907
MAGNET_MODULUS = 100  # last-two-digit grid on INDEX price
# Spirit examples from founder ask: 10:100 → (10,0), 30:70, 20:60. Not sacred 80/20.
_SPIRIT_PAIRS: tuple[tuple[int, int], ...] = ((10, 0), (30, 70), (20, 60))
_RESIDUE_SPACE: tuple[int, ...] = tuple(range(0, 100, 10))  # decade endings search space

REGIMES = ("bullish", "bearish", "sideways", "choppy")
SETUPS = ("LEVEL", "FORK", "H_CROSS", "REPAIR")

# Risk port HYPOTHESIS: NQ 10/15 pts → ATR-scaled INDEX points (ratio 1.5 kept).
SL_ATR_MULT = 0.50
TP_SL_RATIO = 15.0 / 10.0
MIN_SL_PTS = {"NIFTY": 8.0, "BANKNIFTY": 20.0}

TOUCH_ATR_FRAC = 0.20
REACTION_WINDOW = 3
NO_CHASE = True
OUTLIER_TRIM = 0.05  # drop top/bottom 5% trade PnL for robust WR


@dataclass
class OkalaTrade:
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
    regime: str
    magnet_pair: tuple[int, int]
    setup: str
    tf_min: int

    @property
    def win(self) -> bool:
        return self.points > 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["magnet_pair"] = list(self.magnet_pair)
        d["win"] = self.win
        return d


def sample_magnet_pairs(
    *,
    seed: int = MAGNET_SEED,
    n_extra: int = 7,
) -> list[tuple[int, int]]:
    """Return 10 ordered (long_residue, short_residue) pairs mod 100.

    Pair meaning (HYPOTHESIS): mean-revert long near first residue, short near second
    — teacher often longs ~20 / shorts ~80; residues here are searchable, not sacred.
    """
    rng = random.Random(seed)
    fixed = list(_SPIRIT_PAIRS)
    candidates = [
        (a, b)
        for a in _RESIDUE_SPACE
        for b in _RESIDUE_SPACE
        if a != b and (a, b) not in fixed
    ]
    extra = rng.sample(candidates, n_extra)
    pairs = fixed + extra
    assert len(pairs) == 3 + n_extra
    return pairs


def magnet_levels_near(price: float, residue: int, *, modulus: int = MAGNET_MODULUS) -> list[float]:
    """Nearest magnet prices with given last-digit residue on the modulus grid."""
    base = math.floor(price / modulus) * modulus
    levels = [base + residue, base + residue - modulus, base + residue + modulus]
    return sorted(levels, key=lambda x: abs(x - price))


def nearest_magnet(price: float, residue: int, *, modulus: int = MAGNET_MODULUS) -> float:
    return magnet_levels_near(price, residue, modulus=modulus)[0]


def _true_range(bars: Sequence[Bar], i: int) -> float:
    if i == 0:
        return bars[0].high - bars[0].low
    prev = bars[i - 1].close
    b = bars[i]
    return max(b.high - b.low, abs(b.high - prev), abs(b.low - prev))


def wilder_adx(bars: list[Bar], period: int = 14) -> list[float | None]:
    """Wilder ADX — HYPOTHESIS regime helper (not a Dhan API field)."""
    n = len(bars)
    out: list[float | None] = [None] * n
    if n < period * 2 + 1:
        return out
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    tr = [0.0] * n
    for i in range(1, n):
        up = bars[i].high - bars[i - 1].high
        down = bars[i - 1].low - bars[i].low
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
        tr[i] = _true_range(bars, i)
    # Wilder smooth
    atr = sum(tr[1 : period + 1]) / period
    sm_plus = sum(plus_dm[1 : period + 1]) / period
    sm_minus = sum(minus_dm[1 : period + 1]) / period
    dx_vals: list[float] = []
    for i in range(period + 1, n):
        atr = (atr * (period - 1) + tr[i]) / period
        sm_plus = (sm_plus * (period - 1) + plus_dm[i]) / period
        sm_minus = (sm_minus * (period - 1) + minus_dm[i]) / period
        if atr <= 0:
            dx_vals.append(0.0)
            continue
        pdi = 100.0 * sm_plus / atr
        mdi = 100.0 * sm_minus / atr
        denom = pdi + mdi
        dx = 0.0 if denom <= 0 else 100.0 * abs(pdi - mdi) / denom
        dx_vals.append(dx)
        if len(dx_vals) == period:
            out[i] = sum(dx_vals) / period
        elif len(dx_vals) > period:
            prev = out[i - 1]
            assert prev is not None
            out[i] = (prev * (period - 1) + dx) / period
    return out


def efficiency_ratio(closes: Sequence[float], i: int, period: int = 20) -> Optional[float]:
    """Kaufman ER — net move / path. HYPOTHESIS chop vs trend."""
    if i < period or period <= 0:
        return None
    net = abs(closes[i] - closes[i - period])
    path = 0.0
    for j in range(i - period + 1, i + 1):
        path += abs(closes[j] - closes[j - 1])
    if path <= 0:
        return 0.0
    return net / path


def classify_regimes(bars: list[Bar]) -> list[str]:
    """Label each bar: bullish | bearish | sideways | choppy.

    HYPOTHESIS rules (measurable, not teacher clocks):
    - SMA20 vs SMA50 + SMA20 slope (5-bar) vs ATR
    - ADX(14)
    - Kaufman ER(20)
    bullish: ADX>=22 and SMA20>SMA50 and slope>+0.05*ATR
    bearish: ADX>=22 and SMA20<SMA50 and slope<-0.05*ATR
    sideways: ADX<18 and ER<0.25
    choppy: else (noisy / mixed)
    """
    n = len(bars)
    out = ["choppy"] * n
    closes = [b.close for b in bars]
    s20 = sma(closes, 20)
    s50 = sma(closes, 50)
    atrs = _wilder_atr(bars, 14)
    adxs = wilder_adx(bars, 14)
    for i in range(n):
        a20, a50, atr, adx = s20[i], s50[i], atrs[i], adxs[i]
        if a20 is None or a50 is None or atr is None or atr <= 0 or adx is None:
            out[i] = "choppy"
            continue
        if i < 5 or s20[i - 5] is None:
            out[i] = "choppy"
            continue
        slope = a20 - float(s20[i - 5])
        er = efficiency_ratio(closes, i, 20)
        if er is None:
            out[i] = "choppy"
            continue
        thr = 0.05 * atr
        if adx >= 22.0 and a20 > a50 and slope > thr:
            out[i] = "bullish"
        elif adx >= 22.0 and a20 < a50 and slope < -thr:
            out[i] = "bearish"
        elif adx < 18.0 and er < 0.25:
            out[i] = "sideways"
        else:
            out[i] = "choppy"
    return out


def _sl_tp_dist(underlying: str, atr: float) -> tuple[float, float]:
    floor = MIN_SL_PTS.get(underlying, 10.0)
    sl = max(SL_ATR_MULT * atr, floor)
    tp = sl * TP_SL_RATIO
    return sl, tp


def _in_session(ts: int) -> bool:
    m = minutes_ist(ts)
    return (9 * 60 + 15) <= m < (15 * 60 + 15)


def _reaction_long(bars: list[Bar], i: int, magnet: float, window: int) -> bool:
    """Price tagged magnet from below/near then bounced (close rising after touch)."""
    touched = False
    for j in range(max(0, i - window), i + 1):
        b = bars[j]
        if b.low <= magnet <= b.high:
            touched = True
        if touched and j > 0 and bars[j].close > bars[j - 1].close and bars[j].close >= magnet:
            return True
    return False


def _reaction_short(bars: list[Bar], i: int, magnet: float, window: int) -> bool:
    touched = False
    for j in range(max(0, i - window), i + 1):
        b = bars[j]
        if b.low <= magnet <= b.high:
            touched = True
        if touched and j > 0 and bars[j].close < bars[j - 1].close and bars[j].close <= magnet:
            return True
    return False


def _already_reacted_away(
    bars: list[Bar],
    i: int,
    magnet: float,
    side: str,
    atr: float,
) -> bool:
    """no_chase: reaction already fired and price left magnet by >0.35 ATR."""
    if i < 1:
        return False
    b = bars[i]
    if side == "CE":
        if b.close > magnet + 0.35 * atr and bars[i - 1].low <= magnet + TOUCH_ATR_FRAC * atr:
            return True
    else:
        if b.close < magnet - 0.35 * atr and bars[i - 1].high >= magnet - TOUCH_ATR_FRAC * atr:
            return True
    return False


def _is_repair_candle(bar: Bar, *, side: str) -> bool:
    """Repair HYPOTHESIS: little/no wick on open side of the move.

    Long repair (bullish open from low): open ≈ low.
    Short repair (bearish open from high): open ≈ high.
    """
    rng = bar.high - bar.low
    if rng <= 0:
        return False
    if side == "CE":
        return (bar.open - bar.low) / rng <= 0.08
    return (bar.high - bar.open) / rng <= 0.08


def lean_level(
    bars: list[Bar],
    pair: tuple[int, int],
    atrs: list[float | None],
    *,
    require_repair: bool = False,
) -> list[str]:
    """LEVEL mean-reversion at magnet residues. Optional REPAIR confluence gate."""
    long_r, short_r = pair
    n = len(bars)
    out = ["SKIP"] * n
    last_sig_i = -999
    for i in range(n):
        atr = atrs[i]
        if atr is None or atr <= 0:
            continue
        if not _in_session(bars[i].ts):
            continue
        if i - last_sig_i < 2:
            continue
        px = bars[i].close
        tol = TOUCH_ATR_FRAC * atr
        long_m = nearest_magnet(px, long_r)
        short_m = nearest_magnet(px, short_r)
        # Prefer nearer magnet
        side: Optional[str] = None
        magnet = 0.0
        if abs(px - long_m) <= abs(px - short_m) and abs(px - long_m) <= tol * 3:
            if bars[i].low <= long_m + tol and _reaction_long(bars, i, long_m, REACTION_WINDOW):
                side, magnet = "CE", long_m
        if side is None and abs(px - short_m) <= tol * 3:
            if bars[i].high >= short_m - tol and _reaction_short(bars, i, short_m, REACTION_WINDOW):
                side, magnet = "PE", short_m
        if side is None:
            continue
        if NO_CHASE and _already_reacted_away(bars, i, magnet, side, atr):
            continue
        if require_repair:
            look = bars[max(0, i - 5) : i + 1]
            if not any(_is_repair_candle(b, side=side) for b in look):
                continue
        out[i] = side
        last_sig_i = i
    return out


def lean_fork(
    bars: list[Bar],
    pair: tuple[int, int],
    atrs: list[float | None],
) -> list[str]:
    """FORK long proxy: capitulation down + failed break of low + HH (BIND spirit).

    Magnet confluence preferred near long residue; structure can fire without exact print.
    """
    long_r, _ = pair
    n = len(bars)
    out = ["SKIP"] * n
    last_sig_i = -999
    for i in range(8, n):
        atr = atrs[i]
        if atr is None or atr <= 0 or not _in_session(bars[i].ts):
            continue
        if i - last_sig_i < 3:
            continue
        # Capitulation: net drop over 4–6 bars >= 1.2 ATR
        look = 5
        drop = bars[i - look].close - bars[i].close
        if drop < 1.2 * atr:
            continue
        init = bars[i - 2]
        body = abs(init.close - init.open)
        rng = init.high - init.low
        if rng <= 0 or body / rng > 0.45:
            continue  # want wick-heavy / short body initiation
        lower_wick = min(init.open, init.close) - init.low
        if lower_wick < 0.35 * rng:
            continue
        prior_low = init.low
        test = bars[i - 1]
        if test.low < prior_low - 0.05 * atr:
            continue  # broke
        # HH reclaim
        if bars[i].high <= init.high or bars[i].close <= test.close:
            continue
        # Prefer near long magnet (relaxed structure-only allowed but weaker — we soft-gate)
        m = nearest_magnet(bars[i].close, long_r)
        if abs(bars[i].close - m) > 2.5 * atr:
            continue
        out[i] = "CE"
        last_sig_i = i
    return out


def lean_h_cross(
    bars: list[Bar],
    pair: tuple[int, int],
    atrs: list[float | None],
) -> list[str]:
    """H-CROSS short proxy: bounce long-mag → weak rally to short-mag → rollover reject.

    Cross geometry underdefined in BIND — this is a structure stand-in (HYPOTHESIS).
    """
    long_r, short_r = pair
    n = len(bars)
    out = ["SKIP"] * n
    last_sig_i = -999
    for i in range(10, n):
        atr = atrs[i]
        if atr is None or atr <= 0 or not _in_session(bars[i].ts):
            continue
        if i - last_sig_i < 3:
            continue
        # Find bounce near long magnet in lookback
        bounced = False
        for j in range(i - 8, i - 2):
            m_long = nearest_magnet(bars[j].close, long_r)
            if bars[j].low <= m_long + 0.25 * atr and bars[j].close > bars[j].open:
                bounced = True
                break
        if not bounced:
            continue
        m_short = nearest_magnet(bars[i].close, short_r)
        # Approach short magnet then reject
        near = any(
            bars[k].high >= m_short - 0.3 * atr for k in range(i - 3, i + 1)
        )
        if not near:
            continue
        # Two bearish / breakdown bars (cross stand-in)
        b0, b1 = bars[i - 1], bars[i]
        if not (b0.close < b0.open and b1.close < b1.open):
            continue
        if b1.close > m_short + 0.15 * atr:
            continue
        # Weak rally into 80-analog: net up from bounce but stalling
        if bars[i].close >= bars[i - 4].close + 0.1 * atr and b1.high < bars[i - 2].high:
            out[i] = "PE"
            last_sig_i = i
        elif b1.close < m_short and b1.high > m_short - 0.5 * atr:
            out[i] = "PE"
            last_sig_i = i
    return out


def leans_for_setup(
    setup: str,
    bars: list[Bar],
    pair: tuple[int, int],
    atrs: list[float | None],
) -> list[str]:
    if setup == "LEVEL":
        return lean_level(bars, pair, atrs, require_repair=False)
    if setup == "FORK":
        return lean_fork(bars, pair, atrs)
    if setup == "H_CROSS":
        return lean_h_cross(bars, pair, atrs)
    if setup == "REPAIR":
        # Confluence-only: LEVEL gated by repair candle (not blind repair entry).
        return lean_level(bars, pair, atrs, require_repair=True)
    raise ValueError(setup)


def simulate_okala(
    bars: list[Bar],
    leans: list[str],
    regimes: list[str],
    atrs: list[float | None],
    *,
    strategy_id: str,
    underlying: str,
    pair: tuple[int, int],
    setup: str,
    tf_min: int,
    use_009: bool = True,
) -> list[OkalaTrade]:
    """Next-open entry; ATR-scaled SL/TP (BE after TP not modeled as runner — TP1 exit)."""
    trades: list[OkalaTrade] = []
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
                OkalaTrade(
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
                    magnet_pair=pair,
                    setup=setup,
                    tf_min=tf_min,
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
                    OkalaTrade(
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
                        magnet_pair=pair,
                        setup=setup,
                        tf_min=tf_min,
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
            OkalaTrade(
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
                magnet_pair=pair,
                setup=setup,
                tf_min=tf_min,
            )
        )
    return trades


def wr_stats(trades: Sequence[OkalaTrade], *, trim: float = OUTLIER_TRIM) -> dict[str, Any]:
    """Raw WR + outlier-robust WR (drop top/bottom trim of PnL)."""
    n = len(trades)
    if n == 0:
        return {
            "n": 0,
            "wins": 0,
            "wr_raw": None,
            "n_robust": 0,
            "wins_robust": 0,
            "wr_robust": None,
            "outlier_method": f"drop_top_bottom_{int(trim * 100)}pct_pnl",
            "expectancy_raw": None,
            "expectancy_robust": None,
        }
    wins = sum(1 for t in trades if t.win)
    pnls = sorted(t.points for t in trades)
    lo = int(math.floor(n * trim))
    hi = n - lo
    if hi <= lo:
        kept = list(trades)
    else:
        lo_v, hi_v = pnls[lo], pnls[hi - 1]
        kept = [t for t in trades if lo_v <= t.points <= hi_v]
    wins_r = sum(1 for t in kept if t.win)
    n_r = len(kept)
    exp = sum(t.points for t in trades) / n
    exp_r = (sum(t.points for t in kept) / n_r) if n_r else None
    return {
        "n": n,
        "wins": wins,
        "wr_raw": wins / n,
        "n_robust": n_r,
        "wins_robust": wins_r,
        "wr_robust": (wins_r / n_r) if n_r else None,
        "outlier_method": f"drop_top_bottom_{int(trim * 100)}pct_pnl",
        "expectancy_raw": exp,
        "expectancy_robust": exp_r,
    }


def mix_id_for_setup(setup: str) -> str:
    return {
        "LEVEL": "MIX-CF-OKALA-IN-LEVEL",
        "FORK": "MIX-CF-OKALA-IN-FORK",
        "H_CROSS": "MIX-CF-OKALA-IN-H-CROSS",
        "REPAIR": "MIX-CF-OKALA-IN-REPAIR",
    }[setup]


def magnet_pairs_meta(seed: int = MAGNET_SEED) -> dict[str, Any]:
    pairs = sample_magnet_pairs(seed=seed)
    return {
        "seed": seed,
        "modulus": MAGNET_MODULUS,
        "residue_space": list(_RESIDUE_SPACE),
        "spirit_fixed": [list(p) for p in _SPIRIT_PAIRS],
        "pairs": [list(p) for p in pairs],
        "pair_meaning": (
            "ordered (long_residue, short_residue) on last-two-digit INDEX grid; "
            "mean-revert long near first / short near second — HYPOTHESIS, not NQ 80/20 law"
        ),
    }
