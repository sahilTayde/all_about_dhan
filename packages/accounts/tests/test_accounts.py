"""V2-22 / C5-01: fail-closed paper/shadow accounts and 5-customer isolation."""

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
from accounts.registry import (
    MAX_CUSTOMER_ACCOUNTS,
    PAPER_LAUNCH_CUSTOMER_IDS,
    AccountRegistry,
    default_config_path,
    set_account_status,
)
from accounts.safety import assert_no_live_modules, assert_paper_only, refuse_broker_name
from accounts.split import EXEC_HANDLERS, SIGNAL_HANDLERS, bind_exec, bind_signal, run_role_once

REPO = Path(__file__).resolve().parents[3]


def _account(account_id: str, budget: int = 10_000) -> Account:
    return Account(account_id=account_id, kind="customer", broker="paper", status="active", risk_budget_inr=budget)


def _write_cfg(path: Path, rows: list[dict[str, object]], default: str = "founder") -> Path:
    path.write_text(yaml.safe_dump({"default_account": default, "accounts": rows}), encoding="utf-8")
    return path


def _founder_row() -> dict[str, object]:
    return {
        "account_id": "founder",
        "kind": "founder",
        "broker": "paper",
        "status": "active",
        "risk_budget_inr": 30000,
    }


def _customer_row(account_id: str, status: str = "disabled") -> dict[str, object]:
    return {
        "account_id": account_id,
        "kind": "customer",
        "broker": "paper",
        "status": status,
        "risk_budget_inr": 1000,
    }


def test_committed_config_is_paper_only() -> None:
    registry = AccountRegistry.load(default_config_path())
    assert registry.default_account == "founder"
    assert set(registry.ids()) == {"founder", "v2-shadow", *PAPER_LAUNCH_CUSTOMER_IDS}
    assert registry.customer_ids() == PAPER_LAUNCH_CUSTOMER_IDS
    founder = registry.require_active("founder")
    shadow = registry.require_active("v2-shadow")
    assert founder.kind == "founder" and founder.broker == "paper"
    assert shadow.broker == "shadow" and shadow.kind == "founder"
    assert all(acc.broker in {"paper", "shadow"} for acc in registry.all())
    for aid in PAPER_LAUNCH_CUSTOMER_IDS:
        acc = registry.get(aid)
        assert acc.kind == "customer"
        assert acc.broker == "paper"
        assert acc.status == "disabled"
        assert acc.risk_budget_inr == 1000
        with pytest.raises(AccountClosed, match="ACCOUNT_DISABLED"):
            registry.require_active(aid)
    with pytest.raises(AccountClosed, match="UNKNOWN_ACCOUNT"):
        registry.get("customer-06")


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
            _founder_row(),
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
    with pytest.raises(AccountClosed, match="UNKNOWN_ACCOUNT"):
        registry.get("customer-06")
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
            _founder_row(),
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


def test_five_customer_books_cannot_cross_read_positions_or_size() -> None:
    instrument = "NSE_FNO:NIFTY:2026-10-06:24500:CE"
    books = {aid: IsolatedBook(account=_account(aid, 5_000)) for aid in PAPER_LAUNCH_CUSTOMER_IDS}
    assert len(books) == MAX_CUSTOMER_ACCOUNTS
    for aid, book in books.items():
        book.apply_fill(aid, instrument, 1, 100)
        assert book.partition == f"ledger:{aid}"
        assert book.stream == f"pos:{aid}"
        assert list(book.positions) == [position_key(aid, instrument)]
    for owner, book in books.items():
        rows = book.read(owner)
        assert len(rows) == 1 and rows[0]["account_id"] == owner
        assert book.size_lots(owner, 100) == 49
        for other in PAPER_LAUNCH_CUSTOMER_IDS:
            if other == owner:
                continue
            with pytest.raises(AccountIsolationError):
                book.read(other)
            with pytest.raises(AccountIsolationError):
                book.apply_fill(other, instrument, 1, 100)
            with pytest.raises(AccountIsolationError):
                book.size_lots(other, 100)
            assert position_key(owner, instrument) not in books[other].positions
            assert ledger_partition(owner) != ledger_partition(other)


def test_customer_cap_refuses_sixth(tmp_path: Path) -> None:
    rows = [_founder_row(), *[_customer_row(aid) for aid in PAPER_LAUNCH_CUSTOMER_IDS], _customer_row("customer-06")]
    cfg = _write_cfg(tmp_path / "six.yaml", rows)
    with pytest.raises(AccountSafetyError, match="customer cap is 5"):
        AccountRegistry.load(cfg)


def test_enable_disable_and_live_refuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AAD_CUSTOMERS", raising=False)
    rows = [_founder_row(), *[_customer_row(aid) for aid in PAPER_LAUNCH_CUSTOMER_IDS]]
    cfg = _write_cfg(tmp_path / "accounts.yaml", rows)
    with pytest.raises(AccountClosed, match="ACCOUNT_DISABLED"):
        AccountRegistry.load(cfg).require_active("customer-01")
    enabled = set_account_status("customer-01", "active", path=cfg, mode="paper")
    assert enabled.status == "active" and enabled.broker == "paper"
    registry = AccountRegistry.load(cfg)
    assert registry.require_active("customer-01").status == "active"
    disabled = set_account_status("customer-01", "disabled", path=cfg, mode="paper")
    assert disabled.status == "disabled"
    with pytest.raises(AccountClosed, match="ACCOUNT_DISABLED"):
        AccountRegistry.load(cfg).require_active("customer-01")
    with pytest.raises(AccountSafetyError, match="live"):
        set_account_status("customer-01", "active", path=cfg, mode="live")
    with pytest.raises(AccountClosed, match="UNKNOWN_ACCOUNT"):
        set_account_status("customer-06", "active", path=cfg, mode="paper")
    with pytest.raises(AccountClosed, match="ACCOUNT_ID_REQUIRED"):
        set_account_status("", "active", path=cfg, mode="paper")


def test_example_overlay_duplicates_committed_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    example = REPO / "config" / "v2" / "accounts" / "customers.example.yaml"
    monkeypatch.setenv("AAD_CUSTOMERS", str(example))
    with pytest.raises(AccountSafetyError, match="duplicate account_id"):
        AccountRegistry.load(default_config_path())


def test_optional_overlay_merges_and_duplicate_or_cap_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = _write_cfg(tmp_path / "accounts.yaml", [_founder_row()])
    overlay = _write_cfg(
        tmp_path / "customers.yaml",
        [_customer_row(aid) for aid in PAPER_LAUNCH_CUSTOMER_IDS],
        default="founder",
    )
    monkeypatch.setenv("AAD_CUSTOMERS", str(overlay))
    registry = AccountRegistry.load(base)
    assert registry.customer_ids() == PAPER_LAUNCH_CUSTOMER_IDS
    enabled = set_account_status("customer-02", "active", path=base, mode="paper")
    assert enabled.status == "active"
    reloaded = AccountRegistry.load(base)
    assert reloaded.require_active("customer-02").status == "active"
    dup = _write_cfg(tmp_path / "dup.yaml", [_founder_row(), _customer_row("customer-01")])
    monkeypatch.setenv("AAD_CUSTOMERS", str(overlay))
    with pytest.raises(AccountSafetyError, match="duplicate account_id"):
        AccountRegistry.load(dup)
    sixth = _write_cfg(
        tmp_path / "six-overlay.yaml",
        [_customer_row(aid) for aid in PAPER_LAUNCH_CUSTOMER_IDS] + [_customer_row("extra-cust")],
    )
    monkeypatch.setenv("AAD_CUSTOMERS", str(sixth))
    with pytest.raises(AccountSafetyError, match="customer cap is 5"):
        AccountRegistry.load(base)


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
    with pytest.raises(AccountClosed, match="ACCOUNT_DISABLED"):
        run_role_once(role="exec", account_id="customer-01", config_path=default_config_path(), mode="paper")


def test_cli_list_enable_disable_and_live_mode(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "accounts", "list"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["ok"] is True and body["live_broker"] is False
    assert body["customer_cap"] == 5
    assert {row["account_id"] for row in body["accounts"]} == {"founder", "v2-shadow", *PAPER_LAUNCH_CUSTOMER_IDS}
    assert body["customer_ids"] == list(PAPER_LAUNCH_CUSTOMER_IDS)
    live = subprocess.run(
        [
            sys.executable,
            "-m",
            "accounts",
            "enable",
            "--account",
            "customer-01",
            "--mode",
            "live",
            "--config",
            str(tmp_path / "unused.yaml"),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert live.returncode == 2
    assert "live" in live.stderr.lower()
    cfg = _write_cfg(
        tmp_path / "cli.yaml",
        [_founder_row(), *[_customer_row(aid) for aid in PAPER_LAUNCH_CUSTOMER_IDS]],
    )
    enable = subprocess.run(
        [sys.executable, "-m", "accounts", "enable", "--account", "customer-03", "--config", str(cfg)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert enable.returncode == 0, enable.stderr
    assert json.loads(enable.stdout)["status"] == "active"
    disable = subprocess.run(
        [sys.executable, "-m", "accounts", "disable", "--account", "customer-03", "--config", str(cfg)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert disable.returncode == 0, disable.stderr
    assert json.loads(disable.stdout)["status"] == "disabled"
    unknown = subprocess.run(
        [sys.executable, "-m", "accounts", "enable", "--account", "customer-06", "--config", str(cfg)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert unknown.returncode == 2
    assert "UNKNOWN_ACCOUNT" in unknown.stderr
    dhan = subprocess.run(
        [sys.executable, "-m", "accounts", "list", "--mode", "dhan"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert dhan.returncode == 2
    assert "live" in dhan.stderr.lower()
