"""runtime/__init__ must not import brokers when loading the kernel (Mac .venv-v2)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import runtime

REPO = Path(__file__).resolve().parents[3]


def test_package_init_does_not_import_recovery() -> None:
    text = (REPO / "packages" / "runtime" / "src" / "runtime" / "__init__.py").read_text(encoding="utf-8")
    head = text.split("def __getattr__", 1)[0]
    assert "from runtime.recovery import" not in head
    assert "import runtime.recovery" not in head
    assert "def __getattr__" in text


def test_kernel_import_does_not_need_brokers() -> None:
    script = r"""
import sys

class _BlockBrokers:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "brokers" or fullname.startswith("brokers."):
            raise ModuleNotFoundError("No module named 'brokers'")
        return None

sys.meta_path.insert(0, _BlockBrokers())
from runtime.kernel import Engine
import runtime
assert Engine is not None
assert "runtime.recovery" not in sys.modules
assert "brokers" not in sys.modules
print("ok")
"""
    proc = subprocess.run([sys.executable, "-c", script], check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok" in proc.stdout


def test_engine_export_still_eager() -> None:
    assert runtime.Engine is not None
    assert runtime.JOBS
