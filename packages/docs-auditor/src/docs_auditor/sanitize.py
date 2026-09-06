"""Strip secret-shaped values from auditor output. Never read `.env`."""

from __future__ import annotations

import re

# Names only. Do not capture values.
_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|"
    r"client[_-]?id|password|authorization|bearer|secret)\b(\s*[:=]\s*)(\S+)"
)
_LONG_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{40,}\b")
_ENV_FILE_HINT = re.compile(r"(?i)(\.env(?:\.\w+)?\s*[:=]\s*)(\S+)")


def sanitize(text: str) -> str:
    """Replace credential-shaped substrings. Safe to write to markdown."""
    if not text:
        return text
    out = _ASSIGNMENT.sub(lambda m: f"{m.group(1)}{m.group(2)}***", text)
    out = _ENV_FILE_HINT.sub(lambda m: f"{m.group(1)}***", out)
    out = _LONG_TOKEN.sub("***", out)
    return out
