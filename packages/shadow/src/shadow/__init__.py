"""V2 shadow launcher. Paper only. Never places a live order."""

from shadow.safety import ShadowClosed, ShadowSafetyError, assert_paper_only

__version__ = "0.1.0+aad"

__all__ = [
    "ShadowClosed",
    "ShadowSafetyError",
    "__version__",
    "assert_paper_only",
]
