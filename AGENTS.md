# AGENTS.md — Root Agent Instructions

**Purpose:** Core rules for all AI agents working on `all_about_dhan`. Read this file first, then read `docs/00_INDEX.md` to find the specific document you need.

---

## Company One-Liner

**all_about_dhan** is a Dhan-broker paper/shadow/limited-live/live trading system for NIFTY, BANKNIFTY, and SENSEX index options (CE/PE buy signals). Designed for Mac (paper trading now) and VPS (live trading later). **No live orders until founder approves.**

---

## Efficient Code Principles (Ponytail Rules)

**Source:** [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (146k stars) — "The best code is the code you never wrote."

You are a **lazy senior developer.** Lazy means efficient, not careless.

### The Ladder (Stop at the First Rung That Holds):

Before writing any code, climb this ladder:

1. **Does this need to be built at all?** (YAGNI — You Aren't Gonna Need It)
2. **Does it already exist in this codebase?** Reuse the helper, util, or pattern that's already here; don't re-write it.
3. **Does the standard library already do this?** Use it (e.g., Python `sqlite3`, `asyncio`, `json`, `csv`, `logging`).
4. **Does a native platform feature cover it?** Use it (e.g., systemd for process management on VPS, not custom daemon).
5. **Does an already-installed dependency solve it?** Use it (e.g., FastAPI for API, Redis for event bus, DuckDB for warehouse).
6. **Can this be one line?** Make it one line (if readable).
7. **Only then:** Write the minimum code that works.

### The Rules:

- **No abstractions that weren't explicitly requested.** Don't build a "framework" for 2 use cases.
- **No new dependency if it can be avoided.** Justify every new package (complexity budget per FOUNDER_REQUIREMENTS § 57).
- **No boilerplate nobody asked for.** No "enterprise patterns" for a 3-service system.
- **Deletion over addition.** If you can delete 100 lines and achieve the same result with 10 lines, do it.
- **Boring over clever.** Simple code is maintainable. Clever code is a liability.
- **Fewest files possible.** Don't create 10 files when 1 will do.
- **Shortest working diff wins** (but only once you understand the problem; a small diff in the wrong place is a second bug).
- **Question complex requests:** "Do you actually need X, or does Y cover it?"
- **Pick the edge-case-correct option** when two stdlib approaches are the same size (lazy means less code, not the flimsier algorithm).
- **Mark deliberate simplifications** with a `ponytail:` comment naming the ceiling and upgrade path (e.g., `# ponytail: global lock for simplicity; ceiling ~1k trades/day; upgrade to per-symbol locks if exceeded`).

### Bug Fix = Root Cause, Not Symptom:

A bug report names a symptom. Grep every caller of the function you touch and **fix the shared function once**—one guard there is a smaller diff than one per caller, and patching only the path the ticket names leaves a sibling caller still broken.

### Not Lazy About:

- **Understanding the problem:** Read it fully and trace the real flow before picking a rung. A small diff you don't understand is just laziness dressed up as efficiency.
- **Input validation at trust boundaries** (API endpoints, file parsing, broker API responses).
- **Error handling that prevents data loss** (e.g., ledger is append-only; reconciliation failures halt trading).
- **Security:** Never commit secrets (`.env`, `secrets/`, Dhan tokens, API keys). Repository is **PUBLIC**.
- **Accessibility** (founder page must be usable on phone).
- **Anything explicitly requested** (if founder asks for a feature, build it; don't YAGNI it away).
- **Checks for non-trivial logic:** Non-trivial code leaves **ONE runnable check behind** (an assert-based demo/self-check or one small test file; no frameworks, no fixtures). Trivial one-liners need no test.

---

## Read-Only Guidelines

### Do NOT Read These at Runtime (Requirement Line 34):

- **No `.md` files during live market hours (09:15-15:30 IST) for trading decisions.** Pre-market compiles `.md` → compact JSON config, boss/desk/analysts read JSON only during market.
- **Exception:** Agent reads `AGENTS.md` and docs before starting work (setup phase, not runtime). Post-market GROK reads docs for PR generation.

### Do Read These (Before Starting Work):

1. **`docs/00_INDEX.md`** — Reading order and topic ownership map. **Read this second** (after `AGENTS.md`).
2. **Owner document for your topic** (from index map). Don't open 10 files; open the single owner.
3. **`docs/FILE_CREATION.md`** — Allowed/forbidden new file names.
4. **Relevant team `SKILL.md`** (if applicable, e.g., `teams/04_quant/docs/SKILL.md` for strategy work).

### Do NOT Read (Waste of Tokens):

- **Glob markdown files** (`**/*.md`). Use the index map to find the one file you need.
- **Recon dumps** (`data/recon/*.json` are raw data; read warehouse queries, not raw files).
- **Old dated `BACKTEST_*` files** not cited by scoreboard.
- **Youtube `PLAN.md`** unless doing collector work.

---

## Test Before Claiming Success (Requirement Line 38)

**Rule:** Non-trivial logic must leave **ONE runnable check behind** (assert-based demo, self-check, or small test file). No untested claims.

**Testing levels:**

1. **Unit tests:** For pure functions (e.g., charges calculator, strike selector, regime classifier). Use pytest or built-in `assert`.
2. **Integration tests:** For service interactions (e.g., boss → desk via event bus). Mock external APIs (Dhan, OpenAI).
3. **Honest backtests:** For strategy changes (e.g., new analyst, weight change, filter). Walk-forward OOS, random placebos, costs, no look-ahead. Use `scripts/lab/lab_hist.py` framework.
4. **Tape replay:** For strategy changes. Re-run last 7 days of exact quotes. If improves ≥80% of random skips (p<0.2), consider adopting.
5. **Manual testing (paper mode):** For infrastructure changes (e.g., broker adapter, risk engine). Run paper system for 1 hour, compare before/after (same trades, same P&L ±₹50).
6. **Shadow mode testing:** For broker adapter. Submit real orders to Dhan, immediately cancel (no fills). Run for 3 days, check latency <500ms p95, error rate <5%.

**If tests fail, fix and re-test.** Do NOT merge failing tests.

---

## PR Template (FOUNDER_REQUIREMENTS § 95)

Every PR must include a **handoff block** (in PR description):

```markdown
## Handoff Block (Section 106)

### Accepted
- [What was accepted from prior analysis/requirements]

### Rejected
- [What was rejected and why]

### Unknown / Data Insufficient
- [What couldn't be determined]

### Gap Addressed
- [Which gap from docs/01_CURRENT_STATE_AND_GAPS.md this PR closes]

### Evidence
- [Backtest result: +X L over Y days, p-value Z]
- [Tape replay result: +X k over Y days, beats A% of random skips]
- [Tests performed: unit tests (N passed), integration tests (M passed), manual test (1 hour paper mode, same trades)]

### Known Risks
- [What could go wrong]

### Next Steps
- [What should happen after merge]
```

**Before merge:**

1. Run `python -m docs_auditor` (if you edited requirements, `AGENTS.md`, `MASTER_REQUIREMENTS.md`, `HANDOFF.md`, `PLAN.md`, `FILE_CREATION.md`, or `config/workspace.yaml`). Do NOT merge if it exits 1.
2. Ensure tests pass (see above).
3. Ensure no secrets committed (check `git diff`, search for `token`, `password`, `secret`, `api_key`). Repository is **PUBLIC**.

---

## Hard Rules (Never Violate)

### Security & Safety

1. **Never commit secrets.** `.env`, `secrets/`, Dhan tokens, OpenAI keys, account data, trade logs, tapes. Repository is **PUBLIC**. Use `.gitignore`, env vars, or `secrets/` (gitignored).
2. **Never call Dhan API or any broker API from agent environment** (FOUNDER_REQUIREMENTS line 7, EXPECTATIONS_DIGEST line 28). Only from user-run system.
3. **Never place live orders** unless founder explicitly enables (mode = LIMITED_LIVE or LIVE, and founder confirms in UI).
4. **Never restart `npm` or `paper_ops_daemon` or any service** unless user asks.

### Data Integrity

5. **Ledger is append-only.** Never delete ledger entries (can add correcting entry, but never DELETE).
6. **Reconciliation failures halt new trading** until resolved (CRITICAL: position book out of sync with broker).
7. **KEEP_ALL policy:** `STRAT-001` through `STRAT-014` stay in `BACKTEST_BOOK` (even if negative; mark `WAITING` or `PARKED`, but don't delete per `expert-coalition.mdc` line 42).

### Decision Quality

8. **No win rates, no coded live strategies in repo** (requirement + rules). Strategies are paper/shadow only. Live requires founder approval.
9. **Do NOT assume anything.** Backtest + replay everything before proposing (GROK requirement line 91).
10. **Do NOT just type "add sentences"** (GROK requirement line 93). Data-driven reports: improvement, pros/cons, win rate, metrics, p-values.
11. **LLM is advisory only.** Deterministic risk engine can veto LLM output (FOUNDER_REQUIREMENTS § 13).
12. **Founder commands always override** boss, desk, risk engine (except risk engine still enforces founder-set limits).

### Communication

13. **Talk to founder in simple English** (no jargon). Every response: **Now** (what is true today), **Why** (reason for WAITING/PARKED/removed), **Next** (one recommended action).
14. **Cite evidence.** File paths, line numbers, backtest results, tape replay results. No "I think" without data.

---

## File Creation Policy (Details in `docs/FILE_CREATION.md`)

**Allowed:**

- `HANDOFF.md` (append to existing team `HANDOFF.md`, don't create new).
- `SKILL.md` (append to existing team `SKILL.md`, don't create new).
- `TASK_*` (only under `teams/00_orchestrator/docs/` if no ticket exists).
- `MIX-*` (new club strategies from research; never `STRAT-015+`).
- `CAS-*` (closing auction session strategies).
- `EQ-*` or `SO-*` (equity or stock option strategies, if scope expands).
- `SOURCE_FACT` handoffs (under `teams/01_research/docs/handoffs/<videoId>.md`).
- One backtest file per topic (e.g., `BACKTEST_STRAT-007.md` or `BACKTEST_MIX-OI-ABSORPTION.md`).

**Forbidden (Do NOT Create):**

- Extra `CONTINUE_*` files (one exists: `teams/00_orchestrator/docs/CONTINUE_NEXT_CHAT.md`).
- `HANDOFF_TOMORROW.md` or dated handoffs (append to `HANDOFF.md`).
- Scratch `NOTES.md`, `THOUGHTS.md`, `IDEAS.md` (use issue, chat, or PR description).
- Dated LLM council dumps (e.g., `LLM_ANALYSIS_2026-09-26.md`; put in PR description or issue).
- Duplicate `MASTER_REQUIREMENTS.md` or `AGENTS.md` (one of each at root; don't create `docs/AGENTS.md`).
- Markdown under `data/recon/` (that's for JSON/CSV data, not docs).
- `teams/07_ui` (UI is `apps/web`; team 07 is engineering lead, not a separate UI folder).
- Root gemini/learning `.txt` files (use docs/).

---

## Company Departments (Brief; Full Doc: `docs/COMPANY_DEPARTMENTS.md`)

Signal company (Stratzy / Algoji / Quantman *class*). Teams **00–09 stay** (do not delete or renumber).

| Dept | Boss | Focus |
|------|------|-------|
| D1 Engineering | 07 | Code (RAG, SQL, ML, nightly, backtest) |
| D2 Faculty | 00 Dean / 04 vice | 01 research, 02 math+stats, 03 market, 04 quant+algo, 05 fusion, 06 score |
| D3 Docs | 09 | Docs auditor + documentation |
| D4 PM / monitor | 00 PM | Founder canvas, vendor/key health, `/pm` spec |
| D5 Front desk | 05 | Customer portal `/` + feasibility kill + counsel |

**Founder talks to D4 PM only** (`/pm` spec). Customer `/` vs research `/desk`. **Zero blocking LLM calls on market-hours fast path**; async live LLM counsel may issue risk-review / partial-book-review / exit-review from compact state.

---

## Docs Auditor (Standing Rule)

**After editing** `AGENTS.md`, `MASTER_REQUIREMENTS.md`, any `HANDOFF.md`, `PLAN.md`, `docs/FILE_CREATION.md`, or `config/workspace.yaml`, you **must** run:

```bash
python -m docs_auditor
```

or `python -m desk_intel audit-docs`.

**Do NOT merge** if auditor exits 1. Fix `MISSING` / `STALE` / `CONTRADICTS` or update the manager sheet.

Nightly POST_MARKET (`python -m desk_intel nightly` / `python -m jobs post-market`) already runs the auditor **last**—that is the daily path, **not** a substitute for running after your edits.

Charter: `teams/09_review/docs/DOCS_AUDITOR.md`. File names: `docs/FILE_CREATION.md`. Never print secrets. No live Dhan. Do not restart npm.

---

## Quick Reference

| Topic | Owner Document |
|-------|----------------|
| **Reading order & topic map** | `docs/00_INDEX.md` |
| **Current state & gaps** | `docs/01_CURRENT_STATE_AND_GAPS.md` |
| **Target architecture** | `docs/02_TARGET_ARCHITECTURE.md` |
| **Data contracts** | `docs/03_DATA_CONTRACTS.md` |
| **Migration plan (PRs)** | `docs/04_MIGRATION_PLAN.md` |
| **Founder guide (plain English)** | `docs/13_FOUNDER_GUIDE.md` |
| **File creation rules** | `docs/FILE_CREATION.md` |
| **Ponytail principles** | This file (AGENTS.md) § Efficient Code Principles |
| **PR template** | This file (AGENTS.md) § PR Template |

---

## Open Questions (For Founder)

(None yet; this section will be populated as PRs progress.)

---

**Last updated:** 2026-09-26 (Rebuild planning package)
