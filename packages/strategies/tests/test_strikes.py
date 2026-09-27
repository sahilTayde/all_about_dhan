"""V2-06b strike-router acceptance tests. Synthetic fixtures only; no secrets."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import pytest
from contracts.instruments import IST, India
from contracts.payloads import QuoteSnapshot, Signal, StrikeQuote

from strategies.strikes import (
    RULES,
    DatedQuote,
    StrikeRouter,
    is_no_quote,
    itm_strike,
    load_router_rules,
    nearest_strike,
    parse_ts,
    rule_version,
    weekly_expiry,
)


@dataclass(frozen=True)
class _Feat:
    value: float
    as_of: datetime
    available_ts: datetime


@dataclass
class _View:
    spot: float
    as_of: datetime
    future_spot: float | None = None
    future_ts: datetime | None = None

    def get(self, name: str, instrument: str = "", tf: str = "") -> _Feat | None:
        if name != "spot":
            return None
        if self.future_spot is not None and self.future_ts is not None:
            return _Feat(self.future_spot, self.future_ts, self.future_ts)
        return _Feat(self.spot, self.as_of, self.as_of)


def _exit_plan(hold_s: int = 900) -> dict[str, Any]:
    return {
        "catastrophic": {"level": {"kind": "premium", "price": 1.0}},
        "time_stops": [{"after_s": hold_s, "when": "always"}],
        "flat_by_ist": "15:15",
    }


def _signal(
    *,
    when: datetime,
    side: str = "CE",
    strike_rule: str = "ROUTER",
    hold_s: int = 900,
    spot: float = 24512.35,
    underlying: str = "NIFTY",
) -> Signal:
    return Signal(
        signal_id="sg_test_v2_06b_nifty",
        strategy_id="TEST-CROSS",
        version="1.0.0",
        params_hash="testhash",
        stage="shadow",
        underlying=underlying,
        side=side,
        strike_rule=strike_rule,
        decision_ts=when.isoformat(),
        confidence=None,
        exit_plan=_exit_plan(hold_s),
        strike_choice={},
        reasons=["fixture"],
        features={"spot": spot, "planned_hold_s": float(hold_s)},
    )


def _snap(
    rule: str,
    side: str,
    instrument_id: str,
    bid: float,
    ask: float,
) -> QuoteSnapshot:
    mid = (bid + ask) / 2.0
    return QuoteSnapshot(
        instrument_id=instrument_id,
        rule=rule,
        side=side,
        bid=bid,
        ask=ask,
        mid=mid,
        spread=ask - bid,
        ltp=mid,
        ltt=None,
        oi=None,
        depth_age_ms=200,
        stale=False,
    )


def _quotes(
    when: datetime,
    side: str,
    *,
    expiry: str,
    spreads: dict[str, float] | None = None,
    age_s: float = 0.4,
) -> list[DatedQuote]:
    india = India()
    spot = 24512.35
    atm = nearest_strike(spot, 50)
    avail = when - timedelta(seconds=age_s)
    spread_map = spreads or {"ATM": 0.20, "ITM100": 0.25, "ITM200": 1.50}
    mids = {"ATM": 88.15, "ITM100": 151.23, "ITM200": 226.18}
    out: list[DatedQuote] = []
    for rule in RULES:
        strike = itm_strike(atm, side, {"ATM": 0, "ITM100": 100, "ITM200": 200}[rule])
        iid = india.format_instrument_id("NSE", "FNO", "NIFTY", expiry, str(strike), side)
        half = spread_map[rule] / 2.0
        mid = mids[rule]
        out.append(
            DatedQuote(
                avail,
                _snap(rule, side, iid, mid - half, mid + half),
            )
        )
    return out


def _router() -> StrikeRouter:
    return StrikeRouter(rules=load_router_rules())


@pytest.mark.parametrize(
    ("when", "hold_s", "strike_rule", "chosen", "reason"),
    [
        (datetime(2026, 9, 29, 11, 0, tzinfo=IST), 900, "ROUTER", "ITM200", "EXPIRY_DAY_NO_ATM"),
        (datetime(2026, 9, 28, 11, 0, tzinfo=IST), 900, "ROUTER", "ITM200", "DTE_LE_1"),
        (datetime(2026, 9, 25, 11, 0, tzinfo=IST), 900, "ROUTER", "ITM100", "DTE_GE_2"),
        (datetime(2026, 9, 28, 9, 30, tzinfo=IST), 900, "ROUTER", "ITM200", "OPEN_DECAY_WINDOW"),
        (datetime(2026, 9, 29, 11, 0, tzinfo=IST), 900, "ITM100", "ITM100", "STRATEGY_FIXED"),
        (
            datetime(2026, 9, 25, 11, 0, tzinfo=IST),
            120,
            "ROUTER",
            "ATM",
            "LOWEST_BREAKEVEN_AT_HOLD",
        ),
    ],
)
def test_hand_computed_choice_table(
    when: datetime, hold_s: int, strike_rule: str, chosen: str, reason: str
) -> None:
    """DTE 0/1/2+, open window, expiry day, pinned, lowest break-even."""
    spreads = (
        {"ATM": 0.05, "ITM100": 2.00, "ITM200": 2.00}
        if reason == "LOWEST_BREAKEVEN_AT_HOLD"
        else None
    )
    sig = _signal(when=when, hold_s=hold_s, strike_rule=strike_rule)
    expiry = weekly_expiry(when.astimezone(IST).date(), "tuesday", India()).isoformat()
    quotes = _quotes(when, "CE", expiry=expiry, spreads=spreads)
    choice = _router().route(sig, _View(24512.35, when), quotes)
    assert choice.chosen == chosen
    assert choice.reason == reason
    assert choice.rule_version == _router().version
    assert len(choice.alternatives) == 3
    assert [a.rule for a in choice.alternatives] == list(RULES)


def test_alternatives_include_quote_age_and_no_quote() -> None:
    when = datetime(2026, 9, 25, 11, 0, tzinfo=IST)
    sig = _signal(when=when)
    expiry = "2026-09-29"
    quotes = [
        q
        for q in _quotes(when, "CE", expiry=expiry)
        if isinstance(q.payload, QuoteSnapshot) and q.payload.rule != "ITM200"
    ]
    choice = _router().route(sig, _View(24512.35, when), quotes)
    by_rule = {a.rule: a for a in choice.alternatives}
    assert set(by_rule) == set(RULES)
    assert by_rule["ATM"].quote_age_ms == 400
    assert by_rule["ITM100"].quote_age_ms == 400
    assert is_no_quote(by_rule["ITM200"])
    assert by_rule["ITM200"].instrument_id != "no_quote"


def test_hand_computed_strikes_from_instrument_master() -> None:
    india = India()
    nifty_atm = nearest_strike(24512.35, 50)
    assert nifty_atm == 24500
    assert itm_strike(nifty_atm, "CE", 100) == 24400
    assert itm_strike(nifty_atm, "CE", 200) == 24300
    assert itm_strike(nifty_atm, "PE", 100) == 24600
    assert itm_strike(nifty_atm, "PE", 200) == 24700
    sensex_atm = nearest_strike(81123.4, 100)
    assert sensex_atm == 81100
    assert itm_strike(sensex_atm, "CE", 100) == 81000
    when = datetime(2026, 9, 24, 11, 0, tzinfo=IST)  # Thursday; NIFTY weekly is Tuesday
    sig = _signal(when=when, side="PE")
    quotes = _quotes(when, "PE", expiry="2026-09-29")
    choice = _router().route(sig, _View(24512.35, when), quotes)
    by_rule = {a.rule: a for a in choice.alternatives}
    assert by_rule["ATM"].instrument_id == india.format_instrument_id(
        "NSE", "FNO", "NIFTY", "2026-09-29", "24500", "PE"
    )
    assert by_rule["ITM100"].instrument_id.endswith(":24600:PE")
    assert by_rule["ITM200"].instrument_id.endswith(":24700:PE")
    lot = india.lot_size("NIFTY")
    charge = 40.0 / float(lot)
    assert by_rule["ATM"].est_round_trip_pts == pytest.approx(0.20 + charge)


def test_nifty_weekly_is_tuesday_from_calendar_not_thursday() -> None:
    india = India()
    thursday = datetime(2026, 9, 24, 11, 0, tzinfo=IST)
    assert thursday.weekday() == 3
    expiry = weekly_expiry(thursday.date(), "tuesday", india)
    assert expiry.isoformat() == "2026-09-29"
    assert expiry.weekday() == 1
    sig = _signal(when=thursday)
    quotes = _quotes(thursday, "CE", expiry="2026-09-29")
    choice = _router().route(sig, _View(24512.35, thursday), quotes)
    assert choice.reason != "EXPIRY_DAY_NO_ATM"
    assert choice.chosen == "ITM100"


def test_holiday_tuesday_rolls_back_via_india_calendar() -> None:
    """2026-10-20 Dussehra is Tuesday; NIFTY weekly rolls to Monday 2026-10-19."""
    india = India()
    monday = datetime(2026, 10, 19, 11, 0, tzinfo=IST)
    expiry = weekly_expiry(monday.date(), "tuesday", india)
    assert expiry.isoformat() == "2026-10-19"
    assert not india.is_trading_day(date(2026, 10, 20))
    sig = _signal(when=monday)
    quotes = _quotes(monday, "CE", expiry="2026-10-19")
    choice = _router().route(sig, _View(24512.35, monday), quotes)
    assert choice.reason == "EXPIRY_DAY_NO_ATM"
    assert choice.chosen == "ITM200"
    assert all(":2026-10-19:" in a.instrument_id for a in choice.alternatives)


def test_weekday_comes_from_instrument_master() -> None:
    rules = load_router_rules()
    nifty = dict(rules["underlyings"]["NIFTY"])
    nifty["weekly_expiry_weekday"] = "friday"
    rules = {**rules, "underlyings": {**rules["underlyings"], "NIFTY": nifty}}
    friday = datetime(2026, 9, 25, 11, 0, tzinfo=IST)
    choice = StrikeRouter(rules=rules).route(
        _signal(when=friday),
        _View(24512.35, friday),
        _quotes(friday, "CE", expiry="2026-09-25"),
    )
    assert choice.reason == "EXPIRY_DAY_NO_ATM"


def test_round_trip_uses_lot_size_from_adapter() -> None:
    when = datetime(2026, 9, 25, 11, 0, tzinfo=IST)
    quotes = _quotes(when, "CE", expiry="2026-09-29")
    choice = _router().route(_signal(when=when), _View(24512.35, when), quotes)
    atm = next(a for a in choice.alternatives if a.rule == "ATM")
    lot = India().lot_size("NIFTY")
    assert atm.est_round_trip_pts == pytest.approx(0.20 + 40.0 / lot)


def test_router_never_reads_quote_after_decision_ts() -> None:
    """Causal quotes only: a cheaper future ATM must not change the choice or shadows."""
    when = datetime(2026, 9, 25, 11, 0, tzinfo=IST)
    sig = _signal(when=when, hold_s=120)
    expiry = "2026-09-29"
    causal = _quotes(
        when,
        "CE",
        expiry=expiry,
        spreads={"ATM": 2.00, "ITM100": 0.25, "ITM200": 1.50},
    )
    future_atm = DatedQuote(
        when + timedelta(seconds=1),
        _snap("ATM", "CE", "NSE_FNO:NIFTY:2026-09-29:24500:CE", 88.00, 88.02),
    )
    view = _View(24512.35, when)
    router = _router()
    base = router.route(sig, view, causal)
    poisoned = router.route(sig, view, [*causal, future_atm])
    assert base.chosen == poisoned.chosen
    assert _mids(base.alternatives) == _mids(poisoned.alternatives)
    assert all(a.quote_age_ms is None or a.quote_age_ms >= 0 for a in poisoned.alternatives)


def test_random_cut_quotes_after_decision_ts_are_invisible() -> None:
    when = datetime(2026, 9, 25, 11, 0, tzinfo=IST)
    sig = _signal(when=when, hold_s=120)
    causal = _quotes(
        when,
        "CE",
        expiry="2026-09-29",
        spreads={"ATM": 2.00, "ITM100": 0.25, "ITM200": 1.50},
    )
    view = _View(24512.35, when)
    router = _router()
    expected = router.route(sig, view, causal)
    rng = random.Random(20260925)
    for i in range(25):
        future = [
            DatedQuote(
                when + timedelta(seconds=1 + i),
                _snap("ATM", "CE", "NSE_FNO:NIFTY:2026-09-29:24500:CE", 1.00, 1.01),
            )
            for i in range(rng.randint(1, 4))
        ]
        mixed = causal + future
        rng.shuffle(mixed)
        got = router.route(sig, view, mixed)
        assert got.chosen == expected.chosen
        assert _mids(got.alternatives) == _mids(expected.alternatives)


def test_future_spot_on_view_is_ignored() -> None:
    when = datetime(2026, 9, 24, 11, 0, tzinfo=IST)
    sig = _signal(when=when, spot=24512.35)
    view = _View(24512.35, when, future_spot=24680.0, future_ts=when + timedelta(minutes=5))
    choice = _router().route(sig, view, _quotes(when, "CE", expiry="2026-09-29"))
    atm = next(a for a in choice.alternatives if a.rule == "ATM")
    assert ":24500:" in atm.instrument_id


def test_rule_version_is_stable_for_same_rules() -> None:
    rules = load_router_rules()
    assert StrikeRouter(rules=rules).version == rule_version(rules)
    assert StrikeRouter(rules=rules).version.startswith("router-1.0.0+")


def test_parse_ts_rejects_naive() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        parse_ts("2026-09-25T11:00:00")


def _mids(alts: tuple[StrikeQuote, ...]) -> dict[str, float | None]:
    return {a.rule: a.mid for a in alts}
