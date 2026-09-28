"""python -m runtime forward-eval — nightly forward harness (off by default).

Uses the V2 engine kernel over TapeSource. Never writes into checkout data/.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from contracts.clock import IST
from strategies.forward import evaluate_session, format_report, load_lock, load_spec
from strategies.forward.spec import SpecRefused

from runtime.jobs import JOBS, JobTimeout, publish_atomic, run_with_deadline


def _checkout_root(start: Path) -> Path | None:
    for p in start.resolve().parents:
        if (p / ".git").exists() or (p / "packages").is_dir():
            return p
    return None


def _guard_out(out_dir: Path) -> None:
    root = _checkout_root(Path(__file__))
    if root is None:
        return
    data = (root / "data").resolve()
    try:
        if out_dir.resolve() == data or out_dir.resolve().is_relative_to(data):
            raise ValueError(f"REG-11: --out cannot be under {data}")
    except (ValueError, OSError):
        if str(out_dir.resolve()).startswith(str(data)):
            raise ValueError(f"REG-11: --out cannot be under {data}") from None


def forward_eval_enabled(engine_yaml: Path) -> bool:
    if not engine_yaml.is_file():
        return False
    loaded = yaml.safe_load(engine_yaml.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        return False
    block = loaded.get("forward_eval") or {}
    if isinstance(block, dict):
        return bool(block.get("enabled", False))
    return False


def run_forward_eval(
    *,
    session: str,
    tape: Path,
    out_dir: Path,
    specs_dir: Path,
    lock_path: Path,
    deadline_s: float | None = None,
) -> dict[str, Any]:
    _guard_out(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lock = load_lock(lock_path)
    reports = []
    trades: list[dict[str, Any]] = []

    def _work() -> dict[str, Any]:
        for spec_path in sorted(specs_dir.glob("*.yaml")):
            spec = load_spec(spec_path)
            report, rows = evaluate_session(spec, tape, session, lock=lock)
            reports.append(report.as_dict())
            trades.extend(rows)
            print(format_report(report))
        body = json.dumps(
            {"ok": True, "session": session, "reports": reports, "trades": trades},
            indent=2,
        )
        publish_atomic(out_dir / "forward_report.json", body + "\n")
        return {"ok": True, "n_specs": len(reports), "n_trades": len(trades)}

    if deadline_s is None:
        return _work()
    return run_with_deadline(_work, float(deadline_s), job="forward-eval")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m runtime forward-eval")
    p.add_argument("--session", default=datetime.now(IST).date().isoformat())
    p.add_argument("--tape", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--config", type=Path, default=Path("config/v2/engine.yaml"))
    p.add_argument("--specs", type=Path, default=Path("config/v2/forward/specs"))
    p.add_argument("--lock", type=Path, default=Path("config/v2/forward/prereg.lock"))
    p.add_argument("--deadline", type=float, default=None)
    args = p.parse_args(argv)

    if not forward_eval_enabled(args.config):
        print(
            json.dumps(
                {
                    "ok": True,
                    "skipped": True,
                    "reason": "forward_eval.enabled: false",
                    "session": args.session,
                }
            )
        )
        return 0

    if args.tape is None or not args.tape.is_file():
        print("forward-eval enabled but --tape is missing", flush=True)
        return 2

    out_dir = args.out if args.out is not None else Path(tempfile.mkdtemp(prefix="forward-eval-"))
    timeout = float(JOBS["forward-eval"] if args.deadline is None else args.deadline)
    try:
        result = run_with_deadline(
            lambda: run_forward_eval(
                session=args.session,
                tape=args.tape,
                out_dir=out_dir,
                specs_dir=args.specs,
                lock_path=args.lock,
            ),
            timeout,
            job="forward-eval",
        )
        print(json.dumps({"ok": True, **result, "out": str(out_dir)}))
        return 0
    except SpecRefused as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}))
        return 2
    except JobTimeout as exc:
        tmp = (out_dir / "forward_report.json").with_name("forward_report.json.tmp")
        if tmp.exists():
            tmp.unlink()
        print(json.dumps({"ok": False, "reason": "JOB_TIMEOUT", "job": exc.job}))
        return 1
    except ValueError as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
