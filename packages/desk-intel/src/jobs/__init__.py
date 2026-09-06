"""python -m jobs pre-market | post-market

Thin wrapper over desk_intel CLI. Shadow paper only. No live orders.
post-market = nightly recon, then Docs Auditor (exit 1 if docs stale).
"""

from __future__ import annotations

from desk_intel.__main__ import main

__all__ = ["main"]
