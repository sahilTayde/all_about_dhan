"""V2-09 exit evaluation: plan primitives only. No hidden cancels. Paper clock."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta
from math import floor
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
        "TIME_EXIT",
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
STALE_EXEMPT = frozenset({"FLATTEN_EOD", "FOUNDER_COMMAND", "KILL_SWITCH", "FAILSAFE_MTM"})
SEND_ON_CLOCK = frozenset({"TIME_EXIT", "FLATTEN_EOD"})
STALE_MAX_AGE_S = 90.0
FOUNDER_KINDS = frozenset({"CUT_LOSS", "FLATTEN", "FLATTEN_ALL", "KILL"})
_INDIA = India()


def instrument_lot_size(instrument_id: str) -> int:
    """Lot size from `contracts.instruments.India`, never a hard-coded 65."""
    symbol = str(_INDIA.parse_instrument_id(instrument_id).get("symbol") or "")
    return _INDIA.lot_size(symbol)


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
) -> ExitRequest | None:
    """Order of section 2.9. Structural / ATR / grace / flip are V2-09b (ignored here)."""
    qty = _held_exit_qty(pos)
    if qty <= 0:
        return None
    plan: ExitPlan = pos["exit_plan"]
    stale = quote_is_stale(quote_ts, now, quote_max_age_s)
    hint = mark if mark is not None else pos.get("last_good_quote")
    if isinstance(hint, float) and hint != hint:  # NaN
        hint = pos.get("last_good_quote")

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
