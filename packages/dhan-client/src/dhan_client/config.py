"""Load DhanHQ credentials from the environment. Never log secret values."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from dhan_client.endpoints import API_BASE, AUTH_BASE, FEED_WS_BASE
from dhan_client.errors import CredentialsError
from dhan_client.logging_util import get_logger

log = get_logger(__name__)

ENV_CLIENT_ID = "DHAN_CLIENT_ID"
ENV_ACCESS_TOKEN = "DHAN_ACCESS_TOKEN"
ENV_REFRESH_TOKEN = "DHAN_REFRESH_TOKEN"
ENV_CLIENT_SECRET = "DHAN_CLIENT_SECRET"

_SECRET_ENV_NAMES = (
    ENV_ACCESS_TOKEN,
    ENV_REFRESH_TOKEN,
    ENV_CLIENT_SECRET,
)


def repo_root() -> Path:
    start = Path(__file__).resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "AGENT.md").is_file() and (candidate / ".env.example").is_file():
            return candidate
    return Path.cwd()


def _load_dotenv_once() -> None:
    root = repo_root()
    env_path = root / ".env"
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


@dataclass(frozen=True)
class Credentials:
    """Tokens live here. ``repr`` omits secret fields."""

    client_id: str
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False, default="")
    client_secret: str = field(repr=False, default="")

    @property
    def has_access(self) -> bool:
        return bool(self.client_id and self.access_token)

    def __str__(self) -> str:
        return (
            f"Credentials(client_id_set={bool(self.client_id)}, "
            f"access_token_set={bool(self.access_token)})"
        )


@dataclass
class Settings:
    credentials: Credentials
    dry_run: bool
    api_base: str = API_BASE
    auth_base: str = AUTH_BASE
    feed_ws_base: str = FEED_WS_BASE
    repo_root: Path = field(default_factory=repo_root)

    def require_live(self) -> Credentials:
        if self.dry_run:
            raise CredentialsError(
                "Live call requested while dry-run is on. "
                "Pass dry_run=False and set DHAN_CLIENT_ID + DHAN_ACCESS_TOKEN."
            )
        if not self.credentials.has_access:
            raise CredentialsError(
                "DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN are required for live calls."
            )
        return self.credentials


def load_settings(*, dry_run: Optional[bool] = None) -> Settings:
    """Read repo-root ``.env`` then process env.

    If ``dry_run`` is None, dry-run is True whenever access credentials are missing.
    """
    _load_dotenv_once()
    creds = Credentials(
        client_id=_env(ENV_CLIENT_ID),
        access_token=_env(ENV_ACCESS_TOKEN),
        refresh_token=_env(ENV_REFRESH_TOKEN),
        client_secret=_env(ENV_CLIENT_SECRET),
    )
    if dry_run is None:
        dry_run = not creds.has_access
    elif dry_run is False and not creds.has_access:
        raise CredentialsError(
            "Live mode needs DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in env / .env."
        )

    # VERIFY FROM DOCS — see refresh.py. These names are reserved in .env.example.
    if creds.refresh_token:
        log.info(
            "DHAN_REFRESH_TOKEN is set; official v2 RenewToken curl does not "
            "show a refresh_token field. Unused in this skeleton. VERIFY FROM DOCS."
        )
    if creds.client_secret:
        log.info(
            "DHAN_CLIENT_SECRET is set; official individual OAuth uses "
            "app_id / app_secret headers. Unused in this skeleton. VERIFY FROM DOCS."
        )

    log.info(
        "dhan-client settings: dry_run=%s client_id_set=%s access_token_set=%s",
        dry_run,
        bool(creds.client_id),
        bool(creds.access_token),
    )
    return Settings(credentials=creds, dry_run=dry_run, repo_root=repo_root())
