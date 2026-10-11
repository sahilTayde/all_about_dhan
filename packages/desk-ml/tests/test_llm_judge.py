"""LLM shadow judge: mocked OpenAI, log-only, never changes a paper fill."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from desk_ml.llm_judge import (
    ACTOR,
    PROMPT_VERSION,
    SCHEMA,
    LlmJudge,
    attach_and_log,
    build_exit_snapshot,
    build_market_snapshot,
    build_pick_snapshot,
    collect_pick_events,
    load_config,
    paper_slot_ids,
    parse_exit,
    parse_pick,
    reset_judge,
    score,
    summarize_candles,
)
from desk_ml.persist import code_root

IST = timezone(timedelta(hours=5, minutes=30))
DAY = "2026-10-09"
TS = datetime(2026, 10, 9, 10, 31, tzinfo=IST)
SRC = Path(__file__).resolve().parents[1] / "src" / "desk_ml" / "llm_judge.py"
FORBIDDEN = (
    "brokers",
    "dhan_client",
    "desk_ml.paper_scalp",
    "desk_ml.event_path",
    "risk_engine",
)


def _snap(und: str, hhmm: str, idx: float, ce: float, pe: float, atm: float = 25000.0, oi_ce: float = 100.0) -> dict:
    return {
        "underlying": und,
        "as_of_ist": f"{DAY}T{hhmm}:50+05:30",
        "index_ltp": idx,
        "atm_strike": atm,
        "atm_ce_ltp": ce,
        "atm_pe_ltp": pe,
        "wing_quotes": {"25000": {"ce": ce, "pe": pe, "ce_oi": oi_ce, "pe_oi": 80.0}},
    }


def _write_tape(root: Path, rows: list[tuple[str, list[dict]]]) -> None:
    folder = root / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{DAY}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for hhmm, snaps in rows:
            fh.write(json.dumps({"as_of_ist": f"{DAY}T{hhmm}:50+05:30", "underlyings": snaps, "orders": "refused"}) + "\n")


def _minutes(start: str, n: int) -> list[str]:
    hour, minute = (int(p) for p in start.split(":"))
    out = []
    for i in range(n):
        total = hour * 60 + minute + i
        out.append(f"{total // 60:02d}:{total % 60:02d}")
    return out


def _pdiv_tape(root: Path) -> None:
    """Warm-up + a PDIV_5 CE fire at 10:00 (index flat, CE rips vs PE)."""
    minutes = _minutes("09:30", 32)
    rows = []
    for i, hhmm in enumerate(minutes):
        idx = 25000.0
        if hhmm == "10:00":
            ce, pe = 120.0, 80.0
        else:
            ce, pe = 100.0, 100.0
        rows.append((hhmm, [_snap("NIFTY", hhmm, idx, ce, pe)]))
    _write_tape(root, rows)


PICK_OK = '{"decision":"TAKE","confidence":0.7,"reason":"CE follows the tape"}'
SKIP_OK = '{"decision":"SKIP","confidence":0.4,"reason":"against vwap"}'
EXIT_OK = '{"action":"HOLD","reason":"premium still alive"}'
EXIT_CUT = '{"action":"EXIT","reason":"thesis broke"}'


class FakeLLM:
    def __init__(self, text: str = PICK_OK, delay: float = 0.0, exc: Exception | None = None) -> None:
        self.text = text
        self.delay = delay
        self.exc = exc
        self.calls = 0
        self.seen: list[str] = []

    def __call__(self, *, system: str, user: str) -> dict:
        self.calls += 1
        self.seen.append(system + user)
        if self.delay:
            import time

            time.sleep(self.delay)
        if self.exc:
            raise self.exc
        return {"text": self.text, "tokens_in": 80, "tokens_out": 20}


def test_parse_pick_and_exit_are_strict() -> None:
    assert parse_pick(PICK_OK)["decision"] == "TAKE"
    assert parse_exit(EXIT_OK)["action"] == "HOLD"
    with pytest.raises(ValueError):
        parse_pick('{"decision":"BUY","confidence":0.5,"reason":"x"}')
    with pytest.raises(ValueError):
        parse_pick(PICK_OK[:-1] + ',"extra":1}')
    with pytest.raises(ValueError):
        parse_exit('{"action":"WAIT","reason":"x"}')
    with pytest.raises(ValueError):
        parse_exit('{"action":"HOLD"}')


def test_config_forces_trade_false(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "llm_judge.yaml").write_text("shadow: true\ntrade: true\ntimeout_s: 3\n", encoding="utf-8")
    cfg = load_config(tmp_path, {"LLM_JUDGE_SHADOW": "1"})
    assert cfg["shadow"] is True
    assert cfg["trade"] is False
    assert cfg["timeout_s"] == 3.0


def test_missing_key_skips_without_calling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_KEY", raising=False)
    judge = LlmJudge(load_config(tmp_path, {}), root=tmp_path, environ={})
    out = judge.review("PICK", {"v": 1, "setup": "R01"}, dedupe_key="a")
    assert out["status"] == "skipped_no_key"
    assert judge.calls == 0
    judge.close()


def test_one_call_per_signal_and_cache(tmp_path: Path) -> None:
    fake = FakeLLM(PICK_OK)
    judge = LlmJudge(load_config(tmp_path), root=tmp_path, complete_fn=fake)
    snap = build_pick_snapshot(
        setup="R01_PDIV_5_ALL_H20",
        side="CE",
        strike=25000,
        underlying="NIFTY",
        market={"index": 25000, "vwap": 24990},
        source="paper_slot",
        hhmm="10:00",
        day=DAY,
    )
    first = judge.review("PICK", snap, dedupe_key="sig-1")
    second = judge.review("PICK", snap, dedupe_key="sig-1")
    third = judge.review("PICK", snap, dedupe_key="sig-2")
    assert first["decision"] == "TAKE"
    assert first["status"] == "ok"
    assert second["status"] == "skipped_dup_signal"
    assert third["cached"] is True
    assert fake.calls == 1
    assert judge.cost_usd > 0
    judge.close()


def test_one_exit_call_per_trade_minute(tmp_path: Path) -> None:
    fake = FakeLLM(EXIT_OK)
    judge = LlmJudge(load_config(tmp_path), root=tmp_path, complete_fn=fake)
    snap = build_exit_snapshot(
        trade={"trade_id": "t1", "side": "CE", "entry": 100, "last_ltp": 104, "opened_ist": f"{DAY}T10:01:00+05:30"},
        market={"index": 25010},
        hhmm="10:05",
        day=DAY,
    )
    a = judge.review("EXIT", snap, dedupe_key="exit:t1:2026-10-09:10:05")
    b = judge.review("EXIT", snap, dedupe_key="exit:t1:2026-10-09:10:05")
    c = judge.review("EXIT", {**snap, "hhmm": "10:06"}, dedupe_key="exit:t1:2026-10-09:10:06")
    assert a["action"] == "HOLD"
    assert b["status"] == "skipped_dup_minute"
    assert c["status"] == "ok"
    assert fake.calls == 2
    judge.close()


def test_timeout_is_fail_soft(tmp_path: Path) -> None:
    fake = FakeLLM(PICK_OK, delay=0.4)
    cfg = {**load_config(tmp_path), "timeout_s": 0.05}
    judge = LlmJudge(cfg, root=tmp_path, complete_fn=fake)
    out = judge.review("PICK", {"setup": "x"}, dedupe_key="slow")
    assert out["status"] == "timeout"
    assert "decision" not in out or out.get("decision") is None
    judge.close()


def test_attach_logs_journal_and_shadow_without_changing_board(tmp_path: Path) -> None:
    _pdiv_tape(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "llm_judge.yaml").write_text(
        "shadow: true\ntrade: true\ntimeout_s: 3\n", encoding="utf-8"
    )
    board = {
        "session_ist_date": DAY,
        "n_open": 1,
        "open_trades": [
            {
                "trade_id": "RR-R01_PDIV_5_ALL_H20-NIFTY-CE-1000",
                "book_id": "R01_PDIV_5_ALL_H20",
                "rule_id": "R01_PDIV_5_ALL_H20",
                "research_rule": True,
                "shadow": True,
                "underlying": "NIFTY",
                "side": "CE",
                "atm_strike": 25000.0,
                "entry": 120.0,
                "last_ltp": 121.0,
                "status": "OPEN_PAPER",
                "phase": "IN_TRADE",
                "sig_min": "10:31",
                "entry_min": "10:32",
                "opened_ist": f"{DAY}T10:31:00+05:30",
                "filled": True,
            }
        ],
        "closed_trades": [],
        "last_step": {
            "underlying": "NIFTY",
            "desk": {"opened_this_tick": True, "product_book": "MIX-DEFAULT-BUY"},
            "picker": {"action": "TICKET", "side": "CE"},
        },
    }
    before = json.dumps(board["open_trades"])

    def complete(*, system: str, user: str) -> dict:
        if "HOLD|TRAIL|EXIT" in system:
            return {"text": EXIT_OK, "tokens_in": 10, "tokens_out": 8}
        return {"text": PICK_OK, "tokens_in": 10, "tokens_out": 8}

    fake_pick = complete
    stats = attach_and_log(
        board,
        root=tmp_path,
        snaps=[_snap("NIFTY", "10:31", 25010, 121, 90)],
        now=TS,
        complete_fn=fake_pick,
        environ={"OPENAI_API_KEY": ""},
    )
    assert stats["trade"] is False
    assert stats["wrote"] >= 1
    assert json.dumps(board["open_trades"]) == before
    assert board["open_trades"][0]["entry"] == 120.0
    shadow = tmp_path / "data" / "shadow" / f"{DAY}.jsonl"
    assert shadow.is_file()
    rows = [json.loads(line) for line in shadow.read_text(encoding="utf-8").splitlines()]
    assert all(r["schema"] == SCHEMA for r in rows)
    assert all(r["prompt_version"] == PROMPT_VERSION for r in rows)
    assert all(r["trade"] is False for r in rows)
    assert any(r["job"] == "PICK" and r.get("decision") == "TAKE" for r in rows)
    assert any(r["job"] == "EXIT" and r.get("action") == "HOLD" for r in rows)
    journal = tmp_path / "data" / "recon" / "decision_journal" / f"{DAY}.jsonl"
    assert journal.is_file()
    jrows = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    assert all(r["actor"] == ACTOR for r in jrows)
    assert {r["stage"] for r in jrows} <= {"llm_pick", "llm_exit"}
    assert any(r["decision"] == "pass" for r in jrows)


def test_score_llm_filtered_vs_plain_vs_random() -> None:
    trades = [
        {"trade_id": "a", "underlying": "NIFTY", "side": "CE", "book_id": "R01_PDIV_5_ALL_H20", "status": "CLOSED", "realized_pnl_inr": 100},
        {"trade_id": "b", "underlying": "NIFTY", "side": "PE", "book_id": "R01_PDIV_5_ALL_H20", "status": "CLOSED", "realized_pnl_inr": -40},
        {"trade_id": "c", "underlying": "NIFTY", "side": "CE", "book_id": "R07_MOM3_TREND", "status": "CLOSED", "realized_pnl_inr": 20},
    ]
    rows = [
        {"schema": SCHEMA, "job": "PICK", "status": "ok", "decision": "TAKE", "trade_id": "a", "underlying": "NIFTY", "side": "CE", "setup": "R01_PDIV_5_ALL_H20"},
        {"schema": SCHEMA, "job": "PICK", "status": "ok", "decision": "SKIP", "trade_id": "b", "underlying": "NIFTY", "side": "PE", "setup": "R01_PDIV_5_ALL_H20"},
        {"schema": SCHEMA, "job": "PICK", "status": "ok", "decision": "TAKE", "trade_id": "c", "underlying": "NIFTY", "side": "CE", "setup": "R07_MOM3_TREND"},
    ]
    out = score(rows, trades, seed=2)
    assert out["plain_pnl"] == 80.0
    assert out["llm_filtered_pnl"] == 120.0
    assert out["llm_skipped_n"] == 1
    assert out["random_skip_n"] == 1
    assert out["promote"] is False


def test_snapshot_marks_missing_as_data_insufficient() -> None:
    market = build_market_snapshot(underlying="NIFTY", bars={}, hhmm="10:31", side="CE")
    assert market["vix"] == "DATA_INSUFFICIENT"
    assert market["futures_basis"] == "DATA_INSUFFICIENT"
    assert market["heavyweights"] == "DATA_INSUFFICIENT"
    assert summarize_candles({})["note"] == "DATA_INSUFFICIENT"


def _active_account_slots(path: Path) -> set[str]:
    import yaml  # type: ignore[import-untyped]

    blob = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        str(row["strategy_id"]).strip()
        for row in (blob.get("accounts") or [])
        if isinstance(row, dict)
        and str(row.get("status") or "").strip().lower() == "active"
        and str(row.get("strategy_id") or "").strip()
    }


def test_paper_slot_ids_match_active_accounts_yaml() -> None:
    path = code_root() / "config" / "v2" / "accounts.yaml"
    expected = _active_account_slots(path)
    assert expected
    assert paper_slot_ids(code_root()) == expected
    src = SRC.read_text(encoding="utf-8")
    for sid in expected:
        assert sid not in src


def test_paper_slot_ids_skip_inactive_accounts(tmp_path: Path) -> None:
    cfg = tmp_path / "config" / "v2"
    cfg.mkdir(parents=True)
    (cfg / "accounts.yaml").write_text(
        "accounts:\n"
        "  - account_id: customer-01\n    status: active\n    strategy_id: LIVE_SLOT\n"
        "  - account_id: customer-02\n    status: disabled\n    strategy_id: PARKED_SLOT\n"
        "  - account_id: founder\n    status: active\n",
        encoding="utf-8",
    )
    assert paper_slot_ids(tmp_path) == frozenset({"LIVE_SLOT"})


def test_collect_pick_events_from_research_rule(tmp_path: Path) -> None:
    _pdiv_tape(tmp_path)
    events = collect_pick_events({"session_ist_date": DAY, "open_trades": [], "closed_trades": []}, root=tmp_path, day=DAY, hhmm="10:00")
    slots = paper_slot_ids(tmp_path)
    setups = {e["setup"] for e in events}
    assert setups & slots
    assert any(e["side"] == "CE" and e["source"] == "paper_slot" and e["setup"] in slots for e in events)


def test_shadow_rule_still_gets_a_pick(tmp_path: Path) -> None:
    events = collect_pick_events(
        {
            "session_ist_date": DAY,
            "open_trades": [
                {
                    "trade_id": "sh-1",
                    "book_id": "R02_MOM_3_0.0005_ALL_H20",
                    "research_rule": True,
                    "shadow": True,
                    "underlying": "NIFTY",
                    "side": "PE",
                    "atm_strike": 25000,
                    "sig_min": "10:00",
                }
            ],
            "closed_trades": [],
        },
        root=tmp_path,
        day=DAY,
        hhmm="10:00",
    )
    assert any(e["setup"] == "R02_MOM_3_0.0005_ALL_H20" and e["source"] == "shadow_rule" for e in events)
    assert "R02_MOM_3_0.0005_ALL_H20" not in paper_slot_ids(tmp_path)


def test_module_stays_off_the_order_path() -> None:
    src = SRC.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        for name in names:
            assert name.split(".")[0] not in FORBIDDEN and name not in FORBIDDEN
    for word in ("place_order", "cancel_order", "modify_order", "ORDER_SUBMITTED", "PaperBroker"):
        assert word not in src


def test_shadow_off_writes_nothing(tmp_path: Path) -> None:
    stats = attach_and_log(
        {"session_ist_date": DAY, "open_trades": [], "closed_trades": []},
        root=tmp_path,
        now=TS,
        complete_fn=FakeLLM(),
        environ={"LLM_JUDGE_SHADOW": "0"},
    )
    assert stats["wrote"] == 0
    assert not (tmp_path / "data" / "shadow" / f"{DAY}.jsonl").is_file()


def test_reset_judge() -> None:
    reset_judge()
    reset_judge()
