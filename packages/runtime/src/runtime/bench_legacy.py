"""Frozen legacy benchmark: replay_paper_scalp on a committed recorder tape.

    python -m runtime bench-legacy --day YYYY-MM-DD --tape PATH --out DIR

Writes trades.csv + summary.json (trade count + net P&L) into --out (default temp).
The benchmark runs under a deadline (default 600s, REG-10 guard) and never writes into
the checkout's data/ folder (REG-11 guard).
"""

from __future__ import annotations

import argparse
import csv
import json
import signal
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from types import FrameType, ModuleType
from typing import Any

# ponytail: Dynamic import after sys.path guard. Caller ensures desk-ml is installed.


class TimeoutError(Exception):
    """Raised when the benchmark exceeds the deadline."""


def _alarm_handler(signum: int, frame: FrameType | None) -> None:
    raise TimeoutError("Benchmark exceeded deadline")


def _patch_module_attr(mod: ModuleType, name: str, value: object) -> None:
    """Write a module global. paper_scalp re-exports resolve_lot_size, so attribute assignment is implicit-reexport."""
    mod.__dict__[name] = value


def _checkout_root(start: Path) -> Path | None:
    """Walk parents for a .git checkout. None if this file is not inside a repo."""
    for p in start.resolve().parents:
        if (p / ".git").exists():
            return p
    return None


def run_benchmark(
    *,
    day: str,
    tape_path: Path,
    out_dir: Path,
    deadline_s: int = 600,
) -> dict[str, Any]:
    """Run frozen legacy replay and return summary.

    Args:
        day: Session date YYYY-MM-DD
        tape_path: Path to recorder tape JSON fixture
        out_dir: Output directory for trades.csv and summary.json
        deadline_s: Timeout in seconds (default 600)

    Returns:
        dict with n_trades and net_pnl_inr

    Raises:
        TimeoutError: If benchmark exceeds deadline
    """
    # REG-11: prevent writing to checkout's data/ folder
    # Check if out_dir (or any ancestor before reaching /) is under a git repo's data/
    check_path = out_dir.absolute()
    while check_path != check_path.parent:
        parent = check_path.parent
        if check_path.name == "data" and (parent / ".git").exists():
            # out_dir is at or under a git repo's data/ folder
            msg = f"REG-11: Cannot write benchmark output to {out_dir.absolute()} (under checkout data/)"
            raise ValueError(msg)
        check_path = parent

    # REG-10: deadline guard
    signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(deadline_s)

    try:
        # desk-ml is an installed workspace package (same as CI). paper_scalp re-exports
        # resolve_lot_size implicitly; patch the module dict so replay sees fixture lots.
        import desk_ml.paper_scalp as paper_scalp_mod
        from desk_ml.paper_lots import resolve_lot_size
        from desk_ml.paper_scalp import replay_paper_scalp
        from desk_ml.testing.canonical import load_fixture

        # Load the tape
        fixture = load_fixture(tape_path.stem, folder=tape_path.parent)
        triples_by_und = fixture["triples"]
        lot_sizes = fixture["lot_sizes"]

        def _fixture_lot_size(und: str, root: Path | None = None) -> tuple[int | None, str]:
            _ = root
            return (int(lot_sizes.get(und, 25)), "fixture")

        # Setup minimal recon (no disk writes to data/)
        with tempfile.TemporaryDirectory() as tmp_root:
            tmp_path = Path(tmp_root)
            recon_dir = tmp_path / "data" / "recon"
            recon_dir.mkdir(parents=True)

            # Minimal founder config
            underlyings = list(triples_by_und.keys())
            (recon_dir / "founder_trade_underlyings.json").write_text(json.dumps({"trade_underlyings": underlyings}))

            # Legacy params (from canonical.PARAMS_LEGACY)
            (recon_dir / "ml_paper_session_params.json").write_text(
                json.dumps({"stop_frac": 0.38, "scalp_hold_bars": 9, "nudge_n_closed": 494})
            )

            saved_resolve = resolve_lot_size
            _patch_module_attr(paper_scalp_mod, "resolve_lot_size", _fixture_lot_size)
            try:
                # Run frozen replay (flag off, live_session=True, write=False)
                board = replay_paper_scalp(
                    root=tmp_path,
                    underlyings=tuple(underlyings),
                    triples_by_und=triples_by_und,
                    session_ist_date=day,
                    write=False,
                    live_session=True,
                    use_event_bus=False,
                )
            finally:
                _patch_module_attr(paper_scalp_mod, "resolve_lot_size", saved_resolve)

        # Extract filled trades
        closed_trades = board.get("closed_trades") or []
        filled = [t for t in closed_trades if t.get("filled")]

        # Write trades.csv
        if filled:
            csv_path = out_dir / "trades.csv"
            fieldnames = [
                "trade_id",
                "book_id",
                "underlying",
                "side",
                "atm_strike",
                "opened_ts",
                "closed_ts",
                "entry",
                "exit",
                "qty",
                "lots",
                "exit_reason",
                "gross_pnl_inr",
                "charges_inr",
                "realized_pnl_inr",
            ]
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for trade in filled:
                    writer.writerow({k: trade.get(k, "") for k in fieldnames})

        # Summary
        n_trades = len(filled)
        net_pnl = sum(float(t.get("realized_pnl_inr") or 0.0) for t in filled)

        summary = {
            "n_trades": n_trades,
            "net_pnl_inr": round(net_pnl, 2),
            "day": day,
            "tape": str(tape_path),
        }

        # Write summary.json
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

        return summary

    finally:
        signal.alarm(0)


def main(argv: list[str] | None = None) -> int:
    """Frozen legacy benchmark CLI."""
    ap = argparse.ArgumentParser(
        prog="python -m runtime bench-legacy",
        description="Frozen legacy benchmark: replay_paper_scalp on recorder tape",
    )
    ap.add_argument("--day", required=True, metavar="YYYY-MM-DD", help="Session date")
    ap.add_argument("--tape", required=True, type=Path, metavar="PATH", help="Path to recorder tape JSON")
    ap.add_argument(
        "--out",
        type=Path,
        metavar="DIR",
        help="Output directory (default: temp dir, REG-11 guard)",
    )
    ap.add_argument("--deadline", type=int, default=600, metavar="SECONDS", help="Timeout in seconds (default 600)")

    args = ap.parse_args(argv)

    # Validate day format
    try:
        datetime.strptime(args.day, "%Y-%m-%d")  # noqa: DTZ007
    except ValueError:
        print(f"Error: invalid day format '{args.day}', expected YYYY-MM-DD", file=sys.stderr)
        return 1

    # Validate tape exists
    if not args.tape.is_file():
        print(f"Error: tape not found: {args.tape}", file=sys.stderr)
        return 1

    # REG-11 guard: default to temp dir, never data/
    if args.out is None:
        out_dir = Path(tempfile.mkdtemp(prefix="bench-legacy-"))
        print(f"Output directory: {out_dir}")
    else:
        out_dir = args.out
        # Prevent writes into checkout's data/ folder (find .git, not a fixed parent count)
        try:
            repo_root = _checkout_root(Path(__file__))
            if repo_root is not None:
                data_dir = repo_root / "data"
                if out_dir.resolve().is_relative_to(data_dir):
                    print(f"Error: --out cannot be under {data_dir} (REG-11 guard)", file=sys.stderr)
                    return 1
        except (ValueError, OSError):
            pass  # Not in repo, allow

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        summary = run_benchmark(
            day=args.day,
            tape_path=args.tape,
            out_dir=out_dir,
            deadline_s=args.deadline,
        )
        print(f"Benchmark complete: {summary['n_trades']} trades, net {summary['net_pnl_inr']:.2f}")
        return 0
    except TimeoutError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except (ImportError, FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
