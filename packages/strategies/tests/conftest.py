"""
Pytest configuration for strategies tests.

Sets up paths and fixtures.
"""

import sys
from pathlib import Path

# Add src to path so imports work
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Also add contracts to path
contracts_src = Path(__file__).parent.parent.parent / "contracts" / "src"
if contracts_src.exists() and str(contracts_src) not in sys.path:
    sys.path.insert(0, str(contracts_src))
