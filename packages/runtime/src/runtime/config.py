"""Last-good YAML loader for engine runtime config (REG-07).

Lives in ``runtime`` (not ``contracts``): contracts owns envelope/schema/clock/ids.
This module owns on-disk engine YAML, last-good cache, and exits-only start-up.
V2-08 / V2-10 import ``runtime.config.load_with_last_good`` for the same policy.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped,unused-ignore]

log = logging.getLogger("runtime.config")


class ConfigLoadError(Exception):
    """Config file is invalid, missing, or fails validation."""


def load_with_last_good(
    config_path: str | Path,
    *,
    cache_dir: str | Path | None = None,
    exits_only_on_missing: bool = False,
) -> dict[str, Any]:
    """Load YAML config with last-good fallback.

    On success: cache as last-good and return config.
    On failure: return last-good if it exists, else raise (or exits-only dict).

    REG-07a/b/c:
    - Bad YAML mid-session: keep last-good (caller must alert CONFIG_INVALID)
    - Valid file replaces last-good (clears the bad state)
    - No valid config at start: exits-only when ``exits_only_on_missing`` is True
    """
    path = Path(config_path)
    cache = path.parent if cache_dir is None else Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    last_good_path = cache / f".last_good_{path.name}"

    try:
        if not path.exists():
            raise ConfigLoadError(f"rejected: config file not found: {path}")

        with path.open(encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)

        if not isinstance(loaded, dict):
            raise ConfigLoadError(f"rejected: config must be a mapping, got {type(loaded).__name__}: {path}")

        shutil.copy2(path, last_good_path)
        log.info("Loaded config %s", path)
        return loaded

    except Exception as exc:
        log.warning("Failed to load config %s: %s", path, exc)

        if last_good_path.exists():
            try:
                with last_good_path.open(encoding="utf-8") as handle:
                    last_good = yaml.safe_load(handle)
                if not isinstance(last_good, dict):
                    raise ConfigLoadError(f"last-good cache is not a mapping: {last_good_path}")
                log.warning("Using last-good config from %s", last_good_path)
                return last_good
            except Exception as cache_exc:
                log.error("Last-good config also invalid: %s", cache_exc)

        if exits_only_on_missing:
            log.critical("No valid config; returning exits-only mode")
            return {"exits_only": True}

        raise ConfigLoadError(f"rejected: config invalid and no last-good at {last_good_path}: {exc}") from exc
