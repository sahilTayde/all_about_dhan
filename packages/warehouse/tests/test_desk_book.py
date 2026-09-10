from warehouse.constituents import parse_equity_ids
from warehouse.store import Warehouse


CSV = """INSTRUMENT,SECURITY_ID,UNDERLYING_SYMBOL,SYMBOL_NAME,SERIES,EXCH_ID
EQUITY,1333,HDFCBANK,HDFC BANK LTD,EQ,NSE
EQUITY,2885,RELIANCE,RELIANCE INDUSTRIES LTD,EQ,NSE
EQUITY,500180,HDFCBANK,HDFC BANK LTD,A,BSE
"""


def test_parse_equity_ids() -> None:
    found = parse_equity_ids(CSV, {"HDFCBANK", "RELIANCE"}, prefer_segment="NSE_EQ")
    assert found["HDFCBANK"] == ("1333", "NSE_EQ")
    assert found["RELIANCE"][0] == "2885"
    bse = parse_equity_ids(CSV, {"HDFCBANK"}, prefer_segment="BSE_EQ")
    assert bse["HDFCBANK"][0] == "500180"


def test_persist_strikes_and_levels(tmp_path) -> None:
    wh = Warehouse(tmp_path / "w.sqlite")
    wh.init()
    snap_id = wh.insert_chain_snapshot_row(
        underlying="NIFTY",
        expiry="2026-09-15",
        atm="25000",
        pcr=0.9,
        payload={"strikes": 1},
    )
    assert snap_id > 0
    n = wh.append_strike_rows(
        snap_id,
        [
            {
                "underlying": "NIFTY",
                "expiry": "2026-09-15",
                "as_of": "2026-09-10T09:00:00+05:30",
                "strike": 25000,
                "ce_ltp": 150.0,
                "pe_ltp": 140.0,
                "ce_oi": 100,
                "pe_oi": 90,
            }
        ],
    )
    assert n == 1
    wh.append_option_level(
        {
            "snapshot_id": snap_id,
            "underlying": "NIFTY",
            "expiry": "2026-09-15",
            "as_of": "2026-09-10T09:00:00+05:30",
            "side": "CE",
            "strike": 25000,
            "entry": 150,
            "stop_hyp": 112.5,
            "target_hyp": 187.5,
            "dealer_action": "HOLD",
            "dealer_reason": "DATA_INSUFFICIENT",
            "layer": "HYPOTHESIS",
        }
    )
    st = wh.status()
    assert st["counts"]["chain_strike_rows"] == 1
    assert st["counts"]["option_levels"] == 1
