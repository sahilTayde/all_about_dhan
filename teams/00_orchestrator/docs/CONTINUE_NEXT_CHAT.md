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
4. docs/FILE_CREATION.md
Do not glob markdown. Do not create extra CONTINUE/HANDOFF/NOTES dumps.

Gate: NOT RESEARCH_READY_FOR_PROGRAMMING. PAPER only. NO_PROMOTE. STRATs UNVALIDATED. Dashboard P/L is MOCK. No live orders. Do not restart npm / Vite / paper ops until I ask. Never print secrets.

Left off 2026-09-16 ~11:20 IST: founder OPERATING PLAN frozen (three clocks). Product during cash hours = parallel PAPER books with round-trip P/L, not dealer OPEN_PAPER spray. Dual-tape stays the one live feed. NO_PROMOTE. Local sqlite — do not git-add.

Left off 2026-09-16 ~10:38 IST: deleted run_news_analyst / run_sentiment_analyst. Dual-tape is the paper bot. NO_PROMOTE. Local sqlite — do not git-add.

Left off 2026-09-15 (next chat): pre-market readiness. At 09:15 IST run paper dual-tape + desk_ml overlay. NO_PROMOTE. OpenAI ACCEPT_WITH_CAVEATS is paper only. No Super Orders. No live orders. Local sqlite — do not git-add.

Left off 2026-09-13: ITM champion PAPER board ready (MIX-CHAMP-* + desk leaderboard + assumed IST VWAP). Docs: teams/06_backtesting/docs/ITM_CHAMPION_PAPER_BOARD.md. CLI: python -m backtest_engine.run_itm_champions. Tuesday = PAPER watch only (prefer ITM PE near spot); live Super Orders refused. Next freeze only after live board evidence; then walk-forward OOS. KEEP_ALL. NO_PROMOTE. Local trading_agents_india.sqlite is working-tree only — do not git-add.
```

---

## Left-off 2026-09-16 ~11:20 IST — founder operating plan (PAPER books = product)

**Now:** Dual-tape can book `OPEN_PAPER` with live INDEX+ATM (`--paper-train`) but **`realized_pnl` is always null** — no stop/target/time-exit on that path. Concurrent ML / TV-EP / signal_lab / STRAT PIDs **were started** (see `data/recon/founder_live_loops.json` 06:56 IST). They **score or retune-propose**; they are **not** four round-trip paper books on the same tape. Old LLM `paper_ops` stays STOPPED. Gate **not** `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE.**

**Why the founder is right:** cash hours were spent on dealer dual-tape *opens* and HOLD notes. A strategy is not the product until it can **enter and exit** on live quotes so a **closed-premium P/L** exists. Win-rate claims stay forbidden.

**Next (only if founder says go):** first implementation slice = **exits on dual-tape** (stop/target or 15:00 IST time-exit; one open paper position per underlying; persist ATM strike on the ledger) **then** score **bound** MIX/STRAT on that same tape. Do not code until asked.

### Three clocks (IST)

| Clock | When | Founder does | Machine does | Must not |
|-------|------|--------------|--------------|----------|
| **PRE** | before 09:15 | Confirm token + overnight files exist | Load overnight **paper** params (`data/recon/tv_ep_paper_params_*.json`, desk_ml cache). `python -m desk_intel pre-market` (live data ok). Arm dual-tape waiter for 09:15 `--live-chain --tick-seconds 45 --paper-train` + overlay 90s. Canvas monitor ok. | Write `MIX-DEFAULT-BUY` production. Restart old LLM `paper_ops`. Start npm unless asked. Super Orders. |
| **OPEN** | 09:15–15:30 cash; **directional paper 09:30–15:00** | Watch one board. Ignore open spray. | **One** live dual-tape. **Parallel paper books** (same quotes): dealer, ML overlay, TV-EP shortlist, **bound** STRAT/MIX only. Each book: ENTRY + STOP/TARGET **or** time-exit so P/L can exist. Leaderboard = **CLOSED** paper premium P/L only. Zero blocking LLM on 45s path. | Live fills. 14 unbound STRATs as live books. Rank by open tickets or confirm-note count. Invent Dhan quotes. |
| **POST** | after 15:30 (yaml nightly ~15:40) | Read recon + mistakes | Flatten remaining paper at close if still OPEN. `python -m jobs post-market` / `desk_intel nightly`. `agent_rag eod-recon`. Emit `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. Overnight tune writes **paper files only**. Next day PRE loads those files. | Auto-retune production. `production_params_written=true`. git-add sqlite. Treat one session as a promote. |

Stop flags: `paper_dual_tape_STOPPED.flag` · `founder_eval_STOPPED.flag`. Old: `paper_ops_STOPPED.flag` (leave it).

### Honest inventory (runs vs dry vs missing)

| Lane | What actually runs today | Bound vs dry | Missing for a fair session |
|------|--------------------------|--------------|----------------------------|
| **Feed** | Dual-tape `--live-chain` 45s, `llm: false`, orders refused. Ticks → JSONL + sqlite `dual_tape_ticks`. | Live Dhan INDEX+ATM when token alive. | Not a second feed. |
| **Dealer book** | `--paper-train` appends `PAPER_TRADE` `OPEN_PAPER` on CE/PE when `allow_new_paper_ce_pe`. | Spray opens; dealer HOLD still notes. | **Exits.** One-position-per-name. Strike on ledger. `realized_pnl`. |
| **ML overlay** | `desk_ml overlay` after tick + founder `loop_ml` (book-tune / fit / mrr-fit / score). | Labels HOLD/WATCH. IsolationForest = anomaly HOLD not BUY. ML-002 window 90 often `DATA_INSUFFICIENT`. | Own closed paper book (entry/exit vs ATM LTP). |
| **TV-EP** | `loop_tv`: `tv-ep-paper-tune` NIFTY + factory grid. Catalog MIX-TV-EP-001–025 KEEP_ALL. | Historical/cache grid ≠ today premium. Session tune **does not** write MIX-DEFAULT-BUY production. Shortlist that has fired mock tickets before: **018, 010, 009, DEFAULT-BUY** (0 wins claimed). Most others 0 trades (lookback / US-crypto / unported). | Closed **premium** P/L on **today’s** dual-tape, not INDEX-proxy WATCH cells. |
| **signal_lab** | Replays fixed days `2026-09-10/11/15`. | Historical lab, **not** live session book. | Park during OPEN or retarget to today tape. |
| **STRAT/MIX loop** | `loop_strat`: print `EVALUATOR_BINDS` + `backtest_engine --dry-run` project/scan/option/books. | **Dry.** Not a live book. | Bind only available evaluators to dual-tape (below). |
| **Old LLM B** | `paper_ops_STOPPED.flag`. News/sentiment agents **deleted**. | Stopped. | Do **not** restart this week. |

**Paper binders that may score (available=True)** — still HYPOTHESIS / NO_PROMOTE, **not** all 14 STRATs:

- MIX: `MIX-DEFAULT-BUY`, `MIX-TA-FLOW-RISK`, `MIX-TA-EVENT-HOLD`, `MIX-TA-EXEC-SANITY`, `MIX-TA-MARKET-HOURS`, `MIX-LEAN-SPOT-ATM`, `MIX-IMPULSE-1M`, `MIX-003-INDEX-PROXY`, `MIX-006-INDEX-PROXY`, `MIX-PCR-EXTREME-HOLD`, `MIX-SELL-CREDIT-PARK`, `MIX-DUAL-INDEX-MASTER`
- STRAT **bound:** `003` (inherits default mix lean — proxy, not a separate bar pass), `007`/`008`/`009` (**filters** from ticket text, not standalone buy books), `013`/`014` (**seller park** — never a buy entry)
- STRAT **unbound (KEEP_ALL, one aggregate DI — do not fire as live books):** `001`, `002`, `004`, `005`, `006`, `010`, `011`, `012`

Working-path catalog (04): bound scoring path ≈ `MIX-DEFAULT-BUY` + STRAT-003/007/008/009 + `MIX-TA-*` + `MIX-LEAN-*`. `MIX-CLUB-GR` PARKED off confidence (not killed). No STRAT-015+.

### Parallel vs park (OPEN)

**Run in parallel (one tape):** dual-tape feed · dealer paper book (once exits exist) · ML score/overlay (labels until it has a book) · TV-EP **shortlist only** (018/010/009 + DEFAULT-BUY; KEEP_ALL catalog stays on disk) · bound MIX-LEAN / MIX-003-INDEX-PROXY if they emit CE/PE with an exit rule.

**Park this week:** unbound STRAT-001/002/004/005/006/010/011/012 as live books · STRAT-013/014 buy · Okala/CF · full 912-cell TV-EP grid during cash hours (POST/overnight only) · signal_lab historic days during OPEN · LLM market-hours · live Super Orders · npm unless founder asks.

### Leaderboard (definition)

| Rule | Detail |
|------|--------|
| **Metric** | Sum of **closed** paper **option-premium** P/L (exit − entry on ATM CE or PE LTP from the live tape), 1 lot shadow, costs tagged HYPOTHESIS until 06 says otherwise. |
| **Unit** | One row per **book** (dealer / ML / TV-EP-id / bound MIX-id), per underlying, per IST session. |
| **When it updates** | On **CLOSE** (stop, target, or 15:00 time-exit). Open `OPEN_PAPER` rows **do not** rank. |
| **Not the score** | Confirm-note count, win %, IsolationForest HOLD, INDEX-proxy grid WATCH, dry `--dry-run` books, ITM champion **historical** `/desk` board. |
| **Honesty** | `win_rate=null` on catalog. Rank ≠ promote. Same quotes for every book. Missing strike / invented fill ⇒ row is invalid, not a win. |

Existing `TV_EP_LEADERBOARD.md` / factory grid is **cache/fixture**, INDEX proxy ≠ option P/L. Session board must be a **new** closed-premium table (recon JSON), not that markdown as proof.

### First slice if founder says go

1. Dual-tape: mark-to-market OPEN rows; stop/target **or** 15:00 flatten; one open per underlying; write `atm_strike` + `exit` + `realized_pnl`.
2. Attach bound MIX/STRAT-003 lean as **separate book ids** on the **same** tick — still paper, still NO_PROMOTE.
3. Session leaderboard JSON from closed rows only.
4. POST: nightly + `RETUNE_PROPOSAL BACKTEST_REQUIRED`; overnight params stay under `data/recon/`.

### Will NOT do this week

Live Super Orders / `ExecutionClient` · promote / `RESEARCH_READY_FOR_PROGRAMMING` · 14 unbound STRATs as live books · LLM market-hours restart · auto-retune MIX-DEFAULT-BUY · git-add `trading_agents_india.sqlite` · invent fills/quotes/win rates · blocking LLM on 45s path.

## Left-off 2026-09-16 ~10:25 IST — feed monitor on existing loop (NO_PROMOTE)

| Topic | State |
|-------|--------|
| IST | **Wed 2026-09-16 ~10:25** — cash OPEN |
| Monitor | Same `scripts/paper_ops_monitor.py` · **Dhan feed class** on Attention · `data/recon/FEED_HEALTH.json` · `ATTENTION_QUEUE_2026-09-16.md` |
| Tape | Dual-tape **RUNNING** `--paper-train --live-chain` after token refresh · live INDEX+ATM · not fixture |
| Read | Desk DI/STALE after API death = **missing print**. HOLD after live LTP = dealer label. **Not** “all denied”. |
| Book | `teams/00_orchestrator/canvases/paper_ops_board.html` |
| Super Orders | **NO** |
| Promote | **NO_PROMOTE** |

## Left-off 2026-09-16 ~06:55 IST — pre-market + paper bots + tune loops (NO_PROMOTE)

| Topic | State |
|-------|--------|
| IST | **Wed 2026-09-16 ~06:55** — pre-open. Dual-tape **arms 09:15 IST** |
| Nightly 15-Sep | **Already ran** (`0d87239`). Fills **0**. Taken **0**. Skipped **3** EXPIRED. Shadow/user P/L **0**. `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. `tune_status=RAN_EMPTY_LEDGER`. Not a win rate. |
| Pre-market | `python -m desk_intel pre-market` **live rc=0**. Dhan chain **200**. News **12**. GIFT/SGX/NSE pre-open **DATA_INSUFFICIENT**. Regime **RISK_OFF** (keyword HYPOTHESIS). Paper tickets **NEUTRAL / VETOED** ×3 |
| Bots | Waiter **95455** → dual-tape `--live-chain` at 09:15 + overlay 90s. Monitor **95466**. **Not** old LLM `paper_ops` |
| Tune / STRAT | ML **95470** · TV-EP **95469** · signal_lab **95468** · STRAT/MIX dry **95467**. Paper files only. KEEP_ALL 001–014. `production_params_written` false |
| Book | `teams/00_orchestrator/canvases/paper_ops_board.html` |
| Stop | `touch data/recon/paper_dual_tape_STOPPED.flag` · `touch data/recon/founder_eval_STOPPED.flag` |
| Super Orders | **NO** |
| Promote | **NO_PROMOTE** |

## Left-off 2026-09-15 ~14:45 IST — STOP all loops + POST_MARKET nightly (NO_PROMOTE)

| Topic | State |
|-------|--------|
| IST | **Tue 2026-09-15 ~14:45** — founder **stopped** live paper before close |
| Dual-tape / overlay / eval / canvas | **STOPPED**. Flags: `paper_dual_tape_STOPPED.flag`, `founder_eval_STOPPED.flag`. Old LLM `paper_ops` still STOPPED |
| Nightly | `python -m jobs post-market` **ok**. `session_kind=NORMAL`. `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. `keep_current_strategy` true. `production_params_written` false |
| EOD | `python -m agent_rag eod-recon --day 2026-09-15` · `tune_status=RAN_EMPTY_LEDGER` · `tuned=false` |
| Paper fills | **0**. User taken **0**. User skipped **3** (EXPIRED). Win rate **none** |
| PhD handoff | `teams/02_phd_math/docs/handoffs/NIGHTLY_2026-09-15.md` |
| Board | `teams/00_orchestrator/canvases/paper_ops_board.html` (frozen at stop) |
| Super Orders | **NO** |
| Promote | **NO_PROMOTE** |

## Left-off 2026-09-15 ~10:45 IST — founder push main + concurrent paper loops (NO_PROMOTE)

| Topic | State |
|-------|--------|
| IST | **Tue 2026-09-15 ~10:45** — cash **OPEN**; directional paper **09:30–15:00** |
| Git | Fast-forward `main` ← `cursor/live-paper-ml-tape-3203` (`e8d99cc`). Premarket unique commits **not** merged (CONTINUE already superseded); `scripts/paper_ops_monitor.py` dual-tape snapshot taken from `cursor/premarket-paper-dual-tape-a7a0`. Local sqlite **not** pushed. |
| Dual-tape | PID **74510** kept · `--live-chain --tick-seconds 45 --max-ticks 0` · **llm false** · orders refused |
| Overlay waiter | PID **72493** · `desk_ml overlay --source dual-tape` every 90s until **15:35 IST** |
| Canvas | PID **82631** · `scripts/paper_ops_monitor.py --interval 25` (respawned detached after 82167 died) |
| Overlay | Session **HOLD**. NIFTY ML-001 `PREMIUM_DIVERGENCE` HOLD. BANKNIFTY `REGIME_OK` WATCH_ONLY. SENSEX `REGIME_OK` WATCH_ONLY. ML-002 **DATA_INSUFFICIENT** (window 90). `production_params_written` false |
| Paper fills | **0** |
| OKLA | **UNKNOWN** as `OKLA`. **Okala** exists as removed CF CLI (`okala-in` / `okala-signal` → stderr + exit 2). Not a named MIX loop. |
| Extra loops | ML **82632** · TV-EP **82633** · Okala idle **82634** · signal_lab **82635** · STRAT/MIX dry **82636**. JSON: `data/recon/founder_live_loops.json`. Stop: `touch data/recon/founder_eval_STOPPED.flag` |
| Super Orders | **NO** |
| Promote | **NO_PROMOTE** |

## Left-off 2026-09-15 ~09:40 IST — live paper dual-tape + ML/TV paper tune (NO_PROMOTE)

| Topic | State |
|-------|--------|
| IST | **Tue 2026-09-15 ~09:40** — cash **OPEN**; directional paper **09:30–15:00** |
| Dual-tape | PID **74510** · `--live-chain --tick-seconds 45 --max-ticks 0` · started 09:15:46 IST · **llm false** · orders refused · tick ~25 |
| Overlay waiter | PID **72493** · `desk_ml overlay --source dual-tape` every 90s · canvas monitor **72494** |
| Overlay | Session **HOLD**. NIFTY ML-001 `IF_OUTLIER` / WATCH_ONLY. BANKNIFTY `PREMIUM_DIVERGENCE` HOLD. SENSEX `REGIME_OK` WATCH_ONLY. ML-002 dual-tape **DATA_INSUFFICIENT** (window 90). `production_params_written` false |
| Paper fills | **0**. Ledger is `DESK_DIVERGENCE` notes only. Live ≥09:15: **34** BUY_*_CONFIRM notes + **38** HOLD notes (16 dead-band ticks + 9+ directional). Overnight stale ticks 692 HOLD. **Not a win rate.** |
| ML paper tune | `desk_ml book-tune` + fit/mrr-fit 40/60/90 embargo 5. NIFTY ML-002 preferred window **90** in-sample CANDIDATE. BN/SX OU **NOT_MEAN_REVERTING**. IsolationForest = anomaly HOLD, not BUY |
| TV-EP | Factory grid cache `--tf 1 3 5 15`: 912 cells WATCH 225 / TESTED_FAIL 412 / PARK 275. Paper-tune vs dual-tape LTP clones: KEEP_ALL 001–025 + DEFAULT-BUY. Most 0 trades (lookback / US-crypto / unported). Fired MOCK tickets (0 wins): 018, 010, 009, DEFAULT-BUY. INDEX JSON cache last **2026-09-03** ≠ today premium |
| Stop | `touch data/recon/paper_dual_tape_STOPPED.flag` |
| Super Orders | **NO** |
| Promote | **NO_PROMOTE** |

## Left-off 2026-09-15 — next chat = pre-market + live paper (no Super Orders)

| Topic | State |
|-------|--------|
| Next chat | **Pre-market readiness**, then paper at **09:15 IST** |
| Dual-tape | `python -m trading_agents_india dual-tape --live-chain` — no LLM, no orders |
| Overlay | `python -m desk_ml score --underlying NIFTY --source dual-tape` — FOLLOW-GAP HOLD |
| OpenAI overlay | `ACCEPT_WITH_CAVEATS` **paper only** — [`OPENAI_OVERLAY_REVIEW.md`](../../06_backtesting/docs/OPENAI_OVERLAY_REVIEW.md) |
| Session prep | [`SESSION_PREP_ML.md`](../../06_backtesting/docs/SESSION_PREP_ML.md) |
| Super Orders | **NO** |
| Promote | **NO_PROMOTE** |

---

## Left-off 2026-09-13 — ITM champions / Tuesday paper

| Topic | State |
|-------|--------|
| Champion catalog | `packages/backtest/src/backtest_engine/itm_champions.py` (`MIX-CHAMP-*`) |
| Leaderboard runner | `python -m backtest_engine.run_itm_champions` → `data/recon/itm_champion_leaderboard.json` |
| Desk UI | `/desk` → **ITM champion leaderboard** (wins, streaks, success %, P/L) |
| API | `GET /paper/backtests/itm-champions` |
| Spec | [`teams/06_backtesting/docs/ITM_CHAMPION_PAPER_BOARD.md`](../../06_backtesting/docs/ITM_CHAMPION_PAPER_BOARD.md) |
| VWAP | IST session; volume when >0; equal-weight **assume** if vol=0 |
| Strike sweep lab | `data/recon/itm_strike_sweep.json` (10 PE + 10 CE × 1m/5m) |
| Live orders | **REFUSED** |
| Next | (1) live PAPER session on board (2) walk-forward OOS (3) freeze discussion — still NO_PROMOTE |

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
| Paper market-hours (old LLM loop) | **stopped** — `data/recon/paper_ops_STOPPED.flag` (2026-09-10). Do **not** restart that LLM stack unless asked. |
| Dual-tape paper (2026-09-14 founder start) | `python -m trading_agents_india dual-tape` — no LLM, no orders. Stop: `paper_dual_tape_STOPPED.flag`. Doc: [`MARKET_HOURS_DUAL_TAPE.md`](MARKET_HOURS_DUAL_TAPE.md) |
| `NEWS_VETO_ENABLED` | **false** unless founder asks |

09 five-pass has **not** passed. Notes ≠ pass. Mandate ≠ “you are profitable.”

---

## What is true as of 2026-09-08

**Git:** `origin/main` includes `4edb503` (gather/env/CF). This CONTINUE file is the wake-up. Confirm with `git log -1 --oneline origin/main`. Remote `https://github.com/sahilTayde/all_about_dhan.git`

**Shipped on main (this slice):**

| Topic | Commit / path |
|-------|----------------|
| Paper-hours gather | `d5eff8f` — live chain ATM/PCR (`hooks/chain.py`), INDEX 1m (`hooks/index_bars.py`), gpt-5.4 / gpt-5.4-nano `max_completion_tokens` |
| Cloud Agent env | `934e969` + `23cb370` + `4e19562` — `.cursor/install.sh` materializes gitignored `.env` from secrets; ports are `{name,port}` objects. **Do not commit `.env`.** |
| CF transcript markdown | `4edb503` |

**PAPER session (laptop, then stopped):** ticks ~90s; live Dhan INDEX 1m + `optionchain_atm`; LLM on after nano param fix; execution refused; fills 0; news gather off. Last tick ~11:53 IST. Honest gaps: Vite/API DOWN (expected), news OFF (requested), unbound STRAT-001–014 DI (KEEP_ALL), EVENT_MEMORY empty.

**Local sqlite (do not git-add):** working `data/knowledge/trading_agents_india.sqlite` is the 2026-09-08 gather book. Tag `backup/local-main-3f20ab6` is a **different** 2026-09-07 vetoed/NEWS_DAY book — do not reset `main` onto it.

**Cloud env:** personal Override may not have fully Saved. If Save is gone, re-propose successful build `bld-20260908-755da165-a259-46ed-a39d-a7f4581233c7`. This laptop chat is not booted from that snapshot.

**Next founder track (2026-09-10):** token **works** (data only). Warehouse **one-shot ingest** coded. Paper loop still **stopped**. Next: **PM-001 `/pm`** when founder allows npm. KEEP_ALL. **NO_PROMOTE.**

---

## Simple signal path (still PAPER notify only)

| Topic | Path |
|-------|------|
| Plain English | [`HOW_SIGNALS_WORK.md`](HOW_SIGNALS_WORK.md) |
| Cleanup canvas | [`/cleanup`](../../../apps/web/public/cleanup-canvas.html) — DhanHQ-only reset board |
| Market-hours runbook | [`PAPER_MARKET_HOURS_RUNBOOK.md`](PAPER_MARKET_HOURS_RUNBOOK.md) |

Old LLM `market-hours` / paper_ops: still respect `paper_ops_STOPPED.flag` unless founder asks. Dual-tape (founder asked 2026-09-14): `dual-tape --live-chain`; stop with `paper_dual_tape_STOPPED.flag`.

---

## Archives (do not re-read unless the task needs them)

| Slice | Pointer |
|-------|---------|
| Overnight archives (CF) | **Removed** 2026-09-09 DhanHQ-only reset. |
| File names | [`docs/FILE_CREATION.md`](../../../docs/FILE_CREATION.md) — do not create extra CONTINUE/HANDOFF dumps |
| Paper-agents rollup | [`BACKTEST_PAPER_AGENTS_2026-09-10.md`](../../06_backtesting/docs/BACKTEST_PAPER_AGENTS_2026-09-10.md) — **NO_PROMOTE** |
| 00 HANDOFF log | [`HANDOFF.md`](../HANDOFF.md) (newest **block** only) |

---

## Score sheet pointers

| Read first | Path |
|------------|------|
| Master sheet | `docs/MASTER_REQUIREMENTS.md` |
| Company departments | [`docs/COMPANY_DEPARTMENTS.md`](../../../docs/COMPANY_DEPARTMENTS.md) |
| Agents | `AGENT.md` |
| Review brief | `teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md` |
| Boss | `teams/00_orchestrator/docs/BOSS_AGENT.md` |
| Research Boss (01, after hours) | [`RESEARCH_BOSS_SKILL.md`](RESEARCH_BOSS_SKILL.md) · 00 [`RESEARCH_BOSS_LOOP.md`](RESEARCH_BOSS_LOOP.md) · [`TOPIC_COVERAGE.md`](../../01_research/docs/TOPIC_COVERAGE.md) — KNOWN vs DI; 00 still default ticket |
| MIX catalog | `teams/04_quant/docs/MIX_CATALOG.md` |
| Docs auditor | `python -m docs_auditor` |
| File names | [`docs/FILE_CREATION.md`](../../../docs/FILE_CREATION.md) |

**KEEP_ALL:** STRAT-001–014 stay `BACKTEST_BOOK` / `UNVALIDATED`. No STRAT-015+. Confidence ≠ win rate.  
`MIX-CLUB-GR` after-cost NIFTY 44.4% — **FAIL promote**.

---

### Agent RAG / EOD recon

**Last EOD stub:** 2026-09-15 (`python -m agent_rag eod-recon`)
- session_kind: `NORMAL` (score_track=`SCORE_SAMPLE`)
- RETUNE_PROPOSAL: **`BACKTEST_REQUIRED`** / tune_status=`RAN_EMPTY_LEDGER` (no auto-retune; `keep_current_strategy: true`; `production_params_written: false`)
- recon: `data/recon/EOD_RECON_2026-09-15.json`
- retune artifact: `data/recon/RETUNE_PROPOSAL_2026-09-15.json`
- KB: `data/knowledge/agent_rag.sqlite` ([`AGENT_RAG.md`](../../01_research/docs/AGENT_RAG.md)) — does **not** touch `transcripts.sqlite`
- Paper agents backtest rollup: [`BACKTEST_PAPER_AGENTS_2026-09-15.md`](../../06_backtesting/docs/BACKTEST_PAPER_AGENTS_2026-09-15.md) — **NO_PROMOTE**

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
