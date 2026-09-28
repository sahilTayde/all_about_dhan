"""Mac desk is CPython 3.9: type aliases must not evaluate PEP 604 ``|`` at import."""

from __future__ import annotations

import ast
from pathlib import Path

from dhan_client.feed import OnFrame, OnPacket

_FEED_SRC = Path(__file__).resolve().parents[1] / "src" / "dhan_client" / "feed.py"


def test_feed_aliases_compile_and_evaluate_on_python39_grammar() -> None:
    text = _FEED_SRC.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(_FEED_SRC), feature_version=(3, 9))
    assert tree.body, "feed.py parsed empty under the 3.9 grammar"
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for child in ast.walk(node.value):
            if isinstance(child, ast.BinOp) and isinstance(child.op, ast.BitOr):
                raise AssertionError(
                    "PEP 604 | in a type alias is evaluated at import on CPython 3.9"
                )
    assert OnPacket is not None
    assert OnFrame is not None
