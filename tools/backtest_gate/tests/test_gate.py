"""Backtest gate helpers and the honest-backtest PR check. The full replay runs as its own CI step."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import gate  # noqa: E402
import mutate  # noqa: E402
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
    keys = {f"{p.stem}/{name}" for p in gate.fixture_paths() for name in gate.PROFILES}
    assert set(expected["fixtures"]) == keys
    for r in expected["fixtures"].values():
        assert r["n_trades"] == sum(1 for t in r["trades"] if t["filled"])
        assert r["handler_errors"] == 0
        if r["fixture"].startswith("recipe:"):
            continue  # generated days: see test_recipe_days_are_deterministic_and_labelled_synthetic
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


def test_source_patch_behaves_like_a_source_edit() -> None:
    """The mutation hook edits the source text, so values derived at import time follow."""
    import subprocess

    probe = (
        "import sys; sys.path.insert(0, {here!r}); import mutate\n"
        "name, _, value = sys.argv[1].partition('=')\n"
        "sys.meta_path.insert(0, mutate.SourcePatch(name, value))\n"
        "import desk_ml.paper_scalp as ps\n"
        "print(ps.DEFAULT_PAPER_PARAMS['stop_frac'], ps.UNFILLED_SECONDS, ps.INDEX_POINT_PROFILES['NIFTY']['min_stop'],"
        " ps.__file__)\n"
    ).format(here=str(HERE))
    outs = {}
    for m in ("STOP_FRAC=0.35", "UNFILLED_BARS=3", "INDEX_POINT_PROFILES.NIFTY.min_stop=5.0"):
        proc = subprocess.run([sys.executable, "-c", probe, m], capture_output=True, text=True, check=True)
        outs[m] = proc.stdout.split()
    assert outs["STOP_FRAC=0.35"][:3] == ["0.35", "120", "6.0"]
    assert outs["UNFILLED_BARS=3"][:3] == ["0.4", "180", "6.0"]
    assert outs["INDEX_POINT_PROFILES.NIFTY.min_stop=5.0"][:3] == ["0.4", "120", "5.0"]
    assert outs["STOP_FRAC=0.35"][3].endswith("desk_ml/paper_scalp.py")  # real file path: repo_root() still works
    src = (Path(outs["STOP_FRAC=0.35"][3])).read_text(encoding="utf-8")
    assert "\nSTOP_FRAC = 0.40\n" in src  # nothing written to the checkout


def test_every_exit_mutant_applies_cleanly() -> None:
    """Each mutant names exactly one top-level assignment (or an existing profile key)."""
    import re as _re

    src = (gate.REPO / "packages/desk-ml/src/desk_ml/paper_scalp.py").read_text(encoding="utf-8")
    for name in mutate.EXIT_MUTANTS:
        if "." in name:
            _t, und, key = name.split(".")
            assert f'"{key}":' in src and und in ("NIFTY", "SENSEX")
            continue
        assert len(_re.findall(rf"^{_re.escape(name)}(\s*:[^=]+)?\s*=", src, _re.M)) == 1, name
    assert set(mutate.UNEXERCISABLE) <= set(mutate.EXIT_MUTANTS)


def test_recipe_days_are_deterministic_and_labelled_synthetic() -> None:
    import synth

    for recipe in synth.load_recipes():
        a, b = synth.dump(synth.generate(recipe)), synth.dump(synth.generate(recipe))
        assert a == b
        assert synth.fixture_path(recipe).read_text(encoding="utf-8") == a
        blob = json.loads(a)
        assert "not market data" in blob["note"].lower() and blob["recipe"] == recipe
