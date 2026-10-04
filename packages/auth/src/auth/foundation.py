"""V2-23 fail-closed auth stubs. Paper only. No secrets logged. No live orders.

ponytail: stdlib HS256 JWT + RFC 6238 TOTP; ceiling = paper/M2 control+gateway.
Upgrade to pyjwt + argon2 + secret store in V2-24.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

ISS = "aad-auth"
AUD = "aad-v2"
ACCESS_TTL_S = 900
REFRESH_TTL_S = 7 * 24 * 3600
# C5-02 paper host: 5 customers + founder. Per-identity caps stay cheap in-process.
PAPER_CUSTOMER_CAP = 5
PAPER_IDENTITY_CAP = PAPER_CUSTOMER_CAP + 1
REST_PER_S = 10
WS_SUBSCRIBE_PER_S = 5
COMMAND_PER_S = 1
CUSTOMER_CHANNELS = frozenset({"signals:public"})
FOUNDER_CHANNELS = (
    frozenset(
        {
            "positions",
            "decisions",
            "health",
            "trace",
            "market:NIFTY",
            "market:BANKNIFTY",
            "market:SENSEX",
        }
    )
    | CUSTOMER_CHANNELS
)
CUSTOMER_SIGNAL_FIELDS = frozenset({"underlying", "side", "decision", "trend", "chain_3m", "news", "cited_news"})
Role = Literal["founder", "customer"]
TokenTyp = Literal["access", "refresh"]
RateBucket = Literal["rest", "ws_subscribe", "command"]
_RATE_CAP: dict[str, int] = {
    "rest": REST_PER_S,
    "ws_subscribe": WS_SUBSCRIBE_PER_S,
    "command": COMMAND_PER_S,
}


class AuthClosed(ValueError):
    """Issue/verify refused. Callers must deny."""


@dataclass(frozen=True)
class AuthDecision:
    ok: bool
    role: str = ""
    sub: str = ""
    typ: str = ""
    tfa: bool = False
    reason: str = ""
    source: str = "jwt"
    channels: tuple[str, ...] = ()

    def denied(self, reason: str) -> AuthDecision:
        return AuthDecision(ok=False, reason=reason, source=self.source)


@dataclass(frozen=True)
class TokenPair:
    """Issued access+refresh. Repr never prints tokens."""

    access: str
    refresh: str
    role: str
    sub: str
    channels: tuple[str, ...]
    expires_in: int = ACCESS_TTL_S

    def __repr__(self) -> str:
        return f"TokenPair(role={self.role!r}, sub={self.sub!r}, redacted=True)"

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "role": self.role,
            "sub": self.sub,
            "channels": list(self.channels),
            "access": self.access,
            "refresh": self.refresh,
            "expires_in": self.expires_in,
            "orders": "REFUSED",
        }


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_json(obj: dict[str, Any]) -> str:
    return _b64url(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode())


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def looks_like_jwt(token: str | None) -> bool:
    raw = str(token or "")
    parts = raw.split(".")
    return len(parts) == 3 and all(parts) and "/" not in raw and " " not in raw


def encode_jwt(claims: dict[str, Any], secret: str) -> str:
    if not secret:
        raise AuthClosed("jwt_secret_missing")
    header = _b64url_json({"alg": "HS256", "typ": "JWT"})
    payload = _b64url_json(claims)
    sig = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def _deny(reason: str) -> AuthDecision:
    return AuthDecision(ok=False, reason=reason)


def verify_jwt(token: str | None, secret: str, now: float) -> AuthDecision:
    """Fail closed: missing secret, bad shape, bad sig, expiry, aud/iss/role/typ."""
    if not secret:
        return _deny("jwt_secret_missing")
    if not looks_like_jwt(token):
        return _deny("unauthorized")
    header_b64, payload_b64, sig_b64 = str(token).split(".")
    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
        got = _b64url_decode(sig_b64)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return _deny("unauthorized")
    if not isinstance(header, dict) or not isinstance(payload, dict):
        return _deny("unauthorized")
    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        return _deny("unauthorized")
    expect = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(got, expect):
        return _deny("unauthorized")
    try:
        exp = int(payload["exp"])
        iat = int(payload["iat"])
    except (KeyError, TypeError, ValueError):
        return _deny("unauthorized")
    if now > exp or exp < iat:
        return _deny("expired")
    if payload.get("iss") != ISS or payload.get("aud") != AUD:
        return _deny("unauthorized")
    role = payload.get("role")
    typ = payload.get("typ")
    sub = str(payload.get("sub") or "")
    if role not in {"founder", "customer"} or typ not in {"access", "refresh"} or not sub:
        return _deny("unauthorized")
    allowed = channels_for(str(role), typ=str(typ))
    claimed = _channels_claim(payload.get("channels"), allowed=allowed, role=str(role), typ=str(typ))
    if claimed is None:
        return _deny("unauthorized")
    tfa = bool(payload.get("tfa")) and role == "founder" and typ == "access"
    return AuthDecision(
        ok=True,
        role=str(role),
        sub=sub,
        typ=str(typ),
        tfa=tfa,
        source="jwt",
        channels=tuple(sorted(claimed)),
    )


def _channels_claim(raw: Any, *, allowed: frozenset[str], role: str, typ: str) -> frozenset[str] | None:
    """Customer access claims must be signals:public only. Legacy tokens omit channels."""
    if raw is None:
        return allowed
    if not isinstance(raw, list) or not all(isinstance(item, str) and item for item in raw):
        return None
    claimed = frozenset(raw)
    if not claimed <= allowed:
        return None
    if role == "customer" and typ == "access" and claimed != CUSTOMER_CHANNELS:
        return None
    if typ == "refresh" and claimed:
        return None
    return claimed


def verify_access(token: str | None, secret: str, now: float) -> AuthDecision:
    decision = verify_jwt(token, secret, now)
    if not decision.ok:
        return decision
    if decision.typ != "access":
        return decision.denied("refresh_forbidden")
    return decision


def issue_access(
    secret: str,
    *,
    role: str,
    sub: str,
    now: float,
    tfa: bool = False,
    totp_secret: str = "",
    totp_code: str = "",
) -> str:
    if not secret:
        raise AuthClosed("jwt_secret_missing")
    if role not in {"founder", "customer"} or not str(sub).strip():
        raise AuthClosed("bad_identity")
    tfa_ok = False
    if tfa:
        if role != "founder":
            raise AuthClosed("tfa_customer")
        if not verify_totp(totp_secret, totp_code, now):
            raise AuthClosed("tfa_failed")
        tfa_ok = True
    chans = tuple(sorted(channels_for(role, typ="access")))
    return encode_jwt(
        {
            "iss": ISS,
            "aud": AUD,
            "sub": str(sub).strip(),
            "role": role,
            "typ": "access",
            "tfa": tfa_ok,
            "channels": list(chans),
            "iat": int(now),
            "exp": int(now) + ACCESS_TTL_S,
        },
        secret,
    )


def issue_refresh(secret: str, *, role: str, sub: str, now: float) -> str:
    if not secret or role not in {"founder", "customer"} or not str(sub).strip():
        raise AuthClosed("jwt_secret_missing" if not secret else "bad_identity")
    return encode_jwt(
        {
            "iss": ISS,
            "aud": AUD,
            "sub": str(sub).strip(),
            "role": role,
            "typ": "refresh",
            "tfa": False,
            "channels": [],
            "iat": int(now),
            "exp": int(now) + REFRESH_TTL_S,
        },
        secret,
    )


def issue_pair(
    secret: str,
    *,
    role: str,
    sub: str,
    now: float,
    tfa: bool = False,
    totp_secret: str = "",
    totp_code: str = "",
) -> TokenPair:
    """Issue access+refresh. Customer channels stay signals:public. Empty secret denies."""
    access = issue_access(
        secret,
        role=role,
        sub=sub,
        now=now,
        tfa=tfa,
        totp_secret=totp_secret,
        totp_code=totp_code,
    )
    refresh = issue_refresh(secret, role=role, sub=sub, now=now)
    return TokenPair(
        access=access,
        refresh=refresh,
        role=role,
        sub=str(sub).strip(),
        channels=tuple(sorted(channels_for(role, typ="access"))),
        expires_in=ACCESS_TTL_S,
    )


def refresh_to_access(refresh_token: str | None, secret: str, now: float) -> str:
    decision = verify_jwt(refresh_token, secret, now)
    if not decision.ok:
        raise AuthClosed(decision.reason)
    if decision.typ != "refresh":
        raise AuthClosed("not_refresh")
    return issue_access(secret, role=decision.role, sub=decision.sub, now=now, tfa=False)


def _hotp(key: bytes, counter: int, digits: int = 6) -> str:
    digest = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return f"{code % (10**digits):0{digits}d}"


def verify_totp(secret: str, code: str, now: float, *, window: int = 1) -> bool:
    """Fail closed: empty seed, bad base32, or non-digit code never match."""
    raw = str(secret or "").replace(" ", "").strip()
    got = str(code or "").strip()
    if not raw or not got.isdigit() or len(got) != 6:
        return False
    try:
        key = base64.b32decode(raw, casefold=True)
    except (ValueError, TypeError):
        return False
    if not key:
        return False
    counter = int(now // 30)
    return any(hmac.compare_digest(_hotp(key, counter + delta), got) for delta in range(-window, window + 1))


def totp_at(secret: str, now: float) -> str:
    """Test helper. Empty seed raises (never mint a code from nothing)."""
    raw = str(secret or "").replace(" ", "").strip()
    if not raw:
        raise AuthClosed("totp_secret_missing")
    key = base64.b32decode(raw, casefold=True)
    if not key:
        raise AuthClosed("totp_secret_missing")
    return _hotp(key, int(now // 30))


def channels_for(role: str, *, typ: str = "access") -> frozenset[str]:
    if typ != "access":
        return frozenset()
    if role == "founder":
        return FOUNDER_CHANNELS
    if role == "customer":
        return CUSTOMER_CHANNELS
    return frozenset()


def allow_channel(role: str, channel: str, *, typ: str = "access") -> bool:
    return channel in channels_for(role, typ=typ)


def customer_safe(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: payload[k] for k in CUSTOMER_SIGNAL_FIELDS if k in payload and payload[k] is not None}


def authorize_control(decision: AuthDecision | None, kind: str = "") -> str | None:
    """None if founder access+2FA. Else a short reason. Fail closed."""
    del kind
    if decision is None or not decision.ok:
        return (decision.reason if decision is not None else None) or "unauthorized"
    if decision.typ != "access":
        return "refresh_forbidden"
    if decision.role != "founder":
        return "founder_only"
    if not decision.tfa:
        return "tfa_required"
    return None


class AuthRateLimiter:
    """In-memory token buckets for 5 paper customers + founder. Redis later.

    Caps: REST 10/s, WS subscribe 5/s, commands 1/s. Verify path never touches this.
    """

    def __init__(self, *, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._hits: dict[tuple[str, str], list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, bucket: RateBucket) -> bool:
        cap = _RATE_CAP[bucket]
        now = self._clock()
        slot = (bucket, key)
        with self._lock:
            hits = [t for t in self._hits.get(slot, []) if now - t < 1.0]
            if len(hits) >= cap:
                self._hits[slot] = hits
                return False
            hits.append(now)
            self._hits[slot] = hits
            return True


__all__ = [
    "ACCESS_TTL_S",
    "AUD",
    "COMMAND_PER_S",
    "CUSTOMER_CHANNELS",
    "CUSTOMER_SIGNAL_FIELDS",
    "FOUNDER_CHANNELS",
    "ISS",
    "PAPER_CUSTOMER_CAP",
    "PAPER_IDENTITY_CAP",
    "REFRESH_TTL_S",
    "REST_PER_S",
    "WS_SUBSCRIBE_PER_S",
    "AuthClosed",
    "AuthDecision",
    "AuthRateLimiter",
    "TokenPair",
    "allow_channel",
    "authorize_control",
    "channels_for",
    "customer_safe",
    "encode_jwt",
    "issue_access",
    "issue_pair",
    "issue_refresh",
    "looks_like_jwt",
    "refresh_to_access",
    "totp_at",
    "verify_access",
    "verify_jwt",
    "verify_totp",
]
