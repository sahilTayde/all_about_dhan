"""V2-recorder gap fill for research_rules replay. Synthetic tapes only; never touches data/."""

from __future__ import annotations

import json
from pathlib import Path

from desk_ml import research_rules as rr

DAY = "2026-10-09"


def _ts(hhmm: str, sec: int = 50) -> str:
    return f"{DAY}T{hhmm}:{sec:02d}+05:30"


def _write_dual(root: Path, minutes: list[str]) -> None:
    folder = root / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{DAY}.jsonl").open("w", encoding="utf-8") as fh:
        for m in minutes:
            snap = {"underlying": "NIFTY", "as_of_ist": _ts(m), "index_ltp": 25000.0, "atm_strike": 25000.0,
                    "atm_ce_ltp": 100.0, "atm_pe_ltp": 90.0,
                    "wing_quotes": {"25000": {"ce": 100.0, "pe": 90.0, "ce_bid": 99.9, "ce_ask": 100.1}}}
            fh.write(json.dumps({"as_of_ist": _ts(m), "underlyings": [snap]}) + "\n")


def _write_v2(root: Path, minutes: list[str]) -> None:
    folder = root / "data" / "tape" / "v2" / DAY
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "depth_quotes.jsonl").open("w", encoding="utf-8") as fh:
        for m in minutes:
            for sec, px in ((5, 25010.0), (55, 25020.0)):
                fh.write(json.dumps({"payload": {"instrument_id": "NSE_IDX:NIFTY", "ltp": px,
                                                 "exchange_ts": _ts(m, sec)}, "timestamp": _ts(m, sec)}) + "\n")
            fh.write(json.dumps({"payload": {"instrument_id": "BSE_IDX:SENSEX", "ltp": 1.0,
                                             "exchange_ts": _ts(m)}, "timestamp": _ts(m)}) + "\n")
    with (folder / "quote_snapshots.jsonl").open("w", encoding="utf-8") as fh:
        for m in minutes:
            for strike, rule in ((25000, "ATM"), (25100, "OTM100")):
                for side, bid, ask in (("CE", 120.0, 121.0), ("PE", 80.0, 81.0)):
                    fh.write(json.dumps({"payload": {"instrument_id": f"NSE_FNO:NIFTY:2026-10-13:{strike}:{side}",
                                                     "rule": rule, "side": side, "bid": bid, "ask": ask, "ltp": bid},
                                         "timestamp": _ts(m, 30)}) + "\n")
            # a null (stale) quote later in the minute must not wipe the good one
            fh.write(json.dumps({"payload": {"instrument_id": "NSE_FNO:NIFTY:2026-10-13:25000:CE", "rule": "ATM",
                                             "bid": None, "ask": None, "ltp": None}, "timestamp": _ts(m, 59)}) + "\n")


def test_v2_fills_only_dual_tape_gaps(tmp_path: Path) -> None:
    _write_dual(tmp_path, ["10:30", "10:31", "11:02"])
    _write_v2(tmp_path, ["10:31", "10:32", "10:33", "11:01"])
    bars = rr.load_minutes_filled(tmp_path, "NIFTY", DAY)
    assert list(bars) == ["10:30", "10:31", "10:32", "10:33", "11:01", "11:02"]
    assert bars["10:31"]["source"] == "dual_tape" and bars["10:31"]["ce"] == 100.0  # never overwritten
    gap = bars["10:32"]
    assert gap["source"] == "v2_fill"
    assert gap["idx"] == 25020.0  # last index print of the minute
    assert gap["atm"] == 25000.0
    assert gap["ce"] == 120.5 and gap["pe"] == 80.5  # mid of the last non-null quote
    assert gap["wings"]["25000"]["ce_ask"] == 121.0 and gap["wings"]["25000"]["ce_bid"] == 120.0
    assert gap["wings"]["25100"]["pe_bid"] == 80.0
    q, flag = rr.strike_quote(gap, "CE", 25000.0, "ask")
    assert q == 121.0 and flag is None


def test_no_v2_folder_is_plain_dual_tape(tmp_path: Path) -> None:
    _write_dual(tmp_path, ["10:30", "10:32"])
    assert list(rr.load_minutes_filled(tmp_path, "NIFTY", DAY)) == ["10:30", "10:32"]
    assert rr.load_v2_minutes(tmp_path, "NIFTY", DAY) == {}


def test_replay_fill_flag_and_held_strike(tmp_path: Path) -> None:
    _write_dual(tmp_path, ["10:30", "10:31"])
    _write_v2(tmp_path, ["10:32"])
    off = rr.replay(tmp_path, DAY, underlyings=("NIFTY",), fill_v2=False)
    on = rr.replay(tmp_path, DAY, underlyings=("NIFTY",), fill_v2=True)
    assert off["v2_fill"] is False and off["per_underlying"]["NIFTY"]["n_minutes"] == 2
    assert on["v2_fill"] is True and on["per_underlying"]["NIFTY"]["n_minutes"] == 3
    row = rr._trade_row(rule=rr.FROZEN_RULES[0], underlying="NIFTY", side="CE", strike=25000.0,
                        sig_min="10:31", entry_min="10:32", exit_min="10:52", entry=121.0, mark=130.0,
                        day=DAY, entry_bar={"source": "v2_fill"}, mark_bar={"hhmm": "10:52"},
                        closed=True, reason="TIME")
    assert row["held_strike"] == 25000.0
    assert row["entry_price_source"] == "v2_fill" and row["exit_price_source"] == "dual_tape"


def _pe_bars(minutes: list[str], strike: float = 22350.0) -> dict:
    out = {}
    for i, m in enumerate(minutes):
        out[m] = {"hhmm": m, "atm": strike, "idx": 22350.0, "ce": 90.0, "pe": 80.0 + i,
                  "wings": {str(int(strike)): {"pe_bid": 80.0 + i, "pe_ask": 80.5 + i}}}
    return out


def test_h20_exit_not_left_open_when_spec_minute_missing() -> None:
    # 2026-10-12 live: spec exit 12:19 not on the tape, tape at 12:20 -> old rule waited for 12:21.
    bars = _pe_bars(["12:15", "12:17", "12:18", "12:20"])
    pick = rr._pick_exit(bars, list(bars), side="PE", strike=22350.0, spec_exit="12:19",
                         entry_min="11:59", last_hhmm="12:20")
    assert pick == ("12:18", 82.0, "EXIT_SHIFTED")  # tie 12:18/12:20 -> earlier


def test_h20_exit_by_wall_clock_when_tape_stalls() -> None:
    bars = _pe_bars(["12:15", "12:17"])
    assert rr._pick_exit(bars, list(bars), side="PE", strike=22350.0, spec_exit="12:19",
                         entry_min="11:59", last_hhmm="12:17") is None  # replay: not yet
    pick = rr._pick_exit(bars, list(bars), side="PE", strike=22350.0, spec_exit="12:19",
                         entry_min="11:59", last_hhmm="12:17", now_hhmm="12:19")
    assert pick == ("12:17", 81.0, "EXIT_SHIFTED")
    far = rr._pick_exit(bars, list(bars), side="PE", strike=22350.0, spec_exit="12:30",
                        entry_min="11:59", last_hhmm="12:17", now_hhmm="12:31")
    assert far == ("12:17", 81.0, "EXIT_EARLY_NO_QUOTE")


def test_h20_exit_never_open_without_any_strike_quote() -> None:
    bars = _pe_bars(["12:15", "12:17"], strike=22400.0)  # held 22350 never quoted
    pick = rr._pick_exit(bars, list(bars), side="PE", strike=22350.0, spec_exit="12:19",
                         entry_min="11:59", last_hhmm="12:17", now_hhmm="12:20")
    assert pick == ("11:59", None, "EXIT_NO_QUOTE_AT_ENTRY_PX")
