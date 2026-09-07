# Process improvement — paper day 2026-09-07

**From:** 00 orchestrator (founder desk)  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING` · **PAPER only** · **NO_PROMOTE** · orders **REFUSED**  
**Mode:** process / ops honesty — not a promote, not a win-rate claim  
**Secrets:** none printed

---

## Verdict

Paper day ran hard and produced **zero directional customer tickets** because policy + fixtures held everything to HOLD/VETOED, not because the UI died. Background “agents” mostly **re-measured the same DI/level bugs** and burned OpenAI (rate-limit + connection failures) without shipping founder-visible fixes. There is **no runnable improvement-model CLI** in this repo — only scan/rollup loops and design-council notes. Next session must convert attention items into **owned P0 tickets with done-when paths**, cut LLM fan-out, and stop treating fixture NEWS_DAY as a live session tag.

---

## What actually happened today (facts + paths)

| Fact | Evidence |
|------|----------|
| Final ledger: **582 SIGNAL, all HOLD**; **0** CE/PE; **0** PAPER fills; shadow **582 SKIPPED** | `data/recon/DAY_ANALYSIS_2026-09-07.md` / `.json` · `data/recon/paper_ledger/2026-09-07.jsonl` (~47MB) |
| Candidates **12141** → DI **11502 (95%)** · VETOED **639** | same · ops status `data/recon/paper_ops_monitor_status.json` |
| UI empty strip = **HOLD → WAITING** (desk up) | `data/recon/UI_NO_SIGNAL_REVIEW_2026-09-07.md` · pack `data/recon/ui_no_signal_2026-09-07/` |
| Ops ticks ~**196**; `openai_used=true` **169** / false **27**; late errors **APIConnection\*** | `DAY_ANALYSIS_*.json` `ops_ticks` · `data/recon/paper_market_hours_ops.log` |
| Analysis loop ran all day (~5m / sometimes overlapping); attention stuck on **LEVELS_NON_NUMERIC** fixtures + DI ratio | `data/recon/paper_analysis_loop_ops.log` · `paper_attention_bugs.json` |
| EOD stub **NO_PROMOTE** / `BACKTEST_REQUIRED`; falsely said **paper ledger missing** | `data/recon/EOD_RECON_2026-09-07.json` (`as_of_utc` 10:14:37Z) while paper ledger existed |
| Paper-agents rollup **NO_PROMOTE** | `data/recon/BACKTEST_PAPER_AGENTS_2026-09-07.json` · `teams/06_backtesting/docs/BACKTEST_PAPER_AGENTS_2026-09-07.md` |
| Shutdown FINAL / STOPPED | `data/recon/paper_ops_shutdown_2026-09-07.json` · `paper_ops_STOPPED.flag` |
| OpenAI “review” notes repeatedly **no OpenAI / connection fail** | `teams/09_review/docs/PAPER_AGENTS_BACKTEST_OPENAI_REVIEW_2026-09-07.md` |

Roles that were alive (then killed): market-hours + ops monitor + analysis loop + Vite/API (see day analysis Shutdown). **Do not auto-restart** while `paper_ops_STOPPED.flag` exists unless founder asks.

---

## Why zero trades (ranked root causes)

1. **NEWS_DAY / MACRO_EVENT customer-ticket hold (dominant)**  
   SIGNAL reasons: `NEWS_DAY / MACRO_EVENT: hold customer ticket` on **555/582**; fixture-style `cited_news` Brent + RBI on **555**. Stage **HOLD/VETOED** on **573**. Soft-default market-hours: `--prefer-desk` + `--gather-news` **on** (`packages/trading_agents_india/__main__.py`). Policy is correct for real MACRO_EVENT — but today’s prints include **fixture / dry news overlays**, so the session never looked NORMAL for the customer ticket. Boss rule: news holds the ticket, does not delete STRATs ([`BOSS_AGENT.md`](../../teams/00_orchestrator/docs/BOSS_AGENT.md)).

2. **Only one PAPER evaluator is bound**  
   `candidate_audit.py`: evaluator available **only** when `candidate_id == ticket.default_mix_cited` (typically `MIX-DEFAULT-BUY`). That row → **VETOED 639**. All **STRAT-001–014** (+ unbound MIX-TA rows) → DI `no PAPER evaluator bound` (**11502** DI rows). KEEP_ALL preserved; DI is honesty — but founder sees “agents working” with **no bindable directional book**.

3. **Premium / OPTIDX / chain DI**  
   Gap buckets (day JSON): Dhan/chain/fixtures, OPTIDX premium unbound, EVENT_MEMORY empty, news feeds. Customer Entry/SL/Target stay DI even if lean unlocked ([`UI_NO_SIGNAL_REVIEW`](UI_NO_SIGNAL_REVIEW_2026-09-07.md)).

4. **Clock dead-band / outside shell (afternoon)**  
   After **15:00 IST**: `allow_directional_paper=false` (MIX-CLOCK-CAS). After **15:30**: outside shell. Cannot produce CE/PE then regardless of news.

5. **OpenAI failure did not cause zero trades**  
   LLM failed often (below) but rule fallback already HOLDs under NEWS_DAY. Fixing OpenAI alone **does not unlock CE/PE** under today’s veto stack.

---

## Why rate limits / LLM pain (who called, how often, overlap)

### Call shape (primary burner)

Per underlying tick, **~8–9 agents** call `LlmClient.complete_json` via `_llm_report` (news, sentiment, technical, chain, bull, bear, boss, risk; trader is rules-only) × **3 underlyings** ≈ **24–27 OpenAI JSON calls per tick**.

Daemon: `scripts/start_paper_ops_daemon.py` forces `--use-llm`, tick **60s**, `--live-chain` when Dhan creds load. Observed median tick spacing ~**92s** (LLM latency stretches the loop) across ~**196** ticks (~10:10–15:47 IST).

**Rough upper bound:** 196 × ~25 ≈ **~5k chat completions** in one NSE afternoon on one key — enough to trip provider rate limits repeatedly.

### Ledger proof (gap annotations on observations/signals)

| Class | Approx gap hits |
|-------|-----------------|
| `APIConnectionError` | **7068** |
| `RateLimitCooldown` | **2280** |
| `RateLimitError` (hard hit) | **228** |
| `APIConnectionCooldown` | **171** |

Day-analysis `ops_ticks.llm_error_classes` only shows late **APIConnection\*** because successful ticks omit error class and rate-limit windows often fell mid-day while `openai_used` still flipped true after cooldown. **Founder “rate limits multiple times” is real** — not imagination.

### Overlap / secondary

| Caller | LLM? | Notes |
|--------|------|-------|
| `market-hours --use-llm` | **yes** | Main burner |
| `paper_analysis_loop` → `agent_rag paper-backtest --no-openai` | no | Good — but still CPU churn every ~5m |
| `agent_rag` OpenAI review path | attempted | `PAPER_AGENTS_BACKTEST_OPENAI_REVIEW` shows `openai_used=false` + connection/BadRequest — burned retries without value |
| Multiple respawns (ops monitor `--allow-restart`) | yes | Fresh processes reset cooldowns; can **re-burst** into RateLimit |

Cooldown: `llm.py` process-local cooldown (30→300s) exists — **not shared across respawned PIDs**.

---

## Why founder saw “no improvement” (visibility / handoff / loop gaps)

1. **Analysis loop monitors; it does not ship.**  
   `scripts/paper_analysis_loop.py` rewrites `paper_attention_bugs.json` with the **same** `LEVELS_NON_NUMERIC` fixture rows and “DI ratio 95% — Tune data path” every cycle. Log proves oscillation `level_bugs=0` ↔ `4` after restarts — **no patch PR, no ticket close, no customer-visible change**.

2. **Ops canvas is operator-internal, not product.**  
   Monitor rewrites `~/.cursor/.../canvases/paper-operations-monitor.canvas.tsx`. Founder on `/` only sees WAITING. No “what we fixed today” strip.

3. **Team HANDOFF.md files are research-bind heavy, not paper-day delivery logs.**  
   `teams/00_orchestrator/HANDOFF.md` / CF bind blocks document prior MIX work. They do **not** append a dated “shipped vs claimed” for 2026-09-07 paper ops. Standing continue doc (`CONTINUE_NEXT_CHAT.md`) lagged until UI review note; process ownership of “done when” was missing.

4. **EOD looked at the wrong ledger path → false “no ledger”.**  
   `agent_rag.eod_recon._load_ledger` reads `data/desk_intel/ledger/{day}/ledger.json`. Paper agents write `data/recon/paper_ledger/{day}.jsonl`. Result: EOD said ledger missing while **47MB** of paper truth existed. Candidate audit (same package) *does* read paper_ledger — split brain.

5. **Agents claimed activity = ticks + rollups, not unlocks.**  
   OpenAI review notes repeat NO_PROMOTE / connection fail. Backtest rollup re-states prior FAIL books. That is honest — and **invisible as improvement** to a founder who wanted CE/PE paper tickets or clear unblockers.

6. **UI honesty without operator narrative.**  
   HOLD→WAITING is correct product behavior (`apps/web/src/lib/status.js`) but without a desk banner citing “NEWS_DAY fixture veto · premium DI · unbound STRAT evaluators” it looks like “agents did nothing.”

---

## Improvement model findings

### What we searched / ran

| Candidate | Result |
|-----------|--------|
| `python -m … improvement` / continuous-improvement / retro CLI | **None exists** (searched `packages/`, `scripts/`, `teams/`, `docs/`) |
| `scripts/paper_analysis_loop.py` | **Ran all day** — scan/attention only |
| `python -m agent_rag paper-backtest` / EOD | Ran; **NO_PROMOTE**; EOD ledger path bug |
| `python -m docs_auditor` | Standing checker — not a process improver |
| Design councils / Astra reviews | Docs only (`OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md`, Astra UX) — **not executed as a daily improvement loop** |
| `MISSED_TRADE_POSTMORTEM.md` | Notes template — not wired to paper ops |

**Conclusion:** The “improvement model” today is **implicit and broken**: detect → rewrite JSON → hope a human reads canvas. No close-the-loop owner, no done-when, no daily founder digest.

### Minimal model (propose — implement next session)

```text
DETECT (analysis loop / ops tick)
  → CLASSIFY (P0 unblock CE/PE paper | P1 cost/rate-limit | P2 hygiene)
  → OWN (team 00–09 + single path)
  → FIX or EXPLICITLY PARK with reason
  → PROVE (artifact path + before/after metric)
  → HANDOFF append + CONTINUE bullet + founder digest (≤10 lines)
```

Cadence: **one** digest at 15:35 IST + on-demand when P0 flips. Never claim promote. KEEP_ALL intact.

---

## Prioritized change list

### P0 — unblock honest paper CE/PE *or* make HOLD explainable

| ID | Change | Owner | Done when |
|----|--------|-------|-----------|
| P0-1 | **Separate fixture NEWS_DAY from live session tag.** Prefer-desk/gather-news must not force MACRO_EVENT hold from dry fixtures when `--live-chain` / live RSS says quiet. Label fixtures `FIXTURE` and exclude from customer veto unless founder `--simulate`. | 05 desk-intel + 00 + trading_agents_india | Next PAPER session on quiet calendar emits ≥1 non-HOLD **or** explicit `session_kind=NORMAL` with reasons that cite live (not Brent fixture); ledger reason counts show fixture NEWS_DAY ≈ 0 |
| P0-2 | **Founder-visible veto banner on `/`.** When all HOLD/VETOED, show top 3 reasons (NEWS_DAY / clock / premium DI / unbound evaluator) from `/paper/signal` — not blank WAITING only. | 07 coding + 05 CUSTOMER_TALK | Screenshot + API field; UI_NO_SIGNAL pack would not look “dead” |
| P0-3 | **Fix EOD ledger reader** to ingest `data/recon/paper_ledger/{day}.jsonl` (keep desk_intel path as secondary). Re-run `eod-recon` so `ledger.missing=false` when paper jsonl exists. | 01 agent_rag / 06 | `EOD_RECON_*.json` matches day-analysis signal counts; no false missing |
| P0-4 | **LLM budget for market-hours.** Cap: shared cooldown file across processes; reduce to **boss+risk+news** LLM (others rules) **or** 1 call / underlying / tick; default tick ≥90s when LLM on; analysis/review **never** compete without `--use-llm`. | 00 + trading_agents_india | Day ledger RateLimitError_hit ≈ 0 under same tick volume; ops_ticks expose `llm_calls_per_tick` |

### P1 — make work DONE and visible

| ID | Change | Owner | Done when |
|----|--------|-------|-----------|
| P1-1 | **Attention → ticket file.** Analysis loop appends `data/recon/ATTENTION_QUEUE_{day}.md` with owner + done-when; stops rewriting the same LEVELS_NON_NUMERIC without a 07 fix or explicit PARK. | 00 + 08 + analysis loop | Queue file exists; fixture LEVELS_NON_NUMERIC either fixed in `mock/signal.json` or PARKED with reason |
| P1-2 | **Daily founder digest** `data/recon/FOUNDER_DIGEST_{day}.md` (≤15 lines): signals CE/PE/HOLD, DI%, LLM errors, top P0, “shipped today” paths. Written at stop + 15:35. | 00 ops | Digest present for next session without reading 47MB jsonl |
| P1-3 | **Bind or quarantine STRAT evaluators.** Either (a) PAPER binders for a **named** MIX subset under PAPER_WATCH, or (b) stop flooding ledger with 14×DI unbound rows every tick (summarize once / tick). KEEP_ALL catalog unchanged. | 04 + 06 + trading_agents_india | Unbound DI rows per tick drop by ≥10× **or** ≥1 non-default candidate can leave DI without inventing fills |
| P1-4 | **Premium bind path honesty.** If live OPTIDX LTP available, bind customer slots; else single clear DI code — no index-as-premium. | 07 + backtest_engine premium helpers | `/paper/signal` premium_bind ≠ silent empty when LTP present |

### P2 — hygiene / research track (do not block paper ops)

| ID | Change | Owner | Done when |
|----|--------|-------|-----------|
| P2-1 | CF RETRY_TOMORROW ASR (fail=30) — unchanged research track | 01 | Inventory yes++ |
| P2-2 | Phase-11 bind Yush + Marco return — only when founder asks | 01 + 04 | Bind docs; no auto-club into DEFAULT |
| P2-3 | EVENT_MEMORY / news calendar for SCORE_SAMPLE | 05 + 06 | EOD can tag NORMAL honestly on quiet days |
| P2-4 | Shared RateLimit cooldown on disk + respawn backoff | trading_agents_india + ops monitor | Monitor restart does not reset LLM strike counter |

---

## What NOT to change

- **KEEP_ALL** STRAT-001–014 in `BACKTEST_BOOK` / UNVALIDATED — DI ≠ delete  
- **NO_PROMOTE** / not `RESEARCH_READY_FOR_PROGRAMMING` / no live orders / no `/alerts/orders`  
- News/MACRO_EVENT **hold ticket** policy (fix fixture pollution, not the hold rule)  
- Confidence ≠ win rate; MOCK book P/L ≠ evidence  
- Do **not** restart npm/Vite/paper ops unless founder asks  
- Do **not** invent Dhan quotes, lots, fills, or win rates as product truth  

---

## Improvement-model script status

**None to run.** Closest executed artifacts today:

- `scripts/paper_analysis_loop.py` → `data/recon/paper_attention_bugs.json`  
- `python -m agent_rag eod-recon` → `data/recon/EOD_RECON_2026-09-07.json` (ledger path bug)  
- `python -m agent_rag paper-backtest` → `data/recon/BACKTEST_PAPER_AGENTS_2026-09-07.json`  

Propose implement as `python -m desk_intel process-improve --day YYYY-MM-DD` (or `scripts/process_improve_day.py`) generating this report shape + digest — **after** P0-3 ledger fix. Out of scope to code in this recon-only pass unless founder asks.

---

## HANDOFF

**Accepted**

- Day facts from `DAY_ANALYSIS_2026-09-07.*`, UI no-signal pack, attention/ops logs, ledger gap tallies  
- Zero CE/PE explained as NEWS_DAY/fixture veto + single-evaluator VETOED + DI unbound STRATs + premium/clock — not “UI broken”  
- Rate-limit + connection pain from ~25 LLM calls/tick under `--use-llm`  
- Visibility gap: scan loops ≠ shipped improvements; EOD wrong ledger path  
- No improvement-model module exists; minimal detect→own→fix→prove→digest proposed  
- KEEP_ALL / NO_PROMOTE / orders refused  

**Rejected**

- Treating DI as catalog delete or promote signal  
- Claiming OpenAI fix alone unlocks directional paper under NEWS_DAY fixtures  
- Auto-restart of paper ops / npm from this report  
- Invented fills, win rates, or live orders  

**UNKNOWN / DATA_INSUFFICIENT**

- Whether a **true** quiet NORMAL session with live chain + premium LTP would emit CE/PE under current MIX-DEFAULT-BUY rules (needs next NSE session after P0-1)  
- Exact OpenAI account TPM/RPM ceiling (never log keys; only error classes observed)  
- Whether desk RSS “Brent/RBI” rows were live pulls or cached fixtures on 2026-09-07 (URLs present; calendar SCORE_SAMPLE still empty)  

**Next owners (immediate):** 00 schedule P0-1…P0-4; 07 banner; agent_rag EOD path; trading_agents_india LLM budget.
