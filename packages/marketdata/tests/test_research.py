"""Research overlay: current-month futures + 10 NIFTY cash names on md:research."""

from __future__ import annotations

import asyncio
from datetime import date

from md_fake_dhan import (
    DAY,
    HEAVYWEIGHT_SIDS,
    StubSource,
    ist,
    run_session,
    scrip_master_csv,
    schema_errors,
)
import pytest

from marketdata.instruments import StartupError
from marketdata.research import (
    NIFTY_HEAVYWEIGHTS,
    RESEARCH_STREAM,
    after_recentre_count,
    current_month_futidx,
    default_unique_subscribe_count,
    dhan_feed_caps,
    load_research_set,
    options_per_book,
    parse_equity_ids,
    research_named_count,
    steady_book_count,
    within_dhan_caps,
)
from marketdata.schemas import load_schema


def test_equity_ids_come_from_scrip_master_not_hardcoded() -> None:
    text = scrip_master_csv()
    ids = parse_equity_ids(text)
    assert list(ids) == list(NIFTY_HEAVYWEIGHTS)
    assert ids == HEAVYWEIGHT_SIDS
    swapped = text.replace("NSE,E,9001,EQUITY,0,HDFCBANK", "NSE,E,7777,EQUITY,0,HDFCBANK")
    assert parse_equity_ids(swapped)["HDFCBANK"] == "7777"
    assert "7777" not in ids.values()


def test_missing_cash_name_is_startup_error() -> None:
    text = "\n".join(line for line in scrip_master_csv().splitlines() if "ITC" not in line) + "\n"
    with pytest.raises(StartupError, match="ITC"):
        parse_equity_ids(text)


def test_detailed_csv_equity_columns() -> None:
    header = (
        "EXCH_ID,SEGMENT,SECURITY_ID,ISIN,INSTRUMENT,UNDERLYING_SECURITY_ID,UNDERLYING_SYMBOL,"
        "SYMBOL_NAME,DISPLAY_NAME,INSTRUMENT_TYPE,SERIES,LOT_SIZE,SM_EXPIRY_DATE,STRIKE_PRICE,"
        "OPTION_TYPE,TICK_SIZE,EXPIRY_FLAG"
    )
    rows = [header]
    for i, name in enumerate(NIFTY_HEAVYWEIGHTS):
        rows.append(
            f"NSE,E,{8000 + i},INE{i:03d},EQUITY,{8000 + i},{name},{name},{name},ES,EQ,1,,0,XX,0.05,NA"
        )
    ids = parse_equity_ids("\n".join(rows) + "\n")
    assert ids["TCS"] == str(8000 + NIFTY_HEAVYWEIGHTS.index("TCS"))
    assert ids["LT"] == str(8000 + NIFTY_HEAVYWEIGHTS.index("LT"))


def test_current_month_future_then_front_month_fallback() -> None:
    text = scrip_master_csv()
    sep = current_month_futidx(text, date(2026, 9, 28), "NIFTY")
    assert sep is not None
    assert (sep.security_id, sep.expiry) == ("35000", "2026-09-29")
    # Sep contract expired, calendar month still September → front-month October
    front = current_month_futidx(text, date(2026, 9, 30), "NIFTY")
    assert front is not None
    assert (front.security_id, front.expiry) == ("35001", "2026-10-27")
    sensex = current_month_futidx(text, date(2026, 9, 28), "SENSEX")
    assert sensex is not None
    assert sensex.security_id == "844700"  # no Sep SENSEX FUT; nearest Oct
    oct_nifty = current_month_futidx(text, date(2026, 10, 5), "NIFTY")
    assert oct_nifty is not None
    assert oct_nifty.expiry == "2026-10-27"


def test_research_set_resolves_two_futures_and_ten_stocks() -> None:
    overlay = load_research_set(scrip_master_csv(), DAY)
    assert [i.kind for i in overlay.futures] == ["FUTURE", "FUTURE"]
    assert {i.instrument_id for i in overlay.futures} == {
        "NSE_FNO:NIFTY:2026-09-29",
        "BSE_FNO:SENSEX:2026-10-29",
    }
    assert [i.instrument_id for i in overlay.stocks] == [f"NSE_EQ:{n}" for n in NIFTY_HEAVYWEIGHTS]
    assert [i.security_id for i in overlay.stocks] == [HEAVYWEIGHT_SIDS[n] for n in NIFTY_HEAVYWEIGHTS]
    assert all(i.exchange_segment == "NSE_EQ" for i in overlay.stocks)
    assert len(overlay) == 12


def test_instrument_counts_sit_inside_dhan_caps() -> None:
    assert options_per_book() == 10
    assert steady_book_count() == 12
    assert research_named_count() == 12
    # Default unique: 48 book ids (moving ATM + open ±5 ladder) + 10 stocks
    assert default_unique_subscribe_count(open_ladder_n=0) == 34
    assert default_unique_subscribe_count() == 58
    assert after_recentre_count() == 78
    # Worst case: current-month futures are extra ids (not the book's nearest)
    assert default_unique_subscribe_count(extra_futures=2) == 60
    assert after_recentre_count(extra_futures=2) == 80
    caps = dhan_feed_caps()
    assert caps == {"sockets_per_user": 5, "ids_per_socket": 5000, "ids_per_subscribe_json": 100}
    for n in (34, 58, 60, 78, 80):
        assert within_dhan_caps(n)
    assert not within_dhan_caps(101)
    snapshot = load_schema("quote_snapshot")
    assert snapshot["properties"]["rule"]["enum"][:5] == ["ATM", "ITM100", "ITM200", "OTM100", "OTM200"]  # + NEAR_* (2026-10-12)
    assert "volume" in snapshot["properties"]
    assert "volume" not in snapshot["required"]
    depth = load_schema("depth_quote")
    assert "volume" not in depth["properties"]


def test_recorder_research_stream_has_volume_and_leaves_book_tapes_alone(tmp_path) -> None:  # type: ignore[no-untyped-def]
    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 0, 8),
            source=StubSource(),
            config_kw={"underlyings": ("NIFTY", "SENSEX"), "research": True},
        )
    )
    assert s.exit_code == 0
    subs = [r for r in s.rows("subscriptions") if r["action"] == "subscribe"]
    ids = {r["instrument_id"] for r in subs}
    research_ids = {r["instrument_id"] for r in subs if r["reason"] == "research"}
    assert research_ids == {f"NSE_EQ:{n}" for n in NIFTY_HEAVYWEIGHTS}
    assert "NSE_FNO:NIFTY:2026-09-29" in ids
    assert any(i.startswith("BSE_FNO:SENSEX:") and i.count(":") == 2 for i in ids)
    assert len(ids) == 58  # 48 book (ATM + open ladder) + 10 cash; futures already on the books
    unique_keys = {(r["exchange_segment"], r["security_id"]) for r in subs}
    assert len(unique_keys) == 58
    assert {"IDX_I", "NSE_FNO", "BSE_FNO", "NSE_EQ"} <= {r["exchange_segment"] for r in subs}

    depth = s.rows("depth_quotes")
    assert depth
    assert all(r["stream"] == "md:depth" for r in depth)
    assert all("volume" not in r["payload"] for r in depth)
    assert all(not r["payload"]["instrument_id"].startswith("NSE_EQ:") for r in depth)
    quotes = s.rows("quote_snapshots")
    assert quotes
    assert {r["payload"]["rule"] for r in quotes} == {"ATM", "ITM100", "ITM200", "OTM100", "OTM200"}
    assert all(r["payload"]["side"] in ("CE", "PE") for r in quotes)
    assert all(r["stream"] == "md:quotes" for r in quotes)
    assert all("volume" in r["payload"] for r in quotes)
    assert all(r["payload"]["volume"] == 50_000 for r in quotes)

    research = s.rows("research_quotes")
    assert research
    assert all(r["event_type"] == "RESEARCH_QUOTE" for r in research)
    assert all(r["stream"] == RESEARCH_STREAM for r in research)
    kinds = {r["payload"]["kind"] for r in research}
    assert kinds == {"FUTURE", "EQUITY"}
    stock_rows = [r for r in research if r["payload"]["kind"] == "EQUITY"]
    fut_rows = [r for r in research if r["payload"]["kind"] == "FUTURE"]
    assert {r["payload"]["instrument_id"] for r in stock_rows} == {f"NSE_EQ:{n}" for n in NIFTY_HEAVYWEIGHTS}
    assert fut_rows
    assert all(r["payload"].get("volume") == 50_000 for r in research if not r["payload"]["repeat"])
    assert all("bid" in r["payload"] and "ask" in r["payload"] and "ltp" in r["payload"] for r in research)
    assert all(r["payload"]["oi"] is not None for r in fut_rows)

    counts, errors = schema_errors(s.day_dir)
    assert errors == []
    assert counts["depth_quotes"] > 0
    import json

    cov = json.loads((s.day_dir / "coverage_summary.json").read_text())
    assert not any(i.startswith("NSE_EQ:") for i in cov["instruments"])


def test_research_off_keeps_legacy_subscribe_count(tmp_path) -> None:  # type: ignore[no-untyped-def]
    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 0, 4),
            source=StubSource(),
            config_kw={"underlyings": ("NIFTY", "SENSEX")},
        )
    )
    ids = {r["instrument_id"] for r in s.rows("subscriptions") if r["action"] == "subscribe"}
    assert len(ids) == 48
    assert s.rows("research_quotes") == []
