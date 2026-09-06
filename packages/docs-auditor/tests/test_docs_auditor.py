"""Fixture-tree tests. The live repo is allowed to FAIL — checker is real."""

from __future__ import annotations

from pathlib import Path

import pytest

from docs_auditor.auditor import STUB_MARKER, run_audit
from docs_auditor.sanitize import sanitize

TEAMS = (
    "00_orchestrator",
    "01_research",
    "02_phd_math",
    "03_phd_market",
    "04_quant",
    "05_analysis",
    "06_backtesting",
    "07_coding",
    "08_testing",
    "09_review",
)


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _workspace_yaml(*, chain: str = "3m", auditor: str = "mapping") -> str:
    jobs = (
        "jobs:\n  docs_auditor: daily\n"
        if auditor == "string"
        else (
            "jobs:\n"
            "  docs_auditor:\n"
            "    enabled: true\n"
            "    cadence: daily\n"
        )
    )
    return (
        "desk_intel:\n"
        "  poll:\n"
        f"    chain_interval: {chain}\n"
        "sources:\n"
        "  cas:\n"
        "    - id: nse_cas\n"
        "      url: https://example.invalid/cas\n"
        f"{jobs}"
    )


def _good_agent() -> str:
    return """# AGENT.md
**Docs Auditor** (09). CAS Closing Auction Session. Staged IN-PROGRESS. RETUNE gate.
3m full chain default. Customer UI vs internal /desk.
Golden rule: no requirement merge without the Docs Auditor.
No live orders.
"""


def _good_master() -> str:
    # Must look like a manager sheet (Scorecard + Status legend + length).
    body = "\n".join(
        f"| {i} | requirement {i} | **PARTIAL** | evidence path teams/00_orchestrator/docs/ |"
        for i in range(120)
    )
    return f"""# MASTER_REQUIREMENTS — morning check sheet

## Status legend
DONE PARTIAL TODO BLOCKED

## Scorecard
| # | Requirement | Status |
| 1 | 3m chain | PARTIAL |
TRANSCRIPT_VERIFIED **45**
Dashboard PARTIAL mock
No live orders.

{body}
"""


def _good_plan() -> str:
    return "# PLAN.md\nTranscripts: 45 verified. Phase 6 Paper UI | Mock started\n"


def make_tree(root: Path, *, chain: str = "3m", agent: str | None = None, master: str | None = None, plan: str | None = None) -> None:
    _write(root, "AGENT.md", agent if agent is not None else _good_agent())
    _write(root, "PLAN.md", plan if plan is not None else _good_plan())
    _write(root, "docs/MASTER_REQUIREMENTS.md", master if master is not None else _good_master())
    _write(root, "docs/HANDOFF.md", "# HANDOFF\n")
    _write(root, "config/workspace.yaml", _workspace_yaml(chain=chain))
    _write(
        root,
        "teams/06_backtesting/docs/RETUNE_GATE.md",
        "BACKTEST_REQUIRED\nNEWS_DAY\nKeep current strategy.\n",
    )
    _write(
        root,
        "teams/03_phd_market/cas/RESEARCH.md",
        "# CAS\nOfficial **Closing Auction Session**.\n",
    )
    _write(root, "teams/09_review/docs/DOCS_AUDITOR.md", "# Docs Auditor\n")
    _write(
        root,
        "teams/00_orchestrator/docs/TASK_DOCS_AUDITOR.md",
        "# TASK — Docs Auditor\n",
    )
    _write(
        root,
        "teams/04_quant/docs/SIGNAL_STAGING.md",
        "WATCH EARLY CONFIRMED IN-PROGRESS EXPIRED VETOED\n",
    )
    _write(
        root,
        "packages/dhan-client/src/dhan_client/execution.py",
        "class SafeModeError(Exception): ...\n"
        "def place_order():\n"
        "    raise SafeModeError('refused')\n",
    )
    _write(
        root,
        "packages/desk-intel/src/desk_intel/schema.py",
        "WATCH EARLY CONFIRMED IN_PROGRESS EXPIRED VETOED\n"
        "production_params_written = False\n",
    )
    _write(
        root,
        "packages/desk-intel/src/desk_intel/nightly.py",
        "BACKTEST_REQUIRED\nproduction_params_written = False\n",
    )
    _write(
        root,
        "packages/desk-intel/src/desk_intel/__main__.py",
        "def cmd_nightly():\n    attach_docs_audit()\n"
        'commands = {"nightly": cmd_nightly, "post-market": cmd_nightly}\n',
    )
    _write(
        root,
        "packages/desk-intel/src/jobs/__main__.py",
        "from desk_intel.__main__ import main\n",
    )
    _write(
        root,
        ".cursor/rules/docs-auditor.mdc",
        "---\nalwaysApply: true\n---\npython -m docs_auditor\n",
    )
    _write(
        root,
        ".cursor/hooks.json",
        '{"version": 1, "hooks": {"postToolUse": [{"command": ".cursor/hooks/docs-auditor-after-edit.py"}]}}\n',
    )
    _write(root, ".cursor/hooks/docs-auditor-after-edit.py", "# reminder stub\n")
    _write(
        root,
        "packages/desk-intel/src/desk_intel/retune_gate.py",
        "BACKTEST_REQUIRED\nNEWS_DAY\n",
    )
    for team in TEAMS:
        _write(root, f"teams/{team}/HANDOFF.md", f"# {team}\n")


def test_complete_fixture_passes(tmp_path: Path) -> None:
    make_tree(tmp_path)
    result = run_audit(root=tmp_path, write=True)
    assert result.ok, [f.to_dict() for f in result.findings]
    assert (tmp_path / "teams/00_orchestrator/docs/AUDIT_LATEST.md").is_file()


def test_string_cadence_daily_passes(tmp_path: Path) -> None:
    make_tree(tmp_path)
    (tmp_path / "config/workspace.yaml").write_text(
        _workspace_yaml(auditor="string"), encoding="utf-8"
    )
    result = run_audit(root=tmp_path, write=False)
    assert result.ok, [f.to_dict() for f in result.findings]


def test_missing_master_writes_stub_and_fails(tmp_path: Path) -> None:
    make_tree(tmp_path)
    (tmp_path / "docs/MASTER_REQUIREMENTS.md").unlink()
    result = run_audit(root=tmp_path, write=False)
    assert result.ok is False
    assert (tmp_path / "docs/MASTER_REQUIREMENTS.md").is_file()
    text = (tmp_path / "docs/MASTER_REQUIREMENTS.md").read_text(encoding="utf-8")
    assert STUB_MARKER in text
    assert "HANDOFF" in text
    kinds = {f.check for f in result.findings}
    assert "master_requirements_sheet" in kinds


def test_wrong_chain_interval_contradicts(tmp_path: Path) -> None:
    make_tree(tmp_path, chain="1m")
    result = run_audit(root=tmp_path, write=False)
    assert result.ok is False
    row = next(f for f in result.findings if f.check == "chain_interval")
    assert row.severity == "CONTRADICTS"


def test_missing_agent_phrases_stale(tmp_path: Path) -> None:
    make_tree(tmp_path, agent="# AGENT.md\nempty\n")
    result = run_audit(root=tmp_path, write=False)
    assert result.ok is False
    assert any(f.check == "agent_phrases" for f in result.findings)


def test_stale_plan_transcript_count(tmp_path: Path) -> None:
    make_tree(
        tmp_path,
        plan="# PLAN.md\nCollector has run. 33 transcripts verified\n"
        "- [ ] Retry 8 `TRANSCRIPT_PENDING` after timedtext cooldown\n"
        "| 6 | Paper UI | Not started |\n",
    )
    result = run_audit(root=tmp_path, write=False)
    assert result.ok is False
    assert any(f.check == "company_board_drift" for f in result.findings)


def test_sanitize_never_keeps_token_assignment() -> None:
    leaked = "DHAN_ACCESS_TOKEN=abcdefghijklmnopqrstuvwxyz0123456789SECRET"
    out = sanitize(leaked)
    assert "SECRET" not in out
    assert "***" in out


def test_report_contains_no_assignment_secret(tmp_path: Path) -> None:
    make_tree(tmp_path, chain="1m")
    result = run_audit(root=tmp_path, write=True)
    report = (tmp_path / "teams/00_orchestrator/docs/AUDIT_LATEST.md").read_text(
        encoding="utf-8"
    )
    assert "ACCESS_TOKEN=" not in report
    assert result.ok is False


def test_missing_nightly_hook_contradicts(tmp_path: Path) -> None:
    make_tree(tmp_path)
    (tmp_path / "packages/desk-intel/src/desk_intel/__main__.py").write_text(
        "def cmd_nightly():\n    pass\n", encoding="utf-8"
    )
    result = run_audit(root=tmp_path, write=False)
    assert result.ok is False
    row = next(f for f in result.findings if f.check == "nightly_hook")
    assert row.severity == "CONTRADICTS"


def test_weak_cursor_rule_stale(tmp_path: Path) -> None:
    make_tree(tmp_path)
    (tmp_path / ".cursor/rules/docs-auditor.mdc").write_text(
        "---\nalwaysApply: false\nglobs: AGENT.md\n---\npython -m docs_auditor\n",
        encoding="utf-8",
    )
    result = run_audit(root=tmp_path, write=False)
    assert result.ok is False
    row = next(f for f in result.findings if f.check == "cursor_rule")
    assert row.severity == "STALE"


def test_missing_cursor_hook_fails(tmp_path: Path) -> None:
    make_tree(tmp_path)
    (tmp_path / ".cursor/hooks.json").write_text("{}\n", encoding="utf-8")
    result = run_audit(root=tmp_path, write=False)
    assert result.ok is False
    assert any(f.check == "cursor_hook" for f in result.findings)


@pytest.mark.parametrize("rel", ["AGENT.md", "teams/06_backtesting/docs/RETUNE_GATE.md"])
def test_missing_required_file(tmp_path: Path, rel: str) -> None:
    make_tree(tmp_path)
    (tmp_path / rel).unlink()
    result = run_audit(root=tmp_path, write=False)
    assert result.ok is False
    assert any(f.severity == "MISSING" for f in result.findings)
