"""Backtest gate: replay the synthetic fixture days and compare with the committed expected results.

    python tools/backtest_gate/gate.py            # exit 1 if any result moved
    python tools/backtest_gate/gate.py --update   # rewrite expected_results.json after an intended change

Each fixture replays through the event path (analysts -> boss -> risk engine -> desk -> ledger), so
a change to strategy, gate, sizing, exit, cost or risk code that moves a trade, a skip count or a
veto shows up here. An intended change ships with the regenerated expected file and the honest
backtest section of the PR template filled in. The fixtures are synthetic, not market data;
matching them says nothing about edge. Paper only; no broker is called.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional, Sequence

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXPECTED = HERE / "expected_results.json"
FIXTURES = (
    REPO / "packages" / "desk-ml" / "tests" / "fixtures" / "synthetic_session_nifty.json",
    HERE / "fixtures" / "synthetic_session_sensex.json",
)
TRADE_KEYS = ("trade_id", "book_id", "underlying", "side", "atm_strike", "strike_source", "opened_ts", "closed_ts",
              "entry", "exit", "stop", "target", "lots", "qty", "exit_reason", "filled", "gross_pnl_inr",
              "charges_inr", "realized_pnl_inr")


def _r(x: Any) -> Any:
    return round(x, 2) if isinstance(x, float) else x


RISK_PROFILES = {"replay_risk": False, "live_paper_risk": True}  # profile -> resolve_risk_config(live_session=...)


def replay_fixture(path: Path, *, live_risk: bool = False) -> dict[str, Any]:
    """One synthetic day through the event path, reduced to the numbers that must not move silently.

    `live_risk` swaps in the live paper loop's risk file (config/event_path.yaml `live_risk_config`)
    so a change to either risk file is caught; the replay's own strategy parameters stay the same.
    """
    import desk_ml.paper_scalp as ps
    from desk_ml.event_parity import fixture_replay_kwargs, load_fixture
    from desk_ml.event_path import EventSession, resolve_risk_config

    fx = load_fixture(path)
    risk_file, _explicit = resolve_risk_config(live_session=live_risk, root=REPO)
    saved = ps.load_index_closes, ps.resolve_lot_size
    ps.load_index_closes = lambda u, root=None: {}  # no prior-day files: the fixture never reads repo data
    ps.resolve_lot_size = lambda und, root=None: (int(fx["lot_size"]), "fixture")
    session = EventSession(risk_config=risk_file)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            board = ps.replay_paper_scalp(**fixture_replay_kwargs(fx, Path(tmp)), write=False, event_session=session)
        bus = session.summary()
        ledger = session.ledger_trades()
    finally:
        session.close()
        ps.load_index_closes, ps.resolve_lot_size = saved

    trades = [{k: _r(t.get(k)) for k in TRADE_KEYS} for t in board.get("closed_trades") or []]
    filled = [t for t in trades if t["filled"]]
    exits: dict[str, int] = {}
    for t in filled:
        exits[str(t["exit_reason"])] = exits.get(str(t["exit_reason"]), 0) + 1
    vetoes: dict[str, int] = {}
    for v in bus.get("vetoes") or []:
        key = str(v.get("reason_code") or v.get("reason"))
        vetoes[key] = vetoes.get(key, 0) + 1
    closed_ledger = [t for t in ledger if t["status"] == "CLOSED"]
    return {
        "fixture": Path(path).resolve().relative_to(REPO).as_posix(),
        "risk_config": Path(risk_file).resolve().relative_to(REPO).as_posix(),
        "session_ist_date": fx["session_ist_date"],
        "underlying": fx["underlying"],
        "n_trades": len(filled),
        "n_wins": sum(1 for t in filled if (t["realized_pnl_inr"] or 0) > 0),
        "gross_pnl_inr": round(sum(t["gross_pnl_inr"] or 0 for t in filled), 2),
        "charges_inr": round(sum(t["charges_inr"] or 0 for t in filled), 2),
        "net_pnl_inr": round(sum(t["realized_pnl_inr"] or 0 for t in filled), 2),
        "exit_reasons": dict(sorted(exits.items())),
        "skip_reason_counts": dict(sorted((board.get("skip_reason_counts") or {}).items())),
        "risk_vetoes": dict(sorted(vetoes.items())),
        "events": dict(sorted((bus.get("events") or {}).items())),
        "handler_errors": len(bus.get("handler_errors") or []),
        "ledger": {"closed": len(closed_ledger), "gross_pnl": round(sum(t["gross_pnl"] for t in closed_ledger), 2),
                   "charges": round(sum(t["charges"] for t in closed_ledger), 2),
                   "net_pnl": round(sum(t["net_pnl"] for t in closed_ledger), 2)},
        "trades_sha256": hashlib.sha256(json.dumps(trades, sort_keys=True).encode()).hexdigest(),
        "trades": trades,
    }


def run_all(fixtures: Sequence[Path] = FIXTURES) -> dict[str, Any]:
    return {"note": "Synthetic fixture replays (not market data). Regenerate with --update; see tools/backtest_gate/README.md.",
            "fixtures": {f"{p.stem}/{name}": replay_fixture(p, live_risk=live)
                         for p in fixtures for name, live in RISK_PROFILES.items()}}


def diff(expected: Any, actual: Any, path: str = "") -> list[str]:
    """Readable leaf-level differences (trade rows are matched by position)."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        out: list[str] = []
        for k in sorted(set(expected) | set(actual)):
            sub = f"{path}.{k}" if path else str(k)
            if k not in expected:
                out.append(f"{sub}: new {json.dumps(actual[k])[:200]}")
            elif k not in actual:
                out.append(f"{sub}: gone (was {json.dumps(expected[k])[:200]})")
            else:
                out += diff(expected[k], actual[k], sub)
        return out
    if isinstance(expected, list) and isinstance(actual, list):
        out = [f"{path}: {len(expected)} -> {len(actual)} rows"] if len(expected) != len(actual) else []
        for n, (a, b) in enumerate(zip(expected, actual)):
            out += diff(a, b, f"{path}[{n}]")
        return out
    return [] if expected == actual else [f"{path}: {json.dumps(expected)} -> {json.dumps(actual)}"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="tools/backtest_gate/gate.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--update", action="store_true", help="write the current results as the new expected file")
    ap.add_argument("--expected", type=Path, default=EXPECTED)
    ap.add_argument("--max-lines", type=int, default=60)
    args = ap.parse_args(argv)

    actual = run_all()
    for name, r in actual["fixtures"].items():
        print(f"{name}: trades {r['n_trades']} wins {r['n_wins']} net ₹{r['net_pnl_inr']:,.2f} "
              f"(gross ₹{r['gross_pnl_inr']:,.2f}, charges ₹{r['charges_inr']:,.2f}) vetoes {sum(r['risk_vetoes'].values())}")
    if args.update:
        args.expected.write_text(json.dumps(actual, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"UPDATED {args.expected.relative_to(REPO)}: commit it with the change and fill in the honest-backtest section.")
        return 0
    if not args.expected.is_file():
        print(f"FAIL: {args.expected} missing; run with --update and commit it.")
        return 1
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    problems = diff(expected.get("fixtures"), actual["fixtures"])
    if not problems:
        print("PASS: synthetic replay matches expected_results.json")
        return 0
    print(f"FAIL: {len(problems)} result(s) moved without an updated expected_results.json:")
    for line in problems[: args.max_lines]:
        print(f"  {line}")
    if len(problems) > args.max_lines:
        print(f"  ... {len(problems) - args.max_lines} more")
    print("If the change is intended: python tools/backtest_gate/gate.py --update, commit the file, and fill in the "
          "honest-backtest section of the PR (OOS, costs, DSR, trial count).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
