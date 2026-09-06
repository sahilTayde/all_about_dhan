"""Smoke tests for paper agent loop (no network, no secrets)."""

from __future__ import annotations

from pathlib import Path

from trading_agents_india.hooks.event_memory import classify_session_kind
from trading_agents_india.fixtures import fixture_contexts
from trading_agents_india.pipeline import run_session
from trading_agents_india.config import Settings


def test_sensex_fixture_is_news_day_hold(tmp_path: Path) -> None:
    settings = Settings(
        repo_root=Path(__file__).resolve().parents[3],
        kb_path=tmp_path / "tai.sqlite",
        openai_model="gpt-4o",
        openai_key_present=False,
    )
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


def test_nifty_can_early_ce_without_llm(tmp_path: Path) -> None:
    settings = Settings(
        repo_root=Path(__file__).resolve().parents[3],
        kb_path=tmp_path / "tai2.sqlite",
        openai_model="gpt-4o",
        openai_key_present=False,
    )
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


def test_session_kind_helper() -> None:
    ctx = fixture_contexts()["SENSEX"]
    assert classify_session_kind(ctx.news, ctx.session_kind_hint) == "NEWS_DAY"


def test_live_mode_refuses_orders(tmp_path: Path) -> None:
    settings = Settings(
        repo_root=Path(__file__).resolve().parents[3],
        kb_path=tmp_path / "tai_live.sqlite",
        openai_model="gpt-4o",
        openai_key_present=False,
    )
    result = run_session(
        underlyings=["NIFTY"],
        dry_run=False,
        use_llm=False,
        persist=False,
        mode="LIVE",
        settings=settings,
    )
    assert result.mode == "LIVE"
    assert result.live_gate.get("orders_allowed") is False
    assert result.live_order_attempt is not None
    assert result.live_order_attempt.get("execution") == "refused"
    payload = result.to_dict()
    assert payload["execution"] == "refused"


def test_personas_registry_has_trading_agents_names() -> None:
    from trading_agents_india.personas import registry_payload

    names = {p["trading_agents_name"] for p in registry_payload()}
    assert "News Analyst" in names
    assert "Bull Researcher" in names
    assert "Trader" in names
