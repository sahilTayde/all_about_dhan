"""Make V2-08 oms test helpers importable as `helpers`."""

from __future__ import annotations

import sys
from pathlib import Path

_HELPERS = Path(__file__).resolve().parents[2] / "packages" / "oms" / "tests"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))
