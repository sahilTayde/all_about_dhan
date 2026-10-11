"""Decode Dhan access-token metadata for ops logs. Never returns or logs the token."""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
AUTH_HTTP = frozenset({401, 403})
AUTH_CODES = frozenset({"DH-901", "DH-902", "DH-903"})

log = logging.getLogger(__name__)


def is_auth_error(exc: BaseException) -> bool:
    """True for HTTP 401/403 or Dhan credential error codes. Safe: no secret fields."""
    status = getattr(exc, "status_code", None)
    if status in AUTH_HTTP:
        return True
    code = str(getattr(exc, "error_code", None) or "")
    return code in AUTH_CODES


def is_rate_limited(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    code = str(getattr(exc, "error_code", None) or "")
    return code in {"429", "805"}


def jwt_exp_unix(token: str) -> int | None:
    """Unverified ``exp`` claim. Returns None when the value is not a JWT or has no exp."""
    if not token or token.count(".") != 2:
        return None
    payload = token.split(".", 2)[1]
    pad = "=" * (-len(payload) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload + pad)
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    exp = data.get("exp")
    if isinstance(exp, bool) or not isinstance(exp, (int, float)):
        return None
    return int(exp)


def describe_jwt_exp(token: str, *, now: datetime | None = None) -> str:
    """One log line. The token itself is never included."""
    exp = jwt_exp_unix(token)
    if exp is None:
        return "Dhan access token has no JWT exp claim (not a JWT, or exp missing)"
    when = datetime.fromtimestamp(exp, tz=IST)
    clock = now if now is not None else datetime.now(IST)
    clock = clock.replace(tzinfo=IST) if clock.tzinfo is None else clock.astimezone(IST)
    delta = when - clock
    seconds = int(delta.total_seconds())
    if seconds >= 0:
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        rel = f"in {hours}h {minutes}m"
    else:
        hours, rem = divmod(-seconds, 3600)
        minutes = rem // 60
        rel = f"expired {hours}h {minutes}m ago"
    return f"Dhan JWT exp={when.isoformat(timespec='seconds')} ({rel})"


def log_jwt_exp(token: str, *, logger: logging.Logger | None = None, now: datetime | None = None) -> str:
    """Log the exp line. Returns the line so tests can assert without reading handlers."""
    line = describe_jwt_exp(token, now=now)
    (logger or log).info("%s", line)
    return line


def auth_failure_message(what: str, exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    code = getattr(exc, "error_code", None)
    parts = [f"HTTP {status}" if status else "auth failure"]
    if code:
        parts.append(str(code))
    return (
        f"Dhan rejected the credentials while {what} ({', '.join(parts)}). "
        "Stop retrying. Check DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN; access tokens expire every 24 hours."
    )
