"""
Engine wiring from config.

Spec: V2_BUILD_PLAN.md V2-04
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from contracts.config import load_with_last_good

log = logging.getLogger("runtime.wiring")


class EngineConfig:
    """
    Engine configuration loaded from YAML.

    For V2-04: minimal config to wire the engine.
    Later tickets add more fields.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.exits_only = data.get("exits_only", False)

    @classmethod
    def load(cls, path: str | Path) -> EngineConfig:
        """Load engine config with last-good fallback."""
        data = load_with_last_good(path, exits_only_on_missing=True)
        return cls(data)

    def __repr__(self) -> str:
        return f"EngineConfig(exits_only={self.exits_only})"
