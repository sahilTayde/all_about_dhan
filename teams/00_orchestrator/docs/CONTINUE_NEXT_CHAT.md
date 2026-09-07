# Continue here — next Composer chat

**Prior conversation (token-heavy):** [all about dhan bootstrap](1b8d6990-a15f-4724-b18e-31ce6631455b)

Paste this as the **first message** of a new chat:

> Continue `all_about_dhan` from [all about dhan bootstrap](1b8d6990-a15f-4724-b18e-31ce6631455b). Read `docs/MASTER_REQUIREMENTS.md`, this file, `AGENT.md`, and `teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md`. Do not restart npm until I ask. STRATs are UNVALIDATED. Dashboard P/L is MOCK. No live orders.

---

## Score

Not a live product. **`RESEARCH_READY_FOR_PROGRAMMING` is not set.**

| Read first | Path |
|------------|------|
| Master sheet | `docs/MASTER_REQUIREMENTS.md` |
| Agents | `AGENT.md` |
| Review brief | `teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md` |
| Algo YAML only | `teams/04_quant/docs/ALGO_HANDOFF.md` |
| Docs auditor | `python -m docs_auditor` |

## Coalition packets (English SOURCE_FACT)

- `teams/01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md` — **authority for STRAT-001–014 spoken rules**
- `teams/01_research/docs/SL_TP_EXTERNAL_HARVEST.md` — **@iqcapital_io harvest + transcript status** (2026-09-06)
- `teams/01_research/docs/SL_TP_CLASSIC_METHODS.md`

## Engine mix (HYPOTHESIS, KEEP_ALL)

Boss: `teams/00_orchestrator/docs/BOSS_AGENT.md`  
Catalog: `teams/04_quant/docs/MIX_CATALOG.md` — §9 **SL/TP MIX** rows + own **`MIX-DESK-IQ-ATR-RR2`**  
Default playbook: `MIX-DEFAULT-BUY` unchanged  
Levels code: `packages/backtest/src/backtest_engine/levels.py` (ATR method; `DESK_PLACEHOLDER` deprecated)  
SL/TP backtest: [`BACKTEST_SLTP_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_SLTP_2026-09-06.md) — **FAIL**, not a promote  
09: [`FIVE_PASS_SLTP_2026-09-06.md`](../../09_review/docs/FIVE_PASS_SLTP_2026-09-06.md) **FAILED**

**Customer ticket box:** CE/PE + stop/target from **named ATR MIX** when seed exists. Confidence ≠ win rate. Orders refused.

**MIX-CLUB-GR KEEP + PAPER_WATCH:** optimistic 69.4% / after-cost 44.4% FAIL promote — unchanged.

### Chart Fanatics — **RETRY TOMORROW** (fail=30 locked)

**Do first on next chat / Monday research pass:**  
[`RETRY_TOMORROW.md`](../../01_research/docs/chart_fanatics/RETRY_TOMORROW.md) — all **30** failed videos (no full transcript body). Prefer **ASR** (audio→whisper); do not caption-hammer. Start at `xUyqIjCfZzg`. Update inventory after each success.

Also pending (transcripts already **yes**): **Phase-11 bind** Yush `hvyf6frvCcA` + Marco return `T_djSNBmV00`.

### Workspace reclaim + Transcript KB (2026-09-06)

- **SQLite:** [`data/knowledge/transcripts.sqlite`](../../../data/knowledge/transcripts.sqlite) — videos / transcripts / binds / docs + **FTS5** (no vector index). How-to: [`TRANSCRIPT_KB.md`](../../01_research/docs/TRANSCRIPT_KB.md). Rebuild: `python scripts/build_transcript_kb.py`.
- **Deleted (safe):** 16 CF `audio/*.m4a` (~1.2G; each had `.asr.txt` + `*_TRANSCRIPT.md`), `apps/web/node_modules`, nested `teams/01_research/youtube/.venv`, `__pycache__` / `.pytest_cache` / `.DS_Store` / `apps/web/dist`. Size ~**2.0G → ~760M**.
- **Kept on purpose:** MD + ASR text, binds, root `.venv`, `packages/docs-auditor/.venv`, **`data/recon/ohlc` (~421M)** — ask before deleting.
- **fail=30 retry path (unchanged):** [`RETRY_TOMORROW.md`](../../01_research/docs/chart_fanatics/RETRY_TOMORROW.md) — ASR first; start `xUyqIjCfZzg`; captions still 429. After new ASR, rebuild KB.


### Chart Fanatics Phase-1+2+3+3B–3I+4+5+6+7+8+9+10 (2026-09-06) — Phase-10 bind DONE; Phase-3I ASR DONE; fail=30 remain; Phase-11 bind next

**CF Phase-2 (priority Fabio) done.** Phase-3 captions still **429**. **Phase-3B–3G ASR** landed **12** videos (inventory **yes=13** with Fabio captions). **Phase-4 Marco+Mayne**, **Phase-5 Marci+Tori**, **Phase-6 TG+Kane**, **Phase-7 Umar+Forest**, **Phase-8 Carmine+Jadecap**, **Phase-9 Usman+Brando** bind+MIX+proxy **DONE**.

- Channel: Chart Fanatics · `@chart-fanatics` · `UC2GyeAMRDA4cRIiISejML2g` · https://www.youtube.com/@chart-fanatics
- Priority LIVE: `tvERE-Beu2U` · guest Fabio Valentini · transcript **yes** · **BIND done**
  - MIX: `MIX-CF-FABIO-TREND-NY` + `MIX-CF-FABIO-MR-RANGE` (`EXTERNAL_RESEARCH`, OF **PARKED**, OHLC proxy **BACKTEST_BOOK**; not default)
  - Proxy backtest: [`BACKTEST_CF_FABIO_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_CF_FABIO_2026-09-06.md) — FAIL/WEAK, **no promote**
- Inventory: `CHANNEL_INVENTORY.md` — **yes=17 / fail=30** (channel **not** done; captions still blocked; Phase-3I ASR landed Trader Yush + Marco return)
- Phase-3B ASR + **Phase-4 DONE** (Marco / Mayne):
  - MIX: `MIX-CF-MARCO-LIQ-TRAP` + `MIX-CF-MARCO-INT-EXT` + `MIX-CF-MAYNE-ICT-HTF` + `MIX-CF-MAYNE-BREAKER`
  - Backtest: [`BACKTEST_CF_MARCO_MAYNE_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_CF_MARCO_MAYNE_2026-09-06.md) — honest, **no promote**
- Phase-3C ASR + **Phase-5 DONE** (Marci / Tori):
  - `AVVM-FyewLg` · guest **Marci Silfrain** · BIND [`AVVM-FyewLg_BIND.md`](../../01_research/docs/chart_fanatics/AVVM-FyewLg_BIND.md)
  - `VTEQ2fhGLqE` · guest **Tori Trades** · BIND [`VTEQ2fhGLqE_BIND.md`](../../01_research/docs/chart_fanatics/VTEQ2fhGLqE_BIND.md)
  - MIX: `MIX-CF-MARCI-RIZZY` + `MIX-CF-MARCI-BB-REALITY` + `MIX-CF-TORI-TL-BOUNCE` + `MIX-CF-TORI-TL-BREAK` (separate; not clubbed)
  - Catalog: `MIX_CATALOG.md` §12
  - Proxy CLI: `python -m backtest_engine --dry-run --years 2 cf-marci-tori`
  - Backtest: [`BACKTEST_CF_MARCI_TORI_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_CF_MARCI_TORI_2026-09-06.md) — honest, **no promote**
  - 02/03/09: [`CF_MARCI_TORI_MATH_NOTES.md`](../../02_phd_math/docs/CF_MARCI_TORI_MATH_NOTES.md), [`CF_MARCI_TORI_MARKET_NOTES.md`](../../03_phd_market/docs/CF_MARCI_TORI_MARKET_NOTES.md), [`CF_MARCI_TORI_REVIEW_NOTES.md`](../../09_review/docs/CF_MARCI_TORI_REVIEW_NOTES.md)
- Phase-3D ASR + **Phase-6 DONE** (TG Capital / Trader Kane):
  - `ADnslyKOwFE` · guest **TG Capital** (aka Tyler) · BIND [`ADnslyKOwFE_BIND.md`](../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md)
  - `HNuRp9Z1bMs` · guest **Trader Kane** · BIND [`HNuRp9Z1bMs_BIND.md`](../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md)
  - MIX: `MIX-CF-TG-TRIDENT` + `MIX-CF-TG-EMA-WAVE` + `MIX-CF-KANE-EQ50` + `MIX-CF-KANE-PO3-SMT` (separate; not clubbed)
  - Catalog: `MIX_CATALOG.md` §13
  - Proxy CLI: `python -m backtest_engine --dry-run --years 2 cf-tg-kane`
  - Backtest: [`BACKTEST_CF_TG_KANE_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_CF_TG_KANE_2026-09-06.md) — FAIL/WEAK, **no promote**; title “90%” = marketing
  - 02/03/09: [`CF_TG_KANE_MATH_NOTES.md`](../../02_phd_math/docs/CF_TG_KANE_MATH_NOTES.md), [`CF_TG_KANE_MARKET_NOTES.md`](../../03_phd_market/docs/CF_TG_KANE_MARKET_NOTES.md), [`CF_TG_KANE_REVIEW_NOTES.md`](../../09_review/docs/CF_TG_KANE_REVIEW_NOTES.md)
  - Log: [`PHASE3D_ASR_LOG.md`](../../01_research/docs/chart_fanatics/PHASE3D_ASR_LOG.md)
- Phase-3E ASR + **Phase-7 DONE** (Umar Ashraf / Forest Knight):
  - `IUo5AwmsE9A` · guest **Umar Ashraf** (TradeZella; ASR 'Buma Ashraf' UNKNOWN) · BIND [`IUo5AwmsE9A_BIND.md`](../../01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md)
  - `q_MdVlZ1SH4` · guest **Forest Knight** / aka Forest · BIND [`q_MdVlZ1SH4_BIND.md`](../../01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md)
  - MIX: `MIX-CF-UMAR-MORNING-TOP` + `MIX-CF-UMAR-OPENING-DRIVE` (DI) + `MIX-CF-FOREST-VPE-EDGE` + `MIX-CF-FOREST-POC-RETEST` (separate; not clubbed)
  - Catalog: `MIX_CATALOG.md` §14
  - Proxy CLI: `python -m backtest_engine --dry-run --years 2 cf-umar-forest`
  - Backtest: [`BACKTEST_CF_UMAR_FOREST_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_CF_UMAR_FOREST_2026-09-06.md) — honest, **no promote**
  - 02/03/09: [`CF_UMAR_FOREST_MATH_NOTES.md`](../../02_phd_math/docs/CF_UMAR_FOREST_MATH_NOTES.md), [`CF_UMAR_FOREST_MARKET_NOTES.md`](../../03_phd_market/docs/CF_UMAR_FOREST_MARKET_NOTES.md), [`CF_UMAR_FOREST_REVIEW_NOTES.md`](../../09_review/docs/CF_UMAR_FOREST_REVIEW_NOTES.md)
  - Log: [`PHASE3E_ASR_LOG.md`](../../01_research/docs/chart_fanatics/PHASE3E_ASR_LOG.md)
- Phase-3F ASR + **Phase-8 DONE** (Carmine Rosato / Jadecap):
  - `UhkRRqO1gQM` · guest **Carmine Rosato** · BIND [`UhkRRqO1gQM_BIND.md`](../../01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md)
  - `8OX-mcSHWhg` · guest **Jadecap** · BIND [`8OX-mcSHWhg_BIND.md`](../../01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md)
  - MIX: `MIX-CF-CARMINE-ABSORB` (DI/OF PARKED) + `MIX-CF-CARMINE-FAIL-BREAK` + `MIX-CF-CARMINE-OPEN-HOLD` + `MIX-CF-JADECAP-SWING-FAIL` + `MIX-CF-JADECAP-SESSION-LIQ` (DI) + `MIX-CF-JADECAP-FVG-DRAW` (separate; not clubbed)
  - Catalog: `MIX_CATALOG.md` §15
  - Proxy CLI: `python -m backtest_engine --dry-run --years 2 cf-carmine-jadecap`
  - Backtest: [`BACKTEST_CF_CARMINE_JADECAP_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_CF_CARMINE_JADECAP_2026-09-06.md) — honest, **no promote**
  - 02/03/09: [`CF_CARMINE_JADECAP_MATH_NOTES.md`](../../02_phd_math/docs/CF_CARMINE_JADECAP_MATH_NOTES.md), [`CF_CARMINE_JADECAP_MARKET_NOTES.md`](../../03_phd_market/docs/CF_CARMINE_JADECAP_MARKET_NOTES.md), [`CF_CARMINE_JADECAP_REVIEW_NOTES.md`](../../09_review/docs/CF_CARMINE_JADECAP_REVIEW_NOTES.md)
  - Log: [`PHASE3F_ASR_LOG.md`](../../01_research/docs/chart_fanatics/PHASE3F_ASR_LOG.md)
- Phase-3G ASR + **Phase-9 DONE** (Usman Ashraf / Brando-Leaf):
  - `6Bdv-_YUQ0s` · guest **Usman Ashraf** (ASR 'Osman Astra' UNKNOWN) · BIND [`6Bdv-_YUQ0s_BIND.md`](../../01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md)
  - `yLuH8YZXORQ` · guest **Brando / Leaf** (Elite Options Trader; ASR 'brand-a-k-a-leaf') · BIND [`yLuH8YZXORQ_BIND.md`](../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md)
  - MIX: `MIX-CF-USMAN-OI-STRIKE` + `MIX-CF-USMAN-0DTE-GAMMA` + `MIX-CF-USMAN-WEEKLY-SIZE` + `MIX-CF-USMAN-PRICE-STOP` (DI) + `MIX-CF-BRANDO-HTF-RECLAIM` + `MIX-CF-BRANDO-ROUND-BREAK` + `MIX-CF-BRANDO-HTF-BOUNCE` + `MIX-CF-BRANDO-SIZE-ZERO` (DI) + `MIX-CF-BRANDO-NEWS-ALIGN` (DI) (separate; not clubbed)
  - Catalog: `MIX_CATALOG.md` §16
  - Proxy CLI: `python -m backtest_engine --dry-run --years 2 cf-usman-brando`
  - Backtest: [`BACKTEST_CF_USMAN_BRANDO_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_CF_USMAN_BRANDO_2026-09-06.md) — honest, **no promote**; title $6k→$10M = marketing
  - 02/03/09: [`CF_USMAN_BRANDO_MATH_NOTES.md`](../../02_phd_math/docs/CF_USMAN_BRANDO_MATH_NOTES.md), [`CF_USMAN_BRANDO_MARKET_NOTES.md`](../../03_phd_market/docs/CF_USMAN_BRANDO_MARKET_NOTES.md), [`CF_USMAN_BRANDO_REVIEW_NOTES.md`](../../09_review/docs/CF_USMAN_BRANDO_REVIEW_NOTES.md)
  - Log: [`PHASE3G_ASR_LOG.md`](../../01_research/docs/chart_fanatics/PHASE3G_ASR_LOG.md)
- Phase-3H ASR + **Phase-10 DONE** (Andrea Cimi / Omor-NBB):
  - `TvoQr6ObjnU` · guest **Andrea Cimi** (ASR Andrea Chimney; stub Fabio wrong — Fabio mentor only; **not** `MIX-CF-FABIO-*`) · BIND [`TvoQr6ObjnU_BIND.md`](../../01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md)
  - `IB-fyWI5j8w` · guest **Omor / NBB Trader** (ASR Omore aka MBB) · BIND [`IB-fyWI5j8w_BIND.md`](../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md)
  - MIX: `MIX-CF-ANDREA-FAIL-AUCTION` + `MIX-CF-ANDREA-ORB-ACCEPT` + `MIX-CF-ANDREA-STOP-FADE` + `MIX-CF-ANDREA-ABSORB` (OF PARKED) + `MIX-CF-OMOR-MMM-FRAME` + `MIX-CF-OMOR-OTE` + `MIX-CF-OMOR-PDH-REVERSAL` + `MIX-CF-OMOR-KZ-ADR` (DI) (separate; not clubbed)
  - Catalog: `MIX_CATALOG.md` §17
  - Proxy CLI: `python -m backtest_engine --dry-run --years 2 cf-andrea-omor`
  - Backtest: [`BACKTEST_CF_ANDREA_OMOR_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_CF_ANDREA_OMOR_2026-09-06.md) — honest, **no promote**
  - 02/03/09: [`CF_ANDREA_OMOR_MATH_NOTES.md`](../../02_phd_math/docs/CF_ANDREA_OMOR_MATH_NOTES.md), [`CF_ANDREA_OMOR_MARKET_NOTES.md`](../../03_phd_market/docs/CF_ANDREA_OMOR_MARKET_NOTES.md), [`CF_ANDREA_OMOR_REVIEW_NOTES.md`](../../09_review/docs/CF_ANDREA_OMOR_REVIEW_NOTES.md)
  - Log: [`PHASE3H_ASR_LOG.md`](../../01_research/docs/chart_fanatics/PHASE3H_ASR_LOG.md)
- Phase-3I ASR (**no MIX** this turn):
  - `hvyf6frvCcA` · guest **Trader Yush / Yush** · transcript **yes** (ASR) · [`hvyf6frvCcA_TRANSCRIPT.md`](../../01_research/docs/chart_fanatics/hvyf6frvCcA_TRANSCRIPT.md)
  - `T_djSNBmV00` · guest **Marco** (return; prior `DAnXM7C16h0`) · transcript **yes** (ASR) · [`T_djSNBmV00_TRANSCRIPT.md`](../../01_research/docs/chart_fanatics/T_djSNBmV00_TRANSCRIPT.md)
  - Log: [`PHASE3I_ASR_LOG.md`](../../01_research/docs/chart_fanatics/PHASE3I_ASR_LOG.md)
  - **Next:** **Phase-11 bind** for Yush and/or Marco return when asked (do **not** auto-club into existing `MIX-CF-MARCO-*` without review)
- **Remaining:** fail=30 still need ASR/caption later. Captions still 429 on this host. Do **not** deep-analyze the fail queue.
- Do **not** merge CF mixes into `MIX-DEFAULT-BUY` / STRAT-001–014 / IQCapital rows / Fabio. No STRAT-015+.

### Left off 2026-09-06 (SL/TP coalition)

1. Fetched @iqcapital_io videos + transcripts (see harvest doc).  
2. Named MIX exits + own `MIX-DESK-IQ-ATR-RR2`.  
3. Replaced silent STOP_PTS default with ATR method / DATA_INSUFFICIENT.  
4. NIFTY INDEX 3m SL/TP backtest **FAIL**.  
5. Next blockers: NIFTY GEX source (or keep PARKED); OPTIDX premium% path; FUTIDX continuous; do not promote.
6. **CF Phase-10 DONE** (Andrea/Omor). **Phase-3I ASR DONE** (Yush + Marco return; yes=17/fail=30). **Next CF:** (a) **`RETRY_TOMORROW.md`** ASR the **30** fails; (b) **Phase-11 bind** Yush + Marco return when asked.

Rate limits: `packages/dhan-client/docs/RATE_LIMITS.md`

### Agent RAG / EOD recon

**Last EOD stub:** 2026-09-06 (`python -m agent_rag eod-recon`)
- session_kind: `UNKNOWN` (score_track=`ANALOG_MEMORY`)
- RETUNE_PROPOSAL: **`BACKTEST_REQUIRED`** (no auto-retune; `keep_current_strategy: true`)
- recon: `data/recon/EOD_RECON_2026-09-06.json`
- KB: `data/knowledge/agent_rag.sqlite` ([`AGENT_RAG.md`](../../01_research/docs/AGENT_RAG.md)) — does **not** touch `transcripts.sqlite`
- Paper agents backtest rollup: [`BACKTEST_PAPER_AGENTS_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_PAPER_AGENTS_2026-09-06.md) — **NO_PROMOTE**

## Do not

- Invent win rates or code live strategies  
- Auto-retune after nightly  
- Show MACD/RSI on the **customer** desk  
- Treat Docs Auditor PASS as a product gate  
- Promote ATR FAIL books or paste wr into confidence UI

---

## External org structure — TradingAgents adoption (2026-09-06)

**Status:** `ADOPTED_SKELETON` / **DEEPENED_PAPER** / **MARKET_HOURS_LOOP** / **UNVALIDATED** / paper only  
**EXTERNAL:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0)  
**Clone:** `research/TradingAgents/` (gitignored nested tree; re-clone if missing)  
**Study notes:** [`ADOPT_TRADINGAGENTS.md`](ADOPT_TRADINGAGENTS.md)  
**Market-hours plan:** [`PLAN_MARKET_HOURS_PAPER_AGENTS.md`](PLAN_MARKET_HOURS_PAPER_AGENTS.md)  
**Astra review (gpt-6-astra + gpt-4o, paper-today):** [`open_ai_astra_review.md`](open_ai_astra_review.md) · runbook [`PAPER_MARKET_HOURS_RUNBOOK.md`](PAPER_MARKET_HOURS_RUNBOOK.md)  
**Customer `/` dashboard UX (Astra `APPROVE_WITH_GUARDRAILS`):** [`../../07_coding/docs/ASTRA_DASHBOARD_REVIEW.md`](../../07_coding/docs/ASTRA_DASHBOARD_REVIEW.md) — ticket + index chart + confidence (i) + paper book; `lightweight-charts` installed once under `apps/web` (do **not** restart npm until asked; `npm run build` verified)  
**Market-hours council:** [`OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md`](OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md) (`gpt-5.4` + desk; `APPROVE_WITH_GUARDRAILS`)  
**Design council (TradingAgents deepen):** [`OPENAI_DESIGN_COUNCIL_2026-09-06.md`](OPENAI_DESIGN_COUNCIL_2026-09-06.md) (`gpt-5.4` + desk; `APPROVE_WITH_GUARDRAILS`)  
**Package:** `packages/trading_agents_india` — personas + chain watcher + handoffs + IST poll loop + `mode=PAPER|LIVE` (LIVE refuses); market-hours soft-defaults LLM when key + desk/news; `--live-chain` opt-in; bounded `agent_rag` in LLM prompts  
**KB:** `data/knowledge/trading_agents_india.sqlite` (separate from `transcripts.sqlite`)  
**Ledger:** `data/recon/paper_watch/MIX-TA-*/` + `MIX-DEFAULT-BUY/`  
**MIX paper-watch (not default):** `MIX-TA-FLOW-RISK`, `MIX-TA-EVENT-HOLD`, `MIX-TA-EXEC-SANITY`, `MIX-TA-MARKET-HOURS` — MIX_CATALOG §18  
**09 notes:** [`TRADINGAGENTS_ADOPTION_REVIEW_2026-09-06.md`](../../09_review/docs/TRADINGAGENTS_ADOPTION_REVIEW_2026-09-06.md), [`TRADINGAGENTS_DEEPEN_NOTES_2026-09-06.md`](../../09_review/docs/TRADINGAGENTS_DEEPEN_NOTES_2026-09-06.md)

**Run:**
```bash
pip install -e packages/trading_agents_india
python -m trading_agents_india session --dry-run
python -m trading_agents_india market-hours --simulate --max-ticks 2
python -m trading_agents_india market-hours --simulate --no-llm --max-ticks 1
python -m trading_agents_india market-hours --tick-seconds 45 --max-ticks 4 --stop-outside-shell
python -m trading_agents_india market-hours --live-chain --max-ticks 2   # data only
python -m trading_agents_india clock
python -m trading_agents_india session --mode PAPER --gather-news
python -m trading_agents_india session --mode LIVE          # always refuses
python -m trading_agents_india session --dry-run --use-llm  # session: LLM opt-in
python -m trading_agents_india personas
python -m agent_rag eod-recon --offline
```

### Still open (market-hours paper) — **empty**

Prior three “still open” items from the 2026-09-06 summary are **closed this phase**:

| Item | Close |
|------|--------|
| Continuous sub-second Dhan depth alpha | **PARKED / DATA_INSUFFICIENT** — `hooks/depth.py` DI-only; no alpha until decode+history |
| `/desk` UI wire | **CLOSED this phase** — use CLI `market-hours`; mock seed `apps/web/public/mock/paper_agents.json` |
| Promote / research-ready | **NO_PROMOTE** — reopen only after 06 OOS+`NORMAL` + 09 five-pass **passes** |

### Future backlog (not “still open”)

| ID | Item | When |
|----|------|------|
| **UI-DESK-PAPER-AGENTS** | Wire `/desk` persona board / blotter to paper ledger or `paper_agents.json` | Founder asks; no npm restart until asked |
| DEPTH-DECODE-VALIDATION | 02/03 prove WS quote/full/depth offsets + history replay | Before un-parking depth |
| IST-LIVE-DATA-PAPER | Run `market-hours` (not `--simulate`) with `DHAN_*` data-only | Next IST session when asked |
| CF-RETRY-30 + Phase-11 | Chart Fanatics fail=30 ASR; bind Yush + Marco return | Research track (see above) |

### Astra paper-today ship (2026-09-06)

- Review: [`open_ai_astra_review.md`](open_ai_astra_review.md) (root pointer `open_ai_astra_review.md`)
- Runbook: [`PAPER_MARKET_HOURS_RUNBOOK.md`](PAPER_MARKET_HOURS_RUNBOOK.md)
- Implemented: market-hours soft-default LLM + desk/news; `--no-llm`; Astra token floor; bounded RAG prompts; clock weekend/09:00 tests; EOD cron docs; live-chain stays opt-in
- Verdict: **ReadyIsolatedResearch** / supervised CLI paper — **not** promote, **not** live orders

**Still DI / gated (standing):** Dhan news API absent in client; Moneycontrol RSS VERIFY IF STABLE; India sentiment feed; EVENT_MEMORY analogs empty; live OI wall parser; OPTIDX dual CE/PE; LIVE founder allow + `TRADING_AGENTS_LIVE_GATE` default off; no live orders. KEEP_ALL unchanged. Not `RESEARCH_READY_FOR_PROGRAMMING`.

Prior blocker `NEED_GITHUB_URL` is **cleared** by this URL. Do not mass-rewrite `teams/` — additive package only.

---

## External org structure (blocked) — SUPERSEDED

~~**Status:** `NEED_GITHUB_URL`~~ → see **TradingAgents adoption** above.
