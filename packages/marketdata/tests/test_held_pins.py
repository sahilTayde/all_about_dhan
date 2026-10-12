"""Held-contract pins, session-open ladder, coverage alert. Paper / shadow only."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import date
from pathlib import Path

from md_fake_dhan import DAY, EXPIRY, ist, make_universe, option_sid, run_session

from marketdata.pins import HeldPinReader, is_option_id, option_instrument_id
from marketdata.strikes import StrikeSet

HELD = f"NSE_FNO:NIFTY:{EXPIRY}:24000:CE"
DAY_S = DAY.isoformat()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_option_id_helpers() -> None:
    assert option_instrument_id("NIFTY", EXPIRY, 24000, "ce") == HELD
    assert option_instrument_id("SENSEX", "2026-10-01", 81200, "PE") == "BSE_FNO:SENSEX:2026-10-01:81200:PE"
    assert is_option_id(HELD)
    assert not is_option_id("NSE_IDX:NIFTY")


def test_pin_reader_merges_paper_journal_shadow_ledger_and_drops_exits(tmp_path: Path) -> None:
    universe = make_universe()
    open_row = {
        "trade_id": "t-open",
        "underlying": "NIFTY",
        "side": "CE",
        "atm_strike": 24000,
        "opened_ts": 1,
        "closed_ts": None,
    }
    closed_row = {
        "trade_id": "t-closed",
        "underlying": "NIFTY",
        "side": "PE",
        "atm_strike": 24100,
        "opened_ts": 1,
        "closed_ts": 2,
    }
    _write(
        tmp_path / "data" / "recon" / "paper_booked" / f"{DAY_S}.jsonl",
        json.dumps(open_row) + "\n" + json.dumps(closed_row) + "\n",
    )
    _write(
        tmp_path / "data" / "recon" / "paper_booked" / f"{DAY_S}.state.json",
        json.dumps(
            {
                "open": {
                    "t-state": {
                        "underlying": "NIFTY",
                        "side": "PE",
                        "atm_strike": 23900,
                        "opened_ts": 1,
                    }
                }
            }
        ),
    )
    journal = tmp_path / "data" / "recon" / "decision_journal" / f"{DAY_S}.jsonl"
    _write(
        journal,
        "\n".join(
            [
                json.dumps(
                    {
                        "candidate_id": "c-open",
                        "stage": "in_trade",
                        "decision": "pass",
                        "instrument_id": f"NSE_FNO:NIFTY:{EXPIRY}:23800:CE",
                    }
                ),
                json.dumps(
                    {
                        "candidate_id": "c-done",
                        "stage": "in_trade",
                        "decision": "pass",
                        "instrument_id": f"NSE_FNO:NIFTY:{EXPIRY}:23700:CE",
                    }
                ),
                json.dumps({"candidate_id": "c-done", "stage": "exit", "decision": "exit"}),
            ]
        )
        + "\n",
    )
    shadow = tmp_path / "data" / "shadow" / "v2" / DAY_S
    _write(
        shadow / "decisions.jsonl",
        json.dumps(
            {
                "action": "ENTER",
                "instrument_id": f"NSE_FNO:NIFTY:{EXPIRY}:23600:PE",
                "side": "PE",
                "underlying": "NIFTY",
            }
        )
        + "\n",
    )
    _write(
        shadow / "pnl.jsonl",
        json.dumps(
            {
                "kind": "SHADOW_OPEN",
                "instrument_id": f"NSE_FNO:NIFTY:{EXPIRY}:23600:PE",
            }
        )
        + "\n",
    )
    db = tmp_path / "data" / "ledger" / "ledger.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE positions_v2 (account_id TEXT, instrument_id TEXT, net_qty INTEGER)"
    )
    con.execute(
        "INSERT INTO positions_v2 VALUES ('founder', ?, 65)",
        (f"NSE_FNO:NIFTY:{EXPIRY}:23500:CE",),
    )
    con.execute(
        "INSERT INTO positions_v2 VALUES ('founder', ?, 0)",
        (f"NSE_FNO:NIFTY:{EXPIRY}:23400:CE",),
    )
    con.commit()
    con.close()

    pins = HeldPinReader(tmp_path, DAY, [universe])
    got = pins()
    assert HELD in got
    assert f"NSE_FNO:NIFTY:{EXPIRY}:23900:PE" in got
    assert f"NSE_FNO:NIFTY:{EXPIRY}:23800:CE" in got
    assert f"NSE_FNO:NIFTY:{EXPIRY}:23600:PE" in got
    assert f"NSE_FNO:NIFTY:{EXPIRY}:23500:CE" in got
    assert f"NSE_FNO:NIFTY:{EXPIRY}:24100:PE" not in got
    assert f"NSE_FNO:NIFTY:{EXPIRY}:23700:CE" not in got
    assert f"NSE_FNO:NIFTY:{EXPIRY}:23400:CE" not in got


def test_held_contract_stays_subscribed_after_atm_walks_away() -> None:
    keep = HELD
    s = StrikeSet(make_universe(), retention_s=1.0, open_positions=lambda: {keep}, open_ladder_n=5)
    s.update(24512.35, 0.0)
    s.update(25200.0, 2.0)
    s.update(25200.0, 20.0)
    assert keep in s.subscribed
    assert keep not in s.current
    assert keep not in s.open_ladder


def test_recorder_keeps_held_quote_and_alerts_coverage_gap(tmp_path: Path) -> None:
    _write(
        tmp_path / "data" / "recon" / "paper_booked" / f"{DAY_S}.jsonl",
        json.dumps(
            {
                "trade_id": "held-1",
                "underlying": "NIFTY",
                "side": "CE",
                "atm_strike": 24000,
                "opened_ts": 1,
            }
        )
        + "\n",
    )
    silent_sid = option_sid(24000, "CE")

    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 0, 12),
            source=None,
            universe=make_universe(),
            config_kw={"pin_root": tmp_path, "open_ladder_n": 5},
            market_kw={"silent": {silent_sid: [(ist(10, 0, 3), ist(10, 0, 12))]}},
        )
    )
    assert HELD in s.recorder.books[0].strikes.subscribed
    subs = {r["instrument_id"] for r in s.rows("subscriptions") if r["action"] == "subscribe"}
    assert HELD in subs
    alerts = [r["payload"] for r in s.rows("feed_status") if r["payload"].get("status") == "COVERAGE_ALERT"]
    assert alerts
    assert alerts[0]["instrument_id"] == HELD
    assert alerts[0]["held"] is True
    assert float(alerts[0]["gap_s"]) > 5.0
    depth = [r for r in s.rows("depth_quotes") if r["payload"]["instrument_id"] == HELD]
    assert depth


def test_held_strike_keeps_quote_snapshots_after_index_moves_away() -> None:
    """2026-10-12 snapshot gap: the moving near-ATM set dropped a strike still held; it stayed subscribed but
    got no QUOTE_SNAPSHOT. Held contracts are now in the snapshot set (rule HELD) until the trade closes."""
    held = {HELD}
    s = StrikeSet(make_universe(), retention_s=1.0, open_positions=lambda: set(held), near_atm_n=4)
    s.update(24512.35, 0.0)
    s.update(25200.0, 2.0)
    s.update(25200.0, 20.0)
    assert HELD not in s.current and HELD in s.subscribed
    assert s.snapshot_targets()[HELD][0] == "HELD"
    held.clear()  # trade closed
    assert HELD not in s.snapshot_targets()


def test_research_rules_desk_and_shadow_opens_are_pinned(tmp_path: Path) -> None:
    j = tmp_path / "data" / "recon" / "research_rules"
    j.mkdir(parents=True)
    (j / f"{DAY_S}.json").write_text(json.dumps({
        "open": [{"underlying": "NIFTY", "side": "PE", "atm_strike": 24300, "held_strike": 24300}],
        "closed": [{"underlying": "NIFTY", "side": "CE", "atm_strike": 24400, "closed_ts": 5}],
        "shadow_parked": {"open": [{"underlying": "NIFTY", "side": "CE", "atm_strike": 24600}], "closed": []}}))
    got = HeldPinReader(tmp_path, DAY, [make_universe()])()
    assert f"NSE_FNO:NIFTY:{EXPIRY}:24300:PE" in got and f"NSE_FNO:NIFTY:{EXPIRY}:24600:CE" in got
    assert f"NSE_FNO:NIFTY:{EXPIRY}:24400:CE" not in got
