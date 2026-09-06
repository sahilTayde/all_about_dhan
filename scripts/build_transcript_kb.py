#!/usr/bin/env python3
"""Build SQLite + FTS5 knowledge store for Chart Fanatics + key research binds.

No embeddings (avoids large model downloads). Query via FTS5 — see
teams/01_research/docs/TRANSCRIPT_KB.md
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "knowledge" / "transcripts.sqlite"
CF_DOCS = ROOT / "teams" / "01_research" / "docs" / "chart_fanatics"
CF_RAW = ROOT / "data" / "transcripts" / "external_chart_fanatics"
IQ_RAW = ROOT / "data" / "transcripts" / "external_iqcapital"
HANDOFFS = ROOT / "teams" / "01_research" / "docs" / "handoffs"
RESEARCH_DOCS = ROOT / "teams" / "01_research" / "docs"

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_guest(text: str) -> str | None:
    for pat in (
        r"\*\*Guest\*\*[|:]\s*(.+)",
        r"guest:\s*(.+)",
        r"·\s*([^(\n]+?)\s*\(Chart Fanatics\)",
        r"# BIND — `[^`]+` · ([^\n(]+)",
    ):
        m = re.search(pat, text, re.I)
        if m:
            g = m.group(1).strip().strip("*").strip()
            g = re.split(r"\s*[|/]\s*", g)[0].strip()
            if g and len(g) < 120:
                return g
    return None


def extract_title_from_transcript_md(text: str) -> str | None:
    for line in text.splitlines()[:40]:
        if line.startswith("# "):
            return line[2:].strip()[:300]
    return None


def parse_inventory(inv_path: Path) -> dict[str, dict]:
    """Parse CHANNEL_INVENTORY.md video table rows into video_id -> meta."""
    text = read_text(inv_path)
    videos: dict[str, dict] = {}
    # Table rows like: | views | dur | yes/fail | `id` | title | notes |
    row_re = re.compile(
        r"^\|\s*([\d,]+)\s*\|\s*([^|]+)\|\s*(yes|fail|partial)[^|]*\|\s*`([A-Za-z0-9_-]{11})`\s*\|\s*([^|]+)\|",
        re.I | re.M,
    )
    for m in row_re.finditer(text):
        vid = m.group(4)
        videos[vid] = {
            "views": m.group(1).replace(",", ""),
            "duration": m.group(2).strip(),
            "transcript_status": m.group(3).lower(),
            "title": m.group(5).strip()[:400],
            "source": "chart_fanatics",
            "channel": "Chart Fanatics",
            "channel_handle": "@chart-fanatics",
        }
    # Priority block
    if "tvERE-Beu2U" not in videos:
        videos["tvERE-Beu2U"] = {
            "views": "4028375",
            "duration": "3h34m10s",
            "transcript_status": "yes",
            "title": "Trading LIVE with the #1 Scalper in the WORLD (EXTREME Accuracy)",
            "source": "chart_fanatics",
            "channel": "Chart Fanatics",
            "channel_handle": "@chart-fanatics",
            "guest": "Fabio Valentini",
        }
    return videos


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        DROP TABLE IF EXISTS transcripts_fts;
        DROP TABLE IF EXISTS binds_fts;
        DROP TABLE IF EXISTS docs_fts;
        DROP TABLE IF EXISTS transcripts;
        DROP TABLE IF EXISTS binds;
        DROP TABLE IF EXISTS docs;
        DROP TABLE IF EXISTS videos;
        DROP TABLE IF EXISTS meta;

        CREATE TABLE meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE TABLE videos (
          video_id TEXT PRIMARY KEY,
          source TEXT NOT NULL,
          channel TEXT,
          channel_handle TEXT,
          title TEXT,
          guest TEXT,
          duration TEXT,
          views INTEGER,
          transcript_status TEXT,
          has_asr INTEGER NOT NULL DEFAULT 0,
          has_transcript_md INTEGER NOT NULL DEFAULT 0,
          has_bind INTEGER NOT NULL DEFAULT 0,
          has_audio_m4a INTEGER NOT NULL DEFAULT 0,
          url TEXT,
          notes TEXT
        );

        CREATE TABLE transcripts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          video_id TEXT NOT NULL,
          kind TEXT NOT NULL,  -- asr|md|en_txt|raw_txt|json
          path TEXT NOT NULL,
          body TEXT NOT NULL,
          char_len INTEGER NOT NULL,
          FOREIGN KEY(video_id) REFERENCES videos(video_id)
        );

        CREATE TABLE binds (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          video_id TEXT,
          path TEXT NOT NULL,
          title TEXT,
          body TEXT NOT NULL,
          char_len INTEGER NOT NULL,
          origin_tag TEXT
        );

        CREATE TABLE docs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          doc_key TEXT NOT NULL UNIQUE,
          path TEXT NOT NULL,
          title TEXT,
          body TEXT NOT NULL,
          char_len INTEGER NOT NULL,
          category TEXT
        );

        CREATE VIRTUAL TABLE transcripts_fts USING fts5(
          video_id UNINDEXED,
          kind UNINDEXED,
          path UNINDEXED,
          body,
          content='transcripts',
          content_rowid='id'
        );

        CREATE VIRTUAL TABLE binds_fts USING fts5(
          video_id UNINDEXED,
          path UNINDEXED,
          title,
          body,
          content='binds',
          content_rowid='id'
        );

        CREATE VIRTUAL TABLE docs_fts USING fts5(
          doc_key UNINDEXED,
          path UNINDEXED,
          title,
          body,
          content='docs',
          content_rowid='id'
        );
        """
    )


def upsert_video(conn: sqlite3.Connection, video_id: str, **fields) -> None:
    cur = conn.execute("SELECT video_id FROM videos WHERE video_id=?", (video_id,))
    if cur.fetchone():
        sets = []
        vals = []
        for k, v in fields.items():
            if v is None:
                continue
            sets.append(f"{k}=?")
            vals.append(v)
        if sets:
            vals.append(video_id)
            conn.execute(f"UPDATE videos SET {', '.join(sets)} WHERE video_id=?", vals)
    else:
        cols = ["video_id"] + list(fields.keys())
        placeholders = ",".join("?" * len(cols))
        conn.execute(
            f"INSERT INTO videos ({','.join(cols)}) VALUES ({placeholders})",
            [video_id] + list(fields.values()),
        )


def add_transcript(conn: sqlite3.Connection, video_id: str, kind: str, path: Path, body: str) -> None:
    rel = str(path.relative_to(ROOT))
    conn.execute(
        "INSERT INTO transcripts (video_id, kind, path, body, char_len) VALUES (?,?,?,?,?)",
        (video_id, kind, rel, body, len(body)),
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO transcripts_fts (rowid, video_id, kind, path, body) VALUES (?,?,?,?,?)",
        (rid, video_id, kind, rel, body),
    )


def add_bind(conn: sqlite3.Connection, video_id: str | None, path: Path, body: str) -> None:
    rel = str(path.relative_to(ROOT))
    title = None
    for line in body.splitlines()[:5]:
        if line.startswith("#"):
            title = line.lstrip("# ").strip()[:300]
            break
    origin = None
    m = re.search(r"Origin tag[^\n]*`([^`]+)`", body, re.I)
    if m:
        origin = m.group(1)
    elif "EXTERNAL_RESEARCH" in body:
        origin = "EXTERNAL_RESEARCH"
    elif "DHAN-DERIVED" in body:
        origin = "DHAN-DERIVED"
    conn.execute(
        "INSERT INTO binds (video_id, path, title, body, char_len, origin_tag) VALUES (?,?,?,?,?,?)",
        (video_id, rel, title, body, len(body), origin),
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO binds_fts (rowid, video_id, path, title, body) VALUES (?,?,?,?,?)",
        (rid, video_id, rel, title or "", body),
    )


def add_doc(conn: sqlite3.Connection, doc_key: str, path: Path, body: str, category: str) -> None:
    rel = str(path.relative_to(ROOT))
    title = path.name
    for line in body.splitlines()[:10]:
        if line.startswith("#"):
            title = line.lstrip("# ").strip()[:300]
            break
    conn.execute(
        "INSERT INTO docs (doc_key, path, title, body, char_len, category) VALUES (?,?,?,?,?,?)",
        (doc_key, rel, title, body, len(body), category),
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO docs_fts (rowid, doc_key, path, title, body) VALUES (?,?,?,?,?)",
        (rid, doc_key, rel, title, body),
    )


def ingest_chart_fanatics(conn: sqlite3.Connection) -> dict:
    inv_path = CF_DOCS / "CHANNEL_INVENTORY.md"
    inventory = parse_inventory(inv_path) if inv_path.exists() else {}
    stats = {"videos": 0, "transcripts": 0, "binds": 0, "docs": 0}

    # Seed videos from inventory
    for vid, meta in inventory.items():
        views = None
        try:
            views = int(meta.get("views") or 0) or None
        except ValueError:
            views = None
        upsert_video(
            conn,
            vid,
            source=meta.get("source", "chart_fanatics"),
            channel=meta.get("channel"),
            channel_handle=meta.get("channel_handle"),
            title=meta.get("title"),
            guest=meta.get("guest"),
            duration=meta.get("duration"),
            views=views,
            transcript_status=meta.get("transcript_status"),
            url=f"https://www.youtube.com/watch?v={vid}",
        )
        stats["videos"] += 1

    # TRANSCRIPT.md
    for path in sorted(CF_DOCS.glob("*_TRANSCRIPT.md")):
        vid = path.name.replace("_TRANSCRIPT.md", "")
        body = read_text(path)
        if VIDEO_ID_RE.match(vid) or vid.startswith("_"):
            guest = extract_guest(body)
            title = extract_title_from_transcript_md(body)
            status = "yes" if len(body) > 1500 else "stub"
            # fail stubs often short
            if "no full transcript" in body.lower() or (
                len(body) < 1200 and "fail" in body[:600].lower()
            ):
                status = "fail"
            upsert_video(
                conn,
                vid,
                source="chart_fanatics",
                channel="Chart Fanatics",
                channel_handle="@chart-fanatics",
                title=title,
                guest=guest,
                transcript_status=status,
                has_transcript_md=1,
                url=f"https://www.youtube.com/watch?v={vid}",
            )
            add_transcript(conn, vid, "md", path, body)
            stats["transcripts"] += 1

    # ASR + caption raws
    for path in sorted(CF_RAW.glob("*.asr.txt")):
        vid = path.name.replace(".asr.txt", "")
        body = read_text(path)
        upsert_video(
            conn,
            vid,
            source="chart_fanatics",
            channel="Chart Fanatics",
            channel_handle="@chart-fanatics",
            has_asr=1,
            transcript_status="yes",
            url=f"https://www.youtube.com/watch?v={vid}",
        )
        add_transcript(conn, vid, "asr", path, body)
        stats["transcripts"] += 1

    for path in sorted(CF_RAW.glob("*.en.txt")):
        vid = path.name.replace(".en.txt", "")
        body = read_text(path)
        upsert_video(
            conn,
            vid,
            source="chart_fanatics",
            has_asr=0,
            transcript_status="yes",
            url=f"https://www.youtube.com/watch?v={vid}",
        )
        add_transcript(conn, vid, "en_txt", path, body)
        stats["transcripts"] += 1

    # BIND.md
    for path in sorted(CF_DOCS.glob("*_BIND.md")):
        vid = path.name.replace("_BIND.md", "")
        body = read_text(path)
        guest = extract_guest(body)
        upsert_video(
            conn,
            vid,
            source="chart_fanatics",
            guest=guest,
            has_bind=1,
            url=f"https://www.youtube.com/watch?v={vid}",
        )
        add_bind(conn, vid, path, body)
        stats["binds"] += 1

    # Audio presence flags (do not store audio)
    audio_dir = CF_RAW / "audio"
    if audio_dir.is_dir():
        for path in audio_dir.glob("*.m4a"):
            vid = path.stem
            upsert_video(conn, vid, has_audio_m4a=1, source="chart_fanatics")

    # Channel-level docs
    for name in (
        "CHANNEL_INVENTORY.md",
        "RETRY_TOMORROW.md",
        "PHASE3_RETRY_LOG.md",
        "PHASE3B_ASR_LOG.md",
        "PHASE3C_ASR_LOG.md",
        "PHASE3D_ASR_LOG.md",
        "PHASE3E_ASR_LOG.md",
        "PHASE3F_ASR_LOG.md",
        "PHASE3G_ASR_LOG.md",
        "PHASE3H_ASR_LOG.md",
        "PHASE3I_ASR_LOG.md",
    ):
        path = CF_DOCS / name
        if path.exists():
            add_doc(conn, f"cf/{name}", path, read_text(path), "chart_fanatics")
            stats["docs"] += 1

    return stats


def ingest_key_research(conn: sqlite3.Connection) -> dict:
    stats = {"binds": 0, "docs": 0, "transcripts": 0}
    # Strategy bind (DhanHQ)
    bind = HANDOFFS / "TRANSCRIPT_STRATEGY_BIND.md"
    if bind.exists():
        add_bind(conn, None, bind, read_text(bind))
        stats["binds"] += 1

    for name, cat in (
        ("SL_TP_EXTERNAL_HARVEST.md", "research"),
        ("SL_TP_CLASSIC_METHODS.md", "research"),
        ("DHAN_OFFICIAL_INDICATORS.md", "research"),
        ("DHAN_ECOSYSTEM.md", "research"),
        ("TOPIC_STRATEGY_PIPELINE.md", "research"),
    ):
        path = RESEARCH_DOCS / name
        if path.exists():
            add_doc(conn, f"research/{name}", path, read_text(path), cat)
            stats["docs"] += 1

    # IQCapital short transcripts
    if IQ_RAW.is_dir():
        for path in sorted(IQ_RAW.glob("*.en.txt")):
            vid = path.name.replace(".en.txt", "")
            body = read_text(path)
            upsert_video(
                conn,
                vid,
                source="iqcapital",
                channel="IQ Capital",
                channel_handle="@iqcapital_io",
                transcript_status="yes",
                url=f"https://www.youtube.com/watch?v={vid}",
            )
            add_transcript(conn, vid, "en_txt", path, body)
            stats["transcripts"] += 1

    return stats


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    for suffix in ("-wal", "-shm"):
        p = Path(str(DB_PATH) + suffix)
        if p.exists():
            p.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        cf = ingest_chart_fanatics(conn)
        research = ingest_key_research(conn)
        summary = {
            "built_at": utc_now(),
            "db": str(DB_PATH.relative_to(ROOT)),
            "chart_fanatics": cf,
            "research": research,
            "vector_index": "SKIPPED — avoid large embedding model download; use FTS5",
            "counts": {
                "videos": conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0],
                "transcripts": conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0],
                "binds": conn.execute("SELECT COUNT(*) FROM binds").fetchone()[0],
                "docs": conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0],
            },
        }
        conn.execute(
            "INSERT INTO meta(key,value) VALUES('build_summary', ?)",
            (json.dumps(summary, indent=2),),
        )
        conn.execute(
            "INSERT INTO meta(key,value) VALUES('retrieval', ?)",
            ("sqlite FTS5 on transcripts_fts / binds_fts / docs_fts",),
        )
        conn.commit()
        print(json.dumps(summary, indent=2))
        print("DB_BYTES", DB_PATH.stat().st_size)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
