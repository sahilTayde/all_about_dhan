"""RB1-BOX-1M-CPR: 1m pivot-width range-box break, CPR WITH + body-size.

Shadow only. Paper / option buying only. Never places orders.

Port of research cell RB1_1m_P0.3_CPRWITH_BSZ05_1_XTR (detect.det / breaks_day /
trades.exit_idx). Desk 15% premium stop and ₹30k daily cap are not in the
research test; they are logged when they would fire so RB1 can be reconciled.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from contracts.ids import signal_id
from contracts.instruments import India
from contracts.payloads import CatastrophicStop, ExitPlan, Level, Trail

from strategies.api import (
    Bar,
    ChainSnapshot,
    EntryPolicy,
    ExitRequest,
    PositionUpdate,
    SessionContext,
    Signal,
    StrategyMeta,
)
from strategies.feature_view_stub import FeatureView
from strategies.params_hash import compute_params_hash
from strategies.plugins.lab_lock import as_ist, feat_f, fixed_strike

logger = logging.getLogger(__name__)

STRATEGY_ID = "RB1-BOX-1M-CPR"
VERSION = "1.0.0"
CELL_ID = "RB1_1m_P0.3_CPRWITH_BSZ05_1_XTR"
LIVE_STAGES = frozenset({"live", "live_eligible", "limited_live"})

TF_MIN = 1
BOX_KIND = "P"
BOX_WIDTH_PCT = 0.30
MIN_BOX_BARS = 3
BREAK_CELL = "cpr=WITH & bsz=.5-1"
SIGNAL_START_MIN = 556  # 09:16 IST
SIGNAL_END_MIN = 905  # 15:05 IST
LAST_EXIT_MIN = 915  # 15:15 IST
MAX_TRADES_DAY = 3
ONE_AT_A_TIME = True
TRAIL_ARM_PTS = 20.0
TRAIL_GIVEBACK = 0.35
LOTS = 10
BSZ_LO = 0.5
BSZ_HI = 1.0
DESK_PREMIUM_STOP_PCT = 0.15
DESK_DAILY_CAP_INR = 30000.0
_INDIA = India()
NIFTY_LOT = int(_INDIA.lot_size("NIFTY"))

EXIT_PLAN = ExitPlan(
    catastrophic=CatastrophicStop(level=Level(kind="max_loss_inr", price=DESK_DAILY_CAP_INR)),
    trail=Trail(
        kind="percent",
        activate_at=Level(kind="underlying", price=TRAIL_ARM_PTS),
        percent=TRAIL_GIVEBACK,
    ),
    flat_by_ist="15:15",
)

PARAMS_DICT: dict[str, Any] = {
    "tf_min": TF_MIN,
    "box_kind": BOX_KIND,
    "box_width_pct": BOX_WIDTH_PCT,
    "min_box_bars": MIN_BOX_BARS,
    "break_cell": BREAK_CELL,
    "signal_window": [SIGNAL_START_MIN, SIGNAL_END_MIN],
    "last_exit": LAST_EXIT_MIN,
    "max_trades_day": MAX_TRADES_DAY,
    "one_at_a_time": ONE_AT_A_TIME,
    "trail_arm_pts": TRAIL_ARM_PTS,
    "trail_giveback": TRAIL_GIVEBACK,
    "lots": LOTS,
    "instrument": "NIFTY ATM weekly CE/PE",
    "side": "BUY_ONLY",
    "orders": "REFUSED",
    "live": False,
    "desk_premium_stop_pct": DESK_PREMIUM_STOP_PCT,
    "desk_daily_cap_inr": DESK_DAILY_CAP_INR,
    "exit_plan": EXIT_PLAN,
}
PARAMS_HASH = compute_params_hash(PARAMS_DICT)


@dataclass(frozen=True)
class Break:
    """One range-box break at bar i (0-based)."""

    i: int
    s: int
    bh: float
    bl: float
    side: str  # "UP" | "DN"
    minute: int


@dataclass(frozen=True)
class TradeRow:
    """Research-parity row: sig_min / side / entry_min / exit_min."""

    sig_min: int
    side: str  # "CE" | "PE"
    entry_min: int
    exit_min: int
    exit_reason: str
    bh: float
    bl: float
    break_i: int
    entry_i: int
    exit_i: int


@dataclass
class OpenTrade:
    """Live book for one RB1 ticket. Paper marks only."""

    side: str
    bl: float
    bh: float
    break_i: int
    entry_i: int
    entry_min: int
    entry_idx: float
    entry_ask: float | None
    best_fav: float = 0.0
    position_id: str = ""
    desk_stop_logged: bool = False
    desk_cap_logged: bool = False


@dataclass
class RangeBoxState:
    """Monotonic-deque box [s, i) with range <= W. Causal — never reads i+1."""

    width: float
    min_bars: int = MIN_BOX_BARS
    s: int = 0
    highs: list[float] = field(default_factory=list)
    lows: list[float] = field(default_factory=list)
    maxq: deque[int] = field(default_factory=deque)
    minq: deque[int] = field(default_factory=deque)

    def _add(self, high: float, low: float) -> int:
        i = len(self.highs)
        self.highs.append(high)
        self.lows.append(low)
        while self.maxq and self.highs[self.maxq[-1]] <= high:
            self.maxq.pop()
        self.maxq.append(i)
        while self.minq and self.lows[self.minq[-1]] >= low:
            self.minq.pop()
        self.minq.append(i)
        return i

    def _shrink(self) -> None:
        while (
            self.maxq
            and self.minq
            and self.highs[self.maxq[0]] - self.lows[self.minq[0]] > self.width
        ):
            left = self.s
            if self.maxq[0] == left:
                self.maxq.popleft()
            if self.minq[0] == left:
                self.minq.popleft()
            self.s += 1

    def on_bar(self, high: float, low: float, close: float, minute: int) -> Break | None:
        """Check bar i against box [s, i), then append or reset at i. No future bars."""
        i = len(self.highs)
        length = i - self.s
        if length >= self.min_bars and self.maxq and self.minq:
            bh = self.highs[self.maxq[0]]
            bl = self.lows[self.minq[0]]
            if (
                bh - bl <= self.width
                and (close > bh or close < bl)
                and max(bh, high) - min(bl, low) > self.width
            ):
                side = "UP" if close > bh else "DN"
                brk = Break(i=i, s=self.s, bh=bh, bl=bl, side=side, minute=minute)
                self.highs.append(high)
                self.lows.append(low)
                self.s = i
                self.maxq = deque([i])
                self.minq = deque([i])
                return brk
        self._add(high, low)
        self._shrink()
        return None


def cpr_levels(
    prior_high: float, prior_low: float, prior_close: float
) -> tuple[float, float, float]:
    """Prior-day daily P / BC / TC."""
    pivot = (prior_high + prior_low + prior_close) / 3.0
    bc = (prior_high + prior_low) / 2.0
    tc = 2.0 * pivot - bc
    return pivot, bc, tc


def box_width(first_open: float, width_pct: float = BOX_WIDTH_PCT) -> float:
    """W = (width_pct / 100) * first 1m open. 0.30 → 0.003 * open."""
    return (width_pct / 100.0) * float(first_open)


def cpr_with(side: str, close: float, tc: float, bc: float) -> bool:
    if side == "UP":
        return close > tc and close > bc
    if side == "DN":
        return close < bc and close < tc
    return False


def body_size_ok(open_px: float, close: float, width: float) -> bool:
    if width <= 0:
        return False
    ratio = abs(close - open_px) / width
    return BSZ_LO <= ratio <= BSZ_HI


def cell_ok(
    *,
    side: str,
    open_px: float,
    close: float,
    width: float,
    tc: float,
    bc: float,
    minute: int,
) -> bool:
    """cpr=WITH and bsz=.5-1; skip if minute > 15:05."""
    if minute > SIGNAL_END_MIN or minute < SIGNAL_START_MIN:
        return False
    if not cpr_with(side, close, tc, bc):
        return False
    return body_size_ok(open_px, close, width)


def favourable(side: str, close: float, entry_idx: float) -> float:
    if side == "CE":
        return close - entry_idx
    return entry_idx - close


def exit_reason(
    *,
    minute: int,
    close: float,
    bl: float,
    bh: float,
    side: str,
    entry_idx: float,
    best_fav: float,
) -> tuple[str | None, float]:
    """First-hit research exit. Returns (reason, updated best)."""
    fav = favourable(side, close, entry_idx)
    best = max(best_fav, fav)
    if minute >= LAST_EXIT_MIN:
        return "TIME", best
    if bl <= close <= bh:
        return "BACK_INSIDE", best
    if best >= TRAIL_ARM_PTS and (best - fav) > TRAIL_GIVEBACK * best:
        return "TRAIL", best
    return None, best


def detect_breaks(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    minutes: list[int],
    width: float,
) -> list[Break]:
    """Causal breaks_day. Truncating at a break bar must still yield that break."""
    state = RangeBoxState(width=width)
    out: list[Break] = []
    if len(opens) != len(highs):
        raise ValueError("OHLC series length mismatch")
    for high, low, close, minute in zip(highs, lows, closes, minutes, strict=True):
        found = state.on_bar(high, low, close, minute)
        if found is not None:
            out.append(found)
    return out


def exit_idx(
    closes: list[float],
    minutes: list[int],
    *,
    entry_i: int,
    bl: float,
    bh: float,
    side: str,
    entry_idx: float,
) -> tuple[int, str]:
    """First research exit at or after the entry bar. Causal on prefix."""
    best = 0.0
    last = len(closes) - 1
    if last < entry_i:
        return entry_i, "NO_BAR"
    for j in range(entry_i, len(closes)):
        reason, best = exit_reason(
            minute=minutes[j],
            close=closes[j],
            bl=bl,
            bh=bh,
            side=side,
            entry_idx=entry_idx,
            best_fav=best,
        )
        if reason is not None:
            return j, reason
    return last, "TIME"


def trades_for_day(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    minutes: list[int],
    *,
    width: float,
    tc: float,
    bc: float,
) -> list[TradeRow]:
    """Batch RB1 book: same filters / one-at-a-time / 3-trade cap as the plugin."""
    breaks = detect_breaks(opens, highs, lows, closes, minutes, width)
    rows: list[TradeRow] = []
    busy_until = -1
    for brk in breaks:
        if len(rows) >= MAX_TRADES_DAY:
            break
        opt = "CE" if brk.side == "UP" else "PE"
        if not cell_ok(
            side=brk.side,
            open_px=opens[brk.i],
            close=closes[brk.i],
            width=width,
            tc=tc,
            bc=bc,
            minute=brk.minute,
        ):
            continue
        entry_i = brk.i + 1
        if entry_i >= len(closes):
            continue
        if ONE_AT_A_TIME and entry_i <= busy_until:
            continue
        x_i, reason = exit_idx(
            closes,
            minutes,
            entry_i=entry_i,
            bl=brk.bl,
            bh=brk.bh,
            side=opt,
            entry_idx=opens[entry_i],
        )
        busy_until = x_i
        rows.append(
            TradeRow(
                sig_min=brk.minute,
                side=opt,
                entry_min=minutes[entry_i],
                exit_min=minutes[x_i],
                exit_reason=reason,
                bh=brk.bh,
                bl=brk.bl,
                break_i=brk.i,
                entry_i=entry_i,
                exit_i=x_i,
            )
        )
    return rows


def desk_premium_stop_would_fire(entry_ask: float, mark: float) -> bool:
    if entry_ask <= 0:
        return False
    return mark <= entry_ask * (1.0 - DESK_PREMIUM_STOP_PCT)


def desk_daily_cap_would_fire(realized_inr: float, open_mtm_inr: float) -> bool:
    return (realized_inr + open_mtm_inr) <= -DESK_DAILY_CAP_INR


def premium_pnl_inr(entry_ask: float, exit_bid: float, *, lots: int = LOTS) -> float:
    return (exit_bid - entry_ask) * float(lots * NIFTY_LOT)


class Rb1Box1mCprPlugin:
    """Buy ATM CE/PE on a 1m pivot-box break. Shadow, paper, buy-only."""

    meta = StrategyMeta(
        strategy_id=STRATEGY_ID,
        version=VERSION,
        params_hash=PARAMS_HASH,
        markets=("IN_INDEX_OPT",),
        underlyings=("NIFTY",),
        inputs=("bars:1m", "chain"),
        features=(
            "prior_high",
            "prior_low",
            "prior_close",
            "day_open",
            "atm_ce",
            "atm_pe",
            "atm_ce_ask",
            "atm_ce_bid",
            "atm_pe_ask",
            "atm_pe_bid",
        ),
        stage="shadow",
        max_positions=1,
        entry_policy=EntryPolicy(),
        legacy_logic_from=(),
    )
    exit_plan = EXIT_PLAN

    def __init__(self) -> None:
        if self.meta.stage in LIVE_STAGES:
            raise RuntimeError(f"{STRATEGY_ID}: live refused")
        self.params = dict(PARAMS_DICT)
        self._box: RangeBoxState | None = None
        self._width = 0.0
        self._tc = 0.0
        self._bc = 0.0
        self._cpr_ready = False
        self._opens: list[float] = []
        self._closes: list[float] = []
        self._minutes: list[int] = []
        self._pending: Break | None = None
        self._open: OpenTrade | None = None
        self._n = 0
        self._realized_inr = 0.0
        self.desk_events: list[dict[str, Any]] = []
        self.trades: list[TradeRow] = []

    def on_session_start(self, ctx: SessionContext) -> None:
        self._box = None
        self._width = 0.0
        self._tc = 0.0
        self._bc = 0.0
        self._cpr_ready = False
        self._opens = []
        self._closes = []
        self._minutes = []
        self._pending = None
        self._open = None
        self._n = 0
        self._realized_inr = 0.0
        self.desk_events = []
        self.trades = []
        cfg = ctx.config
        ph, pl, pc = cfg.get("prior_high"), cfg.get("prior_low"), cfg.get("prior_close")
        if (
            isinstance(ph, (int, float))
            and isinstance(pl, (int, float))
            and isinstance(pc, (int, float))
        ):
            _p, self._bc, self._tc = cpr_levels(float(ph), float(pl), float(pc))
            self._cpr_ready = True
        day_open = cfg.get("day_open")
        if isinstance(day_open, (int, float)) and float(day_open) > 0:
            self._width = box_width(float(day_open))
            self._box = RangeBoxState(width=self._width)

    def _ensure_cpr(self, view: FeatureView) -> bool:
        if self._cpr_ready:
            return True
        ph, pl, pc = (
            feat_f(view, "prior_high"),
            feat_f(view, "prior_low"),
            feat_f(view, "prior_close"),
        )
        if ph is None or pl is None or pc is None:
            return False
        _p, self._bc, self._tc = cpr_levels(ph, pl, pc)
        self._cpr_ready = True
        return True

    def _ensure_box(self, bar: Bar, view: FeatureView) -> bool:
        if self._box is not None:
            return True
        raw = feat_f(view, "day_open")
        open_px = raw if raw is not None and raw > 0 else bar.open
        if open_px <= 0:
            return False
        self._width = box_width(open_px)
        self._box = RangeBoxState(width=self._width)
        return True

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]:
        if self.meta.stage in LIVE_STAGES:
            return []
        if "NIFTY" not in bar.instrument_id.upper():
            return []
        if not self._ensure_cpr(view) or not self._ensure_box(bar, view):
            return []
        assert self._box is not None
        ts = as_ist(bar.available_ts)
        minute = ts.hour * 60 + ts.minute
        self._opens.append(bar.open)
        self._closes.append(bar.close)
        self._minutes.append(minute)
        i = len(self._closes) - 1

        signals: list[Signal] = []
        if self._pending is not None and self._open is None:
            self._open_from_pending(bar, view, i, minute)

        found = self._box.on_bar(bar.high, bar.low, bar.close, minute)
        busy = self._open is not None or self._pending is not None
        if (
            found is not None
            and not busy
            and self._n < MAX_TRADES_DAY
            and cell_ok(
                side=found.side,
                open_px=bar.open,
                close=bar.close,
                width=self._width,
                tc=self._tc,
                bc=self._bc,
                minute=minute,
            )
        ):
            signals.append(self._emit_break(bar, view, found))

        if self._open is not None:
            self._mark_open(bar, view, i, minute)
        return signals

    def _emit_break(self, bar: Bar, view: FeatureView, found: Break) -> Signal:
        del view
        opt = "CE" if found.side == "UP" else "PE"
        self._n += 1
        self._pending = found
        entry_min = found.minute + 1
        plan = ExitPlan(
            catastrophic=EXIT_PLAN.catastrophic,
            trail=EXIT_PLAN.trail,
            flat_by_ist="15:15",
        )
        return Signal(
            signal_id=signal_id(STRATEGY_ID, VERSION, "NIFTY", bar.available_ts, self._n),
            strategy_id=STRATEGY_ID,
            underlying="NIFTY",
            side=opt,
            strike_rule="ATM",
            strike_choice=fixed_strike("ATM"),
            decision_ts=bar.available_ts,
            confidence=0.5,
            exit_plan=plan,
            reasons=(
                "RB1_BOX_BREAK",
                CELL_ID,
                f"BUY_{opt}",
                "PAPER_ONLY",
                "LIVE_REFUSED",
                "SHADOW_ONLY",
            ),
            features={
                "sig_min": float(found.minute),
                "entry_min": float(entry_min),
                "bh": found.bh,
                "bl": found.bl,
                "W": self._width,
                "lots": float(LOTS),
                "lot_size": float(NIFTY_LOT),
                "qty": float(LOTS * NIFTY_LOT),
            },
        )

    def _open_from_pending(self, bar: Bar, view: FeatureView, i: int, minute: int) -> None:
        pending = self._pending
        self._pending = None
        if pending is None:
            return
        opt = "CE" if pending.side == "UP" else "PE"
        self._open = OpenTrade(
            side=opt,
            bl=pending.bl,
            bh=pending.bh,
            break_i=pending.i,
            entry_i=i,
            entry_min=minute,
            entry_idx=bar.open,
            entry_ask=_option_px(view, opt, "ask"),
        )

    def _mark_open(self, bar: Bar, view: FeatureView, i: int, minute: int) -> None:
        trade = self._open
        if trade is None:
            return
        mark = _option_px(view, trade.side, "bid")
        if trade.entry_ask is not None and mark is not None:
            if desk_premium_stop_would_fire(trade.entry_ask, mark) and not trade.desk_stop_logged:
                self._log_desk(
                    "DESK_PREMIUM_STOP_15PCT",
                    minute,
                    extra={"entry_ask": trade.entry_ask, "mark": mark},
                )
                trade.desk_stop_logged = True
            mtm = premium_pnl_inr(trade.entry_ask, mark)
            if desk_daily_cap_would_fire(self._realized_inr, mtm) and not trade.desk_cap_logged:
                self._log_desk(
                    "DESK_DAILY_CAP_30K",
                    minute,
                    extra={"realized_inr": self._realized_inr, "open_mtm_inr": mtm},
                )
                trade.desk_cap_logged = True
        reason, best = exit_reason(
            minute=minute,
            close=bar.close,
            bl=trade.bl,
            bh=trade.bh,
            side=trade.side,
            entry_idx=trade.entry_idx,
            best_fav=trade.best_fav,
        )
        trade.best_fav = best
        if reason is None:
            return
        if trade.entry_ask is not None and mark is not None:
            self._realized_inr += premium_pnl_inr(trade.entry_ask, mark)
        sig_min = (
            self._minutes[trade.break_i]
            if 0 <= trade.break_i < len(self._minutes)
            else trade.entry_min
        )
        self.trades.append(
            TradeRow(
                sig_min=sig_min,
                side=trade.side,
                entry_min=trade.entry_min,
                exit_min=minute,
                exit_reason=reason,
                bh=trade.bh,
                bl=trade.bl,
                break_i=trade.break_i,
                entry_i=trade.entry_i,
                exit_i=i,
            )
        )
        self._open = None

    def _log_desk(self, kind: str, minute: int, extra: dict[str, float]) -> None:
        payload = {"kind": kind, "minute": minute, "strategy_id": STRATEGY_ID, **extra}
        self.desk_events.append(payload)
        logger.info("RB1 %s would fire minute=%s extra=%s", kind, minute, extra)

    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]:
        del snap, view
        return []

    def on_position(self, update: PositionUpdate) -> list[ExitRequest]:
        trade = self._open
        if trade is None:
            return []
        if desk_daily_cap_would_fire(self._realized_inr, float(update.unrealized_pnl)) and (
            not trade.desk_cap_logged
        ):
            self._log_desk(
                "DESK_DAILY_CAP_30K",
                self._minutes[-1] if self._minutes else 0,
                extra={
                    "realized_inr": self._realized_inr,
                    "open_mtm_inr": float(update.unrealized_pnl),
                },
            )
            trade.desk_cap_logged = True
        mark = float(update.avg_price)
        if (
            trade.entry_ask is not None
            and mark > 0
            and desk_premium_stop_would_fire(trade.entry_ask, mark)
            and not trade.desk_stop_logged
        ):
            self._log_desk(
                "DESK_PREMIUM_STOP_15PCT",
                self._minutes[-1] if self._minutes else 0,
                extra={"entry_ask": trade.entry_ask, "mark": mark},
            )
            trade.desk_stop_logged = True
        return []

    def on_session_end(self) -> dict[str, Any]:
        return {
            "signals_emitted": self._n,
            "stage": "shadow",
            "orders": "REFUSED",
            "live": False,
            "cell_id": CELL_ID,
            "desk_events": list(self.desk_events),
            "trades": [
                {
                    "sig_min": row.sig_min,
                    "side": row.side,
                    "entry_min": row.entry_min,
                    "exit_min": row.exit_min,
                    "exit_reason": row.exit_reason,
                }
                for row in self.trades
            ],
        }


def _option_px(view: FeatureView, side: str, which: str) -> float | None:
    named = f"atm_{side.lower()}_{which}"
    raw = feat_f(view, named)
    if raw is not None and raw > 0:
        return raw
    mid = feat_f(view, f"atm_{side.lower()}")
    if mid is not None and mid > 0:
        return mid
    fallback = feat_f(view, which)
    if fallback is not None and fallback > 0:
        return fallback
    return None


strategy = Rb1Box1mCprPlugin()
