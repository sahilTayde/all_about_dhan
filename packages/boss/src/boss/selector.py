"""V2-07 boss selector. Paper only; never calls a broker or constructs a Dhan client.

Turns strategy signals into at most one DECISION per underlying per bar
(architecture §2.6). Frozen legacy path: `orchestrator.py` (do not import it).
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from contracts.clock import IST, Clock
from contracts.instruments import India
from contracts.payloads import Decision, StrikeChoice
from desk_ml.regime.intermarket import intermarket_regime
from desk_ml.regime.weights import WeightConfig, cap_shares
from strategies.api import Signal
from strategies.registry import Basket, BasketEntry

ENGINE_YAML = Path("config/v2/engine.yaml")
PAPER_STAGES = ("paper", "live_eligible")
HOLD_CONFLICT = "CONFLICT"
HOLD_BELOW_MIN_LOTS = "BELOW_MIN_LOTS"
HOLD_NOT_IN_BASKET = "NOT_IN_BASKET"
HOLD_STAGE = "STAGE_NOT_PAPER"
HOLD_ATM_EXPIRY = "ATM_EXPIRY"
HOLD_FEED_DOWN = "FEED_DOWN"
HOLD_FEED_STALE = "FEED_STALE"
HOLD_FOUNDER_PAUSE = "FOUNDER_PAUSE"
HOLD_FOUNDER_STOP = "FOUNDER_STOP"
HOLD_EVENT_DAY = "EVENT_DAY"
HOLD_NEWS = "NEWS_HOLD"
HOLD_RECON = "RECON_MISMATCH"


class LookAheadError(ValueError):
    """REG-01: a value stamped after decision time was offered to the selector."""


class BasketFrozenError(ValueError):
    """K5: the session basket is fixed; founder may remove, not add."""


class EngineConfigError(ValueError):
    """engine.yaml is missing or not a mapping (fail closed)."""


@dataclass(frozen=True)
class HoldWindow:
    """One clock-window hold loaded from engine.yaml."""

    id: str
    start: time
    end: time
    except_specs: tuple[str, ...]


@dataclass(frozen=True)
class EngineConfig:
    """Parsed `config/v2/engine.yaml` (holds, sizing, regime.mode)."""

    timezone: timezone
    founder_pause: bool
    founder_stop: bool
    event_day: bool
    news_hold: bool
    recon_mismatch: bool
    feed_status_holds: tuple[str, ...]
    no_atm_on_expiry_day: bool
    windows: tuple[HoldWindow, ...]
    volsize_ref_lots: float
    volsize_ref_em30: float
    risk_budget_inr: float
    min_lots: int
    regime_mode: str
    paper_stages: tuple[str, ...]
    raw: dict[str, Any]
    config_hash: str


@dataclass(frozen=True)
class BarContext:
    """Per-bar inputs. Every timestamp must be IST-aware; no future stamps."""

    underlying: str
    bar_ts: datetime
    available_ts: datetime
    feed_status: str = "UP"
    recon_ok: bool = True
    event_day: bool = False
    news_hold: bool = False
    founder_pause: bool = False
    founder_stop: bool = False
    is_expiry: bool = False
    em30: float | None = None
    delta: float | None = None
    stop: float | None = None
    regime_label: str = "unknown"
    intermarket: dict[str, Any] = field(default_factory=dict)
    intermarket_closes: Mapping[str, Sequence[tuple[str, float]]] | None = None
    weights: Mapping[str, float] | None = None
    signal_stages: Mapping[str, str] = field(default_factory=dict)


@dataclass
class SessionBasketGate:
    """Session-fixed basket (K5). Founder may remove entries, never add."""

    basket: Basket
    removed: set[str] = field(default_factory=set)

    def active_ids(self) -> set[str]:
        return {e.strategy_id for e in self.basket.entries} - self.removed

    def entry(self, strategy_id: str) -> BasketEntry | None:
        if strategy_id in self.removed:
            return None
        return next((e for e in self.basket.entries if e.strategy_id == strategy_id), None)

    def remove(self, strategy_id: str) -> None:
        if strategy_id not in {e.strategy_id for e in self.basket.entries}:
            raise KeyError(f"BASKET_REMOVE: {strategy_id} is not in the session basket")
        self.removed.add(strategy_id)

    def add(self, entry: BasketEntry) -> None:
        raise BasketFrozenError(
            f"K5: BASKET_ADD {entry.strategy_id} rejected; founder may remove, not add"
        )


@dataclass(frozen=True)
class SelectorResult:
    """One bar of boss output: decisions plus published BOSS_SHADOW events."""

    decisions: tuple[Decision, ...]
    shadow_events: tuple[dict[str, Any], ...]
    strike_choices: dict[str, StrikeChoice]


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def _aware(ts: datetime | str, label: str) -> datetime:
    dt = ts if isinstance(ts, datetime) else datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware IST")
    return dt


def engine_config_hash(raw: Mapping[str, Any]) -> str:
    """Hash of the hold/sizing document (REG-13 companion for engine.yaml)."""
    blob = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def load_engine_config(path: Path | None = None) -> EngineConfig:
    """Load holds and sizing from YAML. Missing file → fail closed."""
    import yaml  # type: ignore[import-untyped]

    target = path if path is not None else ENGINE_YAML
    if not target.is_file():
        raise EngineConfigError(f"missing engine config: {target}")
    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise EngineConfigError("engine.yaml must be a mapping")
    holds = dict(loaded.get("holds") or {})
    sizing = dict(loaded.get("sizing") or {})
    regime = dict(loaded.get("regime") or {})
    windows = tuple(
        HoldWindow(
            id=str(w["id"]),
            start=_parse_hhmm(str(w["start"])),
            end=_parse_hhmm(str(w["end"])),
            except_specs=tuple(w.get("except_specs") or ()),
        )
        for w in holds.get("windows") or ()
    )
    stages = tuple(loaded.get("paper_stages") or PAPER_STAGES)
    tz_raw = str(loaded.get("timezone") or "+05:30")
    sign = 1 if tz_raw.startswith("+") else -1
    hh, mm = tz_raw[1:].split(":", 1)
    tz = timezone(sign * timedelta(hours=int(hh), minutes=int(mm)))
    return EngineConfig(
        timezone=tz,
        founder_pause=bool(holds.get("founder_pause", False)),
        founder_stop=bool(holds.get("founder_stop", False)),
        event_day=bool(holds.get("event_day", False)),
        news_hold=bool(holds.get("news_hold", False)),
        recon_mismatch=bool(holds.get("recon_mismatch", False)),
        feed_status_holds=tuple(holds.get("feed_status_holds") or ("DOWN", "STALE")),
        no_atm_on_expiry_day=bool(holds.get("no_atm_on_expiry_day", True)),
        windows=windows,
        volsize_ref_lots=float(sizing.get("volsize_ref_lots", 25)),
        volsize_ref_em30=float(sizing.get("volsize_ref_em30", 27.4)),
        risk_budget_inr=float(sizing.get("risk_budget_inr", 30000)),
        min_lots=int(sizing.get("min_lots", 2)),
        regime_mode=str(regime.get("mode") or "shadow"),
        paper_stages=stages,
        raw=loaded,
        config_hash=engine_config_hash(loaded),
    )


def volsize(em30: float, cfg: EngineConfig) -> int:
    """Round 8 §3.0 VOLSIZE(EM30) = round(ref_lots * ref_em30 / EM30)."""
    if em30 <= 0:
        raise ValueError("EM30 must be positive")
    return int(round(cfg.volsize_ref_lots * cfg.volsize_ref_em30 / em30))


def caplots(risk_budget_inr: float, delta: float, stop: float, lot_size: int) -> int:
    """Round 8 §3.0 CAPLOTS = floor(risk_budget / (δ × stop × lot_size))."""
    if delta <= 0 or stop <= 0 or lot_size <= 0:
        raise ValueError("delta, stop and lot_size must be positive")
    return int(risk_budget_inr // (delta * stop * lot_size))


def size_lots(
    *,
    em30: float,
    delta: float,
    stop: float,
    lot_size: int,
    basket_max: int,
    cfg: EngineConfig,
) -> tuple[int | None, dict[str, int]]:
    """lots = min(basket_max, VOLSIZE, CAPLOTS); None when below min_lots."""
    vs = volsize(em30, cfg)
    cap = caplots(cfg.risk_budget_inr, delta, stop, lot_size)
    lots = min(int(basket_max), vs, cap)
    sizing = {"volsize": vs, "caplots": cap, "basket_max": int(basket_max)}
    if lots < cfg.min_lots:
        return None, sizing
    return lots, sizing


def in_window(now: datetime, window: HoldWindow) -> bool:
    """True when the IST clock sits in [start, end)."""
    clock = now.astimezone(IST).time()
    if window.start <= window.end:
        return window.start <= clock < window.end
    return clock >= window.start or clock < window.end


def evaluate_holds(
    cfg: EngineConfig,
    ctx: BarContext,
    now: datetime,
    *,
    strategy_id: str | None = None,
    chosen_rule: str | None = None,
) -> list[str]:
    """Return every hold reason that applies. Reasons come from engine.yaml + ctx."""
    reasons: list[str] = []
    if cfg.founder_pause or ctx.founder_pause:
        reasons.append(HOLD_FOUNDER_PAUSE)
    if cfg.founder_stop or ctx.founder_stop:
        reasons.append(HOLD_FOUNDER_STOP)
    if cfg.event_day or ctx.event_day:
        reasons.append(HOLD_EVENT_DAY)
    if cfg.news_hold or ctx.news_hold:
        reasons.append(HOLD_NEWS)
    if cfg.recon_mismatch or not ctx.recon_ok:
        reasons.append(HOLD_RECON)
    feed = ctx.feed_status.upper()
    if feed in cfg.feed_status_holds:
        reasons.append(HOLD_FEED_DOWN if feed == "DOWN" else HOLD_FEED_STALE if feed == "STALE" else f"FEED_{feed}")
    for window in cfg.windows:
        if in_window(now, window) and (strategy_id is None or strategy_id not in window.except_specs):
            reasons.append(window.id)
    if cfg.no_atm_on_expiry_day and ctx.is_expiry and chosen_rule == "ATM":
        reasons.append(HOLD_ATM_EXPIRY)
    return reasons


def _instrument_id(choice: StrikeChoice) -> str | None:
    for alt in choice.alternatives:
        if alt.rule == choice.chosen and alt.instrument_id:
            return alt.instrument_id
    return None


def _decision_id(underlying: str, now: datetime, n: int) -> str:
    stamp = now.astimezone(IST)
    return f"dc_{underlying.lower()}_{stamp.strftime('%Y%m%d')}_{stamp.strftime('%H%M')}_{n}"


def _refuse_future(now: datetime, stamped: datetime, label: str) -> None:
    if stamped > now:
        raise LookAheadError(f"REG-01: {label} {stamped.isoformat()} is after {now.isoformat()}")


class BossSelector:
    """Basket gate, holds, conflicts, VOLSIZE/CAPLOTS, shadow ranks. No broker."""

    def __init__(
        self,
        *,
        clock: Clock,
        config: EngineConfig,
        basket: SessionBasketGate,
        lot_size_fn: Callable[[str], int] | None = None,
    ) -> None:
        self.clock = clock
        self.config = config
        self.basket = basket
        self._lot_size = lot_size_fn or India().lot_size
        self._seq = 0

    def basket_remove(self, strategy_id: str) -> None:
        """Founder `BASKET_REMOVE {strategy_id}` (K5)."""
        self.basket.remove(strategy_id)

    def basket_add(self, entry: BasketEntry) -> None:
        """Always rejected (K5)."""
        self.basket.add(entry)

    def decide(self, signals: Sequence[Signal], ctx: BarContext) -> SelectorResult:
        """One decision per underlying. Shadow ranks never change the ENTER/HOLD."""
        now = self.clock.now()
        if now.tzinfo is None:
            raise ValueError("engine clock must be timezone-aware")
        bar_ts = _aware(ctx.bar_ts, "bar_ts")
        avail = _aware(ctx.available_ts, "available_ts")
        _refuse_future(now, bar_ts, "bar_ts")
        _refuse_future(now, avail, "available_ts")
        grouped: dict[str, list[Signal]] = defaultdict(list)
        for sig in signals:
            decision_ts = _aware(sig.decision_ts, "signal.decision_ts")
            _refuse_future(now, decision_ts, f"signal {sig.signal_id} decision_ts")
            if sig.underlying == ctx.underlying:
                grouped[sig.underlying].append(sig)
        decisions: list[Decision] = []
        shadows: list[dict[str, Any]] = []
        choices: dict[str, StrikeChoice] = {}
        for underlying, group in grouped.items():
            decision, shadow, choice = self._one_underlying(group, ctx, now)
            decisions.append(decision)
            shadows.append(shadow)
            if choice is not None:
                choices[decision.decision_id] = choice
        return SelectorResult(tuple(decisions), tuple(shadows), choices)

    def _one_underlying(
        self, signals: list[Signal], ctx: BarContext, now: datetime
    ) -> tuple[Decision, dict[str, Any], StrikeChoice | None]:
        weights = self._weights([s.strategy_id for s in signals], ctx)
        intermarket = self._intermarket(ctx)
        shadow = self._boss_shadow(signals, ctx, weights, intermarket)
        gated, gate_holds = self._basket_gate(signals, ctx)
        if not gated:
            return (
                self._emit("HOLD", ctx, now, signals, shadow, holds=gate_holds or [HOLD_NOT_IN_BASKET]),
                shadow,
                None,
            )
        sides = {s.side for s in gated}
        if len(sides) > 1:
            winner = self._priority_side(gated, weights)
            if winner is None:
                return self._emit("HOLD", ctx, now, gated, shadow, holds=[HOLD_CONFLICT]), shadow, None
            gated = [s for s in gated if s.side == winner]
        pick = max(gated, key=lambda s: (weights.get(s.strategy_id, 1.0), s.signal_id))
        holds = evaluate_holds(
            self.config, ctx, now, strategy_id=pick.strategy_id, chosen_rule=pick.strike_choice.chosen
        )
        if holds:
            return self._emit("HOLD", ctx, now, gated, shadow, holds=holds), shadow, pick.strike_choice
        entry = self.basket.entry(pick.strategy_id)
        basket_max = entry.max_lots if entry is not None else 0
        if ctx.em30 is None or ctx.delta is None or ctx.stop is None:
            return (
                self._emit("HOLD", ctx, now, gated, shadow, holds=[HOLD_BELOW_MIN_LOTS]),
                shadow,
                pick.strike_choice,
            )
        lots, sizing = size_lots(
            em30=ctx.em30,
            delta=ctx.delta,
            stop=ctx.stop,
            lot_size=self._lot_size(ctx.underlying),
            basket_max=basket_max,
            cfg=self.config,
        )
        if lots is None:
            return (
                self._emit("HOLD", ctx, now, gated, shadow, holds=[HOLD_BELOW_MIN_LOTS], sizing=sizing),
                shadow,
                pick.strike_choice,
            )
        return (
            self._emit("ENTER", ctx, now, gated, shadow, lots=lots, sizing=sizing, choice=pick.strike_choice),
            shadow,
            pick.strike_choice,
        )

    def _basket_gate(self, signals: Sequence[Signal], ctx: BarContext) -> tuple[list[Signal], list[str]]:
        kept: list[Signal] = []
        holds: list[str] = []
        active = self.basket.active_ids()
        for sig in signals:
            if sig.strategy_id not in active:
                holds.append(HOLD_NOT_IN_BASKET)
                continue
            stage = ctx.signal_stages.get(sig.strategy_id, "shadow")
            if stage not in self.config.paper_stages:
                holds.append(HOLD_STAGE)
                continue
            kept.append(sig)
        return kept, list(dict.fromkeys(holds))

    def _priority_side(self, signals: Sequence[Signal], weights: Mapping[str, float]) -> str | None:
        best: dict[str, float] = {}
        for sig in signals:
            w = weights.get(sig.strategy_id, 1.0)
            entry = self.basket.entry(sig.strategy_id)
            if entry is not None:
                w = max(w, float(entry.weight))
            best[sig.side] = max(best.get(sig.side, 0.0), w)
        if len(best) < 2:
            return next(iter(best), None)
        ordered = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
        if ordered[0][1] > ordered[1][1]:
            return ordered[0][0]
        return None

    def _weights(self, strategy_ids: Sequence[str], ctx: BarContext) -> dict[str, float]:
        raw = dict(ctx.weights or {})
        cfg = WeightConfig(static_weights=raw)
        return cap_shares({sid: cfg.static(sid) for sid in strategy_ids}, cfg.max_share)

    def _intermarket(self, ctx: BarContext) -> dict[str, Any]:
        if ctx.intermarket:
            return dict(ctx.intermarket)
        if ctx.intermarket_closes:
            return intermarket_regime(ctx.intermarket_closes)
        return {"regime": "unknown"}

    def _boss_shadow(
        self,
        signals: Sequence[Signal],
        ctx: BarContext,
        weights: Mapping[str, float],
        intermarket: Mapping[str, Any],
    ) -> dict[str, Any]:
        ranks = sorted(
            (
                {"strategy_id": s.strategy_id, "side": s.side, "weight": float(weights.get(s.strategy_id, 1.0))}
                for s in signals
            ),
            key=lambda row: (-float(row["weight"]), str(row["strategy_id"])),
        )
        return {
            "event_type": "BOSS_SHADOW",
            "mode": self.config.regime_mode,
            "regime": ctx.regime_label,
            "ranks": ranks,
            "intermarket": dict(intermarket),
            "decision_unchanged": True,
        }

    def _shadow_block(self, shadow: Mapping[str, Any], choice: StrikeChoice | None) -> dict[str, Any]:
        block = {
            "regime": shadow.get("regime"),
            "ranks": list(shadow.get("ranks") or ()),
            "intermarket": dict(shadow.get("intermarket") or {}),
            "mode": shadow.get("mode"),
        }
        if choice is not None:
            block["strike_choice"] = {
                "chosen": choice.chosen,
                "reason": choice.reason,
                "rule_version": choice.rule_version,
            }
        return block

    def _emit(
        self,
        kind: str,
        ctx: BarContext,
        now: datetime,
        signals: Sequence[Signal],
        shadow: Mapping[str, Any],
        *,
        holds: Sequence[str] = (),
        lots: int | None = None,
        sizing: dict[str, int] | None = None,
        choice: StrikeChoice | None = None,
    ) -> Decision:
        self._seq += 1
        picked = choice or (signals[0].strike_choice if signals else None)
        return Decision(
            decision_id=_decision_id(ctx.underlying, now, self._seq),
            underlying=ctx.underlying,
            decision=kind,
            signal_ids=[s.signal_id for s in signals],
            instrument_id=_instrument_id(picked) if picked is not None else None,
            lots=lots,
            lot_size=self._lot_size(ctx.underlying),
            limit_price=None,
            sizing=sizing,
            holds=list(holds),
            basket_hash=self.basket.basket.basket_hash,
            shadow=self._shadow_block(shadow, picked),
            entry_location=None,
            stretch=None,
        )
