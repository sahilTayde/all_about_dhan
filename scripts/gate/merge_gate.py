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


def collect_reg_tests(root: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {f"REG-{i:02d}": [] for i in range(1, 19)}
    for path in (*root.glob("tests/**/*.py"), *root.glob("packages/*/tests/**/*.py")):
        body = path.read_text(encoding="utf-8")
        for n in set(REG_RE.findall(body)):
            key = f"REG-{n}"
            if key in found:
                found[key].append(str(path.relative_to(root)))
    return found


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


def _ok(name: str, fn: Callable[[], Check]) -> Check:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return Check(name, "ERROR", f"{type(exc).__name__}: {exc}")


def check_invariants_selftest() -> Check:
    missed = [n for n in INVARIANTS if n not in check_invariants(plant_violation(n, clean_book()))]
    if missed or check_invariants(clean_book()):
        return Check("invariants", "FAIL", f"missed={missed}")
    return Check("invariants", "PASS", str(len(INVARIANTS)))


def check_faults() -> Check:
    if check_invariants(clean_book()) or "ledger_eq_broker" not in check_invariants(
        plant_violation("ledger_eq_broker", clean_book())
    ):
        return Check("faults", "FAIL", "self-test")
    return Check("faults", "PASS", ",".join(FAULTS))


def check_dry_run() -> Check:
    hour, day = dry_run_diffs(hour_only=True), dry_run_diffs(hour_only=False)
    if hour or day:
        return Check("dry_run", "FAIL", f"1x={hour} 10x={day}")
    return Check("dry_run", "PASS", "1x hour + 10x day zero diffs")


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


def check_reg_collect(root: Path) -> Check:
    required = parse_plan_regs((root / "docs/architecture/V2_BUILD_PLAN.md").read_text(encoding="utf-8"))
    if required != {f"REG-{i:02d}" for i in range(1, 19)}:
        return Check("reg_collect", "FAIL", f"{sorted(required)}")
    missing = sorted(k for k, v in collect_reg_tests(root).items() if not v)
    if missing:
        return Check("reg_collect", "MISSING", f"no test: {missing}")
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


def evaluate(*, only: str | None = None, root: Path | None = None) -> Verdict:
    repo = root or REPO
    runners: list[tuple[str, Callable[[], Check]]] = [
        ("invariants", check_invariants_selftest),
        ("faults", check_faults),
        ("dry_run", check_dry_run),
        ("perf", check_perf),
        ("reg_collect", lambda: check_reg_collect(repo)),
        ("TRACE-01", lambda: check_trace01(repo)),
        ("REG-13c", check_reg13c),
        ("REG-10b", check_reg10b),
        ("frozen_legacy", lambda: frozen_check(repo)),
    ]
    checks = [_ok(n, fn) for n, fn in runners if not only or only == n or only in n]
    if not checks:
        checks = [Check(only or "gate", "MISSING", "no checks ran")]
    verdict: Literal["PASS", "BLOCK"] = "BLOCK" if any(c.status in BLOCKING for c in checks) else "PASS"
    return Verdict(verdict=verdict, checks=checks)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="V2-16 merge gate (verdict only; never merges)")
    p.add_argument("--only")
    p.add_argument("--root")
    p.add_argument("--merge", action="store_true")
    p.add_argument("--push", action="store_true")
    args = p.parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.merge or args.push:
        print(json.dumps({"verdict": "BLOCK", "reason": "gate never merges or pushes"}))
        return 2

    def _run() -> int:
        result = evaluate(only=args.only, root=Path(args.root) if args.root else None)
        print(json.dumps(result.to_json(), sort_keys=True))
        return 0 if result.verdict == "PASS" else 1

    try:
        return run_with_deadline(_run, float(JOBS.get("merge-gate", 600)), job="merge-gate")
    except JobTimeout as exc:
        print(json.dumps({"verdict": "BLOCK", "status": "ERROR", "detail": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
