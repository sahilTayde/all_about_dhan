"""V2-22: fail-closed paper/shadow accounts and A/B isolation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from accounts.errors import AccountClosed, AccountIsolationError, AccountSafetyError
from accounts.isolation import IsolatedBook, ledger_partition, position_key, position_stream
from accounts.model import Account
from accounts.registry import AccountRegistry, default_config_path
from accounts.safety import assert_no_live_modules, assert_paper_only, refuse_broker_name
from accounts.split import EXEC_HANDLERS, SIGNAL_HANDLERS, bind_exec, bind_signal, run_role_once

REPO = Path(__file__).resolve().parents[3]


def _account(account_id: str, budget: int = 10_000) -> Account:
    return Account(account_id=account_id, kind="customer", broker="paper", status="active", risk_budget_inr=budget)


def _write_cfg(path: Path, rows: list[dict[str, object]], default: str = "founder") -> Path:
    path.write_text(yaml.safe_dump({"default_account": default, "accounts": rows}), encoding="utf-8")
    return path


def test_committed_config_is_paper_only() -> None:
    registry = AccountRegistry.load(default_config_path())
    assert registry.default_account == "founder"
    assert set(registry.ids()) == {"founder", "v2-shadow"}
    founder = registry.require_active("founder")
    shadow = registry.require_active("v2-shadow")
    assert founder.kind == "founder" and founder.broker == "paper"
    assert shadow.broker == "shadow" and shadow.kind == "founder"
    assert all(acc.broker in {"paper", "shadow"} for acc in registry.all())


def test_live_mode_and_broker_are_refused() -> None:
    for mode in ("live", "limited_live", "dhan", "LIVE"):
        with pytest.raises(AccountSafetyError, match="live"):
            assert_paper_only(mode)
    assert assert_paper_only("paper") == "paper"
    with pytest.raises(AccountSafetyError, match="live"):
        refuse_broker_name("dhan")
    with pytest.raises(AccountSafetyError, match="live"):
        Account(account_id="evil", kind="customer", broker="dhan", status="active")
    assert_no_live_modules()


def test_unknown_disabled_and_missing_config_fail_closed(tmp_path: Path) -> None:
    cfg = _write_cfg(
        tmp_path / "accounts.yaml",
        [
            {
                "account_id": "founder",
                "kind": "founder",
                "broker": "paper",
                "status": "active",
                "risk_budget_inr": 30000,
            },
            {
                "account_id": "parked",
                "kind": "customer",
                "broker": "paper",
                "status": "disabled",
                "risk_budget_inr": 1000,
            },
        ],
    )
    registry = AccountRegistry.load(cfg)
    with pytest.raises(AccountClosed, match="UNKNOWN_ACCOUNT"):
        registry.get("nope")
    with pytest.raises(AccountClosed, match="ACCOUNT_DISABLED"):
        registry.require_active("parked")
    with pytest.raises(AccountClosed, match="ACCOUNT_ID_REQUIRED"):
        registry.get("")
    with pytest.raises(AccountClosed, match="ACCOUNTS_CONFIG_MISSING"):
        AccountRegistry.load(tmp_path / "missing.yaml")


def test_poisoned_live_row_refuses_whole_registry(tmp_path: Path) -> None:
    cfg = _write_cfg(
        tmp_path / "bad.yaml",
        [
            {
                "account_id": "founder",
                "kind": "founder",
                "broker": "paper",
                "status": "active",
                "risk_budget_inr": 30000,
            },
            {
                "account_id": "live-cust",
                "kind": "customer",
                "broker": "dhan",
                "status": "active",
                "risk_budget_inr": 1000,
            },
        ],
    )
    with pytest.raises(AccountSafetyError, match="live"):
        AccountRegistry.load(cfg)


def test_a_cannot_read_affect_or_be_sized_by_b() -> None:
    book_a = IsolatedBook(account=_account("acct-a", 10_000))
    book_b = IsolatedBook(account=_account("acct-b", 10_000))
    book_a.apply_fill("acct-a", "NSE_FNO:NIFTY:2026-10-06:24500:CE", 1, 2_000)
    assert book_a.remaining_budget_inr == 8_000
    assert book_b.remaining_budget_inr == 10_000
    assert book_b.read("acct-b") == []
    assert position_key("acct-a", "x") != position_key("acct-b", "x")
    assert ledger_partition("acct-a") != ledger_partition("acct-b")
    assert position_stream("acct-a") == "pos:acct-a"
    with pytest.raises(AccountIsolationError):
        book_a.read("acct-b")
    with pytest.raises(AccountIsolationError):
        book_a.apply_fill("acct-b", "NSE_FNO:NIFTY:2026-10-06:24500:CE", 1, 100)
    with pytest.raises(AccountIsolationError):
        book_a.size_lots("acct-b", 1_000)
    assert book_a.size_lots("acct-a", 1_000) == 8
    assert book_b.size_lots("acct-b", 1_000) == 10
    with pytest.raises(AccountClosed, match="BUDGET"):
        book_a.apply_fill("acct-a", "NSE_FNO:NIFTY:2026-10-06:24500:CE", 1, 9_000)


def test_shared_signal_stamps_distinct_order_ids() -> None:
    book_a = IsolatedBook(account=_account("acct-a"))
    book_b = IsolatedBook(account=_account("acct-b"))
    decision = {"signal_id": "sg_r8-e1-v1.0.0_bfe5cd_nifty_20261006_1001_0", "account_id": None}
    row_a = book_a.apply_decision(decision)
    row_b = book_b.apply_decision(decision)
    assert row_a["client_order_id"] != row_b["client_order_id"]
    assert row_a["account_id"] == "acct-a" and row_b["account_id"] == "acct-b"
    assert row_a["client_order_id"].startswith("aad") and len(row_a["client_order_id"]) == 27
    with pytest.raises(AccountIsolationError):
        book_a.apply_decision({"signal_id": "sg_x", "account_id": "acct-b"})


def test_signal_exec_handlers_are_disjoint() -> None:
    assert SIGNAL_HANDLERS.isdisjoint(EXEC_HANDLERS)
    signal = bind_signal()
    assert signal.account_id is None
    assert signal.produces == frozenset({"boss:decisions"})
    acc = _account("acct-a")
    exec_bind, book = bind_exec(acc)
    assert exec_bind.account_id == "acct-a"
    assert exec_bind.handlers == EXEC_HANDLERS
    assert exec_bind.produces == frozenset({"oms:acct-a", "pos:acct-a"})
    assert book.partition == "ledger:acct-a"
    assert "risk" not in signal.handlers
    assert "boss" not in exec_bind.handlers


def test_run_role_once_writes_ready(tmp_path: Path) -> None:
    signal = run_role_once(role="signal", state_dir=tmp_path / "sig", mode="paper")
    assert signal["ok"] is True and signal["role"] == "signal" and signal["live_broker"] is False
    assert (tmp_path / "sig" / "signal.ready").is_file()
    exec_body = run_role_once(
        role="exec",
        account_id="founder",
        state_dir=tmp_path / "ex",
        config_path=default_config_path(),
        mode="paper",
    )
    assert exec_body["ok"] is True and exec_body["account_id"] == "founder"
    assert exec_body["partition"] == "ledger:founder"
    assert (tmp_path / "ex" / "exec-founder.ready").is_file()
    with pytest.raises(AccountSafetyError, match="live"):
        run_role_once(role="exec", account_id="founder", mode="live")


def test_cli_list_and_live_mode(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "accounts", "list"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    body = json.loads(proc.stdout)
    assert body["ok"] is True and body["live_broker"] is False
    assert {row["account_id"] for row in body["accounts"]} == {"founder", "v2-shadow"}
    live = subprocess.run(
        [
            sys.executable,
            "-m",
            "accounts",
            "exec",
            "--account",
            "founder",
            "--mode",
            "live",
            "--state-dir",
            str(tmp_path),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert live.returncode == 2
    assert "live" in live.stderr.lower()
