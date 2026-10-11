"""Async LLM trade explainer: log-only, no veto, zero wait on the fill path."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from desk_ml.llm_explain import collect_paper_slot_trades, reset_explain_pool, schedule_explains
from desk_ml.llm_judge import (
    _board_fingerprint,
    attach_and_log,
    parse_explain,
    plain_market_type,
    reset_judge,
)

IST = timezone(timedelta(hours=5, minutes=30))
DAY = "2026-10-10"
TS = datetime(2026, 10, 10, 10, 31, tzinfo=IST)
EXPLAIN_OK = '{"explanation":"Call premium is following a rising index. The open range is holding.","market_type":"trend up"}'


class FakeLLM:
    def __init__(self, text: str = EXPLAIN_OK, delay: float = 0.0, exc: Exception | None = None) -> None:
        self.text = text
        self.delay = delay
        self.exc = exc
        self.calls = 0

    def __call__(self, *, system: str, user: str) -> dict:
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.exc:
            raise self.exc
        return {"text": self.text, "tokens_in": 40, "tokens_out": 30}


def _accounts(root: Path, sid: str = "R01_PDIV_5_ALL_H20") -> None:
    path = root / "config" / "v2"
    path.mkdir(parents=True)
    path.joinpath("accounts.yaml").write_text(
        "accounts:\n"
        f"  - account_id: customer-01\n    status: active\n    strategy_id: {sid}\n",
        encoding="utf-8",
    )


def _trade(**kw) -> dict:
    row = {
        "trade_id": "t-n",
        "book_id": "R01_PDIV_5_ALL_H20",
        "underlying": "NIFTY",
        "side": "CE",
        "atm_strike": 25000,
        "entry": 120.0,
        "last_ltp": 121.0,
        "status": "OPEN_PAPER",
        "opened_ist": f"{DAY}T10:31:00+05:30",
        "filled": True,
    }
    row.update(kw)
    return row


def test_parse_explain_is_strict_and_plain() -> None:
    out = parse_explain(EXPLAIN_OK)
    assert out["market_type"] == "trend up"
    assert "Call premium" in out["explanation"]
    assert out["reason"] == out["explanation"]
    assert parse_explain('{"explanation":"Chop all morning.","market_type":"CHOP"}')["market_type"] == "chop"
    with pytest.raises(ValueError):
        parse_explain('{"explanation":"x","market_type":"trend up","decision":"SKIP"}')
    with pytest.raises(ValueError):
        parse_explain('{"explanation":"One. Two. Three. Four.","market_type":"trend up"}')
    with pytest.raises(ValueError):
        parse_explain('{"explanation":"ok","market_type":"MOON"}')


def test_plain_market_type_hides_codes() -> None:
    assert plain_market_type("TREND_UP") == "trend up"
    assert plain_market_type("high-VIX") == "high-VIX"
    assert plain_market_type("unknown-regime") is None


def test_missing_key_skips_without_blocking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_KEY", raising=False)
    _accounts(tmp_path)
    board = {"session_ist_date": DAY, "open_trades": [_trade()], "closed_trades": []}
    before = _board_fingerprint(board)
    stats = schedule_explains(board, root=tmp_path, now=TS, environ={}, wait=True)
    assert stats["trade"] is False
    assert stats["veto"] is False
    assert stats["scheduled"] == 1
    assert _board_fingerprint(board) == before
    reset_explain_pool()


def test_schedule_adds_zero_wait_on_caller(tmp_path: Path) -> None:
    _accounts(tmp_path)
    board = {"session_ist_date": DAY, "open_trades": [_trade()], "closed_trades": []}
    fake = FakeLLM(delay=0.35)
    t0 = time.perf_counter()
    stats = schedule_explains(board, root=tmp_path, now=TS, complete_fn=fake, wait=False)
    elapsed = time.perf_counter() - t0
    assert stats["scheduled"] == 1
    assert elapsed < 0.2
    for fut in stats["futures"]:
        fut.result(timeout=2)
    journal = tmp_path / "data" / "recon" / "decision_journal" / f"{DAY}.jsonl"
    assert journal.is_file()
    rows = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    assert any(r["stage"] == "llm_explain" and r["actor"] == "LLM judge" for r in rows)
    assert any("rising index" in r["reason"] for r in rows)
    assert any((r.get("inputs") or {}).get("market_type") == "trend up" for r in rows)
    assert all("TREND_UP" not in json.dumps(r) for r in rows)
    reset_explain_pool()


def test_explainer_never_vetoes_or_changes_fills(tmp_path: Path) -> None:
    _accounts(tmp_path)
    board = {"session_ist_date": DAY, "n_open": 1, "open_trades": [_trade()], "closed_trades": []}
    before = _board_fingerprint(board)
    snapshot = json.dumps(board["open_trades"])
    fake = FakeLLM(text='{"decision":"SKIP","confidence":0.9,"reason":"veto"}')
    stats = schedule_explains(board, root=tmp_path, now=TS, complete_fn=fake, wait=True)
    assert stats["trade"] is False
    assert stats["veto"] is False
    assert _board_fingerprint(board) == before
    assert json.dumps(board["open_trades"]) == snapshot
    assert board["open_trades"][0]["entry"] == 120.0
    assert board["open_trades"][0].get("status") == "OPEN_PAPER"
    reset_explain_pool()


def test_shadow_rule_is_not_explained(tmp_path: Path) -> None:
    _accounts(tmp_path)
    board = {
        "session_ist_date": DAY,
        "open_trades": [_trade(book_id="R02_MOM_3_0.0005_ALL_H20", trade_id="shadow-1", research_rule=True, shadow=True)],
        "closed_trades": [],
    }
    assert collect_paper_slot_trades(board, root=tmp_path) == []
    stats = schedule_explains(board, root=tmp_path, now=TS, complete_fn=FakeLLM(), wait=True)
    assert stats["scheduled"] == 0
    reset_explain_pool()


def test_attach_and_log_still_no_veto_with_explainer(tmp_path: Path) -> None:
    _accounts(tmp_path)
    (tmp_path / "config" / "llm_judge.yaml").write_text("shadow: true\ntrade: true\n", encoding="utf-8")
    board = {
        "session_ist_date": DAY,
        "n_open": 1,
        "open_trades": [_trade()],
        "closed_trades": [],
        "last_step": {"underlying": "NIFTY", "desk": {"opened_this_tick": True, "product_book": "R01_PDIV_5_ALL_H20"}},
    }
    before = _board_fingerprint(board)

    def complete(*, system: str, user: str) -> dict:
        if "explanation" in system:
            return {"text": EXPLAIN_OK, "tokens_in": 10, "tokens_out": 8}
        if "HOLD|TRAIL|EXIT" in system:
            return {"text": '{"action":"HOLD","reason":"still alive"}', "tokens_in": 10, "tokens_out": 8}
        return {"text": '{"decision":"SKIP","confidence":0.8,"reason":"skip it"}', "tokens_in": 10, "tokens_out": 8}

    stats = attach_and_log(board, root=tmp_path, now=TS, complete_fn=complete, environ={"OPENAI_API_KEY": "x"})
    assert stats["trade"] is False
    assert stats.get("veto") is False
    assert _board_fingerprint(board) == before
    assert board["open_trades"][0]["entry"] == 120.0
    reset_explain_pool()
    reset_judge()
