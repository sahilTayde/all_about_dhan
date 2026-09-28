"""V2-16 merge gate. Fail-closed. Verdict only — never merges or pushes. Paper, no network."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from contracts.clock import IST, SimClock
from contracts.envelope import Envelope
from events.bus import MemoryBus
from runtime.jobs import JOBS, JobTimeout, run_with_deadline
from runtime.kernel import Engine
from runtime.services import wait_ready, write_engine_status
from runtime.sources import EnvelopeSource
from runtime.store import InMemoryLedgerStore
from strategies.params_hash import compute_params_hash

Status = Literal["PASS", "FAIL", "MISSING", "UNKNOWN", "ERROR", "NA"]
BLOCKING = frozenset({"FAIL", "MISSING", "UNKNOWN", "ERROR"})
REPO = Path(__file__).resolve().parents[2]
NIFTY_BASELINE = "63 / -96,190.79"
ALL3_BASELINE = "140 / -27,022.54"
HEADROOM = 2.0
DAY = datetime(2026, 9, 28, 9, 15, tzinfo=IST)
FLAT = datetime(2026, 9, 28, 15, 15, tzinfo=IST)
INVARIANTS = (
    "ledger_eq_broker",
    "fill_has_order",
    "no_dup_order_id",
    "pnl_eq_trades",
    "no_entry_after_cutoff_or_hold",
    "flat_after_flat_by_ist",
    "enter_has_one_risk_decision",
    "available_ts_ge_event_ts",
)
FAULTS = (
    "kill9_commit_before_submit",
    "kill9_fill_before_ledger",
    "redis_down_30s",
    "ws_reconnect_storm",
    "dup_out_of_order",
    "stale_depth_60s",
    "broker_timeout_submit",
    "broker_rejects_exit",
    "ledger_write_failure",
    "corrupt_founder_command",
    "strategy_raises_or_budget",
    "clock_skew",
)
BUDGETS = {
    "risk_check": 0.010,
    "session_replay": 60.0,
    "restart_ready": 60.0,
    "bar_to_decision": 0.100,
}
EXIT_KEYS = (
    "exit_plan",
    "stop",
    "target",
    "time_stops",
    "trail",
    "partials",
    "flat_by_ist",
    "strike_router",
    "catastrophic",
    "structural",
    "atr",
    "grace",
    "signal_flip",
)
ITEM_RE = re.compile(r"^\|\s*\*?\*?(C\d+|A\d+|REG-\d{2})\*?\*?\s*\|")
REG_RE = re.compile(r"(?:REG-|test_reg_)(\d{2})")
CI_JOB_RE = re.compile(r"^  ([a-z][a-z0-9-]*):")
STUB_SOURCES = frozenset({"stub", "grep", "json_hop", "self-test", "plant", "fixture_only", "memory_bus"})
SUCCESS = frozenset({"success"})
InputKind = Literal["absent", "stub", "error", "ok"]


@dataclass
class Check:
    name: str
    status: Status
    detail: str


@dataclass
class Book:
    ledger: dict[str, int] = field(default_factory=dict)
    broker: dict[str, int] = field(default_factory=dict)
    orders: dict[str, str] = field(default_factory=dict)
    fills: list[str] = field(default_factory=list)
    sent: list[str] = field(default_factory=list)
    trades_pnl: float = 0.0
    realised: float = 0.0
    entries: list[tuple[bool, bool]] = field(default_factory=list)
    open_after_flat: bool = False
    enters: list[str] = field(default_factory=list)
    risk: dict[str, int] = field(default_factory=dict)
    envelopes: list[tuple[datetime, datetime]] = field(default_factory=list)


@dataclass
class Verdict:
    verdict: Literal["PASS", "BLOCK"]
    checks: list[Check]

    def to_json(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "checks": [asdict(c) for c in self.checks],
            "nifty_baseline": NIFTY_BASELINE,
            "all3_baseline": ALL3_BASELINE,
            "auto_merge": False,
            "pushed": False,
        }


def clean_book() -> Book:
    t = datetime(2026, 9, 28, 10, 0, tzinfo=IST)
    return Book(
        ledger={"NIFTY-CE": 65},
        broker={"NIFTY-CE": 65},
        orders={"o1": "FILLED"},
        fills=["o1"],
        sent=["o1"],
        trades_pnl=-100.0,
        realised=-100.0,
        entries=[(False, False)],
        enters=["c1"],
        risk={"c1": 1},
        envelopes=[(t, t + timedelta(milliseconds=10))],
    )


def check_invariants(book: Book) -> list[str]:
    bad: list[str] = []
    if book.ledger != book.broker:
        bad.append("ledger_eq_broker")
    if any(book.orders.get(i) not in {"FILLED", "PARTIAL"} for i in book.fills):
        bad.append("fill_has_order")
    if len(book.sent) != len(set(book.sent)):
        bad.append("no_dup_order_id")
    if abs(book.realised - book.trades_pnl) > 1e-9:
        bad.append("pnl_eq_trades")
    if any(after or hold for after, hold in book.entries):
        bad.append("no_entry_after_cutoff_or_hold")
    if book.open_after_flat:
        bad.append("flat_after_flat_by_ist")
    if any(book.risk.get(c, 0) != 1 for c in book.enters):
        bad.append("enter_has_one_risk_decision")
    if any(a < e for e, a in book.envelopes):
        bad.append("available_ts_ge_event_ts")
    return bad


def plant_violation(name: str, book: Book) -> Book:
    plants: dict[str, Callable[[Book], None]] = {
        "ledger_eq_broker": lambda b: b.broker.update({"X": 1}),
        "fill_has_order": lambda b: b.fills.append("ghost"),
        "no_dup_order_id": lambda b: b.sent.extend([b.sent[0] if b.sent else "d", "d"]),
        "pnl_eq_trades": lambda b: setattr(b, "realised", b.trades_pnl + 1),
        "no_entry_after_cutoff_or_hold": lambda b: b.entries.append((True, False)),
        "flat_after_flat_by_ist": lambda b: setattr(b, "open_after_flat", True),
        "enter_has_one_risk_decision": lambda b: b.enters.append("orphan"),
        "available_ts_ge_event_ts": lambda b: b.envelopes.append((FLAT, FLAT - timedelta(seconds=1))),
    }
    plants[name](book)
    return book


def _env(n: int, kind: str, ts: datetime, payload: dict[str, Any]) -> Envelope:
    iso = ts.isoformat()
    return Envelope(
        2,
        kind,
        f"g{n:06d}",
        "gate",
        "fixture",
        iso,
        iso,
        iso,
        "paper",
        f"c{n:04d}",
        None,
        payload,
    )


def fixture_envelopes(*, hour_only: bool) -> list[Envelope]:
    out: list[Envelope] = []
    n = 0
    for h in range(1 if hour_only else 6):
        ts = DAY + timedelta(hours=h, minutes=5)
        cid = f"c{n + 3:04d}"
        for kind, payload in (
            ("MARKET_TICK", {"ltp": 100.0 + h}),
            ("ENTRY_APPROVED", {"action": "ENTER", "correlation_id": cid}),
            ("ORDER_FILLED", {"correlation_id": cid, "qty": 65}),
            ("POSITION_CLOSED", {"correlation_id": cid}),
        ):
            n += 1
            out.append(_env(n, kind, ts + timedelta(seconds=n), payload))
    if not hour_only:
        out.append(_env(n + 1, "POSITION_CLOSED", FLAT, {"flat_by_ist": "15:15"}))
    return out


def _record(envelopes: list[Envelope]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    class H:
        def handle(self, envelope: Envelope) -> None:
            rows.append(
                {
                    "event_type": envelope.event_type,
                    "event_id": envelope.event_id,
                    "payload": envelope.payload,
                }
            )

    Engine(
        EnvelopeSource(list(envelopes)),
        SimClock(datetime.fromisoformat(envelopes[0].available_ts)),
        MemoryBus(),
        [H()],
        InMemoryLedgerStore(),
    ).run()
    return rows


def redis_path(envelopes: list[Envelope]) -> list[dict[str, Any]]:
    return _record([Envelope.from_json(json.dumps(e.to_json())) for e in envelopes])


def dry_run_diffs(*, hour_only: bool) -> list[str]:
    tape = fixture_envelopes(hour_only=hour_only)
    left, right = _record(tape), redis_path(tape)
    if len(left) != len(right):
        return [f"len {len(left)}!={len(right)}"]
    return [f"row {i}" for i, (a, b) in enumerate(zip(left, right, strict=True)) if a != b]


def exit_version_ok(before: dict[str, Any], after: dict[str, Any]) -> bool:
    same = compute_params_hash({k: before.get(k) for k in EXIT_KEYS}) == compute_params_hash(
        {k: after.get(k) for k in EXIT_KEYS}
    )
    return same or str(before.get("version")) != str(after.get("version"))


def _section(text: str, start: str, end: str) -> str:
    i, j = text.find(start), text.find(end)
    if i < 0 or j <= i:
        raise ValueError(start)
    return text[i:j]


def parse_items(text: str) -> set[str]:
    return {m.group(1) for line in text.splitlines() if (m := ITEM_RE.match(line))}


def _row_ticket_and_test(row: str) -> bool:
    cols = [c.strip() for c in row.strip().strip("|").split("|")]
    if len(cols) < 5:
        return False
    tickets, proof = cols[3], cols[4]
    return bool(proof) and ("V2-" in tickets or "V2-" in row or "per REG" in tickets)


def parse_plan_41(text: str) -> dict[str, str]:
    body = _section(text, "### 4.1 Traceability table", "### 4.2")
    return {m.group(1): line for line in body.splitlines() if (m := ITEM_RE.match(line))}


def parse_plan_regs(text: str) -> set[str]:
    return {f"REG-{n}" for n in re.findall(r"REG-(\d{2})", _section(text, "## 3. Legacy bug carry-over", "## 4."))}


def parse_ci_jobs(text: str) -> list[str]:
    jobs: list[str] = []
    in_jobs = False
    for line in text.splitlines():
        if line.startswith("jobs:"):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        match = CI_JOB_RE.match(line)
        if match:
            jobs.append(match.group(1))
    return jobs


def required_ci_jobs(text: str) -> list[str]:
    return [name for name in parse_ci_jobs(text) if name != "gate"]


def collect_reg_tests(root: Path) -> dict[str, list[str]]:
    """Grep-only index. Never sufficient for a PASS."""
    found: dict[str, list[str]] = {f"REG-{i:02d}": [] for i in range(1, 19)}
    for path in (*root.glob("tests/**/*.py"), *root.glob("packages/*/tests/**/*.py")):
        body = path.read_text(encoding="utf-8")
        for n in set(REG_RE.findall(body)):
            key = f"REG-{n}"
            if key in found:
                found[key].append(str(path.relative_to(root)))
    return found


def _is_stub_payload(data: dict[str, Any]) -> bool:
    if data.get("stub") is True:
        return True
    kind = str(data.get("kind", data.get("source", ""))).lower()
    return kind in STUB_SOURCES


def _junit_to_results(path: Path) -> dict[str, Any]:
    tree = ET.parse(path)
    tests: list[dict[str, str]] = []
    for case in tree.iter("testcase"):
        nodeid = f"{case.get('classname', '')}::{case.get('name', '')}"
        if case.find("failure") is not None or case.find("error") is not None:
            outcome = "failed"
        elif case.find("skipped") is not None:
            outcome = "skipped"
        else:
            outcome = "passed"
        tests.append({"nodeid": nodeid, "outcome": outcome})
    return {"tests": tests}


def _load_mapping(value: str | Path | dict[str, Any] | None) -> tuple[InputKind, dict[str, Any]]:
    if value is None:
        return "absent", {}
    if isinstance(value, dict):
        data: Any = value
    else:
        text = str(value).strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                return "error", {"detail": str(exc)}
        else:
            path = Path(text)
            if not path.is_file():
                return "absent", {}
            try:
                data = (
                    _junit_to_results(path) if path.suffix == ".xml" else json.loads(path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError, ET.ParseError) as exc:
                return "error", {"detail": f"{type(exc).__name__}: {exc}"}
    if not isinstance(data, dict):
        return "error", {"detail": "not an object"}
    if _is_stub_payload(data):
        return "stub", data
    return "ok", data


def parse_sha_manifest(path: Path) -> dict[str, str] | Check:
    expected: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            return Check("lock", "UNKNOWN", f"bad line {line!r}")
        expected[parts[1]] = parts[0]
    return expected


def _pytest_passed_regs(data: dict[str, Any]) -> set[str] | None:
    tests = data.get("tests")
    if not isinstance(tests, list):
        if "files" in data or "ids" in data:
            return None
        return set()
    if not tests and ("files" in data or "ids" in data):
        return None
    covered: set[str] = set()
    saw_outcome = False
    for row in tests:
        if not isinstance(row, dict) or "outcome" not in row:
            continue
        saw_outcome = True
        if str(row["outcome"]).lower() != "passed":
            continue
        blob = f"{row.get('nodeid', '')} {row.get('file', '')} {row.get('classname', '')}"
        for n in set(REG_RE.findall(blob)):
            covered.add(f"REG-{n}")
    if not saw_outcome:
        return None
    return covered


def frozen_check(root: Path) -> Check:
    manifest = root / "config" / "legacy_frozen.sha256"
    if not manifest.is_file():
        return Check("frozen_legacy", "MISSING", "manifest absent")
    changed: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            return Check("frozen_legacy", "UNKNOWN", f"bad line {line!r}")
        digest, rel = parts
        path = root / rel
        if not path.is_file():
            return Check("frozen_legacy", "MISSING", rel)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            changed.append(rel)
    note = f"NIFTY {NIFTY_BASELINE}; 3-index {ALL3_BASELINE} must stay identical"
    if changed:
        return Check("frozen_legacy", "FAIL", f"changed {changed}; {note}")
    return Check("frozen_legacy", "PASS", f"unchanged; {note}")


def _p99(xs: list[float]) -> float:
    if not xs:
        raise ValueError("no samples")
    ys = sorted(xs)
    return ys[min(len(ys) - 1, max(0, math.ceil(0.99 * len(ys)) - 1))]


def check_invariants_selftest() -> Check:
    missed = [n for n in INVARIANTS if n not in check_invariants(plant_violation(n, clean_book()))]
    if missed or check_invariants(clean_book()):
        return Check("invariants", "FAIL", f"missed={missed}")
    return Check("invariants", "PASS", str(len(INVARIANTS)))


def check_ci_conclusions(required: list[str], kind: InputKind, data: dict[str, Any]) -> Check:
    if kind == "absent":
        return Check("ci_conclusions", "MISSING", "file absent")
    if kind == "stub":
        return Check("ci_conclusions", "MISSING", "stub")
    if kind == "error":
        return Check("ci_conclusions", "ERROR", str(data.get("detail", "invalid")))
    if not required:
        return Check("ci_conclusions", "MISSING", "ci.yml jobs absent")
    missing = [name for name in required if name not in data]
    if missing:
        return Check("ci_conclusions", "MISSING", f"missing jobs: {missing}")
    bad = [name for name in required if str(data[name]).lower() not in SUCCESS]
    if bad:
        return Check("ci_conclusions", "FAIL", f"not success: { {n: data[n] for n in bad} }")
    return Check("ci_conclusions", "PASS", ",".join(required))


def check_named_job(name: str, required: list[str], kind: InputKind, data: dict[str, Any]) -> Check:
    if kind == "absent":
        return Check(name, "MISSING", "ci conclusions absent")
    if kind == "stub":
        return Check(name, "MISSING", "stub")
    if kind == "error":
        return Check(name, "ERROR", str(data.get("detail", "invalid")))
    if name not in required:
        return Check(name, "MISSING", "job not in ci.yml")
    if name not in data:
        return Check(name, "MISSING", "job missing")
    if str(data[name]).lower() not in SUCCESS:
        return Check(name, "FAIL", str(data[name]))
    return Check(name, "PASS", str(data[name]))


def check_lock(root: Path) -> Check:
    manifest = root / "config" / "requirements_lock.sha256"
    files = sorted(p for p in root.glob("requirements/*.txt") if p.is_file())
    if not manifest.is_file():
        return Check("lock", "MISSING", "manifest absent")
    parsed = parse_sha_manifest(manifest)
    if isinstance(parsed, Check):
        return parsed
    if not parsed:
        return Check("lock", "MISSING", "empty manifest")
    changed: list[str] = []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if rel not in parsed:
            changed.append(f"unlisted {rel}")
        elif parsed[rel] != digest:
            changed.append(rel)
    for rel in parsed:
        if not (root / rel).is_file():
            changed.append(f"missing {rel}")
    if changed:
        return Check("lock", "FAIL", f"changed {changed}")
    return Check("lock", "PASS", f"{len(parsed)} files")


def _real_fault_proof(proof: Any, faults_job_ok: bool) -> bool:
    if not isinstance(proof, dict) or not faults_job_ok:
        return False
    source = str(proof.get("source", "")).lower()
    if source in STUB_SOURCES or source not in {"pytest", "ci"}:
        return False
    return bool(str(proof.get("nodeid", "")).strip())


def check_fault_matrix(kind: InputKind, data: dict[str, Any], ci: dict[str, Any] | None) -> list[Check]:
    if kind == "absent":
        return [Check("faults", "MISSING", "fault-rows absent")]
    if kind == "stub":
        return [Check("faults", "MISSING", "stub")]
    if kind == "error":
        return [Check("faults", "ERROR", str(data.get("detail", "invalid")))]
    rows_raw = data.get("rows", data)
    if not isinstance(rows_raw, dict):
        return [Check("faults", "MISSING", "stub")]
    faults_ok = ci is not None and str(ci.get("faults", "")).lower() in SUCCESS
    rows: list[Check] = []
    for name in FAULTS:
        if _real_fault_proof(rows_raw.get(name), faults_ok):
            rows.append(Check(f"faults.{name}", "PASS", "exercised"))
        else:
            rows.append(Check(f"faults.{name}", "MISSING", "not exercised"))
    if any(item.status in BLOCKING for item in rows):
        return [Check("faults", "MISSING", "rows not exercised"), *rows]
    return [Check("faults", "PASS", ",".join(FAULTS)), *rows]


def check_lookahead(
    required: list[str],
    ci_kind: InputKind,
    ci_data: dict[str, Any],
    report_kind: InputKind,
    report: dict[str, Any],
) -> Check:
    if report_kind == "stub":
        return Check("no-lookahead", "MISSING", "stub")
    if report_kind == "error":
        return Check("no-lookahead", "ERROR", str(report.get("detail", "invalid")))
    if ci_kind == "ok" and str(ci_data.get("no-lookahead", "")).lower() in SUCCESS:
        return Check("no-lookahead", "PASS", "ci")
    if "no-lookahead" in required:
        if ci_kind == "absent":
            return Check("no-lookahead", "MISSING", "ci conclusions absent")
        if ci_kind == "stub":
            return Check("no-lookahead", "MISSING", "stub")
        if "no-lookahead" not in ci_data:
            return Check("no-lookahead", "MISSING", "job missing")
        return Check("no-lookahead", "FAIL", str(ci_data.get("no-lookahead")))
    if report_kind == "ok" and str(report.get("status", "")).lower() == "passed":
        return Check("no-lookahead", "PASS", "report")
    return Check("no-lookahead", "MISSING", "not run")


def check_compose(kind: InputKind, data: dict[str, Any]) -> Check:
    if kind == "absent":
        return Check("redis_compose", "MISSING", "compose report absent; JSON hop is not Redis")
    if kind == "stub":
        return Check("redis_compose", "MISSING", "stub; JSON hop is not Redis compose")
    if kind == "error":
        return Check("redis_compose", "ERROR", str(data.get("detail", "invalid")))
    kind_name = str(data.get("kind", "")).lower()
    if kind_name in STUB_SOURCES or data.get("redis") is not True:
        return Check("redis_compose", "MISSING", "not a redis compose report")
    if kind_name != "redis_compose":
        return Check("redis_compose", "MISSING", "not a redis compose report")
    hour = data.get("hour_diffs")
    day = data.get("day_diffs")
    if hour == [] and day == []:
        return Check("redis_compose", "PASS", "1x hour + 10x day")
    return Check("redis_compose", "FAIL", f"1x={hour} 10x={day}")


def check_perf() -> Check:
    from risk_engine import (  # type: ignore[import-untyped]
        RiskEngine,
        RiskState,
        TradeIntent,
    )

    now = datetime(2026, 9, 28, 10, 0, tzinfo=IST)
    risk, intent = (
        RiskEngine(),
        TradeIntent("NIFTY 24400 CE", "BUY", 1, 65, decision_price=100.0, stop_loss=90.0),
    )
    samples = []
    for _ in range(40):
        t0 = time.perf_counter()
        risk.check_entry(intent, now=now, state=RiskState())
        samples.append(time.perf_counter() - t0)
    tape = fixture_envelopes(hour_only=False)
    t0 = time.perf_counter()
    _record(tape)
    replay = time.perf_counter() - t0
    with tempfile.TemporaryDirectory() as raw:
        t0 = time.perf_counter()
        write_engine_status(Path(raw), SimClock(now))
        if not wait_ready(Path(raw), timeout_s=2.0):
            return Check("perf", "FAIL", "READY missing")
        ready = time.perf_counter() - t0
    measured = {
        "risk_check": _p99(samples),
        "session_replay": replay,
        "restart_ready": ready,
        "bar_to_decision": replay / max(1, len(tape)),
    }
    over = [f"{k}={v:.6f}>{BUDGETS[k] * HEADROOM}" for k, v in measured.items() if v > BUDGETS[k] * HEADROOM]
    if over:
        return Check("perf", "FAIL", "; ".join(over))
    return Check("perf", "PASS", json.dumps(measured, sort_keys=True))


def check_reg_collect(root: Path, kind: InputKind, data: dict[str, Any], ci: dict[str, Any] | None) -> Check:
    required = parse_plan_regs((root / "docs/architecture/V2_BUILD_PLAN.md").read_text(encoding="utf-8"))
    need = {f"REG-{i:02d}" for i in range(1, 19)}
    if required != need:
        return Check("reg_collect", "FAIL", f"{sorted(required)}")
    if ci is not None and "regression" in ci and str(ci["regression"]).lower() not in SUCCESS:
        return Check("reg_collect", "FAIL", f"regression job {ci['regression']}")
    if kind == "absent":
        return Check("reg_collect", "MISSING", "pytest results absent; grep-only is not evidence")
    if kind == "stub":
        return Check("reg_collect", "MISSING", "stub")
    if kind == "error":
        return Check("reg_collect", "ERROR", str(data.get("detail", "invalid")))
    covered = _pytest_passed_regs(data)
    if covered is None:
        return Check("reg_collect", "MISSING", "grep-only or no outcomes")
    missing = sorted(need - covered)
    if missing:
        return Check("reg_collect", "MISSING", f"no passed test: {missing}")
    return Check("reg_collect", "PASS", "REG-01..18")


def check_trace01(root: Path) -> Check:
    log_items = parse_items((root / "docs/founder/FOUNDER_COMMENTS_LOG.md").read_text(encoding="utf-8"))
    plan = (root / "docs/architecture/V2_BUILD_PLAN.md").read_text(encoding="utf-8")
    rows, regs = parse_plan_41(plan), parse_plan_regs(plan)
    need = log_items | regs
    missing = sorted(i for i in need if i not in rows or not _row_ticket_and_test(rows[i]))
    if missing:
        return Check("TRACE-01", "FAIL", f"{missing}")
    return Check("TRACE-01", "PASS", str(len(need)))


def check_reg13c() -> Check:
    before = {"version": "1.0.0", "exit_plan": {"catastrophic": {"max_loss": 30000}}}
    after = {"version": "1.0.0", "exit_plan": {"catastrophic": {"max_loss": 1}}}
    if exit_version_ok(before, after) or not exit_version_ok(before, {**after, "version": "1.1.0"}):
        return Check("REG-13c", "FAIL", "fixture")
    return Check("REG-13c", "PASS", "no-bump fails")


def check_reg10b() -> Check:
    if any(n not in JOBS or JOBS[n] <= 0 for n in ("merge-gate", "perf")) or any(t <= 0 for t in JOBS.values()):
        return Check("REG-10b", "MISSING", str(sorted(JOBS)))
    return Check("REG-10b", "PASS", str(sorted(JOBS)))


def _run_check(name: str, fn: Callable[[], Check | list[Check]]) -> list[Check]:
    try:
        got = fn()
    except Exception as exc:  # noqa: BLE001
        return [Check(name, "ERROR", f"{type(exc).__name__}: {exc}")]
    return got if isinstance(got, list) else [got]


def evaluate(
    *,
    only: str | None = None,
    root: Path | None = None,
    ci_conclusions: str | Path | dict[str, Any] | None = None,
    pytest_results: str | Path | dict[str, Any] | None = None,
    fault_rows: str | Path | dict[str, Any] | None = None,
    compose_report: str | Path | dict[str, Any] | None = None,
    lookahead_report: str | Path | dict[str, Any] | None = None,
) -> Verdict:
    repo = root or REPO
    ci_kind, ci_data = _load_mapping(ci_conclusions)
    py_kind, py_data = _load_mapping(pytest_results)
    fr_kind, fr_data = _load_mapping(fault_rows)
    co_kind, co_data = _load_mapping(compose_report)
    la_kind, la_data = _load_mapping(lookahead_report)
    ci_yml = repo / ".github/workflows/ci.yml"
    jobs = required_ci_jobs(ci_yml.read_text(encoding="utf-8") if ci_yml.is_file() else "")
    ci_dict = ci_data if ci_kind == "ok" else None
    runners: list[tuple[str, Callable[[], Check | list[Check]]]] = [
        ("ci_conclusions", lambda: check_ci_conclusions(jobs, ci_kind, ci_data)),
        ("lock", lambda: check_lock(repo)),
        ("golden-replay", lambda: check_named_job("golden-replay", jobs, ci_kind, ci_data)),
        ("determinism", lambda: check_named_job("determinism", jobs, ci_kind, ci_data)),
        ("reg_collect", lambda: check_reg_collect(repo, py_kind, py_data, ci_dict)),
        ("faults", lambda: check_fault_matrix(fr_kind, fr_data, ci_dict)),
        ("no-lookahead", lambda: check_lookahead(jobs, ci_kind, ci_data, la_kind, la_data)),
        ("redis_compose", lambda: check_compose(co_kind, co_data)),
        ("invariants", check_invariants_selftest),
        ("perf", check_perf),
        ("TRACE-01", lambda: check_trace01(repo)),
        ("REG-13c", check_reg13c),
        ("REG-10b", check_reg10b),
        ("frozen_legacy", lambda: frozen_check(repo)),
    ]
    checks: list[Check] = []
    for name, fn in runners:
        if only and only != name and only not in name:
            continue
        checks.extend(_run_check(name, fn))
    if not checks:
        checks = [Check(only or "gate", "MISSING", "no checks ran")]
    verdict: Literal["PASS", "BLOCK"] = "BLOCK" if any(c.status in BLOCKING for c in checks) else "PASS"
    return Verdict(verdict=verdict, checks=checks)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="V2-16 merge gate (verdict only; never merges)")
    p.add_argument("--only")
    p.add_argument("--root")
    p.add_argument("--ci-conclusions")
    p.add_argument("--pytest-results")
    p.add_argument("--fault-rows")
    p.add_argument("--compose-report")
    p.add_argument("--lookahead-report")
    p.add_argument("--merge", action="store_true")
    p.add_argument("--push", action="store_true")
    args = p.parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.merge or args.push:
        print(json.dumps({"verdict": "BLOCK", "reason": "gate never merges or pushes"}))
        return 2

    def _run() -> int:
        result = evaluate(
            only=args.only,
            root=Path(args.root) if args.root else None,
            ci_conclusions=args.ci_conclusions,
            pytest_results=args.pytest_results,
            fault_rows=args.fault_rows,
            compose_report=args.compose_report,
            lookahead_report=args.lookahead_report,
        )
        print(json.dumps(result.to_json(), sort_keys=True))
        return 0 if result.verdict == "PASS" else 1

    try:
        return run_with_deadline(_run, float(JOBS.get("merge-gate", 600)), job="merge-gate")
    except JobTimeout as exc:
        print(json.dumps({"verdict": "BLOCK", "status": "ERROR", "detail": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
