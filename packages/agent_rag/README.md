# agent_rag

Speed knowledge store for MIX / STRAT / CF binds / ADOPT notes / paper sessions.

- DB: `data/knowledge/agent_rag.sqlite` (FTS5 only — **does not** touch `transcripts.sqlite`)
- Doc: `teams/01_research/docs/AGENT_RAG.md`

```bash
pip install -e packages/agent_rag
python -m agent_rag rebuild
python -m agent_rag query "fake breakout"
python -m agent_rag paper-backtest --day 2026-09-06
python -m agent_rag eod-recon --day 2026-09-06 --offline
```

No live orders. No auto-retune. KEEP_ALL.
