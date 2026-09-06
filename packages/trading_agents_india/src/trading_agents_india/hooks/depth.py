"""Dhan Live Market Feed depth / sub-second tape hook.

Honest stub only. Documented packet kinds exist (ticker / quote / full);
repo decode for quote/full/depth is still placeholder. Do **not** treat
any return as alpha until 02/03 decode VALIDATION + history replay.

Status this phase: **PARKED** / **DATA_INSUFFICIENT**.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

DepthStatus = Literal["PARKED", "DATA_INSUFFICIENT"]


@dataclass(frozen=True)
class DepthSnapshot:
    """Always DI until WS decode + replay prove otherwise."""

    underlying: str
    status: DepthStatus
    layer: str
    summary: str
    data_gaps: list[str] = field(default_factory=list)
    packets_seen: int = 0
    claims_alpha: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_GAPS = (
    "DATA_INSUFFICIENT: Dhan Live Market Feed documents ticker/quote/full; "
    "dhan_client.decode has ticker OK — quote/full/depth offsets still placeholder",
    "PARKED: no sub-second depth alpha until decode VALIDATION + history proven",
    "Do not block market-hours paper on depth — use charts + 3m chain + quote REST",
)


def fetch_depth_snapshot(underlying: str = "NIFTY") -> DepthSnapshot:
    """Return a DI-only depth snapshot. Never invents book edges."""
    u = (underlying or "NIFTY").upper()
    return DepthSnapshot(
        underlying=u,
        status="DATA_INSUFFICIENT",
        layer="DATA_INSUFFICIENT",
        summary=(
            f"{u}: continuous sub-second depth PARKED — WS docs exist; "
            "no alpha claim until decode+history VALIDATION"
        ),
        data_gaps=list(_GAPS),
        packets_seen=0,
        claims_alpha=False,
    )
