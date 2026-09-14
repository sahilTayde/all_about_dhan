# Counsel — train 02/04 like pro quant (no pirate books)

**Date:** 2026-09-14  
**Job:** one joint `complete_panel` review (`trading_agents_india.counsel`) — same package as `counsel-job` / `tv-ep-counsel`.  
**Models:** Gemini `gemini-3.5-flash-lite` + OpenAI `gpt-5.4-nano`  
**Together:** `ALIGNED` on `ACCEPT_WITH_CAVEATS`  
**Layer:** `VALIDATION` (counsel) + desk policy  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Policy:** PAPER. **No live orders.** No win-rate claims. **No book PDF download or ingest.**

Founder asked agents to invent NIFTY/SENSEX option formulas like a pro quant, constantly self-review, and said downloading copyrighted books is fine. **Desk rejects pirate ingest.** Copyright still stands. Training uses existing FTS exam notes + tape + MIX-FORM + ML-001.

Related: [`COUNSEL_LLM.md`](COUNSEL_LLM.md) · standing prompt [`PRO_QUANT_AGENT_PROMPT.md`](../../02_phd_math/docs/PRO_QUANT_AGENT_PROMPT.md) · KB [`book_kb/INDEX.md`](../../02_phd_math/docs/book_kb/INDEX.md) · [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) · nightly loop [`QUANT_SELF_REVIEW_LOOP.md`](../../06_backtesting/docs/QUANT_SELF_REVIEW_LOOP.md)

---

## What we asked (one shot)

(a) Train desk agents without pirate books.  
(b) A great standing prompt for 02/04.  
(c) Autonomous learning that does **not** violate `RETUNE_GATE`, live-order ban, or **zero blocking LLM** on the 30s path.

---

## Panel

### Gemini (`ok`)

```text
ACCEPT_WITH_CAVEATS

A:
To train 02/04 desk agents like pro quants and research analysts without pirate or copyrighted book PDFs, the desk must rely entirely on approved internal artifacts and metadata: `teams/02_phd_math/docs/book_kb/` (FTS kind=phd_book_kb via `python -m agent_rag`), original exam notes, `@DhanHQ SOURCE_FACT`, the Dhan HQ API book, dual-tape paper data, `MIX-FORM-*` from `INDEX_CE_PE_EDA`, the `ML-001` KMeans+IsolationForest overlay, `RETUNE_GATE`, `EVENT_MEMORY`, and `SIGNAL_STAGING`. Agents ingest derived mathematical summaries, empirical desk notes, and structured feature stores rather than full texts.

B:
A GREAT standing prompt for 02 math + 04 quant agents MUST contain:
- Must-load sources: FTS `phd_book_kb`, dual-tape paper data, `MIX-FORM-*`, and `ML-001` overlay.
- Execution logic: CE/PE buy first; issue HOLD on `MIX-FORM-FOLLOW-GAP` or `PREMIUM_DIVERGENCE`.
- Formula policy: Invented formulas must be flagged strictly as `HYPOTHESIS` with `BACKTEST_REQUIRED`; no `STRAT-015+`; and `KEEP_ALL` for `001-014`.
- Constraint boundaries: PAPER only, no win rates as fact, no live orders, and adherence to `RETUNE_GATE` protocols.

C:
Autonomous self-review and retune learning operate offline via the nightly routine (`python -m desk_intel nightly` writing `NIGHTLY_YYYY-MM-DD.md REVIEW` to `02`, which is never auto-applied). The `RETUNE_GATE` nightly emits `BACKTEST_REQUIRED` with `keep_current_strategy: true` and prohibits production parameter writes, promoting only out-of-sample (OOS) plus normal conditions. To preserve execution speed, `TOKEN_ML` enforces zero blocking LLM calls on the 30-second market-hours fast path; asynchronous counsel may only review compact state data off-line.
```

### OpenAI (`ok`, truncated)

`gpt-5.4-nano` hit `max_completion_tokens` (400) after section **A**. Sections **B** and **C** from OpenAI are **`DATA_INSUFFICIENT`** (cut mid-heading). Do not invent the missing lines.

```text
ACCEPT_WITH_CAVEATS

A: How to train 02/04 desk agents “like pro quant + research analysts” (PAPER only; no pirate/PDF ingest)
- Use only allowed training sources already listed: @DhanHQ SOURCE_FACT, Dhan HQ API book, dual-tape paper, MIX-FORM-* from INDEX_CE_PE_EDA, ML-001 (KMeans+IsolationForest) overlay, RETUNE_GATE, EVENT_MEMORY, SIGNAL_STAGING.
- For “pro quant + research analyst” behavior, structure training around:
  1) Evidence-first prompting: every claim must reference an allowed source or be explicitly marked HYPOTHESIS.
  2) Shadow-mode execution discipline: PAPER/shadow, no live orders; decisions + rationale only.
  3) Portfolio of tasks: (i) data QA, (ii) feature explanation, (iii) model/cluster interpretation, (iv) signal gating, (v) reviewable backtest plan (never results unless supplied).
  4) Continuous consistency checks using EVENT_MEMORY and SIGNAL_STAGING.
- Explicit prohibition: do not download or ingest book PDFs; book-like depth = FTS kind=phd_book_kb or approved desk paper.
- If you need bibliographic sources beyond FTS phd_book_kb / allowed papers, DATA_INSUFFICIENT.

B: What a GREAT standing prompt for 02 math + 04 quant agents MUST contain (include all required items)
```

---

## 00 verdict (what we accepted / rejected)

| Item | Call |
|------|------|
| Pirate / web PDF ingest | **Rejected** (both models + copyright HARD) |
| FTS `phd_book_kb` + SOURCE_FACT + dual-tape + MIX-FORM + ML-001 | **Accepted** as the training corpus |
| Standing prompt file | **Accepted** — [`PRO_QUANT_AGENT_PROMPT.md`](../../02_phd_math/docs/PRO_QUANT_AGENT_PROMPT.md) |
| Nightly auto-write of MIX/params | **Rejected** — `keep_current_strategy: true` |
| Blocking LLM on 30s / dual-tape | **Rejected** |
| Async counsel on compact state | **Accepted** (pre/post / material-change jobs only) |
| Invented formulas | **Accepted** only as `HYPOTHESIS` + `BACKTEST_REQUIRED` |
| Win rates / live orders / `STRAT-015+` | **Rejected** |

**UNKNOWN:** walk-forward of MIX-FORM / ML-001 on the next `NORMAL` session; OpenAI B/C text.

---

## Nightly self-review (how it must work)

This is **autonomous learning** that stays legal with the gates.

1. **Market hours (fast path):** `dual-tape` + dealer rules + `desk_ml score` after 1m close. **Zero LLM.** FOLLOW-GAP / `PREMIUM_DIVERGENCE` → HOLD new CE/PE. No orders.
2. **POST_MARKET:** `python -m desk_intel nightly` (or `python -m jobs post-market`). Stamps `session_kind`. Writes recon JSON + `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED` and `keep_current_strategy: true`. Hands `teams/02_phd_math/docs/handoffs/NIGHTLY_YYYY-MM-DD.md` as **REVIEW**, not apply.
3. **02 self-review (offline):** load [`PRO_QUANT_AGENT_PROMPT.md`](../../02_phd_math/docs/PRO_QUANT_AGENT_PROMPT.md). FTS-query `phd_book_kb` (`python -m agent_rag query "…"`). Compare dual-tape / MIX-FORM residuals / ML-001 overlay vs the packet. Cite `doc_id`, not chapters. Root cause + **one** backtestable change. Optional **async** counsel job (`REVIEW_NOTES` / `COUNSEL_NEXT`) on a compact facts pack — never on the 30s loop.
4. **04:** if a new expression is needed, name `MIX-FORM-*` or another `MIX-*` (not `STRAT-015+`). Layer = `HYPOTHESIS`. Catalog stub `customer_default: false`.
5. **06:** OOS + `NORMAL` only. Event days stay in `ANALOG_MEMORY`, not the promote score.
6. **09 / Docs Auditor:** last on nightly. No promote from notes.

Re-run this counsel: same `complete_panel` brief when keys exist. If both keys missing, write `DATA_INSUFFICIENT` and keep the prompt file.

---

## HANDOFF

```text
From:     teams/00_orchestrator + counsel panel
To:       02 / 04 / 06 / 09 / founder
Date:     2026-09-14
Status:   REVIEW notes / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Joint counsel ALIGNED ACCEPT_WITH_CAVEATS. Train on FTS notes +
  tape + MIX-FORM + ML-001. Standing prompt for 02/04. Nightly REVIEW +
  BACKTEST_REQUIRED only.
Rejected: Book PDF download/ingest; auto-retune; blocking LLM on 30s;
  live orders; win rates; STRAT-015+.
UNKNOWN: OpenAI B/C (truncated); next NORMAL OOS.
```
