"""Load the JWT HMAC key. Env / file first; secretstore next. Never write secrets.

Empty key is a deny. Values are never logged. Paper only.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from auth.foundation import AuthClosed

JWT_ENV = "AAD_JWT_SECRET"
JWT_FILE_ENV = "AAD_JWT_SECRET_FILE"
JWT_STORE_ID_ENV = "AAD_JWT_SECRET_STORE_ID"
DEFAULT_STORE_ID = "jwt"
TOTP_ENV = "AAD_FOUNDER_TOTP_SECRET"
TOTP_FILE_ENV = "AAD_FOUNDER_TOTP_SECRET_FILE"


def read_env_or_file(env_name: str, file_env: str, *, environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    path = str(env.get(file_env, "") or "").strip()
    if path:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            return ""
        return text.splitlines()[0].strip() if text else ""
    return str(env.get(env_name, "") or "").strip()


def _from_secretstore(*, environ: Mapping[str, str] | None = None, store: object | None = None) -> str:
    env = os.environ if environ is None else environ
    name = str(env.get(JWT_STORE_ID_ENV, DEFAULT_STORE_ID) or DEFAULT_STORE_ID).strip() or DEFAULT_STORE_ID
    try:
        from secretstore.errors import SecretClosed
    except ImportError:
        return ""
    holder = store
    if holder is None:
        if not (env.get("AAD_SECRETS_DIR") or env.get("AAD_AGE_IDENTITY_FILE")):
            return ""
        try:
            from secretstore import open_store_from_env
        except ImportError:
            return ""
        try:
            holder = open_store_from_env()
        except SecretClosed:
            return ""
    getter = getattr(holder, "hmac_secret", None)
    if not callable(getter):
        return ""
    try:
        value = getter(name)
    except SecretClosed:
        return ""
    return str(value or "").strip()


def load_jwt_secret(*, environ: Mapping[str, str] | None = None, store: object | None = None) -> str:
    """Return the signing key or "". Never raises. Never logs the value."""
    got = read_env_or_file(JWT_ENV, JWT_FILE_ENV, environ=environ)
    if got:
        return got
    return _from_secretstore(environ=environ, store=store)


def require_jwt_secret(*, environ: Mapping[str, str] | None = None, store: object | None = None) -> str:
    secret = load_jwt_secret(environ=environ, store=store)
    if not secret:
        raise AuthClosed("jwt_secret_missing")
    return secret


def load_totp_secret(*, environ: Mapping[str, str] | None = None) -> str:
    return read_env_or_file(TOTP_ENV, TOTP_FILE_ENV, environ=environ)


__all__ = [
    "DEFAULT_STORE_ID",
    "JWT_ENV",
    "JWT_FILE_ENV",
    "JWT_STORE_ID_ENV",
    "TOTP_ENV",
    "TOTP_FILE_ENV",
    "load_jwt_secret",
    "load_totp_secret",
    "read_env_or_file",
    "require_jwt_secret",
]
