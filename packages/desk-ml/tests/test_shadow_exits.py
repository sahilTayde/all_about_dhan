"""Log-only alternative exits. No broker. Frozen variants next to the 20-min hold."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from desk_ml import research_rules as rr
from desk_ml import shadow_exits as sx

DAY = "2026-10-09"


def _ts(hhmm: str, sec: int = 50) -> str:
    return f"{DAY}T{hhmm}:{sec:02d}+05:30"


def _snap(und: str, hhmm: str, idx: float, ce: float, pe: float, atm: float = 25000.0) -> dict:
    return {
        "underlying": und,
        "as_of_ist": _ts(hhmm),
        "index_ltp": idx,
        "atm_strike": atm,
        "atm_ce_ltp": ce,
        "atm_pe_ltp": pe,
        "wing_quotes": {"25000": {"ce": ce, "pe": pe}},
    }


def _write_tape(root: Path, rows: list) -> None:
    folder = root / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{DAY}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for hhmm, snaps in rows:
            fh.write(json.dumps({"as_of_ist": _ts(hhmm), "underlyings": snaps, "orders": "refused"}) + "\n")


def _minutes(start: str, n: int) -> list[str]:
    out = [start]
    for _ in range(n - 1):
        out.append(rr.mplus(out[-1], 1))
    return out


def test_target_trail_and_dead_rules() -> None:
    entry = 100.0
    path = [
        ("10:01", 100.0),
        ("10:03", 111.0),  # +11% — T10 hits
        ("10:05", 140.0),  # peak
        ("10:06", 97.0),  # trail 30% from 140 → 98; 97 hits TR30
        ("10:08", 101.0),
        ("10:21", 105.0),
    ]
    t10 = sx.simulate_one(path, entry=entry, variant={"id": sx.R13_T10, "kind": "target", "pct": 0.10})
    assert t10["hit"] is True
    assert t10["exit_min"] == "10:03"
    assert t10["reason"] == "TARGET_10"
    t30 = sx.simulate_one(path, entry=entry, variant={"id": sx.R23_T30, "kind": "target", "pct": 0.30})
    assert t30["hit"] is True
    assert t30["exit_min"] == "10:05"
    assert t30["reason"] == "TARGET_30"
    trail = sx.simulate_one(path, entry=entry, variant={"id": sx.R17_TR30, "kind": "trail", "pct": 0.30})
    assert trail["hit"] is True
    assert trail["exit_min"] == "10:06"
    assert trail["reason"] == "TRAIL_30"
    dead_path = [("10:01", 100.0), ("10:08", 101.0), ("10:21", 102.0)]
    dead = sx.simulate_one(
        dead_path, entry=entry, variant={"id": sx.DEAD3_7, "kind": "dead", "pct": 0.03, "after_min": 7}
    )
    assert dead["hit"] is True
    assert dead["reason"] == "DEAD"
    assert dead["exit_min"] == "10:08"
    live_path = [("10:01", 100.0), ("10:08", 110.0), ("10:21", 112.0)]
    alive = sx.simulate_one(
        live_path, entry=entry, variant={"id": sx.DEAD3_7, "kind": "dead", "pct": 0.03, "after_min": 7}
    )
    assert alive["hit"] is False
    assert alive["reason"] == "TIME"
    assert alive["exit_min"] == "10:21"


def test_config_defaults_off_for_trade_on_for_shadow_log() -> None:
    cfg = sx.load_config(environ={})
    assert cfg["trade"] is False
    assert cfg["shadow_log"] is True
    assert [v["id"] for v in cfg["variants"]] == [
        sx.R13_T10,
        sx.R21_T10,
        sx.R17_TR30,
        sx.R23_T30,
        sx.R09_TR30,
        sx.DEAD3_7,
    ]
    assert sx.logging_enabled(environ={sx.FLAG_ENV: "0"}) is False
    assert sx.trade_enabled(environ={}) is False
    assert sx.trade_enabled(environ={sx.TRADE_ENV: "1"}) is True


def test_replay_attaches_variants_and_logs_closed_once(tmp_path: Path, pre_park_rule_set) -> None:
    mins = _minutes("09:30", 52)
    rows = []
    for hhmm in mins:
        idx = 25000.0
        ce, pe = 100.0, 100.0
        if hhmm == "10:00":
            idx = 25015.0
        if hhmm == "10:01":
            ce = 100.0
        if hhmm == "10:05":
            ce = 112.0  # T10
        if hhmm == "10:21":
            ce = 99.0
        rows.append((hhmm, [_snap("NIFTY", hhmm, idx, ce, pe)]))
    _write_tape(tmp_path, rows)
    out = rr.replay(tmp_path, DAY)
    mom = [t for t in out["closed"] if t["rule_id"] == rr.R02 and t["underlying"] == "NIFTY"]
    assert len(mom) == 1
    variants = mom[0]["exit_variants"]
    assert set(variants) == {sx.R13_T10, sx.R21_T10, sx.R17_TR30, sx.R23_T30, sx.R09_TR30, sx.DEAD3_7}
    assert variants[sx.R13_T10]["hit"] is True
    assert variants[sx.R13_T10]["exit_min"] == "10:05"
    assert variants[sx.R21_T10]["hit"] is True
    assert mom[0]["exit_reason"] == "TIME"
    assert mom[0]["exit_min"] == "10:21"
    board = {"session_ist_date": DAY, "open_trades": [], "closed_trades": []}
    rr.attach_to_board(board, root=tmp_path, environ={rr.FLAG_ENV: "1"})
    shadow = tmp_path / "data" / "shadow" / f"{DAY}.jsonl"
    assert shadow.is_file()
    rows_out = [json.loads(line) for line in shadow.read_text(encoding="utf-8").splitlines() if line.strip()]
    exits = [r for r in rows_out if r.get("schema") == sx.SCHEMA]
    assert len(exits) == len({t["trade_id"] for t in out["closed"]})
    first = exits[0]
    assert first["orders"] == "REFUSED"
    assert first["execution"] == "refused"
    assert first["default"]["hold_min"] == 20
    assert sx.R13_T10 in first["variants"]
    # Second attach must not duplicate.
    rr.attach_to_board(board, root=tmp_path, environ={rr.FLAG_ENV: "1"})
    rows2 = [json.loads(line) for line in shadow.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len([r for r in rows2 if r.get("schema") == sx.SCHEMA]) == len(exits)


def test_shadow_off_writes_nothing(tmp_path: Path) -> None:
    trade = {
        "trade_id": "RR-x",
        "status": "CLOSED",
        "closed_ts": 1_769_000_000,
        "opened_ts": 1_768_999_000,
        "exit_variants": {sx.R13_T10: {"hit": True}},
        "rule_id": rr.R02,
        "underlying": "NIFTY",
        "side": "CE",
        "entry": 100.0,
        "entry_min": "10:01",
        "exit_min": "10:21",
        "exit_reason": "TIME",
        "exit": 99.0,
    }
    written = sx.attach_and_log([trade], root=tmp_path, environ={sx.FLAG_ENV: "0"})
    assert written == []
    assert not (tmp_path / "data" / "shadow").exists()


def test_source_never_calls_a_broker() -> None:
    src = inspect.getsource(sx)
    assert "place_order" not in src
    assert "ExecutionClient" not in src
    assert "dhanhq" not in src.lower()
