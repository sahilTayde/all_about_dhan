"""Per-account credential envelopes. Decrypt only when a named account needs a session."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from secretstore.accounts import AccountDirectory, AccountStub, MemoryAccounts
from secretstore.crypto import AgeIdentity, AgeRecipient, load_identity_file, open_envelope, seal
from secretstore.errors import SecretClosed

ACCOUNT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
DEFAULT_ENV_FALLBACK = Path("/etc/aad/aad.env")
FOUNDER_ID = "founder"
_CLIENT_NAME = "DHAN_CLIENT_ID"
_TOKEN_NAME = "DHAN_ACCESS_TOKEN"


class SecretStore(Protocol):
    def credentials_for_session(self, account_id: str) -> BrokerCredential: ...


@dataclass(frozen=True)
class BrokerCredential:
    """In-process only. Repr never prints tokens."""

    account_id: str
    broker: str
    client_id: str
    access_token: str

    def __repr__(self) -> str:
        return f"BrokerCredential(account_id={self.account_id!r}, broker={self.broker!r}, redacted=True)"


class BlobBackend(Protocol):
    name: str

    def get(self, account_id: str) -> bytes: ...


class DiskBlobBackend:
    """Encrypted ``accounts/<id>.sops.json`` files. Never a live secret in git."""

    name = "disk"

    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, account_id: str) -> Path:
        return self.root / "accounts" / f"{account_id}.sops.json"

    def get(self, account_id: str) -> bytes:
        path = self.path_for(account_id)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise SecretClosed("missing_envelope") from exc
        if not data:
            raise SecretClosed("missing_envelope")
        return data

    def put(self, account_id: str, blob: bytes) -> Path:
        path = self.path_for(account_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        return path


class VaultAdapter:
    """Thin HashiCorp Vault interface. Fail closed until configured (V2-24 stub)."""

    name = "vault"

    def get(self, account_id: str) -> bytes:
        raise SecretClosed("adapter_not_configured", "vault")


class OnePasswordConnectAdapter:
    """Thin 1Password Connect interface. Fail closed until configured (V2-24 stub)."""

    name = "onepassword-connect"

    def get(self, account_id: str) -> bytes:
        raise SecretClosed("adapter_not_configured", "onepassword-connect")


def _safe_account_id(account_id: str) -> str:
    if not ACCOUNT_ID_RE.fullmatch(account_id):
        raise SecretClosed("unknown_account", "illegal id")
    return account_id


def credential_from_dict(payload: dict[str, object], *, account_id: str) -> BrokerCredential:
    if payload.get("account_id") != account_id:
        raise SecretClosed("invalid_envelope", "payload account mismatch")
    broker = payload.get("broker")
    client_id = payload.get("client_id")
    token = payload.get("access_token")
    if broker != "dhan" or not isinstance(client_id, str) or not isinstance(token, str):
        raise SecretClosed("invalid_envelope", "payload fields")
    if not client_id or not token:
        raise SecretClosed("invalid_envelope", "empty credential")
    return BrokerCredential(account_id=account_id, broker="dhan", client_id=client_id, access_token=token)


def parse_env_file(text: str, *, account_id: str) -> BrokerCredential:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip("'\"")
    client = values.get(_CLIENT_NAME, "")
    token = values.get(_TOKEN_NAME, "")
    if not client or not token:
        raise SecretClosed("fallback_invalid")
    return BrokerCredential(account_id=account_id, broker="dhan", client_id=client, access_token=token)


class FileSecretStore:
    """Load encrypted blobs + decrypt in-process. Optional ``/etc/aad/aad.env`` founder fallback."""

    def __init__(
        self,
        *,
        backend: BlobBackend,
        identity: AgeIdentity | None,
        accounts: AccountDirectory,
        allow_env_fallback: bool = False,
        env_fallback_path: Path = DEFAULT_ENV_FALLBACK,
        founder_account_id: str = FOUNDER_ID,
    ) -> None:
        self.backend = backend
        self.identity = identity
        self.accounts = accounts
        self.allow_env_fallback = allow_env_fallback
        self.env_fallback_path = env_fallback_path
        self.founder_account_id = founder_account_id

    def put_broker_credentials(self, cred: BrokerCredential, recipient: AgeRecipient) -> Path:
        if not isinstance(self.backend, DiskBlobBackend):
            raise SecretClosed("adapter_not_configured", "put requires disk backend")
        _safe_account_id(cred.account_id)
        payload = {
            "account_id": cred.account_id,
            "broker": cred.broker,
            "client_id": cred.client_id,
            "access_token": cred.access_token,
        }
        blob = seal(recipient, json.dumps(payload, separators=(",", ":")).encode("utf-8"), account_id=cred.account_id)
        return self.backend.put(cred.account_id, blob)

    def credentials_for_session(self, account_id: str) -> BrokerCredential:
        aid = _safe_account_id(account_id)
        self.accounts.require(aid)
        try:
            blob = self.backend.get(aid)
        except SecretClosed as exc:
            if exc.reason == "missing_envelope":
                return self._fallback(aid)
            raise
        if self.identity is None:
            raise SecretClosed("missing_identity")
        plain = open_envelope(self.identity, blob, account_id=aid)
        try:
            payload = json.loads(plain.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SecretClosed("invalid_envelope") from exc
        if not isinstance(payload, dict):
            raise SecretClosed("invalid_envelope")
        return credential_from_dict(payload, account_id=aid)

    def put_hmac_secret(self, name: str, value: str, recipient: AgeRecipient) -> Path:
        """Seal a named HMAC (JWT signing key). Not a broker credential. Disk only."""
        if not isinstance(self.backend, DiskBlobBackend):
            raise SecretClosed("adapter_not_configured", "put requires disk backend")
        aid = _safe_account_id(name)
        secret = str(value or "").strip()
        if not secret:
            raise SecretClosed("invalid_envelope", "empty hmac")
        payload = {"kind": "hmac", "name": aid, "value": secret}
        blob = seal(recipient, json.dumps(payload, separators=(",", ":")).encode("utf-8"), account_id=f"sys.{aid}")
        path = self.backend.root / "system" / f"{aid}.sops.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        return path

    def hmac_secret(self, name: str) -> str:
        """Decrypt a named HMAC. Fail closed. Never used on the JWT verify hot path."""
        if not isinstance(self.backend, DiskBlobBackend):
            raise SecretClosed("adapter_not_configured", "hmac requires disk backend")
        aid = _safe_account_id(name)
        path = self.backend.root / "system" / f"{aid}.sops.json"
        try:
            blob = path.read_bytes()
        except OSError as exc:
            raise SecretClosed("missing_envelope") from exc
        if self.identity is None:
            raise SecretClosed("missing_identity")
        plain = open_envelope(self.identity, blob, account_id=f"sys.{aid}")
        try:
            payload = json.loads(plain.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SecretClosed("invalid_envelope") from exc
        if not isinstance(payload, dict) or payload.get("kind") != "hmac" or payload.get("name") != aid:
            raise SecretClosed("invalid_envelope", "hmac payload")
        value = payload.get("value")
        if not isinstance(value, str) or not value.strip():
            raise SecretClosed("invalid_envelope", "empty hmac")
        return value.strip()

    def _fallback(self, account_id: str) -> BrokerCredential:
        if not self.allow_env_fallback or account_id != self.founder_account_id:
            raise SecretClosed("missing_envelope" if not self.allow_env_fallback else "fallback_disabled")
        try:
            text = self.env_fallback_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SecretClosed("fallback_invalid") from exc
        return parse_env_file(text, account_id=account_id)


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def open_store(
    *,
    secrets_dir: Path,
    identity: AgeIdentity | None,
    accounts: AccountDirectory | None = None,
    allow_env_fallback: bool = False,
    env_fallback_path: Path = DEFAULT_ENV_FALLBACK,
) -> FileSecretStore:
    directory = accounts or MemoryAccounts([AccountStub(FOUNDER_ID, kind="founder")])
    return FileSecretStore(
        backend=DiskBlobBackend(secrets_dir),
        identity=identity,
        accounts=directory,
        allow_env_fallback=allow_env_fallback,
        env_fallback_path=env_fallback_path,
    )


def open_store_from_env(
    *,
    accounts: AccountDirectory | None = None,
    secrets_dir: Path | None = None,
    identity_path: Path | None = None,
    env_fallback_path: Path | None = None,
) -> FileSecretStore:
    root = secrets_dir or Path(os.environ.get("AAD_SECRETS_DIR", "secrets/v2"))
    ident_s = os.environ.get("AAD_AGE_IDENTITY_FILE") if identity_path is None else str(identity_path)
    identity: AgeIdentity | None = None
    if ident_s:
        identity = load_identity_file(ident_s)
    fallback = env_fallback_path or Path(os.environ.get("AAD_ENV_FALLBACK", str(DEFAULT_ENV_FALLBACK)))
    return open_store(
        secrets_dir=root,
        identity=identity,
        accounts=accounts,
        allow_env_fallback=env_flag("AAD_SECRETS_ALLOW_ENV_FALLBACK"),
        env_fallback_path=fallback,
    )
