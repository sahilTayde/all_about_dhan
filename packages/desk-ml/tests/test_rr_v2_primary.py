"""2026-10-12 skipped R01 10:44 IST NIFTY 22450 PE: the legacy DUAL-TAPE carried the last index LTP with
premium_source=unavailable / chain_source=fixture from ~10:31 to 11:02 IST, while V2 was clean. Desk
research rules now price/signal from V2 first, legacy only as fallback, and never treat a carried print
as fresh."""

from __future__ import annotations

import json
from pathlib import Path

from desk_ml import research_rules as rr
from desk_ml.tape import _snap_ltps, is_carried_over
from trading_agents_india.dual_tape import carried_over_sources

from test_research_rules_v2_fill import DAY, _ts, _write_dual, _write_v2

CARRIED = {"index_source": "carry_prev", "premium_source": "unavailable", "chain_source": "fixture"}


def test_carried_print_flagged_and_not_a_tick() -> None:
    assert carried_over_sources(**CARRIED)
    assert not carried_over_sources(index_source="dhan_intraday_1m", premium_source="dhan_rollingoption_1m",
                                    chain_source="dhan_live")
    assert not carried_over_sources(index_source="dhan_intraday_1m", premium_source="unavailable",
                                    chain_source="dhan_live")  # chain LTP is live: fresh
    snap = {"underlying": "NIFTY", "index_ltp": 22457.1, "atm_ce_ltp": 99.75, "atm_pe_ltp": 93.35, **CARRIED}
    assert is_carried_over(snap) and _snap_ltps(snap) is None


def test_v2_is_primary_legacy_fills_gaps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DESK_RR_SOURCE", raising=False)
    rr._V2_STATE.clear()
    _write_dual(tmp_path, ["10:30", "10:31"])
    _write_v2(tmp_path, ["10:31", "10:32"])
    bars = rr.load_minutes_v2_primary(tmp_path, "NIFTY", DAY)
    assert list(bars) == ["10:30", "10:31", "10:32"]
    assert bars["10:31"]["source"] == "v2" and bars["10:31"]["idx"] == 25020.0
    assert bars["10:30"]["source"] == "dual_tape_fallback"
    res = rr.replay(tmp_path, DAY, underlyings=("NIFTY",))
    assert res["price_source"].startswith("v2_primary") and res["per_underlying"]["NIFTY"]["n_minutes"] == 3


def test_legacy_carried_snaps_dropped(tmp_path: Path) -> None:
    folder = tmp_path / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    folder.mkdir(parents=True)
    rows = []
    for m, extra in (("10:31", {}), ("10:44", CARRIED)):
        snap = {"underlying": "NIFTY", "as_of_ist": _ts(m), "index_ltp": 22457.1, "atm_strike": 22450.0,
                "atm_ce_ltp": 99.75, "atm_pe_ltp": 93.35, **extra}
        rows.append(json.dumps({"as_of_ist": _ts(m), "underlyings": [snap]}))
    (folder / f"{DAY}.jsonl").write_text("\n".join(rows) + "\n")
    assert list(rr.load_atm_minutes(tmp_path, "NIFTY", DAY)) == ["10:31"]


def test_v2_reads_are_incremental(tmp_path: Path) -> None:
    rr._V2_STATE.clear()
    _write_v2(tmp_path, ["10:31"])
    assert list(rr.load_v2_minutes(tmp_path, "NIFTY", DAY)) == ["10:31"]
    key = next(iter(rr._V2_STATE))
    off = rr._V2_STATE[key]["off_qs"]
    folder = tmp_path / "data" / "tape" / "v2" / DAY
    extra = tmp_path / "x"; _write_v2(extra, ["10:32"])
    for name in ("depth_quotes.jsonl", "quote_snapshots.jsonl"):
        with (folder / name).open("a") as fh:
            fh.write((extra / "data" / "tape" / "v2" / DAY / name).read_text())
    assert list(rr.load_v2_minutes(tmp_path, "NIFTY", DAY)) == ["10:31", "10:32"]
    assert rr._V2_STATE[key]["off_qs"] > off
