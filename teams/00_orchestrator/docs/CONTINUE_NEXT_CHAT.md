# Continue here — next Composer chat

**Handoff frozen:** 2026-09-08 (token reset).  
**Prior conversation (do not reload):** [all about dhan bootstrap](1b8d6990-a15f-4724-b18e-31ce6631455b)

This file is the **left-off**. `docs/MASTER_REQUIREMENTS.md` is the **score**. Do not paste the old thread.

---

## Paste this as the **first message** of a new chat

```
Continue all_about_dhan. Do not reload the bootstrap chat.

Read in order:
1. docs/MASTER_REQUIREMENTS.md
2. teams/00_orchestrator/docs/CONTINUE_NEXT_CHAT.md
3. AGENT.md

Gate: NOT RESEARCH_READY_FOR_PROGRAMMING. PAPER only. NO_PROMOTE. STRATs UNVALIDATED. Dashboard P/L is MOCK. No live orders. Do not restart npm / Vite / paper ops until I ask. Never print secrets.

Left off 2026-09-08: PAPER market-hours ran --mode PAPER --tick-seconds 90 --use-llm --no-gather-news --live-chain; founder stop 11:54 IST; paper_ops_STOPPED.flag present. Gather (live chain ATM/PCR + INDEX 1m + gpt-5.4-nano max_completion_tokens) + Cloud Agent env + CF transcript markdown are on origin/main @ 4edb503. Next: strategies (KEEP_ALL, no STRAT-015+, no promote, no live orders). Local trading_agents_india.sqlite is working-tree only — do not git-add. Cloud env Save may still be incomplete.
```

---

## Current gate (hard)

| Gate | State |
|------|--------|
| `RESEARCH_READY_FOR_PROGRAMMING` | **not set** |
| Trading / agents mode | **PAPER only** |
| Promote any MIX / STRAT / paper book | **NO_PROMOTE** |
| Live Dhan orders | **refused** (always) |
| Dashboard P/L | **MOCK** / paper labels |
| npm / Vite | **stopped** — do **not** restart until founder asks |
| Paper market-hours | **stopped** 11:54 IST — `data/recon/paper_ops_STOPPED.flag` — do **not** restart until asked |
| `NEWS_VETO_ENABLED` | **false** unless founder asks |

09 five-pass has **not** passed. Notes ≠ pass. Mandate ≠ “you are profitable.”

---

## What is true as of 2026-09-08

**Git:** `origin/main` tip `4edb503` — `https://github.com/sahilTayde/all_about_dhan.git`

**Shipped on main (this slice):**

| Topic | Commit / path |
|-------|----------------|
| Paper-hours gather | `d5eff8f` — live chain ATM/PCR (`hooks/chain.py`), INDEX 1m (`hooks/index_bars.py`), gpt-5.4 / gpt-5.4-nano `max_completion_tokens` |
| Cloud Agent env | `934e969` + `23cb370` + `4e19562` — `.cursor/install.sh` materializes gitignored `.env` from secrets; ports are `{name,port}` objects. **Do not commit `.env`.** |
| CF transcript markdown | `4edb503` |

**PAPER session (laptop, then stopped):** ticks ~90s; live Dhan INDEX 1m + `optionchain_atm`; LLM on after nano param fix; execution refused; fills 0; news gather off. Last tick ~11:53 IST. Honest gaps: Vite/API DOWN (expected), news OFF (requested), unbound STRAT-001–014 DI (KEEP_ALL), EVENT_MEMORY empty.

**Local sqlite (do not git-add):** working `data/knowledge/trading_agents_india.sqlite` is the 2026-09-08 gather book. Tag `backup/local-main-3f20ab6` is a **different** 2026-09-07 vetoed/NEWS_DAY book — do not reset `main` onto it.

**Cloud env:** personal Override may not have fully Saved. If Save is gone, re-propose successful build `bld-20260908-755da165-a259-46ed-a39d-a7f4581233c7`. This laptop chat is not booted from that snapshot.

**Next founder track:** **strategies** — KEEP_ALL `STRAT-001`–`014` stay `BACKTEST_BOOK` / `UNVALIDATED`. No `STRAT-015+`. New clubs = `MIX-*`. Use 2026-09-08 sqlite as gather evidence only; 2026-09-07 tagged sqlite is a separate vetoed book. **NO_PROMOTE.**

---

## Simple signal path (still PAPER notify only)

| Topic | Path |
|-------|------|
| Plain English | [`HOW_SIGNALS_WORK.md`](HOW_SIGNALS_WORK.md) |
| Okala-IN PAPER accept | [`OKALA_IN_PAPER_ACCEPT.md`](../../04_quant/docs/OKALA_IN_PAPER_ACCEPT.md) — **NO_PROMOTE** |
| Market-hours runbook | [`PAPER_MARKET_HOURS_RUNBOOK.md`](PAPER_MARKET_HOURS_RUNBOOK.md) |

Do not start the paper loop unless founder asks. If they do: `--no-gather-news --live-chain`; respect `paper_ops_STOPPED.flag`.

---

## Archives (do not re-read unless the task needs them)

| Slice | Pointer |
|-------|---------|
| Overnight D (CF BT + paper wire) | [`HOW_SIGNALS_WORK.md`](HOW_SIGNALS_WORK.md) · local `data/recon/CF_OVERNIGHT_BACKTEST_ROLLUP_2026-09-07.md` |
| Overnight A (CF inventory) | local `data/recon/CF_OVERNIGHT_INVENTORY_2026-09-07.md` · [`RETRY_TOMORROW.md`](../../01_research/docs/chart_fanatics/RETRY_TOMORROW.md) |
| Process P0/P1 2026-09-07 | `data/recon/PROCESS_FIXES_SHIPPED_2026-09-07.md` |
| Paper-agents rollup | [`BACKTEST_PAPER_AGENTS_2026-09-08.md`](../../06_backtesting/docs/BACKTEST_PAPER_AGENTS_2026-09-08.md) — **NO_PROMOTE** |
| 00 HANDOFF log | [`HANDOFF.md`](../HANDOFF.md) (newest first) |

CF ASR fail queue still exists (`RETRY_TOMORROW.md`). Not the next default ticket.

---

## Score sheet pointers

| Read first | Path |
|------------|------|
| Master sheet | `docs/MASTER_REQUIREMENTS.md` |
| Agents | `AGENT.md` |
| Review brief | `teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md` |
| Boss | `teams/00_orchestrator/docs/BOSS_AGENT.md` |
| MIX catalog | `teams/04_quant/docs/MIX_CATALOG.md` |
| Docs auditor | `python -m docs_auditor` |

**KEEP_ALL:** STRAT-001–014 stay `BACKTEST_BOOK` / `UNVALIDATED`. No STRAT-015+. Confidence ≠ win rate.  
`MIX-CLUB-GR` after-cost NIFTY 44.4% — **FAIL promote**.

---

## Do not

- Invent win rates or code live strategies
- Auto-retune after nightly
- Show MACD/RSI on the **customer** desk
- Treat Docs Auditor PASS as a product gate
- Promote ATR / CF / paper-agent FAIL books
- Restart npm / Vite / paper ops unless founder asks
- Print `.env` / tokens / secrets
- `git add` `data/knowledge/*.sqlite` or `.env`
- Force-push or delete KEEP_ALL STRATs
