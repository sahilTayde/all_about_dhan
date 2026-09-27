"""Engine wiring from runtime config."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from runtime.config import ConfigLoadError, load_with_last_good

log = logging.getLogger("runtime.wiring")


class EngineConfig:
    """Engine configuration loaded from YAML.

    V2-04: ``exits_only`` plus the raw mapping. Later tickets add fields.
    Unknown keys are kept (forward compatible); known keys are type-checked.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        if "exits_only" in data and not isinstance(data["exits_only"], bool):
            raise ConfigLoadError(
                f"rejected: exits_only must be a bool, got {type(data['exits_only']).__name__}"
            )
        self.data = data
        self.exits_only = bool(data.get("exits_only", False))

    @classmethod
    def load(cls, path: str | Path, *, cache_dir: str | Path | None = None) -> EngineConfig:
        """Load engine config with last-good fallback (exits-only if nothing valid)."""
        data = load_with_last_good(path, cache_dir=cache_dir, exits_only_on_missing=True)
        return cls(data)

    def __repr__(self) -> str:
        return f"EngineConfig(exits_only={self.exits_only})"
