"""Auth failures stop; 429 backs off with jitter. No live Dhan."""

from __future__ import annotations

from typing import Any

from data_recorder.runner import AuthFailed, DataRecorderRunner
from dhan_client.errors import DhanApiError
from dhan_client.token_info import auth_failure_message, is_auth_error, log_jwt_exp


def test_auth_error_is_not_retryable() -> None:
    assert is_auth_error(DhanApiError("no", status_code=401))
    assert is_auth_error(DhanApiError("no", status_code=403))
    assert not is_auth_error(DhanApiError("slow", status_code=429))
    msg = auth_failure_message("running Index recorder", DhanApiError("no", status_code=401))
    assert "Stop retrying" in msg
    assert "HTTP 401" in msg


def test_start_exits_2_on_auth_failed(monkeypatch: Any) -> None:
    runner = DataRecorderRunner(dry_run=True)

    async def boom() -> None:
        raise AuthFailed("Dhan rejected the credentials while running Index recorder (HTTP 401).")

    monkeypatch.setattr(runner, "run_async", boom)
    assert runner.start() == 2


def test_jwt_exp_logged_without_token(caplog: Any) -> None:
    import base64
    import json
    from datetime import datetime, timedelta, timezone

    ist = timezone(timedelta(hours=5, minutes=30))

    def b64(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode().rstrip("=")

    exp = int(datetime(2026, 10, 12, 10, 0, tzinfo=ist).timestamp())
    token = f"{b64({'alg': 'none'})}.{b64({'exp': exp})}.sig"
    with caplog.at_level("INFO"):
        line = log_jwt_exp(token, now=datetime(2026, 10, 12, 1, 0, tzinfo=ist))
    assert "Dhan JWT exp=" in line
    assert token not in caplog.text
    assert "eyJ" not in line
