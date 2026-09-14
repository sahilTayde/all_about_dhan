"""Founder ITM option scalp (Dhan chart rules). PROJECT-DERIVED. NO_PROMOTE.

Honest API limit: DhanHQ / MCP returns OPTIDX OHLC (+OI), not VPVR POC series and
not the chart-only \"RSI Strength & Momentum\" pane. We compute RSI / EMA3 / WMA21 /
EMA21 / session VWAP or session volume-POC from that OHLC and label HYPOTHESIS.

Gemini Pine mistake (caught 2026-09-13): requiring EMA3×WMA21 *crossover event*
on the *same* bar as RSI≥70 wiped September. Founder chart reading is bullish MA
*state* (EMA3 > WMA21) while RSI / POC / EMA21 hold — rising-edge of that setup.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Literal, Optional

from backtest_engine.clocks import session_date_ist
from backtest_engine.costs import DEFAULT_COST, CostModel, apply_round_trip
from backtest_engine.indicators import Bar, ema, rsi, session_vwap_of, wma
from backtest_engine.simulate import Trade

MIX_ID = "MIX-ITM-OPT-SCALP"
LAYER = "HYPOTHESIS"
ORIGIN = "PROJECT-DERIVED"

PocMode = Literal["session_vwap", "session_vpoc"]
MaMode = Literal["bullish_state", "cross_event"]  # cross_event = Gemini Pine (broken for Sep)
FillMode = Literal["signal_close", "signal_poc", "next_open"]
ExitMode = Literal["ma_or_rsi", "ma_only", "rsi_only"]


@dataclass(frozen=True)
class ItmScalpParams:
    rsi_length: int = 14
    rsi_entry_th: float = 70.0
    rsi_exit_th: float = 68.0
    ema_fast_len: int = 3
    wma_slow_len: int = 21
    ema_base_len: int = 21
    poc_mode: PocMode = "session_vwap"
    ma_mode: MaMode = "bullish_state"
    fill_mode: FillMode = "signal_close"
    exit_mode: ExitMode = "ma_or_rsi"
    # Cap re-entries per IST session (1 ≈ discretionary diamond day).
    max_entries_per_session: Optional[int] = None
    # HYPOTHESIS premium SL/TP fractions (None = off). Dealer fantasy warning applies.
    stop_loss_frac: Optional[float] = None  # e.g. 0.15 = -15% premium
    target_frac: Optional[float] = None  # e.g. 0.30 = +30% premium
    vpoc_bins: int = 40


def session_volume_poc(bars: list[Bar], *, bins: int = 40) -> list[float | None]:
    """Developing session volume-POC (silver-line proxy for chart VPVR).

    Not TradingView Visible-Range VPVR. Resets each IST session day. Bins the
    session high-low range; each bar's volume lands in the bin of its typical price.
    """
    from collections import defaultdict

    out: list[float | None] = []
    day: Optional[str] = None
    hist: dict[int, float] = {}
    lo = hi = 0.0
    for bar in bars:
        d = session_date_ist(bar.ts)
        if d != day:
            day = d
            hist = defaultdict(float)
            lo, hi = bar.low, bar.high
        lo = min(lo, bar.low)
        hi = max(hi, bar.high)
        span = max(hi - lo, 1e-9)
        typical = (bar.high + bar.low + bar.close) / 3.0
        key = int(min(bins - 1, max(0, (typical - lo) / span * (bins - 1))))
        weight = bar.volume if bar.volume > 0 else 1.0
        hist[key] += weight
        best = max(hist, key=hist.get)
        out.append(lo + (best + 0.5) / bins * span)
    return out


def _poc_series(bars: list[Bar], params: ItmScalpParams) -> list[float | None]:
    closes = [b.close for b in bars]
    if params.poc_mode == "session_vpoc":
        return session_volume_poc(bars, bins=params.vpoc_bins)
    return session_vwap_of(bars, closes, equal_weight_if_no_volume=True)


def itm_scalp_setup_flags(
    bars: list[Bar],
    params: ItmScalpParams | None = None,
) -> tuple[list[bool], list[bool], list[bool]]:
    """Return (setup_true, exit_flags, rising_edge_entry).

    setup_true = close > POC and RSI >= entry and close > EMA21 and MA bullish.
    rising_edge_entry = setup just became true (one signal per streak).
    exit = MA cross down OR RSI < exit_th (even if still above POC).
    """
    p = params or ItmScalpParams()
    closes = [b.close for b in bars]
    rsi_val = rsi(closes, p.rsi_length)
    ema_fast = ema(closes, p.ema_fast_len)
    wma_slow = wma(closes, p.wma_slow_len)
    ema_base = ema(closes, p.ema_base_len)
    poc = _poc_series(bars, p)

    setup = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(len(bars)):
        if (
            rsi_val[i] is None
            or ema_fast[i] is None
            or wma_slow[i] is None
            or ema_base[i] is None
            or poc[i] is None
        ):
            continue
        ma_bull = ema_fast[i] > wma_slow[i]
        ma_cross_up = False
        ma_cross_down = False
        if i > 0 and ema_fast[i - 1] is not None and wma_slow[i - 1] is not None:
            ma_cross_up = ema_fast[i - 1] <= wma_slow[i - 1] and ema_fast[i] > wma_slow[i]
            ma_cross_down = ema_fast[i - 1] >= wma_slow[i - 1] and ema_fast[i] < wma_slow[i]
        ma_ok = ma_cross_up if p.ma_mode == "cross_event" else ma_bull
        setup[i] = (
            closes[i] > poc[i]
            and rsi_val[i] >= p.rsi_entry_th
            and closes[i] > ema_base[i]
            and ma_ok
        )
        if p.exit_mode == "ma_only":
            exit_[i] = ma_cross_down
        elif p.exit_mode == "rsi_only":
            exit_[i] = rsi_val[i] < p.rsi_exit_th
        else:
            exit_[i] = ma_cross_down or (rsi_val[i] < p.rsi_exit_th)

    rising = [False] * len(bars)
    for i in range(len(bars)):
        prev = setup[i - 1] if i else False
        rising[i] = setup[i] and not prev
    return setup, exit_, rising


def itm_scalp_signals(
    bars: list[Bar],
    params: ItmScalpParams | None = None,
) -> tuple[list[bool], list[bool]]:
    """Compat: (entry_rising_edge, exit_flags)."""
    _, exit_, rising = itm_scalp_setup_flags(bars, params)
    return rising, exit_


def _entry_fill(
    bars: list[Bar],
    i: int,
    params: ItmScalpParams,
    poc: list[float | None],
) -> Optional[tuple[int, float]]:
    bar = bars[i]
    if params.fill_mode == "signal_close":
        return bar.ts, bar.close
    if params.fill_mode == "signal_poc":
        if poc[i] is None:
            return bar.ts, bar.close
        return bar.ts, float(poc[i])
    if i + 1 >= len(bars):
        return None
    nxt = bars[i + 1]
    return nxt.ts, nxt.open


def _exit_fill(bars: list[Bar], i: int, params: ItmScalpParams) -> Optional[tuple[int, float]]:
    bar = bars[i]
    if params.fill_mode in ("signal_close", "signal_poc"):
        return bar.ts, bar.close
    if i + 1 >= len(bars):
        return None
    nxt = bars[i + 1]
    return nxt.ts, nxt.open


def simulate_itm_scalp_long(
    bars: list[Bar],
    *,
    underlying: str = "NIFTY",
    side: str = "PE",
    strategy_id: str = MIX_ID,
    params: ItmScalpParams | None = None,
) -> list[Trade]:
    """Long-only option-premium scalp with optional HYPOTHESIS % SL/TP."""
    p = params or ItmScalpParams()
    _, exit_flags, rising = itm_scalp_setup_flags(bars, p)
    poc = _poc_series(bars, p)
    trades: list[Trade] = []
    in_pos = False
    entry_px = 0.0
    entry_ts = 0
    stop_px: Optional[float] = None
    target_px: Optional[float] = None
    session_entries: dict[str, int] = {}

    for i, bar in enumerate(bars):
        session = session_date_ist(bar.ts)
        if in_pos:
            reason = None
            exit_px = None
            exit_ts = None
            # Intrabar SL/TP: stop before target (conservative).
            if stop_px is not None and bar.low <= stop_px:
                reason = "stop_loss"
                exit_ts, exit_px = bar.ts, stop_px
            elif target_px is not None and bar.high >= target_px:
                reason = "target"
                exit_ts, exit_px = bar.ts, target_px
            elif exit_flags[i]:
                fill = _exit_fill(bars, i, p)
                if fill is None:
                    reason = "eod_close"
                    exit_ts, exit_px = bar.ts, bar.close
                else:
                    reason = "exit_signal"
                    exit_ts, exit_px = fill
            if reason is not None and exit_px is not None and exit_ts is not None:
                trades.append(
                    Trade(
                        strategy_id=strategy_id,
                        underlying=underlying,
                        side=side,
                        entry_ts=entry_ts,
                        exit_ts=exit_ts,
                        entry_px=entry_px,
                        exit_px=exit_px,
                        points=exit_px - entry_px,
                        reason=reason,
                        session=session,
                    )
                )
                in_pos = False
                stop_px = target_px = None
                continue

        if not in_pos and rising[i]:
            used = session_entries.get(session, 0)
            if p.max_entries_per_session is not None and used >= p.max_entries_per_session:
                continue
            fill = _entry_fill(bars, i, p, poc)
            if fill is None:
                break
            entry_ts, entry_px = fill
            in_pos = True
            session_entries[session] = used + 1
            stop_px = (
                entry_px * (1.0 - p.stop_loss_frac) if p.stop_loss_frac else None
            )
            target_px = (
                entry_px * (1.0 + p.target_frac) if p.target_frac else None
            )

    if in_pos and bars:
        bar = bars[-1]
        trades.append(
            Trade(
                strategy_id=strategy_id,
                underlying=underlying,
                side=side,
                entry_ts=entry_ts,
                exit_ts=bar.ts,
                entry_px=entry_px,
                exit_px=bar.close,
                points=bar.close - entry_px,
                reason="series_end",
                session=session_date_ist(bar.ts),
            )
        )
    return trades


def summarize_lot_pnl(
    trades: list[Trade],
    *,
    lot_size: int,
    lots: int = 1,
    cost_model: CostModel = DEFAULT_COST,
) -> dict[str, Any]:
    """Premium points → rupees for N lots. Raw + hypothesis RT haircut."""
    qty = int(lot_size) * int(lots)
    raw_pts = sum(t.points for t in trades)
    costed = [apply_round_trip(t, cost_model) for t in trades]
    cost_pts = sum(t.points for t in costed)
    wins = sum(1 for t in trades if t.points > 0)
    losses = sum(1 for t in trades if t.points <= 0)
    return {
        "trade_count": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / len(trades)) if trades else None,
        "gross_points": round(raw_pts, 4),
        "gross_pnl_inr": round(raw_pts * qty, 2),
        "after_cost_points": round(cost_pts, 4),
        "after_cost_pnl_inr": round(cost_pts * qty, 2),
        "lot_size": lot_size,
        "lots": lots,
        "quantity": qty,
        "cost_model": cost_model.as_dict(),
        "trades": [
            {
                **asdict(t),
                "pnl_inr": round(t.points * qty, 2),
                "after_cost_points": round(c.points, 4),
                "after_cost_pnl_inr": round(c.points * qty, 2),
            }
            for t, c in zip(trades, costed)
        ],
    }


def sltp_grid_scan(
    bars: list[Bar],
    *,
    underlying: str,
    side: str,
    lot_size: int,
    lots: int = 1,
    base: ItmScalpParams | None = None,
) -> list[dict[str, Any]]:
    """Small HYPOTHESIS SL/TP grid — research only, not a promote."""
    base = base or ItmScalpParams()
    rows: list[dict[str, Any]] = []
    for sl in (None, 0.10, 0.15, 0.20, 0.25):
        for tp in (None, 0.20, 0.30, 0.40, 0.50):
            params = replace(base, stop_loss_frac=sl, target_frac=tp)
            trades = simulate_itm_scalp_long(
                bars, underlying=underlying, side=side, params=params
            )
            summary = summarize_lot_pnl(trades, lot_size=lot_size, lots=lots)
            rows.append(
                {
                    "stop_loss_frac": sl,
                    "target_frac": tp,
                    "trade_count": summary["trade_count"],
                    "wins": summary["wins"],
                    "losses": summary["losses"],
                    "win_rate": summary["win_rate"],
                    "gross_pnl_inr": summary["gross_pnl_inr"],
                    "after_cost_pnl_inr": summary["after_cost_pnl_inr"],
                }
            )
    rows.sort(key=lambda r: r["after_cost_pnl_inr"], reverse=True)
    return rows


def diamond_overlap(
    pe_trades: list[Trade],
    ce_trades: list[Trade],
) -> dict[str, Any]:
    """Yellow PE vs blue CE — count same-session overlaps (should stay low if inverse)."""
    pe_sessions = {t.session for t in pe_trades}
    ce_sessions = {t.session for t in ce_trades}
    both = sorted(pe_sessions & ce_sessions)
    return {
        "pe_sessions": sorted(pe_sessions),
        "ce_sessions": sorted(ce_sessions),
        "overlap_sessions": both,
        "overlap_count": len(both),
        "note": (
            "Inverse diamonds ≈ PE long days vs CE long days should rarely overlap. "
            "Not a Dhan chart diamond API — reconstructed from our buy signals."
        ),
    }
