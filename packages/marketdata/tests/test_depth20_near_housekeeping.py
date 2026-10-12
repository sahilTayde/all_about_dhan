"""2026-10-12 recorder upgrades (box fixtures only, no broker): 20-level depth parser, every 50-pt strike
near ATM, gzip of prior days and a free-space alert."""

from __future__ import annotations

import gzip
import os

from marketdata import depth20, housekeeping
from marketdata.config import RecorderConfig
from marketdata.strikes import StrikeSet
from md_fake_dhan import make_universe


def test_depth20_parse_both_sides_in_one_frame() -> None:
    bids = [(100.0 - i * 0.05, 65 * (i + 1), i + 1) for i in range(20)]
    asks = [(100.1 + i * 0.05, 65, 1) for i in range(12)]  # 8 empty levels
    frame = depth20.pack_message(41, 2, 43210, bids) + depth20.pack_message(51, 2, 43210, asks)
    msgs = depth20.parse_frame(frame)
    assert [m["side"] for m in msgs] == ["bid", "ask"]
    book = depth20.merge_sides(msgs)["43210"]
    assert len(book["bid"]) == 20 and book["bid"][19] == [99.05, 1300, 20]
    assert len(book["ask"]) == 12 and book["ask"][0] == [100.1, 65, 1]
    assert depth20.MESSAGE_LEN == 332


def test_depth20_ignores_truncated_and_unknown() -> None:
    m = depth20.pack_message(41, 2, 1, [(10.0, 1, 1)])
    assert depth20.parse_frame(m[:-1]) == []
    assert depth20.parse_frame(depth20.pack_message(99, 2, 1, [(10.0, 1, 1)])) == []


def test_every_50pt_strike_near_atm() -> None:
    u = make_universe()
    s = StrikeSet(u, near_atm_n=4, max_instruments=200)
    atm = s.nearest_strike(24512.35)
    t = s.targets(atm)
    strikes = {u_k[0] for u_k, inst in u.options.items() if inst.instrument_id in t}
    step = u.strike_step
    assert {atm + k * step for k in range(-4, 5)} <= strikes
    rules = {r for r, _ in t.values()}
    assert "ATM" in rules and "NEAR_P1" in rules and "NEAR_M3" in rules and "NEAR_M4" not in rules  # +-200 = named ITM/OTM200
    assert RecorderConfig(tape_root=".").near_atm_n == 0  # CLI turns it on (MD_NEAR_ATM_N, default 4)


def test_gzip_prior_days_and_disk_alert(tmp_path) -> None:
    for day in ("2026-10-09", "2026-10-12"):
        (tmp_path / day).mkdir()
        (tmp_path / day / "depth_quotes.jsonl").write_bytes(b'{"a":1}\n' * 1000)
    done = housekeeping.gzip_prior_days(tmp_path, "2026-10-12")
    assert done == [str(tmp_path / "2026-10-09" / "depth_quotes.jsonl.gz")]
    assert gzip.open(done[0]).read() == b'{"a":1}\n' * 1000
    assert not (tmp_path / "2026-10-09" / "depth_quotes.jsonl").exists()
    assert (tmp_path / "2026-10-12" / "depth_quotes.jsonl").exists()  # today untouched
    assert housekeeping.disk_alert(tmp_path, 30, free=29.9).startswith("ALERT")
    assert housekeeping.disk_alert(tmp_path, 30, free=116.0) is None
