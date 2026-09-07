from pathlib import Path

from trading_agents_india.paper_ledger import (
    CustomerAction,
    PaperLedger,
    PaperTrade,
    Provenance,
    SignalRecord,
    assess_fees,
)
from trading_agents_india.paper_fixture import PaperFixtureAdapter


def _signal() -> SignalRecord:
    return SignalRecord(
        signal_id="2026-09-04:1:NIFTY",
        underlying="NIFTY",
        lean="BUY_CE",
        stage="EARLY",
        as_of_ist="2026-09-04T11:00:00+05:30",
        strategy_or_mix_id="MIX-DEFAULT-BUY",
        provenance=Provenance(
            source="fixture", layer="HYPOTHESIS", freshness_status="FIXTURE"
        ),
    )


def test_fee_semantics_keep_unknown_components_pending() -> None:
    fee = assess_fees(
        trade_id="t1", gross_pnl=1000, gross_costs=100, lots=1
    )
    assert fee.success_commission is None
    assert fee.external_commission_owner == "separate_company_api"
    assert "does not calculate or charge" in fee.external_commission_note
    assert fee.customer_net_profit is None
    assert fee.status == "PENDING"
    assert "service_charge_per_lot" in fee.unresolved
    assert "statutory_components" in fee.unresolved


def test_fee_semantics_mark_unknown_profit_as_unknown() -> None:
    fee = assess_fees(
        trade_id="unknown",
        gross_pnl=None,
        gross_costs=None,
        lots=1,
        service_charge_per_lot=10,
        statutory_components=5,
    )
    assert fee.status == "UNKNOWN"
    assert fee.success_commission is None
    assert fee.customer_net_profit is None


def test_fee_known_uses_only_known_configured_costs() -> None:
    fee = assess_fees(
        trade_id="t1",
        gross_pnl=1000,
        gross_costs=100,
        lots=2,
        service_charge_per_lot=10,
        statutory_components=5,
    )
    assert fee.success_commission is None
    assert fee.customer_net_profit == 875.0
    shadow = assess_fees(
        trade_id="shadow",
        gross_pnl=1000,
        gross_costs=100,
        lots=1,
        service_charge_per_lot=0,
        statutory_components=0,
        shadow=True,
    )
    assert shadow.success_commission is None
    assert shadow.customer_net_profit == 900.0


def test_append_is_idempotent_across_restart(tmp_path: Path) -> None:
    db = tmp_path / "ledger.sqlite"
    jsonl = tmp_path / "ledger.jsonl"
    first = PaperLedger(db, jsonl)
    assert first.append_contract("SIGNAL", _signal(), {"signal_id": _signal().signal_id})
    assert not first.append_contract(
        "SIGNAL", _signal(), {"signal_id": _signal().signal_id}
    )
    second = PaperLedger(db, jsonl)
    assert len(second.events("SIGNAL")) == 1
    assert len(jsonl.read_text().splitlines()) == 1


def test_customer_correction_and_shadow_reconciliation(tmp_path: Path) -> None:
    ledger = PaperLedger(tmp_path / "ledger.sqlite")
    signal = _signal()
    ledger.append_contract("SIGNAL", signal, {"signal_id": signal.signal_id})
    trade = PaperTrade(
        trade_id="2026-09-04:1:NIFTY:shadow",
        signal_id=signal.signal_id,
        underlying="NIFTY",
        side="BUY_CE",
        status="SHADOW_SKIPPED",
        quantity_lots=None,
        entry=None,
        exit=None,
        realized_pnl=None,
        shadow=True,
        as_of_ist=signal.as_of_ist,
        provenance=signal.provenance,
    )
    ledger.append_contract("SHADOW_TRADE", trade, {"trade_id": trade.trade_id})
    assert ledger.record_customer_action(
        CustomerAction(
            signal_id=signal.signal_id,
            action="SKIPPED",
            recorded_at_ist=signal.as_of_ist,
        )
    )
    assert ledger.record_customer_action(
        CustomerAction(
            signal_id=signal.signal_id,
            action="CORRECTED",
            correction_of=signal.signal_id,
            recorded_at_ist=signal.as_of_ist,
        )
    )
    recon = ledger.reconcile("2026-09-04")
    assert recon.signal_count == 1
    assert recon.paper_trade_count == 1
    assert recon.corrected_count == 1


def test_customer_actions_are_append_only_and_idempotent(tmp_path: Path) -> None:
    ledger = PaperLedger(tmp_path / "ledger.sqlite")
    action = CustomerAction(
        signal_id="s1",
        action="TOOK",
        recorded_at_ist="2026-09-04T11:00:00+05:30",
        lots=2,
        reported_pnl=100.0,
    )
    assert ledger.record_customer_action(action)
    assert not ledger.record_customer_action(action)
    for kind in ("SKIPPED", "UNKNOWN", "CORRECTED"):
        assert ledger.record_customer_action(
            CustomerAction(
                signal_id="s1",
                action=kind,
                recorded_at_ist=f"2026-09-04T11:00:0{len(kind)}+05:30",
                correction_of="s1" if kind == "CORRECTED" else None,
            )
        )
    assert [row["action"] for row in ledger.events("CUSTOMER_ACTION")] == [
        "TOOK",
        "SKIPPED",
        "UNKNOWN",
        "CORRECTED",
    ]


def test_fixture_adapter_replays_jsonl_after_sqlite_reopen(tmp_path: Path) -> None:
    db = tmp_path / "ledger.sqlite"
    mirror = tmp_path / "ledger.jsonl"
    first = PaperLedger(db, mirror)
    adapter = PaperFixtureAdapter(first)
    assert adapter.record_action(
        signal_id="s-replay",
        action="TOOK",
        recorded_at_ist="2026-09-04T11:00:00+05:30",
        lots=1,
    )
    assert adapter.record_action(
        signal_id="s-replay",
        action="CORRECTED",
        recorded_at_ist="2026-09-04T11:01:00+05:30",
        correction_of="s-replay",
    )

    reopened = PaperLedger(db, mirror)
    assert reopened.replay_jsonl() == 0
    assert reopened.replay_jsonl() == 0
    export = PaperFixtureAdapter(reopened).export_eod("2026-09-04")
    assert export["customer_action_count"] == 2
    assert export["action_counts"] == {"CORRECTED": 1, "TOOK": 1}
    assert export["duplicate_event_count"] == 0
    assert export["mirror_event_count"] == 2
    assert export["metadata"]["mode"] == "PAPER"
    assert export["metadata"]["promote"] == "NO_PROMOTE"
    assert export["metadata"]["replay_idempotent"] is True
    assert len(mirror.read_text(encoding="utf-8").splitlines()) == 2


def test_eod_export_reports_fee_totals_and_unresolved_state(tmp_path: Path) -> None:
    ledger = PaperLedger(tmp_path / "ledger.sqlite", tmp_path / "ledger.jsonl")
    fee = assess_fees(
        trade_id="t-eod",
        gross_pnl=1000,
        gross_costs=100,
        lots=2,
        service_charge_per_lot=10,
        statutory_components=5,
    )
    ledger.record_fee_assessment(fee)
    export = ledger.export_eod("2026-09-04")
    assert export["fee_status"] == "KNOWN"
    assert export["gross_pnl_total"] == 1000.0
    assert export["gross_costs_total"] == 100.0
    assert export["commission_total"] is None
    assert export["customer_net_total"] == 875.0
    assert export["unresolved"] == []
