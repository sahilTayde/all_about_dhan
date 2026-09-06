"""Retune gate: session tags + RETUNE_PROPOSAL. No invented backtest metrics."""

from desk_intel.fixtures import FIXTURE_NEWS
from desk_intel.nightly import RECON_JSON_KEYS
from desk_intel.retune_gate import (
    NIGHTLY_RETUNE_STATUS,
    RETUNE_KIND,
    assert_no_production_param_write,
    build_retune_proposal,
    classify_session,
    event_is_news_or_calendar,
)
from desk_intel.schema import COMPLIANCE_NOTE, MarketSignal


def _plain_signal(*, expiry: str = "2026-09-10", tags=None, vetoes=None) -> MarketSignal:
    return MarketSignal(
        id="desk-nifty-gate",
        underlying="NIFTY",
        lean="NEUTRAL",
        confidence=0.2,
        risk_regime="MIXED",
        reasons=["fixture"],
        vetoes=list(vetoes or []),
        timestamp="2026-09-01T10:03:00+05:30",
        news_bias="MIXED",
        chain_bias="NEUTRAL",
        tags=list(tags or ["DESK_INTEL"]),
        expiry=expiry,
        dry_run=True,
        layer="HYPOTHESIS",
        compliance=COMPLIANCE_NOTE,
        stage="EXPIRED",
        outcome="EXPIRED",
        still_valid=False,
    )


def test_fixture_news_is_calendar_or_print() -> None:
    assert any(event_is_news_or_calendar(e) for e in FIXTURE_NEWS)


def test_session_news_day_from_calendar_news() -> None:
    tag = classify_session(
        day="2026-09-01",
        signals=[_plain_signal()],
        events=list(FIXTURE_NEWS),
    )
    assert tag.kind == "NEWS_DAY"
    assert "NEWS_DAY" in tag.flags
    assert tag.usable_for_retune_sample is False


def test_session_expiry_when_sheet_is_today() -> None:
    tag = classify_session(
        day="2026-09-03",
        signals=[_plain_signal(expiry="2026-09-03")],
        events=[],
    )
    assert tag.kind == "EXPIRY"
    assert "EXPIRY" in tag.flags
    assert tag.usable_for_retune_sample is False


def test_session_normal_when_quiet() -> None:
    tag = classify_session(
        day="2026-09-01",
        signals=[_plain_signal(expiry="2026-09-10")],
        events=[],
    )
    assert tag.kind == "NORMAL"
    assert tag.flags == ["NORMAL"]
    assert tag.usable_for_retune_sample is True


def test_news_and_expiry_flags_together() -> None:
    tag = classify_session(
        day="2026-09-03",
        signals=[_plain_signal(expiry="2026-09-03")],
        events=list(FIXTURE_NEWS),
    )
    assert tag.kind == "NEWS_DAY"
    assert "NEWS_DAY" in tag.flags
    assert "EXPIRY" in tag.flags
    assert tag.usable_for_retune_sample is False


def test_retune_proposal_is_backtest_required_not_production() -> None:
    session = classify_session(day="2026-09-01", signals=[], events=[])
    proposal = build_retune_proposal(session=session, candidate_notes=["hint"])
    payload = proposal.to_dict()
    assert payload["kind"] == RETUNE_KIND
    assert payload["status"] == NIGHTLY_RETUNE_STATUS
    assert payload["keep_current_strategy"] is True
    assert payload["production_params_written"] is False
    assert payload["handoff"] == "REVIEW"
    assert payload["backtest_results"] is None
    assert payload["one_day_pnl_is_not_evidence"] is True
    assert "expectancy" in payload["metrics_required"]


def test_nightly_keys_include_retune_gate() -> None:
    required = {
        "session_kind",
        "session_flags",
        "retune_proposal",
        "production_params_written",
        "param_review_unvalidated",
    }
    assert required.issubset(set(RECON_JSON_KEYS))


def test_guard_allows_recon_paths() -> None:
    assert_no_production_param_write(
        (
            "/repo/data/recon/2026-09-01.json",
            "/repo/teams/02_phd_math/docs/handoffs/NIGHTLY_2026-09-01.md",
            "/repo/data/desk_intel/ledger/2026-09-01.json",
        )
    )


def test_guard_refuses_candidate_specs() -> None:
    try:
        assert_no_production_param_write(
            ("/repo/teams/04_quant/docs/candidates/STRAT-001.md",)
        )
    except RuntimeError as exc:
        assert "refused production param write" in str(exc)
    else:
        raise AssertionError("expected refuse")


def test_run_nightly_emits_proposal_without_persist() -> None:
    from desk_intel.nightly import run_nightly
    from desk_intel.workspace import load_desk_workspace

    cfg = load_desk_workspace()
    out = run_nightly(
        cfg,
        day="2026-09-01",
        persist=False,
        fixture_signals=[_plain_signal()],
        events=list(FIXTURE_NEWS),
        session_expired=True,
    )
    assert out["production_params_written"] is False
    assert out["recon_json"] is None
    assert out["phd_handoff"] is None
    proposal = out["retune_proposal"]
    assert proposal["kind"] == RETUNE_KIND
    assert proposal["status"] == NIGHTLY_RETUNE_STATUS
    assert proposal["backtest_results"] is None
    assert proposal["keep_current_strategy"] is True
    assert out["session_kind"] == "NEWS_DAY"
