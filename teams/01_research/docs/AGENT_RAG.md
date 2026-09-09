# Agent RAG — speed knowledge store (FTS5)

**Path:** `data/knowledge/agent_rag.sqlite`  
**Package:** `packages/agent_rag`  
**Rebuild:** `python -m agent_rag rebuild`  
**Query:** `python -m agent_rag query "fake breakout"`  

**Does not touch** [`transcripts.sqlite`](../../../data/knowledge/transcripts.sqlite) (see [`TRANSCRIPT_KB.md`](TRANSCRIPT_KB.md)).  
**Embeddings / vector models:** **skipped** — keeps the store lightweight (same policy as transcript KB).

---

## Why this exists

Agents need a **fast** lookup over MIX catalog snippets, STRAT candidate summaries, Chart Fanatics binds, ADOPT / TradingAgents notes, and paper session logs — without re-reading the whole tree or hammering the transcript store.

Layer: retrieval aid only. Contents stay tagged `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS` in their source docs. **No win rates invented here.**

---

## What is ingested

| Kind | Source |
|------|--------|
| `mix_snippet` / `mix_banner` | `teams/04_quant/docs/MIX_CATALOG.md` (`### MIX-*` sections) |
| `strat_summary` | `teams/04_quant/docs/candidates/STRAT-*.md` (truncated) |
| `cf_bind` | **removed** 2026-09-09 (Chart Fanatics wipe) |
| `strat_bind` | `TRANSCRIPT_STRATEGY_BIND.md` |
| `adopt_note` | ADOPT / design council / 09 TradingAgents notes + EVENT_MEMORY / RETUNE_GATE |
| `paper_session` / `paper_note` | `data/knowledge/trading_agents_india.sqlite` (read-only) |
| `backtest_snip` | `teams/06_backtesting/docs/BACKTEST_*2026-09-06.md` headers |

Rebuild report: `data/knowledge/AGENT_RAG_BUILD.json`.

---

## CLI

```bash
pip install -e packages/agent_rag

python -m agent_rag rebuild
python -m agent_rag status
python -m agent_rag query "fake breakout"
python -m agent_rag query "MIX-DEFAULT-BUY" --kind mix_snippet
python -m agent_rag paper-backtest --day 2026-09-06
python -m agent_rag eod-recon --day 2026-09-06 --offline
```

Also: `python -m desk_intel eod-recon` (thin alias).

### Query example (Python)

```python
from agent_rag.query import query
for hit in query("fake breakout", limit=5):
    print(hit.doc_id, hit.source_path, hit.snippet)
```

---

## Related jobs (same package)

| Command | Output | Rule |
|---------|--------|------|
| `paper-backtest` | `data/recon/BACKTEST_PAPER_AGENTS_*.json` + 06 MD + 09 OpenAI review notes | Rollup only; **NO_PROMOTE** |
| `eod-recon` | `data/recon/EOD_RECON_*.json` + CONTINUE patch | `RETUNE_PROPOSAL` **`BACKTEST_REQUIRED`**; no auto-retune |

Aligns [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md) + [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md): NEWS_DAY / UNKNOWN out of SCORE_SAMPLE; remember outliers; keep current strategy.

---

## Hard rules

- KEEP_ALL: do not delete STRAT-001–014 from catalog because a search missed them.
- No live orders. No `/alerts/orders`.
- Do not promote on thin samples.
- Never print `.env` secrets.
- Prefer opening the cited `source_path` for the hit you need — FTS snippets are not the full SOURCE_FACT packet.

```text
HANDOFF
From: 01 / agent_rag
To:   00 / 04 / 06 / 09
Accepted: separate FTS5 store; ingest MIX/STRAT/CF/ADOPT/paper; query CLI;
  paper-backtest rollup + eod-recon stub.
Rejected: overwrite transcripts.sqlite; vector model downloads; auto-retune;
  invent win rates; promote.
UNKNOWN: SCORE_SAMPLE until news calendar exists.
```
