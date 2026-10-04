"""V2-23: fail-closed JWT, founder 2FA, role channels, rate caps. No secrets in git."""

from __future__ import annotations

import pytest

from auth import (
    ACCESS_TTL_S,
    COMMAND_PER_S,
    CUSTOMER_CHANNELS,
    CUSTOMER_SIGNAL_FIELDS,
    FOUNDER_CHANNELS,
    ISS,
    REST_PER_S,
    WS_SUBSCRIBE_PER_S,
    AuthClosed,
    AuthDecision,
    AuthRateLimiter,
    allow_channel,
    authorize_control,
    customer_safe,
    encode_jwt,
    issue_access,
    issue_refresh,
    looks_like_jwt,
    refresh_to_access,
    totp_at,
    verify_access,
    verify_jwt,
    verify_totp,
)

# RFC 6238 Appendix B seed (ASCII 12345678901234567890) as base32. Test vector only.
RFC_SEED = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
JWT = "paper-test-hmac-not-a-production-key"
NOW = 1_700_000_000.0


def _founder(*, tfa: bool = False) -> str:
    return issue_access(
        JWT,
        role="founder",
        sub="founder",
        now=NOW,
        tfa=tfa,
        totp_secret=RFC_SEED,
        totp_code=totp_at(RFC_SEED, NOW) if tfa else "",
    )


def test_missing_secret_cannot_issue_or_verify() -> None:
    with pytest.raises(AuthClosed, match="jwt_secret_missing"):
        issue_access("", role="founder", sub="founder", now=NOW)
    with pytest.raises(AuthClosed, match="jwt_secret_missing"):
        issue_refresh("", role="customer", sub="c1", now=NOW)
    denied = verify_jwt("x.y.z", "", NOW)
    assert denied.ok is False
    assert denied.reason == "jwt_secret_missing"


def test_expired_and_bad_sig_and_wrong_aud_fail_closed() -> None:
    token = issue_access(JWT, role="customer", sub="c1", now=NOW)
    assert verify_access(token, JWT, NOW).ok is True
    assert verify_access(token, JWT, NOW + ACCESS_TTL_S + 1).reason == "expired"
    assert verify_access(token, "other-hmac-key", NOW).reason == "unauthorized"
    tampered = token[:-2] + ("x" if token[-2] != "x" else "y") + token[-1]
    assert verify_access(tampered, JWT, NOW).ok is False
    bad_aud = encode_jwt(
        {
            "iss": ISS,
            "aud": "other",
            "sub": "c1",
            "role": "customer",
            "typ": "access",
            "tfa": False,
            "iat": int(NOW),
            "exp": int(NOW) + 60,
        },
        JWT,
    )
    assert verify_access(bad_aud, JWT, NOW).reason == "unauthorized"
    none = verify_access(None, JWT, NOW)
    assert none.ok is False and none.reason == "unauthorized"
    assert looks_like_jwt("not-a-jwt") is False


def test_refresh_cannot_access_or_control() -> None:
    refresh = issue_refresh(JWT, role="founder", sub="founder", now=NOW)
    denied = verify_access(refresh, JWT, NOW)
    assert denied.ok is False
    assert denied.reason == "refresh_forbidden"
    raw = verify_jwt(refresh, JWT, NOW)
    assert raw.ok is True and raw.typ == "refresh"
    assert authorize_control(raw) == "refresh_forbidden"
    assert allow_channel(raw.role, "positions", typ=raw.typ) is False
    access = refresh_to_access(refresh, JWT, NOW)
    fresh = verify_access(access, JWT, NOW)
    assert fresh.ok is True and fresh.tfa is False
    assert authorize_control(fresh) == "tfa_required"
    with pytest.raises(AuthClosed, match="not_refresh"):
        refresh_to_access(access, JWT, NOW)


def test_founder_2fa_required_for_control() -> None:
    assert verify_totp("", "123456", NOW) is False
    assert verify_totp(RFC_SEED, "abcdef", NOW) is False
    assert verify_totp(RFC_SEED, totp_at(RFC_SEED, NOW), NOW) is True
    # RFC 6238 SHA-1, T=59 → 287082
    assert totp_at(RFC_SEED, 59) == "287082"
    with pytest.raises(AuthClosed, match="tfa_failed"):
        issue_access(
            JWT,
            role="founder",
            sub="founder",
            now=NOW,
            tfa=True,
            totp_secret=RFC_SEED,
            totp_code="000000",
        )
    with pytest.raises(AuthClosed, match="totp_secret_missing"):
        totp_at("", NOW)
    no_tfa = verify_access(_founder(tfa=False), JWT, NOW)
    assert no_tfa.role == "founder" and no_tfa.tfa is False
    assert authorize_control(no_tfa) == "tfa_required"
    with_tfa = verify_access(_founder(tfa=True), JWT, NOW)
    assert with_tfa.tfa is True
    assert authorize_control(with_tfa) is None
    customer = verify_access(issue_access(JWT, role="customer", sub="c1", now=NOW), JWT, NOW)
    assert authorize_control(customer) == "founder_only"
    assert authorize_control(None) == "unauthorized"
    assert authorize_control(AuthDecision(ok=False, reason="expired")) == "expired"


def test_role_scoped_channels_and_customer_copy() -> None:
    assert "signals:public" in CUSTOMER_CHANNELS
    assert CUSTOMER_CHANNELS <= FOUNDER_CHANNELS
    assert allow_channel("customer", "signals:public") is True
    assert allow_channel("customer", "positions") is False
    assert allow_channel("customer", "decisions") is False
    assert allow_channel("founder", "positions") is True
    assert allow_channel("founder", "signals:public") is True
    assert allow_channel("unknown", "signals:public") is False
    soup = {
        "underlying": "NIFTY",
        "side": "CE",
        "trend": "up",
        "chain_3m": {"atm": 1},
        "news": ["cited"],
        "rsi": 90,
        "macd": 1,
        "supertrend": "long",
    }
    safe = customer_safe(soup)
    assert safe["underlying"] == "NIFTY"
    assert "rsi" not in safe and "macd" not in safe and "supertrend" not in safe
    assert set(safe) <= CUSTOMER_SIGNAL_FIELDS


def test_rate_limits_rest_ws_command() -> None:
    ticks = iter([0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 1.1])
    lim = AuthRateLimiter(clock=lambda: next(ticks))
    for _ in range(REST_PER_S):
        assert lim.allow("ip", "rest") is True
    assert lim.allow("ip", "rest") is False
    ticks_ws = iter([0.0] * (WS_SUBSCRIBE_PER_S + 1) + [1.1])
    ws = AuthRateLimiter(clock=lambda: next(ticks_ws))
    assert [ws.allow("ip", "ws_subscribe") for _ in range(WS_SUBSCRIBE_PER_S)] == [True] * WS_SUBSCRIBE_PER_S
    assert ws.allow("ip", "ws_subscribe") is False
    cmd = AuthRateLimiter(clock=lambda: next(iter([0.0, 0.1, 1.1])))
    assert cmd.allow("ip", "command") is True
    assert cmd.allow("ip", "command") is False
    assert COMMAND_PER_S == 1
