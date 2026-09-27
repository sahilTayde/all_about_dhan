"""V2-09 / V2-09b exit evaluation: plan primitives only. Paper clock."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from math import floor
from pathlib import Path
from typing import Any

from contracts.instruments import India
from contracts.payloads import (
    AtrStop,
    CatastrophicStop,
    ExitPlan,
    GracePeriod,
    Level,
    Partial,
    SignalFlipExit,
    StructuralStop,
    TimeStop,
    Trail,
)
from risk_engine import IST

ALLOWED_REASONS = frozenset(
    {
        "CATASTROPHIC_STOP",
        "STRUCTURAL_STOP",
        "ATR_STOP",
        "TIME_EXIT",
        "SIGNAL_FLIP",
        "TARGET_HIT",
        "PARTIAL",
        "TRAIL_STOP",
        "FLATTEN_EOD",
        "FOUNDER_COMMAND",
        "KILL_SWITCH",
        "STRATEGY_EXIT",
        "FAILSAFE_MTM",
    }
)
# reason → ExitPlan field that must be present (or a non-plan always-on exit).
REASON_PLAN_FIELD = {
    "CATASTROPHIC_STOP": "catastrophic",
    "STRUCTURAL_STOP": "structural",
    "ATR_STOP": "atr",
    "TIME_EXIT": "time_stops",
    "SIGNAL_FLIP": "signal_flip",
    "TARGET_HIT": "target",
    "PARTIAL": "partials",
    "TRAIL_STOP": "trail",
    "FLATTEN_EOD": "flat_by_ist",
    "FOUNDER_COMMAND": "founder",
    "KILL_SWITCH": "kill_switch",
    "STRATEGY_EXIT": "strategy",
    "FAILSAFE_MTM": "mark",
}
ALWAYS_ON_REASONS = frozenset(
    {"FOUNDER_COMMAND", "KILL_SWITCH", "STRATEGY_EXIT", "FAILSAFE_MTM", "FLATTEN_EOD"}
)
STALE_EXEMPT = frozenset({"FLATTEN_EOD", "FOUNDER_COMMAND", "KILL_SWITCH", "FAILSAFE_MTM"})
SEND_ON_CLOCK = frozenset({"TIME_EXIT", "FLATTEN_EOD"})
STALE_MAX_AGE_S = 90.0
FOUNDER_KINDS = frozenset({"CUT_LOSS", "FLATTEN", "FLATTEN_ALL", "KILL"})
TICK_KINDS = frozenset({"TICK", "DEPTH_QUOTE", "QUOTE_SNAPSHOT"})
HOUSE_MAX_LOSS_INR = 30000.0
PREMIUM_TICK = 0.05
DEFAULTS_RELATIVE = Path("config/v2/exits/defaults.yaml")
_INDIA = India()


class ExitPlanLoadError(ValueError):
    """REG-18d / inherit: a plan that cannot be resolved must refuse to load."""


def instrument_lot_size(instrument_id: str) -> int:
    """Lot size from `contracts.instruments.India`, never a hard-coded 65."""
    symbol = str(_INDIA.parse_instrument_id(instrument_id).get("symbol") or "")
    return _INDIA.lot_size(symbol)


def option_side(instrument_id: str) -> str:
    """CE or PE from the held instrument id. Buyer-only desk."""
    parsed = _INDIA.parse_instrument_id(instrument_id)
    raw = str(parsed.get("option_type") or "")
    if raw in {"CE", "PE"}:
        return raw
    return "CE"


def house_stop_premium(entry: float, qty: int, max_loss: float = HOUSE_MAX_LOSS_INR) -> float:
    """Premium stop so qty * (entry - stop) <= max_loss (round 11 house stop)."""
    if qty <= 0:
        raise ValueError("qty must be positive")
    return max(PREMIUM_TICK, round(float(entry) - float(max_loss) / int(qty), 2))


def resolve_catastrophic_premium(plan: ExitPlan, fill_price: float, qty: int) -> float:
    """Use a declared premium, or resolve `max_loss_inr` at the fill."""
    level = plan.catastrophic.level
    if level.kind == "max_loss_inr":
        return house_stop_premium(fill_price, qty, float(level.price))
    if level.kind == "premium":
        return float(level.price)
    return float(level.price)


def freeze_atr_level(side: str, entry_underlying: float, k: float, atr14: float) -> float:
    """ATR stop fixed at the fill: entry -/+ k * ATR14(1m)."""
    offset = float(k) * float(atr14)
    if side == "PE":
        return round(float(entry_underlying) + offset, 2)
    return round(float(entry_underlying) - offset, 2)


def freeze_fill_levels(
    pos: dict[str, Any],
    plan: ExitPlan,
    fill_price: float,
    qty: int,
    *,
    entry_underlying: float | None = None,
    atr14: float | None = None,
) -> None:
    """Freeze house-stop premium and ATR level on the position at the fill."""
    pos["stop_price"] = resolve_catastrophic_premium(plan, fill_price, qty)
    if entry_underlying is not None:
        pos["entry_underlying"] = float(entry_underlying)
    if atr14 is not None:
        pos["atr14"] = float(atr14)
    atr = plan.atr
    under = pos.get("entry_underlying", entry_underlying)
    atr_val = pos.get("atr14", atr14)
    if atr is not None and under is not None and atr_val is not None:
        pos["atr_stop_level"] = freeze_atr_level(
            option_side(str(pos.get("instrument_id") or "")),
            float(under),
            float(atr.k),
            float(atr_val),
        )


def load_exit_defaults(path: Path | None = None) -> tuple[dict[str, Any], str]:
    """Load `config/v2/exits/defaults.yaml` and the sha256 of the raw bytes."""
    import yaml

    target = path if path is not None else DEFAULTS_RELATIVE
    raw = target.read_bytes()
    loaded = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(loaded, dict):
        raise ExitPlanLoadError("exit defaults YAML must be a mapping")
    return loaded, hashlib.sha256(raw).hexdigest()


def defaults_from_tag(file_sha256: str) -> str:
    return f"exit_defaults@{file_sha256}"


def assert_exit_reason(req: ExitRequest, plan: ExitPlan) -> None:
    """REG-18a: reason is allowed and names the plan field that fired."""
    if req.reason not in ALLOWED_REASONS:
        raise RuntimeError(f"REG-18a: illegal exit reason {req.reason}")
    expected = REASON_PLAN_FIELD.get(req.reason)
    if expected is None or req.plan_field != expected:
        raise RuntimeError(f"REG-18a: {req.reason} must name {expected}, got {req.plan_field!r}")
    if req.reason in ALWAYS_ON_REASONS:
        return
    field = expected
    value = getattr(plan, field, None)
    if field == "time_stops" and not value:
        raise RuntimeError("REG-18a: TIME_EXIT fired but plan.time_stops is empty")
    if field not in {"time_stops", "flat_by_ist"} and value in (None, (), []):
        raise RuntimeError(f"REG-18a: {req.reason} fired but plan.{field} is absent")


def whole_lots_qty(qty: int, lot_size: int) -> int:
    """Largest whole-lot unit count ≤ qty. Raises if lot_size is not positive."""
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    return (int(qty) // lot_size) * lot_size


def partial_exit_qty(
    *,
    orig_qty: int,
    net_qty: int,
    fraction: float,
    instrument_id: str,
) -> int | None:
    """Units to sell on a PARTIAL, or None to skip.

    close_lots = floor(orig_lots * fraction), minimum 1 lot when the book has
    2+ lots. A 1-lot book skips: a partial is not a flatten.
    """
    lot = instrument_lot_size(instrument_id)
    held_lots = int(net_qty) // lot
    orig_lots = int(orig_qty) // lot
    if held_lots <= 1:
        return None
    close_lots = min(held_lots, max(1, floor(orig_lots * float(fraction))))
    return close_lots * lot


def _held_exit_qty(pos: dict[str, Any]) -> int:
    inst = str(pos.get("instrument_id") or "")
    lot = instrument_lot_size(inst)
    return whole_lots_qty(int(pos.get("net_qty") or 0), lot)


@dataclass(frozen=True)
class ExitRequest:
    reason: str
    plan_field: str
    qty: int
    stale_quote: bool = False
    price_hint: float | None = None
    new_stop: float | None = None


def as_ist(ts: datetime | str) -> datetime:
    dt = ts if isinstance(ts, datetime) else datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(IST)


def parse_hhmm(raw: str) -> time:
    parts = raw.strip().split(":")
    return time(int(parts[0]), int(parts[1] if len(parts) > 1 else 0))


def when_matches(when: str, fill_ts: datetime, expiry: datetime | None) -> bool:
    """First-class TimeStop window. `when` tokens joined by `&`."""
    fill = as_ist(fill_ts)
    exp = as_ist(expiry).date() if expiry is not None else None
    tokens = [t.strip() for t in when.split("&") if t.strip()]
    if not tokens:
        return True
    for token in tokens:
        if token == "always":
            continue
        if token == "expiry_day":
            if exp is None or fill.date() != exp:
                return False
            continue
        if token.startswith("entry_in:"):
            window = token.split(":", 1)[1]
            start_s, end_s = window.split("-", 1)
            start, end = parse_hhmm(start_s), parse_hhmm(end_s)
            if not start <= fill.time() < end:
                return False
            continue
        return False
    return True


def choose_time_stop(plan: ExitPlan, fill_ts: datetime, expiry: datetime | None) -> TimeStop | None:
    """First matching `when` at the fill wins; stored on the position."""
    for stop in plan.time_stops:
        if when_matches(stop.when, fill_ts, expiry):
            return stop
    return None


def _level(raw: dict[str, Any] | None) -> Level | None:
    if not raw:
        return None
    return Level(kind=str(raw["kind"]), price=float(raw["price"]))


def plan_from_mapping(raw: dict[str, Any] | None) -> ExitPlan:
    if not raw or not raw.get("catastrophic") or not raw["catastrophic"].get("level"):
        raise ValueError("exit plan missing required catastrophic stop")
    cat = raw["catastrophic"]
    structural = raw.get("structural")
    atr = raw.get("atr")
    grace = raw.get("grace")
    flip = raw.get("signal_flip")
    trail = raw.get("trail")
    return ExitPlan(
        catastrophic=CatastrophicStop(level=_level(cat["level"]) or Level("premium", 0.05)),
        structural=(
            StructuralStop(
                level=_level(structural["level"]) or Level("premium", 0.0),
                trigger=structural.get("trigger", "bar_close"),
            )
            if structural and structural.get("level")
            else None
        ),
        atr=(
            AtrStop(k=float(atr["k"]), trigger=str(atr.get("trigger", "bar_close")))
            if atr
            else None
        ),
        time_stops=tuple(
            TimeStop(
                after_s=int(t["after_s"]),
                when=str(t.get("when", "always")),
                unless_profit_pts=t.get("unless_profit_pts"),
            )
            for t in (raw.get("time_stops") or ())
        ),
        grace=GracePeriod(seconds=int(grace["seconds"])) if grace else None,
        signal_flip=(
            SignalFlipExit(
                on=tuple(flip.get("on") or ("own_opposite",)),
                trigger=str(flip.get("trigger", "bar_close")),
            )
            if flip
            else None
        ),
        target=_level(raw.get("target")),
        partials=tuple(
            Partial(at=_level(p["at"]) or Level("premium", 0.0), fraction=float(p["fraction"]))
            for p in (raw.get("partials") or ())
            if p.get("at")
        ),
        trail=(
            Trail(
                kind=str(trail["kind"]),
                activate_at=_level(trail.get("activate_at")) or Level("premium", 0.0),
                step=trail.get("step"),
                percent=trail.get("percent"),
            )
            if trail
            else None
        ),
        flat_by_ist=str(raw.get("flat_by_ist") or "15:15"),
        defaults_from=raw.get("defaults_from"),
    )


def plan_as_json(plan: ExitPlan) -> dict[str, Any]:
    return asdict(plan)


def quote_is_stale(
    quote_ts: datetime | None, now: datetime, max_age_s: float = STALE_MAX_AGE_S
) -> bool:
    if quote_ts is None:
        return True
    return (as_ist(now) - as_ist(quote_ts)).total_seconds() > max_age_s


def _hit_long(level: Level | None, mark: float) -> bool:
    return level is not None and mark + 1e-9 >= float(level.price)


def trigger_matches(trigger: str, event_kind: str) -> bool:
    if trigger == "bar_close":
        return event_kind == "BAR_CLOSED"
    if trigger == "tick":
        return event_kind in TICK_KINDS
    return False


def level_breached(level: Level, price: float, *, side: str) -> bool:
    """Long CE/PE premium stops down; underlying PE breaks up, CE breaks down."""
    px = float(level.price)
    if level.kind == "premium":
        return price <= px + 1e-9
    if side == "PE":
        return price + 1e-9 >= px
    return price <= px + 1e-9


def in_grace(plan: ExitPlan, fill_ts: datetime | None, now: datetime) -> bool:
    if plan.grace is None or fill_ts is None:
        return False
    return (as_ist(now) - as_ist(fill_ts)).total_seconds() < int(plan.grace.seconds)


def evaluate(
    pos: dict[str, Any],
    now: datetime,
    *,
    mark: float | None,
    quote_ts: datetime | None,
    kill: bool = False,
    founder_kind: str | None = None,
    strategy_exit: bool = False,
    quote_max_age_s: float = STALE_MAX_AGE_S,
    event_kind: str = "",
    underlying: float | None = None,
    own_opposite: bool = False,
    boss_opposite: bool = False,
) -> ExitRequest | None:
    """Order of architecture §2.9, including V2-09b primitives."""
    qty = _held_exit_qty(pos)
    if qty <= 0:
        return None
    plan: ExitPlan = pos["exit_plan"]
    stale = quote_is_stale(quote_ts, now, quote_max_age_s)
    hint = mark if mark is not None else pos.get("last_good_quote")
    if isinstance(hint, float) and hint != hint:  # NaN
        hint = pos.get("last_good_quote")
    side = option_side(str(pos.get("instrument_id") or ""))

    if founder_kind in FOUNDER_KINDS:
        reason = "KILL_SWITCH" if founder_kind == "KILL" else "FOUNDER_COMMAND"
        return ExitRequest(reason, "founder", qty, stale_quote=stale, price_hint=hint)
    if kill:
        return ExitRequest("KILL_SWITCH", "kill_switch", qty, stale_quote=stale, price_hint=hint)

    stop = float(pos["stop_price"])
    if mark is not None and mark == mark and mark <= stop + 1e-9:
        return ExitRequest("CATASTROPHIC_STOP", "catastrophic", qty, price_hint=mark)

    flat = parse_hhmm(plan.flat_by_ist)
    if as_ist(now).time() >= flat:
        return ExitRequest("FLATTEN_EOD", "flat_by_ist", qty, stale_quote=stale, price_hint=hint)

    if in_grace(plan, pos.get("fill_ts"), now):
        return None

    structural = plan.structural
    if structural is not None and trigger_matches(structural.trigger, event_kind):
        px = mark if structural.level.kind == "premium" else underlying
        if px is not None and px == px and level_breached(structural.level, float(px), side=side):
            return ExitRequest("STRUCTURAL_STOP", "structural", qty, price_hint=hint)

    atr = plan.atr
    atr_level = pos.get("atr_stop_level")
    if atr is not None and atr_level is not None and trigger_matches(atr.trigger, event_kind):
        px = underlying if underlying is not None else mark
        frozen = Level(kind="underlying", price=float(atr_level))
        if px is not None and px == px and level_breached(frozen, float(px), side=side):
            return ExitRequest("ATR_STOP", "atr", qty, price_hint=hint)

    chosen: TimeStop | None = pos.get("chosen_time_stop")
    if chosen is not None:
        deadline = as_ist(pos["fill_ts"]) + timedelta(seconds=int(chosen.after_s))
        profit = (mark - float(pos["avg_price"])) if mark is not None and mark == mark else None
        skip = (
            chosen.unless_profit_pts is not None
            and profit is not None
            and profit + 1e-9 >= float(chosen.unless_profit_pts)
        )
        if as_ist(now) >= deadline and not skip:
            return ExitRequest("TIME_EXIT", "time_stops", qty, price_hint=hint)

    flip = plan.signal_flip
    if flip is not None:
        allowed = set(flip.on)
        if own_opposite and "own_opposite" in allowed:
            pos["flip_pending"] = "own_opposite"
        if boss_opposite and "boss_opposite" in allowed:
            pos["flip_pending"] = "boss_opposite"
        pending = pos.get("flip_pending")
        if pending and trigger_matches(flip.trigger, event_kind):
            return ExitRequest("SIGNAL_FLIP", "signal_flip", qty, price_hint=hint)

    if mark is not None and mark == mark:
        done = int(pos.get("partials_done") or 0)
        partials = plan.partials
        if done < len(partials):
            part = partials[done]
            if _hit_long(part.at, mark):
                close_qty = partial_exit_qty(
                    orig_qty=int(pos.get("orig_qty") or qty),
                    net_qty=qty,
                    fraction=float(part.fraction),
                    instrument_id=str(pos.get("instrument_id") or ""),
                )
                if close_qty:
                    return ExitRequest("PARTIAL", "partials", close_qty, price_hint=mark)
        if _hit_long(plan.target, mark):
            return ExitRequest("TARGET_HIT", "target", qty, price_hint=mark)
        trail = plan.trail
        if trail is not None and _hit_long(trail.activate_at, mark):
            step = float(trail.step or 0.0)
            trail_floor = float(trail.activate_at.price)
            proposed = max(stop, mark - step) if step else max(stop, trail_floor)
            if proposed > stop + 1e-9:
                return ExitRequest(
                    "TRAIL_STOP", "trail", 0, new_stop=round(proposed, 2), price_hint=mark
                )

    if strategy_exit:
        return ExitRequest("STRATEGY_EXIT", "strategy", qty, price_hint=hint)
    return None
