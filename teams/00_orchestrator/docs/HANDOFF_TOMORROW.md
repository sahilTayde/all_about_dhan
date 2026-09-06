# HANDOFF_TOMORROW — where we left off

**Date:** 2026-09-01 (session end). Catalog `retrieved_at`: 2026-08-31T03:15:28Z (not re-fetched).  
**Phase:** 0→2 overlap + Phase 6 **mock** + Phase 1 **skeleton**. SOURCE_FACT still partial. **No strategy code.** **Not** `RESEARCH_READY_FOR_PROGRAMMING`.

**Wake-up (human + frontier model):** read [`docs/MASTER_REQUIREMENTS.md`](../../../docs/MASTER_REQUIREMENTS.md) first. Then [`REVIEW_BRIEF_FOR_FRONTIER_MODEL.md`](REVIEW_BRIEF_FOR_FRONTIER_MODEL.md). **Do not restart npm** (`apps/web`) until the user asks. Do not re-run catalog. Do not call live Dhan.

**As of now (must match every team README/HANDOFF):** YouTube **45** verified + **45** English; customer switch file [`config/workspace.yaml`](../../../config/workspace.yaml); Dhan **dry-run, no orders**; customer dashboard `/` = ticket + **IN-PROGRESS** + **CasPanel** (book P/L **MOCK**); internal **`/desk`**; chain **3m**; nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**; CAS = **Closing Auction Session**; STRATs **UNVALIDATED**.

---

## Where we left off

Overnight docs pass (orchestrator): master requirements sheet + SDLC honesty + this handoff + frontier review brief. CAS analyst and retune-gate work from the same day are **folded into the sheet** (not re-implemented).

**CAS (03, 2026-09-01):** official **Closing Auction Session** (NSE/BSE F&O cash names, **15:15–15:35 IST**, live **3 Aug 2026**). Not pre-open, not PCA. Home [`teams/03_phd_market/cas/`](../../03_phd_market/cas/). Daily `BOUNCE|SIDEWAYS|FALL` **`UNVALIDATED`**. First call SIDEWAYS / `DATA_INSUFFICIENT`. Nightly `cas_calls[]`. Dashboard `CasPanel`. **No win rates.** Ticket [`TASK_CAS_ANALYST.md`](TASK_CAS_ANALYST.md) `IN_PROGRESS`.

**Retune gate (06, 2026-09-01):** [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md). Nightly emits `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`; **never** auto-writes params. Promote only if more profitable OOS on **`NORMAL`** days (expectancy / PF / DD) or a documented glitch fix. Engine **does not exist**. Ticket [`TASK_RETUNE_GATE.md`](TASK_RETUNE_GATE.md) **DONE** (docs + stubs).

**Transcript retry (01, 2026-09-01):** [`TASK_YOUTUBE_TRANSCRIPT_RETRY.md`](TASK_YOUTUBE_TRANSCRIPT_RETRY.md) **DONE**.

- Related retry: **12/12** `TRANSCRIPT_VERIFIED`. Remaining related 429s: **0**.
- YouTube English (`tlang=en`): **44** new + native `T9eo_YxAr9U` = **45** `ENGLISH_VERIFIED`. **No LLM translation.**
- Parked 4 unchanged.

Research coalition (2026-08-30) still stands:

- **14 strategy candidates** — all `UNVALIDATED` / `DRAFT`. **No win rates.**
- Generic DhanHQ client + FastAPI **dry-run**. **No live orders.**
- Paper dashboard: `apps/web` **mock**. **Do not implement strategies.**

---

## Next commands

Transcript retry is **done**. Do **not** re-run `catalog`. Do **not** `npm run dev` until asked.

Optional (only if new verified files appear):

```bash
# from teams/01_research/youtube with venv — not needed unless new verified IDs
python -m src transcripts --english --english-cap 50
```

Desk intel dry-run (no npm, no live token):

```bash
python -m desk_intel status
python -m desk_intel nightly --offline
python -m docs_auditor
```

**Next human / 01 work:** OPTIONS_INDEX + remaining **verified-EN** equity IDs **done** 2026-09-03. Leftover: catalog `STOCK_ONLY` **9** (no English file); `2YBmiyVmNNw` still `DATA_INSUFFICIENT`. Prefer `normalized_en/`. Do not overwrite Hindi `SOURCE_FACT`.

Parked IDs stay in `data/transcripts/parked_tomorrow/`.

**Live Dhan:** **TODO**. Put `DHAN_CLIENT_ID` + `DHAN_ACCESS_TOKEN` in `.env` (not chat) only when the user wants validation. `python -m dhan_client status` first. Execution must still **refuse** orders.

---

## File list (this coalition)

**00 / morning sheet**

- `docs/MASTER_REQUIREMENTS.md`
- `docs/SDLC.md`
- `teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md`
- `teams/00_orchestrator/docs/STATUS.md`
- this file

**Docs Auditor**

- `teams/09_review/docs/DOCS_AUDITOR.md`
- `packages/docs-auditor/`
- `teams/00_orchestrator/docs/TASK_DOCS_AUDITOR.md`
- `teams/00_orchestrator/docs/AUDIT_LATEST.md`

**CAS**

- `teams/03_phd_market/cas/` (README, RESEARCH, METHODOLOGY, HANDOFF, notes, calls)
- `teams/00_orchestrator/docs/TASK_CAS_ANALYST.md`
- `apps/web/src/components/CasPanel.jsx`

**Retune**

- `teams/06_backtesting/docs/RETUNE_GATE.md`
- `teams/00_orchestrator/docs/TASK_RETUNE_GATE.md`
- `packages/desk-intel/src/desk_intel/retune_gate.py`

**01 SOURCE_FACT**

- `teams/01_research/docs/handoffs/HAUSZx-hYdY.md` … `pvmvkiS1cx4.md`
- `teams/01_research/docs/handoffs/TRANSFERABLE_AND_SKIPPED.md`

**04 master + candidates**

- `teams/04_quant/docs/MASTER_STRATEGY_PLAN.md` (v0.1 DRAFT; coalition banner 2026-09-03)
- `teams/04_quant/docs/ALGO_HANDOFF.md` (YAML shape; do not code)
- `teams/04_quant/docs/candidates/STRAT-001.md` … `STRAT-014.md`
- `teams/04_quant/docs/SIGNAL_STAGING.md`

**Transcript coalition (2026-09-03, IN_PROGRESS)**

- `teams/00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md`
- `teams/01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md` (**EXTRACTED** 2026-09-03 English SOURCE_FACT)
- `teams/01_research/docs/handoffs/TA_STRUCTURE_PACKET.md` (on disk; 09 notes only)
- `teams/02_phd_math/docs/TA_FROM_TRANSCRIPTS.md` (on disk)
- `teams/01_research/docs/handoffs/EQUITY_ETF_PACKET.md` (on disk; thin)
- `teams/04_quant/docs/candidates/EQUITY_ETF_BACKLOG.md` (on disk; `UNVALIDATED`)
- `teams/09_review/docs/COALITION_REVIEW.md`
- `teams/03_phd_market/docs/TRANSCRIPT_MARKET_NOTES.md`

---

## Videos extracted (SOURCE_FACT — OPTIONS_INDEX 2026-09-03)

| Band | Count | IDs |
|------|------:|-----|
| Full SOURCE_FACT (index-options / selling / OF) | 10 | Hindi 6 kept + EN `_exmJYgFwFA`, `DzT_681GThA`, `8h9SYvQWKMA`, `HAUSZx-hYdY.en` |
| Thin / transferable TA | 5 | `H_6keeRUCDM`, `PUkzVgVPCf0`, `njqeZc_tYy8` (partial), `6E_K1wVkHyw`, `wDZXqzdGBDc` |
| Promo only | 3 | `6WZxLShiUT8`, `qSgKA0-T7Uw`, `lNSmwmlUI54` |
| **OPTIONS_INDEX packet** | **DONE** | [`OPTIONS_INDEX_PACKET.md`](../../01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md) |
| Skipped as evidence (equity slice) | — | STOCK scanners, BTST, swing-stock, brand/LOW, parked |

Not all 45 `TRANSCRIPT_VERIFIED` files were extracted.

**Still no English transcript (catalog titles only):** 9 `STOCK_ONLY` + stock-options series + ETF strategy titles. **`2YBmiyVmNNw`:** EN on disk but **no recipe** (`DATA_INSUFFICIENT`).

**Strategy candidates:** 14 (`STRAT-001`–`014`). **UNVALIDATED.**

---

## Blockers

1. Live Dhan token — **TODO**. Do not call overnight.
2. Official **lot-size** and **F&O close (15:30 vs 15:40)** circulars **not in repo** — VERIFY.
3. Super Scalper **EMA lengths UNKNOWN**; MACD ×3/×4 and 9 vs 10 MA **SOURCE_UNCERTAIN**.
4. Order-flow **history** likely `DATA_INSUFFICIENT`. `DzT_681GThA` SOURCE_FACT extracted (English); HQ series still missing.
5. No git remote / `.git` still absent.
6. CAS: no live IEP / indicative index.
7. Backtest engine missing — retune cannot promote.

---

## Tomorrow’s order

1. Read **MASTER_REQUIREMENTS** (and REVIEW_BRIEF if you are the frontier model).  
2. Do **not** restart npm until asked.  
3. OPTIONS_INDEX + remaining verified-EN equity SOURCE_FACT is **done**. Leftover 01: catalog `STOCK_ONLY` titles (no EN).  
4. Do **not** start 07_coding **strategies**.  
5. Live Dhan only after tokens are in `.env` and the user asks.  
6. Optional: attach NSE/BSE circular PDFs under `teams/03_phd_market/docs/refs/`.  
7. Keep `DRAFT` / `WAITING_FOR_EDIT` / `UNVALIDATED` labels. No invented win rates.
