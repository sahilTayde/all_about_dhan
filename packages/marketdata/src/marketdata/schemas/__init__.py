"""JSON Schemas for the recorder's payloads, vendored from V2-01 contracts (PR #32, 2196590)."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

NAMES = ("depth_quote", "quote_snapshot", "oi_cadence")


def load_schema(name: str) -> dict[str, Any]:
    if name not in NAMES:
        raise KeyError(name)
    schema: dict[str, Any] = json.loads(files(__name__).joinpath(f"{name}.json").read_text(encoding="utf-8"))
    return schema
