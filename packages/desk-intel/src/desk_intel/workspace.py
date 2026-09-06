"""Load workspace.yaml without printing secret values."""

from __future__ import annotations

import sys
from pathlib import Path

from dhan_client.config import repo_root as dhan_repo_root


def ensure_repo_on_path() -> Path:
    root = dhan_repo_root()
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    return root


ensure_repo_on_path()

from config.load import DeskIntelSettings, Market, WorkspaceConfig, load_workspace  # noqa: E402


def load_desk_workspace() -> WorkspaceConfig:
    return load_workspace()


def enabled_markets(cfg: WorkspaceConfig) -> list[Market]:
    return [m for m in cfg.markets if m.enabled]


def desk_settings(cfg: WorkspaceConfig) -> DeskIntelSettings:
    return cfg.desk_intel


def parse_interval_seconds(raw: str, default: int = 180) -> int:
    text = (raw or "").strip().lower()
    if not text:
        return default
    if text.endswith("min"):
        return int(float(text[:-3].strip() or 0)) * 60
    if text.endswith("m"):
        return int(float(text[:-1].strip() or 0)) * 60
    if text.endswith("s"):
        return int(float(text[:-1].strip() or 0))
    if text.endswith("h"):
        return int(float(text[:-1].strip() or 0)) * 3600
    return int(float(text))
