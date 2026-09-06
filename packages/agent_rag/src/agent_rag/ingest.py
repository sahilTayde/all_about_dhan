"""Build data/knowledge/agent_rag.sqlite (FTS5). Never writes transcripts.sqlite."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from agent_rag.paths import agent_rag_db, repo_root, transcripts_db

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS docs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  source_path TEXT NOT NULL,
  body TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '',
  ingested_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
  doc_id,
  kind,
  title,
  body,
  tags,
  content='docs',
  content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
  INSERT INTO docs_fts(rowid, doc_id, kind, title, body, tags)
  VALUES (new.id, new.doc_id, new.kind, new.title, new.body, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, doc_id, kind, title, body, tags)
  VALUES ('delete', old.id, old.doc_id, old.kind, old.title, old.body, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, doc_id, kind, title, body, tags)
  VALUES ('delete', old.id, old.doc_id, old.kind, old.title, old.body, old.tags);
  INSERT INTO docs_fts(rowid, doc_id, kind, title, body, tags)
  VALUES (new.id, new.doc_id, new.kind, new.title, new.body, new.tags);
END;
"""

MIX_HEADING = re.compile(r"^###\s+(MIX-[A-Z0-9*_-]+)\b.*$", re.M)
MIX_ID_LINE = re.compile(r"^mix_id:\s*(MIX-[A-Z0-9_-]+)\s*$", re.M)
STRAT_HEADING = re.compile(r"^#\s+(STRAT-\d+)\b", re.M)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path, limit: int | None = None) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if limit is not None and len(text) > limit:
        return text[:limit] + "\n\n…[truncated for agent_rag]"
    return text


def _upsert(
    conn: sqlite3.Connection,
    *,
    doc_id: str,
    kind: str,
    title: str,
    source_path: str,
    body: str,
    tags: str = "",
) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO docs(doc_id, kind, title, source_path, body, tags, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(doc_id) DO UPDATE SET
          kind=excluded.kind,
          title=excluded.title,
          source_path=excluded.source_path,
          body=excluded.body,
          tags=excluded.tags,
          ingested_at=excluded.ingested_at
        """,
        (doc_id, kind, title, source_path, body, tags, now),
    )


def _split_mix_catalog(text: str) -> dict[str, str]:
    """Return mix_id -> section snippet from ### headings and mix_id: yaml rows."""
    out: dict[str, str] = {}
    matches = list(MIX_HEADING.finditer(text))
    for i, m in enumerate(matches):
        mix_id = m.group(1).rstrip("*")
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else min(
            len(text), start + 4500
        )
        # Prefer next ## / ### boundary for long CF sections
        nxt = re.search(r"^##\s+", text[m.end() :], re.M)
        if nxt:
            end = min(end, m.end() + nxt.start())
        chunk = text[start:end].strip()
        if len(chunk) > 4000:
            chunk = chunk[:4000] + "\n\n…[truncated]"
        out[mix_id] = chunk
    # YAML-style mix_id rows (CF / SLTP / WEB / TA) — window around each
    for m in MIX_ID_LINE.finditer(text):
        mix_id = m.group(1)
        if mix_id in out:
            continue
        start = max(0, m.start() - 200)
        end = min(len(text), m.end() + 900)
        chunk = text[start:end].strip()
        out[mix_id] = chunk
    return out


def ingest_mix_catalog(conn: sqlite3.Connection, root: Path) -> int:
    path = root / "teams" / "04_quant" / "docs" / "MIX_CATALOG.md"
    if not path.is_file():
        return 0
    text = read_text(path)
    n = 0
    for mix_id, body in _split_mix_catalog(text).items():
        _upsert(
            conn,
            doc_id=f"mix:{mix_id}",
            kind="mix_snippet",
            title=mix_id,
            source_path=str(path.relative_to(root)),
            body=body,
            tags="MIX KEEP_ALL",
        )
        n += 1
    banner = "\n".join(text.splitlines()[:80])
    _upsert(
        conn,
        doc_id="mix:CATALOG_BANNER",
        kind="mix_banner",
        title="MIX_CATALOG banner",
        source_path=str(path.relative_to(root)),
        body=banner,
        tags="MIX KEEP_ALL policy",
    )
    # Candidate MIX-*.md files (CF / TA / club)
    cand = root / "teams" / "04_quant" / "docs" / "candidates"
    if cand.is_dir():
        for cpath in sorted(cand.glob("MIX-*.md")):
            mix_id = cpath.stem
            _upsert(
                conn,
                doc_id=f"mix_cand:{mix_id}",
                kind="mix_candidate",
                title=mix_id,
                source_path=str(cpath.relative_to(root)),
                body=read_text(cpath, limit=3500),
                tags="MIX CANDIDATE KEEP_ALL UNVALIDATED",
            )
            n += 1
    return n + 1


def ingest_strat_candidates(conn: sqlite3.Connection, root: Path) -> int:
    cand = root / "teams" / "04_quant" / "docs" / "candidates"
    if not cand.is_dir():
        return 0
    n = 0
    for path in sorted(cand.glob("STRAT-*.md")):
        text = read_text(path, limit=3500)
        m = STRAT_HEADING.search(text)
        strat_id = m.group(1) if m else path.stem
        _upsert(
            conn,
            doc_id=f"strat:{strat_id}",
            kind="strat_summary",
            title=strat_id,
            source_path=str(path.relative_to(root)),
            body=text,
            tags="STRAT BACKTEST_BOOK UNVALIDATED KEEP_ALL",
        )
        n += 1
    return n


def ingest_cf_binds(conn: sqlite3.Connection, root: Path) -> int:
    cf = root / "teams" / "01_research" / "docs" / "chart_fanatics"
    n = 0
    if cf.is_dir():
        for path in sorted(cf.glob("*_BIND.md")):
            text = read_text(path, limit=6000)
            vid = path.name.replace("_BIND.md", "")
            title_line = next(
                (ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")),
                path.stem,
            )
            _upsert(
                conn,
                doc_id=f"cf_bind:{vid}",
                kind="cf_bind",
                title=title_line[:200],
                source_path=str(path.relative_to(root)),
                body=text,
                tags=f"CF BIND {vid}",
            )
            n += 1
    strat_bind = (
        root / "teams" / "01_research" / "docs" / "handoffs" / "TRANSCRIPT_STRATEGY_BIND.md"
    )
    if strat_bind.is_file():
        _upsert(
            conn,
            doc_id="bind:TRANSCRIPT_STRATEGY_BIND",
            kind="strat_bind",
            title="TRANSCRIPT_STRATEGY_BIND",
            source_path=str(strat_bind.relative_to(root)),
            body=read_text(strat_bind, limit=8000),
            tags="STRAT BIND ENGLISH SOURCE_FACT",
        )
        n += 1
    return n


def ingest_adopt_notes(conn: sqlite3.Connection, root: Path) -> int:
    paths = [
        root / "teams" / "00_orchestrator" / "docs" / "ADOPT_TRADINGAGENTS.md",
        root
        / "teams"
        / "00_orchestrator"
        / "docs"
        / "OPENAI_DESIGN_COUNCIL_2026-09-06.md",
        root
        / "teams"
        / "09_review"
        / "docs"
        / "TRADINGAGENTS_ADOPTION_REVIEW_2026-09-06.md",
        root
        / "teams"
        / "09_review"
        / "docs"
        / "TRADINGAGENTS_DEEPEN_NOTES_2026-09-06.md",
        root / "teams" / "06_backtesting" / "docs" / "EVENT_MEMORY.md",
        root / "teams" / "06_backtesting" / "docs" / "RETUNE_GATE.md",
    ]
    n = 0
    for path in paths:
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        _upsert(
            conn,
            doc_id=f"adopt:{path.stem}",
            kind="adopt_note",
            title=path.stem,
            source_path=rel,
            body=read_text(path, limit=7000),
            tags="ADOPT PAPER AGENTS UNVALIDATED",
        )
        n += 1
    return n


def ingest_paper_sessions(conn: sqlite3.Connection, root: Path) -> int:
    """Pull summaries from trading_agents_india.sqlite (read-only)."""
    kb = root / "data" / "knowledge" / "trading_agents_india.sqlite"
    if not kb.is_file():
        return 0
    n = 0
    try:
        src = sqlite3.connect(f"file:{kb}?mode=ro", uri=True)
    except sqlite3.Error:
        return 0
    try:
        rows = src.execute(
            "SELECT id, as_of_ist, mode, payload_json FROM sessions ORDER BY id"
        ).fetchall()
        for sid, as_of, mode, payload_json in rows:
            try:
                payload = json.loads(payload_json)
            except json.JSONDecodeError:
                payload = {"raw": payload_json[:2000]}
            tickets = payload.get("tickets") or []
            lines = [
                f"paper session id={sid} mode={mode} as_of_ist={as_of}",
                f"openai_used={payload.get('openai_used')}",
                "KEEP_ALL — not a promote. No live orders.",
            ]
            for t in tickets:
                lines.append(
                    "ticket "
                    f"{t.get('underlying')} lean={t.get('lean')} "
                    f"stage={t.get('stage')} session_kind={t.get('session_kind')} "
                    f"risk_veto={t.get('risk_veto')}"
                )
                for r in t.get("reports") or []:
                    lines.append(
                        f"  [{r.get('role')}] {r.get('summary', '')[:400]}"
                    )
            body = "\n".join(lines)
            _upsert(
                conn,
                doc_id=f"paper_session:{sid}",
                kind="paper_session",
                title=f"paper session {sid} ({mode})",
                source_path="data/knowledge/trading_agents_india.sqlite",
                body=body,
                tags=f"PAPER SESSION {mode}",
            )
            n += 1
        try:
            notes = src.execute(
                "SELECT id, session_id, role, summary, layer FROM agent_notes ORDER BY id"
            ).fetchall()
        except sqlite3.Error:
            notes = []
        for nid, sess, role, summary, layer in notes:
            _upsert(
                conn,
                doc_id=f"paper_note:{nid}",
                kind="paper_note",
                title=f"{role} @ session {sess}",
                source_path="data/knowledge/trading_agents_india.sqlite",
                body=f"layer={layer}\n{summary}",
                tags=f"PAPER NOTE {role}",
            )
            n += 1
    finally:
        src.close()
    return n


def ingest_backtest_md_snips(conn: sqlite3.Connection, root: Path) -> int:
    bt = root / "teams" / "06_backtesting" / "docs"
    if not bt.is_dir():
        return 0
    n = 0
    for path in sorted(bt.glob("BACKTEST_*2026-09-06.md")):
        text = read_text(path, limit=2500)
        _upsert(
            conn,
            doc_id=f"backtest_md:{path.stem}",
            kind="backtest_snip",
            title=path.stem,
            source_path=str(path.relative_to(root)),
            body=text,
            tags="BACKTEST UNVALIDATED NO_PROMOTE",
        )
        n += 1
    return n


def rebuild(root: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    tdb = transcripts_db(root)
    assert tdb.name == "transcripts.sqlite"

    db_path = agent_rag_db(root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.is_file():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA)
        counts = {
            "mix": ingest_mix_catalog(conn, root),
            "strat": ingest_strat_candidates(conn, root),
            "cf_binds": ingest_cf_binds(conn, root),
            "adopt": ingest_adopt_notes(conn, root),
            "paper": ingest_paper_sessions(conn, root),
            "backtest_md": ingest_backtest_md_snips(conn, root),
        }
        total = sum(counts.values())
        meta = {
            "schema_version": "1",
            "purpose": "agent speed KB — MIX/STRAT/CF/ADOPT/paper; not transcripts.sqlite",
            "embeddings": "skipped (FTS5 only)",
            "built_at": utc_now(),
            "doc_count": str(total),
            "counts_json": json.dumps(counts),
            "transcripts_sqlite_untouched": "true",
        }
        for k, v in meta.items():
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                (k, v),
            )
        conn.commit()
        report = {
            "db": str(db_path.relative_to(root)),
            "doc_count": total,
            "counts": counts,
            "built_at": meta["built_at"],
            "embeddings": "skipped",
            "transcripts_sqlite_untouched": True,
        }
        report_path = root / "data" / "knowledge" / "AGENT_RAG_BUILD.json"
        report_path.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        report["report"] = str(report_path.relative_to(root))
        return report
    finally:
        conn.close()


def iter_kinds(conn: sqlite3.Connection) -> Iterable[tuple[str, int]]:
    return conn.execute(
        "SELECT kind, COUNT(*) FROM docs GROUP BY kind ORDER BY kind"
    )
