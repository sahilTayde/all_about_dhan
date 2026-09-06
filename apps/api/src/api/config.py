"""API settings. Tokens stay in dhan-client; this process never logs them."""

from __future__ import annotations

from dataclasses import dataclass

from dhan_client.config import Settings as DhanSettings, load_settings


@dataclass
class ApiSettings:
    dhan: DhanSettings
    title: str = "all_about_dhan API"
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


def load_api_settings(*, dry_run: bool | None = None) -> ApiSettings:
    return ApiSettings(dhan=load_settings(dry_run=dry_run))
