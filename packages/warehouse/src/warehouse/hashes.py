"""Stable hashes for append-only rows. Never hash secrets."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_hash(payload: Any) -> str:
    blob = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
