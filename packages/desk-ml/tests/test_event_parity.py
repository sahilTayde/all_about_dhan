"""Acceptance: USE_EVENT_BUS replay reproduces the monolith's trade list exactly; budgets from the plan."""

import tempfile
from pathlib import Path

import pytest

import desk_ml.paper_scalp as ps
from desk_ml.event_parity import fixture_replay_kwargs, load_fixture, run_fixture_parity

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "synthetic_session_nifty.json"


@pytest.fixture(scope="module")
def report():
    return run_fixture_parity(FIXTURE)


def test_event_path_reproduces_monolith_trades(report):
    assert report["problems"] == []
    assert report["ok"]
    assert report["old"] == report["new"]
    assert report["new"]["n_trades"] >= 5, "fixture must actually trade"
    bus = report["event_bus"]
    assert bus["ledger_trades_closed"] == report["new"]["n_trades"]
    assert bus["vetoes"] == [] and bus["handler_errors"] == []


def test_every_step_is_on_the_audit_log(report):
    ev, n_analysts = report["event_bus"]["events"], len(report["event_bus"]["analysts"])
    n_tickets = len(report["closed_trades"])
    assert ev["REQUEST_VOTES"] == ev["MARKET_TICK"]
    assert ev["ANALYST_VOTE"] == n_analysts * ev["REQUEST_VOTES"]
    assert ev["ENTRY_APPROVED"] == n_tickets
    assert ev["POSITION_CLOSED"] == n_tickets
    assert ev["ORDER_SUBMITTED"] == n_tickets + report["new"]["n_trades"]  # entries + exits


def test_latency_budgets(report):
    """docs/04_MIGRATION_PLAN.md: boss decision < 1 s p99, desk paper execution < 100 ms p99."""
    lat = report["event_bus"]["latency_p99_ms"]
    print(f"p99 ms: {lat}")
    assert lat["boss_decision"] < 1000.0
    assert lat["desk_entry"] < 100.0


def test_two_indices_walked_one_after_another(monkeypatch, tmp_path):
    """Replay walks NIFTY's whole day, then SENSEX from 09:15: SENSEX risk checks must not see NIFTY's later exits."""
    from desk_ml.event_parity import run_parity, synthetic_triples
    from desk_ml.founder_session import save_founder_book

    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: ({"NIFTY": 65, "SENSEX": 20}.get(und, 30), "t"))
    tbu = {"NIFTY": synthetic_triples(seed=5)[:750], "SENSEX": synthetic_triples(seed=9, underlying="SENSEX")[:750]}
    save_founder_book(list(tbu), root=tmp_path)
    rep = run_parity(root=tmp_path, underlyings=tuple(tbu), triples_by_und=tbu, session_ist_date="2026-09-10")
    assert rep["problems"] == [] and rep["ok"]
    assert {r["underlying"] for r in rep["closed_trades"] if r["filled"]} == {"NIFTY", "SENSEX"}


def test_flag_is_off_by_default_and_env_turns_it_on(monkeypatch):
    fx = load_fixture(FIXTURE)
    fx["triples"] = fx["triples"][:80]
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (65, "fixture"))
    monkeypatch.delenv(ps.USE_EVENT_BUS_ENV, raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        assert "event_bus" not in ps.replay_paper_scalp(**fixture_replay_kwargs(fx, Path(tmp)), write=False)
    monkeypatch.setenv(ps.USE_EVENT_BUS_ENV, "1")
    with tempfile.TemporaryDirectory() as tmp:
        board = ps.replay_paper_scalp(**fixture_replay_kwargs(fx, Path(tmp)), write=False)
    assert board["event_bus"]["events"]["MARKET_TICK"] == 79
