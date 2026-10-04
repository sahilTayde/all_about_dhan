"""python -m runtime <command> — paper only.

Commands: engine, health, llm-advisor, reset-breaker, deploy, backup, restore, job,
flatten (out-of-band paper flatten), bench-legacy (V2-17), forward-eval
(V2-20a; off by default), and V2-22 signal / exec --account.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from contracts.clock import IST, LiveClock, SimClock

from runtime.jobs import JOBS, JobTimeout, publish_atomic, run_with_deadline
from runtime.services import (
    backup_state,
    deploy,
    reset_breaker,
    restore_state,
    run_engine,
    run_guarded,
    run_health,
    run_llm_advisor,
    write_engine_status,
)


def _state_dir(raw: str | None) -> Path:
    if raw:
        return Path(raw)
    env = os.environ.get("AAD_STATE_DIR")
    if env:
        return Path(env)
    return Path("data/state")


def _clock(now: str | None) -> LiveClock | SimClock:
    if now:
        dt = datetime.fromisoformat(now)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return SimClock(dt)
    env = os.environ.get("AAD_NOW")
    if env:
        dt = datetime.fromisoformat(env)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return SimClock(dt)
    return LiveClock()


def _idle(state_dir: Path, name: str) -> None:
    write_engine_status(state_dir, LiveClock()) if name == "engine" else None
    (state_dir / f"{name}.ready").write_text("ok\n", encoding="utf-8")


_USAGE = """usage: python -m runtime {engine|health|llm-advisor|reset-breaker|
  deploy|backup|restore|job|flatten|bench-legacy|forward-eval|signal|exec} ...
  engine|health|llm-advisor [--once] [--state-dir DIR] [--now ISO] [--mode replay|paper]
  reset-breaker <service> [--state-dir DIR] [--now ISO]
  flatten [--account founder] [--state-dir DIR] [--now ISO]
  signal [--once] [--state-dir DIR] [--mode replay|paper]
  exec --account <id> [--once] [--state-dir DIR] [--mode replay|paper]
  job <name> [--state-dir DIR]
  bench-legacy --day YYYY-MM-DD --tape PATH [--out DIR] [--deadline SECONDS]
  forward-eval --session YYYY-MM-DD [--tape PATH] [--out DIR] [--config PATH]
  deploy <sha> | backup | restore --snapshot PATH
"""


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw or raw[0] in ("-h", "--help"):
        print(_USAGE, end="")
        return 0
    if raw[0].replace("_", "-") == "bench-legacy":
        from runtime.bench_legacy import main as bench_legacy_main

        return bench_legacy_main(raw[1:])
    if raw[0].replace("_", "-") == "forward-eval":
        from runtime.forward_eval import main as forward_eval_main

        return forward_eval_main(raw[1:])

    p = argparse.ArgumentParser(description="V2 runtime (paper only; no broker orders)")
    p.add_argument("command")
    p.add_argument("target", nargs="?")
    p.add_argument("--state-dir", default=None)
    p.add_argument("--now", default=None, help="ISO IST timestamp (tests / deploy clock)")
    p.add_argument("--once", action="store_true")
    p.add_argument("--role", default="all")
    p.add_argument("--mode", default="replay")
    p.add_argument("--emergency", action="store_true")
    p.add_argument("--sha", default="")
    p.add_argument("--snapshot", default="")
    p.add_argument("--ready-timeout", type=float, default=5.0)
    p.add_argument("--account", default="founder")
    args = p.parse_args(raw)
    if args.mode not in {"replay", "paper"}:
        print(
            "live-data/live modes are not started from this ticket (no credentials)",
            file=sys.stderr,
        )
        return 2
    state = _state_dir(args.state_dir)
    clock = _clock(args.now)
    cmd = args.command.replace("_", "-")

    if cmd == "reset-breaker":
        if not args.target:
            print("reset-breaker requires <service>", file=sys.stderr)
            return 2
        reset_breaker(args.target, state, clock)
        print(json.dumps({"reset": args.target, "ts": clock.now().isoformat(timespec="seconds")}))
        return 0

    if cmd == "health":
        snap = run_health(state, clock, once=args.once)
        print(json.dumps(snap))
        return 0

    if cmd == "engine":
        return run_guarded(
            "engine",
            lambda: run_engine(state, clock, once=args.once),
            state_dir=state,
            clock=clock,
        )

    if cmd in {"marketdata", "gateway"}:
        return run_guarded(cmd, lambda: _idle(state, cmd), state_dir=state, clock=clock)

    if cmd == "llm-advisor":
        return run_guarded(
            "llm-advisor",
            lambda: run_llm_advisor(state, clock, once=args.once, mode=args.mode),
            state_dir=state,
            clock=clock,
        )

    if cmd == "deploy":
        sha = args.sha or args.target or ""
        if not sha:
            print("deploy requires <sha>", file=sys.stderr)
            return 2
        result = deploy(
            sha,
            state_dir=state,
            clock=clock,
            emergency=args.emergency,
            ready_timeout_s=args.ready_timeout,
            start_engine=lambda: run_engine(state, clock, once=True),
        )
        print(json.dumps(result))
        return 0 if result.get("ok") else 1

    if cmd == "backup":
        dest = Path(args.snapshot or args.target or state.parent / "backup_snap")
        digest = backup_state(state, dest)
        print(json.dumps({"ok": True, "output_hash": digest, "dest": str(dest)}))
        return 0

    if cmd == "restore":
        snap_path = Path(args.snapshot or args.target or "")
        if not snap_path:
            print("restore requires --snapshot", file=sys.stderr)
            return 2
        digest = restore_state(snap_path, state)
        print(json.dumps({"ok": True, "output_hash": digest}))
        return 0

    if cmd in {"signal", "exec"}:
        from accounts.errors import AccountClosed, AccountSafetyError
        from accounts.split import run_role_once

        try:
            result = run_role_once(
                role=cmd,
                account_id=None if cmd == "signal" else (args.account or args.target or "founder"),
                state_dir=state,
                mode=args.mode,
            )
        except (AccountSafetyError, AccountClosed) as exc:
            print(json.dumps({"ok": False, "reason": str(exc), "orders": "REFUSED"}), file=sys.stderr)
            return 2
        print(json.dumps(result))
        return 0 if result.get("ok") else 1

    if cmd == "flatten":
        from runtime.flatten_cli import flatten_cli

        result = flatten_cli(
            account=args.account or args.target or "founder",
            state_dir=state,
            clock=clock,
        )
        print(json.dumps(result))
        return 0 if result.get("ok") else 1

    if cmd == "job":
        job = args.target or ""
        if job not in JOBS:
            print(f"unknown job {job!r}; have {sorted(JOBS)}", file=sys.stderr)
            return 2
        dest = state / f"{job}.out"
        try:
            run_with_deadline(
                lambda: publish_atomic(dest, f"{job} ok\n"),
                float(JOBS[job]),
                job=job,
            )
        except JobTimeout as exc:
            tmp = dest.with_name(dest.name + ".tmp")
            if tmp.exists():
                tmp.unlink()
            print(json.dumps({"ok": False, "reason": "JOB_TIMEOUT", "job": exc.job}))
            return 1
        print(json.dumps({"ok": True, "job": job, "timeout_s": JOBS[job]}))
        return 0

    print(f"unknown command {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
