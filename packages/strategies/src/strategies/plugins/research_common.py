"""Shared C5 paper research-slot helpers. Option buying only. Live refused.

R01 / R01_B3A_VOL math stays in desk_ml.research_rules — this module calls it.
R07 / B8a / B8b add only the frozen lab gates (ER30, 10:30 window) on top.
"""

from __future__ import annotations

from typing import Any

from contracts.ids import signal_id
from contracts.payloads import (
    CatastrophicStop,
    ExitPlan,
    Level,
    StrikeChoice,
    StrikeQuote,
    TimeStop,
)
from desk_ml import research_rules as rr

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
from strategies.plugins.lab_lock import as_ist, feat, feat_f

VERSION = "1.0.0"
HOLD_MIN = 20
ER30_TREND = 0.35
ER30_SIDEWAYS = 0.20
ER30_LOOKBACK = 30
ER30_MIN_OBS = 20
WINDOW_DEFAULT = ("09:30", "14:50")
WINDOW_B8A = ("10:30", "14:50")
UNDERLYINGS = ("NIFTY", "SENSEX")
FEATURES = ("idx", "atm", "atm_ce", "atm_pe", "underlying")
LIVE_STAGES = frozenset({"live", "live_eligible", "limited_live"})

EXIT_PLAN = ExitPlan(
    catastrophic=CatastrophicStop(level=Level(kind="max_loss_inr", price=30000.0)),
    structural=None,
    time_stops=(TimeStop(after_s=HOLD_MIN * 60, when="always"),),
    flat_by_ist="15:15",
)

R01_RULE = next(row for row in rr.FROZEN_RULES if row["rule_id"] == rr.R01)
R01_B3A_RULE = next(row for row in rr.FROZEN_RULES if row["rule_id"] == rr.R01_B3A)
R07_RULE: dict[str, Any] = {
    "rule_id": "R07_MOM3_TREND",
    "family": "MOM",
    "params": {"k": 3, "thr": 0.0005},
    "regime_filter": "TREND",
    "hold_min": HOLD_MIN,
}

SLOT_IDS = (
    "R01_PDIV_5_ALL_H20",
    "R01_B3A_VOL",
    "B8B_B3A_EX_CHOPPY",
    "R07_MOM3_TREND",
    "B8A_R07_NO_PRE1030",
)


def er30(bars: dict[str, dict[str, Any]], t: str) -> float | None:
    """Roster ER30: |idx_t - idx_{t-30}| / sum |1m diffs| on observed minutes.

    Needs >= 20 observed index prints in [t-30, t]; else None.
    TREND >= 0.35; SIDEWAYS 0.20-0.35; CHOPPY < 0.20 (roster.json common).
    """
    vals: list[float] = []
    for j in range(ER30_LOOKBACK, -1, -1):
        bar = bars.get(rr.mplus(t, -j))
        if not bar:
            continue
        idx = feat_num(bar.get("idx"))
        if idx is None:
            continue
        vals.append(idx)
    if len(vals) < ER30_MIN_OBS:
        return None
    diffs = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    path = sum(abs(delta) for delta in diffs)
    net = abs(vals[-1] - vals[0])
    if path <= 1e-12:
        return 0.0 if net <= 1e-12 else None
    return net / path


def feat_num(raw: object) -> float | None:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    val = float(raw)
    if val <= 0:
        return None
    return val


def hhmm_of(bar: Bar) -> str:
    ts = as_ist(bar.available_ts)
    return f"{ts.hour:02d}:{ts.minute:02d}"


def underlying_of(bar: Bar, view: FeatureView) -> str | None:
    raw = feat(view, "underlying")
    if isinstance(raw, str) and raw.strip():
        name = raw.strip().upper()
        if name in UNDERLYINGS:
            return name
        return None
    inst = bar.instrument_id.upper()
    for name in UNDERLYINGS:
        if name in inst:
            return name
    return None


def atm_choice() -> StrikeChoice:
    empty = StrikeQuote(
        rule="ATM",
        instrument_id="",
        bid=None,
        ask=None,
        mid=None,
        spread=None,
        quote_age_ms=None,
        est_delta=None,
        est_round_trip_pts=None,
    )
    return StrikeChoice(
        chosen="ATM",
        reason="SIGNAL_MINUTE_ATM",
        rule_version="roster25-v1",
        alternatives=(empty,),
    )


def size_for(underlying: str) -> tuple[int, int, int]:
    """Return (qty, lots, lot_size). NIFTY 650 / SENSEX 200 at 10 lots."""
    und = underlying.upper()
    return int(rr.QTY[und]), int(rr.LOTS), int(rr.LOT_SIZE[und])


def in_signal_window(minutes: list[str], t: str, window: tuple[str, str]) -> bool:
    if not minutes:
        return False
    if t < rr.mplus(minutes[0], rr.WARMUP_MIN):
        return False
    return window[0] <= t <= window[1]


def _bar_cell(bar: Bar, view: FeatureView) -> dict[str, Any] | None:
    idx = feat_f(view, "idx")
    if idx is None or idx <= 0:
        idx = feat_num(bar.close)
    atm = feat_f(view, "atm")
    ce = feat_f(view, "atm_ce")
    if ce is None:
        ce = feat_f(view, "ce")
    pe = feat_f(view, "atm_pe")
    if pe is None:
        pe = feat_f(view, "pe")
    if idx is None or atm is None or ce is None or pe is None:
        return None
    if idx <= 0 or atm <= 0 or ce <= 0 or pe <= 0:
        return None
    return {
        "idx": idx,
        "atm": atm,
        "ce": ce,
        "pe": pe,
        "wings": {str(int(atm)) if float(atm) == int(atm) else str(atm): {"ce": ce, "pe": pe}},
    }


def decide_side(
    rule: dict[str, Any],
    bars: dict[str, dict[str, Any]],
    t: str,
    underlying: str,
    min_er: float | None,
) -> str | None:
    side = rr.signal(rule, bars, t, underlying=underlying)
    if side not in ("CE", "PE"):
        return None
    if min_er is None:
        return side
    ratio = er30(bars, t)
    if ratio is None or ratio < float(min_er):
        return None
    return side


def params_for(
    *,
    strategy_id: str,
    rule: dict[str, Any],
    window: tuple[str, str],
    min_er: float | None,
) -> dict[str, Any]:
    return {
        "strategy_id": strategy_id,
        "family": rule["family"],
        "params": dict(rule["params"]),
        "regime_filter": rule.get("regime_filter", "ALL"),
        "vol_gate": bool(rule.get("vol_gate")),
        "min_er": min_er,
        "hold_min": HOLD_MIN,
        "window": list(window),
        "warmup_min": rr.WARMUP_MIN,
        "qty": dict(rr.QTY),
        "lots": rr.LOTS,
        "lot_size": dict(rr.LOT_SIZE),
        "side": "BUY_ONLY",
        "orders": "REFUSED",
        "live": False,
        "exit_plan": EXIT_PLAN,
    }


SLOT_SPECS: dict[str, dict[str, Any]] = {
    "R01_PDIV_5_ALL_H20": {
        "rule": R01_RULE,
        "window": WINDOW_DEFAULT,
        "min_er": None,
        "reasons": ("R01_PDIV_5", "ALL", "H20"),
    },
    "R01_B3A_VOL": {
        "rule": R01_B3A_RULE,
        "window": WINDOW_DEFAULT,
        "min_er": None,
        "reasons": ("R01_PDIV_5", "B3A_VOL", "H20"),
    },
    "B8B_B3A_EX_CHOPPY": {
        "rule": R01_B3A_RULE,
        "window": WINDOW_DEFAULT,
        "min_er": ER30_SIDEWAYS,
        "reasons": ("B8B_B3A_EX_CHOPPY", "ER30_GE_0.20", "H20"),
    },
    "R07_MOM3_TREND": {
        "rule": R07_RULE,
        "window": WINDOW_DEFAULT,
        "min_er": ER30_TREND,
        "reasons": ("R07_MOM3_TREND", "ER30_GE_0.35", "H20"),
    },
    "B8A_R07_NO_PRE1030": {
        "rule": R07_RULE,
        "window": WINDOW_B8A,
        "min_er": ER30_TREND,
        "reasons": ("B8A_R07_NO_PRE1030", "NO_PRE1030", "ER30_GE_0.35", "H20"),
    },
}


class ResearchSlotPlugin:
    """One frozen research rule. Emits CE/PE buy signals. Never places orders."""

    def __init__(self, strategy_id: str) -> None:
        if strategy_id not in SLOT_SPECS:
            raise ValueError(f"unknown research slot {strategy_id}")
        spec = SLOT_SPECS[strategy_id]
        self.strategy_id = strategy_id
        self.rule: dict[str, Any] = spec["rule"]
        self.window: tuple[str, str] = spec["window"]
        self.min_er: float | None = spec["min_er"]
        self.reason_tags: tuple[str, ...] = spec["reasons"]
        params = params_for(
            strategy_id=strategy_id,
            rule=self.rule,
            window=self.window,
            min_er=self.min_er,
        )
        self.params = params
        params_hash = compute_params_hash(params)
        stage = "paper"
        if stage in LIVE_STAGES:
            raise RuntimeError(f"{strategy_id}: live refused")
        self.meta = StrategyMeta(
            strategy_id=strategy_id,
            version=VERSION,
            params_hash=params_hash,
            markets=("IN_INDEX_OPT",),
            underlyings=UNDERLYINGS,
            inputs=("bars:1m", "chain"),
            features=FEATURES,
            stage=stage,
            max_positions=2,
            entry_policy=EntryPolicy(),
            legacy_logic_from=(),
        )
        self.exit_plan = EXIT_PLAN
        self._bars: dict[str, dict[str, dict[str, Any]]] = {}
        self._busy: dict[str, str] = {}
        self._n = 0

    def on_session_start(self, ctx: SessionContext) -> None:
        del ctx
        self._bars = {}
        self._busy = {}
        self._n = 0

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]:
        if self.meta.stage in LIVE_STAGES:
            return []
        und = underlying_of(bar, view)
        if und is None:
            return []
        cell = _bar_cell(bar, view)
        if cell is None:
            return []
        t = hhmm_of(bar)
        hist = self._bars.setdefault(und, {})
        hist[t] = cell
        minutes = sorted(hist)
        if self.window == WINDOW_DEFAULT:
            if not rr.allowed(minutes, t):
                return []
        elif not in_signal_window(minutes, t, self.window):
            return []
        busy = self._busy.get(und, "")
        if busy and t <= busy:
            return []
        side = decide_side(self.rule, hist, t, und, self.min_er)
        if side is None:
            return []
        qty, lots, lot_size = size_for(und)
        entry_min = rr.mplus(t, 1)
        exit_min = rr.mplus(entry_min, HOLD_MIN)
        self._busy[und] = exit_min
        self._n += 1
        ratio = er30(hist, t)
        features = {
            "idx": float(cell["idx"]),
            "atm": float(cell["atm"]),
            "qty": float(qty),
            "lots": float(lots),
            "lot_size": float(lot_size),
        }
        if ratio is not None:
            features["er30"] = float(ratio)
        return [
            Signal(
                signal_id=signal_id(self.strategy_id, VERSION, und, bar.available_ts, self._n),
                strategy_id=self.strategy_id,
                underlying=und,
                side=side,
                strike_rule="ATM",
                strike_choice=atm_choice(),
                decision_ts=bar.available_ts,
                confidence=0.5,
                exit_plan=self.exit_plan,
                reasons=(*self.reason_tags, f"BUY_{side}", "PAPER_ONLY", "LIVE_REFUSED"),
                features=features,
            )
        ]

    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]:
        del snap, view
        return []

    def on_position(self, update: PositionUpdate) -> list[ExitRequest]:
        del update
        return []

    def on_session_end(self) -> dict[str, Any]:
        return {
            "signals_emitted": self._n,
            "stage": self.meta.stage,
            "orders": "REFUSED",
            "live": False,
        }


def build_plugin(strategy_id: str) -> ResearchSlotPlugin:
    return ResearchSlotPlugin(strategy_id)
