"""FTS5 query against agent_rag.sqlite."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agent_rag.paths import agent_rag_db, repo_root

_SAFE_TOKEN = re.compile(r"[A-Za-z0-9_]+")


@dataclass
class Hit:
    doc_id: str
    kind: str
    title: str
    source_path: str
    snippet: str
    rank: float


def _fts_query(raw: str) -> str:
    """Turn free text into a safe FTS5 MATCH expression (AND of tokens)."""
    tokens = _SAFE_TOKEN.findall(raw)
    if not tokens:
        return '""'
    # Quote each token; AND so multi-word queries are precise
    return " AND ".join(f'"{t}"' for t in tokens[:12])


def query(
    text: str,
    *,
    limit: int = 8,
    kind: Optional[str] = None,
    root: Path | None = None,
) -> list[Hit]:
    root = root or repo_root()
    db = agent_rag_db(root)
    if not db.is_file():
        raise FileNotFoundError(
            f"missing {db} — run: python -m agent_rag rebuild"
        )
    match = _fts_query(text)
    sql = """
        SELECT
          d.doc_id,
          d.kind,
          d.title,
          d.source_path,
          snippet(docs_fts, 3, '[', ']', '…', 24) AS snip,
          bm25(docs_fts) AS score
        FROM docs_fts
        JOIN docs d ON d.id = docs_fts.rowid
        WHERE docs_fts MATCH ?
    """
    params: list[object] = [match]
    if kind:
        sql += " AND d.kind = ?"
        params.append(kind)
    sql += " ORDER BY score LIMIT ?"
    params.append(limit)

    conn = sqlite3.connect(str(db))
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return [
        Hit(
            doc_id=r[0],
            kind=r[1],
            title=r[2],
            source_path=r[3],
            snippet=r[4] or "",
            rank=float(r[5] or 0.0),
        )
        for r in rows
    ]


def hits_as_dicts(hits: list[Hit]) -> list[dict]:
    return [
        {
            "doc_id": h.doc_id,
            "kind": h.kind,
            "title": h.title,
            "source_path": h.source_path,
            "snippet": h.snippet,
            "rank": h.rank,
        }
        for h in hits
    ]
