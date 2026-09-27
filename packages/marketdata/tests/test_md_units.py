"""Unit checks: instrument resolution, strike set, frame wrapper, tape repair, coverage."""

from __future__ import annotations

import json
import os
import random
from datetime import date
from pathlib import Path

import pytest
from dhan_client.decode import decode_frame, packet_as_dict
from dhan_client.errors import DhanApiError
from md_fake_dhan import (
    DAY,
    EXPIRY,
    StubSource,
    full_packet,
    index_packet,
    ist,
    make_universe,
    oi_packet,
    option_chain,
    option_sid,
    scrip_master_csv,
)

from marketdata.clock import IST
from marketdata.coverage import summarize
from marketdata.frames import decode_frame_checked
from marketdata.instruments import (
    StartupError,
    build_universe,
    load_cached_universe,
    load_universe,
    parse_scrip_master,
    save_universe,
)
from marketdata.strikes import StrikeSet
from marketdata.tape import TapeWriter, repair_tail

# ---- instruments -------------------------------------------------------------------------


def test_universe_from_compact_csv_and_option_chain() -> None:
    u = load_universe(StubSource(), "NIFTY", DAY, sleep=lambda _s: None)
    assert u.expiry == "2026-09-29"  # Tuesday, from the expiry list API (2026-09-22 already passed)
    assert u.spot == 24512.35
    assert u.strike_step == 50
    assert (u.index.security_id, u.index.exchange_segment, u.index.instrument_id) == ("13", "IDX_I", "NSE_IDX:NIFTY")
    assert u.future is not None
    assert (u.future.security_id, u.future.expiry) == ("35000", "2026-09-29")  # nearest FUTIDX, not FINNIFTY
    assert u.future.instrument_id == "NSE_FNO:NIFTY:2026-09-29"
    atm = u.options[(24500, "CE")]
    assert (atm.security_id, atm.exchange_segment) == (str(option_sid(24500, "CE")), "NSE_FNO")
    assert atm.instrument_id == "NSE_FNO:NIFTY:2026-09-29:24500:CE"
    assert len(u.options) == 202


def test_detailed_csv_columns_and_sensex_segment() -> None:
    header = (
        "EXCH_ID,SEGMENT,SECURITY_ID,ISIN,INSTRUMENT,UNDERLYING_SECURITY_ID,UNDERLYING_SYMBOL,SYMBOL_NAME,"
        "DISPLAY_NAME,INSTRUMENT_TYPE,SERIES,LOT_SIZE,SM_EXPIRY_DATE,STRIKE_PRICE,OPTION_TYPE,TICK_SIZE,EXPIRY_FLAG"
    )
    rows = [header, "BSE,I,51,NA,INDEX,51,SENSEX,SENSEX,SENSEX,INDEX,NA,1,,0,XX,0.05,NA"]
    rows.append("BSE,D,700,NA,FUTIDX,51,SENSEX,SENSEX-Oct2026-FUT,SENSEX OCT FUT,FUT,NA,20,2026-10-29,-0.01,XX,0.05,M")
    for k in range(80000, 83001, 100):
        for side in ("CE", "PE"):
            sid = 800000 + k // 100 * 2 + (side == "PE")
            rows.append(
                f"BSE,D,{sid},NA,OPTIDX,51,SENSEX,SENSEX-Oct2026-{k}-{side},SENSEX {k} {side},OP,NA,20,"
                f"2026-10-01,{k}.00000,{side},0.05,W"
            )
    text = "\n".join(rows) + "\n"
    sm = parse_scrip_master(text, "SENSEX")
    assert sm.index_ids == ["51"]
    u = build_universe(text, sm, {"last_price": 81234.5}, "SENSEX", DAY, "2026-10-01")
    assert u.strike_step == 100
    assert u.index.instrument_id == "BSE_IDX:SENSEX"
    opt = u.options[(81200, "PE")]
    assert (opt.exchange_segment, opt.instrument_id) == ("BSE_FNO", "BSE_FNO:SENSEX:2026-10-01:81200:PE")
    assert u.future is not None
    assert u.future.exchange_segment == "BSE_FNO"


def test_chain_security_ids_win_over_csv() -> None:
    text = scrip_master_csv()
    chain = option_chain()
    chain["oc"]["24500.000000"]["ce"]["security_id"] = 99_999
    u = build_universe(text, parse_scrip_master(text, "NIFTY"), chain, "NIFTY", DAY, EXPIRY)
    assert u.options[(24500, "CE")].security_id == "99999"


def test_startup_errors_are_loud_and_classified() -> None:
    with pytest.raises(StartupError, match="no last_price"):
        load_universe(_Src(chain={"oc": {}}), "NIFTY", DAY, sleep=lambda _s: None)
    with pytest.raises(StartupError, match="not a CSV"):
        load_universe(_Src(csv="<html>blocked</html>"), "NIFTY", DAY, sleep=lambda _s: None)
    delays: list[float] = []
    flaky = StubSource(fail={"option_chain": [DhanApiError("network"), DhanApiError("x", status_code=502)]})
    assert load_universe(flaky, "NIFTY", DAY, sleep=delays.append).expiry == EXPIRY
    assert delays == [2.0, 4.0]


class _Src(StubSource):
    def __init__(self, csv: str | None = None, chain: dict | None = None) -> None:  # type: ignore[type-arg]
        super().__init__()
        self._csv, self._chain = csv, chain

    def scrip_master_csv(self) -> str:
        return self._csv if self._csv is not None else super().scrip_master_csv()

    def option_chain(self, underlying_scrip: int, underlying_seg: str, expiry: str) -> dict:  # type: ignore[type-arg]
        return (
            self._chain if self._chain is not None else super().option_chain(underlying_scrip, underlying_seg, expiry)
        )


def test_universe_cache_round_trip(tmp_path: Path) -> None:
    u = make_universe()
    save_universe(u, tmp_path, DAY)
    cached = load_cached_universe(tmp_path, "NIFTY", DAY)
    assert cached is not None
    assert cached[0] == u
    assert load_cached_universe(tmp_path, "NIFTY", date(2026, 9, 30)) is None  # expiry passed


# ---- strike set --------------------------------------------------------------------------


def test_itm_direction_and_recentre_with_retention() -> None:
    s = StrikeSet(make_universe(), retention_s=600)
    first = s.update(24512.35, 0.0)
    assert [i.instrument_id for i in first.subscribe][:2] == ["NSE_IDX:NIFTY", "NSE_FNO:NIFTY:2026-09-29"]
    assert s.current == {
        "NSE_FNO:NIFTY:2026-09-29:24500:CE": ("ATM", "CE"),
        "NSE_FNO:NIFTY:2026-09-29:24400:CE": ("ITM100", "CE"),
        "NSE_FNO:NIFTY:2026-09-29:24300:CE": ("ITM200", "CE"),
        "NSE_FNO:NIFTY:2026-09-29:24500:PE": ("ATM", "PE"),
        "NSE_FNO:NIFTY:2026-09-29:24600:PE": ("ITM100", "PE"),
        "NSE_FNO:NIFTY:2026-09-29:24700:PE": ("ITM200", "PE"),
    }
    assert not s.update(24534.0, 10.0).subscribe  # inside hysteresis (|24534-24500| <= 35)
    moved = s.update(24560.0, 20.0)
    assert moved.recentred
    assert moved.atm == 24550
    assert {i.instrument_id for i in moved.subscribe} == {
        "NSE_FNO:NIFTY:2026-09-29:24550:CE",
        "NSE_FNO:NIFTY:2026-09-29:24450:CE",
        "NSE_FNO:NIFTY:2026-09-29:24350:CE",
        "NSE_FNO:NIFTY:2026-09-29:24550:PE",
        "NSE_FNO:NIFTY:2026-09-29:24650:PE",
        "NSE_FNO:NIFTY:2026-09-29:24750:PE",
    }
    assert not s.update(24560.0, 619.0).unsubscribe
    dropped = s.update(24560.0, 620.0).unsubscribe
    assert len(dropped) == 6
    assert len(s.subscribed) == 8


def test_open_positions_are_never_dropped_and_cap_holds() -> None:
    keep = "NSE_FNO:NIFTY:2026-09-29:24500:CE"
    s = StrikeSet(make_universe(), retention_s=600, max_instruments=20, open_positions=lambda: {keep})
    s.update(24512.35, 0.0)
    for i, spot in enumerate(range(24600, 26000, 100)):
        s.update(float(spot), 1.0 + i)
    assert keep in s.subscribed
    assert len(s.subscribed) <= 20
    s.update(25900.0, 5000.0)
    assert keep in s.subscribed


# ---- frames ------------------------------------------------------------------------------


def test_frame_wrapper_matches_decode_frame_on_good_frames() -> None:
    rng = random.Random(7)
    for _ in range(200):
        parts = []
        for _ in range(rng.randint(1, 6)):
            kind = rng.choice(["full", "index", "oi"])
            sid = rng.randint(1, 2**31 - 1)
            if kind == "full":
                parts.append(full_packet(sid, 2, rng.uniform(1, 500), 10.0, 10.05, oi=rng.randint(0, 2**31)))
            elif kind == "index":
                parts.append(index_packet(sid, rng.uniform(1000, 90000)))
            else:
                parts.append(oi_packet(sid, 2, rng.randint(0, 2**31 - 1)))
        frame = b"".join(parts)
        packets, errors = decode_frame_checked(frame)
        assert errors == []
        assert [packet_as_dict(p.decoded) for p in packets] == [packet_as_dict(p) for p in decode_frame(frame)]
        assert b"".join(p.raw for p in packets) == frame


# ---- tape --------------------------------------------------------------------------------


def _rows(path: Path) -> list[dict]:  # type: ignore[type-arg]
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_tape_repairs_partial_line_and_long_nul_tail(tmp_path: Path) -> None:
    w = TapeWriter(tmp_path, "s")
    for i in range(500):
        w.write({"i": i}, ist(10, 0))
    w.close()
    path = tmp_path / "2026-09-28" / "s.jsonl"
    good = path.read_bytes()
    with open(path, "ab") as f:
        f.write(b'{"i": 500, "partial')
        f.write(b"\0" * 100_000)  # longer than any fixed scan window
    info = repair_tail(path)
    assert info is not None
    assert info["offset"] == len(good)
    assert info["nul_bytes"] == 100_000
    assert path.read_bytes() == good
    w2 = TapeWriter(tmp_path, "s")
    w2.write({"i": 501}, ist(10, 1))
    w2.close()
    assert [r["i"] for r in _rows(path)] == [*range(500), 501]


def test_tape_nan_written_as_null_and_file_without_newline(tmp_path: Path) -> None:
    w = TapeWriter(tmp_path, "s")
    w.write({"x": float("nan"), "y": [1.0, float("inf")], "z": {"a": float("-inf")}}, ist(10, 0))
    w.close()
    assert _rows(tmp_path / "2026-09-28" / "s.jsonl") == [{"x": None, "y": [1.0, None], "z": {"a": None}}]
    lone = tmp_path / "lone.jsonl"
    lone.write_bytes(b'{"half": ')
    info = repair_tail(lone)
    assert info is not None
    assert info["removed_bytes"] == 9
    assert lone.read_bytes() == b""


def test_tape_day_folder_is_ist_date(tmp_path: Path) -> None:
    w = TapeWriter(tmp_path, "s")
    from datetime import datetime, timezone

    w.write({"a": 1}, datetime(2026, 9, 27, 19, 0, tzinfo=timezone.utc))  # 00:30 IST on the 28th
    w.close()
    assert (tmp_path / "2026-09-28" / "s.jsonl").is_file()
    assert oct(os.stat(tmp_path / "2026-09-28" / "s.jsonl").st_mode)[-3:] == "644"
    assert IST.utcoffset(None).total_seconds() == 19800


# ---- coverage ----------------------------------------------------------------------------


def test_coverage_summary_reports_a_two_minute_gap(tmp_path: Path) -> None:
    day_dir = tmp_path / "2026-09-28"
    day_dir.mkdir()
    iid = "NSE_FNO:NIFTY:2026-09-29:24500:CE"
    (day_dir / "subscriptions.jsonl").write_text(
        json.dumps({"ts": ist(9, 13).isoformat(), "action": "subscribe", "instrument_id": iid}) + "\n"
    )
    lines = []
    for minute in range(375):
        if minute in (105, 106):  # 11:00-11:02 silent
            continue
        t = ist(9, 15) + (ist(9, 16) - ist(9, 15)) * minute
        payload = {"instrument_id": iid, "exchange_ts": t.isoformat(), "repeat": False}
        lines.append(json.dumps({"timestamp": t.isoformat(), "payload": payload}))
    (day_dir / "depth_quotes.jsonl").write_text("\n".join(lines) + "\n{broken\n")
    s = summarize(day_dir, DAY)
    row = s["instruments"][iid]
    assert row["subscribed_minutes"] == 375
    assert row["minutes_with_depth"] == 373
    assert row["gaps"] == [["11:00", "11:02"]]
    assert row["pct_of_subscribed"] == round(100 * 373 / 375, 2)
    assert s["failing"] == []
    assert s["bad_lines"]["depth_quotes"] == 1


def test_background_flush_never_blocks_on_a_slow_disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    real_fsync = os.fsync

    def slow_fsync(fd: int) -> None:
        time.sleep(0.3)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", slow_fsync)
    writers = [TapeWriter(tmp_path, f"s{i}", background=True) for i in range(7)]
    t0 = time.perf_counter()
    for second in range(3):
        for w in writers:
            w.write({"second": second}, ist(10, 0, second))
            w.flush()
    assert time.perf_counter() - t0 < 0.2  # 21 fsyncs of 0.3 s ran off this thread
    for w in writers:
        w.close()
    for i in range(7):
        assert [r["second"] for r in _rows(tmp_path / "2026-09-28" / f"s{i}.jsonl")] == [0, 1, 2]
