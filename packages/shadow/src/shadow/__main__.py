"""python -m shadow — paper-only V2 shadow launcher.

Commands: run, follow, status, compare, dry-run.
Live modes are refused. Missing tape fails closed (no invented ticks).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from contracts.clock import IST

from shadow.journal import ShadowJournal
from shadow.runner import compare_day, follow_tape, ist_day, run_once, tape_paths, write_fixture_tape
from shadow.safety import ShadowSafetyError, assert_paper_only


def _state_dir(raw: str | None) -> Path:
    if raw:
        return Path(raw)
    env = os.environ.get("AAD_SHADOW")
    if env:
        return Path(env)
    return Path("data/shadow/v2")


def _tape(raw: str | None, day: str) -> Path:
    if raw:
        return Path(raw)
    env = os.environ.get("AAD_TAPE_V2")
    root = Path(env) if env else Path("data/tape/v2")
    return root / day


def _print(row: dict[str, object]) -> None:
    print(json.dumps(row, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(description="V2 shadow launcher (paper only; no live orders)")
    p.add_argument("command", choices=("run", "follow", "status", "compare", "dry-run"))
    p.add_argument("--state-dir", default=None)
    p.add_argument("--tape", default=None)
    p.add_argument("--day", default=None)
    p.add_argument("--mode", default="paper")
    p.add_argument("--legacy", default=None, help="Optional read-only legacy shadow-v1 JSONL")
    p.add_argument("--stop-flag", default=None)
    p.add_argument("--poll-s", type=float, default=1.0)
    p.add_argument("--max-idle-polls", type=int, default=None)
    p.add_argument("--demo-fills", action="store_true", help="Dry-run only. Refused on follow.")
    args = p.parse_args(raw)

    try:
        mode = assert_paper_only(args.mode)
    except ShadowSafetyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    state = _state_dir(args.state_dir)
    day = args.day or ist_day()
    cmd = args.command

    if cmd == "dry-run":
        fixture = state / "_dry_run" / "ticks.jsonl"
        write_fixture_tape(fixture)
        result = run_once(tape=fixture, state_dir=state, mode=mode, day=day, demo_fills=True)
        _print(
            {
                "ok": True,
                "command": "dry-run",
                "day": result.day,
                "decisions": result.decisions,
                "opens": result.opens,
                "flats": result.flats,
                "closed_reason": result.closed_reason,
                "output_hash": result.output_hash,
                "orders": "REFUSED",
            }
        )
        return 0 if result.closed_reason is None else 1

    if cmd == "run":
        tape = _tape(args.tape, day)
        if args.demo_fills:
            print("V2 shadow fail-closed: --demo-fills is dry-run only", file=sys.stderr)
            return 2
        result = run_once(tape=tape, state_dir=state, mode=mode, day=day, demo_fills=False)
        _print(
            {
                "ok": result.closed_reason is None,
                "command": "run",
                "day": result.day,
                "decisions": result.decisions,
                "holds": result.holds,
                "envelopes": result.envelopes,
                "closed_reason": result.closed_reason,
                "tape": str(tape),
                "paths": [str(path) for path in tape_paths(tape)],
                "orders": "REFUSED",
            }
        )
        return 0 if result.closed_reason is None else 1

    if cmd == "follow":
        if args.demo_fills:
            print("V2 shadow fail-closed: --demo-fills is dry-run only", file=sys.stderr)
            return 2
        tape = _tape(args.tape, day)
        stop = Path(args.stop_flag) if args.stop_flag else state / "STOPPED.flag"
        result = follow_tape(
            tape=tape,
            state_dir=state,
            stop_flag=stop,
            mode=mode,
            day=day,
            poll_s=args.poll_s,
            max_idle_polls=args.max_idle_polls,
        )
        _print(
            {
                "ok": True,
                "command": "follow",
                "day": result.day,
                "decisions": result.decisions,
                "closed_reason": result.closed_reason,
                "orders": "REFUSED",
            }
        )
        return 0

    if cmd == "status":
        journal = ShadowJournal(state)
        status_path = journal.files(day).status
        if not status_path.is_file():
            _print(
                {
                    "ok": False,
                    "command": "status",
                    "day": day,
                    "reason": "NO_STATUS",
                    "state_dir": str(state),
                    "orders": "REFUSED",
                }
            )
            return 1
        body = json.loads(status_path.read_text(encoding="utf-8"))
        body["command"] = "status"
        body["ok"] = True
        _print(body)
        return 0

    if cmd == "compare":
        legacy = Path(args.legacy) if args.legacy else Path("data/shadow") / f"{day}.jsonl"
        body = compare_day(state_dir=state, day=day, legacy_path=legacy)
        body["command"] = "compare"
        body["as_of"] = datetime.now(IST).isoformat(timespec="seconds")
        _print(body)
        return 0

    print(f"unknown command {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
