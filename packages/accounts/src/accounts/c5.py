"""C5-04 founder ops: one shared signal + <=5 customer execs. Paper/shadow only."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from accounts.errors import AccountClosed, AccountSafetyError
from accounts.model import Account
from accounts.registry import MAX_CUSTOMER_ACCOUNTS, AccountRegistry, default_config_path
from accounts.safety import assert_active, assert_paper_only, refuse_broker_name

MAX_CUSTOMER_EXECS = MAX_CUSTOMER_ACCOUNTS
OPS_NAME = "ops.json"
STOPPED_NAME = "STOPPED.flag"
MANIFEST_NAME = "MANIFEST.json"
_LEGACY_DIR_NAMES = frozenset({"paper_watch", "DUAL-TAPE"})
_LIVE_MODES = frozenset({"live", "limited_live", "limited-live", "dhan"})
_C5_MODES = frozenset({"paper", "shadow", "replay"})
_REPO_ROOT = Path(__file__).resolve().parents[4]


def repo_root() -> Path:
    return _REPO_ROOT


def default_state_root() -> Path:
    env = os.environ.get("AAD_C5_STATE")
    if env:
        return Path(env)
    return repo_root() / "data" / "c5"


def assert_c5_mode(mode: str) -> str:
    cleaned = (mode or "").strip().lower()
    if cleaned in _LIVE_MODES:
        raise AccountSafetyError(f"V2 c5 fail-closed: mode {mode!r} is live and cannot start")
    if cleaned not in _C5_MODES:
        raise AccountSafetyError(f"V2 c5 fail-closed: mode {mode!r} is not paper/shadow/replay")
    return assert_paper_only(cleaned)


def _runtime_mode(mode: str) -> str:
    cleaned = assert_c5_mode(mode)
    return "replay" if cleaned == "replay" else "paper"


def assert_allowed_state_path(path: Path, *, repo: Path | None = None) -> Path:
    """Refuse legacy dual-tape / shadow book paths. C5 never steals those dirs."""
    resolved = path.expanduser().resolve()
    root = (repo or repo_root()).resolve()
    text = resolved.as_posix()
    forbidden_prefixes = (
        (root / "data" / "recon").as_posix(),
        (root / "data" / "shadow").as_posix(),
    )
    for prefix in forbidden_prefixes:
        if text == prefix or text.startswith(prefix + "/"):
            raise AccountSafetyError(f"V2 c5 fail-closed: refuses legacy book path {path}")
    if any(part in _LEGACY_DIR_NAMES for part in resolved.parts):
        raise AccountSafetyError(f"V2 c5 fail-closed: refuses legacy book path {path}")
    return resolved


def require_state_dir(path: Path, *, repo: Path | None = None) -> Path:
    resolved = assert_allowed_state_path(path, repo=repo)
    if not resolved.is_dir():
        raise AccountClosed(f"STATE_DIR_MISSING:{resolved}")
    return resolved


def signal_state_dir(state_root: Path) -> Path:
    return state_root / "signal"


def exec_state_dir(state_root: Path, account_id: str) -> Path:
    return state_root / "exec" / account_id


def _argv(python: str, role: str, state_dir: Path, mode: str, account_id: str | None) -> tuple[str, ...]:
    runtime_mode = _runtime_mode(mode)
    if role == "signal":
        return (
            python,
            "-m",
            "runtime",
            "signal",
            "--once",
            "--state-dir",
            str(state_dir),
            "--mode",
            runtime_mode,
        )
    if role != "exec" or not account_id:
        raise AccountClosed(f"UNKNOWN_ROLE:{role}")
    return (
        python,
        "-m",
        "runtime",
        "exec",
        "--account",
        account_id,
        "--once",
        "--state-dir",
        str(state_dir),
        "--mode",
        runtime_mode,
    )


@dataclass(frozen=True)
class C5Process:
    role: Literal["signal", "exec"]
    account_id: str | None
    kind: str | None
    broker: str | None
    state_dir: Path
    argv: tuple[str, ...]
    portal_sub: str | None = None
    slot: str | None = None
    journal_tag: str | None = None
    strategy_id: str | None = None
    basket: str | None = None
    slot_armed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "account_id": self.account_id,
            "kind": self.kind,
            "broker": self.broker,
            "state_dir": str(self.state_dir),
            "argv": list(self.argv),
            "portal_sub": self.portal_sub,
            "slot": self.slot,
            "journal_tag": self.journal_tag,
            "strategy_id": self.strategy_id,
            "basket": self.basket,
            "slot_armed": self.slot_armed,
            "live_broker": False,
        }


@dataclass(frozen=True)
class C5Plan:
    mode: str
    state_root: Path
    signal: C5Process
    execs: tuple[C5Process, ...]
    customer_count: int
    include_founder: bool
    include_shadow: bool
    config_path: Path

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": self.mode,
            "state_root": str(self.state_root),
            "config_path": str(self.config_path),
            "signal": self.signal.as_dict(),
            "execs": [row.as_dict() for row in self.execs],
            "customer_count": self.customer_count,
            "include_founder": self.include_founder,
            "include_shadow": self.include_shadow,
            "live_broker": False,
            "orders": "PAPER",
            "max_customer_execs": MAX_CUSTOMER_EXECS,
            "shared_signal": True,
        }


def _bind_exec_proc(account: Account, state_root: Path, mode: str, python: str, repo: Path) -> C5Process:
    refuse_broker_name(account.broker)
    assert_active(account)
    state = require_state_dir(exec_state_dir(state_root, account.account_id), repo=repo)
    return C5Process(
        role="exec",
        account_id=account.account_id,
        kind=account.kind,
        broker=account.broker,
        state_dir=state,
        argv=_argv(python, "exec", state, mode, account.account_id),
        portal_sub=account.portal_sub or None,
        slot=account.slot or None,
        journal_tag=account.journal_tag or None,
        strategy_id=account.strategy_id or None,
        basket=account.basket or None,
        slot_armed=account.slot_armed,
    )


def plan_launch(
    *,
    config_path: Path | None = None,
    state_root: Path | None = None,
    mode: str = "paper",
    include_founder: bool = False,
    include_shadow: bool = False,
    python: str | None = None,
    repo: Path | None = None,
) -> C5Plan:
    """Fail closed: live mode, >5 active customers, disabled/live broker, missing/legacy dirs."""
    cleaned = assert_c5_mode(mode)
    root_repo = repo or repo_root()
    root = require_state_dir(state_root or default_state_root(), repo=root_repo)
    py = python or sys.executable
    sig_dir = require_state_dir(signal_state_dir(root), repo=root_repo)
    cfg = Path(config_path) if config_path is not None else default_config_path()
    registry = AccountRegistry.load(cfg)
    customers = [acc for acc in registry.all() if acc.kind == "customer" and acc.status == "active"]
    if len(customers) > MAX_CUSTOMER_EXECS:
        raise AccountSafetyError(f"V2 c5 fail-closed: customer exec cap is {MAX_CUSTOMER_EXECS}, got {len(customers)}")
    execs: list[C5Process] = []
    seen: set[str] = set()
    for acc in customers:
        execs.append(_bind_exec_proc(acc, root, cleaned, py, root_repo))
        seen.add(acc.account_id)
    if include_founder:
        founder = registry.require_active(registry.default_account)
        if founder.account_id not in seen:
            execs.append(_bind_exec_proc(founder, root, cleaned, py, root_repo))
            seen.add(founder.account_id)
    if include_shadow:
        shadow = registry.require_active("v2-shadow")
        if shadow.account_id not in seen:
            execs.append(_bind_exec_proc(shadow, root, cleaned, py, root_repo))
    return C5Plan(
        mode=cleaned,
        state_root=root,
        signal=C5Process(
            role="signal",
            account_id=None,
            kind=None,
            broker=None,
            state_dir=sig_dir,
            argv=_argv(py, "signal", sig_dir, cleaned, None),
        ),
        execs=tuple(execs),
        customer_count=len(customers),
        include_founder=include_founder,
        include_shadow=include_shadow,
        config_path=cfg,
    )


def _run_proc(proc: C5Process, *, cwd: Path, config_path: Path) -> dict[str, Any]:
    if any(part in _LIVE_MODES for part in proc.argv):
        raise AccountSafetyError("V2 c5 fail-closed: live argv refused")
    if "--mode" in proc.argv:
        idx = proc.argv.index("--mode")
        if idx + 1 < len(proc.argv):
            assert_c5_mode(proc.argv[idx + 1])
    env = os.environ.copy()
    env["AAD_ACCOUNTS"] = str(config_path)
    completed = subprocess.run(list(proc.argv), cwd=cwd, capture_output=True, text=True, check=False, env=env)
    stdout = completed.stdout.strip()
    body: dict[str, Any]
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = {"stdout": stdout}
        body = parsed if isinstance(parsed, dict) else {"stdout": parsed}
    else:
        body = {}
    if completed.returncode != 0:
        err = completed.stderr.strip()
        reason = err or body.get("reason") or f"exit {completed.returncode}"
        raise AccountClosed(f"RUNTIME_REFUSED:{reason}")
    body.setdefault("ok", True)
    body["role"] = proc.role
    body["account_id"] = proc.account_id
    body["state_dir"] = str(proc.state_dir)
    return body


def start_launch(plan: C5Plan, *, dry_run: bool = False, cwd: Path | None = None) -> dict[str, Any]:
    body = plan.as_dict()
    if dry_run:
        body["dry_run"] = True
        body["started"] = False
        return body
    work = cwd or repo_root()
    # Shared signal once, then fan-out <=5 customer execs. Status stays file-only.
    started = [_run_proc(plan.signal, cwd=work, config_path=plan.config_path)]
    if plan.execs:
        workers = min(len(plan.execs), MAX_CUSTOMER_EXECS + 2)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            started.extend(pool.map(lambda row: _run_proc(row, cwd=work, config_path=plan.config_path), plan.execs))
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    ops = {
        **body,
        "dry_run": False,
        "started": True,
        "started_at": stamp,
        "stopped": False,
        "results": started,
    }
    (plan.state_root / STOPPED_NAME).unlink(missing_ok=True)
    (plan.state_root / OPS_NAME).write_text(json.dumps(ops, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return ops


def status_launch(state_root: Path, *, repo: Path | None = None) -> dict[str, Any]:
    root = require_state_dir(state_root, repo=repo)
    ops_path = root / OPS_NAME
    if not ops_path.is_file():
        return {
            "ok": True,
            "running": False,
            "reason": "NOT_STARTED",
            "state_root": str(root),
            "live_broker": False,
            "orders": "PAPER",
        }
    ops = json.loads(ops_path.read_text(encoding="utf-8"))
    if not isinstance(ops, dict):
        raise AccountClosed("OPS_CORRUPT")
    stopped = (root / STOPPED_NAME).is_file() or bool(ops.get("stopped"))
    raw_signal = ops.get("signal")
    signal: dict[str, Any] = raw_signal if isinstance(raw_signal, dict) else {}
    sig_dir = Path(str(signal.get("state_dir") or root / "signal"))
    exec_rows: list[dict[str, Any]] = []
    raw_execs = ops.get("execs")
    if isinstance(raw_execs, list):
        for row in raw_execs:
            if not isinstance(row, dict):
                continue
            aid = str(row.get("account_id") or "")
            ed = Path(str(row.get("state_dir") or exec_state_dir(root, aid)))
            exec_rows.append(
                {
                    "account_id": aid,
                    "kind": row.get("kind"),
                    "ready": (ed / f"exec-{aid}.ready").is_file() if aid else False,
                    "state_dir": str(ed),
                    "portal_sub": row.get("portal_sub"),
                    "slot": row.get("slot"),
                    "journal_tag": row.get("journal_tag"),
                    "strategy_id": row.get("strategy_id"),
                    "basket": row.get("basket"),
                    "slot_armed": bool(row.get("slot_armed")),
                }
            )
    return {
        "ok": True,
        "running": not stopped,
        "stopped": stopped,
        "state_root": str(root),
        "mode": ops.get("mode", "paper"),
        "customer_count": ops.get("customer_count", 0),
        "signal_ready": (sig_dir / "signal.ready").is_file(),
        "execs": exec_rows,
        "live_broker": False,
        "orders": "PAPER",
    }


def stop_launch(state_root: Path, *, repo: Path | None = None) -> dict[str, Any]:
    root = require_state_dir(state_root, repo=repo)
    (root / STOPPED_NAME).write_text("stopped\n", encoding="utf-8")
    ops_path = root / OPS_NAME
    if ops_path.is_file():
        raw = json.loads(ops_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw["stopped"] = True
            raw["running"] = False
            ops_path.write_text(json.dumps(raw, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "stopped": True,
        "state_root": str(root),
        "live_broker": False,
        "orders": "PAPER",
        "ledgers": "kept",
    }


def _safe_arcname(name: str) -> str:
    cleaned = name.replace("\\", "/").lstrip("./")
    if cleaned.startswith("/") or cleaned.startswith("../"):
        raise AccountSafetyError(f"V2 c5 fail-closed: unsafe archive member {name!r}")
    parts = Path(cleaned).parts
    if ".." in parts or any(part in _LEGACY_DIR_NAMES for part in parts):
        raise AccountSafetyError(f"V2 c5 fail-closed: archive names a legacy book path {name!r}")
    if cleaned.startswith("data/recon") or cleaned.startswith("data/shadow"):
        raise AccountSafetyError(f"V2 c5 fail-closed: archive names a legacy book path {name!r}")
    return cleaned


def backup_paper_state(state_root: Path, dest: Path, *, repo: Path | None = None) -> dict[str, Any]:
    root = require_state_dir(state_root, repo=repo)
    dest = dest.expanduser()
    dest.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix not in {".tgz", ".tar", ".gz"})
    rels = [_safe_arcname(p.relative_to(root).as_posix()) for p in files]
    manifest = {
        "kind": "c5-paper-state",
        "live_broker": False,
        "orders": "PAPER",
        "files": rels,
        "customer_exec_dirs": sorted(
            {Path(rel).parts[1] for rel in rels if rel.startswith("exec/") and len(Path(rel).parts) >= 2}
        ),
    }
    payload = json.dumps(manifest, sort_keys=True).encode("utf-8")
    with tarfile.open(dest, "w:gz") as tf:
        info = tarfile.TarInfo(MANIFEST_NAME)
        info.size = len(payload)
        tf.addfile(info, io.BytesIO(payload))
        for path, rel in zip(files, rels, strict=True):
            if rel == MANIFEST_NAME:
                continue
            tf.add(path, arcname=rel)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    return {
        "ok": True,
        "dest": str(dest.resolve()),
        "sha256": digest,
        "file_count": len(rels),
        "live_broker": False,
        "orders": "PAPER",
    }


def restore_dry_run(snapshot: Path) -> dict[str, Any]:
    if not snapshot.is_file():
        raise AccountClosed(f"SNAPSHOT_MISSING:{snapshot}")
    members: list[str] = []
    manifest: dict[str, Any] | None = None
    with tarfile.open(snapshot, "r:gz") as tf:
        for info in tf.getmembers():
            name = _safe_arcname(info.name)
            members.append(name)
            if name == MANIFEST_NAME and info.isfile():
                extracted = tf.extractfile(info)
                if extracted is None:
                    continue
                raw = json.loads(extracted.read().decode("utf-8"))
                if isinstance(raw, dict):
                    manifest = raw
    if manifest is not None and manifest.get("live_broker") is True:
        raise AccountSafetyError("V2 c5 fail-closed: snapshot claims live_broker")
    if manifest is not None and manifest.get("kind") not in {None, "c5-paper-state"}:
        raise AccountSafetyError("V2 c5 fail-closed: snapshot is not a c5 paper state tarball")
    return {
        "ok": True,
        "dry_run": True,
        "would_write": False,
        "snapshot": str(snapshot),
        "members": members,
        "manifest": manifest,
        "live_broker": False,
        "orders": "PAPER",
    }


def restore_apply(snapshot: Path, state_root: Path, *, repo: Path | None = None) -> dict[str, Any]:
    dry = restore_dry_run(snapshot)
    root = require_state_dir(state_root, repo=repo)
    with tarfile.open(snapshot, "r:gz") as tf:
        for info in tf.getmembers():
            name = _safe_arcname(info.name)
            if name == MANIFEST_NAME:
                continue
            dest = (root / name).resolve()
            assert_allowed_state_path(dest, repo=repo)
            if dest != root and root not in dest.parents:
                raise AccountSafetyError(f"V2 c5 fail-closed: extract escaped state root {name!r}")
            if info.isdir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            if not info.isfile():
                raise AccountSafetyError(f"V2 c5 fail-closed: refusing non-file archive member {name!r}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            extracted = tf.extractfile(info)
            if extracted is None:
                raise AccountClosed(f"SNAPSHOT_MEMBER_UNREADABLE:{name}")
            dest.write_bytes(extracted.read())
    dry["dry_run"] = False
    dry["would_write"] = False
    dry["applied"] = True
    dry["state_root"] = str(root)
    return dry


def _fail(exc: Exception) -> int:
    print(json.dumps({"ok": False, "reason": str(exc), "orders": "REFUSED", "live_broker": False}), file=sys.stderr)
    return 2


def cli(argv: list[str]) -> int:
    raw = [argv[0].replace("_", "-"), *argv[1:]] if argv else ["c5"]
    p = argparse.ArgumentParser(description="C5-04 founder ops (paper/shadow only; never live)")
    p.add_argument(
        "command",
        choices=("c5-plan", "c5-start", "c5-status", "c5-stop", "c5-backup", "c5-restore"),
    )
    p.add_argument("--config", default=None)
    p.add_argument("--state-dir", default=None)
    p.add_argument("--mode", default="paper")
    p.add_argument("--with-founder", action="store_true")
    p.add_argument("--with-shadow", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--snapshot", default="")
    args = p.parse_args(raw)
    try:
        assert_c5_mode(args.mode)
        cfg = Path(args.config) if args.config else default_config_path()
        state = Path(args.state_dir) if args.state_dir else default_state_root()
        cmd = args.command
        if cmd in {"c5-plan", "c5-start"}:
            plan = plan_launch(
                config_path=cfg,
                state_root=state,
                mode=args.mode,
                include_founder=args.with_founder,
                include_shadow=args.with_shadow,
            )
            body = start_launch(plan, dry_run=args.dry_run or cmd == "c5-plan")
            print(json.dumps(body, sort_keys=True))
            return 0 if body.get("ok") else 1
        if cmd == "c5-status":
            print(json.dumps(status_launch(state), sort_keys=True))
            return 0
        if cmd == "c5-stop":
            print(json.dumps(stop_launch(state), sort_keys=True))
            return 0
        if cmd == "c5-backup":
            dest = Path(args.snapshot) if args.snapshot else state.parent / "c5-backups" / "c5-paper.tgz"
            print(json.dumps(backup_paper_state(state, dest), sort_keys=True))
            return 0
        if cmd == "c5-restore":
            if not args.snapshot:
                print("c5-restore requires --snapshot", file=sys.stderr)
                return 2
            snap = Path(args.snapshot)
            if args.apply and not args.dry_run:
                print(json.dumps(restore_apply(snap, state), sort_keys=True))
                return 0
            print(json.dumps(restore_dry_run(snap), sort_keys=True))
            return 0
        raise AccountClosed(f"UNKNOWN_COMMAND:{cmd}")
    except (AccountSafetyError, AccountClosed, tarfile.TarError, OSError, json.JSONDecodeError) as exc:
        return _fail(exc)
