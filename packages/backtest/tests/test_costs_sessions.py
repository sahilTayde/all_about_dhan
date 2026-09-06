from backtest_engine.costs import CostModel, apply_round_trip, round_trip_cost_pts
from backtest_engine.futidx_continuous import stitch_front_month
from backtest_engine.indicators import Bar
from backtest_engine.sessions import (
    filter_trades,
    last_session_of_iso_week,
    tag_session,
)
from backtest_engine.simulate import Trade
from dhan_client.futidx import FutIdxContract, parse_all_futidx_csv, parse_futidx_csv
from datetime import date


def _t(session: str, points: float = 10.0, entry: float = 100.0, exit_px: float = 110.0) -> Trade:
    return Trade(
        strategy_id="t",
        underlying="NIFTY",
        side="CE",
        entry_ts=1,
        exit_ts=2,
        entry_px=entry,
        exit_px=exit_px,
        points=points,
        reason="test",
        session=session,
    )


def test_round_trip_haircut_is_1pct_each_way():
    t = _t("2026-09-01", points=10.0, entry=100.0, exit_px=110.0)
    cost = round_trip_cost_pts(t)
    assert abs(cost - 2.1) < 1e-9  # 0.01*(100+110)
    after = apply_round_trip(t)
    assert abs(after.points - 7.9) < 1e-9


def test_statutory_stays_zero_on_default_model():
    assert CostModel().statutory_status == "UNKNOWN"
    assert CostModel().statutory_frac_round_trip == 0.0


def test_iso_week_expiry_proxy_takes_last_session():
    days = {"2026-09-01", "2026-09-02", "2026-09-03", "2026-09-07"}
    # 2026-09-01 Tue / 02 Wed / 03 Thu = week 36; 07 Mon = week 37
    got = last_session_of_iso_week(days)
    assert "2026-09-03" in got
    assert "2026-09-01" not in got
    assert "2026-09-07" in got


def test_news_insufficient_is_not_normal():
    tag = tag_session(
        "2026-09-02",
        expiry_proxy=set(),
        news_days=set(),
        news_status="DATA_INSUFFICIENT",
    )
    assert tag["session_kind"] == "UNKNOWN"
    assert tag["score_sample_member"] is False


def test_expiry_strip_drops_proxy_days():
    trades = [_t("2026-09-03"), _t("2026-09-02")]
    kept = filter_trades(
        trades,
        expiry_proxy={"2026-09-03"},
        news_days=set(),
        news_status="DATA_INSUFFICIENT",
        mode="expiry_stripped",
    )
    assert [t.session for t in kept] == ["2026-09-02"]
    score = filter_trades(
        trades,
        expiry_proxy={"2026-09-03"},
        news_days=set(),
        news_status="DATA_INSUFFICIENT",
        mode="score_sample",
    )
    assert score == []


def test_parse_all_includes_back_month():
    csv = """INSTRUMENT,SECURITY_ID,UNDERLYING_SYMBOL,DISPLAY_NAME,SM_EXPIRY_DATE,EXCH_ID,SEGMENT
FUTIDX,68407,NIFTY,NIFTY SEP FUT,2026-09-29,NSE,D
FUTIDX,48704,NIFTY,NIFTY OCT FUT,2026-10-27,NSE,D
FUTIDX,68390,BANKNIFTY,BANKNIFTY SEP FUT,2026-09-29,NSE,D
"""
    all_c = parse_all_futidx_csv(csv)
    assert [c.security_id for c in all_c["NIFTY"]] == ["68407", "48704"]
    nearest = parse_futidx_csv(csv, as_of=date(2026, 9, 3))
    assert nearest["NIFTY"].security_id == "68407"


def test_stitch_front_month_rolls_on_expiry():
    sep = FutIdxContract("NIFTY", "1", "NSE_FNO", "2026-09-29", "SEP")
    oct_ = FutIdxContract("NIFTY", "2", "NSE_FNO", "2026-10-27", "OCT")
    # ts around 2026-09-28 and 2026-10-01
    t_sep = int(date(2026, 9, 28).strftime("%s"))  # may be local — use explicit
    from datetime import datetime, timezone, timedelta

    ist = timezone(timedelta(hours=5, minutes=30))
    t_sep = int(datetime(2026, 9, 28, 12, 0, tzinfo=ist).timestamp())
    t_oct = int(datetime(2026, 10, 1, 12, 0, tzinfo=ist).timestamp())
    stitched = stitch_front_month(
        [
            (sep, [Bar(ts=t_sep, open=1, high=1, low=1, close=100, volume=1)]),
            (oct_, [Bar(ts=t_sep, open=1, high=1, low=1, close=200, volume=1),
                    Bar(ts=t_oct, open=1, high=1, low=1, close=300, volume=1)]),
        ]
    )
    assert [b.close for b in stitched] == [100, 300]
