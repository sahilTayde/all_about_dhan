# RESEARCH_BOSS_LOOP — after-hours club → propose → backtest request

**Team:** 01_research (chair) · 00 routes · 02 VALIDATION · 04 catalogs MIX · 06 owns the engine · 09 reviews  
**Status:** `HYPOTHESIS` / spec · **UNVALIDATED** · **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Sibling law:** [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) · [`QUANT_SELF_REVIEW_LOOP.md`](../../06_backtesting/docs/QUANT_SELF_REVIEW_LOOP.md)  
**Standing prompt:** [`RESEARCH_BOSS_SKILL.md`](../../00_orchestrator/docs/RESEARCH_BOSS_SKILL.md)  
**Club:** [`book_reads/CLUB_SEVEN_BOOKS.md`](book_reads/CLUB_SEVEN_BOOKS.md)

Education ≠ advice. **No live orders.** This file is **not** a backtest and contains **no** P/L.

The founder asked for a loop that clubs seven book notes and “becomes research boss.” **Hard reading:** the loop is **not** auto-perfect and **never** sets `production_params_written`. Pretty paper P/L is **not** the stop.

---

## When this runs

| Allowed | Forbidden |
|---------|-----------|
| After hours / POST_MARKET / paper EOD review | Market-hours **30s / poll** path |
| Async counsel on a **compact** facts pack | Blocking LLM on live gather |
| Propose `MIX-*` + `RETUNE_PROPOSAL` | Write `MIX-DEFAULT-BUY` production params |
| Request 06 OOS + `NORMAL` | Live Super Order / `ExecutionClient` |

00 still prints the **customer default** ticket. This loop only fills the **backtest queue**.

---

## Loop (one cycle)

1. **RAG query** — `python -m agent_rag query "<topic>"` against `research_book_notes` and `phd_book_kb`. Open the cited `source_path`. If a `book_reads/` sibling file is missing, stamp `UNKNOWN` and use on-disk `book_kb` only. **Do not** open or paste PDFs.
2. **Propose formula** — named `MIX-*` HYPOTHESIS (origin tag). 5m Supertrend/MACD/RSI = confirm-or-kill. Include HOLD veto (FOLLOW-GAP / NEWS_DAY / stale). Cite club + `doc_id`.
3. **Paper / backtest request** — hand **06** a single OOS + `NORMAL` ask (window, costs, what would falsify). Optional paper watch is **not** a promote.
4. **Emit** `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED`, `keep_current_strategy: true`, `production_params_written: false`, `tuned: false`, `backtest_results: null`, `one_day_pnl_is_not_evidence: true`.
5. **Stop the cycle.** Start another cycle only after 06 returns an engine result **or** `DATA_INSUFFICIENT`. Do not grind knobs overnight to green a ledger.

---

## Stop condition (gate — not “until perfect”)

| Stop | Meaning |
|------|---------|
| **Continue looping** | 06 has not run OOS+`NORMAL`, or result is FAIL / thin / event-contaminated |
| **Park MIX (KEEP_ALL catalog)** | 06 FAIL with root cause; next test named; STRAT-001–014 untouched |
| **Candidate freeze discussion** | 06 OOS+`NORMAL` beats current **and** 09 five-pass **passes** — 00 may then consider default. **Not** this loop’s write. |
| **Never stop for** | Dashboard P/L, one-day paper, “notes feel complete,” LLM saying perfect |

09 notes ≠ pass. Mandate ≠ “you are profitable.”

---

## Hard constants (every proposal)

| Field | Value |
|-------|--------|
| `kind` | `RETUNE_PROPOSAL` |
| `status` | `BACKTEST_REQUIRED` |
| `keep_current_strategy` | `true` |
| `production_params_written` | **`false` always** in this loop |
| `tuned` | `false` |
| `backtest_results` | `null` (never invent) |
| `one_day_pnl_is_not_evidence` | `true` |
| `oos_non_event_required` | `true` |
| KEEP_ALL | `STRAT-001`–`014` stay `BACKTEST_BOOK` |
| New ids | `MIX-*` only — no `STRAT-015+` |
| Live Super Order | **refused** |

---

## Who runs what

| Job | Command / artifact | Loop role |
|-----|-------------------|-----------|
| Rebuild notes | `python -m agent_rag rebuild` | After `book_reads/` or `book_kb` edits |
| Query | `python -m agent_rag query "…" --kind research_book_notes` | Step 1 |
| Query 02 KB | `python -m agent_rag query "…" --kind phd_book_kb` | Step 1 |
| Nightly | `python -m desk_intel nightly` | Packet + same gate fields |
| Paper EOD | `python -m agent_rag eod-recon --offline` | Same; no auto-retune |
| Engine | 06 (named OOS) | Only 06 writes real metrics |
| Docs | `python -m docs_auditor` | After HANDOFF / this spec |

---

## HANDOFF block (copy when a cycle runs)

```text
From:     01 RESEARCH_BOSS_LOOP
To:       00 / 02 / 04 / 06 / 09
Status:   RETUNE_PROPOSAL BACKTEST_REQUIRED
production_params_written: false
live_super_order: refused
Accepted: <club cite + MIX-* proposed>
Rejected: auto-perfect; production write; STRAT-015+; PDF paste; 30s LLM
UNKNOWN: <missing book_reads notes / thin tape>
```
