# RESEARCH_BOSS_LOOP — 00 transition after 01 finishes

**Team:** 00_orchestrator (transition) · 01 chairs invent + coverage · 06 owns the engine · 09 reviews  
**Status:** `HYPOTHESIS` / routing · **UNVALIDATED** · **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**01 invent cycle:** [`teams/01_research/docs/RESEARCH_BOSS_LOOP.md`](../../01_research/docs/RESEARCH_BOSS_LOOP.md)  
**Coverage:** [`teams/01_research/docs/TOPIC_COVERAGE.md`](../../01_research/docs/TOPIC_COVERAGE.md)  
**Prompt:** [`RESEARCH_BOSS_SKILL.md`](RESEARCH_BOSS_SKILL.md)  
**Gate:** [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)

Education ≠ advice. **No live orders.** This file is **not** a backtest and contains **no** P/L.

00 runs this **after** 01 librarian / research-analyst / Research Boss finish a notes or coverage cycle. This is **not** the 30s / dual-tape path.

---

## When this runs

| Allowed | Forbidden |
|---------|-----------|
| After hours / POST_MARKET / after 01 HANDOFF on notes | Market-hours **30s / dual-tape poll** |
| `python -m agent_rag rebuild` then read `TOPIC_COVERAGE` | Blocking LLM on live gather |
| Emit `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` for **KNOWN** hooks | Write production params / swap `MIX-DEFAULT-BUY` |
| Stamp `DATA_INSUFFICIENT` and **stop inventing** | Live Super Order / `ExecutionClient` |

00 still prints the **customer default** ticket. This loop only fills the **backtest queue**.

---

## Transition (00 — one cycle)

1. **Wait for 01.** Analyst updated [`TOPIC_COVERAGE.md`](../../01_research/docs/TOPIC_COVERAGE.md) (or 01 HANDOFF says coverage unchanged). Missing matrix = treat all new claims as `UNKNOWN`.
2. **RAG rebuild** — `python -m agent_rag rebuild` so `research_book_notes` + `phd_book_kb` match disk. After hours only.
3. **Read coverage** — for each topic:
   - `KNOWN` → may emit `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` naming the **existing** desk hook (`MIX-FORM-*`, dual-tape, `ML-001`, `ML-002` OU/MRR).
   - `PARTIAL` → same proposal **only** for the named hook; no new formula.
   - `DI` / `DATA_INSUFFICIENT` → **do not** invent MIX, IV, Δ, or half-life-as-vega. Leave `UNKNOWN` on the ticket.
4. **Emit** `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED`, `keep_current_strategy: true`, `production_params_written: false`, `tuned: false`, `backtest_results: null`, `one_day_pnl_is_not_evidence: true`.
5. **Do not** write production params. **Do not** block the 30s / dual-tape path. Hand 06 the OOS+`NORMAL` queue. Stop.

---

## Hard constants (every 00 emit)

| Field | Value |
|-------|--------|
| `kind` | `RETUNE_PROPOSAL` |
| `status` | `BACKTEST_REQUIRED` |
| `keep_current_strategy` | `true` |
| `production_params_written` | **`false` always** |
| `tuned` | `false` |
| `backtest_results` | `null` (never invent) |
| `one_day_pnl_is_not_evidence` | `true` |
| KEEP_ALL | `STRAT-001`–`014` stay `BACKTEST_BOOK` |
| New ids | `MIX-*` only — no `STRAT-015+` |
| Live Super Order | **refused** |
| 30s / dual-tape | **zero** blocking LLM; this loop is after hours |

---

## Who runs what

| Job | Who | Command / artifact |
|-----|-----|-------------------|
| Notes + coverage stamps | 01 Hat C | [`TOPIC_COVERAGE.md`](../../01_research/docs/TOPIC_COVERAGE.md) |
| MIX propose | 01 Hat B | 01 [`RESEARCH_BOSS_LOOP.md`](../../01_research/docs/RESEARCH_BOSS_LOOP.md) |
| Rebuild FTS | **00** (this file) | `python -m agent_rag rebuild` |
| Queue retune | **00** | `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` |
| Engine metrics | 06 | Named OOS + `NORMAL` only |
| Docs | 09 / 00 | `python -m docs_auditor` after this spec |

---

## HANDOFF block (copy when 00 runs the transition)

```text
From:     00 RESEARCH_BOSS_LOOP (transition)
To:       01 / 02 / 04 / 06 / 09
Status:   RETUNE_PROPOSAL BACKTEST_REQUIRED
production_params_written: false
live_super_order: refused
30s_path_blocked: false
Accepted: rag rebuild; TOPIC_COVERAGE read; KNOWN hooks queued
Rejected: production write; STRAT-015+; invent on DI; 30s LLM
UNKNOWN: <DI rows from TOPIC_COVERAGE>
```
