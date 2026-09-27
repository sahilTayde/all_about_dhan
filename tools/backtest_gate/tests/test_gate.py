"""Backtest gate helpers and the honest-backtest PR check. The full replay runs as its own CI step."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import gate  # noqa: E402
import pr_check  # noqa: E402

TEMPLATE = (HERE.parents[1] / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
FILLED = """## Honest backtest
- **OOS results:** walk-forward 2026-08-01..09-25, 38 trades, net +₹41,200 after costs, max DD ₹18k
- **Costs:** config/charges.yaml (Groww + STT), 1 tick slippage each side
- **DSR:** 0.91 (Sharpe 1.4)
- **Trial count:** 12
- **Expected results file:** regenerated; NIFTY fixture loses one STOP trade
"""


def test_diff_reports_leaf_changes_and_row_counts() -> None:
    exp = {"a": {"n": 1, "trades": [{"x": 1}, {"x": 2}]}, "b": 1}
    act = {"a": {"n": 2, "trades": [{"x": 1}]}, "c": 3}
    out = gate.diff(exp, act)
    assert "a.n: 1 -> 2" in out
    assert "a.trades: 2 -> 1 rows" in out
    assert any(line.startswith("b: gone") for line in out) and any(line.startswith("c: new") for line in out)
    assert gate.diff(exp, json.loads(json.dumps(exp))) == []


def test_expected_file_covers_every_fixture_and_risk_profile() -> None:
    expected = json.loads(gate.EXPECTED.read_text(encoding="utf-8"))
    keys = {f"{p.stem}/{name}" for p in gate.FIXTURES for name in gate.RISK_PROFILES}
    assert set(expected["fixtures"]) == keys
    for r in expected["fixtures"].values():
        assert r["n_trades"] == sum(1 for t in r["trades"] if t["filled"])
        assert r["handler_errors"] == 0
        assert (gate.REPO / r["fixture"]).is_file()
        assert "not market data" in json.loads((gate.REPO / r["fixture"]).read_text(encoding="utf-8"))["note"].lower()


def test_no_gated_change_needs_nothing() -> None:
    assert pr_check.check("", ["packages/warehouse/src/warehouse/etl.py", "docs/x.md"]) == []


def test_gated_change_needs_the_section() -> None:
    [msg] = pr_check.check("## Summary\nrefactor", ["packages/risk-engine/src/risk_engine/engine.py"])
    assert "Honest backtest" in msg


def test_unfilled_template_fails_every_field() -> None:
    problems = pr_check.check(TEMPLATE, ["config/risk_limits.yaml"])
    assert len(problems) == 4 and all("is empty" in p for p in problems)


def test_na_with_reason_is_fine_only_when_results_did_not_move() -> None:
    na = "\n".join(f"- **{label}:** N/A: pure refactor, gate PASS unchanged" for label in pr_check.FIELDS.values())
    body = "## Honest backtest\n" + na + "\n## Handoff Block\n### Accepted\n- x"
    assert pr_check.check(body, ["packages/desk-ml/src/desk_ml/paper_scalp.py"]) == []
    moved = pr_check.check(body, ["packages/desk-ml/src/desk_ml/paper_scalp.py", pr_check.EXPECTED_REL])
    assert len(moved) == 4 and all("cannot be N/A" in p for p in moved)
    bare = body.replace(": pure refactor, gate PASS unchanged", "")
    assert all("without a reason" in p for p in pr_check.check(bare, ["config/charges.yaml"]))


def test_filled_section_passes_even_when_results_moved() -> None:
    assert pr_check.check(FILLED, [pr_check.EXPECTED_REL, "packages/boss/src/boss/orchestrator.py"]) == []
    no_number = FILLED.replace("0.91 (Sharpe 1.4)", "good")
    [msg] = pr_check.check(no_number, [pr_check.EXPECTED_REL])
    assert "'DSR' needs a number" in msg


def test_cli_reads_body_file(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text(FILLED, encoding="utf-8")
    assert pr_check.main(["--body-file", str(body), "--changed", pr_check.EXPECTED_REL]) == 0
    body.write_text(TEMPLATE, encoding="utf-8")
    assert pr_check.main(["--body-file", str(body), "--changed", pr_check.EXPECTED_REL]) == 1
