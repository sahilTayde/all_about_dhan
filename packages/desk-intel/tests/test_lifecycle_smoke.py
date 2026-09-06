"""Cheap smoke: outcomes never leave a withdrawn signal still valid."""

from desk_intel.nightly import RECON_JSON_KEYS, load_cas_calls
from desk_intel.outcomes import (
    OUTCOME_HELP,
    build_record,
    still_valid,
    resolve_outcome,
)
from desk_intel.schema import (
    ACTIVE_STAGES,
    COMPLIANCE_NOTE,
    MarketSignal,
    TERMINAL_OUTCOMES,
    UserFill,
)


def test_outcome_enum_names() -> None:
    expected = {
        "ACHIEVED",
        "STOPPED",
        "INVALIDATED",
        "EXPIRED",
        "LOST",
        "COMPLETED",
        "SHADOW_CLOSED",
    }
    assert set(OUTCOME_HELP) == expected
    assert TERMINAL_OUTCOMES == expected
    assert "IN_PROGRESS" in ACTIVE_STAGES


def test_invalidated_is_never_still_valid() -> None:
    assert still_valid("CONFIRMED", "INVALIDATED") is False
    assert still_valid("EARLY", "ACHIEVED") is False
    assert still_valid("CONFIRMED", None) is True


def test_in_progress_is_still_valid_until_outcome() -> None:
    assert still_valid("IN_PROGRESS", None) is True
    assert still_valid("IN_PROGRESS", "ACHIEVED") is False
    assert still_valid("IN_PROGRESS", "STOPPED") is False
    assert still_valid("IN_PROGRESS", "INVALIDATED") is False


def _confirmed_signal() -> MarketSignal:
    return MarketSignal(
        id="desk-nifty-test",
        underlying="NIFTY",
        lean="BUY_CE",
        confidence=0.5,
        risk_regime="MIXED",
        reasons=["fixture"],
        vetoes=[],
        timestamp="2026-09-01T10:03:00+05:30",
        news_bias="MIXED",
        chain_bias="CE",
        tags=["DESK_INTEL"],
        dry_run=True,
        layer="HYPOTHESIS",
        compliance=COMPLIANCE_NOTE,
        stage="CONFIRMED",
        outcome=None,
        still_valid=True,
    )


def test_confirmed_live_trade_promotes_to_in_progress() -> None:
    rec = build_record(
        _confirmed_signal(),
        user=UserFill(took_trade=True, lots=1, recorded_at="2026-09-01T10:04:00+05:30"),
        entry=100.0,
        stop=70.0,
        target=140.0,
        mark=110.0,
        invalidated=False,
        session_expired=False,
    )
    assert rec.stage == "IN_PROGRESS"
    assert rec.outcome is None
    assert rec.still_valid is True


def test_premium_target_and_stop() -> None:
    hit, _ = resolve_outcome(
        stage="CONFIRMED",
        lean="BUY_PE",
        entry=95.0,
        stop=62.0,
        target=155.0,
        mark=160.0,
        invalidated=False,
        session_expired=False,
        user_took=False,
    )
    assert hit == "ACHIEVED"
    stopped, _ = resolve_outcome(
        stage="CONFIRMED",
        lean="BUY_CE",
        entry=100.0,
        stop=70.0,
        target=140.0,
        mark=65.0,
        invalidated=False,
        session_expired=False,
        user_took=True,
    )
    assert stopped == "STOPPED"
    dead, _ = resolve_outcome(
        stage="CONFIRMED",
        lean="BUY_CE",
        entry=100.0,
        stop=70.0,
        target=140.0,
        mark=110.0,
        invalidated=True,
        session_expired=False,
        user_took=False,
    )
    assert dead == "INVALIDATED"


def test_recon_schema_keys() -> None:
    required = {
        "schema_version",
        "job",
        "day",
        "counts",
        "records",
        "param_review_unvalidated",
        "session_kind",
        "retune_proposal",
        "production_params_written",
        "cas_calls",
    }
    assert required.issubset(set(RECON_JSON_KEYS))


def test_load_cas_calls_reads_analyst_json(tmp_path) -> None:
    day = "2026-09-01"
    folder = tmp_path / "cas_calls"
    folder.mkdir()
    (folder / f"{day}.json").write_text(
        '{"calls": [{"underlying": "NIFTY", "bias": "SIDEWAYS"}]}',
        encoding="utf-8",
    )
    rows = load_cas_calls(tmp_path, "cas_calls", day)
    assert len(rows) == 1
    assert rows[0]["bias"] == "SIDEWAYS"
    assert load_cas_calls(tmp_path, "cas_calls", "1999-01-01") == []
