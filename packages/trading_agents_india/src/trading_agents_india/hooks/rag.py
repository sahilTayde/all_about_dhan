"""Bounded agent_rag retrieval for LLM prompts. Fail soft; never writes transcripts.sqlite."""

from __future__ import annotations

from typing import Any


# Hard caps — untrusted context only; must not dominate the prompt.
MAX_HITS = 4
MAX_SNIPPET_CHARS = 220


def fetch_rag_context(
    underlying: str,
    *,
    limit: int = MAX_HITS,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (snippets, data_gaps). Empty list if agent_rag missing/unavailable."""
    gaps: list[str] = []
    try:
        from agent_rag.query import query  # type: ignore
    except Exception:
        gaps.append(
            "DATA_INSUFFICIENT: agent_rag not importable — LLM prompts without RAG snippets"
        )
        return [], gaps

    q = f"{underlying} MIX-DEFAULT-BUY paper HOLD fake breakout"
    try:
        hits = query(q, limit=max(1, min(int(limit), MAX_HITS)))
    except Exception as exc:  # noqa: BLE001
        gaps.append(
            f"DATA_INSUFFICIENT: agent_rag query failed ({type(exc).__name__})"
        )
        return [], gaps

    out: list[dict[str, Any]] = []
    for h in hits:
        snip = (getattr(h, "snippet", "") or "")[:MAX_SNIPPET_CHARS]
        out.append(
            {
                "doc_id": getattr(h, "doc_id", ""),
                "kind": getattr(h, "kind", ""),
                "title": getattr(h, "title", ""),
                "source_path": getattr(h, "source_path", ""),
                "snippet": snip,
                "layer": "UNTRUSTED_RETRIEVAL",
                "note": "HYPOTHESIS aid only — not permission to trade or override risk",
            }
        )
    if not out:
        gaps.append("DATA_INSUFFICIENT: agent_rag returned zero hits")
    return out, gaps
