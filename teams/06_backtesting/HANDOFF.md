# Handoff log — Team 06 Backtesting

## As of now (2026-09-16) — paper greeks/IV on tickets (NO_PROMOTE)

```text
From:     teams/06_backtesting + 04
To:       00 / founder
Date:     2026-09-16
Status:   PAPER OVERLAY / HYPOTHESIS / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Open/closed paper tickets stamp Dhan delta/gamma/theta/IV
  when parsed. Strike pick prefers |delta| 0.45–0.70 ITM-side else
  ITM_100. BACKTEST_REQUIRED vs ATM-only. Not a promote.
Rejected: Live orders. Claiming wr/PnL lift from greeks.
UNKNOWN: Session expectancy with greeks overlay.
```

## As of now (2026-09-16) — paper ITM_100 wing (NO_PROMOTE)

```text
From:     teams/06_backtesting + 04
To:       00 / founder
Date:     2026-09-16
Status:   PAPER ITM ENTRY / HYPOTHESIS / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Founder: stop getting stuck on ATM. Paper books now prefer
  ~100pt ITM (CE ATM-100 / PE ATM+100) using chain LTP, not invented
  prints. Dealer side still from INDEX vs ATM deltas. ATM fallback
  if ITM LTP missing. STRAT-006 wing, not a new STRAT.
Rejected: Live Super Order. MIX-DEFAULT-BUY production. Deep ITM.
UNKNOWN: ITM vs ATM expectancy this session (BACKTEST_REQUIRED).
```

## As of now (2026-09-16) — cancel stuck paper tickets (NO_PROMOTE)

```text
From:     teams/06_backtesting + desk_ml
To:       00 / 04 / founder
Date:     2026-09-16
Status:   PAPER EXIT FIX / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Founder: SENSEX 74300 CE under 258 still OPEN. Root: 1m last
  print + sit-until-TIME. Now cancel: minute low, 12% give-up,
  ATM strike roll, opposite BUY_*_CONFIRM, wall-clock TIME.
Rejected: Live Super Order. MIX-DEFAULT-BUY write.
UNKNOWN: Chain ATM LTP vs Dhan 74300 CE quote mismatch (~300 vs ~258).
```

## As of now (2026-09-16) — live IST session paper desk (NO_PROMOTE)

```text
From:     teams/06_backtesting + desk_ml
To:       00 / 04 / 07 / founder
Date:     2026-09-16
Status:   PAPER LIVE SESSION / UNVALIDATED / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: dual-tape --paper-scalp now walks TODAY IST ticks only
  (not full jsonl). ₹10k/book. OPEN kept (no REPLAY_END flatten).
  Dashboard: strike/limit/SL/CE|PE/status/WIN|LOSS/money lost/overall P/L.
  Mistakes → session paper_params only. MIX-DEFAULT-BUY not written.
Rejected: Live Super Orders. Promote from session wr. git-add sqlite.
UNKNOWN: How many aligned 1m triples exist for 2026-09-16 until close.
```

## As of now (2026-09-16) — paper-scalp closed premium board (NO_PROMOTE)

```text
From:     teams/06_backtesting + desk_ml
To:       00 / 04 / 07 / founder
Date:     2026-09-16
Status:   PAPER CACHE REPLAY / UNVALIDATED / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: 10-trade paper smoke: OPTIDX lots from instrument master
  (NIFTY 65 / BN 30 / SX 20). ₹10k/book. win_rate_pct. Tickets:
  strike/limit/target/stop/sl_hit/pnl_inr. deny_model_signals=false.
  Live dual-tape --paper-scalp --paper-train started (no Super Order).
Rejected: Live orders. MIX-DEFAULT-BUY production write. Promote from 10 trades.
UNKNOWN: Live dual-tape INDEX null if Dhan errors.
```

## As of now (2026-09-16) — ML replay-hold diagnostic (NO_PROMOTE)

```text
From:     teams/06_backtesting + desk_ml
To:       00 / 04 / founder
Date:     2026-09-16
Status:   HYPOTHESIS / CACHE REPLAY / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: replay-hold on NIFTY recon join (599 triples). HOLD vs 15m
  ATM straddle. Result inverted on this tape (HOLD then recovered).
  Tests 28 passed. MIX-DEFAULT-BUY not written.
Rejected: Promote. Win rate. Live orders.
UNKNOWN: BANKNIFTY/SENSEX replay; second session; flag PAPER_TRAIN_NO_DENY off.
```

## As of now (2026-09-15 ~10:45 IST) — TV-EP / STRAT / Okala paper loops (NO_PROMOTE)

```text
From:     teams/06_backtesting
To:       00 / 04 / 09 / founder
Date:     2026-09-15 ~10:45 IST
Status:   PAPER / UNVALIDATED / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Loop tv-ep-paper-tune KEEP_ALL MIX-TV-EP-001–025 + MIX-DEFAULT-BUY
  vs dual-tape; tv-ep-grid --cache; signal_lab on premium_tape days;
  backtest_engine books/project/scan as remaining STRAT/MIX paper eval.
Rejected: Promote; writing production_params; treating Okala grid as live.
UNKNOWN: okala-in CLI is _CF_GONE (DhanHQ-only reset). One-shot logs
  the removed banner; no Okala grid this session.
```

## As of now (2026-09-15 ~09:40 IST) — TV-EP + signal_lab paper (NO_PROMOTE)

```text
From:     teams/06_backtesting
To:       00 / 04 / 09 / founder
Date:     2026-09-15 ~09:40 IST
Status:   PAPER / UNVALIDATED / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: tv-ep-grid --cache --tf 1 3 5 15 --write → 912 cells
  WATCH 225 / TESTED_FAIL 412 / PARK 275. KEEP_ALL MIX-TV-EP.
  Paper-tune 001–025 + MIX-DEFAULT-BUY on dual-tape ticks
  (LTP-clone CE/PE; NOT same as OPTIDX OHLC). Most 0 trades.
  Fired MOCK tickets, 0 wins: 018, 010, 009, DEFAULT-BUY
  (paper_improved = less-negative in-sample tweak only).
  signal_lab 1/3/5/10m × gates × overlays on 2026-09-10/11
  premium_tape only; today ATM tape <40 bars = DI.
  ITM MIX-CHAMP-* leaderboard re-ran — lab cache WR, not
  today's paper fills.
Rejected: Promote TV Pine; treat ITM board % as live wr;
  write workspace.yaml / MIX-DEFAULT-BUY production knobs.
UNKNOWN: event_calendar empty; INDEX JSON last 2026-09-03
  vs premium 2026-09-15 SESSION_CLOCK mismatch on cache tuner.
Artifact: data/recon/tv_ep_paper_tune_dualtape_2026-09-15.json
  data/recon/tv_ep_leaderboard.json (gitignored)
Next: walk-forward 018/DEFAULT-BUY on a full same-day
  INDEX+OPTIDX OHLC session after cache refresh.
```

## As of now (2026-09-15) — paper overlay recode after OpenAI REJECT

```text
From:     teams/06_backtesting
To:       00 / 07 / 09 / founder
Date:     2026-09-15
Status:   PAPER OVERLAY / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Causal z; thin-tick HOLD; overlay CLI NIFTY/BANKNIFTY/SENSEX;
  dual-tape overlay_last.json; production_params_written false.
Rejected: Five-pass / RESEARCH_READY; live Super Order; promote.
UNKNOWN: Five-pass still unset. Paper overlay counsel ALIGNED ACCEPT_WITH_CAVEATS (gpt-4.1).
Artifact: teams/06_backtesting/docs/OPENAI_OVERLAY_REVIEW.md
```

## As of now (2026-09-15) — SESSION_PREP_ML dual-tape + desk_ml score

```text
From:     teams/06_backtesting (gate)
To:       00 / 04 / 05 / 07 / founder
Date:     2026-09-15
Status:   PAPER PREP / UNVALIDATED / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Warehouse+premium join; ML-001 embargo 5 (not CPCV);
  score --source dual-tape; FOLLOW-GAP HOLD at 09:15 IST.
  production_params_written false. ExecutionClient unused.
Rejected: Live Super Order; promote; STRAT-015+.
UNKNOWN: ATM depth at open; SENSEX OU mean-reversion.
Artifact: teams/06_backtesting/docs/SESSION_PREP_ML.md
CLI: python -m desk_ml score --underlying NIFTY --source dual-tape
```

## As of now (2026-09-15) — BOOK_MODEL_TUNE cache fit (NO_PROMOTE)

```text
From:     teams/06_backtesting (gate)
To:       00 / 04 / 07 / 09 / founder
Date:     2026-09-15
Status:   CACHE TUNE / UNVALIDATED / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: desk_ml book-tune on recon cache. NIFTY/SENSEX 599 triples
  2026-09-09..10. ML-001 seed 14 cluster counts. ML-002 MRR 40/60/90
  + FOLLOW-GAP. production_params_written false.
Rejected: Treating cluster/OU numbers as OOS+NORMAL promote; live Super Order.
UNKNOWN: ATM 1m for 2026-09-11..15 (three tape days only, not 15–21).
Artifact: teams/06_backtesting/docs/BOOK_MODEL_TUNE.md
CLI: python -m desk_ml book-tune --calendar-days 21
```

## As of now (2026-09-14) — QUANT_SELF_REVIEW_LOOP spec

```text
From:     teams/06_backtesting
To:       00 / 02 / 04 / 09
Date:     2026-09-14
Status:   SPEC / HYPOTHESIS / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Nightly/paper self-review of our own research emits
  RETUNE_PROPOSAL BACKTEST_REQUIRED only. production_params_written
  stays false. Live Super Order never requested from this loop.
  Aligns RETUNE_GATE + 02 book_kb topics (fit vs retune, overfitting).
Rejected: Auto-write MIX/workspace params; treating BACKTEST_REQUIRED
  as a completed backtest; live Dhan orders.
UNKNOWN: OOS+NORMAL beat of current spec (none).

Artifact: teams/06_backtesting/docs/QUANT_SELF_REVIEW_LOOP.md
```

## As of now (2026-09-14) — ML-001 fit is not a retune sample

```text
From:     teams/06_backtesting (gate)
To:       04 / 00 / 09
Date:     2026-09-14
Status:   REVIEW / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: desk-ml holiday fit printed NIFTY cluster sizes only.
Rejected: Treating cluster counts as OOS+NORMAL promote evidence.
```

## As of now (2026-09-14) — TV-EP paper session tuner (NO_PROMOTE)

```text
From:     teams/06_backtesting + 05 dual-tape
To:       00 / 04 / 09 / founder
Date:     2026-09-14
Status:   HYPOTHESIS / PAPER CLI / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Bounded paper tuner python -m backtest_engine tv-ep-paper-tune
  (alias trading_agents_india paper-tune). Shortlist MIX-TV-EP-005/010/016
  + MIX-DEFAULT-BUY paper proxy. One MIX at a time, ≤3 param tweaks, next-
  premium score, mistake_notes, RETUNE_PROPOSAL BACKTEST_REQUIRED + local
  data/recon/tv_ep_paper_params_*.json. Dual-tape PREMIUM_DIVERGENCE blocks
  new tickets. Leaderboard paper_sessions[] append. KEEP_ALL MIX-TV-EP.
Rejected: Auto-write MIX-DEFAULT-BUY / workspace.yaml; live Dhan orders;
  blocking LLM; STRAT-015+; promote on one green replay; infinite poll.
UNKNOWN: Same-calendar INDEX+CE+PE 1m (INDEX cache last 2026-09-03; ATM
  premium tape last 2026-09-11 — clock-align dry session only).
```

Spec: [`docs/TV_EP_PAPER_TUNE.md`](docs/TV_EP_PAPER_TUNE.md).

## As of now (2026-09-14) — 1m real-cache TV-EP grid (NIFTY 23500 PE)

```text
From:     teams/06_backtesting + 03 tape
To:       00 / 04 / 09 / founder
Date:     2026-09-14
Status:   VALIDATION cache run / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: tv-ep-grid --cache --tf 1 on Dhan INDEX 1m (NIFTY 13 / SENSEX 51 /
  BANKNIFTY 25, 11957 bars 2026-07-22→09-03) and NIFTY 23500 PE OPTIDX
  47298 (7185 bars 2026-08-18→09-11). SENSEX/BN premium = 3-day ATM PE
  tape. MIX-TV-EP-001..025 named ports. PREMIUM after-cost all FAIL where
  n≥5. INDEX WATCH ≠ option P/L.
Rejected: Synthetic-only as the founder answer; fake 23500 path; promote;
  live orders.
UNKNOWN: TV tester CSV; INDEX 1m after 09-03; next weekly PE after 09-15.
```

Spec: [`docs/TV_EP_1M_NIFTY_PREMIUM.md`](docs/TV_EP_1M_NIFTY_PREMIUM.md).

## As of now (2026-09-14) — TV-EP listing adapters (not stub)

```text
From:     teams/06_backtesting (harness) + 01/04 ports
To:       00 / 09
Date:     2026-09-14
Status:   HYPOTHESIS / 23 named adapters / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX-TV-EP-001..023 call Python ports via tv_ep registry.
  Stub remains only for unknown ids. Fixture tests long/short/flat.
Rejected: STRAT-015+; promoting fixture WATCH; live Dhan.
UNKNOWN: Real INDEX/OPTIDX cache on clone.
```

## As of now (2026-09-14) — TV-EP validate CE/PE × TF × market (NO_PROMOTE)

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-14
Status:   HYPOTHESIS / fixture-validated mapping / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: KEEP_ALL MIX-TV-EP-001–023 on the founder board even FAIL/PARK/DI/n=0.
  TV long/buy → BUY_CE; TV short/sell → BUY_PE (options buy first). Long-only
  sell/flat counted as EXIT, not discarded. Grid TFs 1m/3m/5m/15m; NIFTY/
  SENSEX + BANKNIFTY when tape exists. Board:
  data/recon/tv_ep_leaderboard.{json,md} + docs/TV_EP_LEADERBOARD.md.
Rejected: STRAT-015+; equity short as customer default; inventing 23500 PE;
  promoting WATCH; TV Strategy Tester clone claim; live orders.
UNKNOWN: Real INDEX/OPTIDX cache on this clone; SCORE_SAMPLE (NEWS_CALENDAR
  empty); OOS+NORMAL; which partial ports survive premium tape.
```

Spec: [`docs/TV_EP_BACKTEST_FACTORY.md`](docs/TV_EP_BACKTEST_FACTORY.md) · board [`docs/TV_EP_LEADERBOARD.md`](docs/TV_EP_LEADERBOARD.md).

## As of now (2026-09-14) — TV-EP factory (MIX-TV-EP-*) NO_PROMOTE

```text
From:     teams/06_backtesting (+ 02/04 engineering)
To:       00 / 01 / 04 / 09
Date:     2026-09-14
Status:   HYPOTHESIS / harness coded / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Repeatable TV Editor Picks factory — registry (sma_cross,
  macd_hist, stub), param×tf×index×premium grid, TREND/RANGE split,
  paper board JSON+MD. Catalog filled MIX-TV-EP-001..023 from live
  Editors’ Picks strategy badges (stub adapters) plus 024–025 textbook
  calibrators. IDs MIX-TV-EP-NNN. Stub still writes a DATA_INSUFFICIENT row.
Rejected: STRAT-015+; Pine dumps; promoting WATCH to customer /; live
  Dhan orders; starting npm / paper hours; treating fixture P/L as truth.
UNKNOWN: INDEX/OPTIDX cache on this clone; named EP ports; SCORE_SAMPLE
  (NEWS_CALENDAR empty). Paper-live attaches later to the same board.
```

Spec: [`docs/TV_EP_BACKTEST_FACTORY.md`](docs/TV_EP_BACKTEST_FACTORY.md). CLI: `python -m backtest_engine tv-ep-grid`.

## As of now (2026-09-10) — MRR shadow book (NO_PROMOTE)

```text
From:     teams/06_backtesting
To:       00 / 02 / 04 / 09
Date:     2026-09-10
Status:   VALIDATION / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Land MRR_BACKTEST_2026-09-10.md as the tracked shadow report
  for MIX-DUAL-INDEX-MASTER. Harness scripts/backtest_mrr.py uses
  PROJECT next-bar-open fills; SENSEX CALL cache is a research lead
  only. NIFTY arm FAIL stays recorded.
Rejected: Treating gross premium points as customer P/L; promoting
  Pine indicators to strategies; INDEX volume as option premium.
UNKNOWN: Brokerage/spread/slippage; live OPTIDX OHLC vs cache; whether
  SENSEX lead survives expiry-week and strike-bucket OOS.
```

## As of now (2026-09-10) — History APIs vs promote

```text
From:     teams/06_backtesting
To:       00 / 02 / 03 / 04 / 09
Date:     2026-09-10
Status:   VALIDATION / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Daily + intraday charts and rollingoption ATM± are the official
  history surfaces. Knowing them does not promote prior FAIL premium OOS.
Rejected: Treating sandbox or INDEX volume as option premium history.
```

## As of now (2026-09-08) — MIX-003/006 INDEX PROXY not a promote

```text
From:     teams/06_backtesting
To:       00 / 02 / 03 / 04 / 09
Date:     2026-09-08
Status:   PROXY labeled / WAITING / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: INDEX 1m resample may score MIX-003-INDEX-PROXY / MIX-006-INDEX-PROXY
  as WAITING PROXY (≠ spoken FUTIDX 3m / OPTIDX 2m). Not a promote. Not OOS.
Rejected: Treating resample as teacher tape; win-rate paste; STRAT delete.
UNKNOWN / DATA_INSUFFICIENT: continuous FUTIDX; VIX filter; SCORE_SAMPLE empty.
```

Newest first.

---

## As of now (2026-09-08) — CLUB-GR PARK not kill (SCORE_SAMPLE empty)

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-08
Status:   NO_PROMOTE / PARK working path
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Documented after-cost MIX-CLUB-GR NIFTY 44.4% FAIL promote
  (BACKTEST_HONEST_2026-09-06). SCORE_SAMPLE n=0 → cannot kill MIX.
  FUTIDX stitch DATA_INSUFFICIENT. Option-premium books historically FAIL.
Rejected: Promote; invent P/L; OOS+NORMAL kill claim.
```

Newest first.

---

## As of now (2026-09-06) — CF Andrea+Omor NIFTY OHLC proxies; honest; **no promote**

ASR guests. Andrea absorb OF PARKED; Omor KZ/ADR DI; six structure proxies. INDEX points ≠ option premium. Andrea ≠ Fabio. Podcast wr ignored.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-06
Status:   Proxy backtest written
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: cf-andrea-omor CLI; two DI arms + six proxy arms; promote=false;
  WEAK OTE ≠ promote; FAIL on ORB/fade/MMM; DI on absorb/KZ/low-n arms.
Rejected: promote; inventing OF/KZ; fake wr paste to UI; Fabio merge.

Artifacts:
- packages/backtest/src/backtest_engine/cf_andrea_omor_proxy.py
- packages/backtest/src/backtest_engine/run_cf_andrea_omor.py
- teams/06_backtesting/docs/BACKTEST_CF_ANDREA_OMOR_2026-09-06.md
- data/recon/BACKTEST_CF_ANDREA_OMOR_2026-09-06.json
```

---

## As of now (2026-09-06) — CF Usman+Brando NIFTY OHLC proxies; honest; **no promote**

ASR guests. Usman options arms DI; Brando news/size-zero DI; three Brando structure proxies. INDEX points ≠ option premium. $6k→$10M ignored.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-06
Status:   Proxy backtest written
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: cf-usman-brando CLI; six DI arms + three proxy arms; promote=false;
  WEAK≠promote; FAIL on reclaim/bounce.
Rejected: promote; inventing OI/greeks/news; fake wr paste to UI.

Artifacts:
- packages/backtest/src/backtest_engine/cf_usman_brando_proxy.py
- packages/backtest/src/backtest_engine/run_cf_usman_brando.py
- teams/06_backtesting/docs/BACKTEST_CF_USMAN_BRANDO_2026-09-06.md
- data/recon/BACKTEST_CF_USMAN_BRANDO_2026-09-06.json
```

---

## As of now (2026-09-06) — CF Carmine+Jadecap NIFTY OHLC proxies; honest; **no promote**

ASR guests. Structure proxies only; Carmine absorb OF + Jade session-liq = DI. INDEX points ≠ option premium. Dollar P/L / Apex ads ignored.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-06
Status:   Proxy backtest written
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: cf-carmine-jadecap CLI; two DI arms + four proxy arms; promote=false;
  WEAK≠promote.
Rejected: promote; inventing DOM/delta or Asia NSE boxes; fake wr paste to UI.

Artifacts:
- packages/backtest/src/backtest_engine/cf_carmine_jadecap_proxy.py
- packages/backtest/src/backtest_engine/run_cf_carmine_jadecap.py
- teams/06_backtesting/docs/BACKTEST_CF_CARMINE_JADECAP_2026-09-06.md
- data/recon/BACKTEST_CF_CARMINE_JADECAP_2026-09-06.json
```

---

## As of now (2026-09-06) — CF TG+Kane NIFTY OHLC proxies; honest; **no promote**

ASR guests. Structure proxies only. INDEX points ≠ option premium. Title 90% ignored.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-06
Status:   Proxy backtest written
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: cf-tg-kane CLI; four proxy arms; promote=false always; WEAK≠promote.
Rejected: promote; claiming proxies = full guest models; fake wr paste to UI.

Artifacts:
- packages/backtest/src/backtest_engine/cf_tg_kane_proxy.py
- packages/backtest/src/backtest_engine/run_cf_tg_kane.py
- teams/06_backtesting/docs/BACKTEST_CF_TG_KANE_2026-09-06.md
- data/recon/BACKTEST_CF_TG_KANE_2026-09-06.json
```

---

## As of now (2026-09-06) — CF Marci+Tori NIFTY OHLC proxies; honest; **no promote**

ASR guests. Structure proxies only. INDEX points ≠ option premium.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-06
Status:   Proxy backtest written
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: cf-marci-tori CLI; four proxy arms; promote=false always.
Rejected: promote; claiming proxies = full guest models; fake wr paste to UI.

Artifacts:
- packages/backtest/src/backtest_engine/cf_marci_tori_proxy.py
- packages/backtest/src/backtest_engine/run_cf_marci_tori.py
- teams/06_backtesting/docs/BACKTEST_CF_MARCI_TORI_2026-09-06.md
- data/recon/BACKTEST_CF_MARCI_TORI_2026-09-06.json
```

---

## As of now (2026-09-06) — CF Marco+Mayne NIFTY OHLC proxies; honest; **no promote**

ASR guests. Structure proxies only. INDEX points ≠ option premium.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-06
Status:   Proxy backtest written
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: cf-marco-mayne CLI; four proxy arms; promote=false always.
Rejected: promote; claiming proxies = full guest models; fake wr paste to UI.

Artifacts:
- packages/backtest/src/backtest_engine/cf_marco_mayne_proxy.py
- packages/backtest/src/backtest_engine/run_cf_marco_mayne.py
- teams/06_backtesting/docs/BACKTEST_CF_MARCO_MAYNE_2026-09-06.md
- data/recon/BACKTEST_CF_MARCO_MAYNE_2026-09-06.json
```

---

## As of now (2026-09-06) — CF Fabio NIFTY OHLC proxies; **FAIL/WEAK**; **no promote**

Teacher OF PARKED. Structure proxies only. Session transfer DATA_INSUFFICIENT.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-06
Status:   BACKTEST_CF_FABIO ran / FAIL+WEAK / not a promote
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Accepted: cf-fabio CLI; failed-auction FAIL; break-retest WEAK; MR_TO_POC FAIL;
  paper-watch stub; OF gaps explicit.
Rejected: promote; claiming proxies = Fabio OF model; option premium as proven.
UNKNOWN: CVD/footprint history; NY clock map.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_CF_FABIO_2026-09-06.md
- data/recon/BACKTEST_CF_FABIO_2026-09-06.json
- packages/backtest/src/backtest_engine/fabio_proxy.py
- packages/backtest/src/backtest_engine/run_cf_fabio.py
```

---

## As of now (2026-09-06) — SL/TP NIFTY overlay backtest; **FAIL**; **no promote**

Named ATR+R2 and ST-flip exits on INDEX 3m. All score **FAIL** or DATA_INSUFFICIENT. Keep current default.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 04 / 09
Date:     2026-09-06
Status:   BACKTEST_SLTP ran / FAIL / not a promote
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Accepted: run_sltp CLI; JSON under data/recon/BACKTEST_SLTP_2026-09-06.json;
  honest FAIL for MIX-DESK-IQ-ATR-RR2 and MIX-SLTP-ST-FLIP.
Rejected: promote; apply option 1% cost to index points as if premium.
UNKNOWN: OPTIDX premium% path; FUTIDX; GEX filter.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_SLTP_2026-09-06.md
- packages/backtest/src/backtest_engine/run_sltp.py
- packages/backtest/src/backtest_engine/simulate_sltp.py
```

---

## As of now (2026-09-06) — costs + expiry strip + FUTIDX stitch; **no promote**

Hypothesis 1% RT haircut on frozen club books. CLUB-GR NIFTY **44% wr FAIL** (was 69% optimistic). SCORE_SAMPLE empty. Continuous FUTIDX **DATA_INSUFFICIENT** (~64d).

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 02 / 04 / 09
Date:     2026-09-06
Status:   honest leftover ran / KEEP current / not a promote
Gate:     NOT a promote; not RESEARCH_READY_FOR_PROGRAMMING

Summary:
python -m backtest_engine --live --years 5 --interval 1 honest.
HYPOTHESIS_OPTION_RT_1PCT. Statutory UNKNOWN. News calendar empty.
CLUB-GR NIFTY after-cost OOS wr 44.4% FAIL. GXR WEAK n=30 SENSEX FAIL.
FUTIDX stitch span 64d DATA_INSUFFICIENT. No grid retune.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_HONEST_2026-09-06.md
- data/recon/BACKTEST_HONEST_2026-09-06.json

What the next team must not do:
- Promote 44% or GXR 50%. Call EXPIRY_STRIPPED NORMAL. Live orders.

Review: FIVE_PASS FAILED REVIEW
```

---

## As of now (2026-09-03) — 2y club + annexure grid; **no promote**

CLUB-GR NIFTY 69% wr on **36** OOS trades is WEAK (winner-soup). RSI 58% wr FAIL exp. Nested grids FAIL holdout.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 02 / 04 / 09
Date:     2026-09-03
Status:   2y club+grid ran / KEEP current / not a promote
Gate:     NOT a promote; not RESEARCH_READY_FOR_PROGRAMMING

Summary:
python -m backtest_engine --live --years 5 --interval 1 club.
GAP∧RANGE-EXP NIFTY OOS wr 69.4% n=36 WEAK. RSI_14 58% wr exp -0.35 FAIL.
GRID RSI/Donch/BB/EMA holdout FAIL. SENSEX all FAIL. Costs UNKNOWN.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_CLUB_2026-09-03.md
- data/recon/BACKTEST_CLUB_2026-09-03.json

What the next team must not do:
- Promote 69%. Treat wr-up as edge. Live orders.

Review: NOTES_ONLY
```

---

## As of now (2026-09-03) — founder clock + ML scan; **no promote**

Drop 09:00–09:30 and 15:00–15:30 IST. ML logit 55.7% NIFTY wr **FAIL** (exp −0.77). GAP/ENGULF WEAK. Default unchanged.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 02 / 04 / 09
Date:     2026-09-03
Status:   CLOCK+ML scan ran / KEEP current / not a promote
Gate:     NOT a promote; not RESEARCH_READY_FOR_PROGRAMMING

Summary:
python -m backtest_engine --live --years 5 --interval 1 scan.
Dead band 09:00-09:30 and 15:00-15:30 IST. ORB empty. MIX-ML-LOGIT NIFTY
OOS wr 55.7% exp -0.77 FAIL. MIX-GAP 55% WEAK (5y 54% still WEAK).
ENGULF WEAK. SENSEX all FAIL wr. Costs UNKNOWN.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_SCAN_CLOCK_2026-09-03.md
- data/recon/BACKTEST_SCAN_CLOCK_2026-09-03.json

What the next team must not do:
- Promote 55% wr. Grid logit threshold. Relabel DHAN-DERIVED. Live orders.

Review: NOTES_ONLY
```

---

## As of now (2026-09-03) — WEB/PATTERN scan ran; **no promote**

20 MIX books, expanding windows, NIFTY+SENSEX option premium. Three NIFTY 730d WEAK; GAP 5y FAIL; SENSEX all FAIL wr. Default mix unchanged.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 02 / 04 / 09
Date:     2026-09-03
Status:   WEB/PATTERN scan ran / KEEP current / not a promote
Gate:     NOT a promote; not RESEARCH_READY_FOR_PROGRAMMING

Summary:
python -m backtest_engine --live --years 5 --interval 1 scan.
20 WEB/PATTERN MIX × NIFTY+SENSEX. 30d/90d SCREEN. 730d: ENGULF / INSIDE-BRK /
GAP NIFTY WEAK (~47–48% wr, optimistic exp>0). GAP 5y FAIL (exp -0.34).
SENSEX all FAIL wr. ORB folklore FAIL. Multiple testing. Costs UNKNOWN.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_SCAN_2026-09-03.md
- data/recon/BACKTEST_SCAN_2026-09-03.json

What the next team must not do:
- Promote 47%. Grid candle/ORB after wr. Relabel DHAN-DERIVED. Live orders.
- Treat 30d NR7 60% (n=5) as edge.

Review: NOTES_ONLY
```

---

## As of now (2026-09-03) — PROJECT_MIX option books **FAIL**

Two isolated PROJECT mixes ran on NIFTY+SENSEX rollingoption. **All FAIL.** Default mix unchanged.

Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 02 / 04 / 09
Date:     2026-09-03
Status:   PROJECT_MIX ran / ALL FAIL / keep current
Gate:     NOT a promote; not RESEARCH_READY_FOR_PROGRAMMING

Summary:
python -m backtest_engine --live --years 5 --interval 1 project.
MIX-MTF-TREND NIFTY OOS wr 35.6%. MIX-CONFIRM-5M NIFTY 42.5% exp -0.11.
SENSEX both wr < 45%. Costs UNKNOWN. Not DHAN-DERIVED.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_PROJECT_2026-09-03.md
- data/recon/BACKTEST_PROJECT_2026-09-03.json

What the next team must not do:
- Promote 42.5%. Grid MACD/ST. Relabel as DHAN-DERIVED. Live orders.

Review: NOTES_ONLY
```

---

## As of now (2026-09-03) — 5y option premium **FAIL**

Rollingoption OPTIDX 1m ran. **All 24 MIX cells FAIL.** Nothing promotes. KEEP_ALL. Not `RESEARCH_READY_FOR_PROGRAMMING`.

Copy the template from [`docs/HANDOFF.md`](../../docs/HANDOFF.md). Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 02 / 04 / 09
Date:     2026-09-03
Status:   HYPOTHESIS / option premium ran / ALL FAIL / keep current
Gate:     BACKTEST_REQUIRED; keep_current_strategy; NOT a promote

Summary:
python -m backtest_engine --live --years 5 --interval 1 option.
NIFTY/BN ~464k 1m OPTIDX bars; SENSEX thinner (20 empty early chunks).
Teacher MIX + PROJECT default all OOS wr < 45% (Mukul BN 43.5% nearest miss).
Costs UNKNOWN. News not stripped. Do not grid Supertrend.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_OPTION_2026-09-03.md
- data/recon/BACKTEST_OPTION_2026-09-03.json (gitignored)

What the next team must do:
- 09 notes (BACKTEST_OPTION_REVIEW). Keep orders refused. Do not auto-retune.

What the next team must not do:
- Promote 43.5%. Treat optimistic exp as after-cost. Delete FAIL books.

Blockers: costs; NORMAL-only; continuous FUTIDX; Q12 fills; live orders.

Review: NOTES_ONLY
```

---

Engine **exists**. 5-year 1m INDEX + current FUTIDX. All coded books **FAIL** OOS win_rate. Nothing promotes. Nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. Not `RESEARCH_READY_FOR_PROGRAMMING`.

Copy the template from [`docs/HANDOFF.md`](../../docs/HANDOFF.md). Newest first.

---

```text
From:     teams/06_backtesting
To:       00 / 02 / 04 / 09
Date:     2026-09-03
Status:   HYPOTHESIS / engine ran / FAIL proxy / not OOS_NORMAL_VALIDATED
Gate:     BACKTEST_REQUIRED; keep current strategy; NOT a promote

Summary:
python -m backtest_engine --live --years 5 --interval 1. INDEX ~500k 1m bars
each. FUTIDX ~17k bars from 2026-07-01 (current contract). MIX-DEFAULT-BUY /
STRAT-003 OOS wr ~27–28%. STRAT-001 ~42%. STRAT-006 ~35%. All FAIL.
option_pnl null. 008 veto 348 days. News filter DATA_INSUFFICIENT.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md
- data/recon/BACKTEST_BOOKS_2026-09-03.json (gitignored)

What the next team must do:
- 09 notes (done: BACKTEST_REVIEW). Option fills next. Do not auto-retune.

What the next team must not do:
- Promote. Treat proxy wr as customer P/L. Delete FAIL books.

Blockers: option history; continuous FUTIDX; NORMAL-only tags.

Review: pending five-pass
```

---

```text
From:     teams/06_backtesting
To:       teams/05_analysis, teams/04_quant, teams/09_review, teams/00_orchestrator
Date:     2026-09-03
Status:   HYPOTHESIS / engine stub exists / not OOS_VALIDATED
Gate:     BACKTEST_REQUIRED; keep current strategy; this run is NOT a promote

Summary:
Live INDEX 5m stub (`python -m backtest_engine --live`) wrote
data/recon/BACKTEST_INDEX_5M_2026-09-03.json. Window 2026-08-27 09:15 →
2026-09-03 15:40 IST. NIFTY / BANKNIFTY / SENSEX each 425 bars (IDX_I,
interval 5). CE/PE/SKIP (all-three lean, after 09:15–09:45 open skip and
after-15:15 flatten): NIFTY 108/137/130; BANKNIFTY 89/143/143; SENSEX
103/136/136. win_rate null. option_pnl null. metrics_claimed false.
FUTURES_PROXY on INDEX OHLC — not option fills; spoken STRAT-003 is 3m
FUTIDX (HQ has no 3m). Do not invent PF/DD.

EVENT_MEMORY (docs/EVENT_MEMORY.md): SCORE_SAMPLE vs ANALOG still
schema-only; analog path fields stay null. 2026-09-03 is SENSEX expiry →
ANALOG_MEMORY / EXPIRY, out of SCORE_SAMPLE. Per EVENT_MEMORY §3 this
run is NOT a promote (one-day / expiry / no OOS+NORMAL; win_rate and
option_pnl null). RETUNE_GATE: default keep current strategy.

RATE_LIMITS (packages/dhan-client/docs/RATE_LIMITS.md): Data APIs 5/s
(day cap documented). Charts gated. Do not burst Data past 5/s. No Order
APIs.

Accepted: bar counts + CE/PE/SKIP as counts only; null win_rate /
option_pnl; expiry-day = analog not score; rate-limit 5/s; stub CLI.
Rejected: treating this as OOS or a MIX/STRAT promote; invented PF/DD /
expectancy / win rate; option P/L from INDEX OHLC; SCORE_SAMPLE fill
from an EXPIRY session.
UNKNOWN / DATA_INSUFFICIENT: option fills, costs/slippage, OOS walk-
forward, analog matcher, 3m vs 5m ablation, 007 vs 009.

Artifacts:
- packages/backtest (python -m backtest_engine --live)
- data/recon/BACKTEST_INDEX_5M_2026-09-03.json
- teams/06_backtesting/docs/EVENT_MEMORY.md
- teams/06_backtesting/docs/RETUNE_GATE.md
- packages/dhan-client/docs/RATE_LIMITS.md

What the next team must do:
- 05: do not turn CE/PE bar counts or analog type into EARLY/CONFIRMED.
  Expiry veto still wins. Analog copy stays DATA_INSUFFICIENT.
- 04: KEEP_ALL. Extra MIX rows for 007 vs 009 / 3m vs 5m. Do not freeze
  MIX-DEFAULT-BUY from this stub.
- 09: not a five-pass. Notes ≠ pass. Do not treat 425-bar counts as
  RESEARCH_READY_FOR_PROGRAMMING.
- 00: score sheet still honest — stub ≠ OOS.

What the next team must not do:
- Invent PF/DD/expectancy/win_rate. Auto-retune. Code live STRATs.
- Promote from INDEX proxy or SENSEX expiry. Burst Data API past 5/s.

Blockers / UNKNOWN / DATA_INSUFFICIENT:
- No option-book engine. No OOS. Analog store empty. Live chain unvalidated
  beyond this INDEX 5m fetch.

Review: n/a (stub run; not RESEARCH_READY_FOR_PROGRAMMING)
```

---

## As of now (2026-09-03) — EVENT_MEMORY schema

YouTube **45** verified + **45** English. Engine **stub now exists** (see block above); this older note froze schema **before** that CLI. Nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. STRATs **UNVALIDATED**. Not `RESEARCH_READY_FOR_PROGRAMMING`. Event memory is **schema only** — no analog paths, no score metrics.

Copy the template from [`docs/HANDOFF.md`](../../docs/HANDOFF.md). Newest first.

---

```text
From:     teams/00_orchestrator (founder ask) + 06_backtesting
To:       teams/05_analysis, teams/04_quant, teams/09_review
Date:     2026-09-03
Status:   HYPOTHESIS / schema only / engine still stub
Gate:     BACKTEST_REQUIRED; keep current strategy; analog payloads DATA_INSUFFICIENT

Summary:
Two tracks for when an engine exists. SCORE_SAMPLE = NORMAL days only
(align RETUNE_GATE), also excluding circuit/gap/halt so outliers do not
fake expectancy/PF/DD. ANALOG_MEMORY stores NEWS_DAY / EXPIRY / circuit /
gap anyway for later type-match (“days like this, in sample, path was X”).
observed_path_fields (open_gap, CAS_close_vs_ref, CE_PE_lean) stay null.
Promotion unchanged: no auto-retune, no invented metrics. Kill MIX/STRAT
only after real OOS+NORMAL; 02/03 disagreement = extra MIX row, not
deletion. Score styles separately later: OPTION_BUYER, OPTION_SELLER,
SCALPER, POSITION, EQUITY, CAS. Today every analog payload is empty.

Accepted: split tracks; analog schema keys; kill-after-OOS; six styles;
hypothesis-only analog copy.
Rejected: ranking on event days; fake P/L or filled path fields; spec-time
kills; analog as entry alpha.
UNKNOWN / DATA_INSUFFICIENT: engine, gap construction, similar_to matcher,
all analog numbers.

Artifacts:
- teams/06_backtesting/docs/EVENT_MEMORY.md
- teams/06_backtesting/docs/RETUNE_GATE.md (pointer)

What the next team must do:
- 05: do not turn analog type-match into EARLY/CONFIRMED; veto still wins
  on NEWS_DAY/EXPIRY. When a store exists, analog copy = hypothesis.
- 04: keep extra MIX rows for 02/03 conflicts (do not delete IDs).
- 09: this is not a five-pass; do not treat schema as results.

What the next team must not do:
- Invent backtest or analog metrics. Auto-retune from similar news.
- Pool EQUITY/CAS into index-option SCORE_SAMPLE. Code live STRATs.

Blockers / UNKNOWN / DATA_INSUFFICIENT:
- No engine. Analog store empty. Live Dhan unvalidated.

Review: n/a (schema; not RESEARCH_READY_FOR_PROGRAMMING)
```

---

## As of now (2026-09-01)

YouTube **45** verified + **45** English. `config/workspace.yaml`. Dhan **dry-run, no orders**. Customer `/`: ticket + **IN-PROGRESS** + **CasPanel**; book P/L **MOCK**. Internal **`/desk`**. Chain **3m**. Nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. Engine **does not exist**. CAS = **Closing Auction Session**. STRATs **UNVALIDATED**. Not `RESEARCH_READY_FOR_PROGRAMMING`. Older “jobs CLI not built” lines are dated history — nightly stub exists.

Copy the template from [`docs/HANDOFF.md`](../../docs/HANDOFF.md). Newest first.

---

```text
From:     teams/00_orchestrator
To:       teams/06_backtesting
Date:     2026-09-01
Status:   INFORMED / engine still stub / RETUNE_GATE docs+stubs
Gate:     nightly RETUNE_PROPOSAL is BACKTEST_REQUIRED; keep current strategy

Summary:
Do not retune from one recon file, especially NEWS_DAY / EXPIRY.
Nightly tags the session and emits RETUNE_PROPOSAL (no production params).
Promote only after OOS + NORMAL backtest on expectancy/PF/DD vs current,
or a documented glitch fix. PhD handoff is REVIEW. No invented metrics.

Artifacts:
- teams/06_backtesting/docs/RETUNE_GATE.md
- teams/00_orchestrator/docs/TASK_RETUNE_GATE.md
- desk_intel.retune_gate + nightly.RECON_JSON_KEYS

What the next team must do:
- When an engine exists: consume recon JSON; exclude event days from retune sample.

What the next team must not do:
- Auto-apply nightly hints. Rank by one-day shadow P/L. Live orders.

Blockers: no engine yet.

Review: n/a
```

---

```text
From:     teams/00_orchestrator
To:       teams/06_backtesting
Date:     2026-09-01
Status:   INFORMED / engine still stub
Gate:     paper daily + pre-prod — nightly schema exists; not live strategy

Summary:
Jobs CLI is in packages/desk-intel: python -m desk_intel nightly --offline
or python -m jobs post-market --offline. JSON data/recon/YYYY-MM-DD.json.
PhD NIGHTLY_YYYY-MM-DD.md. Param review UNVALIDATED. Do not rewrite live
strategy. Mock ACHIEVED in the UI is not OOS.

Artifacts:
- desk_intel.nightly.RECON_JSON_KEYS
- teams/06_backtesting/README.md (prerequisites)

What the next team must do:
- When scheduled: engine with costs; ingest nightly JSON as paper/pre-prod.
- Keep UNVALIDATED.

What the next team must not do:
- Live orders. Hardcode 15:30 vs 15:40. Rank by one-day shadow P/L.
- Treat mock UI ACHIEVED as a backtest fill.

Blockers: no engine yet; DHAN_* for live chain; circulars not in repo.

Review: n/a
```

---

```text
From:     teams/00_orchestrator
To:       teams/06_backtesting
Date:     2026-09-01
Status:   INFORMED / engine still stub
Gate:     Need nightly recon schema + paper fills before strategy retune

Summary:
Paper UI now labels closed tickets (INVALIDATED/ACHIEVED/STOPPED/LOST/EXPIRED)
and shadow-tracks skips. That is mock JSON, not a backtest fill. Prerequisite:
nightly recon + paper-fill schema from 07 jobs before any STRAT-* retune.

Artifacts:
- apps/web/public/mock/signal.json (lifecycle.outcome, shadowPaper)
- teams/00_orchestrator/docs/STATUS.md

What the next team must do:
- Wait for recon/jobs schema. Rank with costs; no look-ahead.

What the next team must not do:
- Treat mock ACHIEVED as OOS. Code live Dhan. Hardcode lots.

Blockers: jobs CLI not built; packet still UNVALIDATED.

Review: n/a
```

---

_(no older handoffs)_
