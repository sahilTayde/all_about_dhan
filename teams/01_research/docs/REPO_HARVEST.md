# GitHub repo harvest: what helps a NIFTY/SENSEX index-options desk (paper only)

**Date:** 2026-11-13. **Who:** Opus lead (harvest and implementation), Sonnet readers (READMEs), Fable (strategy judgment and ranking).
**How:** read-only `gh api` (README, file tree, at most 2 key files per repo). Nothing was cloned, run or installed, and no instruction inside a repo was followed. Licences come from the GitHub SPDX field, and from the LICENSE file text where that field said NOASSERTION.
**Layer:** SOURCE_FACT (what a repo says) is kept apart from VALIDATION (what we checked). No repo's numbers have been reproduced by us.

**Now.** No repo has a proven, cost-honest intraday edge in Indian index options. Three independent repos reached our own null by different routes:
- **mahav235-svg/nifty-options-lab:** 359 pre-registered variants; weekly short vol nets about 0 (walk-forward t -0.09, PBO 0.54).
- **sahilempire/nifty-options-research-lab:** 40+ strategies, all negative after costs.
- **JATINDHURVE/nifty-options-research:** volatility is predictable, direction is not, so the same D2 result as ours.

What the harvest does give us:
- better tools for not fooling ourselves (built in this PR);
- one untested event strategy (frozen as E40);
- one low-prior structure (frozen as E41);
- a data-hygiene list the 5-year E39 test needs before it can be trusted.

**Why.** Costs and theta still dominate (D2, D4). Every gain on offer is in how we measure, not in a new signal.

**Next.** Before E39 is scored:
1. ~~Build the 5-year cost hygiene (adoption #2 below).~~ Done, see §5.
2. Run `honest_stats.lookahead_scan` on every E39-E41 feature function.

## 1. What we have / what we lack (our own terms, written before any search, i.e. before this PR)

**What we have**
- **Data.** Dhan expired weekly options, 1m bars, ATM±3, 2025-10-27..2026-10-23 (one year; D1). E39 found that index weeklies are now served to ATM±10 in 2-day calls, and a 5-year pull at ATM±10 has been launched (phase A our year ±4..10, phase B 2021-10..2025-10). There is also a live recorder tape (1 s quotes + 5-level depth, moving ATM±4/±5 ladder), but it was down 10-30..11-12 (token). And there are 5y index 1m bars, NSE/BSE bhavcopy, participant OI and FRED.
- **Engines.** `opt1y_lab.trade` (legacy; exits at the first data gap, which flatters long holds, D7); `sell_lab.struct` multi-leg with **cons/opt bounds** for legs that leave the window, spot exits, trail, lots; `sweep_lab` (247k-variant grid on `struct` cons, known-answer vs the older labs); `playbook_lab` (E32-E36 per-slot state x action tables with a scramble-the-future look-ahead test, `selftest33`); `exec_lab` / `depth_lab` (execution and order-book tape); `casino_lab` (book, exits, DIST, promotion).
- **Honest selection kit.** Rules are **frozen** before results (freeze notes). Monthly **walk-forward**, day-block bootstrap p, random-entry **placebo** (p_vs_rand), **Hansen SPA** (per family and global), a **deflated Sharpe** helper (`sweep_lab.dsr_family`), Bonferroni per round, empirical-Bayes shrunk EV per (state, action) cell, quarter Kelly on a 50%-shrunk mean, block-bootstrap ruin.
- **Paper DESK.** `fin1_shadow.decide` runs each sym-day at 09:46: data health → kill switch → daily 2L / weekly 4L stop → SGATE → B1, with one short-gamma per index, max 2 open and a hard flatten at -L. **Promotion ladder** 0/1/2/5/10 lots is tested only at **40/80/120 forward trades**: RETIRED if the shrunk mean ≤ 0 at 80, demoted on a rolling-30 mean < 0 or a drawdown > 1.5x dev. The **forward tape** logs B1, SC1, IVS and the E33 cells, all rung 0 (log only).
- **Production side.** `risk-engine` is a deterministic fail-closed veto (mode, kill switch, recon, time gate, duplicate, max lots/positions, per-trade and daily loss, 15-min cooldown). Next to it: `brokers` (paper broker with super order / OCO / trailing; Dhan mapper, not wired), `ledger` (append-only), `data-recorder`, and `claude_daily.sh` (morning/close/heal/report/token).

**What we lack**
1. **Any edge.** E1-E37, B1-B10 and E31's 247k variants (global SPA p 0.93) are all null after costs. D2: volatility is predictable but option P&L is not. D4: a random ATM buy costs Rs 1.0-1.3k per trade.
2. **An untouched holdout.** Every rule since E30 runs on a seen-again year. E38 (vendor full chain) and E39 (5y Dhan) are the first real learn ≠ test designs, and both wait on data.
3. **Wings and long holds.** These are undecidable under D1 (cons/opt bounds dominate: FIN1, E5b credit spread, E19 overnight, condors). ATM±10 lifts this only for index weeklies.
4. **Over-fitting diagnostics beyond SPA.** We have no PBO (probability that the in-sample best is below the OOS median), no step-down test that names WHICH variants are real (Romano-Wolf StepM / model confidence set), and no combinatorial purged CV that gives many OOS paths from 5 years.
5. **A reusable look-ahead guard.** Two E33 bugs (5m bar closing after the slot, `s[i-60]` wrap) were caught late by another session. The scramble test exists for E33 only.
6. **A DESK explanation layer.** `decide` returns the first failing reason only. There is no full pre-trade checklist (each gate PASS/BLOCK) or trade journal that the founder can read per decision.
7. **Forward volume.** SGATE trades about 50 times a year, so its first 40-trade checkpoint is about 10 months of recorder uptime away.
8. **Meta-labelling on a primary signal with costs in the label.** E8 already tried it in substance for S1 (AUC 0.445 holdout); it has not been tried for B1. Too few trades (90 dev) until E39 data arrives.

## 2. Repos read (31): what each is, how it works, licence, last push, what transfers

Stars and pushes are as of 2026-11-13. "Transfer" is our judgment for NIFTY/SENSEX weekly CE/PE buy and sell, costs dominating, 1m data, ATM±3 (±10 coming).

### Claude / agent skills for trading

**Jakeschincariol/day-trader-skill** (founder's example). MIT, 2026-10-20, 7.5k★.
- What it is: 11 Claude skills for US day trading, all stdlib Python.
- How it works: the skills pass JSON files along one pipeline: scanner → news → entry → exit → timemachine → budget → risk → broker.
  - **Time Machine:** replays the rest of the day 10,000 times from same-time-of-day 5m bars, plus the real record of the same rule on past sessions.
  - **Risk:** PASS/BLOCK per check; exits are never blocked.
  - **Broker:** a yes for each exact ticket.
- Transfer:
  - the full PASS/BLOCK checklist, **adopted (#4)**;
  - the "exits never blocked" rule, which our risk-engine already has;
  - the Time Machine is covered by our E26 DIST and placebos.

**jackson-kanchanapally/day-trader-skill-codex.** MIT, 2026-11-12, 17★.
- What it is: an NSE/BSE equities port of the above.
- How it works: sealed per-agent reviews over a hash-bound frozen data snapshot; fail closed on years with no data; Indian charges, with 10 bp spread and 5 bp slippage.
- Transfer: hash the freeze notes (#10). Nothing for options.

**sanT-0/nse-day-trader-skills.** MIT, 2026-11-02, 4★.
- What it is: NSE long-only skills with a manual broker ticket.
- How it works: the risk gate must PASS before a ticket; India VIX and trend checks.
- Transfer: nothing new.

**augusten6383/DayTraderSkill-INDIAN.** MIT, 2026-10-25, 3★.
- What it is: Angel One ORB plus Monte Carlo.
- How it works: its lot sizes are stale (NIFTY 25), and it publishes no backtest.
- Transfer: none (hype-adjacent).

**dhan-oss/dhanhq-skills.** MIT, 2026-06-30.
- What it is: Dhan's official agent skill (SDK wrappers, references).
- How it works: its PCR, OI-wall and max-pain snippets are folklore.
- Transfer: already used in E39 (ATM±10, 2-day calls). Its OI ideas are already tested (E16, E22).

**marketcalls/openalgo.** AGPL-3.0, 2026-11-13, 3k★.
- What it is: a self-hosted broker abstraction (38 brokers including Dhan), with a strategy host and an Analyzer (sandbox) mode.
- Transfer: design reference only, no code (AGPL). It matches our `brokers` package. Its hardening checklist is useful for the shadow-mode adapter test.

**TauricResearch/TradingAgents.** Apache-2.0, 2026-11-04, 122k★.
- What it is: LLM analysts, then a bull/bear debate, then a trader, a risk team and a portfolio manager.
- How it works: there is no out-of-sample P&L, and its changelog is mostly look-ahead fixes.
- Transfer: at most an advisory bull/bear critic. The LLM stays advisory by house rule.

**virattt/ai-hedge-fund** (MIT, 65k★), **AI4Finance-Foundation/FinRL** (MIT), **FinGPT** (MIT), **microsoft/qlib** (MIT).
- How they work: persona agents; RL on prices; financial LLMs; an ML platform.
- No honest out-of-sample evidence was found in any of them.
- Transfer: qlib's separation of layers (dataset/handler, model, strategy, executor, analysis) is terminology only.

### Indian index-options research and strategies

**mahav235-svg/nifty-options-lab.** MIT, 2026-10-27.
- How it works: 359 pre-registered variants on bhavcopy plus Upstox 1m data, with walk-forward, DSR, PBO and bootstrap.
- Its results:
  - weekly short vol held to expiry nets about 0;
  - the overnight straddle is positive gross and negative net;
  - **pre-RBI iron fly from the T-2 close to the T-1 close:** 52 events, +956 per event, t 2.32, placebo-difference t 2.75, replicates on BANKNIFTY (t 3.0), not around FOMC, DSR 0.25 (fail).
- Its hygiene rules: no fills on untraded rows, a holiday-expiry map, date-versioned STT, lot-size history.
- Transfer: **E40 (frozen)**, and **hygiene #2**.

**sahilempire/nifty-options-research-lab.** MIT, 2026-09-06.
- Its results: 40+ strategies, all negative. It says about 94% of the loss is brokerage, and a 72%-win configuration still lost.
- Transfer: an independent check of our null, and a cost-model comparison.

**JATINDHURVE/nifty-options-research.** NOASSERTION, 2026-08-05.
- Its results: 15 years of Breeze data; direction ACF < 0.03; squared-return ACF 0.12-0.44; implied above realised on 80.7% of days.
- Transfer: confirms D2. Its decay-by-DTE cost table is a useful framing.

**aprameyap/nifty-0dte-vrp.** No licence, 2026-07-07.
- How it works: a model of remaining realised variance on expiry days; out-of-sample R² 0.39.
- Transfer: rejected, because it is covered by E6, E18 and E28 (volatility is predictable, P&L is not). No licence, so ideas only.

**codewithpom/nifty-straddle-vix-router.** MIT, 2026-07-12.
- How it works: a grid over entry time × SL, routed by VIX. In-sample Sharpe 4.58, and the repo itself calls that an artefact.
- Transfer: a cautionary case. Covered by E31's IV-rank gates.

**kunalrbhatia/ratio-spread-expiryday-strategy.** MIT, 2026-11-03.
- How it works: on expiry day at 09:20, buy ATM CE+PE and sell 3x the strikes priced at about one third of the ATM premium; legs under Rs 5 are left to expire. It publishes no evidence.
- Transfer: **E41 (frozen, prior null)**.

**marketcalls/openfly.** MIT, 2026-09-12.
- How it works: a short straddle driven by a "fly connectome" readout, with no edge shown. Its control set is what matters: a fixed 09:20 straddle, a random entry with the same count, shuffled labels, and flat.
- Transfer: the shuffled-label control (#9). We already have the random-entry control.

### Data and broker access

**jugaad-py/jugaad-data.** Licence file "YOLO" (unclear), 2026-11-11, 595★.
- What it is: NSE bhavcopy (EOD, F&O including UDiFF), index history, RBI rates.
- Transfer: we already cache bhavcopy (`ext_fetch.py`). Ideas only.

**Broker SDKs:**
- dhan-oss/DhanHQ-py (MIT), zerodha/pykiteconnect (MIT), upstox/upstox-python (MIT): official SDKs.
- Shoonya-Dev/ShoonyaApi-py: no licence, last push 2024.
- FyersDev sample code: no licence.

Transfer: none needed. We already have `dhan-client` and `brokers`.

### Quant research frameworks and statistics

**bashtage/arch.** NCSA-style permissive, 2026-11-12.
- What it has: SPA, **StepM**, **MCS**, GARCH/HAR.
- Transfer: StepM re-implemented, **adopted (#7)**. MCS is later.

**eslazarev/purged-cross-validation.** MIT, 2026-11-13.
- What it has: purge, embargo, CPCV, PBO, PSR/DSR, `effective_n_trials`.
- Transfer: **effective N (#6)** and **PBO (#3)**, both re-implemented. CPCV is #8, later.

**esvhd/pypbo.** AGPL-3.0, 2026-07-06.
- What it has: PBO via CSCV, PSR/DSR, minimum track-record length.
- Transfer: the algorithm only, re-implemented from Bailey et al. 2014.

**hudson-and-thames/mlfinlab.** Proprietary ("all rights reserved"), 2023-10. Also **meta-labeling** (no licence).
- What it has: triple barrier, meta-labelling, uniqueness weights, sequential bootstrap.
- Transfer: concepts only. Meta-labelling S1 was in substance E8, which failed.

**freqtrade/freqtrade.** GPL-3.0, 2026-11-12, 57k★.
- What it has: **lookahead-analysis** (re-run on truncated data and compare), **recursive-analysis** (warm-up stability), and protections (cooldown, stoploss guard, max drawdown).
- Transfer: the idea of **#1**, re-implemented, no code. The protections already sit in our risk-engine and DESK.

**polakowo/vectorbt.** Apache-2.0 with Commons Clause, 2026-11-11.
- What it is: vectorised parameter sweeps.
- Transfer: nothing; `sweep_lab` already does this.

**Engines:**
- nautechsystems/nautilus_trader (LGPL-3.0): an event-driven engine with backtest/live parity and fill models.
- QuantConnect/Lean (Apache-2.0): the Alpha → Insight → Portfolio → Risk → Execution chain, with India equity templates.
- mementum/backtrader (GPL-3.0, last push 2024-08), stefan-jansen/zipline-reloaded (Apache-2.0), pmorissette/bt (MIT), kernc/backtesting.py (AGPL-3.0).

Transfer: Lean's layer names (#12). No engine swap: we have engines and no edge.

**Analytics:**
- ranaroussi/quantstats (Apache-2.0): outlier win ratio, ulcer index, gain-to-pain, PSR, smart Sharpe.
- stefan-jansen/pyfolio-reloaded (Apache-2.0): stability, top drawdowns.

Transfer: #11 for the ladder, later.

**Option pricing:**
- vollib/py_vollib (MIT): Black, greeks, a robust IV solver.
- lballabio/QuantLib (BSD-style): SVI, calendars.

Transfer: none yet. Our Black-76 IV is enough at ATM±10.

**Portfolio optimisation:** dcajasn/Riskfolio-Lib (BSD-3), skfolio (BSD-3). Not relevant to a 1-2 stream desk.

**stefan-jansen/machine-learning-for-trading.** MIT. A book companion; nothing on options or intraday.

## 3. Ranked adoption table (Fable ranking, Opus checks)

Tags: (a) method, (b) strategy not yet in the registry, (c) terminology/structure, (d) infrastructure.

**Test-plan words:**
- **frozen rule:** written into the registry before any result.
- **cons engine:** `sell_lab.struct` cons.
- **WF/SPA:** walk-forward with Hansen SPA.
- **forward tape:** the DESK log.

**Effort:** S < 1 day, M 1-3 days.

| # | Repo / idea | Licence | Tag | What to adopt | Why it helps us | Effort | Risk | Test plan | Status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | freqtrade lookahead-analysis | GPL-3.0 (idea only) | a/d | `honest_stats.lookahead` / `lookahead_scan`: scramble everything after the decision index; features must not change | The two E33 bugs (a 5m bar closing 4 min after the slot; the `s[i-60]` wrap) were found late, and the scramble test covered E33 only | S | Slow on big grids, so sample the slots | Known answers: the wrap leaks at exactly slots 0..59 of a 300-point series; a trailing mean is clean; a centred mean leaks at 299/300; a whole-day max, the next bar and an open 5m bar are caught. Run on every E39-E41 feature function before scoring | **built** |
| 2 | nifty-options-lab hygiene | MIT | d | Date-versioned STT and charges, lot-size history, a holiday-expiry map, and no fill on an untraded bar | E39 runs 2021-2025 at today's lot sizes and STT (disclosed). STT on option sales went 0.05 → 0.0625 → 0.1 → 0.15%, and the NIFTY lot changed five times. Without this, the 5-year P&L is wrong | M | Wrong tables fail silently | Known answers at every cutover (`sell_lab.py OUT costs`, §5) | **built** (`COSTS=dated`, stale guard) |
| 3 | PBO via CSCV (Bailey et al.; purgedcv / pypbo idea) | MIT / AGPL (re-implemented) | a | `honest_stats.pbo_cscv` | SPA asks whether ANY variant is real. PBO asks how often the in-sample best lands below the out-of-sample median. We lacked it | S | Needs a days × variants matrix (sweep_lab has X) | Known answers: A/B flip → 1.0; a constant +1 edge → 0.0; iid noise 0.37 (band 0.3-0.7); regime-flip grid 0.93. Then on the E31 matrix and on E39 | **built** |
| 4 | day-trader-skill trader-risk | MIT | c/d | Every DESK gate PASS/BLOCK in `decide()["checks"]`, printed as a `checklist:` line | The founder sees why a trade was taken or blocked at every gate, not only the first reason | S | None (actions unchanged) | Parity: TRADE iff no BLOCK, and the first BLOCK equals `why` over 7 state cases; `casino_lab desk` (13 cases) still passes | **built** |
| 5 | Pre-RBI short vol, T-2 close → T-1 close | MIT (source) | b | Registry **E40**: naked straddle and iron fly (wings min(3 EM, 10 strikes)) | The only harvested rule with a placebo and a replication. Not B9 (after the release), R3 (long on the day), E19 (no event), E32 (intraday) or E13 | M | Overnight gaps; ~30 events in 5y; wings may leave ATM±10 | Frozen rule (E40), cons engine at ATM±10, learn 2021-25 / test our year once, placebo on non-event nights, PBO + DSR beside it, then the forward tape at rung 0 | **frozen, waits on E39 data** |
| 6 | purgedcv `effective_n_trials` | MIT (re-implemented) | a | `honest_stats.effective_n` (participation ratio of the correlation eigenvalues) | E31's 247k variants are near-duplicates, and a raw-N deflated Sharpe over-deflates | S | Estimator choice | Known answers: 20 identical → 1, independent → 20, two identical blocks → 2. Feed it as N to `sweep_lab.dsr_family` | **built** |
| 7 | arch StepM (Romano-Wolf) | NCSA (re-implemented) | a | `honest_stats.stepm` | Names WHICH variants are real, with family-wise error controlled. Not useful while SPA p is 0.93; needed for E39's 10 cells | S | None | Known answer: 200 noise + 3 planted → exactly the 3; pure noise → none | **built** |
| 8 | Combinatorial purged CV | MIT | a | CPCV paths on the 5-year learn window | Many out-of-sample paths instead of one walk-forward | M | Purge/embargo mistakes | E39 learn window only; known-answer on a planted-signal panel | later |
| 9 | openfly controls | MIT | a | A shuffled-label control for gated rules | Random entry exists; shuffling gate labels (as in E34) should be standard | S | None | Add to the E39 report | later (E34 already did it once) |
| 10 | day-trader-skill-codex frozen snapshot | MIT | c/d | A sha256 of the freeze note and the data manifest, recorded in the registry row | Freezes become tamper-evident | S | None | The hash is printed by the study run | later |
| 11 | quantstats metrics | Apache-2.0 | a | Outlier win ratio, ulcer index, gain-to-pain in `casino_lab.promote` reporting | Flags streams carried by one day (B1 holdout is Oct-only) | S | None | Hand-computed toy series | later |
| 12 | Lean framework terms | Apache-2.0 | c | Alpha (signal) → Insight (direction, size, horizon, confidence) → Portfolio → Risk → Execution | Clear names for the analyst → boss → desk → risk-engine chain | S | Renaming churn | Docs only | later |
| 13 | Next-weekly expiry pull | own | d | Pull expiryCode 2 at ATM±10 | Unlocks calendars and E40 when T-1 is an expiry day | M | Pull time | After E39 phase B | later |
| 14 | freqtrade recursive-analysis | GPL (idea only) | a | Warm-up stability: features must not depend on the start date | Catches EMA/ADX start bias | S | Minor | Same harness as #1 | later |
| 15 | Expiry 1x3 ratio spread | MIT (source) | b | Registry **E41** | Not E30/E37/E31/E4/IVS. A low prior: 8 legs ≈ Rs 3-4k entry cost, naked tails | M | Naked tails break the one-short-gamma rule | Frozen rule (E41), cons engine at ATM±10, learn/test as E39, random-minute placebo | **frozen, prior null** |

### Rejected (and why)

- **Remaining-variance / vol-forecast models** (nifty-0dte-vrp, VIX routers): covered by E6, E18 and E28. Volatility is predictable, but option P&L is not (D2).
- **Weekly short vol held to expiry** and the **overnight short straddle**: the source's own results net about 0 or negative; the overnight straddle is E19.
- **LLM debate desks** (TradingAgents, ai-hedge-fund, FinGPT, FinRL): no out-of-sample evidence. The LLM is advisory only by house rule.
- **Meta-labelling / triple barrier:** mlfinlab is now proprietary, and E8 already failed (holdout AUC 0.445). Revisit for B1 only on the E39 5-year data.
- **Time Machine bootstrap:** covered by the day-block bootstrap, placebos and E26 DIST.
- **New engines** (Lean, nautilus, zipline, backtrader, vectorbt, qlib) and portfolio optimisers: no edge to execute.
- **Licence traps** (ideas only, never code): AGPL (openalgo, pypbo, backtesting.py); GPL (freqtrade, backtrader); Commons Clause (vectorbt); proprietary (mlfinlab); no licence (jugaad-data "YOLO", Shoonya, nifty-0dte-vrp, meta-labeling).

## 4. Built in this PR (each with a known-answer check)

- `scripts/lab5y/honest_stats.py`: `pbo_cscv`, `effective_n`, `stepm`, `lookahead`, `lookahead_scan`. numpy only, no data needed. Check: `python scripts/lab5y/honest_stats.py`.
- `scripts/lab5y/fin1_shadow.py`: `decide()` returns `checks` (PASS/BLOCK per gate), printed in `forward`. Checks: `fin1_shadow.py selftest` (parity) and `casino_lab.py OUT desk` (unchanged 13 cases).
- Registry: **E40** and **E41** pre-registered (frozen before any result), plus a 2026-11-13 infrastructure note with the rule that every E39-E41 score prints PBO and an effective-N DSR, and passes `lookahead_scan` first.

## 5. Five-year cost hygiene (adoption #2, built 2026-11-13)

**What changed.**
- **`COSTS=dated`:** charges at the rates of the trade day, and whole lots at the size of the contract's expiry. Default `today` is unchanged.
- **Untraded-bar guard:** a zero-volume bar is never filled on. `LAB_STALE=keep` reproduces the old behaviour.
- **Expiry days:** already data-driven in `opt1y_load --full`, so no change was needed.

**Sources** (public; numbers checked against at least two summaries where the circular itself could not be opened):
- **STT on sale of options:**
  - 0.05% → 0.0625% from 2023-04-01: Finance Act 2023 ([NSE circular FATAX56235](https://archives.nseindia.com/content/circulars/FATAX56235.pdf), [Upstox community](https://community.upstox.com/t/stt-on-sale-of-options-hiked-to-0-0625-6-250-on-a-turnover-of-1-crore/44)).
  - → 0.1% from 2024-10-01: Finance (No. 2) Act 2024 ([MSEI circular 16075](https://msei.in/SX-Content/Circulars/2024/October/Circular-16075.pdf), [StudyCafe](https://studycafe.in/budget-2024-securities-transaction-tax-rates-revised-check-new-rates-330491.html)).
  - → 0.15% from 2026-04-01: Budget 2026 ([ICICI Direct](https://www.icicidirect.com/ilearn/futures-and-options/articles/stt-changes-in-budget-2026-what-f-o-traders-should-know), [Groww](https://groww.in/blog/what-is-stt)).
- **NSE options transaction charge:**
  - 0.053% → 0.05% from 2023-04-01 ([Zerodha bulletin](https://zerodha.com/marketintel/bulletin/347967/revision-in-transaction-charges-and-stt-from-1st-april-2023), [NSE/FA/56129](https://nsearchives.nseindia.com/content/circulars/FA56129.pdf)).
  - → Rs 35.03 per lakh from 2024-10-01 ([Zerodha bulletin](https://zerodha.com/marketintel/bulletin/391488/revision-in-transactions-charges-from-1st-october-2024), [Fyers](https://fyers.in/notice-board/revision-of-brokerage-mtf-interest-and-other-charges-effective-october-1-2024.html)).
  - → Rs 3,552.99 per crore from 2026-03-01 ([NSE/FA/73061](https://nsearchives.nseindia.com/content/circulars/FA73061.pdf)).
  - Unclear point: one source gives 0.0495% (slab top) instead of 0.05% for 2023-24. The difference is 1% of a 0.05% charge, so it is immaterial.
- **BSE SENSEX options:** Rs 3,250 per crore from 2024-10-01 ([Angel One](https://www.angelone.in/news/market-updates/bse-updates-transaction-fees-for-sensex-bankex-options)). Before that it was slab-priced per member (Rs 500-3,750 per crore). We use the flat 3,250 throughout and mark it UNCLEAR; the effect is about Rs 2 per leg.
- **NIFTY lot:**
  - 75 → 50 from the Jul-2021 contracts ([NSE/FAOP/47854](https://archives.nseindia.com/content/circulars/FAOP47854.pdf)).
  - → 25 for contracts expiring after 2024-04-26 ([Fyers notice](https://fyers.in/notice-board/revision-in-lot-size-for-index-derivative-contracts-from-26th-april-2024/)).
  - → 75 from the 2024-12-26 weekly; the last old weekly was 2024-12-19 ([Zerodha bulletin](https://zerodha.com/marketintel/bulletin/393605/revision-in-lot-size-of-index-derivative-contracts-from-november-20-2024)).
  - → 65 from the 2026-01-06 weekly ([Zerodha bulletin](https://zerodha.com/marketintel/bulletin/429705/revision-in-lot-size-of-index-derivative-contracts-from-december-30-2025), [Kotak Neo](https://www.kotakneo.com/bulletins/lot-size-changes-in-index-derivatives-effective-december-30-2025/)).
- **SENSEX lot:** 10 → 20 from the 2025-01-10 weekly; the last old weekly was 2025-01-03 ([Fyers](https://fyers.in/notice-board/sebis-revised-lot-sizes-for-index-derivatives-effective-november-20-2024/), [Angel One](https://www.angelone.in/announcements/market/revision-in-market-lot-for-index-derivatives-contracts)).
- **Constant over the window:** stamp 0.003% of buy, SEBI Rs 10 per crore, GST 18%, Dhan brokerage Rs 20 per order.
- **Not modelled:** STT on exercise (0.125% of intrinsic), because every engine flattens at 15:15. E41's "let sub-Rs-5 shorts expire" rule must add it for ITM legs.

**Effect on the 5-year panel** (costs and counts only; no P&L was looked at, so the E39 LEARN years stay unseen). This is the 09:47 ATM straddle round trip, charges ×1.5 excluding spread, in Rs:

| sym | year | sym-days | refused (stale entry) | charges at today's rates | charges at the day's rates | units (dated) |
|---|---|---|---|---|---|---|
| NIFTY | 2021 | 45 | 0 | 603 | 489 | 650 |
| NIFTY | 2022 | 247 | 0 | 649 | 523 | 650 |
| NIFTY | 2023 | 245 | 0 | 483 | 404 | 650 |
| NIFTY | 2024 | 245 | 0 | 688 | 567 | 650 |
| NIFTY | 2025 | 247 | 0 | 639 | 546 | 675 |
| NIFTY | 2026 | 201 | 0 | 739 | 697 | 650 |
| SENSEX | 2023 | 154 | 18 | 485 | 354 | 200 |
| SENSEX | 2024 | 245 | 0 | 696 | 509 | 200 |
| SENSEX | 2025 | 247 | 0 | 650 | 539 | 200 |
| SENSEX | 2026 | 201 | 0 | 710 | 668 | 200 |

**Reading.**
- Today's rates are 10-27% dearer than the real 2021-24 charges. So the frozen `today` convention is cautious for sellers, and it slightly flatters nothing.
- The stale guard bites at SENSEX 2023 (the relaunch year) and in the wings (about 20% of ATM±10 bars), which is exactly where E38/E40 wings live.
- **E39-E41 amendment, made before any result and tightening only:** the guard is ON. The verdict uses `today` as frozen, and a PASS also needs the same sign under `dated`.
