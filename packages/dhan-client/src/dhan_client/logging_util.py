"""Logging helpers. Never print tokens, secrets, or Authorization-like headers."""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SECRET_KEY_RE = re.compile(
    r"(token|secret|password|passwd|authorization|api[_-]?key|pin|totp)",
    re.IGNORECASE,
)

_REDACTED = "REDACTED"


def is_secret_key(name: str) -> bool:
    return bool(_SECRET_KEY_RE.search(name))


def redact_value(_value: Any) -> str:
    return _REDACTED


def redact_mapping(data: Mapping[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    out: dict[str, Any] = {}
    for key, value in data.items():
        if is_secret_key(str(key)):
            out[key] = _REDACTED
        elif isinstance(value, Mapping):
            out[key] = redact_mapping(value)
        else:
            out[key] = value
    return out


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    if not parts.query:
        return url
    redacted = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if is_secret_key(key) or key.lower() in {"token", "clientid"}:
            redacted.append((key, _REDACTED))
        else:
            redacted.append((key, value))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(redacted), parts.fragment)
    )


class RedactingFilter(logging.Filter):
    """Last-line filter: drop records that look like they contain a JWT."""

    _jwtish = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\.")

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if self._jwtish.search(msg):
            record.msg = "[redacted: possible secret in log record]"
            record.args = ()
        return True


def get_logger(name: str = "dhan_client") -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
    return logger


def secret_keys_present(names: Iterable[str]) -> list[str]:
    """Return env *names* that look secret and are non-empty. Never return values."""
    import os

    present = []
    for name in names:
        raw = os.environ.get(name)
        if raw is not None and str(raw).strip():
            present.append(name)
    return present
