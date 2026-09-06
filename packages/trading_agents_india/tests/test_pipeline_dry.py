"""Smoke tests: paper vs LIVE refuse + dry market-hours simulation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from trading_agents_india.config import Settings
from trading_agents_india.fixtures import fixture_contexts
from trading_agents_india.handoffs import HANDOFF_GRAPH, build_handoff_chain
from trading_agents_india.hooks.depth import fetch_depth_snapshot
from trading_agents_india.hooks.event_memory import classify_session_kind
from trading_agents_india.hooks.premium import index_proxy_lean
from trading_agents_india.mix_inputs import PAPER_INPUT_MIXES, build_reason_inputs
from trading_agents_india.pipeline import run_session
from trading_agents_india.session_clock import IST, snapshot
from trading_agents_india.session_runner import run_market_hours_loop


def _settings(tmp_path: Path, name: str = "tai.sqlite") -> Settings:
    return Settings(
        repo_root=Path(__file__).resolve().parents[3],
        kb_path=tmp_path / name,
        openai_model="gpt-4o",
        openai_key_present=False,
    )


def test_sensex_fixture_is_news_day_hold(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    result = run_session(
        underlyings=["SENSEX"],
        dry_run=True,
        use_llm=False,
        persist=True,
        settings=settings,
    )
    assert len(result.tickets) == 1
    t = result.tickets[0]
    assert t.underlying == "SENSEX"
    assert t.session_kind == "NEWS_DAY"
    assert t.lean == "HOLD"
    assert t.risk_veto is True
    assert t.execution == "refused"
    assert settings.kb_path.is_file()
    assert t.chain_watcher_summary
    assert t.handoffs
    assert any("MIX-DEFAULT-BUY" in r for r in t.reasons)


def test_nifty_can_early_ce_without_llm(tmp_path: Path) -> None:
    settings = _settings(tmp_path, "tai2.sqlite")
    result = run_session(
        underlyings=["NIFTY"],
        dry_run=True,
        use_llm=False,
        persist=False,
        settings=settings,
    )
    t = result.tickets[0]
    assert t.lean in ("BUY_CE", "HOLD")
    assert t.stage in ("EARLY", "WATCH", "VETOED")
    assert "MIX-DEFAULT-BUY" in t.default_mix_cited
    assert t.premium_lean.get("source") in ("index_proxy", "optidx_rolling", "unavailable")
    assert t.premium_lean.get("layer") in ("HYPOTHESIS", "SOURCE_FACT")


def test_depth_hook_is_di_only() -> None:
    snap = fetch_depth_snapshot("NIFTY")
    assert snap.status == "DATA_INSUFFICIENT"
    assert snap.layer == "DATA_INSUFFICIENT"
    assert snap.claims_alpha is False
    assert snap.packets_seen == 0
    assert any("PARKED" in g for g in snap.data_gaps)


def test_session_kind_helper() -> None:
    ctx = fixture_contexts()["SENSEX"]
    assert classify_session_kind(ctx.news, ctx.session_kind_hint) == "NEWS_DAY"


def test_paper_vs_live_refuse(tmp_path: Path) -> None:
    settings = _settings(tmp_path, "tai_modes.sqlite")
    paper = run_session(
        underlyings=["NIFTY"],
        dry_run=True,
        use_llm=False,
        persist=False,
        mode="PAPER",
        settings=settings,
    )
    assert paper.mode == "PAPER"
    assert paper.live_gate.get("orders_allowed") is False
    assert paper.to_dict()["execution"] == "refused"
    assert paper.live_order_attempt is None

    live = run_session(
        underlyings=["NIFTY"],
        dry_run=False,
        use_llm=False,
        persist=False,
        mode="LIVE",
        settings=settings,
    )
    assert live.mode == "LIVE"
    assert live.live_gate.get("orders_allowed") is False
    assert live.live_order_attempt is not None
    assert live.live_order_attempt.get("execution") == "refused"
    assert live.to_dict()["execution"] == "refused"
    for t in live.tickets:
        assert t.execution == "refused"


def test_live_mode_refuses_orders(tmp_path: Path) -> None:
    # Keep legacy name used by deepen notes
    test_paper_vs_live_refuse(tmp_path)


def test_personas_registry_has_trading_agents_names() -> None:
    from trading_agents_india.personas import registry_payload

    names = {p["trading_agents_name"] for p in registry_payload()}
    assert "News Analyst" in names
    assert "Bull Researcher" in names
    assert "Trader" in names
    assert "Option Chain Watcher" in names


def test_handoff_graph_includes_chain_and_trader() -> None:
    roles = {a for a, _ in HANDOFF_GRAPH} | {b for _, b in HANDOFF_GRAPH}
    assert "chain_watcher" in roles
    assert "trader" in roles
    assert ("trader", "risk_committee") in HANDOFF_GRAPH


def test_dry_market_hours_simulation(tmp_path: Path) -> None:
    settings = _settings(tmp_path, "tai_loop.sqlite")
    mid = datetime(2026, 9, 4, 11, 15, tzinfo=IST)
    dead = datetime(2026, 9, 4, 9, 10, tzinfo=IST)
    runner = run_market_hours_loop(
        underlyings=["NIFTY"],
        mode="PAPER",
        tick_seconds=30,
        max_ticks=2,
        simulate=True,
        simulate_clocks=[mid, dead],
        use_llm=False,
        persist=True,
        write_paper_watch=True,
        settings=settings,
    )
    assert runner.simulated is True
    assert runner.mode == "PAPER"
    assert len(runner.ticks) == 2
    assert runner.ticks[0].clock["allow_directional_paper"] is True
    assert runner.ticks[1].clock["in_dead_band"] is True
    # Dead-band tick forced HOLD
    t1 = runner.ticks[1].result.tickets[0]
    assert t1.lean == "HOLD"
    assert t1.execution == "refused"
    assert runner.ticks[0].ledger_paths
    # paper_watch MIX-TA-MARKET-HOURS path written
    assert any("MIX-TA-MARKET-HOURS" in p for p in runner.ticks[0].ledger_paths)
    payload = runner.to_dict()
    assert payload["execution"] == "refused"
    assert "path_toward_faster" in payload


def test_clock_dead_band_and_active() -> None:
    active = snapshot(datetime(2026, 9, 4, 12, 0, tzinfo=IST))
    assert active.allow_directional_paper is True
    morning = snapshot(datetime(2026, 9, 4, 9, 15, tzinfo=IST))
    assert morning.in_dead_band is True
    assert morning.allow_directional_paper is False
    afternoon = snapshot(datetime(2026, 9, 4, 15, 10, tzinfo=IST))
    assert afternoon.in_dead_band is True


def test_clock_shell_open_at_0900_and_weekend() -> None:
    open_shell = snapshot(datetime(2026, 9, 4, 9, 0, tzinfo=IST))
    assert open_shell.in_session_shell is True
    assert open_shell.in_dead_band is True
    assert open_shell.allow_directional_paper is False
    # 2026-09-06 is Sunday — outside shell
    sunday = snapshot(datetime(2026, 9, 6, 11, 0, tzinfo=IST))
    assert sunday.in_session_shell is False
    assert sunday.allow_directional_paper is False


def test_rag_hook_fail_soft() -> None:
    from trading_agents_india.hooks.rag import fetch_rag_context

    snippets, gaps = fetch_rag_context("NIFTY", limit=2)
    assert isinstance(snippets, list)
    assert isinstance(gaps, list)
    assert len(snippets) <= 2


def test_cli_flag_triple_precedence() -> None:
    from trading_agents_india.__main__ import _resolve_flag_triple

    assert _resolve_flag_triple(explicit_on=False, explicit_off=True, default=True) is False
    assert _resolve_flag_triple(explicit_on=True, explicit_off=False, default=False) is True
    assert _resolve_flag_triple(explicit_on=False, explicit_off=False, default=True) is True


def test_index_proxy_premium_labeled_hypothesis() -> None:
    r = index_proxy_lean("NIFTY", chain_lean="CE")
    assert r.source == "index_proxy"
    assert r.layer == "HYPOTHESIS"
    assert r.lean == "BUY_CE"


def test_mix_inputs_cite_default_and_ta(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    blob = build_reason_inputs(root)
    assert "MIX-DEFAULT-BUY" in blob["mixes_cited"]
    assert "MIX-TA-FLOW-RISK" in PAPER_INPUT_MIXES
    assert any("input_mix:MIX-DEFAULT-BUY" in line for line in blob["reason_lines"])


def test_build_handoff_chain_from_session(tmp_path: Path) -> None:
    settings = _settings(tmp_path, "tai_ho.sqlite")
    result = run_session(
        underlyings=["BANKNIFTY"],
        dry_run=True,
        use_llm=False,
        persist=False,
        settings=settings,
    )
    reports = result.tickets[0].reports
    from trading_agents_india.schemas import AgentReport

    rebuilt = [
        AgentReport(
            role=r["role"],
            summary=r["summary"],
            lean_hint=r.get("lean_hint", "HOLD"),
            confidence=float(r.get("confidence") or 0),
            layer=r.get("layer", "HYPOTHESIS"),
            citations=list(r.get("citations") or []),
            data_gaps=list(r.get("data_gaps") or []),
        )
        for r in reports
    ]
    chain = build_handoff_chain(rebuilt)
    assert any(h.from_role == "trader" for h in chain)
    assert all(h.execution == "refused" for h in chain)
