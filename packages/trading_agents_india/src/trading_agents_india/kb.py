"""Separate SQLite store for agent paper sessions. Does not touch transcripts.sqlite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  as_of_ist TEXT NOT NULL,
  mode TEXT NOT NULL,
  openai_used INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  underlying TEXT NOT NULL,
  lean TEXT NOT NULL,
  stage TEXT NOT NULL,
  session_kind TEXT NOT NULL,
  risk_veto INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS agent_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  summary TEXT NOT NULL,
  layer TEXT NOT NULL,
  data_gaps_json TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);
"""


class AgentKB:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                ("schema_version", "1"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                (
                    "purpose",
                    "trading_agents_india paper sessions — not transcripts.sqlite",
                ),
            )
            conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                (
                    "external_ref",
                    "https://github.com/TauricResearch/TradingAgents Apache-2.0",
                ),
            )
            conn.commit()

    def save_session(self, payload: dict[str, Any]) -> int:
        created = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO sessions(as_of_ist, mode, openai_used, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.get("as_of_ist", ""),
                    payload.get("mode", ""),
                    1 if payload.get("openai_used") else 0,
                    json.dumps(payload, ensure_ascii=False),
                    created,
                ),
            )
            session_id = int(cur.lastrowid)
            for ticket in payload.get("tickets") or []:
                conn.execute(
                    """
                    INSERT INTO tickets(
                      session_id, underlying, lean, stage, session_kind, risk_veto, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        ticket.get("underlying", ""),
                        ticket.get("lean", "HOLD"),
                        ticket.get("stage", "WATCH"),
                        ticket.get("session_kind", "NORMAL"),
                        1 if ticket.get("risk_veto") else 0,
                        json.dumps(ticket, ensure_ascii=False),
                    ),
                )
                for report in ticket.get("reports") or []:
                    conn.execute(
                        """
                        INSERT INTO agent_notes(
                          session_id, role, summary, layer, data_gaps_json
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            report.get("role", ""),
                            report.get("summary", ""),
                            report.get("layer", "HYPOTHESIS"),
                            json.dumps(report.get("data_gaps") or [], ensure_ascii=False),
                        ),
                    )
            conn.commit()
            return session_id

    def latest_session(self) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        return json.loads(row[0])
