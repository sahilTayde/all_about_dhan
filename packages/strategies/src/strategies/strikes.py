"""V2-06b strike router with shadow-priced alternatives. Paper only; never places orders.

`StrikeRouter.route(signal, view, quotes)` picks ATM / ITM100 / ITM200 from versioned
rules. Quotes are used only when `available_ts <= decision_ts` (no look-ahead).
Lot size and the trading calendar come from `contracts.instruments.India`; weekly
expiry weekday and strike step come from the instrument-master block in
`config/v2/strategies/strike_router.yaml` (never a hard-coded weekday).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Protocol

from contracts.instruments import IST, India
from contracts.payloads import DepthQuote, QuoteSnapshot, Signal, StrikeChoice, StrikeQuote

RULES: tuple[str, ...] = ("ATM", "ITM100", "ITM200")
ITM_OFFSETS: dict[str, int] = {"ATM": 0, "ITM100": 100, "ITM200": 200}
NO_QUOTE = "no_quote"
REASON_STRATEGY_FIXED = "STRATEGY_FIXED"
REASON_OPEN_DECAY = "OPEN_DECAY_WINDOW"
REASON_EXPIRY_NO_ATM = "EXPIRY_DAY_NO_ATM"
REASON_DTE_GE_2 = "DTE_GE_2"
REASON_DTE_LE_1 = "DTE_LE_1"
REASON_LOWEST_BE = "LOWEST_BREAKEVEN_AT_HOLD"
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class FeatureView(Protocol):
    """Minimal V2-05 FeatureView surface. `get` must not yield future values."""

    def get(self, name: str, instrument: str = "", tf: str = "") -> object | None: ...


@dataclass(frozen=True)
class DatedQuote:
    """A QUOTE_SNAPSHOT or DEPTH_QUOTE stamped with the time it became available."""

    available_ts: datetime
    payload: QuoteSnapshot | DepthQuote


def is_no_quote(quote: StrikeQuote) -> bool:
    """True when the alternative has no causal bid/ask (marked no_quote)."""
    return quote.bid is None and quote.ask is None and quote.quote_age_ms is None


def parse_ts(ts: str | datetime) -> datetime:
    """Parse an ISO timestamp. Naive values are rejected (clock is IST-aware)."""
    dt = ts if isinstance(ts, datetime) else datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return dt


def rule_version(rules: Mapping[str, Any]) -> str:
    """REG-13: version + hash of the effective rule document."""
    raw = json.dumps(rules, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:8]
    version = str(rules.get("version", "0"))
    return f"router-{version}+{digest}"


def load_router_rules(path: Path | None = None) -> dict[str, Any]:
    """Load strike-router YAML. A missing file is an error (no silent weekday fallback)."""
    import yaml  # type: ignore[import-untyped]

    target = path if path is not None else _default_yaml_path()
    if target is None or not target.is_file():
        shown = target if target is not None else "config/v2/strategies/strike_router.yaml"
        raise ValueError(
            f"strike_router.yaml missing at {shown}; "
            "pass rules= explicitly — packaged weekday defaults are not applied"
        )
    loaded = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("strike_router.yaml must be a mapping")
    return loaded


def nearest_strike(spot: float, step: int) -> int:
    """ATM from the instrument-master step (half-up)."""
    if step <= 0:
        raise ValueError("strike_step must be positive")
    return int((spot + step / 2) // step) * step


def itm_strike(atm: int, side: str, offset: int) -> int:
    """ITM strike: CE below spot, PE above spot."""
    if side == "CE":
        return atm - offset
    if side == "PE":
        return atm + offset
    raise ValueError(f"side must be CE or PE, got {side}")


def weekly_expiry(session: date, weekday_name: str, adapter: India) -> date:
    """Nearest weekly expiry on or after `session`, rolled back across holidays."""
    key = weekday_name.strip().lower()
    if key not in _WEEKDAYS:
        raise ValueError(f"unknown weekly_expiry_weekday: {weekday_name}")
    target = _WEEKDAYS[key]
    candidate = session + timedelta(days=(target - session.weekday()) % 7)
    guard = 0
    while not adapter.is_trading_day(candidate):
        candidate -= timedelta(days=1)
        guard += 1
        if guard > 14:
            raise ValueError(f"expiry calendar exhausted around {session.isoformat()}")
    return candidate


def _default_yaml_path() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "config" / "v2" / "strategies" / "strike_router.yaml"
        if candidate.is_file():
            return candidate
    return None


def _hhmm(text: str) -> time:
    parts = text.split(":")
    return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


def _underlying_cfg(rules: Mapping[str, Any], symbol: str) -> dict[str, Any]:
    book = rules.get("underlyings") or {}
    if not isinstance(book, dict) or symbol not in book:
        raise ValueError(f"unknown underlying: {symbol} (not in instrument master)")
    cfg = book[symbol]
    if not isinstance(cfg, dict):
        raise ValueError(f"instrument master row for {symbol} must be a mapping")
    return cfg


def _planned_hold_s(signal: Signal, rules: Mapping[str, Any]) -> int:
    raw = signal.features.get("planned_hold_s")
    if isinstance(raw, (int, float)) and raw >= 0:
        return int(raw)
    stops = signal.exit_plan.get("time_stops") if isinstance(signal.exit_plan, dict) else None
    if isinstance(stops, list):
        for stop in stops:
            if isinstance(stop, dict) and stop.get("when", "always") == "always":
                after = stop.get("after_s")
                if isinstance(after, int) and after >= 0:
                    return after
    default = (rules.get("rules") or {}).get("default_hold_s", 900)
    return int(default) if isinstance(default, (int, float)) else 900


def _spot(signal: Signal, view: FeatureView | None, decision_ts: datetime) -> float | None:
    if view is not None:
        feat = view.get("spot", signal.underlying, "")
        if feat is not None:
            avail = getattr(feat, "available_ts", None)
            if isinstance(avail, datetime) and avail > decision_ts:
                feat = None
            val = getattr(feat, "value", None) if feat is not None else None
            if isinstance(val, (int, float)):
                return float(val)
    raw = signal.features.get("spot")
    return float(raw) if isinstance(raw, (int, float)) else None


def _in_open_window(decision_ts: datetime, rules: Mapping[str, Any]) -> bool:
    window = (rules.get("rules") or {}).get("open_decay_window") or {}
    if not isinstance(window, dict):
        return False
    local = decision_ts.astimezone(IST)
    start = _hhmm(str(window.get("start", "09:15")))
    end = _hhmm(str(window.get("end", "10:00")))
    t = local.timetz().replace(tzinfo=None)
    return start <= t < end


def _session_end(expiry: date) -> datetime:
    return datetime.combine(expiry, time(15, 30), tzinfo=IST)


def _match_quote(
    quotes: Sequence[DatedQuote],
    *,
    rule: str,
    side: str,
    instrument_id: str,
    decision_ts: datetime,
) -> DatedQuote | None:
    chosen: DatedQuote | None = None
    for item in quotes:
        if item.available_ts.tzinfo is None:
            raise ValueError("quote available_ts must be timezone-aware")
        if item.available_ts > decision_ts:
            continue
        payload = item.payload
        if isinstance(payload, QuoteSnapshot):
            if payload.rule != rule or payload.side != side:
                continue
            if payload.instrument_id != instrument_id:
                continue
        elif isinstance(payload, DepthQuote):
            if payload.instrument_id != instrument_id:
                continue
        else:
            continue
        if chosen is None or item.available_ts >= chosen.available_ts:
            chosen = item
    return chosen


def _prices(
    payload: QuoteSnapshot | DepthQuote,
) -> tuple[float | None, float | None, float | None, float | None]:
    bid = payload.bid
    ask = payload.ask
    if isinstance(payload, QuoteSnapshot):
        mid = payload.mid
        spread = payload.spread
    else:
        mid = (bid + ask) / 2.0 if bid is not None and ask is not None else payload.ltp
        spread = (ask - bid) if bid is not None and ask is not None else None
    return bid, ask, mid, spread


def _friction_be(
    *,
    rule: str,
    mid: float | None,
    spread: float | None,
    hold_s: int,
    remaining_s: float,
    lot_size: int,
    rules: Mapping[str, Any],
) -> float | None:
    if spread is None or lot_size <= 0:
        return None
    deltas = rules.get("delta") or {}
    decay_k = rules.get("decay_k") or {}
    costs = rules.get("costs") or {}
    delta = float(deltas.get(rule, 0.5))
    if delta <= 0:
        return None
    k = float(decay_k.get(rule, 1.0))
    mid_px = float(mid) if mid is not None else 0.0
    decay_pts = mid_px * (hold_s / max(remaining_s, 1.0)) * k
    brokerage = float(costs.get("brokerage_inr_per_order", 20))
    charge_pts = (2.0 * brokerage) / float(lot_size)
    return (float(spread) + decay_pts + charge_pts) / delta


class StrikeRouter:
    """Causal ATM/ITM100/ITM200 router with shadow-priced alternatives."""

    def __init__(
        self,
        rules: Mapping[str, Any] | None = None,
        adapter: India | None = None,
        rules_path: Path | None = None,
    ) -> None:
        loaded = dict(rules) if rules is not None else load_router_rules(rules_path)
        self.rules: dict[str, Any] = loaded
        self.adapter = adapter if adapter is not None else India()
        self.version = rule_version(self.rules)

    def route(
        self,
        signal: Signal,
        view: FeatureView | None,
        quotes: Sequence[DatedQuote],
    ) -> StrikeChoice:
        decision_ts = parse_ts(signal.decision_ts)
        cfg = _underlying_cfg(self.rules, signal.underlying)
        spot = _spot(signal, view, decision_ts)
        session = decision_ts.astimezone(IST).date()
        expiry = weekly_expiry(session, str(cfg["weekly_expiry_weekday"]), self.adapter)
        dte = (expiry - session).days
        hold_s = _planned_hold_s(signal, self.rules)
        step = int(cfg["strike_step"])
        alternatives = self._alternatives(
            signal=signal,
            spot=spot,
            expiry=expiry,
            step=step,
            cfg=cfg,
            quotes=quotes,
            decision_ts=decision_ts,
        )
        chosen, reason = self._choose(
            signal=signal,
            dte=dte,
            decision_ts=decision_ts,
            hold_s=hold_s,
            alternatives=alternatives,
        )
        return StrikeChoice(
            chosen=chosen,
            reason=reason,
            rule_version=self.version,
            alternatives=alternatives,
        )

    def _instrument_id(
        self, cfg: Mapping[str, Any], symbol: str, expiry: date, strike: int, side: str
    ) -> str:
        return self.adapter.format_instrument_id(
            str(cfg["exchange"]),
            str(cfg["segment"]),
            symbol,
            expiry.isoformat(),
            str(strike),
            side,
        )

    def _alternatives(
        self,
        *,
        signal: Signal,
        spot: float | None,
        expiry: date,
        step: int,
        cfg: Mapping[str, Any],
        quotes: Sequence[DatedQuote],
        decision_ts: datetime,
    ) -> tuple[StrikeQuote, ...]:
        lot_size = self.adapter.lot_size(signal.underlying)
        atm = nearest_strike(spot, step) if spot is not None else None
        out: list[StrikeQuote] = []
        for rule in RULES:
            if atm is None:
                out.append(
                    StrikeQuote(
                        rule=rule,
                        instrument_id=NO_QUOTE,
                        bid=None,
                        ask=None,
                        mid=None,
                        spread=None,
                        quote_age_ms=None,
                        est_delta=None,
                        est_round_trip_pts=None,
                    )
                )
                continue
            strike = itm_strike(atm, signal.side, ITM_OFFSETS[rule])
            instrument_id = self._instrument_id(cfg, signal.underlying, expiry, strike, signal.side)
            hit = _match_quote(
                quotes,
                rule=rule,
                side=signal.side,
                instrument_id=instrument_id,
                decision_ts=decision_ts,
            )
            if hit is None:
                out.append(
                    StrikeQuote(
                        rule=rule,
                        instrument_id=instrument_id,
                        bid=None,
                        ask=None,
                        mid=None,
                        spread=None,
                        quote_age_ms=None,
                        est_delta=None,
                        est_round_trip_pts=None,
                    )
                )
                continue
            bid, ask, mid, spread = _prices(hit.payload)
            age_ms = int((decision_ts - hit.available_ts).total_seconds() * 1000)
            brokerage = float((self.rules.get("costs") or {}).get("brokerage_inr_per_order", 20))
            charge_pts = (2.0 * brokerage) / float(lot_size)
            rt = (float(spread) + charge_pts) if spread is not None else None
            deltas = self.rules.get("delta") or {}
            out.append(
                StrikeQuote(
                    rule=rule,
                    instrument_id=instrument_id,
                    bid=bid,
                    ask=ask,
                    mid=mid,
                    spread=spread,
                    quote_age_ms=age_ms,
                    est_delta=float(deltas[rule]) if rule in deltas else None,
                    est_round_trip_pts=rt,
                )
            )
        return tuple(out)

    def _choose(
        self,
        *,
        signal: Signal,
        dte: int,
        decision_ts: datetime,
        hold_s: int,
        alternatives: tuple[StrikeQuote, ...],
    ) -> tuple[str, str]:
        policy = self.rules.get("rules") or {}
        dte_map = policy.get("dte") or {}
        ge_2 = str(dte_map.get("ge_2", "ITM100"))
        le_1 = str(dte_map.get("le_1", "ITM200"))
        pinned = signal.strike_rule in RULES and bool(policy.get("honor_strategy_fixed", True))
        if pinned:
            return signal.strike_rule, REASON_STRATEGY_FIXED
        if _in_open_window(decision_ts, self.rules):
            window = policy.get("open_decay_window") or {}
            return str(window.get("choice", "ITM200")), REASON_OPEN_DECAY
        if dte == 0 and bool(policy.get("no_atm_on_expiry_day", True)):
            return le_1, REASON_EXPIRY_NO_ATM
        if dte <= 1:
            return le_1, REASON_DTE_LE_1
        allowed = {ge_2, "ITM200"}
        atm_cap = int(policy.get("atm_max_hold_s", 300))
        if hold_s <= atm_cap:
            allowed.add("ATM")
        if bool(policy.get("lowest_breakeven", True)):
            expiry_session = decision_ts.astimezone(IST).date()
            # remaining life uses the same expiry the alternatives were built for
            cfg = _underlying_cfg(self.rules, signal.underlying)
            expiry = weekly_expiry(expiry_session, str(cfg["weekly_expiry_weekday"]), self.adapter)
            remaining_s = max((_session_end(expiry) - decision_ts).total_seconds(), 1.0)
            lot_size = self.adapter.lot_size(signal.underlying)
            scored: list[tuple[float, str]] = []
            for alt in alternatives:
                if alt.rule not in allowed or is_no_quote(alt):
                    continue
                be = _friction_be(
                    rule=alt.rule,
                    mid=alt.mid,
                    spread=alt.spread,
                    hold_s=hold_s,
                    remaining_s=remaining_s,
                    lot_size=lot_size,
                    rules=self.rules,
                )
                if be is not None:
                    scored.append((be, alt.rule))
            if scored:
                scored.sort(key=lambda row: (row[0], RULES.index(row[1])))
                winner = scored[0][1]
                if winner != ge_2:
                    return winner, REASON_LOWEST_BE
        return ge_2, REASON_DTE_GE_2
