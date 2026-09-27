"""Single-use confirm tokens for destructive founder commands (120 s)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
from typing import Any

TOKEN_TTL_S = 120


class ConfirmTokens:
    """HMAC tokens bound to (kind, target). A restart voids them."""

    def __init__(self) -> None:
        self._key = secrets.token_bytes(32)
        self._used: dict[str, float] = {}
        self._lock = threading.Lock()

    def _sig(self, kind: str, target: str, exp: int, nonce: str) -> str:
        return hmac.new(self._key, f"{kind}|{target}|{exp}|{nonce}".encode(), hashlib.sha256).hexdigest()[:32]

    def issue(self, kind: str, target: str | None, now: float) -> dict[str, Any]:
        exp, nonce = int(now) + TOKEN_TTL_S, secrets.token_hex(8)
        token = f"{exp}.{nonce}.{self._sig(kind, target or '', exp, nonce)}"
        return {"confirm_token": token, "expires_in_s": TOKEN_TTL_S}

    def consume(self, token: str | None, kind: str, target: str | None, now: float) -> str | None:
        """None when valid and spent; otherwise why not."""
        try:
            exp_s, nonce, sig = str(token or "").split(".")
            exp = int(exp_s)
        except ValueError:
            return "missing or malformed confirmation token"
        if not hmac.compare_digest(sig, self._sig(kind, target or "", exp, nonce)):
            return "confirmation token is for a different command"
        if now > exp:
            return "confirmation token expired"
        with self._lock:
            self._used = {t: e for t, e in self._used.items() if e >= now}
            if token in self._used:
                return "confirmation token already used"
            self._used[str(token)] = float(exp)
        return None
