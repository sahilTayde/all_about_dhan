"""Redact API keys and token-like strings from any string that might be logged."""

from __future__ import annotations

import re

_KEY_QUERY = re.compile(r"(?i)([?&]key=)[^&\s]+")
_GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_\-]{20,}")
_BEARER = re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._\-]+")


def sanitize(text: str, secret: str = "") -> str:
    """Return text with secrets removed. Never log the original."""
    if not text:
        return text
    out = text
    if secret:
        out = out.replace(secret, "[REDACTED]")
    out = _KEY_QUERY.sub(r"\1[REDACTED]", out)
    out = _GOOGLE_KEY.sub("[REDACTED]", out)
    out = _BEARER.sub(r"\1[REDACTED]", out)
    return out
