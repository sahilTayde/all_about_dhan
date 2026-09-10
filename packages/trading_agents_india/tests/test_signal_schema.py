"""DESK_SIGNAL_JSON v1 — precedence, downgrade, expiry, honesty guards."""

from __future__ import annotations

from datetime import datetime, timedelta

from trading_agents_india.schemas import PaperTicket
from trading_agents_india.signal_schema import (
    CONFIDENCE_NULL_FLOOR,
    IST,
    RISK_FLAG_DOWNGRADED_INVALIDATION,
    RISK_FLAG_DOWNGRADED_PREMIUM,
    apply_expiry,
    build_signal_json,
    human_summary,
)

NOW = datetime(2026, 9, 10, 11, 0, 0, tzinfo=IST)
LATER = (NOW + timedelta(hours=1)).isoformat(timespec="seconds")


def _ticket(**kwargs) -> PaperTicket:
    base = dict(
        underlying="NIFTY",
        lean="BUY_CE",
        stage="EARLY",
        reasons=["input_mix:MIX-DEFAULT-BUY"],
        risk_veto=False,
        vetoes=[],
        session_kind="NORMAL",
        confidence=0.6,
        data_gaps=[],
        premium_lean={"source": "optionchain_atm", "option_ltp": 120.5},
    )
    base.update(kwargs)
    return PaperTicket(**base)  # type: ignore[arg-type]


def test_veto_overrides_everything() -> None:
    sig = build_signal_json(
        _ticket(risk_veto=True, vetoes=["BIG_NEWS: hold"], lean="BUY_CE"),
        signal_id="s1",
        now_ist=NOW,
        invalidation="spot below X",
        valid_until_ist=LATER,
        premium_ohlc_present=True,
        spot=25000.0,
    )
    assert sig["decision"] == "NO_TRADE"
    assert sig["status"] == "VETOED"


def test_buy_downgrades_without_invalidation() -> None:
    sig = build_signal_json(
        _ticket(),
        signal_id="s2",
        now_ist=NOW,
        premium_ohlc_present=True,
        spot=25000.0,
    )
    assert sig["decision"] == "WAIT"
    assert sig["status"] == "WATCHING"
    assert RISK_FLAG_DOWNGRADED_INVALIDATION in sig["risk_flags"]


def test_buy_downgrades_without_premium_ohlc() -> None:
    sig = build_signal_json(
        _ticket(),
        signal_id="s3",
        now_ist=NOW,
        invalidation="NIFTY loses 24,950 and holds below",
        valid_until_ist=LATER,
        premium_ohlc_present=False,
        spot=25000.0,
    )
    assert sig["decision"] == "WAIT"
    assert RISK_FLAG_DOWNGRADED_PREMIUM in sig["risk_flags"]


def test_buy_allowed_with_full_evidence() -> None:
    sig = build_signal_json(
        _ticket(),
        signal_id="s4",
        now_ist=NOW,
        invalidation="NIFTY loses 24,950 and holds below",
        valid_until_ist=LATER,
        premium_ohlc_present=True,
        spot=25000.0,
    )
    assert sig["decision"] == "BUY_CE"
    assert sig["status"] == "ACTIVE"
    assert sig["risk_flags"] == []
    assert sig["compliance"]["NO_PROMOTE"] is True
    assert sig["compliance"]["win_rate_claim"] is None
    assert sig["order_flow"] == {"status": "UNAVAILABLE"}


def test_confidence_null_when_data_quality_poor() -> None:
    sig = build_signal_json(
        _ticket(
            premium_lean={},
            data_gaps=[f"gap-{i}" for i in range(8)],
        ),
        signal_id="s5",
        now_ist=NOW,
        spot=None,
    )
    assert sig["data_quality"]["score"] < CONFIDENCE_NULL_FLOOR
    assert sig["confidence_score"] is None


def test_hold_maps_to_wait_and_expiry_lifecycle() -> None:
    sig = build_signal_json(_ticket(lean="HOLD"), signal_id="s6", now_ist=NOW, spot=25000.0)
    assert sig["decision"] == "WAIT"
    assert sig["status"] == "WATCHING"
    sig["valid_until_ist"] = NOW.isoformat(timespec="seconds")
    expired = apply_expiry(sig, now_ist=NOW + timedelta(minutes=5))
    assert expired["status"] == "EXPIRED"


def test_human_summary_never_claims_win_rate() -> None:
    sig = build_signal_json(_ticket(lean="HOLD"), signal_id="s7", now_ist=NOW, spot=25000.0)
    text = human_summary(sig)
    assert "not win probability" in text or "n/a" in text
    assert "UNVALIDATED" in text
    assert "win rate" not in text.lower()
