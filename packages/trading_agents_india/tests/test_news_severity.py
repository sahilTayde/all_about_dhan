"""P0-1: fixture/routine news must not veto; BIG_NEWS gated by NEWS_VETO_ENABLED."""

from __future__ import annotations

from pathlib import Path

import pytest

from trading_agents_india.config import Settings
from trading_agents_india.fixtures import MarketContext, NewsItem, fixture_contexts
from trading_agents_india.hooks.event_memory import (
    classify_session_kind,
    news_item_severity,
    score_premarket_sentiment,
)
from trading_agents_india.pipeline import run_session


def _settings(tmp_path: Path, name: str = "sev.sqlite") -> Settings:
    return Settings(
        repo_root=Path(__file__).resolve().parents[3],
        kb_path=tmp_path / name,
        openai_model="gpt-4o",
        openai_key_present=False,
    )


def test_routine_fixture_is_not_big_news() -> None:
    item = NewsItem(
        headline="Brent crude jumps (FIXTURE)",
        source_url="https://example.invalid/brent",
        tags=["MACRO_EVENT", "CRUDE", "FIXTURE", "ROUTINE"],
        risk_bias="RISK_OFF",
    )
    assert news_item_severity(item) == "ROUTINE"
    assert classify_session_kind([item], "NORMAL") == "NORMAL"
    assert classify_session_kind([item], "NEWS_DAY") == "NORMAL"


def test_big_news_forces_news_day() -> None:
    item = NewsItem(
        headline="Geopolitical shock — circuit risk",
        source_url="https://example.invalid/shock",
        tags=["BIG_NEWS", "GEOPOLITICAL_SHOCK", "MACRO_EVENT"],
        risk_bias="RISK_OFF",
    )
    assert news_item_severity(item) == "BIG_NEWS"
    assert classify_session_kind([item], "NORMAL") == "NEWS_DAY"


def test_nifty_fixture_session_not_vetoed_by_routine_news(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    result = run_session(
        underlyings=["NIFTY"],
        dry_run=True,
        use_llm=False,
        prefer_desk=False,
        gather_india_news=False,
        persist=False,
        settings=settings,
    )
    t = result.tickets[0]
    assert t.session_kind == "NORMAL"
    assert t.risk_veto is False or t.stage in ("EARLY", "WATCH", "VETOED")
    # Routine news must not force NEWS_DAY
    assert t.session_kind != "NEWS_DAY"
    assert any("premarket_sentiment" in r for r in t.reasons) or t.lean in (
        "BUY_CE",
        "HOLD",
    )


def test_sensex_big_news_fixture_no_longer_holds_by_default(tmp_path: Path) -> None:
    """NEWS_VETO_ENABLED soft-default false → SENSEX BIG_NEWS fixture may lean CE/PE."""
    settings = _settings(tmp_path, "sensex.sqlite")
    result = run_session(
        underlyings=["SENSEX"],
        dry_run=True,
        use_llm=False,
        persist=False,
        settings=settings,
    )
    t = result.tickets[0]
    # Session may still tag NEWS_DAY for analog, but ticket must not hard-HOLD from news.
    assert t.risk_veto is False
    assert t.lean in ("BUY_CE", "BUY_PE", "HOLD")
    assert t.stage != "VETOED" or t.lean != "HOLD" or not t.risk_veto
    # Chain fixture lean is PE → prefer BUY_PE when news parked
    assert t.lean == "BUY_PE"
    assert any("news_veto_enabled=false" in r for r in t.reasons)


def test_sensex_big_news_holds_when_veto_reenabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NEWS_VETO_ENABLED", "true")
    settings = _settings(tmp_path, "sensex_veto_on.sqlite")
    result = run_session(
        underlyings=["SENSEX"],
        dry_run=True,
        use_llm=False,
        persist=False,
        settings=settings,
    )
    t = result.tickets[0]
    assert t.session_kind == "NEWS_DAY"
    assert t.lean == "HOLD"
    assert t.risk_veto is True
    assert t.stage == "VETOED"


def test_desk_style_brent_rbi_overlay_no_veto(tmp_path: Path) -> None:
    """Reproduce 2026-09-07 failure mode: Brent+RBI fixtures must not HOLD all day."""
    settings = _settings(tmp_path, "desk_overlay.sqlite")
    ctx = MarketContext(
        underlying="NIFTY",
        chain_lean="CE",
        trend_plain="Fixture mild upside",
        news=[
            NewsItem(
                headline="Brent crude jumps from 90 to 95 (FIXTURE)",
                source_url="https://www.eia.gov/rss/todayinenergy.xml",
                tags=["MACRO_EVENT", "CRUDE", "FIXTURE", "ROUTINE"],
                risk_bias="RISK_OFF",
            ),
            NewsItem(
                headline="RBI commentary watch — no policy print",
                source_url="https://rbi.org.in/Scripts/rss.aspx",
                tags=["MACRO_EVENT", "RBI", "FIXTURE", "ROUTINE"],
                risk_bias="MIXED",
            ),
        ],
        session_kind_hint="NORMAL",
    )
    assert classify_session_kind(ctx.news, ctx.session_kind_hint) == "NORMAL"
    soft = score_premarket_sentiment(ctx.news)
    assert soft["label"] in ("SOFT_RISK_OFF", "SOFT_MIXED")
    assert soft["big_news_count"] == 0

    # Pipeline with NIFTY fixtures (not desk) already NORMAL; inject via classify only.
    nifty = fixture_contexts()["NIFTY"]
    assert classify_session_kind(nifty.news, nifty.session_kind_hint) == "NORMAL"


def test_premarket_sentiment_quiet() -> None:
    out = score_premarket_sentiment([])
    assert out["label"] == "QUIET"
    assert out["big_news_count"] == 0
