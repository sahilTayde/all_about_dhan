"""Versioned, idempotent PAPER ledger contracts and persistence.

This module is deliberately broker-independent.  It records signals, simulated
paper outcomes, customer declarations, fee assessments, and reconciliation
events; it never submits an order or treats a paper mark as a fill.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

CONTRACT_VERSION = "paper-ledger.v1"
CustomerActionKind = Literal["TOOK", "SKIPPED", "UNKNOWN", "CORRECTED"]
FeeStatus = Literal["KNOWN", "PENDING", "UNKNOWN"]


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def stable_event_key(event_type: str, identity: dict[str, Any]) -> str:
    """Return a stable key for replay-safe append-only writes."""
    raw = f"{CONTRACT_VERSION}|{event_type}|{_json(identity)}".encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class Provenance:
    source: str
    layer: str = "HYPOTHESIS"
    observed_at_ist: str = ""
    freshness_seconds: Optional[int] = None
    freshness_status: str = "UNKNOWN"
    data_gaps: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SignalRecord:
    signal_id: str
    underlying: str
    lean: str
    stage: str
    as_of_ist: str
    strategy_or_mix_id: str
    provenance: Provenance
    contract_version: str = CONTRACT_VERSION
    vetoed: bool = False
    reasons: list[str] = field(default_factory=list)
    vetoes: list[str] = field(default_factory=list)
    top_veto_reasons: list[str] = field(default_factory=list)
    session_kind: str = "NORMAL"


@dataclass(frozen=True)
class CandidateAuditRecord:
    observation_id: str
    candidate_id: str
    strategy_or_mix_id: str
    underlying: str
    timeframe: str
    source: str
    provenance: dict[str, Any]
    as_of_ist: str
    freshness: dict[str, Any]
    raw_lean: str
    final_lean: str
    outcome: str
    vetoes: list[str] = field(default_factory=list)
    confidence_components: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    execution: str = "refused"
    data_gaps: list[str] = field(default_factory=list)
    status: str = "UNVALIDATED"
    promote: bool = False


@dataclass(frozen=True)
class PaperTrade:
    trade_id: str
    signal_id: str
    underlying: str
    side: str
    status: str
    quantity_lots: Optional[int]
    entry: Optional[float]
    exit: Optional[float]
    realized_pnl: Optional[float]
    shadow: bool
    as_of_ist: str
    provenance: Provenance
    contract_version: str = CONTRACT_VERSION


@dataclass(frozen=True)
class CustomerAction:
    signal_id: str
    action: CustomerActionKind
    recorded_at_ist: str
    source: str = "customer"
    correction_of: Optional[str] = None
    lots: Optional[int] = None
    reported_pnl: Optional[float] = None
    contract_version: str = CONTRACT_VERSION


@dataclass(frozen=True)
class FeeAssessment:
    trade_id: str
    gross_pnl: Optional[float]
    gross_costs: Optional[float]
    success_commission: Optional[float]
    external_commission_owner: str
    external_commission_note: str
    service_charge_per_lot: Optional[float]
    service_charge_total: Optional[float]
    statutory_components: Optional[float]
    customer_net_profit: Optional[float]
    status: FeeStatus
    unresolved: list[str] = field(default_factory=list)
    contract_version: str = CONTRACT_VERSION
    assessed_at_ist: str = ""


@dataclass(frozen=True)
class EODReconciliation:
    day: str
    signal_count: int
    paper_trade_count: int
    customer_action_count: int
    corrected_count: int
    fee_status: FeeStatus
    unresolved: list[str] = field(default_factory=list)
    generated_at_ist: str = ""
    contract_version: str = CONTRACT_VERSION
    action_counts: dict[str, int] = field(default_factory=dict)
    gross_pnl_total: Optional[float] = None
    gross_costs_total: Optional[float] = None
    commission_total: Optional[float] = None
    customer_net_total: Optional[float] = None
    duplicate_event_count: int = 0
    replayed_event_count: int = 0
    mirror_event_count: int = 0
    metadata: dict[str, Any] = field(
        default_factory=lambda: {"mode": "PAPER", "promote": "NO_PROMOTE"}
    )


def assess_fees(
    *,
    trade_id: str,
    gross_pnl: Optional[float],
    gross_costs: Optional[float],
    lots: Optional[int],
    service_charge_per_lot: Optional[float] = None,
    statutory_components: Optional[float] = None,
    shadow: bool = False,
) -> FeeAssessment:
    """Assess customer fees without silently converting unknown costs to zero.

    The separate company API owns the success commission.  This repository
    records that ownership for downstream integration but never calculates or
    charges it.  Known gross P/L, broker charges, statutory components, and
    configured service charges are the only inputs to customer net P/L.
    """
    unresolved: list[str] = []
    if gross_pnl is None:
        unresolved.append("gross_pnl")
    if gross_costs is None:
        unresolved.append("gross_costs")
    base_profit = None
    if gross_pnl is not None and gross_costs is not None:
        base_profit = float(gross_pnl) - float(gross_costs)
    service_total = None
    if service_charge_per_lot is None:
        unresolved.append("service_charge_per_lot")
    elif lots is None:
        unresolved.append("lots")
    else:
        service_total = float(service_charge_per_lot) * int(lots)
    if statutory_components is None:
        unresolved.append("statutory_components")
    customer_net_profit = None
    if base_profit is not None and service_total is not None and statutory_components is not None:
        customer_net_profit = (
            base_profit - service_total - float(statutory_components)
        )
    status: FeeStatus = (
        "UNKNOWN"
        if any(item in unresolved for item in ("gross_pnl", "gross_costs", "lots"))
        else "PENDING"
        if unresolved
        else "KNOWN"
    )
    return FeeAssessment(
        trade_id=trade_id,
        gross_pnl=gross_pnl,
        gross_costs=gross_costs,
        success_commission=None,
        external_commission_owner="separate_company_api",
        external_commission_note=(
            "Separate company API is authoritative for the 5% commission; "
            "this PAPER ledger does not calculate or charge it."
        ),
        service_charge_per_lot=service_charge_per_lot,
        service_charge_total=service_total,
        statutory_components=statutory_components,
        customer_net_profit=customer_net_profit,
        status=status,
        unresolved=unresolved,
    )


class PaperLedger:
    """Append-only SQLite event store with a JSONL audit mirror."""

    def __init__(self, sqlite_path: Path, jsonl_path: Optional[Path] = None) -> None:
        self.sqlite_path = sqlite_path
        self.jsonl_path = jsonl_path
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ledger_events (
                  event_key TEXT PRIMARY KEY,
                  event_type TEXT NOT NULL,
                  contract_version TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ledger_events_type
                  ON ledger_events(event_type);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.sqlite_path))
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def append(self, event_type: str, payload: dict[str, Any], identity: dict[str, Any]) -> bool:
        key = stable_event_key(event_type, identity)
        row = {
            "contract_version": CONTRACT_VERSION,
            "event_key": key,
            "event_type": event_type,
            **payload,
        }
        created = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT OR IGNORE INTO ledger_events
                   (event_key, event_type, contract_version, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (key, event_type, CONTRACT_VERSION, _json(row), created),
            )
        inserted = cur.rowcount == 1
        if inserted and self.jsonl_path is not None:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with self.jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(_json(row) + "\n")
        return inserted

    def replay_jsonl(self) -> int:
        """Replay the JSONL mirror into SQLite without writing mirror rows."""
        if self.jsonl_path is None or not self.jsonl_path.exists():
            return 0
        replayed = 0
        with self.jsonl_path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                key = str(row["event_key"])
                with self._connect() as conn:
                    inserted = conn.execute(
                        """INSERT OR IGNORE INTO ledger_events
                           (event_key, event_type, contract_version,
                            payload_json, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            key,
                            str(row["event_type"]),
                            str(row.get("contract_version", CONTRACT_VERSION)),
                            _json(row),
                            str(row.get("created_at", "")),
                        ),
                    ).rowcount == 1
                replayed += int(inserted)
        return replayed

    def append_contract(self, event_type: str, value: Any, identity: dict[str, Any]) -> bool:
        return self.append(event_type, asdict(value), identity)

    def record_customer_action(self, action: CustomerAction) -> bool:
        """Append a customer declaration; corrections remain separate events."""
        return self.append_contract(
            "CUSTOMER_ACTION",
            action,
            {
                "signal_id": action.signal_id,
                "action": action.action,
                "correction_of": action.correction_of,
                "recorded_at_ist": action.recorded_at_ist,
            },
        )

    def record_fee_assessment(self, assessment: FeeAssessment) -> bool:
        return self.append_contract(
            "FEE_ASSESSMENT", assessment, {"trade_id": assessment.trade_id}
        )

    def record_candidate_observation(self, observation: CandidateAuditRecord) -> bool:
        """Append a candidate observation without replacing aggregate signals."""
        return self.append_contract(
            "CANDIDATE_OBSERVATION",
            observation,
            {"observation_id": observation.observation_id},
        )

    def reconcile(self, day: str) -> EODReconciliation:
        rows = self.events()
        day_rows = [
            row
            for row in rows
            if str(row.get("as_of_ist") or row.get("recorded_at_ist") or "").startswith(day)
        ]
        actions = [row for row in day_rows if row.get("event_type") == "CUSTOMER_ACTION"]
        fees = [
            row
            for row in rows
            if row.get("event_type") == "FEE_ASSESSMENT"
            and (
                str(row.get("assessed_at_ist") or "").startswith(day)
                or not row.get("assessed_at_ist")
            )
        ]
        statuses = {str(row.get("status")) for row in fees}
        fee_status: FeeStatus = (
            "UNKNOWN"
            if not fees or "UNKNOWN" in statuses
            else "PENDING"
            if "PENDING" in statuses
            else "KNOWN"
        )
        def total(field_name: str) -> Optional[float]:
            values = [row.get(field_name) for row in fees if row.get(field_name) is not None]
            return float(sum(float(value) for value in values)) if values else None

        duplicate_count, mirror_events = self._mirror_stats()
        unresolved = sorted(
            {
                str(item)
                for row in fees
                for item in (row.get("unresolved") or [])
            }
        )
        action_counts = dict(
            sorted(Counter(str(row.get("action")) for row in actions).items())
        )
        return EODReconciliation(
            day=day,
            signal_count=sum(row.get("event_type") == "SIGNAL" for row in day_rows),
            paper_trade_count=sum(
                row.get("event_type") in ("PAPER_TRADE", "SHADOW_TRADE")
                for row in day_rows
            ),
            customer_action_count=len(actions),
            corrected_count=sum(row.get("action") == "CORRECTED" for row in actions),
            fee_status=fee_status,
            unresolved=unresolved,
            action_counts=action_counts,
            gross_pnl_total=total("gross_pnl"),
            gross_costs_total=total("gross_costs"),
            commission_total=total("success_commission"),
            customer_net_total=total("customer_net_profit"),
            duplicate_event_count=duplicate_count,
            replayed_event_count=0,
            mirror_event_count=mirror_events,
            metadata={"mode": "PAPER", "promote": "NO_PROMOTE"},
        )

    def export_eod(self, day: str, output_path: Optional[Path] = None) -> dict[str, Any]:
        """Return and optionally write a stable, fixture-only EOD export."""
        export = asdict(self.reconcile(day))
        candidate_rows = [
            row
            for row in self.events("CANDIDATE_OBSERVATION")
            if str(row.get("as_of_ist") or "").startswith(day)
        ]
        outcomes = Counter(str(row.get("outcome")) for row in candidate_rows)
        export["candidate_audit"] = {
            "observation_count": len(candidate_rows),
            "candidate_ids": sorted(
                {str(row.get("candidate_id")) for row in candidate_rows}
            ),
            "outcome_counts": dict(sorted(outcomes.items())),
            "marks_available": any(
                row.get("outcome") in {"ACHIEVED", "STOPPED", "INVALIDATED", "LOST"}
                for row in candidate_rows
            ),
            "note": (
                "Candidate observations are PAPER audit data. Missing marks remain "
                "DATA_INSUFFICIENT; no P/L or outcome is fabricated."
            ),
        }
        export["metadata"] = {
            "mode": "PAPER",
            "promote": "NO_PROMOTE",
            "orders": "REFUSED",
            "customer_actions_are_declarations": True,
            "replay_idempotent": True,
        }
        encoded = json.dumps(export, sort_keys=True, separators=(",", ":"), default=str)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(encoded + "\n", encoding="utf-8")
        return json.loads(encoded)

    def _mirror_stats(self) -> tuple[int, int]:
        if self.jsonl_path is None or not self.jsonl_path.exists():
            return 0, 0
        keys: list[str] = []
        with self.jsonl_path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    keys.append(str(json.loads(line)["event_key"]))
        counts = Counter(keys)
        return sum(max(count - 1, 0) for count in counts.values()), len(keys)

    def events(self, event_type: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM ledger_events"
        params: tuple[Any, ...] = ()
        if event_type:
            query += " WHERE event_type = ?"
            params = (event_type,)
        query += " ORDER BY created_at, event_key"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [json.loads(row[0]) for row in rows]
