"""
Config loader with last-good fallback.

Spec: V2_BUILD_PLAN.md V2-04, REG-07
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("contracts.config")


class ConfigLoadError(Exception):
    """Config file is invalid or missing."""

    pass


def load_with_last_good(
    config_path: str | Path,
    *,
    cache_dir: str | Path | None = None,
    exits_only_on_missing: bool = False,
) -> dict[str, Any]:
    """
    Load YAML config with last-good fallback.

    On success: cache as last-good and return config.
    On failure: return last-good config if it exists, else raise (or return exits-only config).

    Args:
        config_path: Path to config file
        cache_dir: Directory for last-good cache (default: same dir as config_path)
        exits_only_on_missing: If True and no valid config exists, return {"exits_only": True}
                              instead of raising

    Returns:
        Config dict

    Raises:
        ConfigLoadError: if config is invalid and no last-good exists (unless exits_only_on_missing)

    REG-07a/b/c:
    - Bad YAML mid-session: keep last-good, raise alert (caller must alert)
    - Valid file clears alert
    - No valid config at start: exits-only mode (if exits_only_on_missing=True)
    """
    path = Path(config_path)
    cache_dir = path.parent if cache_dir is None else Path(cache_dir)

    cache_dir.mkdir(parents=True, exist_ok=True)
    last_good_path = cache_dir / f".last_good_{path.name}"

    # Try to load current config
    try:
        if not path.exists():
            raise ConfigLoadError(f"Config file not found: {path}")

        with open(path) as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ConfigLoadError(f"Config must be a dict, got {type(config).__name__}")

        # Success: cache as last-good
        shutil.copy2(path, last_good_path)
        log.info("Loaded config %s", path)
        return config

    except Exception as e:
        log.warning("Failed to load config %s: %s", path, e)

        # Try last-good
        if last_good_path.exists():
            try:
                with open(last_good_path) as f:
                    last_good = yaml.safe_load(f)
                log.warning("Using last-good config from %s", last_good_path)
                # Caller must raise CONFIG_INVALID alert
                return last_good
            except Exception as e2:
                log.error("Last-good config also invalid: %s", e2)

        # No last-good available
        if exits_only_on_missing:
            log.critical("No valid config; returning exits-only mode")
            return {"exits_only": True}
        else:
            raise ConfigLoadError(f"Config invalid and no last-good: {e}") from e
