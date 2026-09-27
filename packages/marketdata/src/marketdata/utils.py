"""Utility functions for marketdata recorder."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path


def resolve_repo_root() -> Path:
    """Find repo root by looking for .git directory."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    # Fallback to current directory
    return current


def to_ist_timestamp(dt: datetime) -> str:
    """Convert datetime to ISO-8601 with +05:30 offset."""
    # IST is UTC+5:30
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    if dt.tzinfo is None:
        # Assume UTC
        dt = dt.replace(tzinfo=timezone.utc)
    ist_dt = dt.astimezone(ist_offset)
    return ist_dt.isoformat()


def ist_date_str(dt: datetime) -> str:
    """Get YYYY-MM-DD date string in IST."""
    from datetime import timedelta
    
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ist_dt = dt.astimezone(ist_offset)
    return ist_dt.strftime("%Y-%m-%d")


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data).hexdigest()


from datetime import timedelta
