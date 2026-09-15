# QUANT_SELF_REVIEW_LOOP — nightly / paper review of our own research

**Team:** 06_backtesting (owns gate + loop) · 02_phd_math (REVIEW) · 04_quant (hypothesis authors) · 05 (`desk_intel nightly`)  
**Status:** `HYPOTHESIS` / spec · **UNVALIDATED** · **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Sibling law:** [`RETUNE_GATE.md`](RETUNE_GATE.md)  
**PhD KB:** [`book_kb/topics/parameter_fit_retune_gate.md`](../../02_phd_math/docs/book_kb/topics/parameter_fit_retune_gate.md)

Education ≠ advice. **No live orders.** This file is **not** a backtest and contains **no** P/L.

---

## Why this exists

Agents and paper jobs will re-read **our** MIX-FORM notes, ML-001 fits, TV-EP grids, and dual-tape ledgers. That reread is a **learning packet**. It must not silently become production knobs or a Dhan **Super Order**.

The loop is: **observe → propose → backtest (06) → 09 review → maybe paper**. Never: **observe → write params → live**.

---

## Loop (POST_MARKET + paper EOD)

1. **Ingest facts** — session kind (`NORMAL` / `NEWS_DAY` / `EXPIRY`), paper ledger, dual-tape flags, MIX-FORM / ML-001 artifacts on disk.  
2. **Self-review** — 02/04/06 comment: what broke (quote stale, FOLLOW-GAP, theta, unbound STRAT), what is `DATA_INSUFFICIENT`. Root cause + **one** backtestable change.  
3. **Emit** `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED`.  
4. **Stop.** 06 may later run an engine. Nightly does **not** run that engine as a promote.

Same rules as the paper session tuner (`tv-ep-paper-tune`): extra JSON under `data/recon/` is allowed; **MIX-DEFAULT-BUY production params are not**.

---

## Hard constants (every proposal)

| Field | Value |
|-------|--------|
| `kind` | `RETUNE_PROPOSAL` |
| `status` | `BACKTEST_REQUIRED` (nightly / paper review) |
| `keep_current_strategy` | `true` |
| `production_params_written` | **`false` always** in this loop |
| `tuned` | `false` |
| `backtest_results` | `null` (never invent) |
| `one_day_pnl_is_not_evidence` | `true` |
| `oos_non_event_required` | `true` |
| Live Super Order / `ExecutionClient` | **refused** — this loop must not call place/modify |

06 later statuses (`REJECTED`, `PROMOTE_CANDIDATE`) are **engine-owner** writes after a real OOS+`NORMAL` run — still not a live order, still 04+09 for any spec freeze.

---

## Will / will not

| This loop **will** | This loop **will not** |
|--------------------|------------------------|
| Re-read original `phd_book_kb` + recon JSON | Download books or treat notes as edge |
| Stamp REVIEW handoff language for 02 | Auto-apply Supertrend/MACD/MIX knobs |
| Keep STRAT-001–014 `BACKTEST_BOOK` | Delete teacher ids because a session failed |
| Point 06 at a **named** next test | Place or even **request** a live Super Order |
| Leave IV/greeks null when missing | Invent IV to finish a story |

---

## Who runs what

| Job | Command (existing) | Loop role |
|-----|-------------------|-----------|
| Nightly recon | `python -m desk_intel nightly` / `python -m jobs post-market` | Packet + `RETUNE_PROPOSAL` |
| Paper EOD | `agent_rag` `run_eod_recon` | Same gate fields |
| Paper tuner | `python -m backtest_engine tv-ep-paper-tune` | Local params file only |
| Docs | `python -m docs_auditor` | After HANDOFF / this spec |

---

## HANDOFF block (copy when the loop runs)

```text
From:     06 QUANT_SELF_REVIEW_LOOP
To:       02 REVIEW / 04 / 09
Status:   RETUNE_PROPOSAL BACKTEST_REQUIRED
production_params_written: false
live_super_order: refused
Accepted: <what the packet actually showed>
Rejected: production write; live Super Order; invented IV/greeks
UNKNOWN: <DATA_INSUFFICIENT>
```
