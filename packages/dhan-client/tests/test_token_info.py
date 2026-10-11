"""JWT exp logging and auth-error classification. Tokens are built at runtime (no literals)."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

from dhan_client.errors import DhanApiError
from dhan_client.rate_limit import jittered_delay, next_backoff
from dhan_client.token_info import (
    auth_failure_message,
    describe_jwt_exp,
    is_auth_error,
    jwt_exp_unix,
    log_jwt_exp,
)

IST = timezone(timedelta(hours=5, minutes=30))


def _b64(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _token(*, exp: int | None) -> str:
    payload = {"sub": "ops"} if exp is None else {"exp": exp}
    return f"{_b64({'alg': 'none'})}.{_b64(payload)}.sig"


def test_jwt_exp_unix_and_describe():
    exp = int(datetime(2026, 10, 12, 10, 22, tzinfo=IST).timestamp())
    token = _token(exp=exp)
    assert jwt_exp_unix(token) == exp
    now = datetime(2026, 10, 12, 1, 22, tzinfo=IST)
    line = describe_jwt_exp(token, now=now)
    assert "Dhan JWT exp=2026-10-12T10:22:00+05:30" in line
    assert "in 9h 0m" in line
    logged = log_jwt_exp(token, now=now)
    assert token not in logged
    assert "eyJ" not in logged


def test_non_jwt_and_auth_errors():
    assert jwt_exp_unix("not-a-jwt") is None
    assert "no JWT exp" in describe_jwt_exp("plain-token")
    assert is_auth_error(DhanApiError("no", status_code=401))
    assert is_auth_error(DhanApiError("no", status_code=403, error_code="DH-901"))
    assert not is_auth_error(DhanApiError("slow", status_code=429))
    msg = auth_failure_message("fetching the chain", DhanApiError("no", status_code=401))
    assert "HTTP 401" in msg
    assert "Stop retrying" in msg


def test_jittered_delay_midpoint_is_identity_and_edges_scale():
    assert jittered_delay(10.0, rng=lambda: 0.5) == 10.0
    assert jittered_delay(10.0, rng=lambda: 1.0) == 12.0
    assert jittered_delay(10.0, rng=lambda: 0.0) == 8.0
    wait, nxt = next_backoff(2.0, cap=30.0, rng=lambda: 1.0)
    assert wait == 2.4
    assert nxt == 4.0
