"""Boss package: frozen PR-007 orchestrator + V2-07 selector. Paper only.

`Boss` (legacy) is lazy-imported so `import boss.selector` never loads
`desk_ml.paper_scalp`. `from boss import Boss` still works.
"""

from __future__ import annotations

from typing import Any

__all__ = ["Boss"]


def __getattr__(name: str) -> Any:
    if name == "Boss":
        from boss.orchestrator import Boss

        return Boss
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
