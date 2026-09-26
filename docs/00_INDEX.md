# Documentation Index

**Purpose:** This index tells you exactly what to read and in what order. It also maps every topic to exactly one document that owns it, so you (or an AI agent) never have to open ten files to understand one thing.

---

## For Humans Learning the System (Read in This Order)

### First-Time Readers (Start Here)
1. **[`docs/13_FOUNDER_GUIDE.md`](13_FOUNDER_GUIDE.md)** — Plain-English overview: what the system does, how you control it, what the stages mean, and where things can go wrong. Read this first if you're Sahil or any human new to the codebase.

### Understanding the Current State
2. **[`docs/01_CURRENT_STATE_AND_GAPS.md`](01_CURRENT_STATE_AND_GAPS.md)** — Gap matrix: what the founder asked for (from FOUNDER_REQUIREMENTS), what exists today in the code, what's tested, what's production-ready, and the gap + priority (P0-P4). This is your map of what works and what's missing.

### Understanding the Plan
3. **[`docs/02_TARGET_ARCHITECTURE.md`](02_TARGET_ARCHITECTURE.md)** — Target design: modular core + market adapters + broker adapters, separation of duties (pre-market, analyst, boss, desk, risk, monitor, post-market), event model, state machines, modes (paper/shadow/limited-live/live), tech stack recommendations. Read this to understand where we're going.

4. **[`docs/03_DATA_CONTRACTS.md`](03_DATA_CONTRACTS.md)** — Data capture specification: daily capture set (index ticks, full chain with OI/IV/greeks, futures with volume, heavyweights, global/commodity/FX, tagged news, multi-timeframe levels), join keys, storage layout, nightly warehouse job, Dhan feed mapping. This is what we record and why.

5. **[`docs/04_MIGRATION_PLAN.md`](04_MIGRATION_PLAN.md)** — Migration roadmap: ordered list of small PRs, each with scope, acceptance test, risk, and performance budget. Start here when you're ready to build. PR-001 is the data recorder (can't be backfilled), PR-002 is the P0 safety core.

### Development Rules and Context
6. **[`AGENTS.md`](../AGENTS.md)** (root) — Agent instructions: ponytail principles (lazy senior dev rules from DietrichGebert/ponytail), runtime .md reading restrictions, test-before-claim mandate, PR template. Read this before opening a PR or asking an agent to work.

7. **[`.cursor/rules/`](../.cursor/rules/)** — Always-on rules enforced by Cursor: docs auditor, company departments, file creation policy, continue-prior-chat, expert coalition. These are automatic.

---

## Topic Ownership Map

**Rule:** If you're writing about one of these topics, edit the listed file. If you're reading about it, go there. Don't duplicate content across files.

| **Topic** | **Owner Document** | **What It Covers** |
|-----------|-------------------|-------------------|
| **User Interface & Founder Controls** | `01_CURRENT_STATE_AND_GAPS.md` § Desk UI, Founder Controls, Founder Page | All UI requirements: desk trade view, founder page, health alarms, decision visual, account ledger, filters, human override API. |
| **Broker Integration (Dhan API)** | `03_DATA_CONTRACTS.md` § Broker Adapter, `02_TARGET_ARCHITECTURE.md` § Broker Adapter Layer | Which Dhan call to use (super order, limit, SL, trailing, target shift, cancel, exit, kill switch), websocket vs REST, order state machine, reconciliation. |
| **Data Capture & Warehouse** | `03_DATA_CONTRACTS.md` (entire file) | Daily capture set, join keys, storage schema, nightly job, Dhan feed mapping, retention policy. |
| **Backtesting & Replay** | `01_CURRENT_STATE_AND_GAPS.md` § Backtest/Replay Engine, `02_TARGET_ARCHITECTURE.md` § Backtest Layer | Honest backtesting (candle-by-candle, costs, slippage, no look-ahead), replay with exact quotes, multi-timeframe tests, strategy evaluation. |
| **Pre-Market, Post-Market, Boss, Analyst, Desk Roles** | `02_TARGET_ARCHITECTURE.md` § Separation of Duties, `13_FOUNDER_GUIDE.md` § How the System Works | Non-overlapping duties for each stage, event model, decision flow, logging, LLM usage. |
| **Risk Management & Safety** | `02_TARGET_ARCHITECTURE.md` § Risk Layer, § Modes (paper/shadow/limited-live/live), `04_MIGRATION_PLAN.md` PR-002 | Pre-trade risk engine with veto power, kill switches, position limits, deterministic risk controls that override LLM. |
| **Order & Position State Machines** | `02_TARGET_ARCHITECTURE.md` § Execution Layer, `01_CURRENT_STATE_AND_GAPS.md` § Broker Adapter | Order lifecycle (created → submitted → acknowledged → filled → closed), position reconciliation, idempotency, single source of truth. |
| **Multi-Market Support (Forex, Crypto)** | `02_TARGET_ARCHITECTURE.md` § Market Adapter Layer | Separation of market-specific logic (calendar, lot/tick size, expiry rules, hours, margin) from core engine. |
| **LLM Cost Control & Second Opinion** | `02_TARGET_ARCHITECTURE.md` § Boss Layer (LLM usage), `04_MIGRATION_PLAN.md` PR-007 | Budget, event-driven (not per tick), structured JSON, advisory only (risk can veto), compact context. |
| **Current Bugs & Fixes** | `01_CURRENT_STATE_AND_GAPS.md` § Current State → Known Bugs, § Gap column (what's broken) | Look-ahead data leakage in `_hold_series` / `ols_beta`, degenerate ML models, reversed OI signal, double-counted `greeks_vote_intent`, unreachable `ML-1`. Also see uploaded phase reports. |
| **Proven Rule Stack (Phase 3 Analysis)** | `01_CURRENT_STATE_AND_GAPS.md` § Proven Fixes | Entry cutoff 15:00, 15-min loss cooldown, DTE-aware strikes (ITM100/ITM200), consolidation block, STRAT-007 clock (10:00–14:30). Sep 17–25 tape +210.1k vs −9.2k baseline. |
| **Lab Results & Strategy Evaluation** | `01_CURRENT_STATE_AND_GAPS.md` § Lab Round 1 Summary, uploaded `lab_journal_a989.md`, `comparison_table_5b04.md` | No standalone strategy has proven edge after costs in held-out year. Intermarket bias, trend-day breakouts, gap-and-go, wing divergence all lost. Binding constraint: missing data (futures 1m volume, multi-strike OI history, heavyweights, more tape days). |
| **Migration Sequencing & PR Breakdown** | `04_MIGRATION_PLAN.md` (entire file) | Ordered PRs with acceptance tests, risks, performance budgets. Start with data recorder (PR-001, can't be backfilled), then safety core (PR-002), then observability (PR-003), then UI (PR-004), etc. |
| **Tech Stack & Deployment** | `02_TARGET_ARCHITECTURE.md` § Technology Stack, § Deployment (Mac now, VPS later) | Lightweight choices: Python services, event bus, DuckDB/Parquet or Postgres/Timescale warehouse, minimal dependencies (ponytail principle), VPS-ready but Mac-testable. |
| **Efficient Code Principles (Ponytail)** | `AGENTS.md` (root) § Efficient Code Principles | YAGNI ladder, reuse over rebuild, stdlib/platform first, deletion over addition, shortest working diff, no abstractions unless requested, check + comment for non-trivial logic. |
| **PR Template & Submission Rules** | `AGENTS.md` (root) § PR Template (Sec 95), `.cursor/rules/docs-auditor.mdc` | Handoff block (accepted / rejected / unknown), gap addressed, backtest/tape result, tests/checks performed, known risks, next steps. Run `python -m docs_auditor` before merge. |
| **File Creation Policy** | `.cursor/rules/file-creation.mdc`, `docs/FILE_CREATION.md` | What new files are allowed (`HANDOFF.md`, `SKILL.md`, `TASK_*` under team 00, `MIX-*` clubs, `SOURCE_FACT` handoffs, one backtest file per topic). What's forbidden (extra `CONTINUE_*`, scratch `NOTES.md`, dated LLM dumps, duplicate MASTER/AGENT). |
| **Docs Auditor (Standing Rule)** | `.cursor/rules/docs-auditor.mdc` | After editing requirements, `AGENTS.md`, `MASTER_REQUIREMENTS.md`, `HANDOFF.md`, `PLAN.md`, `FILE_CREATION.md`, or `workspace.yaml`, run `python -m docs_auditor`. Do not merge if it exits 1. Fix `MISSING` / `STALE` / `CONTRADICTS`. |
| **Company Departments & Teams** | `.cursor/rules/company-departments.mdc`, `docs/COMPANY_DEPARTMENTS.md` | Founder org: teams 00–09 (orchestrator, research, math, market, quant, desk-intel, backtest, UI, review). Do not delete or renumber teams 00–09. |

---

## Quick Lookup by File

| **File** | **What It Contains** |
|----------|----------------------|
| **`docs/00_INDEX.md`** (this file) | Reading order and topic ownership map. |
| **`docs/01_CURRENT_STATE_AND_GAPS.md`** | Gap matrix: requirement &#124; code exists &#124; tested &#124; production-ready &#124; gap &#124; priority (P0-P4). Code-verified, not doc-verified. Covers all founder requirements from FOUNDER_REQUIREMENTS lines 1-106 + sections 1-108. |
| **`docs/02_TARGET_ARCHITECTURE.md`** | Target modular design: core + market adapters + broker adapters; separation of duties (pre-market, analyst, boss, desk, risk, monitor, post-market); event model; order/position state machines; modes (paper/shadow/limited-live/live); tech stack. |
| **`docs/03_DATA_CONTRACTS.md`** | Data capture spec: daily set (index ticks, full chain, futures, heavyweights, news, levels), join keys, storage, nightly warehouse job, Dhan feed mapping. |
| **`docs/04_MIGRATION_PLAN.md`** | Ordered PRs with scope, acceptance test, risk, performance budget. PR-001: data recorder (can't be backfilled, highest priority). PR-002: P0 safety core (risk engine, kill switches, order state machine, broker adapter, reconciliation). |
| **`docs/13_FOUNDER_GUIDE.md`** | Plain-English guide for Sahil: how the system works, how to control it, what each stage does, health indicators, emergency controls. |
| **`AGENTS.md`** (root) | Ponytail principles, .md reading restrictions, test-before-claim, PR template. |
| **`.cursor/rules/`** (directory) | Always-on rules: docs auditor, departments, file creation, continue-prior-chat, expert coalition. |
| **`docs/MASTER_REQUIREMENTS.md`** | Historical master requirements (referenced by rules, may predate FOUNDER_REQUIREMENTS upload). |
| **`docs/FILE_CREATION.md`** | Allowed/forbidden new file names. |
| **`teams/*/docs/SKILL.md`** | Team operational playbooks (duties, inputs, output template, quality bar, must-not rules). |
| **Uploaded founder documents** | `uploads/FOUNDER_REQUIREMENTS_v1_2026-09-26_b562.md` (source of truth lines 1-106), `EXPECTATIONS_DIGEST_c332.md`, `lab_journal_a989.md`, `comparison_table_5b04.md`, `data_inventory_bcba.md`. |
| **Uploaded phase reports** | `uploads/report_94e3.md` (Phase 1 loss breakdown Sep 21-25), `phase2_report_f22f.md` (model/analyst diagnostics), `phase3_report_6418.md` (honest backtests, proven fixes). |
| **Audit artifacts** | `/opt/cursor/artifacts/rebuild/REPO_AUDIT.md`, `TARGET_ARCHITECTURE.md`, `MIGRATION_PLAN.md`, `AGENTS.md`, `SUMMARY.md` (previous audit deliverables, now replaced by committed docs). |

---

## For AI Agents

**Before working on a ticket:**
1. Read `docs/00_INDEX.md` (this file) to understand structure.
2. Check the topic ownership map above. Open the single owner document for your topic.
3. Read `AGENTS.md` for rules (ponytail, no runtime .md, test first, PR template).
4. If creating files, verify names against `docs/FILE_CREATION.md`.
5. After editing requirement/HANDOFF/PLAN/AGENT docs, run `python -m docs_auditor`.

**Do not:** Glob markdown files (`**/*.md`). Do not read recon dumps, old dated `BACKTEST_*` not cited by scoreboard, or youtube `PLAN.md` unless doing collector work.

**Do:** Read the specific docs you need (from this index), then the relevant team `SKILL.md` if applicable.

---

## Reading Order for Specific Tasks

### "I want to add a new strategy or improve an existing one"
1. `docs/13_FOUNDER_GUIDE.md` § How the System Works (understand the flow)
2. `docs/01_CURRENT_STATE_AND_GAPS.md` § Lab Results, § Proven Fixes, § Known Bugs (learn what failed and what worked)
3. `teams/04_quant/docs/SKILL.md` (if it exists; strategy design playbook)
4. `teams/06_backtesting/docs/SKILL.md` (if it exists; honest backtest rules)
5. `docs/03_DATA_CONTRACTS.md` (check available data)
6. `AGENTS.md` § PR Template (prepare handoff block with backtest results)

### "I want to fix a bug"
1. `docs/01_CURRENT_STATE_AND_GAPS.md` § Known Bugs (see if it's already documented)
2. Find the owner document from the topic map above
3. Read the relevant source file
4. `AGENTS.md` § Ponytail Principles (fix root cause, not symptom; shortest working diff)
5. `AGENTS.md` § PR Template (include repro steps, fix verification)

### "I want to build the data recorder"
1. `docs/04_MIGRATION_PLAN.md` PR-001 (scope, acceptance test, risk)
2. `docs/03_DATA_CONTRACTS.md` (complete data spec)
3. `docs/02_TARGET_ARCHITECTURE.md` § Data Capture Layer (design)
4. `docs/13_FOUNDER_GUIDE.md` § Data (founder-readable explanation)
5. `AGENTS.md` § Ponytail Principles (minimize code, reuse existing utils)

### "I want to deploy to a VPS"
1. `docs/02_TARGET_ARCHITECTURE.md` § Deployment
2. `docs/02_TARGET_ARCHITECTURE.md` § Technology Stack (dependencies)
3. `docs/01_CURRENT_STATE_AND_GAPS.md` § Tech Stack row (what's ready, what's not)
4. `docs/04_MIGRATION_PLAN.md` (which PRs must complete before VPS is viable)

---

**Last updated:** 2026-09-26 (Rebuild planning package)
