# Transcript knowledge base (SQLite + FTS5)

**Path:** `data/knowledge/transcripts.sqlite`  
**Rebuild:** `python scripts/build_transcript_kb.py` (from repo root; uses root `.venv`)  
**Vectors / embeddings:** **skipped** — would pull large model weights. Retrieval path = **SQLite FTS5**.

## What is inside

| Table | Contents |
|-------|----------|
| `videos` | Chart Fanatics + IQCapital video ids, guest/title/status, flags (`has_asr`, `has_bind`, …) |
| `transcripts` | Full bodies: `*_TRANSCRIPT.md`, `*.asr.txt`, caption `*.en.txt` |
| `binds` | CF `*_BIND.md` + `teams/01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md` |
| `docs` | Inventory, ASR phase logs, `RETRY_TOMORROW.md`, SL/TP harvest notes, etc. |
| `*_fts` | FTS5 indexes over transcript / bind / doc bodies |

Source MD + ASR files stay on disk (agents can open them). Audio `.m4a` used only for ASR was deleted after both `.asr.txt` and `*_TRANSCRIPT.md` existed.

## Query examples

```bash
sqlite3 data/knowledge/transcripts.sqlite
```

```sql
-- Semantic-ish keyword search over transcripts
SELECT video_id, kind, snippet(transcripts_fts, 3, '[', ']', '…', 16)
FROM transcripts_fts
WHERE transcripts_fts MATCH 'order AND flow'
LIMIT 10;

-- Bind search
SELECT video_id, title
FROM binds_fts
WHERE binds_fts MATCH 'liquidity OR breaker'
LIMIT 10;

-- Inventory-style status
SELECT video_id, guest, transcript_status, has_bind, has_asr
FROM videos
WHERE source = 'chart_fanatics'
ORDER BY transcript_status, video_id;

-- Pull one full ASR body
SELECT body FROM transcripts WHERE video_id = 'tvERE-Beu2U' AND kind = 'asr' LIMIT 1;
```

Python:

```python
import sqlite3
c = sqlite3.connect("data/knowledge/transcripts.sqlite")
rows = c.execute(
    "SELECT video_id, path FROM transcripts_fts WHERE transcripts_fts MATCH ? LIMIT 5",
    ("mean NEAR/5 reversion",),
).fetchall()
```

## Agent usage (token hygiene)

Prefer FTS / `videos` lookups over re-reading every raw dump. Open the cited `path` only for the hit you need. Do not re-download audio for ids that already have ASR + MD.

## Rebuild note

After new CF ASR / binds land, re-run `scripts/build_transcript_kb.py`. Report: `data/knowledge/RECLAIM_REPORT.json`.
