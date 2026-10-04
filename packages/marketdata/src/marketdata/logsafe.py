"""Keep credentials out of every log line, at every level.

The feed URL carries ``token=`` and ``clientId=``; at DEBUG the websockets client logs the
handshake request line with it. A filter on the websockets loggers scrubs those records for
any handler (including ones we do not own), and ``RedactingFormatter`` scrubs whatever our
own handlers format, tracebacks included.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

_KEYS = re.compile(r"(?i)\b(token|clientId|client_id|access-token|client-id)(=|:\s*)([^&\s'\",;]+)")
_WEBSOCKETS_LOGGERS = ("websockets", "websockets.client", "websockets.server", "websockets.protocol")
_secrets: set[str] = set()


def redact(text: str) -> str:
    text = _KEYS.sub(lambda m: f"{m.group(1)}{m.group(2)}REDACTED", text)
    for secret in _secrets:
        text = text.replace(secret, "REDACTED")
    return text


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        clean = redact(message)
        if clean != message:
            record.msg, record.args = clean, None
        return True


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


_FILTER = RedactFilter()


def install(secrets: Iterable[str] = ()) -> None:
    """Register secret values and attach the filter to the websockets loggers (idempotent)."""
    _secrets.update(s for s in secrets if s and len(s) >= 4)
    for name in _WEBSOCKETS_LOGGERS:
        logger = logging.getLogger(name)
        if _FILTER not in logger.filters:
            logger.addFilter(_FILTER)
