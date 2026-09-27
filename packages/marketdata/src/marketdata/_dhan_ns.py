"""Load ``dhan_client`` submodules without running the package ``__init__``.

``dhan_client.__init__`` imports ``DhanClient`` / ``ExecutionClient``. The live
feed process must not load that order facade. Installing a namespace module
with the real ``__path__`` lets ``dhan_client.feed`` / ``.config`` / ``.rest``
load on their own.
"""

from __future__ import annotations

import importlib.util
import sys
import types

_INSTALLED = False


def ensure_dhan_client_namespace() -> None:
    """Idempotent. No-op if ``dhan_client`` is already in ``sys.modules``."""
    global _INSTALLED
    if _INSTALLED or "dhan_client" in sys.modules:
        _INSTALLED = True
        return
    spec = importlib.util.find_spec("dhan_client")
    if spec is None or spec.submodule_search_locations is None:
        raise ImportError("dhan_client")
    pkg = types.ModuleType("dhan_client")
    pkg.__path__ = list(spec.submodule_search_locations)
    pkg.__file__ = spec.origin
    pkg.__package__ = "dhan_client"
    pkg.__spec__ = spec
    sys.modules["dhan_client"] = pkg
    _INSTALLED = True


ensure_dhan_client_namespace()

from dhan_client.config import Settings, load_settings, repo_root  # noqa: E402
from dhan_client.errors import CredentialsError  # noqa: E402
from dhan_client.feed import MarketFeedCollector  # noqa: E402
from dhan_client.types import FeedMode  # noqa: E402

__all__ = [
    "CredentialsError",
    "FeedMode",
    "MarketFeedCollector",
    "Settings",
    "ensure_dhan_client_namespace",
    "load_settings",
    "repo_root",
]
