"""Compare requirements docs vs code/config. Local disk only.

Flags: MISSING (file/sheet absent), STALE (docs lag the tree), CONTRADICTS
(docs vs yaml/code disagree). Never interpolates ${ENV}. Never reads `.env`.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional
from zoneinfo import ZoneInfo

import yaml

from docs_auditor.paths import MASTER_REL, STUB_MARKER, find_repo_root, read_text
from docs_auditor.report import render_report
from docs_auditor.sanitize import sanitize

IST = ZoneInfo("Asia/Kolkata")
Severity = Literal["MISSING", "STALE", "CONTRADICTS"]

REQUIRED_FILES = (
    "AGENT.md",
    "PLAN.md",
    "docs/MASTER_REQUIREMENTS.md",
    "docs/HANDOFF.md",
    "config/workspace.yaml",
    "teams/06_backtesting/docs/RETUNE_GATE.md",
    "teams/03_phd_market/cas/RESEARCH.md",
    "teams/09_review/docs/DOCS_AUDITOR.md",
    "teams/04_quant/docs/SIGNAL_STAGING.md",
    "packages/dhan-client/src/dhan_client/execution.py",
    "packages/desk-intel/src/desk_intel/schema.py",
    "teams/00_orchestrator/docs/TASK_DOCS_AUDITOR.md",
    ".cursor/rules/docs-auditor.mdc",
    ".cursor/hooks.json",
)

TEAM_HANDOFFS = tuple(
    f"teams/{folder}/HANDOFF.md"
    for folder in (
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
)

SIGNAL_STATES_DOC = ("WATCH", "EARLY", "CONFIRMED", "IN-PROGRESS", "EXPIRED", "VETOED")
SIGNAL_STATES_CODE = ("WATCH", "EARLY", "CONFIRMED", "IN_PROGRESS", "EXPIRED", "VETOED")

MASTER_SHEET_MARKERS = (
    "Scorecard",
    "Status legend",
    "MASTER_REQUIREMENTS",
)
# A stub pointer is short and lacks the morning scorecard.
MIN_SHEET_CHARS = 2500

STUB_TEXT = """# MASTER_REQUIREMENTS — STUB

**Status:** STUB — manager sheet does not exist yet. This file is a pointer, not a review.

Do **not** treat this as DONE. The Docs Auditor **fails** until orchestrator writes the real morning check sheet.

See:

- [`docs/HANDOFF.md`](HANDOFF.md)
- [`teams/00_orchestrator/docs/HANDOFF_TOMORROW.md`](../teams/00_orchestrator/docs/HANDOFF_TOMORROW.md)
- [`AGENT.md`](../AGENT.md)

**Gate:** still not `RESEARCH_READY_FOR_PROGRAMMING`. No live orders. Education ≠ advice.
"""


@dataclass
class Finding:
    severity: Severity
    check: str
    path: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {k: sanitize(str(v)) for k, v in asdict(self).items()}


@dataclass
class AuditResult:
    ok: bool
    as_of_ist: str
    report_path: str
    findings: list[Finding] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "as_of_ist": self.as_of_ist,
            "report_path": self.report_path,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "checks_run": list(self.checks_run),
            "compliance": "No secrets. Tokens never printed. No web scrape. Education ≠ advice.",
        }

    def console_summary(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        n = len(self.findings)
        counts: dict[str, int] = {}
        for item in self.findings:
            counts[item.severity] = counts.get(item.severity, 0) + 1
        tally = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none"
        return (
            f"docs_auditor {status} ({n} finding{'s' if n != 1 else ''}: {tally}). "
            f"Report: {self.report_path}"
        )


def _now_ist_iso() -> str:
    return datetime.now(IST).replace(microsecond=0).isoformat()


def _find(
    findings: list[Finding],
    severity: Severity,
    check: str,
    path: str,
    detail: str,
) -> None:
    findings.append(
        Finding(
            severity=severity,
            check=check,
            path=path,
            detail=sanitize(detail),
        )
    )


def _load_yaml_no_interp(path: Path) -> dict[str, Any]:
    """Parse yaml as written. Do not expand ${ENV} — that would pull secret values."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return {}
    return raw


def _chain_interval(data: dict[str, Any]) -> Optional[str]:
    desk = data.get("desk_intel") if isinstance(data.get("desk_intel"), dict) else {}
    poll = desk.get("poll") if isinstance(desk.get("poll"), dict) else {}
    raw = poll.get("chain_interval")
    if raw is None:
        return None
    return str(raw).strip().lower()


def _docs_auditor_cadence(data: dict[str, Any]) -> Optional[str]:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), dict) else {}
    raw = jobs.get("docs_auditor")
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.strip().lower()
    if isinstance(raw, dict):
        if raw.get("cadence"):
            return str(raw.get("cadence")).strip().lower()
        if raw.get("enabled") is False:
            return "off"
        return "daily"
    return str(raw).strip().lower()


def _ensure_master_sheet(root: Path, findings: list[Finding]) -> str:
    path = root / MASTER_REL
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(STUB_TEXT, encoding="utf-8")
        _find(
            findings,
            "MISSING",
            "master_requirements_sheet",
            str(MASTER_REL),
            "MASTER_REQUIREMENTS.md was missing. Wrote a stub that points at HANDOFF. "
            "Auditor fails until the manager score sheet exists.",
        )
        return STUB_TEXT
    text = path.read_text(encoding="utf-8", errors="replace")
    is_stub = STUB_MARKER.lower() in text.lower()
    has_sheet = all(m.lower() in text.lower() for m in MASTER_SHEET_MARKERS)
    if is_stub or (not has_sheet) or len(text.strip()) < MIN_SHEET_CHARS:
        _find(
            findings,
            "STALE" if path.is_file() else "MISSING",
            "master_requirements_sheet",
            str(MASTER_REL),
            "File exists but is not the manager score sheet (stub, missing Scorecard/"
            "Status legend, or too short). Auditor fails until orchestrator writes the real sheet.",
        )
    return text


def _check_required_files(root: Path, findings: list[Finding]) -> None:
    for rel in REQUIRED_FILES:
        if rel == str(MASTER_REL):
            continue  # handled with stub write
        if not (root / rel).is_file():
            _find(
                findings,
                "MISSING",
                "required_file",
                rel,
                f"Required file missing: {rel}",
            )


def _check_team_handoffs(root: Path, findings: list[Finding]) -> None:
    for rel in TEAM_HANDOFFS:
        if not (root / rel).is_file():
            _find(
                findings,
                "MISSING",
                "team_handoff",
                rel,
                f"Team HANDOFF.md missing: {rel}",
            )


def _check_agent_phrases(agent: Optional[str], findings: list[Finding]) -> None:
    if agent is None:
        _find(findings, "MISSING", "agent_phrases", "AGENT.md", "AGENT.md missing.")
        return
    checks = [
        ("CAS", ["CAS"]),
        ("IN-PROGRESS", ["IN-PROGRESS"]),
        ("RETUNE", ["RETUNE"]),
        ("Docs Auditor", ["Docs Auditor"]),
    ]
    for label, needles in checks:
        if not all(n in agent for n in needles):
            _find(
                findings,
                "STALE",
                "agent_phrases",
                "AGENT.md",
                f"AGENT.md missing required phrase: {label}",
            )
    # 3m chain — interval and chain must appear near each other or both be present.
    has_3m_chain = bool(
        re.search(r"3m.{0,120}chain|chain.{0,120}3m", agent, flags=re.I | re.S)
    )
    if not has_3m_chain:
        _find(
            findings,
            "STALE",
            "agent_phrases",
            "AGENT.md",
            "AGENT.md must mention the 3m chain poll (e.g. '3m full chain').",
        )
    if "/desk" not in agent or not re.search(r"customer", agent, flags=re.I):
        _find(
            findings,
            "STALE",
            "agent_phrases",
            "AGENT.md",
            "AGENT.md must mention customer vs internal /desk.",
        )


def _check_chain_interval(
    data: dict[str, Any],
    agent: Optional[str],
    master: Optional[str],
    findings: list[Finding],
) -> None:
    interval = _chain_interval(data)
    if interval is None:
        _find(
            findings,
            "MISSING",
            "chain_interval",
            "config/workspace.yaml",
            "desk_intel.poll.chain_interval is missing.",
        )
        return
    if interval != "3m":
        _find(
            findings,
            "CONTRADICTS",
            "chain_interval",
            "config/workspace.yaml",
            f"chain_interval is {interval!r}; requirement is 3m "
            "(full option-chain poll, inside Dhan 1 unique / 3s budget).",
        )
        return
    # Docs that still advertise a 1m full-chain default contradict yaml.
    blob = f"{agent or ''}\n{master or ''}"
    if re.search(r"full (option[- ]?)?chain.{0,40}1m|chain_interval:\s*1m", blob, flags=re.I):
        _find(
            findings,
            "CONTRADICTS",
            "chain_interval",
            "AGENT.md / docs/MASTER_REQUIREMENTS.md",
            "Docs still describe a 1m full-chain default; yaml chain_interval is 3m.",
        )


def _check_retune_gate(root: Path, findings: list[Finding]) -> None:
    rel = "teams/06_backtesting/docs/RETUNE_GATE.md"
    text = read_text(root, rel)
    if text is None:
        return  # required_file already flagged
    for needle in ("BACKTEST_REQUIRED", "NEWS_DAY", "keep current"):
        if needle.lower() not in text.lower() and needle not in text:
            _find(
                findings,
                "STALE",
                "retune_gate",
                rel,
                f"RETUNE_GATE.md missing expected gate language: {needle}",
            )
            break
    nightly = read_text(root, "packages/desk-intel/src/desk_intel/nightly.py") or ""
    retune = read_text(root, "packages/desk-intel/src/desk_intel/retune_gate.py") or ""
    code = nightly + "\n" + retune
    if "BACKTEST_REQUIRED" not in code:
        _find(
            findings,
            "CONTRADICTS",
            "retune_gate",
            "packages/desk-intel/src/desk_intel/nightly.py",
            "RETUNE_GATE.md exists but nightly/retune_gate code does not emit BACKTEST_REQUIRED.",
        )
    if "production_params_written" in nightly and not re.search(
        r"production_params_written.*=.*False", nightly
    ):
        # still ok if the payload hardcodes False
        pass
    if "production_params_written" in nightly and "False" not in nightly:
        _find(
            findings,
            "CONTRADICTS",
            "retune_gate",
            "packages/desk-intel/src/desk_intel/nightly.py",
            "Nightly must keep production_params_written false (no live param write).",
        )


def _check_cas_research(root: Path, data: dict[str, Any], findings: list[Finding]) -> None:
    rel = "teams/03_phd_market/cas/RESEARCH.md"
    text = read_text(root, rel)
    if text is None:
        return
    if "Closing Auction Session" not in text and "closing auction session" not in text.lower():
        _find(
            findings,
            "STALE",
            "cas_research",
            rel,
            "cas/RESEARCH.md must name official CAS = Closing Auction Session.",
        )
    sources = data.get("sources") if isinstance(data.get("sources"), dict) else {}
    cas = sources.get("cas")
    if not isinstance(cas, list) or not cas:
        _find(
            findings,
            "MISSING",
            "cas_research",
            "config/workspace.yaml",
            "sources.cas[] missing while cas/RESEARCH.md exists.",
        )


def _check_signal_states(root: Path, agent: Optional[str], findings: list[Finding]) -> None:
    schema = read_text(root, "packages/desk-intel/src/desk_intel/schema.py") or ""
    staging = read_text(root, "teams/04_quant/docs/SIGNAL_STAGING.md") or ""
    missing_code = [s for s in SIGNAL_STATES_CODE if s not in schema]
    if missing_code:
        _find(
            findings,
            "CONTRADICTS",
            "signal_states",
            "packages/desk-intel/src/desk_intel/schema.py",
            "schema.py missing signal states: " + ", ".join(missing_code),
        )
    missing_docs = [s for s in SIGNAL_STATES_DOC if s not in staging]
    if staging and missing_docs:
        _find(
            findings,
            "STALE",
            "signal_states",
            "teams/04_quant/docs/SIGNAL_STAGING.md",
            "SIGNAL_STAGING.md missing states: " + ", ".join(missing_docs),
        )
    if agent and "IN-PROGRESS" not in agent:
        _find(
            findings,
            "STALE",
            "signal_states",
            "AGENT.md",
            "AGENT.md must list IN-PROGRESS in the staged-signal chain.",
        )


def _check_no_live_orders(root: Path, agent: Optional[str], master: Optional[str], findings: list[Finding]) -> None:
    exe = read_text(root, "packages/dhan-client/src/dhan_client/execution.py") or ""
    if "SafeModeError" not in exe or "refuse" not in exe.lower():
        _find(
            findings,
            "CONTRADICTS",
            "no_live_orders",
            "packages/dhan-client/src/dhan_client/execution.py",
            "ExecutionClient must refuse place_order (SafeModeError). Docs say no live orders.",
        )
    blob = f"{agent or ''}\n{master or ''}"
    if not re.search(r"no live orders", blob, flags=re.I):
        _find(
            findings,
            "STALE",
            "no_live_orders",
            "AGENT.md / docs/MASTER_REQUIREMENTS.md",
            "Requirements must state no live orders.",
        )
    if re.search(r"places live orders|live order placement is enabled", blob, flags=re.I):
        _find(
            findings,
            "CONTRADICTS",
            "no_live_orders",
            "AGENT.md / docs/MASTER_REQUIREMENTS.md",
            "Docs claim live order placement; execution.py must stay refused.",
        )


def _check_jobs_auditor(data: dict[str, Any], findings: list[Finding]) -> None:
    cadence = _docs_auditor_cadence(data)
    if cadence is None:
        _find(
            findings,
            "MISSING",
            "jobs_docs_auditor",
            "config/workspace.yaml",
            "jobs.docs_auditor is missing; requirement is daily.",
        )
        return
    if cadence not in {"daily", "nightly"}:
        _find(
            findings,
            "CONTRADICTS",
            "jobs_docs_auditor",
            "config/workspace.yaml",
            f"jobs.docs_auditor cadence is {cadence!r}; requirement is daily.",
        )


def _check_company_board_drift(
    plan: Optional[str],
    master: Optional[str],
    findings: list[Finding],
) -> None:
    """Do not pretend PLAN.md is current. Flag known drift vs the score sheet."""
    if not plan or not master:
        return
    master_has_45 = bool(re.search(r"TRANSCRIPT_VERIFIED[^\n]*\b45\b", master))
    plan_has_old_count = bool(
        re.search(r"\b33 (transcripts )?verified\b", plan, flags=re.I)
        or "Retry 8 `TRANSCRIPT_PENDING`" in plan
        or "retry 8 `TRANSCRIPT_PENDING`" in plan.lower()
    )
    if master_has_45 and plan_has_old_count:
        _find(
            findings,
            "STALE",
            "company_board_drift",
            "PLAN.md",
            "PLAN.md still cites 33 verified transcripts / retry-8 pending; "
            "MASTER_REQUIREMENTS.md score sheet says TRANSCRIPT_VERIFIED 45.",
        )
    plan_paper_not_started = bool(
        re.search(r"Paper UI\s*\|\s*Not started", plan, flags=re.I)
    )
    master_paper_partial = "Dashboard" in master and "PARTIAL" in master and "mock" in master.lower()
    if plan_paper_not_started and master_paper_partial:
        _find(
            findings,
            "STALE",
            "company_board_drift",
            "PLAN.md",
            "PLAN.md Phase 6 Paper UI is still 'Not started'; "
            "MASTER_REQUIREMENTS.md scores the dashboard as PARTIAL (mock).",
        )


def _check_golden_rule(agent: Optional[str], findings: list[Finding]) -> None:
    if not agent:
        return
    if "no requirement merge" not in agent.lower():
        _find(
            findings,
            "STALE",
            "agent_phrases",
            "AGENT.md",
            "Golden rule missing: no requirement merge without the Docs Auditor.",
        )


def _check_nightly_hook(root: Path, findings: list[Finding]) -> None:
    main = read_text(root, "packages/desk-intel/src/desk_intel/__main__.py") or ""
    jobs_main = read_text(root, "packages/desk-intel/src/jobs/__main__.py") or ""
    if "attach_docs_audit" not in main or "cmd_nightly" not in main:
        _find(
            findings,
            "CONTRADICTS",
            "nightly_hook",
            "packages/desk-intel/src/desk_intel/__main__.py",
            "jobs.docs_auditor is daily but nightly CLI does not call attach_docs_audit.",
        )
    if '"nightly": cmd_nightly' not in main or '"post-market": cmd_nightly' not in main:
        _find(
            findings,
            "CONTRADICTS",
            "nightly_hook",
            "packages/desk-intel/src/desk_intel/__main__.py",
            "desk_intel nightly / post-market must both dispatch to cmd_nightly (auditor last).",
        )
    if "from desk_intel.__main__ import main" not in jobs_main:
        _find(
            findings,
            "CONTRADICTS",
            "nightly_hook",
            "packages/desk-intel/src/jobs/__main__.py",
            "python -m jobs post-market must keep wrapping desk_intel main (auditor at end of nightly).",
        )


def _check_cursor_force(root: Path, findings: list[Finding]) -> None:
    """Agents must see the rule on every chat and get a reminder after requirement edits."""
    rule_rel = ".cursor/rules/docs-auditor.mdc"
    rule = read_text(root, rule_rel) or ""
    if not rule:
        _find(
            findings,
            "MISSING",
            "cursor_rule",
            rule_rel,
            "Cursor rule missing; agents will not be forced to run the Docs Auditor.",
        )
    else:
        if not re.search(r"(?m)^alwaysApply:\s*true\s*$", rule):
            _find(
                findings,
                "STALE",
                "cursor_rule",
                rule_rel,
                "Cursor rule is not alwaysApply: true; glob-only is too weak "
                "(agents miss it unless those files are already in context).",
            )
        if "python -m docs_auditor" not in rule:
            _find(
                findings,
                "STALE",
                "cursor_rule",
                rule_rel,
                "Cursor rule must tell agents to run python -m docs_auditor.",
            )
    hooks_rel = ".cursor/hooks.json"
    hooks = read_text(root, hooks_rel) or ""
    if "docs-auditor" not in hooks and "docs_auditor" not in hooks:
        _find(
            findings,
            "MISSING",
            "cursor_hook",
            hooks_rel,
            "Project hook missing; after requirement-file edits agents are not reminded to run the auditor.",
        )
    script_rel = ".cursor/hooks/docs-auditor-after-edit.py"
    if not (root / script_rel).is_file():
        _find(
            findings,
            "MISSING",
            "cursor_hook",
            script_rel,
            "afterFileEdit/postToolUse reminder script missing.",
        )


def run_audit(
    *,
    root: Optional[Path] = None,
    write: bool = True,
) -> AuditResult:
    repo = Path(root).resolve() if root is not None else find_repo_root()
    findings: list[Finding] = []
    checks_run = [
        "required_files",
        "master_requirements_sheet",
        "team_handoffs",
        "agent_phrases",
        "chain_interval",
        "retune_gate",
        "cas_research",
        "signal_states",
        "no_live_orders",
        "jobs_docs_auditor",
        "nightly_hook",
        "cursor_rule",
        "company_board_drift",
    ]

    _check_required_files(repo, findings)
    master = _ensure_master_sheet(repo, findings)
    _check_team_handoffs(repo, findings)

    agent = read_text(repo, "AGENT.md")
    plan = read_text(repo, "PLAN.md")
    yaml_path = repo / "config" / "workspace.yaml"
    data: dict[str, Any] = {}
    if yaml_path.is_file():
        try:
            data = _load_yaml_no_interp(yaml_path)
        except yaml.YAMLError as exc:
            _find(
                findings,
                "CONTRADICTS",
                "chain_interval",
                "config/workspace.yaml",
                f"workspace.yaml failed to parse: {type(exc).__name__}",
            )

    _check_agent_phrases(agent, findings)
    _check_golden_rule(agent, findings)
    _check_chain_interval(data, agent, master, findings)
    _check_retune_gate(repo, findings)
    _check_cas_research(repo, data, findings)
    _check_signal_states(repo, agent, findings)
    _check_no_live_orders(repo, agent, master, findings)
    _check_jobs_auditor(data, findings)
    _check_nightly_hook(repo, findings)
    _check_cursor_force(repo, findings)
    _check_company_board_drift(plan, master, findings)

    as_of = _now_ist_iso()
    report_rel = "teams/00_orchestrator/docs/AUDIT_LATEST.md"
    result = AuditResult(
        ok=not findings,
        as_of_ist=as_of,
        report_path=report_rel,
        findings=findings,
        checks_run=checks_run,
    )
    if write:
        out = repo / report_rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sanitize(render_report(result)), encoding="utf-8")
    return result
