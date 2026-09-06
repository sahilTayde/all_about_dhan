"""Config for trading_agents_india. Never print secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def repo_root() -> Path:
    # packages/trading_agents_india/src/trading_agents_india/config.py → repo root
    return Path(__file__).resolve().parents[4]


def _load_dotenv() -> None:
    env_path = repo_root() / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except ImportError:
        # Minimal parse: set missing keys only; never log values.
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw = line.split("=", 1)
            key = key.strip()
            val = raw.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    kb_path: Path
    openai_model: str
    openai_key_present: bool
    default_mix: str = "MIX-DEFAULT-BUY"
    underlyings: tuple[str, ...] = ("NIFTY", "BANKNIFTY", "SENSEX")


def load_settings(
    kb_path: Optional[Path] = None,
    openai_model: Optional[str] = None,
) -> Settings:
    _load_dotenv()
    root = repo_root()
    key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or "").strip()
    model = (
        openai_model
        or os.getenv("OPENAI_MODEL")
        or os.getenv("TRADING_AGENTS_INDIA_MODEL")
        or "gpt-5.4"
    )
    kb = kb_path or (root / "data" / "knowledge" / "trading_agents_india.sqlite")
    return Settings(
        repo_root=root,
        kb_path=kb,
        openai_model=model,
        openai_key_present=bool(key and len(key) > 8),
    )
