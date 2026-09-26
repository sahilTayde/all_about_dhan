"""Shadow features: causal math, GEX convention, CSV export, boss ignores them."""

import csv
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from analysts.eval import dsr, norm_ppf
from analysts.shadow import (
    DEALER_LONG_CALLS_SHORT_PUTS,
    bars_upto,
    build_shadow_snapshot,
    days_to_expiry,
    dealer_gex,
    detect_oi_unit,
    expiry_dates,
    late_momentum,
    range_over_atr,
    realised_vol_pct,
    resolve_expiries,
    session_open,
    log_returns,
    wilder_atr,
    _CALENDAR_WARNED,
    _OHLC_OPEN_CACHE,
    _day_open,
    _prior_close_state,
)
from analysts.shadow_export import export_shadow_csv

IST = timezone(timedelta(hours=5, minutes=30))

# Bailey & López de Prado 2014, evaluated on this fixed sample (sample Sharpe, raw moments).
# n_trials=1 is the probabilistic Sharpe against zero. n_trials=100 applies the selection haircut.
_PNLS = (1.0, 0.5, -0.2, 0.8, 0.1, -0.4, 0.6, 0.3, -0.1, 0.7)


def _ts(day: str, h: int, m: int, s: int = 0) -> int:
    y, mo, d = (int(p) for p in day.split("-"))
    return int(datetime(y, mo, d, h, m, s, tzinfo=IST).timestamp())


def _bars(n: int, *, start: int, close0: float = 100.0, step: float = 0.1) -> list[dict]:
    out = []
    for i in range(n):
        close = close0 + i * step
        out.append({"ts": start + i * 60, "open": close - 0.05, "high": close + 0.4, "low": close - 0.4, "close": close})
    return out


def _daily(n: int = 20) -> list[dict]:
    rows = []
    for i in range(n):
        close = 100.0 + i
        rows.append({"date": f"2026-08-{i+1:02d}", "high": close + 2.0, "low": close - 2.0, "close": close})
    return rows


def test_norm_ppf_and_deflated_sharpe_known_example():
    assert norm_ppf(0.975) == pytest.approx(1.95996398454, abs=1e-8)
    assert dsr(_PNLS, 1) == pytest.approx(0.9756895418901521, abs=1e-12)
    assert dsr(_PNLS, 100) == pytest.approx(0.2881825717656473, abs=1e-12)
    assert dsr(_PNLS, 100) < dsr(_PNLS, 1)  # more trials, more deflation
    with pytest.raises(ValueError):
        dsr([1.0, 2.0], 1)


def test_truncated_series_does_not_see_the_future():
    start = _ts("2026-09-10", 9, 15)
    bars = _bars(70, start=start)
    prior = _daily()
    atr = wilder_atr(prior, 14)
    assert atr is not None and atr > 0
    prefix = bars[:60]
    future = dict(bars[-1])
    future["ts"] = bars[-1]["ts"] + 60
    future["high"] = 1000.0
    future["low"] = 1.0
    full = bars + [future]

    def rng(series):
        return range_over_atr(series[-60:], atr)

    assert rng(prefix) == rng(full[:60])
    assert rng(full) != rng(prefix)
    assert bars_upto(full, prefix[-1]["ts"]) == prefix

    # A later print does not rewrite the 14:44 close, and 14:44 is unknown before 14:45.
    b1444 = {"ts": _ts("2026-09-10", 14, 44), "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0}
    b1500 = {"ts": _ts("2026-09-10", 15, 0), "open": 100.0, "high": 999.0, "low": 1.0, "close": 999.0}
    early = late_momentum([b1444], 90.0, _ts("2026-09-10", 14, 44, 30))
    assert early["value"] is None and early["reasoning"] == "NOT_YET"
    done = late_momentum([b1444], 90.0, _ts("2026-09-10", 14, 50))
    with_later = late_momentum([b1444, b1500], 90.0, _ts("2026-09-10", 15, 10))
    assert done["value"] == 1 and with_later["value"] == done["value"]
    assert with_later["extra"]["close_1444"] == 100.0

    opens = _bars(5, start=start, close0=25000.0, step=1.0)
    assert _day_open(opens, "2026-09-10") == _day_open(opens + [future], "2026-09-10")


def test_snapshot_drops_a_bar_after_the_tick():
    start = _ts("2026-09-10", 10, 0)
    bars = _bars(61, start=start, close0=25000.0, step=0.2)
    now = bars[60]["ts"]
    future = {"ts": now + 60, "open": 1.0, "high": 99999.0, "low": 1.0, "close": 99999.0}
    engine = SimpleNamespace(closed=[], opens={}, lot_by_und={"NIFTY": (65, "t")}, shadow_prior_daily={"NIFTY": _daily()})
    tick = SimpleNamespace(ts=now, idx_close=bars[60]["close"], wing_quotes={})
    step = SimpleNamespace(und="NIFTY", tick=tick, bars_1m=bars + [future])
    plain = SimpleNamespace(und="NIFTY", tick=tick, bars_1m=bars)
    a = build_shadow_snapshot(engine, step, None)
    b = build_shadow_snapshot(engine, plain, None)
    assert a["rng60_atr"]["value"] == b["rng60_atr"]["value"]
    assert a["rng60_atr"]["extra"]["expected_abs_move_pts"] == pytest.approx(
        a["rng60_atr"]["value"] * a["rng60_atr"]["extra"]["atr14"]
    )


def test_dealer_gex_sign_convention_and_missing_chain():
    # spot 100, lot 50 → scale 5000. Strike 100 net +30, strike 110 net −90.
    rows = [
        {"strike": 100, "ce_gamma": 0.001, "ce_oi": 10, "pe_gamma": 0.001, "pe_oi": 4},
        {"strike": 110, "ce_gamma": 0.001, "ce_oi": 2, "pe_gamma": 0.002, "pe_oi": 10},
    ]
    got = dealer_gex(rows, 100.0, 50.0, convention=DEALER_LONG_CALLS_SHORT_PUTS)
    assert got["gex"] == pytest.approx(-60.0)
    assert got["regime"] == "neg"
    assert got["zero_gamma"] == pytest.approx(100.0 + 10.0 / 3.0)
    flipped = dealer_gex(rows, 100.0, 50.0, convention="short_calls_long_puts")
    assert flipped["gex"] == pytest.approx(60.0) and flipped["regime"] == "pos"
    assert dealer_gex(rows, 100.0, 50.0, convention="nope") is None
    assert dealer_gex([{"strike": 100, "ce_oi": 10, "pe_oi": 4}], 100.0, 50.0) is None
    assert dealer_gex([], 100.0, 50.0) is None

    start = _ts("2026-09-10", 11, 0)
    bars = _bars(5, start=start)
    engine = SimpleNamespace(closed=[], opens={}, lot_by_und={"NIFTY": (65, "t")}, shadow_prior_daily={})
    tick = SimpleNamespace(ts=bars[-1]["ts"], idx_close=100.0, wing_quotes={})
    snap = build_shadow_snapshot(engine, SimpleNamespace(und="NIFTY", tick=tick, bars_1m=bars), None)
    assert snap["gex"]["value"] is None
    assert "MISSING" in snap["gex"]["reasoning"]


def test_expiry_day_uses_repo_calendar():
    assert days_to_expiry("2026-09-08", ["2026-09-08", "2026-09-15"]) == 0
    assert days_to_expiry("2026-09-09", ["2026-09-08", "2026-09-15"]) == 6
    assert days_to_expiry("2030-01-01", ["2026-09-15"]) is None


def test_rv_is_annualised_percent():
    import math

    from analysts.shadow import ANN_FACTOR

    closes = [100.0, 101.0, 100.0, 102.0]
    rets = log_returns(closes)
    assert rets is not None and len(rets) == 3
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    expected = math.sqrt(var) * ANN_FACTOR * 100.0
    assert realised_vol_pct(rets) == pytest.approx(expected)
    assert expected > 10.06  # above the high_vol flag, so the scale is annualised percent


def test_export_one_row_per_session_minute(tmp_path):
    from events import EventAuditLog, MemoryBus

    path = tmp_path / "events.sqlite"
    bus = MemoryBus(EventAuditLog(path))
    t0 = _ts("2026-09-10", 10, 15, 5)
    t1 = _ts("2026-09-10", 10, 15, 40)
    t2 = _ts("2026-09-10", 10, 16, 5)

    def vote(ts, value, aid="rng60_atr"):
        bus.publish("ANALYST_VOTE", {
            "analyst_id": aid, "signal": "ABSTAIN", "confidence": 0.5, "reasoning": "t",
            "metadata": {"shadow": True, "value": value, "flag": value > 0.3, "expected_abs_move_pts": value * 10},
            "value": value, "flag": value > 0.3, "underlying": "NIFTY", "ts": ts,
        }, source=f"analyst:{aid}")

    vote(t0, 0.1)
    vote(t1, 0.5)  # same minute, later value wins
    vote(t2, 0.2)
    out = tmp_path / "shadow.csv"
    assert export_shadow_csv(path, out) == 2
    rows = list(csv.DictReader(out.open()))
    assert rows[0]["session"] == "2026-09-10" and rows[0]["minute_ist"] == "10:15"
    assert rows[0]["rng60_atr"] == "0.5"
    assert rows[0]["rng60_atr_expected_abs_move_pts"] == "5.0"
    assert rows[1]["minute_ist"] == "10:16" and rows[1]["rng60_atr"] == "0.2"


def test_day_open_uses_quote_or_ohlc_else_the_first_bar(tmp_path):
    late = _bars(3, start=_ts("2026-09-10", 9, 30), close0=25010.0)
    assert _day_open(late, "2026-09-10") is None
    px, source = session_open(late, "2026-09-10")
    assert source == "fallback_first_bar" and px == late[0]["open"]
    quoted, qsrc = session_open(late, "2026-09-10", quote_open=24900.0)
    assert qsrc == "quote" and quoted == 24900.0
    bar915 = {"ts": _ts("2026-09-10", 9, 15), "open": 24850.0, "high": 24860.0, "low": 24840.0, "close": 24855.0}
    assert session_open([bar915] + late, "2026-09-10") == (24850.0, "bar_0915")

    stamp = _ts("2026-09-10", 9, 15)
    ohlc = tmp_path / "data" / "recon" / "ohlc"
    ohlc.mkdir(parents=True)
    (ohlc / "INDEX_IDX_I_13_1_sample.json").write_text(json.dumps({
        "timestamp": [stamp, _ts("2026-09-10", 9, 16)],
        "open": [24700.0, 24710.0],
        "close": [24705.0, 24720.0],
    }), encoding="utf-8")
    _OHLC_OPEN_CACHE.clear()
    engine = SimpleNamespace(root=tmp_path, closed=[], opens={}, lot_by_und={"NIFTY": (65, "t")}, shadow_prior_daily={})
    tick = SimpleNamespace(ts=late[-1]["ts"], idx_close=24950.0, wing_quotes={}, day_open=None)
    from_ohlc = build_shadow_snapshot(engine, SimpleNamespace(und="NIFTY", tick=tick, bars_1m=late), None)
    assert from_ohlc["day_direction"]["extra"]["open_source"] == "ohlc"
    assert from_ohlc["day_direction"]["extra"]["day_open"] == 24700.0
    assert from_ohlc["day_direction"]["flag"] == "CE"

    tick.day_open = 24900.0
    from_quote = build_shadow_snapshot(engine, SimpleNamespace(und="NIFTY", tick=tick, bars_1m=late), None)
    assert from_quote["day_direction"]["extra"]["open_source"] == "quote"
    assert from_quote["day_direction"]["flag"] == "CE"

    bare = SimpleNamespace(closed=[], opens={}, lot_by_und={"NIFTY": (65, "t")}, shadow_prior_daily={})
    fallback = build_shadow_snapshot(bare, SimpleNamespace(und="NIFTY", tick=SimpleNamespace(
        ts=late[-1]["ts"], idx_close=25000.0, wing_quotes={}, day_open=None,
    ), bars_1m=late), None)
    assert fallback["day_direction"]["extra"]["open_source"] == "fallback_first_bar"


def test_stale_or_missing_prior_close_logs_no_sign():
    bar = {"ts": _ts("2026-09-10", 14, 44), "open": 100.0, "high": 101.0, "low": 99.0, "close": 110.0}
    now = _ts("2026-09-10", 14, 50)
    stale = late_momentum([bar], 90.0, now, prior_state="stale")
    missing = late_momentum([bar], None, now, prior_state="missing")
    assert stale["value"] is None and stale["reasoning"] == "STALE_PRIOR_CLOSE"
    assert missing["value"] is None and missing["reasoning"] == "MISSING_PRIOR_CLOSE"
    assert late_momentum([bar], 90.0, _ts("2026-09-10", 14, 44), prior_state="stale")["reasoning"] == "NOT_YET"
    assert _prior_close_state([{"date": "2026-09-08", "close": 100.0}], "2026-09-10") == (None, "stale")
    assert _prior_close_state([{"date": "2026-09-09", "close": 100.0}], "2026-09-10") == (100.0, "ok")
    assert _prior_close_state([], "2026-09-10")[1] == "missing"


def test_share_oi_is_normalised_and_the_window_is_logged():
    contracts = [
        {"strike": 100, "ce_gamma": 0.001, "ce_oi": 10, "pe_gamma": 0.001, "pe_oi": 4},
        {"strike": 110, "ce_gamma": 0.001, "ce_oi": 2, "pe_gamma": 0.002, "pe_oi": 10},
    ]
    shares = [{**row, "ce_oi": row["ce_oi"] * 50, "pe_oi": row["pe_oi"] * 50} for row in contracts]
    shares.append({"strike": 500, "ce_gamma": 0.01, "ce_oi": 50000, "pe_gamma": 0.01, "pe_oi": 50000})
    got = dealer_gex(shares, 100.0, 50.0)
    base = dealer_gex(contracts, 100.0, 50.0)
    assert detect_oi_unit([10, 4, 2, 10], 50) == "contracts"
    assert got["oi_unit"] == "shares" and base["oi_unit"] == "contracts"
    assert got["gex"] == pytest.approx(base["gex"])
    assert got["n_strikes"] == 2 and got["strike_min"] == 100 and got["strike_max"] == 110
    assert got["window_points"] == 300
    hinted = [{**contracts[0], "oi_unit": "shares"}]
    small = dealer_gex(hinted, 100.0, 50.0)
    one = dealer_gex([contracts[0]], 100.0, 50.0)
    assert small["oi_unit"] == "shares" and small["gex"] == pytest.approx(one["gex"] / 50.0)


def test_each_index_uses_its_own_chain_expiry(tmp_path, caplog):
    """NIFTY Tuesdays must not override SENSEX or BANKNIFTY chain expiries."""
    session = "2026-09-15"
    now = _ts(session, 11, 0)
    chain = tmp_path / "data" / "recon" / "option_chain"
    chain.mkdir(parents=True)
    (chain / "20260915.jsonl").write_text(
        "\n".join([
            json.dumps({"underlying": "NIFTY", "timestamp": now - 60, "expiry": "2026-09-15"}),
            json.dumps({"underlying": "SENSEX", "timestamp": now - 60, "expiry": "2026-09-17"}),
            json.dumps({"underlying": "BANKNIFTY", "timestamp": now - 60, "expiry": "2026-09-24"}),
            json.dumps({"underlying": "SENSEX", "timestamp": now + 3600, "expiry": "2026-10-01"}),
            json.dumps({"timestamp": now - 30, "expiry": "2026-09-15"}),
        ]) + "\n",
        encoding="utf-8",
    )
    engine = SimpleNamespace(root=tmp_path, live_chain_rows=None)
    tick = SimpleNamespace(expiry=None, wing_quotes={})

    def cell(und, expiry):
        tick.expiry = expiry
        dates, source, exhausted = resolve_expiries(engine, tick, und, now, session)
        return days_to_expiry(session, dates), source, exhausted, dates

    assert cell("NIFTY", "2026-09-15")[:3] == (0, "chain", False)
    assert cell("SENSEX", "2026-09-17")[:3] == (2, "chain", False)
    assert cell("BANKNIFTY", "2026-09-24")[:3] == (9, "chain", False)
    # The jsonl row with no underlying is ignored, so it cannot stamp NIFTY's Tuesday onto SENSEX.
    tick.expiry = None
    sensex_dates, sensex_source, _ex = resolve_expiries(engine, tick, "SENSEX", now, session)
    assert sensex_source == "chain" and sensex_dates == ["2026-09-17"]
    assert days_to_expiry(session, sensex_dates) == 2
    nifty_only, nifty_source, _ = resolve_expiries(engine, tick, "NIFTY", now, session)
    assert nifty_source == "chain" and "2026-09-17" not in nifty_only

    bare = SimpleNamespace(root=None, live_chain_rows=None)
    empty_tick = SimpleNamespace(expiry=None, wing_quotes={})
    _none, src, _ = resolve_expiries(bare, empty_tick, "SENSEX", now, session)
    assert src == "no_index_expiry"
    _CALENDAR_WARNED.discard("2026-09-22")
    with caplog.at_level("WARNING", logger="analysts.shadow"):
        extended, ext_source, exhausted = resolve_expiries(
            bare, empty_tick, "NIFTY", _ts("2026-09-22", 10, 0), "2026-09-22",
        )
    assert exhausted and ext_source == "weekly_tuesday_extension" and "2026-09-22" in extended
    assert "EXPIRY CALENDAR EXHAUSTED" in caplog.text


def test_boss_ignores_shadow_votes():
    from analysts import ABSTAIN, BUY_CE, Vote
    from boss import Boss
    from events import MemoryBus

    bus = MemoryBus()
    boss = Boss(
        bus, SimpleNamespace(), steps={}, signals={}, contexts={},
        analyst_ids=["follows", "rng60_atr"], shadow_ids=["rng60_atr"],
    )
    votes = [
        Vote("follows", BUY_CE, 1.0, "a", {"legacy": True, "reason_class": "CONFIRM", "silent": False, "side": "CE"}),
        Vote("rng60_atr", ABSTAIN, 0.5, "s", {"shadow": True, "value": 9.0, "flag": True}),
    ]
    out = boss.legacy_votes(votes, {})
    assert [v.source for v in out] == ["follows"]


def test_minutes_since_ignores_a_future_trade():
    start = _ts("2026-09-10", 11, 0)
    bars = _bars(40, start=start, close0=25000.0)
    now = bars[-1]["ts"]
    engine = SimpleNamespace(
        closed=[{"underlying": "NIFTY", "closed_ts": now + 600}, {"underlying": "NIFTY", "closed_ts": now - 120}],
        opens={},
        lot_by_und={"NIFTY": (65, "t")},
        shadow_prior_daily={"NIFTY": _daily()},
    )
    tick = SimpleNamespace(ts=now, idx_close=bars[-1]["close"], wing_quotes={})
    snap = build_shadow_snapshot(engine, SimpleNamespace(und="NIFTY", tick=tick, bars_1m=bars), None)
    assert snap["minutes_since_prior_trade"]["value"] == pytest.approx(2.0)
