"""V2 gateway auth: bearer / WS token, Host/Origin, bind, rate limit, JWT names.

Paper only. JWT / founder 2FA verify lives in ``packages/auth`` (V2-23).
No secrets in logs. Legacy /paper/* and /founder/* are not gated here.

Token sources (names only): AAD_GATEWAY_TOKEN, AAD_GATEWAY_TOKEN_FILE,
AAD_GATEWAY_CUSTOMER_TOKEN, AAD_GATEWAY_CUSTOMER_TOKEN_FILE,
AAD_JWT_SECRET, AAD_JWT_SECRET_FILE, AAD_FOUNDER_TOTP_SECRET,
AAD_FOUNDER_TOTP_SECRET_FILE.
Empty + bind 127.0.0.1 = localhost-dev (Mac, no token). Query string is
never an auth channel. Mutating control commands are rate-limited (1/s).
``uvicorn --host`` is read at create_app time so ``0.0.0.0`` fails closed
without a token.
"""

from __future__ import annotations

import hmac
import logging
import os
import re
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

TOKEN_ENV = "AAD_GATEWAY_TOKEN"
TOKEN_FILE_ENV = "AAD_GATEWAY_TOKEN_FILE"
CUSTOMER_TOKEN_ENV = "AAD_GATEWAY_CUSTOMER_TOKEN"
CUSTOMER_TOKEN_FILE_ENV = "AAD_GATEWAY_CUSTOMER_TOKEN_FILE"
JWT_ENV = "AAD_JWT_SECRET"
JWT_FILE_ENV = "AAD_JWT_SECRET_FILE"
TOTP_ENV = "AAD_FOUNDER_TOTP_SECRET"
TOTP_FILE_ENV = "AAD_FOUNDER_TOTP_SECRET_FILE"
BIND_ENV = "AAD_GATEWAY_BIND"
HOSTS_ENV = "AAD_GATEWAY_HOSTS"
ORIGINS_ENV = "AAD_GATEWAY_ORIGINS"
RATE_ENV = "AAD_GATEWAY_CONTROL_RATE_PER_S"
DEFAULT_BIND = "127.0.0.1"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
LOOPBACK_BINDS = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_ORIGIN_PORTS = frozenset({80, 443, 3000, 5173, 8000})
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_IPV4 = re.compile(
    r"^(?:25[0-5]|2[0-4]\d|1?\d?\d)\.(?:25[0-5]|2[0-4]\d|1?\d?\d)\."
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\.(?:25[0-5]|2[0-4]\d|1?\d?\d)$"
)
log = logging.getLogger("api.v2.control")


@dataclass(frozen=True)
class HostPort:
    host: str
    port: int | None


@dataclass(frozen=True)
class AuthIdentity:
    role: str
    source: str
    subprotocol: str | None = None


@dataclass
class GatewayAuth:
    founder_token: str
    customer_token: str
    bind_host: str
    extra_hosts: frozenset[str]
    extra_origins: frozenset[str]
    control_rate_per_s: float
    jwt_secret: str = ""
    totp_secret: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.founder_token or self.customer_token or self.jwt_secret)

    @property
    def jwt_required(self) -> bool:
        return bool(self.jwt_secret)

    @property
    def localhost_dev(self) -> bool:
        return (not self.configured) and is_loopback_bind(self.bind_host)

    @property
    def auth_required(self) -> bool:
        return self.configured


def is_loopback_host(host: str) -> bool:
    return host.lower() in LOOPBACK_HOSTS


def is_loopback_bind(host: str) -> bool:
    return host.strip().lower() in LOOPBACK_BINDS


def parse_host_header(header: str | None) -> HostPort | None:
    """Parse Host as host[:port] exactly. Look-alikes (port junk, extra dots) → None."""
    raw = str(header or "").strip().lower()
    if (
        not raw
        or any(ch.isspace() for ch in raw)
        or "/" in raw
        or "@" in raw
        or "#" in raw
    ):
        return None
    if raw.startswith("["):
        end = raw.find("]")
        if end < 2:
            return None
        host = raw[1:end]
        rest = raw[end + 1 :]
        if not host or ":" not in host:
            return None
        if rest == "":
            return HostPort(host, None) if _host_ok(host) else None
        if not rest.startswith(":"):
            return None
        return _with_port(host, rest[1:])
    if raw.count(":") > 1:
        return None
    if ":" in raw:
        host, port_s = raw.rsplit(":", 1)
        return _with_port(host, port_s)
    return HostPort(raw, None) if _host_ok(raw) else None


def _with_port(host: str, port_s: str) -> HostPort | None:
    if not host or not port_s.isdigit() or (len(port_s) > 1 and port_s.startswith("0")):
        return None
    port = int(port_s)
    if port < 1 or port > 65535:
        return None
    return HostPort(host, port) if _host_ok(host) else None


def _host_ok(host: str) -> bool:
    if host in LOOPBACK_HOSTS:
        return True
    if _IPV4.fullmatch(host):
        return True
    if host.startswith(".") or host.endswith(".") or ".." in host or "_" in host:
        return False
    labels = host.split(".")
    return bool(labels) and all(_HOST_LABEL.fullmatch(part) for part in labels)


def parse_origin(header: str | None) -> HostPort | None:
    """Parse Origin. Reject userinfo, query, fragment, look-alike hosts."""
    raw = str(header or "").strip()
    if not raw:
        return None
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"}:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    if parts.path not in {"", "/"} or parts.query or parts.fragment:
        return None
    return parse_host_header(parts.netloc)


def _read_secret(env_name: str, file_env: str) -> str:
    path = os.environ.get(file_env, "").strip()
    if path:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            return ""
        line = text.splitlines()[0].strip() if text else ""
        return line
    return os.environ.get(env_name, "").strip()


def load_gateway_auth() -> GatewayAuth:
    extra_hosts = frozenset(
        p.strip().lower() for p in os.environ.get(HOSTS_ENV, "").split(",") if p.strip()
    )
    extra_origins = frozenset(
        p.strip() for p in os.environ.get(ORIGINS_ENV, "").split(",") if p.strip()
    )
    try:
        rate = float(os.environ.get(RATE_ENV, "1") or "1")
    except ValueError:
        rate = 1.0
    if rate <= 0:
        rate = 1.0
    bind = os.environ.get(BIND_ENV, DEFAULT_BIND).strip() or DEFAULT_BIND
    return GatewayAuth(
        founder_token=_read_secret(TOKEN_ENV, TOKEN_FILE_ENV),
        customer_token=_read_secret(CUSTOMER_TOKEN_ENV, CUSTOMER_TOKEN_FILE_ENV),
        bind_host=bind,
        extra_hosts=extra_hosts,
        extra_origins=extra_origins,
        control_rate_per_s=rate,
        jwt_secret=_read_secret(JWT_ENV, JWT_FILE_ENV),
        totp_secret=_read_secret(TOTP_ENV, TOTP_FILE_ENV),
    )


def bind_host_from_argv(argv: list[str] | None = None) -> str | None:
    """Return ``uvicorn --host`` / ``--host=`` from argv, else None. Not ``-h``."""
    args = list(sys.argv if argv is None else argv)
    for i, item in enumerate(args):
        if item == "--host" and i + 1 < len(args):
            return args[i + 1]
        if item.startswith("--host="):
            return item.split("=", 1)[1]
    return None


def effective_bind_host(env_bind: str, argv: list[str] | None = None) -> str:
    """CLI ``--host`` wins over ``AAD_GATEWAY_BIND`` so uvicorn cannot bypass."""
    cli = bind_host_from_argv(argv)
    if cli is not None and cli.strip():
        return cli.strip()
    return env_bind


def assert_bind_allowed(host: str, auth_configured: bool) -> None:
    """Refuse 0.0.0.0 / non-loopback unless a gateway token is configured."""
    name = (host or "").strip().lower()
    if is_loopback_bind(name):
        return
    if not auth_configured:
        raise ValueError(
            f"refusing bind {host!r} without {TOKEN_ENV} / {TOKEN_FILE_ENV}"
        )


def _digest(value: str) -> bytes:
    return hmac.new(b"aad-gateway-auth-v1", value.encode(), "sha256").digest()


def tokens_match(provided: str | None, expected: str) -> bool:
    """Constant-time compare. Empty expected never matches."""
    if not expected:
        return False
    got = _digest(str(provided or ""))
    want = _digest(expected)
    return hmac.compare_digest(got, want)


def identity_from_token(
    provided: str | None, settings: GatewayAuth
) -> AuthIdentity | None:
    if not provided:
        return None
    founder = tokens_match(provided, settings.founder_token)
    customer = tokens_match(provided, settings.customer_token)
    if founder:
        return AuthIdentity(role="founder", source="token")
    if customer:
        return AuthIdentity(role="customer", source="token")
    return None


def bearer_from_authorization(header: str | None) -> str | None:
    raw = str(header or "")
    if len(raw) < 8 or raw[:7].lower() != "bearer ":
        return None
    token = raw[7:].strip()
    return token or None


def tokens_from_protocol(header: str | None) -> list[tuple[str, str]]:
    """Return (offered_protocol, candidate_token) pairs. Never logs values."""
    out: list[tuple[str, str]] = []
    for part in str(header or "").split(","):
        offered = part.strip()
        if not offered:
            continue
        token = offered
        low = offered.lower()
        if low.startswith("bearer."):
            token = offered[7:]
        elif low.startswith("v2."):
            token = offered[3:]
        if token:
            out.append((offered, token))
    return out


def identity_from_headers(
    authorization: str | None,
    protocol: str | None,
    settings: GatewayAuth,
) -> AuthIdentity | None:
    ident = identity_from_token(bearer_from_authorization(authorization), settings)
    if ident is not None:
        return ident
    for offered, token in tokens_from_protocol(protocol):
        ident = identity_from_token(token, settings)
        if ident is not None:
            return AuthIdentity(
                role=ident.role, source="ws-protocol", subprotocol=offered
            )
    return None


def query_has_auth_attempt(query: str | None) -> bool:
    """True when a client tried to pass a credential on the URL (always refuse)."""
    raw = str(query or "").lstrip("?")
    if not raw:
        return False
    for pair in raw.split("&"):
        key = pair.split("=", 1)[0].strip().lower()
        if key in {"access_token", "authorization", "auth", "bearer"}:
            return True
    return False


def host_allowed(parsed: HostPort | None, settings: GatewayAuth) -> bool:
    if parsed is None:
        return False
    if is_loopback_host(parsed.host):
        return True
    exact = parsed.host if parsed.port is None else f"{parsed.host}:{parsed.port}"
    return parsed.host in settings.extra_hosts or exact in settings.extra_hosts


def origin_allowed(header: str | None, settings: GatewayAuth) -> bool:
    if header is None or str(header).strip() == "":
        return True
    parsed = parse_origin(header)
    if parsed is None:
        return False
    raw = str(header).strip()
    if raw in settings.extra_origins:
        return True
    return is_loopback_host(parsed.host) and (
        parsed.port is None or parsed.port in DEFAULT_ORIGIN_PORTS
    )


def check_host_origin(
    host: str | None, origin: str | None, settings: GatewayAuth
) -> str | None:
    """None if ok, else a short reason (no header values)."""
    parsed = parse_host_header(host)
    if not host_allowed(parsed, settings):
        return "bad_host"
    if not origin_allowed(origin, settings):
        return "bad_origin"
    return None


class CommandRateLimiter:
    """Mutating control commands are rate-limited (1/s). GET is not. Redis later."""

    def __init__(
        self,
        *,
        per_s: float = 1.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.per_s = per_s if per_s > 0 else 1.0
        self._clock = clock or time.monotonic
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < 1.0]
            if len(hits) >= self.per_s:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


def audit_control(
    *,
    result: str,
    kind: str | None = None,
    method: str = "POST",
    path: str = "/v2/control/commands",
) -> None:
    """One line per control command. Never log tokens or headers."""
    log.info(
        "control_command method=%s path=%s kind=%s result=%s",
        method,
        path,
        kind or "-",
        result,
    )


__all__ = [
    "BIND_ENV",
    "CUSTOMER_TOKEN_ENV",
    "CUSTOMER_TOKEN_FILE_ENV",
    "DEFAULT_BIND",
    "JWT_ENV",
    "JWT_FILE_ENV",
    "TOKEN_ENV",
    "TOKEN_FILE_ENV",
    "TOTP_ENV",
    "TOTP_FILE_ENV",
    "AuthIdentity",
    "CommandRateLimiter",
    "GatewayAuth",
    "HostPort",
    "assert_bind_allowed",
    "audit_control",
    "bearer_from_authorization",
    "bind_host_from_argv",
    "check_host_origin",
    "effective_bind_host",
    "identity_from_headers",
    "identity_from_token",
    "is_loopback_bind",
    "is_loopback_host",
    "load_gateway_auth",
    "origin_allowed",
    "parse_host_header",
    "parse_origin",
    "query_has_auth_attempt",
    "tokens_from_protocol",
    "tokens_match",
]
