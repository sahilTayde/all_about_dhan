from datetime import date

from dhan_client.futidx import parse_all_futidx_csv, parse_futidx_csv


CSV = """INSTRUMENT,SECURITY_ID,UNDERLYING_SYMBOL,DISPLAY_NAME,SM_EXPIRY_DATE,EXCH_ID,SEGMENT
FUTIDX,35938,NIFTYFPI,NIFTYFPI SEP FUT,2026-09-29,NSE,D
FUTIDX,68407,NIFTY,NIFTY SEP FUT,2026-09-29,NSE,D
FUTIDX,68390,BANKNIFTY,BANKNIFTY SEP FUT,2026-09-29,NSE,D
FUTIDX,844615,SENSEX,SENSEX SEP FUT,2026-09-24,BSE,D
FUTIDX,48704,NIFTY,NIFTY OCT FUT,2026-10-27,NSE,D
"""


def test_nearest_unexpired():
    got = parse_futidx_csv(CSV, as_of=date(2026, 9, 3))
    assert set(got) == {"NIFTY", "BANKNIFTY", "SENSEX"}
    assert got["NIFTY"].security_id == "68407"
    assert got["BANKNIFTY"].security_id == "68390"
    assert got["SENSEX"].security_id == "844615"
    assert got["SENSEX"].exchange_segment == "BSE_FNO"


def test_parse_all_keeps_front_and_back():
    got = parse_all_futidx_csv(CSV)
    assert [c.security_id for c in got["NIFTY"]] == ["68407", "48704"]
    assert got["BANKNIFTY"][0].security_id == "68390"
