"""Mint a 24h Dhan access token via official TOTP generateAccessToken.

Official (do not invent):
  POST https://auth.dhan.co/app/generateAccessToken?dhanClientId=&pin=&totp=
  Response fields: accessToken, expiryTime (~24h). SEBI: no permanent token.

Paper desk only. Writes ``DHAN_ACCESS_TOKEN`` to repo-root ``.env`` — the same
path ``scripts/desk.sh`` ``token_keys_set`` already reads. Never logs PIN, TOTP,
the access token, or the full request URL (secrets live in the query string).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

import httpx
from dotenv import dotenv_values

from dhan_client.config import (
    ENV_ACCESS_TOKEN,
    ENV_CLIENT_ID,
    ENV_PIN,
    ENV_TOTP_SECRET,
    repo_root,
)
from dhan_client.endpoints import AUTH_BASE, GENERATE_ACCESS_TOKEN
from dhan_client.errors import MintError
from dhan_client.logging_util import get_logger

log = get_logger(__name__)

KEYCHAIN_ACCOUNT = "all_about_dhan"
GENERATE_URL = f"{AUTH_BASE.rstrip('/')}{GENERATE_ACCESS_TOKEN}"

HttpPost = Callable[[str, Mapping[str, str]], Mapping[str, Any]]
KeychainGet = Callable[[str], str]


@dataclass(frozen=True)
class VaultMaterial:
    """PIN / TOTP seed never appear in ``repr``."""

    client_id: str
    pin: str = field(repr=False)
    totp_secret: str = field(repr=False)

    @property
    def missing_names(self) -> tuple[str, ...]:
        missing = []
        if not self.client_id:
            missing.append(ENV_CLIENT_ID)
        if not self.pin:
            missing.append(ENV_PIN)
        if not self.totp_secret:
            missing.append(ENV_TOTP_SECRET)
        return tuple(missing)

    @property
    def complete(self) -> bool:
        return not self.missing_names


@dataclass(frozen=True)
class MintCheck:
    env_path: str
    token_key: str
    client_id_set: bool
    pin_set: bool
    totp_secret_set: bool
    totp_secret_valid: bool
    missing_names: tuple[str, ...]
    ready: bool


@dataclass(frozen=True)
class MintResult:
    wrote: bool
    expiry_time: str
    env_path: str
    token_key: str
    token_set: bool


def env_file_path(root: Path | None = None) -> Path:
    """Desk token file: repo-root ``.env`` (see ``scripts/desk.sh`` token_keys_set)."""
    return (root or repo_root()) / ".env"


def totp_secret_valid(secret: str) -> bool:
    raw = str(secret or "").replace(" ", "").strip()
    if not raw:
        return False
    try:
        key = base64.b32decode(raw, casefold=True)
    except (ValueError, TypeError):
        return False
    return bool(key)


def totp_at(secret: str, now: float) -> str:
    """RFC 6238 TOTP (SHA-1, 30s, 6 digits). Empty / bad secret raises."""
    raw = str(secret or "").replace(" ", "").strip()
    if not raw:
        raise MintError("totp_secret_invalid")
    try:
        key = base64.b32decode(raw, casefold=True)
    except (ValueError, TypeError) as exc:
        raise MintError("totp_secret_invalid") from exc
    if not key:
        raise MintError("totp_secret_invalid")
    counter = int(now // 30)
    digest = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def keychain_get(service: str, *, account: str = KEYCHAIN_ACCOUNT) -> str:
    """macOS Keychain only. Never log stdout. Empty on Linux / missing item."""
    if sys.platform != "darwin":
        return ""
    name = str(service or "").strip()
    if not name:
        return ""
    try:
        proc = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                account,
                "-s",
                name,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _read_secret(
    name: str,
    environ: Mapping[str, str],
    keychain: KeychainGet,
) -> str:
    raw = str(environ.get(name) or "").strip()
    if raw:
        return raw
    return str(keychain(name) or "").strip()


def load_vault_material(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
    keychain: KeychainGet | None = None,
    load_file: bool = True,
) -> VaultMaterial:
    merged: dict[str, str] = {}
    path = env_path or env_file_path()
    if load_file and path.is_file():
        for key, value in dotenv_values(path).items():
            if key and value and str(value).strip():
                merged[str(key)] = str(value).strip()
    src = os.environ if environ is None else environ
    for key in (ENV_CLIENT_ID, ENV_PIN, ENV_TOTP_SECRET):
        raw = str(src.get(key) or "").strip()
        if raw:
            merged[key] = raw
    getter = keychain if keychain is not None else keychain_get
    return VaultMaterial(
        client_id=_read_secret(ENV_CLIENT_ID, merged, getter),
        pin=_read_secret(ENV_PIN, merged, getter),
        totp_secret=_read_secret(ENV_TOTP_SECRET, merged, getter),
    )


def check_mint(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
    keychain: KeychainGet | None = None,
    load_file: bool = True,
) -> MintCheck:
    """Validate vault names are present. No HTTP."""
    path = env_path or env_file_path()
    material = load_vault_material(
        environ=environ,
        env_path=path,
        keychain=keychain,
        load_file=load_file,
    )
    secret_ok = totp_secret_valid(material.totp_secret) if material.totp_secret else False
    missing = list(material.missing_names)
    if material.totp_secret and not secret_ok and ENV_TOTP_SECRET not in missing:
        missing.append(ENV_TOTP_SECRET)
    log.info("mint generateAccessToken check-only (no HTTP)")
    return MintCheck(
        env_path=str(path),
        token_key=ENV_ACCESS_TOKEN,
        client_id_set=bool(material.client_id),
        pin_set=bool(material.pin),
        totp_secret_set=bool(material.totp_secret),
        totp_secret_valid=secret_ok,
        missing_names=tuple(missing),
        ready=material.complete and secret_ok,
    )


def upsert_env_key(path: Path, key: str, value: str) -> None:
    """Replace or append ``KEY=value`` in a dotenv file. Never logs the value."""
    if key != ENV_ACCESS_TOKEN:
        raise MintError("write_key_refused")
    if not value or any(ch in value for ch in "\n\r\x00"):
        raise MintError("token_invalid")
    text = ""
    existed = path.is_file()
    if existed:
        text = path.read_text(encoding="utf-8")
    prefix = f"{key}="
    export_prefix = f"export {key}="
    lines = text.splitlines()
    replaced = False
    out: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(prefix) or stripped.startswith(export_prefix):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        if out and out[-1] != "":
            out.append(f"{key}={value}")
        else:
            out.append(f"{key}={value}")
    payload = "\n".join(out)
    if not payload.endswith("\n"):
        payload += "\n"
    tmp = path.with_name(f".{path.name}.mint.tmp")
    tmp.write_text(payload, encoding="utf-8")
    if not existed:
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    tmp.replace(path)


def _safe_expiry(raw: object) -> str:
    text = str(raw or "").strip()
    if text.startswith("eyJ"):
        return "REDACTED"
    return text


def _parse_mint_payload(payload: Mapping[str, Any]) -> tuple[str, str]:
    token = str(payload.get("accessToken") or "").strip()
    if not token:
        raise MintError("access_token_missing")
    if any(ch in token for ch in "\n\r\x00"):
        raise MintError("token_invalid")
    return token, _safe_expiry(payload.get("expiryTime"))


def http_post_generate(url: str, params: Mapping[str, str]) -> Mapping[str, Any]:
    """POST official generateAccessToken. Exceptions never include the URL."""
    if "?" in url or "pin=" in url.lower() or "totp=" in url.lower():
        raise MintError("request_url_must_not_include_query")
    if url != GENERATE_URL:
        raise MintError("request_url_refused")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                params=dict(params),
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError:
        raise MintError("network_error") from None
    try:
        payload: Any = response.json()
    except ValueError:
        payload = None
    if response.status_code >= 400 or not isinstance(payload, dict):
        raise MintError("generate_access_token_failed")
    return payload


def run_mint(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
    keychain: KeychainGet | None = None,
    load_file: bool = True,
    now: float | None = None,
    http_post: HttpPost | None = None,
) -> MintResult:
    """Mint and write ``DHAN_ACCESS_TOKEN``. Refuses if vault material is missing."""
    path = env_path or env_file_path()
    material = load_vault_material(
        environ=environ,
        env_path=path,
        keychain=keychain,
        load_file=load_file,
    )
    if not material.complete:
        names = ",".join(material.missing_names)
        raise MintError(f"vault_material_missing:{names}")
    if not totp_secret_valid(material.totp_secret):
        raise MintError("totp_secret_invalid")
    code = totp_at(material.totp_secret, time.time() if now is None else now)
    params = {
        "dhanClientId": material.client_id,
        "pin": material.pin,
        "totp": code,
    }
    poster = http_post if http_post is not None else http_post_generate
    log.info("mint generateAccessToken POST (query not logged)")
    payload = poster(GENERATE_URL, params)
    token, expiry = _parse_mint_payload(payload)
    upsert_env_key(path, ENV_ACCESS_TOKEN, token)
    log.info("mint wrote DHAN_ACCESS_TOKEN to env file (value not logged)")
    return MintResult(
        wrote=True,
        expiry_time=expiry,
        env_path=str(path),
        token_key=ENV_ACCESS_TOKEN,
        token_set=True,
    )
