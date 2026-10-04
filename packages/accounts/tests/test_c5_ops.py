"""C5-04 founder ops: refuse live, cap 5 customers, keep legacy books isolated."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from accounts.c5 import (
    MAX_CUSTOMER_EXECS,
    assert_c5_mode,
    backup_paper_state,
    plan_launch,
    restore_dry_run,
    start_launch,
    status_launch,
    stop_launch,
)
from accounts.errors import AccountClosed, AccountSafetyError

REPO = Path(__file__).resolve().parents[3]
C5_SH = REPO / "scripts" / "c5_ops.sh"
DESK = REPO / "scripts" / "desk.sh"


def _row(
    account_id: str, *, kind: str = "customer", status: str = "active", broker: str = "paper"
) -> dict[str, object]:
    return {
        "account_id": account_id,
        "kind": kind,
        "broker": broker,
        "status": status,
        "risk_budget_inr": 1000,
    }


def _write_cfg(path: Path, rows: list[dict[str, object]], default: str = "founder") -> Path:
    path.write_text(yaml.safe_dump({"default_account": default, "accounts": rows}), encoding="utf-8")
    return path


def _base_rows(n_customers: int, *, status: str = "active") -> list[dict[str, object]]:
    rows = [
        _row("founder", kind="founder"),
        _row("v2-shadow", kind="founder", broker="shadow"),
    ]
    rows.extend(_row(f"cust-{i:02d}", status=status) for i in range(1, n_customers + 1))
    return rows


def _tree(root: Path, account_ids: list[str]) -> Path:
    (root / "signal").mkdir(parents=True, exist_ok=True)
    for aid in account_ids:
        (root / "exec" / aid).mkdir(parents=True, exist_ok=True)
    return root


def test_live_mode_refused() -> None:
    for mode in ("live", "limited_live", "limited-live", "dhan", "LIVE"):
        with pytest.raises(AccountSafetyError, match="live"):
            assert_c5_mode(mode)
    assert assert_c5_mode("paper") == "paper"


def test_more_than_five_active_customers_refused(tmp_path: Path) -> None:
    cfg = _write_cfg(tmp_path / "accounts.yaml", _base_rows(6))
    root = _tree(tmp_path / "c5", [f"cust-{i:02d}" for i in range(1, 7)])
    with pytest.raises(AccountSafetyError, match="cap is 5"):
        plan_launch(config_path=cfg, state_root=root, mode="paper")
    assert MAX_CUSTOMER_EXECS == 5


def test_five_customers_plus_optional_founder_shadow_ok(tmp_path: Path) -> None:
    cfg = _write_cfg(tmp_path / "accounts.yaml", _base_rows(5))
    ids = [f"cust-{i:02d}" for i in range(1, 6)] + ["founder", "v2-shadow"]
    root = _tree(tmp_path / "c5", ids)
    bare = plan_launch(config_path=cfg, state_root=root, mode="paper")
    assert bare.customer_count == 5
    assert [row.account_id for row in bare.execs] == [f"cust-{i:02d}" for i in range(1, 6)]
    assert bare.signal.account_id is None
    assert bare.as_dict()["shared_signal"] is True
    assert "--mode" in bare.signal.argv and "paper" in bare.signal.argv
    assert "live" not in bare.signal.argv
    extra = plan_launch(
        config_path=cfg,
        state_root=root,
        mode="paper",
        include_founder=True,
        include_shadow=True,
    )
    assert extra.customer_count == 5
    assert {row.account_id for row in extra.execs} == set(ids)


def test_disabled_live_broker_and_missing_state_fail_closed(tmp_path: Path) -> None:
    cfg = _write_cfg(
        tmp_path / "accounts.yaml",
        [
            _row("founder", kind="founder"),
            _row("v2-shadow", kind="founder", broker="shadow"),
            _row("parked", status="disabled"),
            _row("ok-cust"),
        ],
    )
    root = _tree(tmp_path / "c5", ["ok-cust"])
    plan = plan_launch(config_path=cfg, state_root=root)
    assert [row.account_id for row in plan.execs] == ["ok-cust"]
    with pytest.raises(AccountClosed, match="STATE_DIR_MISSING"):
        plan_launch(config_path=cfg, state_root=root, include_founder=True)
    disabled_founder = _write_cfg(
        tmp_path / "disabled-founder.yaml",
        [
            _row("founder", kind="founder", status="disabled"),
            _row("v2-shadow", kind="founder", broker="shadow"),
            _row("ok-cust"),
        ],
    )
    _tree(root, ["ok-cust", "founder"])
    with pytest.raises(AccountClosed, match="ACCOUNT_DISABLED"):
        plan_launch(config_path=disabled_founder, state_root=root, include_founder=True)
    missing = tmp_path / "no-such-c5"
    with pytest.raises(AccountClosed, match="STATE_DIR_MISSING"):
        plan_launch(config_path=cfg, state_root=missing)
    poisoned = _write_cfg(
        tmp_path / "live.yaml",
        [_row("founder", kind="founder"), _row("evil", broker="dhan")],
    )
    with pytest.raises(AccountSafetyError, match="live"):
        plan_launch(config_path=poisoned, state_root=root)


def test_refuses_legacy_book_paths(tmp_path: Path) -> None:
    cfg = _write_cfg(tmp_path / "accounts.yaml", _base_rows(1))
    recon = tmp_path / "data" / "recon" / "paper_watch"
    recon.mkdir(parents=True)
    (recon / "signal").mkdir()
    (recon / "exec" / "cust-01").mkdir(parents=True)
    with pytest.raises(AccountSafetyError, match="legacy book path"):
        plan_launch(config_path=cfg, state_root=recon, repo=tmp_path)
    shadow = tmp_path / "data" / "shadow" / "v2"
    shadow.mkdir(parents=True)
    (shadow / "signal").mkdir()
    (shadow / "exec" / "cust-01").mkdir(parents=True)
    with pytest.raises(AccountSafetyError, match="legacy book path"):
        plan_launch(config_path=cfg, state_root=shadow, repo=tmp_path)


def test_start_status_stop_and_backup_restore(tmp_path: Path) -> None:
    cfg = _write_cfg(tmp_path / "accounts.yaml", _base_rows(1))
    root = _tree(tmp_path / "c5", ["cust-01"])
    (root / "signal" / "marker.txt").write_text("sig\n", encoding="utf-8")
    (root / "exec" / "cust-01" / "ledger.txt").write_text("cust\n", encoding="utf-8")
    plan = plan_launch(config_path=cfg, state_root=root, python=sys.executable)
    dry = start_launch(plan, dry_run=True)
    assert dry["dry_run"] is True and dry["started"] is False
    assert dry["live_broker"] is False
    started = start_launch(plan, dry_run=False, cwd=REPO)
    assert started["started"] is True
    assert (root / "signal" / "signal.ready").is_file()
    assert (root / "exec" / "cust-01" / "exec-cust-01.ready").is_file()
    st = status_launch(root)
    assert st["ok"] is True and st["running"] is True and st["signal_ready"] is True
    assert st["execs"][0]["ready"] is True
    stopped = stop_launch(root)
    assert stopped["stopped"] is True and stopped["ledgers"] == "kept"
    assert (root / "exec" / "cust-01" / "ledger.txt").read_text(encoding="utf-8") == "cust\n"
    assert status_launch(root)["running"] is False
    dest = tmp_path / "c5-paper.tgz"
    backup = backup_paper_state(root, dest)
    assert backup["ok"] is True and dest.is_file()
    dry_restore = restore_dry_run(dest)
    assert dry_restore["dry_run"] is True and dry_restore["would_write"] is False
    assert dry_restore["live_broker"] is False
    assert "exec/cust-01/ledger.txt" in dry_restore["members"]
    assert (root / "exec" / "cust-01" / "ledger.txt").read_text(encoding="utf-8") == "cust\n"


def _run_sh(script: Path, args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(env)
    return subprocess.run([str(script), *args], cwd=REPO, capture_output=True, text=True, check=False, env=merged)


def test_cli_and_shell_refuse_live_and_over_cap(tmp_path: Path) -> None:
    live = subprocess.run(
        [sys.executable, "-m", "accounts", "c5-start", "--mode", "live", "--state-dir", str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert live.returncode == 2
    assert "live" in live.stderr.lower()
    assert "REFUSED" in live.stderr

    cfg = _write_cfg(tmp_path / "accounts.yaml", _base_rows(6))
    root = _tree(tmp_path / "c5", [f"cust-{i:02d}" for i in range(1, 7)])
    over = subprocess.run(
        [
            sys.executable,
            "-m",
            "accounts",
            "c5-start",
            "--config",
            str(cfg),
            "--state-dir",
            str(root),
            "--dry-run",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert over.returncode == 2
    assert "cap is 5" in over.stderr

    env = {"AAD_C5_PY": sys.executable, "AAD_ROOT": str(REPO)}
    sh_live = _run_sh(C5_SH, ["start", "--mode", "live"], env)
    assert sh_live.returncode == 2
    assert "live" in sh_live.stderr.lower()
    sh_cap = _run_sh(
        C5_SH,
        ["start", "--config", str(cfg), "--state-dir", str(root), "--dry-run"],
        env,
    )
    assert sh_cap.returncode == 2
    assert "cap is 5" in sh_cap.stderr

    desk_live = _run_sh(DESK, ["c5-start", "--mode", "LIVE"], env)
    assert desk_live.returncode == 2
    assert "live" in desk_live.stderr.lower()
