"""C5-07: five paper books to five slots. Portal c1-c5. Knobs unset. No live."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from accounts.errors import AccountClosed, AccountSafetyError
from accounts.model import Account
from accounts.registry import PAPER_LAUNCH_CUSTOMER_IDS, AccountRegistry, default_config_path, set_account_status
from accounts.slots import (
    ACCOUNT_TO_SLOT,
    LAUNCH_SLOT_PLAN,
    PAPER_SLOT_LABELS,
    PORTAL_TO_ACCOUNT,
    account_id_for_portal_sub,
)
from accounts.split import bind_exec, run_role_once

REPO = Path(__file__).resolve().parents[3]


def _account(
    account_id: str,
    *,
    slot: str = "",
    portal_sub: str = "",
    strategy_id: str = "",
    basket: str = "",
    status: str = "active",
) -> Account:
    return Account(
        account_id=account_id,
        kind="customer",
        broker="paper",
        status=status,
        risk_budget_inr=1000,
        portal_sub=portal_sub,
        slot=slot,
        strategy_id=strategy_id,
        basket=basket,
    )


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


def test_committed_config_has_five_distinct_unarmed_slots() -> None:
    registry = AccountRegistry.load(default_config_path())
    assert registry.portal_map() == PORTAL_TO_ACCOUNT
    seen_slots: set[str] = set()
    seen_tags: set[str] = set()
    for account_id, portal_sub, slot in LAUNCH_SLOT_PLAN:
        acc = registry.get(account_id)
        assert acc.status == "disabled"
        assert acc.broker == "paper"
        assert acc.portal_sub == portal_sub
        assert acc.slot == slot
        assert acc.journal_tag == f"SLOT-{slot}"
        assert acc.strategy_id == ""
        assert acc.basket == ""
        assert acc.slot_armed is False
        seen_slots.add(acc.slot)
        seen_tags.add(acc.journal_tag)
        assert registry.account_id_for_portal_sub(portal_sub) == account_id
    assert seen_slots == set(PAPER_SLOT_LABELS)
    assert len(seen_tags) == 5
    founder = registry.require_active("founder")
    shadow = registry.require_active("v2-shadow")
    assert founder.slot_armed is False and founder.slot == ""
    assert shadow.slot_armed is False and shadow.slot == ""


def test_portal_c1_through_c5_map_to_customer_books() -> None:
    assert account_id_for_portal_sub("c1") == "customer-01"
    assert account_id_for_portal_sub("C5") == "customer-05"
    with pytest.raises(AccountClosed, match="UNKNOWN_PORTAL_SUB"):
        account_id_for_portal_sub("c6")
    with pytest.raises(AccountClosed, match="UNKNOWN_PORTAL_SUB"):
        account_id_for_portal_sub("customer-01")
    registry = AccountRegistry.load(default_config_path())
    assert registry.account_id_for_portal_sub("c3") == "customer-03"


def test_exec_emits_journal_tag_and_stays_unarmed(tmp_path: Path) -> None:
    rows = [
        _founder_row(),
        {
            "account_id": "customer-01",
            "kind": "customer",
            "broker": "paper",
            "status": "active",
            "risk_budget_inr": 1000,
            "portal_sub": "c1",
            "slot": "CONTROL",
            "journal_tag": "SLOT-CONTROL",
        },
    ]
    cfg = _write_cfg(tmp_path / "accounts.yaml", rows)
    body = run_role_once(
        role="exec",
        account_id="customer-01",
        state_dir=tmp_path / "ex",
        config_path=cfg,
        mode="paper",
    )
    assert body["ok"] is True
    assert body["account_id"] == "customer-01"
    assert body["portal_sub"] == "c1"
    assert body["slot"] == "CONTROL"
    assert body["journal_tag"] == "SLOT-CONTROL"
    assert body["strategy_id"] is None
    assert body["basket"] is None
    assert body["slot_armed"] is False
    assert body["live_broker"] is False
    acc = AccountRegistry.load(cfg).require_active("customer-01")
    bind, book = bind_exec(acc)
    assert bind.slot_armed is False
    stamped = book.apply_decision({"signal_id": "sg_slot_nifty_20261006_1001_0", "account_id": None})
    assert stamped["journal_tag"] == "SLOT-CONTROL"
    assert stamped["slot"] == "CONTROL"
    assert stamped["slot_armed"] is False
    assert stamped["strategy_id"] is None


def test_strategy_id_or_basket_arms_slot_without_inventing_edge(tmp_path: Path) -> None:
    rows = [
        _founder_row(),
        {
            "account_id": "customer-02",
            "kind": "customer",
            "broker": "paper",
            "status": "active",
            "risk_budget_inr": 1000,
            "portal_sub": "c2",
            "slot": "CANDLE_GEOM",
            "strategy_id": "R8-E1-COIL-SIDE",
        },
    ]
    cfg = _write_cfg(tmp_path / "armed.yaml", rows)
    acc = AccountRegistry.load(cfg).require_active("customer-02")
    assert acc.slot_armed is True
    assert acc.strategy_id == "R8-E1-COIL-SIDE"
    assert acc.journal_tag == "SLOT-CANDLE_GEOM"
    body = run_role_once(role="exec", account_id="customer-02", config_path=cfg, mode="paper")
    assert body["slot_armed"] is True
    assert body["strategy_id"] == "R8-E1-COIL-SIDE"


def test_duplicate_slot_and_forbidden_ids_fail_closed(tmp_path: Path) -> None:
    dup = _write_cfg(
        tmp_path / "dup.yaml",
        [
            _founder_row(),
            {
                "account_id": "customer-01",
                "kind": "customer",
                "broker": "paper",
                "status": "disabled",
                "risk_budget_inr": 1000,
                "slot": "CONTROL",
            },
            {
                "account_id": "customer-02",
                "kind": "customer",
                "broker": "paper",
                "status": "disabled",
                "risk_budget_inr": 1000,
                "slot": "CONTROL",
            },
        ],
    )
    with pytest.raises(AccountSafetyError, match="duplicate slot"):
        AccountRegistry.load(dup)
    with pytest.raises(AccountSafetyError, match="dry-run only"):
        _account("customer-01", strategy_id="TEST-CROSS")
    with pytest.raises(AccountSafetyError, match="STRAT-015"):
        _account("customer-01", strategy_id="STRAT-015")
    with pytest.raises(AccountSafetyError, match="not one of"):
        _account("customer-01", slot="FAKE_EDGE")
    with pytest.raises(AccountSafetyError, match="not paper/shadow"):
        _account("customer-01", basket="dry_run")
    with pytest.raises(AccountSafetyError, match="portal_sub"):
        _account("customer-01", portal_sub="c6")


def test_enable_preserves_slot_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AAD_CUSTOMERS", raising=False)
    rows = [_founder_row()]
    for account_id, portal_sub, slot in LAUNCH_SLOT_PLAN:
        rows.append(
            {
                "account_id": account_id,
                "kind": "customer",
                "broker": "paper",
                "status": "disabled",
                "risk_budget_inr": 1000,
                "portal_sub": portal_sub,
                "slot": slot,
                "journal_tag": f"SLOT-{slot}",
            }
        )
    cfg = _write_cfg(tmp_path / "accounts.yaml", rows)
    enabled = set_account_status("customer-04", "active", path=cfg, mode="paper")
    assert enabled.status == "active"
    assert enabled.slot == "SKLEARN"
    assert enabled.journal_tag == "SLOT-SKLEARN"
    assert enabled.slot_armed is False
    reloaded = AccountRegistry.load(cfg).require_active("customer-04")
    assert reloaded.portal_sub == "c4"
    assert reloaded.strategy_id == ""


def test_c5_plan_stamps_journal_tag_on_enabled_exec(tmp_path: Path) -> None:
    from accounts.c5 import plan_launch

    rows = [
        _founder_row(),
        {
            "account_id": "v2-shadow",
            "kind": "founder",
            "broker": "shadow",
            "status": "active",
            "risk_budget_inr": 30000,
        },
        {
            "account_id": "customer-01",
            "kind": "customer",
            "broker": "paper",
            "status": "active",
            "risk_budget_inr": 1000,
            "portal_sub": "c1",
            "slot": "CONTROL",
            "journal_tag": "SLOT-CONTROL",
        },
    ]
    cfg = _write_cfg(tmp_path / "accounts.yaml", rows)
    root = tmp_path / "c5"
    (root / "signal").mkdir(parents=True)
    (root / "exec" / "customer-01").mkdir(parents=True)
    plan = plan_launch(config_path=cfg, state_root=root, mode="paper")
    assert plan.customer_count == 1
    exec_row = plan.execs[0]
    assert exec_row.account_id == "customer-01"
    assert exec_row.slot == "CONTROL"
    assert exec_row.journal_tag == "SLOT-CONTROL"
    assert exec_row.slot_armed is False
    assert exec_row.as_dict()["portal_sub"] == "c1"


def test_cli_list_includes_portal_map_and_unarmed_slots() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "accounts", "list"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["portal_map"] == PORTAL_TO_ACCOUNT
    by_id = {row["account_id"]: row for row in body["accounts"]}
    for account_id in PAPER_LAUNCH_CUSTOMER_IDS:
        row = by_id[account_id]
        assert row["status"] == "disabled"
        assert row["slot"] == ACCOUNT_TO_SLOT[account_id]
        assert row["journal_tag"] == f"SLOT-{ACCOUNT_TO_SLOT[account_id]}"
        assert row["slot_armed"] is False
        assert row["strategy_id"] is None
        assert row["basket"] is None
