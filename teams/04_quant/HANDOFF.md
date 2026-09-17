# Handoff log — Team 04 Quant

## As of now (2026-09-17) — path-feasible target; IV widens stop only (NO_PROMOTE)

```text
MIX / STRAT: none new. KEEP_ALL 001–014. No STRAT-015+.
Origin tags: PROJECT-DERIVED paper overlay.
Entry hypothesis: none. Side still dealer/logit/TV.
Confirm-or-kill: OPEN_SETTLE_35M blocks NEW before 09:50.
  Fantasy 266/219/615 = TARGET_FEASIBILITY_FAIL or clipped.
Hold / veto rules: SIDEWAYS + TREND-against still skip NEW.
Feasibility rules: MAX_R=2.0 independent of inflated typical.
  same_contract_premium_path drops index-like / other-strike.
  greeks_paper_adjust: Dhan IV ≥25 widens STOP only — proven in
  code; IV is not an input to propose_levels. Did not 3–4× target.
Parameters to grid: session paper_add_lot default false;
  max_target_r=2. production_params_written false.
Backtest request: smoke 266/219/615 + 09:50 gate.
Customer copy allowed: none.
Internal-only: TARGET_STEP_1/2 within cap; prefer cancel.
UNKNOWN / DATA_INSUFFICIENT: India VIX (not on Dhan/warehouse
  path used here). Max pain only if already computed.
```

## As of now (2026-09-17) — ML books get Dhan greeks pack; ml001-v1 still returns-only

```text
MIX / STRAT: MIX-ML-GREEKS (ml-greeks-v1). ML-001/002 stay ml001-v1.
Origin tags: PROJECT-DERIVED overlay. Dhan fields SOURCE_FACT.
Entry hypothesis: none. Greeks HOLD/skip only. Side still dealer/index.
Confirm-or-kill: GREEKS_MISSING if delta+IV+theta all null. Vega not a skip.
Hold / veto rules: this book only. Do not dump greeks into KMeans.
Feasibility rules: existing paper stop/target. Dealer kills fantasy SL.
Parameters to grid: none this tick. Pack-only.
Backtest request: none. Live DUAL-TAPE 2026-09-17 tick 12 already has
  NIFTY ITM CE delta 0.656 / theta -17.06 / IV 13.61 / gamma 0.00095.
Customer copy allowed: none.
Internal-only: wing pack now includes vega + oi. Heartbeat adds gamma/vega.
UNKNOWN / DATA_INSUFFICIENT: option volume 0 pre 09:15; ML-1 still <30 labels.
```

## As of now (2026-09-17 PRE) — TREND-UP confirm/kill overlay (NO_PROMOTE)

```text
MIX / STRAT: none new. Overlay on LIVE_BOOKS. KEEP_ALL 001–014.
Origin tags: PROJECT-DERIVED HYPOTHESIS. Not SOURCE_FACT.
Entry hypothesis: none. Side still dealer/logit/TV.
Confirm-or-kill: TREND+UP kills new PE; TREND+DOWN kills new CE.
  SIDEWAYS_HOLD still skips NEW opens. 5m ST/MACD/RSI still not entry.
Hold / veto rules: flatten/cancel + greeks-dead cancel still run.
Feasibility rules: working limit = signal × (1-limit_discount_frac).
Parameters to grid: limit_discount_frac {0.008,0.012,0.02};
  skip_trend_against {true,false}. Session file only.
  production_params_written false.
Backtest request: smoke 17 Sep DI; 16 Sep max-5 not today.
Customer copy allowed: none.
Internal-only: skip_trend_against paper param.
UNKNOWN / DATA_INSUFFICIENT: 17 Sep INDEX 1m path empty before 09:15.
```

## As of now (2026-09-16) — INDEX 1m SIDEWAYS HOLD (NO_PROMOTE)

```text
MIX / STRAT: none new. Overlay on LIVE_BOOKS opens. KEEP_ALL 001–014.
Origin tags: PROJECT-DERIVED HYPOTHESIS. Not SOURCE_FACT. Not XR.
Entry hypothesis: none. Side still dealer/logit/TV. Regime is skip only.
Confirm-or-kill: SIDEWAYS_HOLD on NEW opens. 5m ST/MACD/RSI still not entry.
Hold / veto rules: flatten/cancel of working tickets still allowed.
Feasibility rules: existing paper stop/target / working-limit.
Parameters to grid: regime_er_max {0.28,0.30,0.35}; flip_min {0.35,0.38};
  lookback {12,20}. Session file only. production_params_written false.
Backtest request: done 2026-09-16 tape — see BACKTEST_SIDEWAYS_REGIME.md.
Customer copy allowed: none.
Internal-only: skip_sideways paper param. XR cloned dealer because
  deny_model_signals=false fallback, not because XR detects 1m chop.
UNKNOWN / DATA_INSUFFICIENT: OOS next session; option L2 not used.
```

## As of now (2026-09-16) — MIX-ML-GREEKS paper book (NO_PROMOTE)

```text
MIX / STRAT: MIX-ML-GREEKS
Origin tags: PROJECT-DERIVED. Dhan greeks SOURCE_FACT. Not STRAT-015+.
Entry hypothesis: none. Side from dealer/index. Greeks HOLD only.
Confirm-or-kill: GREEKS_MISSING / DELTA_OTM / IV_RICH / IV_FLAT / THETA_LATE.
Hold / veto rules: this book only. ml001-v1 unchanged.
Feasibility rules: existing paper stop/target + dealer kill of fantasy SL.
Parameters to grid: IV_RICH_ABS {18,20,22}; THETA_BLEED {0.04,0.06,0.08}.
Backtest request: done 2026-09-16 tape — 28 closes vs dealer 250. wr not better.
Customer copy allowed: none.
Internal-only: ml-greeks-v1. Bind LIVE_BOOKS for 09:15 IST tomorrow.
UNKNOWN / DATA_INSUFFICIENT: most session ticks had LTP wings without greeks.
```

## As of now (2026-09-16) — paper greeks/IV from Dhan chain (NO_PROMOTE)

```text
From:     teams/04_quant + 03
To:       00 / 06 / founder
Date:     2026-09-16
Status:   PAPER GREEKS OVERLAY / HYPOTHESIS / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Official chain fields exist: implied_volatility +
  greeks.delta/theta/gamma/vega (DHAN_API_END_TO_END). parse_oc now
  keeps IV/theta/vega (was dropping IV; chain_iv.py had to reparse).
  Paper: |delta|<0.40 skip (HAUS ~40d). IV≥25 wider stop. High
  |theta|/entry closer target. Delta band 0.45–0.70 pick vs ITM_100.
  STRAT-006 0.55–0.60 stays WEAK — not frozen.
Rejected: Invented greeks. Promote from wr. Live orders. STRAT-015+.
UNKNOWN: Whether live Dhan payload fills greeks today (null until tick).
```

## As of now (2026-09-16) — paper ITM_100 not ATM (NO_PROMOTE)

```text
From:     teams/04_quant
To:       00 / 06 / founder
Date:     2026-09-16
Status:   PAPER STRIKE WING / KEEP_ALL / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Paper scalp books use STRAT-006 ITM_100_to_200 wing (~100 pts).
  CE ITM below ATM, PE ITM above. MTM that strike from chain wing quotes.
Rejected: STRAT-015+. ATM-only tickets as the paper default. Live orders.
UNKNOWN: 0.55–0.60 delta still WEAK — not frozen.
```

## As of now (2026-09-16) — session paper params from mistakes (NO_PROMOTE)

```text
From:     teams/04_quant
To:       00 / 06 / founder
Date:     2026-09-16
Status:   PAPER TUNE FILE / KEEP_ALL / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: SL-hit / TIME-loss lessons write data/recon/ml_paper_session_params.json
  (stop_frac / target_frac / hold bars). Nudge every +8 session closes.
  Overlay books still independent of dealer.
Rejected: Writing MIX-DEFAULT-BUY. Auto-retune production. STRAT-015+.
UNKNOWN: Whether session overfit beats default 0.40/0.55/8 on next day OOS.
```

## As of now (2026-09-16) — parallel paper scalpers (HOLD does not veto dealer)

```text
From:     teams/04_quant
To:       00 / 06 / 07 / founder
Date:     2026-09-16
Status:   PAPER BOOKS / KEEP_ALL / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: ML-001/002 SKIP their own book on HOLD; MIX-DEFAULT-BUY still
  independent. MIX-ML-LOGIT remains coded scan in ml_leans.py, not default.
Rejected: STRAT-015+. Deleting inverted NIFTY HOLD overlay. Live orders.
UNKNOWN: ML-1 still thin on NIFTY-first pass (7 closes this replay).
```

## As of now (2026-09-16) — ML bucket first (HOLD overlay, not buy)

```text
MIX / STRAT: ML-001, ML-002, MIX-FORM-*, MIX-ML-LOGIT* (scan coded in ml_leans.py; KEEP, not default)
Origin tags: PROJECT-DERIVED overlays. Not DHAN-DERIVED. Not STRAT-015+.
Entry hypothesis: none. Overlays do not enter. Logit labels INDEX 3m next-close, not premium.
Confirm-or-kill: FOLLOW-GAP / DIVERGE / residual IF / |z|≥2 → HOLD new paper CE/PE.
Hold / veto rules: session_action=HOLD. PAPER_TRAIN_NO_DENY bypasses this (do not use when tuning).
Feasibility rules: need ≥2 INDEX+ATM CE+PE ticks; empty window → HOLD DATA_INSUFFICIENT.
Parameters to grid: ML-002 window {40,60,90} only; z=2; seed 14. Ablation DIVERGE_ONLY / UNION_NO_FOLLOW_GAP did not flip NIFTY — keep FOLLOW-GAP, do not delete.
Backtest request: paper-scalp replay on joined INDEX∩ATM (now 1643 triples 2026-09-09…16).
Customer copy allowed: "machine can HOLD if premium does not follow the index." No live win %.
Internal-only: cluster names, z, IsolationForest.
UNKNOWN / DATA_INSUFFICIENT: NORMAL-day split; HQ IV. Overlay replay-hold still 09-09…10 diagnostic.

Accepted: ML bucket first, not STRAT-003. replay-hold n_scored=583 (2026-09-09…10 only):
  NIFTY FOLLOW_GAP n=133 HOLD +0.293% vs not −0.182% (inverted). DIVERGE_ONLY still inverted.
  BANKNIFTY FOLLOW_GAP n=178 −0.076% vs −0.055%. SENSEX FOLLOW_GAP n=191 −0.359% vs −0.848%.
  MIX-ML-LOGIT already scored 2026-09-03: NIFTY 2y wr 55.7% exp −0.77 FAIL; XR WEAK. Keep IDs.
  paper-scalp win_rate is closed pnl>0 / n — not a promote.
Rejected: Treating ML FAIL as STRAT FAIL. Auto-retune MIX-DEFAULT-BUY. Live orders. Discarding ML-002.
```

## As of now (2026-09-16) — CAS-* PARKED off MIX working book

```text
From:     teams/04_quant
To:       00 / 03 / founder
Date:     2026-09-16
Status:   PARKED / KEEP_ALL (Dhan TV ML only) / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX-CAS pointer PARKED. Do not attach CAS-* to
  MIX-DEFAULT-BUY. STRAT-009 stays.
Rejected: Scoring CAS-001–005. STRAT-015+.
```

## As of now (2026-09-16) — KEEP_ALL inventory (Dhan / TV / ML)

```text
From:     teams/04_quant
To:       00 / 01 / 06 / 09 / founder
Date:     2026-09-16
Status:   HYPOTHESIS / KEEP_ALL / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Catalog now names the held book in one place:
  Dhan STRAT-001–014 + MIX clubs + MIX-ALGO-*;
  TV MIX-TV-EP-001–025; MIX-CHAMP-* family file;
  MIX-FORM-* family file; ML-001 + ML-002 overlays.
  Family files: candidates/MIX-CHAMP.md, MIX-FORM.md, MIX-ALGO.md.
Rejected: Deleting any of those IDs. STRAT-015+. Rebuilding MIX-CF/Okala.
  Treating lab WR or IsolationForest as a buy.
UNKNOWN: Closed option-premium P/L on today's dual-tape (exits still missing).
```

## As of now (2026-09-16 ~09:45 IST) — PAPER_TRAIN_NO_DENY (boss 00↔04)

```text
From:     teams/04_quant (research) reviewed by 00 boss
To:       00 / 06 / founder
Date:     2026-09-16 ~09:45 IST
Status:   HYPOTHESIS / PAPER TRAIN / NO_PROMOTE / no live orders
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Founder asked to stop explicit paper DENY so ML + TV-EP +
  STRAT can train on live dual-tape. Dealer still LABELS HOLD /
  PREMIUM_DIVERGENCE / FOLLOW-GAP. Paper path books CE/PE on index
  lean anyway (PAPER_TRADE OPEN_PAPER). STALE / WRONG_STRIKE / DI
  still cannot invent a fill. IsolationForest remains anomaly label,
  not a live BUY. TV-EP causal overlay / premium_divergence do not
  drop tickets when PAPER_TRAIN_NO_DENY=1. Production live deny
  stays the default when the flag is off.
Rejected: Dhan Super Orders; auto-promote; STRAT-015+; treating
  paper fills as expectancy/PF/DD.
UNKNOWN: Whether LTP-clone TV tickets match OPTIDX OHLC OOS.
Next backtestable: score today's PAPER_TRADE jsonl vs HOLD labels
  after close; walk-forward MIX-TV-EP-018 / MIX-DEFAULT-BUY on OHLC.
```

## As of now (2026-09-15 ~10:45 IST) — HYPOTHESIS queued into paper loops (NO_PROMOTE)

```text
From:     teams/04_quant
To:       00 / 06 / founder
Date:     2026-09-15 ~10:45 IST
Status:   HYPOTHESIS overlay / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Queue (1) persist dual-tape 1m triples for ML-002 window 90
  into desk_ml fit/mrr-fit/score loop; (2) 5m ST/MACD/RSI confirm-or-kill
  stays in lean MIX eval — not entry; (3) TV-EP paper-tune must not treat
  LTP clones as OPTIDX OHLC OOS.
Rejected: Promote; IF as BUY; STRAT-015+; Okala as customer default.
UNKNOWN: Named MIX "OKLA" — not in catalog. Okala CF path removed.
```

## As of now (2026-09-15 ~09:40 IST) — live paper ML + MIX scores (NO_PROMOTE)

```text
From:     teams/04_quant
To:       00 / 06 / 02 / founder
Date:     2026-09-15 ~09:40 IST
Status:   HYPOTHESIS overlay / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: IsolationForest = IF_OUTLIER / WATCH_ONLY — not BUY.
  Embargo 5 hygiene (not CPCV / not OOS). Seed 14.
  ML-002 windows 40/60/90: NIFTY preferred 90 in-sample CANDIDATE
  (half-life description only). BN/SX NOT_MEAN_REVERTING.
  Lean MIX on latest tick: SPOT-ATM EARLY BUY_CE (chain lean);
  IMPULSE/003/006 DI (need ≥40 INDEX 1m lookback on ticket);
  SELL-CREDIT PARKED; PCR overlay ALLOW (not entry).
Rejected: DIVERGE/IF as entry; production_params_written;
  STRAT-015+; treating paper_improved as promote.
HYPOTHESIS (PhD queue): (1) persist dual-tape 1m triples so
  ML-002 scores live window 90; (2) 5m ST/MACD/RSI stay
  confirm-or-kill on any MIX that fires EARLY from chain;
  (3) do not use LTP-clone CE/PE as OPTIDX OHLC for OOS.
VALIDATION: no Supertrend/RSI/MACD series on Dhan charts REST;
  annexure has no EMA_9. Conditional Trigger ≠ FNO series.
```

## As of now (2026-09-15) — ML-001 dual-tape score + embargo (NO_PROMOTE)

```text
From:     teams/04_quant
To:       00 / 06 / 07 / founder
Date:     2026-09-15
Status:   HYPOTHESIS overlay / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: FOLLOW-GAP HOLD on dual-tape score. Embargo 5 = leakage
  hygiene not OOS. Warehouse INDEX/ATM join. Seed 14. MRR 40/60/90 only.
Rejected: DIVERGE as BUY; CPCV claim; live orders; STRAT-015+.
CLI: python -m desk_ml score --underlying NIFTY --source dual-tape
Doc: teams/06_backtesting/docs/SESSION_PREP_ML.md
```

## As of now (2026-09-15) — ML-002 mrr-fit overlay (NO_PROMOTE)

```text
From:     teams/04_quant + packages/desk-ml
To:       00 / 06 / 07 / 09 / founder
Date:     2026-09-15
Status:   HYPOTHESIS overlay / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: ML-002 = OU on MIX-FORM residual + VWMA windows 40/60/90.
  FOLLOW-GAP HOLD. Seed 14 for ML-001 unchanged. Max 3 tweaks.
Rejected: Promote from half-life; live orders; STRAT-015+.
CLI: python -m desk_ml mrr-fit --underlying NIFTY
Doc: teams/06_backtesting/docs/BOOK_MODEL_TUNE.md
```

## As of now (2026-09-14) — ML-001 KMeans+IsolationForest overlay (NO_PROMOTE)

```text
From:     teams/04_quant + packages/desk-ml
To:       00 / 05 / 06 / 07 / 09 / founder
Date:     2026-09-14
Status:   HYPOTHESIS overlay coded / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: KMeans k=4 + IsolationForest on 1m INDEX/CE/PE. Overlay HOLD /
  DIVERGENCE after bar close. Holiday cache fit. KEEP_ALL STRAT-001–014.
Rejected: Live orders; blocking LLM; auto-write MIX params; STRAT-015+.
Artifacts: teams/04_quant/docs/ML_001_LOCAL_PATTERN.md ; packages/desk-ml/
CLI: python -m desk_ml fit --underlying NIFTY
```

## As of now (2026-09-14) — TV-EP CE/PE mapping KEEP_ALL board (NO_PROMOTE)

```text
From:     teams/04_quant (id namespace) + 06 validate
To:       00 / 06 / 09
Date:     2026-09-14
Status:   HYPOTHESIS / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX-TV-EP-001–023 never dropped from the founder board. TV long→BUY_CE,
  TV short→BUY_PE. Customer default still MIX-DEFAULT-BUY / CE-PE buy first.
Rejected: STRAT-015+; equity short as default; promoting WATCH; TV tester clone.
UNKNOWN: OOS+NORMAL; real INDEX/OPTIDX cache.
```

## As of now (2026-09-14) — MIX-TV-EP-001..023 named adapters (NO_PROMOTE)

```text
From:     teams/04_quant (with 01 research + 06 harness)
To:       00 / 06 / 09 / founder
Date:     2026-09-14
Status:   HYPOTHESIS / adapters coded / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Listing 001–023 adapter field = real names (ag_sell … grover_llorens).
  024/025 stay sma_cross / macd_hist calibrators. TV inputs exposed as
  ParamSpec grids. KEEP_ALL STRAT-001–014. No STRAT-015+.
Rejected: Leaving 001–023 as stub; Pine dumps; live orders; customer /.
UNKNOWN: Walk-forward OOS; which partials beat PREMIUM haircut.
```

## As of now (2026-09-14) — MIX-TV-EP factory harness (NO_PROMOTE)

```text
From:     teams/04_quant (id namespace) + 06 harness
To:       00 / 01 / 06 / 09
Date:     2026-09-14
Status:   HYPOTHESIS / factory coded / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Listing 001–023 stay stub. Factory calibrators MIX-TV-EP-024
  sma_cross and MIX-TV-EP-025 macd_hist are PROJECT, not EP cards.
  Customer default unchanged. Paper board only.
Rejected: STRAT-015+; aliasing listing 001/002 to SMA/MACD; promoting WATCH.
UNKNOWN: Which listing EPs are public-rule portable to OPTIDX.
```

## As of now (2026-09-14) — MIX-TV-EP-001..023 Editors’ Picks catalog

```text
From:     teams/04_quant + 01 research
To:       00 / 06 / 09
Date:     2026-09-14
Status:   HYPOTHESIS named MIX rows / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX catalog §22 = 23 current TV Editors’ Picks strategy badges
  as MIX-TV-EP-001 through MIX-TV-EP-023 (listing order). Origin
  WEB-DERIVED / TV-EDITOR-PICK. adapter stub. KEEP_ALL STRAT-001–014.
  MIX-DEFAULT-BUY unchanged. Pine not in git. NEVER_DISCARD test rows.
Rejected: STRAT-015+; aliasing 001/002 to SMA/MACD textbook adapters;
  promoting EP onto /; win rates; live orders; Pine dumps.
UNKNOWN: Historical EP no longer on the live Editors’ list; JS-only extra
  strategy pages; per-chart tester reports; OPTIDX+cost port.
```

## As of now (2026-09-11, 13:54 IST) — Day-split: anti-edge is regime-robust

```text
From:     teams/04_quant (with 06)
To:       00 / 02 / 06 / 09 / founder
Date:     2026-09-11
Status:   VALIDATION measurement (3 days incl. a trend day) / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Day-split runner compared 09-09/09-10 (flat decay) vs 09-11
  (down trend, tilt 1.3-1.8, NIFTY PE +53% midday), ATM + ATM+/-1.
  Signals-minus-drift negative on ALL days/sides/moneyness (-1.9 to
  -3.7%/15m, ~2,800 signals): 1m rising-edge breakout entries buy local
  premium tops in every regime tested. 3m consistently beats 1m. Only
  green cells: PE side + 3m + trend/pullback on falling days (n=3-11),
  where skew tilt was elevated — directional support for
  MIX-ALGO-SKEW-BUY side selection. Negative knowledge promoted to
  design rule: exclude 1m breakout-chasing from future candidates;
  schedule a 3m MIX-DUAL variant in the next 06 grid.
Rejected: Promoting any green cell (small n); treating partial-day
  shell numbers as outcomes; win-rate claims.
UNKNOWN: Whether PE+3m+tilt cells survive more trend days and costs;
  formal IV-entropy HOLD threshold (02/06); EOD full-session rerun.

Artifacts: scripts/run_signal_lab_daysplit.py,
  06 docs/SIGNAL_LAB_2026-09-11.md (addendum),
  data/recon/signal_lab/daysplit_2026-09-11_1354.json
```

## As of now (2026-09-11) — Signal-lab grid: entries anti-edged on decay days

```text
From:     teams/04_quant (with 06)
To:       00 / 02 / 06 / 09 / founder
Date:     2026-09-11
Status:   VALIDATION measurement / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: signal_lab.py grid (founder ask): 1/3/5/10m x 5 gates (incl new
  pullback) x 4 overlays (S/R opening-range, volume-profile POC) on real
  persisted tape 09-09 + 09-10, 3 indices, CE+PE, 1764 signals, next-bar
  entry, 15/30m forward + SL25/TP50 shell. Result: ALL combos negative;
  unconditional drift ~0 but gated entries -3.5%/15m => breakout entries
  bought local tops. dual_full (MIX-DUAL baseline) least bad -3.6% shell;
  every relaxation worse. VP/SR overlays measured harmful on chop days.
  IV entropy ~0.999 on 09-10 = flat-surface decay day: first supporting
  evidence for MIX-ALGO-IV-REGIME-HOLD as the actual improvement lever.
Rejected: Entry tuning on 2 decay days; promoting any combo; deleting
  VP/SR ideas before trend-day tape; win-rate claims.
UNKNOWN: Trend-day behavior (no trending session in tape); ITM tape
  (Dhan token expired 09-11 morning — founder must regenerate before
  live gather resumes); spot joins; costs/fills.

Artifacts: signal_lab.py, tests/test_signal_lab.py,
  scripts/run_signal_lab.py, 06 docs/SIGNAL_LAB_2026-09-11.md,
  data/recon/signal_lab/signal_lab_2026-09-11_0930.json
```

## As of now (2026-09-10) — chain_iv_stats gather landed + live-validated

```text
From:     teams/04_quant
To:       00 / 03 / 06 / 09
Date:     2026-09-10
Status:   CODE + LIVE 5-MIN TICKER (founder-invoked) / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: chain_iv.py parses implied_volatility per strike both sides from
  the documented POST /optionchain payload (desk_intel parse_oc drops it)
  and persists per-snapshot skew_tilt / curvature / normalized IV entropy
  (ATM±5) to data/recon/chain_iv/{UND}_iv_stats_{day}.json (upsert by ts).
  scripts/run_chain_iv_ticker.py ran 5 min live 14:24-14:29 IST at the
  documented >=3s call spacing: 46 snapshots, NIFTY 231/231 strikes with
  IV, BANKNIFTY 359/359, SENSEX 123-125/183 (BSE far wings unquoted).
  Observed: NIFTY tilt 0.50-0.92, BANKNIFTY 0.28-0.73 flat curvature,
  SENSEX tilt 2.0-3.6 with curvature 3+ on its 0DTE chain. 9 new tests.
Rejected: Treating one 5-min window as signal evidence; restarting the
  standing paper loop (founder asked for 5 min only); cross-index tilt
  comparison without tenor normalization; promotes; orders.
UNKNOWN: Nearest-expiry selection mixes tenors (SENSEX 0DTE 09-10,
  NIFTY weekly 09-15, BANKNIFTY monthly 09-29) — 02/06 must decide a
  tenor rule before tilt thresholds mean anything. History depth starts
  today; no Dhan IV backfill. Dead-band width still a backtest grid.

Artifacts: packages/trading_agents_india/src/trading_agents_india/chain_iv.py,
  tests/test_chain_iv.py, scripts/run_chain_iv_ticker.py,
  candidates/MIX-ALGO-SKEW-BUY.md (blocker note updated)
```

## As of now (2026-09-10) — MIX-ALGO-* clubs from marketplace study (NO_PROMOTE)

```text
From:     teams/04_quant
To:       00 / 01 / 03 / 06 / 09
Date:     2026-09-10
Status:   Catalog section 21 added / all UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Four clubs from 01's algos.dhan.co study, WEB-DERIVED concepts
  with PROJECT construction: MIX-ALGO-SKEW-BUY (skew tilt picks CE/PE
  side, premium-tape dual gate confirms entry, dead-band + hysteresis
  mandatory, EOD flat, 40% TSL shell; BACKTEST_REQUIRED, blocked on
  chain_iv_stats gather ticket); MIX-ALGO-IV-REGIME-HOLD (flat IV
  surface + quiet RV => suppress premium buys; WAITING); MIX-ALGO-RR-SHELL
  (exit shells as explicit overlay params; WAITING); MIX-ALGO-CREDIT-PARK
  (seller family parked with India short-vol citations; PARKED). KEEP_ALL
  001-014. No STRAT-015+. Both CE and PE always evaluated.
Rejected: Copying undisclosed SkewHunter params; raw thresholds without
  dead-band; marketplace returns as claims; MIX-DEFAULT-BUY rewrite;
  orders; promoting any MIX-ALGO-* row.
UNKNOWN: Intraday survival of weekly-horizon skew evidence after costs;
  ATM±k / dead-band / momentum-lookback grid (06 owns); IV history depth
  starts only when the gather ticket starts.

Artifacts: docs/MIX_CATALOG.md section 21,
  docs/candidates/MIX-ALGO-SKEW-BUY.md,
  01 docs/DHAN_ALGO_MARKETPLACE_STRATZY.md
```

## As of now (2026-09-10) — MIX-DUAL-INDEX-MASTER (MRR Pine, NO_PROMOTE)

```text
From:     teams/04_quant
To:       00 / 03 / 06 / 09
Date:     2026-09-10
Status:   BACKTEST_REQUIRED / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: PROJECT-DERIVED MIX-DUAL-INDEX-MASTER as current-testing row
  only. SENSEX CALL premium 1m + spot VWAP/EMA21 gate. Pine lives under
  docs/mrr/. Paper-watch records audit/blocker, not customer ticket.
  KEEP_ALL 001–014. No STRAT-015+.
Rejected: Promote measured SENSEX OOS; NIFTY arm (FAIL in cache pass);
  BANKNIFTY until a separate spec; rewrite MIX-DEFAULT-BUY; live orders.
UNKNOWN: Real fills/spread/brokerage; expiry-week walk-forward; same-day
  replay until rolling 1m CALL premium OHLC is persisted.
```

## As of now (2026-09-10) — MIX may only use HQ fields that exist

```text
From:     teams/04_quant
To:       00 / 03 / 06 / 09
Date:     2026-09-10
Status:   VALIDATION note / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Design against DHAN_API_END_TO_END.md. Honest ticket = spot +
  ATM LTP from chain/ltp. SL/TP still HYPOTHESIS. KEEP_ALL 001–014.
  No new STRAT from “we found more APIs.”
Rejected: Fake 3m REST; ScanX RSI as entry; skill iron-condor as default.
UNKNOWN: FUTIDX/OPTIDX candles still not default warehouse.
```

## As of now (2026-09-08) — MIX-LEAN gather ticket (WAITING, NO_PROMOTE)

```text
From:     teams/04_quant
To:       00 / 01 / 02 / 03 / 05 / 06 / 09
Date:     2026-09-08
Status:   WAITING MIX rows + PAPER evaluators
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
Layers:   SOURCE_FACT (INDEX 1m + optionchain_atm when gather works)
          VALIDATION (03 PCR-without-price is not a signal)
          HYPOTHESIS (CE/PE WATCH/EARLY; INDEX proxy ≠ FUTIDX/OPTIDX)

Accepted: MIX-LEAN-SPOT-ATM + MIX-IMPULSE-1M fire WATCH/EARLY from gather;
  empty SL/TP if no ATM LTP; MIX-003/006-INDEX-PROXY WAITING PROXY labeled;
  MIX-PCR-EXTREME-HOLD HOLD overlay (no STRAT delete);
  MIX-SELL-CREDIT-PARK parks 013/014 as non-buy; MIX-DEFAULT-BUY left
  UNVALIDATED customer default; EARLY valid; no CONFIRMED from 5m ST/MACD.
Rejected: Promote; STRAT-015+; STRAT deletes; rewrite DEFAULT-BUY; win rates;
  live orders; invented PCR numeric law.
UNKNOWN / DATA_INSUFFICIENT: FUTIDX/OPTIDX tape still not this path;
  analog EVENT_MEMORY empty; 004 lengths; 010 OF history.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md §20
- packages/trading_agents_india/src/trading_agents_india/lean_mix.py
Next: paper gather can score these MIX rows. Do not promote.
```

Newest first.

---

## As of now (2026-09-08) — Working-path WAITING/PARK (KEEP_ALL)

```text
From:     teams/04_quant
To:       00 / 06 / 09
Date:     2026-09-08
Status:   HYPOTHESIS working-path flags
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX-HAUS-001 + MIX-SCALP-006 working_path WAITING (proxy, not
  INDEX 1m = teacher TF). MIX-CLUB-GR working_path PARKED / paper_watch
  false (not kill). STRAT-001–014 IDs unchanged BACKTEST_BOOK.
Rejected: STRAT-015+; promote; MIX kill; pretend FUT 3m / 2m on INDEX 1m.
UNKNOWN: 004 lengths; 010 OF history.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md
- teams/04_quant/docs/ENGINE_MIX.md
- teams/04_quant/docs/PAPER_WATCH_CLUB_GR.md
```

Newest first.

---

## As of now (2026-09-06) — MIX-TA-MARKET-HOURS PAPER_WATCH

Named ledger MIX for IST market-hours agent poll. Not default. Not promote. Orders refused.

Newest first.

---

```text
From:     teams/04_quant
To:       00 / 05 / 07 / 09
Date:     2026-09-06
Status:   PAPER_WATCH catalog row
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX-TA-MARKET-HOURS (PROJECT_MIX) beside existing MIX-TA-*;
  cites MIX-CLOCK-CAS dead-bands; reasons may cite MIX-DEFAULT-BUY + MIX-TA-*
  as inputs (not silent deletes). KEEP_ALL.
Rejected: Promote; customer_default; live agent orders; STRAT-015+.
UNKNOWN: 15s tick readiness; live OI wall parser.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md §18
- teams/00_orchestrator/docs/PLAN_MARKET_HOURS_PAPER_AGENTS.md
Next: paper ledger only during session; do not swap default ticket.
```

---

## As of now (2026-09-06) — MIX-CF-ANDREA-* + MIX-CF-OMOR-* catalog rows

EXTERNAL Chart Fanatics Phase-10 ASR guests. Separate from prior CF (incl. Fabio). Andrea absorb OF PARKED; Omor KZ/ADR DI; structure proxies BACKTEST_BOOK. Not default.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00
Date:     2026-09-06
Status:   HYPOTHESIS MIX rows catalogued
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX-CF-ANDREA-FAIL-AUCTION + MIX-CF-ANDREA-ORB-ACCEPT +
  MIX-CF-ANDREA-STOP-FADE + MIX-CF-ANDREA-ABSORB (OF PARKED) +
  MIX-CF-OMOR-MMM-FRAME + MIX-CF-OMOR-OTE + MIX-CF-OMOR-PDH-REVERSAL +
  MIX-CF-OMOR-KZ-ADR (DI)
  (separate themes; ASR caveat; Andrea ≠ Fabio; null metrics).
Rejected: Clubbing into Fabio/prior CF/DEFAULT/IQ/STRAT; inventing OF/KZ;
  STRAT-015+.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md §17
- teams/04_quant/docs/candidates/MIX-CF-ANDREA-*.md
- teams/04_quant/docs/candidates/MIX-CF-OMOR-*.md
```

---

## As of now (2026-09-06) — MIX-CF-USMAN-* + MIX-CF-BRANDO-* catalog rows

EXTERNAL Chart Fanatics Phase-9 ASR guests. Separate from prior CF. Usman mostly DI; Brando HTF proxies BACKTEST_BOOK. Not default.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00
Date:     2026-09-06
Status:   HYPOTHESIS MIX rows catalogued
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX-CF-USMAN-OI-STRIKE + MIX-CF-USMAN-0DTE-GAMMA +
  MIX-CF-USMAN-WEEKLY-SIZE + MIX-CF-USMAN-PRICE-STOP (DI) +
  MIX-CF-BRANDO-HTF-RECLAIM + MIX-CF-BRANDO-ROUND-BREAK +
  MIX-CF-BRANDO-HTF-BOUNCE + MIX-CF-BRANDO-SIZE-ZERO (DI) +
  MIX-CF-BRANDO-NEWS-ALIGN (DI)
  (separate themes; ASR caveat; $6k→$10M null metrics; KEEP_ALL stop conflict).
Rejected: Clubbing into prior CF/DEFAULT/IQ/STRAT; inventing OI/greeks/news;
  STRAT-015+.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md §16
- teams/04_quant/docs/candidates/MIX-CF-USMAN-*.md
- teams/04_quant/docs/candidates/MIX-CF-BRANDO-*.md
```

---

## As of now (2026-09-06) — MIX-CF-CARMINE-* + MIX-CF-JADECAP-* catalog rows

EXTERNAL Chart Fanatics Phase-8 ASR guests. Separate from prior CF. Carmine absorb + Jade session-liq DI; structure proxies BACKTEST_BOOK. Not default.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00
Date:     2026-09-06
Status:   HYPOTHESIS MIX rows catalogued
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX-CF-CARMINE-ABSORB (DI/OF PARKED) + MIX-CF-CARMINE-FAIL-BREAK +
  MIX-CF-CARMINE-OPEN-HOLD + MIX-CF-JADECAP-SWING-FAIL +
  MIX-CF-JADECAP-SESSION-LIQ (DI) + MIX-CF-JADECAP-FVG-DRAW
  (separate themes; ASR caveat; payout/dollar P/L null metrics).
Rejected: Clubbing into prior CF/DEFAULT/IQ/STRAT; inventing DOM/Asia boxes;
  STRAT-015+.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md §15
- teams/04_quant/docs/candidates/MIX-CF-CARMINE-*.md
- teams/04_quant/docs/candidates/MIX-CF-JADECAP-*.md
```

---

## As of now (2026-09-06) — MIX-CF-TG-* + MIX-CF-KANE-* catalog rows

EXTERNAL Chart Fanatics Phase-6 ASR guests. Separate from prior CF. Proxies BACKTEST_BOOK. Not default.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00
Date:     2026-09-06
Status:   HYPOTHESIS MIX rows catalogued
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MIX-CF-TG-TRIDENT + MIX-CF-TG-EMA-WAVE + MIX-CF-KANE-EQ50 +
  MIX-CF-KANE-PO3-SMT (separate themes; ASR caveat; title 90% null metrics).
Rejected: Clubbing into Fabio/Marco/Mayne/Marci/Tori/DEFAULT/IQ/STRAT; STRAT-015+.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md §13
- teams/04_quant/docs/candidates/MIX-CF-TG-*.md
- teams/04_quant/docs/candidates/MIX-CF-KANE-*.md
```

---

## As of now (2026-09-06) — MIX-CF-MARCI-* + MIX-CF-TORI-* catalog rows

EXTERNAL Chart Fanatics Phase-5 ASR guests. Separate from Fabio/Marco/Mayne. Proxies BACKTEST_BOOK. Not default.

Newest first.

---

```text
From:     teams/04_quant
To:       00 / 06 / 09
Date:     2026-09-06
Status:   HYPOTHESIS catalog rows added
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Accepted: MIX-CF-MARCI-RIZZY + MIX-CF-MARCI-BB-REALITY + MIX-CF-TORI-TL-BOUNCE +
  MIX-CF-TORI-TL-BREAK (separate themes; ASR caveat).
Rejected: Clubbing into Fabio/Marco/Mayne/STRAT/IQ/DEFAULT; STRAT-015+.
UNKNOWN: Session/instrument transfer; hand TL / thick-line freeze.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md §12
- teams/04_quant/docs/candidates/MIX-CF-MARCI-*.md
- teams/04_quant/docs/candidates/MIX-CF-TORI-*.md
```

---

## As of now (2026-09-06) — MIX-CF-MARCO-* + MIX-CF-MAYNE-* catalog rows

EXTERNAL Chart Fanatics Phase-4 ASR guests. Separate from Fabio. Proxies BACKTEST_BOOK. Not default.

Newest first.

---

```text
From:     teams/04_quant
To:       00 / 06 / 09
Date:     2026-09-06
Status:   HYPOTHESIS catalog rows added
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Accepted: MIX-CF-MARCO-LIQ-TRAP + MIX-CF-MARCO-INT-EXT + MIX-CF-MAYNE-ICT-HTF +
  MIX-CF-MAYNE-BREAKER (separate themes; ASR caveat).
Rejected: Clubbing into Fabio/STRAT/IQ/DEFAULT; STRAT-015+.
UNKNOWN: Session transfer; OB combine freeze.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md §11
- teams/04_quant/docs/candidates/MIX-CF-MARCO-*.md
- teams/04_quant/docs/candidates/MIX-CF-MAYNE-*.md
```

---

## As of now (2026-09-06) — MIX-CF-FABIO-* catalog rows

EXTERNAL Chart Fanatics Fabio books. PARKED on OF. Proxies BACKTEST_BOOK. Not default.


Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00 / 01
Date:     2026-09-06
Status:   MIX catalog §10 added
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Accepted: MIX-CF-FABIO-TREND-NY + MIX-CF-FABIO-MR-RANGE (separate themes).
Rejected: STRAT-015+; merge into MIX-DEFAULT-BUY / IQCapital rows.
UNKNOWN: OF trigger on Dhan; session transfer.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md §10
- teams/04_quant/docs/candidates/MIX-CF-FABIO-TREND-NY.md
- teams/04_quant/docs/candidates/MIX-CF-FABIO-MR-RANGE.md
```

---

## As of now (2026-09-06) — §9 SL/TP MIX + MIX-DESK-IQ-ATR-RR2

Named exit overlays + own PROJECT_MIX from IQCapital harvest. Levels engine method ids. No STRAT-015+. Not customer default.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 05 / 09 / 00
Date:     2026-09-06
Status:   MIX catalog §9 UNVALIDATED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Accepted: MIX-SLTP-ATR-R2, MIX-SLTP-ST-FLIP, MIX-SLTP-PREM-PCT, MIX-SLTP-SWING,
  MIX-DESK-IQ-ATR-RR2, MIX-IQ-GEX-HOLD (PARKED).
Rejected: STRAT-015+; silent STOP_PTS as recipe; promote.
UNKNOWN: GEX NIFTY; swing lookback.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md
- packages/backtest/src/backtest_engine/levels.py
```

---

## As of now (2026-09-06) — MIX-CLUB-GR KEEP + PAPER_WATCH

Optimistic 69.4% stays on the book. After-cost 44.4% FAIL as promote. Paper in market hours in parallel with MIX-DEFAULT-BUY. No live orders.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 07 / 00 / 09
Date:     2026-09-06
Status:   HYPOTHESIS / PAPER_WATCH / KEEP MIX-CLUB-GR
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Named PAPER_WATCH_CLUB_GR.md. Catalog MIX-CLUB-GR paper_watch: true.
Live /ws/signals runs CLUB-GR beside default. Ledger data/recon/paper_watch/.
Do not swap customer default. Do not delete 69% record.

Artifacts:
- teams/04_quant/docs/PAPER_WATCH_CLUB_GR.md
- teams/04_quant/docs/MIX_CATALOG.md
- packages/backtest/src/backtest_engine/live_signals.py
```

---

## As of now (2026-09-06) — honest leftover; default unchanged

06 after-cost: CLUB-GR FAIL. GXR WEAK only. Do not swap MIX-DEFAULT-BUY. No STRAT-015+.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00
Date:     2026-09-06
Status:   HYPOTHESIS / KEEP current
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Frozen club leans rescored. No new MIX IDs. Default MIX-DEFAULT-BUY.
Continuous FUTIDX 003 still DATA_INSUFFICIENT.

Artifacts:
- teams/06_backtesting/docs/BACKTEST_HONEST_2026-09-06.md
```

---

## As of now (2026-09-03) — club/grid MIX named; **no promote**

MIX-CLUB-* and MIX-GRID-RSI named. 06 2y run: CLUB-GR WEAK n=36. Default unchanged.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00
Date:     2026-09-03
Status:   HYPOTHESIS / club+grid named / KEEP current
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Club WEAK survivors; annexure RSI/SMA/MACD from OHLC; nested grids.
Do not swap MIX-DEFAULT-BUY. No STRAT-015+.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md
- teams/06_backtesting/docs/BACKTEST_CLUB_2026-09-03.md
```

---

## As of now (2026-09-03) — MIX-CLOCK-CAS + ML named; scan ran; default unchanged

Founder dead-band overlay and two ML MIX IDs. Metrics still **null** in catalog. 06 clock run is **not** a promote.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00 / 02
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / clock+ML named / KEEP current
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Named MIX-CLOCK-CAS (09:00-09:30 / 15:00-15:30 drop), MIX-ML-LOGIT,
MIX-ML-LOGIT-XR. Catalog metrics null. 06: ML 55% wr FAIL exp. GAP WEAK.
Do not swap MIX-DEFAULT-BUY. No STRAT-015+.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md
- teams/06_backtesting/docs/BACKTEST_SCAN_CLOCK_2026-09-03.md

What the next team must not do:
- Promote 55%. Grid logit. Relabel DHAN-DERIVED. Live orders.
```

---

## As of now (2026-09-03) — WEB/PATTERN scan **ran**; default unchanged

20 scan MIX IDs scored on NIFTY+SENSEX premium. **No promote.** `MIX-DEFAULT-BUY` not edited. No `STRAT-015+`.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00 / 02
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / scan ran / KEEP current
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
WEB/PATTERN MIX catalog §8 ran. ENGULF / INSIDE-BRK NIFTY 730d WEAK only.
GAP NIFTY 5y FAIL. SENSEX all FAIL wr. ORB 09:15–09:30 FAIL. Do not swap
MIX-DEFAULT-BUY. Do not grid candle rules after wr. Origin stays
WEB-DERIVED / PROJECT_MIX.

Artifacts:
- teams/04_quant/docs/MIX_SCAN_2026-09-03.md
- teams/06_backtesting/docs/BACKTEST_SCAN_2026-09-03.md

What the next team must not do:
- Promote. STRAT-015+. Relabel DHAN-DERIVED. Live orders.
```

---

## As of now (2026-09-03) — PROJECT_MIX queued and **FAIL** on premium

MIX-MTF-TREND / MIX-CONFIRM-5M coded and scored. **FAIL**. Default mix unchanged.

Newest first.

---

```text
From:     teams/04_quant
To:       06 / 09 / 00
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / PROJECT_MIX FAIL
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Two PROJECT mixes (Murphy MTF; desk 5m MACD confirm) ran on NIFTY+SENSEX
005 ITM premium. All FAIL. Do not swap MIX-DEFAULT-BUY. No STRAT-015+.

Artifacts:
- teams/04_quant/docs/MIX_PROJECT_2026-09-03.md
- teams/06_backtesting/docs/BACKTEST_PROJECT_2026-09-03.md

What the next team must not do:
- Promote. Grid MACD/ST. Relabel DHAN-DERIVED. Live orders.
```

---

Option-premium MIX books queued. Metrics **UNVALIDATED**. No promote. Default mix unchanged (`MIX-DEFAULT-BUY`, `PROJECT_MIX`). Paper 003/001/006 5y proxy **FAIL**. KEEP_ALL. Not `RESEARCH_READY_FOR_PROGRAMMING`.

Newest first.

---

```text
From:     teams/04_quant
To:       06_backtesting / 02 / 09 / 00
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / KEEP_ALL
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Option-premium MIX books queued: MIX-GOKUL-003-009, MIX-GOKUL-003,
MIX-DEFAULT-BUY, MIX-HAUS-001, MIX-MUKUL-006. Metrics still UNVALIDATED.
No promote. MIX-GOKUL-003-009 = 02 first charter (003 + 009 only;
no 007, no 008). MIX-DEFAULT-BUY stays customer default and PROJECT_MIX
(003 + Himanshu 007 AND Gokul 009 + desk 5m confirm). No STRAT-015+.
KEEP_ALL.

Accepted: Teacher clubs DHAN-DERIVED. Default ticket unchanged.
Rejected: Relabel MIX-DEFAULT-BUY as DHAN-DERIVED. Promote. STRAT-015+.
UNKNOWN: after-cost NORMAL; continuous FUTIDX; SENSEX 2021 gap.

Artifacts:
- teams/04_quant/docs/ENGINE_MIX.md
- teams/04_quant/docs/MIX_CATALOG.md
- teams/01_research/docs/handoffs/TRANSCRIPT_ANALYST.md

What the next team must not do:
- Promote any MIX. Invent win rates. Code live orders. STRAT-015+.

Review: notes ≠ pass
```

---

```text
From:     teams/04_quant
To:       06 / 09 / 00
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / KEEP_ALL / paper subset coded
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
STRAT-003/001/006 + 007/008/009 in packages/backtest. 004/005/010–014 not coded.
5y OOS wr FAIL. Do not freeze 5m INDEX as Gokul. Do not swap default to 001.

Artifacts:
- packages/backtest/src/backtest_engine/algos.py
- teams/06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md

What the next team must not do:
- STRAT-015+. Live orders. Promote FAIL books.

Review: 09 NOTES_ONLY
```

---

```text
From:     teams/04_quant
To:       06_backtesting / 02 / 03 / 09
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / KEEP_ALL
Gate:     Still NOT RESEARCH_READY_FOR_PROGRAMMING

Summary:
Paper/backtest compute path is HQ {1,5,15,25,60} 5m INDEX
(IDX_I; live interval 5 confirmed). Labeled PROJECT vs spoken
STRAT-003 3m FUTIDX. Do not freeze 5m as Gokul. KEEP_ALL — 003
recipe stays. win_rate null. Pointer: packages/backtest
(run_index_5m, all-three count, not option P/L). No STRAT-015+.

Accepted: 5m INDEX as PROJECT proxy; 3m FUTIDX as DHAN-DERIVED book.
Rejected: Relabeling 5m as Gokul; inventing win rates; dropping 003.
UNKNOWN: 3m resample vs FUTIDX history on HQ.

Artifacts:
- teams/04_quant/docs/ALGO_HANDOFF.md (compute-path section)
- teams/04_quant/docs/ENGINE_MIX.md (003 TF vs HQ row)

What the next team must do:
- Keep origin tags. Metrics null. Keep UNVALIDATED.

What the next team must not do:
- Claim 5m INDEX is the spoken 003 TF. Add STRAT-015+. Invent
  win_rate. Code live orders.

Blockers: FUTIDX 3m not in HQ enum.

Review: notes only — not RESEARCH_READY_FOR_PROGRAMMING
```

---

```text
From:     teams/04_quant
To:       06_backtesting / 02 / 03 / 05 / 09
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / KEEP_ALL
Gate:     Still NOT RESEARCH_READY_FOR_PROGRAMMING

Summary:
KEEP_ALL founder policy. Every DHAN-video STRAT is BACKTEST_BOOK.
WAITING/PARKED = not customer default — not deleted. 004/010/011/
012/013/014 stay. Disagreement is a named MIX-* (not STRAT-015+).
Customer default remains MIX-DEFAULT-BUY (PROJECT_MIX). Same-video
Gokul MIX-GOKUL-003 / MIX-GOKUL-CLASS = DHAN-DERIVED. 013/014 are
OPTION_SELLER books (IDs unchanged). 010 PARKED DATA_INSUFFICIENT
but catalogued MIX-OF-010. MIX-CONFLICT-STRIKE = 002 vs 005 vs 006
ablation (CONFLICT). MIX-EQ / MIX-CAS are pointers only. No win
rates. No apps/. No Dhan.

Accepted: STRAT-001–014 all BACKTEST_BOOK; MIX namespace; KEEP_ALL.
Rejected: Vetoing teacher recipes; silent 002-on-003; STRAT-015+;
invented 9/21, fills, lots, win rates.
UNKNOWN: 004 lengths; 010 OF history; CAS-* until 03 writes.

Artifacts:
- teams/04_quant/docs/MIX_CATALOG.md
- teams/04_quant/docs/ENGINE_MIX.md (KEEP_ALL pointer)
- teams/04_quant/docs/MASTER_STRATEGY_PLAN.md (pointer)

What the next team must do:
- Queue MIX IDs on fixtures. Keep metrics null. Keep UNVALIDATED.

What the next team must not do:
- Drop 004/010/013/014/011/012. Add STRAT-015+. Relabel
  PROJECT_MIX as DHAN-DERIVED. Code live. Claim RESEARCH_READY.

Blockers: 09 five-pass not run; 004/010 parked data.

Review: notes only — not RESEARCH_READY_FOR_PROGRAMMING
```

---

```text
From:     teams/04_quant
To:       02_phd_math / 03_phd_market / 05_analysis / 09_review
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / WAITING_FOR_EDIT
Gate:     Still NOT RESEARCH_READY_FOR_PROGRAMMING

Summary:
Rewrote mix + STRAT specs against 01 English SOURCE_FACT bind
(TRANSCRIPT_STRATEGY_BIND.md). Do not claim a single Dhan recipe
no video taught. Same-video Gokul 003/004/005/008/009 stays
DHAN-DERIVED. Default 003+007+009 AND and 5m MACD confirm-or-kill
stay PROJECT_MIX. 002 never overlays 003. 011 index use
PROJECT_MIX; gA5 fill was a sell. 004 lengths NOT_IN_EN.
Supertrend 10,3 is WEAK ("103"), not spoken "ten comma three."
Guests: Gokul spoken SEBI RA; Himanshu "star trader" not spoken
SEBI RA — education ≠ edge. 013/014 WAITING sell. No STRAT-015+.
Metrics null. No apps/. No Dhan.

Accepted: English bind wins; 14 IDs; 002 vs 005 split; 012 four
patterns named (WAITING = rule-detail); 006 VIX>15–16 condition.
Rejected: 2h HAUS parent; 002-on-003; gA5 bull-put → buy CE;
invented 004 lengths; blanket 006 beginner ban; SEBI RA as edge.
UNKNOWN: 004 lengths; 010 OF history; 103 digits; 006 delta.

Artifacts:
- teams/04_quant/docs/ENGINE_MIX.md (Transcript bind section)
- teams/04_quant/docs/candidates/STRAT-001,002,003,004,006,011,012
- teams/04_quant/docs/candidates/STRAT-013,014 (WAITING sell headers)

What the next team must do:
- Keep PROJECT_MIX labeled. Sign or reject. Keep UNVALIDATED.

What the next team must not do:
- Relabel PROJECT_MIX as DHAN-DERIVED. Add STRAT-015+. Invent
  win rates/fills/9/21. Implement apps/. Call Dhan. Issue
  RESEARCH_READY_FOR_PROGRAMMING.

Blockers: 09 five-pass not run; 004/010 parked.

Review: notes only — not RESEARCH_READY_FOR_PROGRAMMING
```

---

```text
From:     teams/04_quant
To:       02_phd_math / 03_phd_market / 05_analysis / 09_review
          (06_backtesting later — fixtures only)
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / WAITING_FOR_EDIT
Gate:     Still NOT RESEARCH_READY_FOR_PROGRAMMING

Summary:
Froze Phase-1 engine mix of the existing 14 STRATs. Not soup: one
primary + filters + confirm/kill + optional overlay per ticket.
Default BULL/BEAR primary = STRAT-003 (DHAN-DERIVED 2RnBT9) + 005
strike; 001/011/006 are alt primaries, never same ticket. SIDEWAYS =
no-trade (003 ST≠VWAP, 008 mixed, 009 clock, news veto). 013/014
WAITING sell — not in buy mix. 010 OF PARKED DATA_INSUFFICIENT.
Conflicts left standing: 002 vs 005 vs 006 strike; HAUS MACD entry
vs staging 5m confirm-or-kill; 003 3m vs HQ {1,5,15,25,60};
Supertrend 10,3 vs _byuht 7,3 (equity — not imported). Metrics null.
No win rates. No apps/. No Dhan.

Accepted: 14 IDs only; futures OHLC; chain 3m; news as veto;
staging WATCH→EARLY→CONFIRMED (EARLY ≠ fill).
Rejected: indicator soup; one true Dhan strike; invented 004
lengths; 7,3 on index; 013/014 as buy UI.
UNKNOWN / DATA_INSUFFICIENT: 004 EMA lengths; 010 OF history;
3m/2m resample; MACD ×3 vs ×4; HAUS 100 vs 300.

Artifacts:
- teams/04_quant/docs/ENGINE_MIX.md
- teams/04_quant/docs/MASTER_STRATEGY_PLAN.md (banner pointer)

What the next team must do:
- 02/03/05/09: sign or reject ENGINE_MIX §7. Keep UNVALIDATED.
- 06: do not code live; fixtures only after 09 notes (notes ≠ pass).

What the next team must not do:
- Add STRAT-015+. Invent win rates/fills. Merge 002+005. Import
  _byuht 7,3 into index. Implement apps/. Call Dhan. Claim
  RESEARCH_READY_FOR_PROGRAMMING.

Blockers: 09 five-pass not run; 004/010 parked; F&O 15:40 VERIFY.

Review: notes only — not RESEARCH_READY_FOR_PROGRAMMING
```

---

```text
From:     teams/01_research + 00_orchestrator
To:       teams/04_quant
Date:     2026-09-03
Status:   INFORMED / EQ-014 + SO-003 added UNVALIDATED / 14 STRATs unchanged
Gate:     other-book only — do not code

Summary:
Equity English second pass. New HYPOTHESIS slots EQ-014 (dEv
5y ATH breakout) and SO-003 (G31 F&O BTST + stock option).
Keep them out of MASTER_STRATEGY_PLAN. No STRAT-015+.

Artifacts:
- teams/04_quant/docs/candidates/EQUITY_ETF_BACKLOG.md
- teams/01_research/docs/handoffs/dEvF8biE02M.md
- teams/01_research/docs/handoffs/G31RFueZLvk.md

What the next team must do:
- Keep 14 IDs UNVALIDATED. Do not mix EQ/SO into index blotter.

What the next team must not do:
- Implement strategies. Invent win rates. Copy 100%/2y or
  Hull-32 “backtest” as evidence.

Blockers: catalog STOCK_ONLY no EN; no engine.

Review: notes only — not RESEARCH_READY_FOR_PROGRAMMING
```

---

```text
From:     teams/00_orchestrator
To:       teams/04_quant
Date:     2026-09-03
Status:   INFORMED / coalition IN_PROGRESS / 14 STRATs remain UNVALIDATED
Gate:     ALGO_HANDOFF is shape only — do not code

Summary:
Coalition banner on MASTER_STRATEGY_PLAN. Packets merge as pointers.
Equity/ETF placeholders are a separate book (EQ-*/SO-*/ETF-*), not STRAT-015+.
Wrote ALGO_HANDOFF.md YAML fields (regime, OHLC vs chain vs news, origin tags).

Artifacts:
- teams/04_quant/docs/ALGO_HANDOFF.md
- teams/04_quant/docs/MASTER_STRATEGY_PLAN.md
- teams/00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md

What the next team must do:
- Keep 14 IDs UNVALIDATED. Merge only after 02+03 tag VALIDATION.

What the next team must not do:
- Implement strategies. Invent win rates. Mix equity into index book.

Blockers: packets on disk; 09 notes only; still UNVALIDATED.

Review: notes only — not RESEARCH_READY_FOR_PROGRAMMING
```

---

```text
From:     teams/00_orchestrator
To:       teams/04_quant
Date:     2026-09-01
Status:   INFORMED / 14 STRATs remain DRAFT / SIGNAL_STAGING UNVALIDATED
Gate:     Do not invent win rates or extra STRATs

Summary:
CUSTOMER vs ENGINE note on MASTER_STRATEGY_PLAN: UI never shows indicator soup;
engine mix of bull/bear/sideways candidates is UNVALIDATED until backtest.
SIGNAL_STAGING adds IN-PROGRESS after CONFIRMED while the ticket is live, then
ACHIEVED/STOPPED/INVALIDATED. 14 candidates are DRAFT; 06 owns mix-and-match;
PhD nightly recon retunes as UNVALIDATED suggestions only.

Artifacts:
- teams/04_quant/docs/MASTER_STRATEGY_PLAN.md (CUSTOMER vs ENGINE)
- teams/04_quant/docs/SIGNAL_STAGING.md (IN-PROGRESS)
- teams/00_orchestrator/docs/TASK_CUSTOMER_DESK.md

What the next team must do:
- Keep UNVALIDATED. Do not add STRAT-015+ to look complete.

What the next team must not do:
- Invent win rates. Implement live staged math. Call Dhan.

Blockers: live DHAN_* TODO; mix-and-match not backtested.

Review: five-pass pending
```

---

```text
From:     teams/00_orchestrator
To:       teams/04_quant
Date:     2026-09-01
Status:   INFORMED / SIGNAL_STAGING still UNVALIDATED
Gate:     Nightly handoff path — do not retune from mock UI

Summary:
Paper desk added INVALIDATED (reversal after EARLY) and ACHIEVED (target).
STOPPED/LOST/EXPIRED wired. Prerequisite: nightly HYPOTHESIS + outcome packet
to 06; do not change STRAT-* from mock ACHIEVED. Keep WAITING_FOR_EDIT.

Artifacts:
- apps/web/public/mock/signal.json
- teams/04_quant/docs/SIGNAL_STAGING.md

What the next team must do:
- Keep UNVALIDATED. Map EXPIRED/VETOED already in spec; outcomes are UI labels.

What the next team must not do:
- Implement live staged math. Claim 1-minute omniscience. Call Dhan.

Blockers: live DHAN_* TODO; jobs/recon not built.

Review: five-pass pending
```

---

```text
From:     teams/04_quant
To:       06_backtesting / 02_phd_math / 08_testing
Date:     2026-09-01
Status:   HYPOTHESIS / UNVALIDATED / WAITING_FOR_EDIT
Gate:     Still NOT RESEARCH_READY_FOR_PROGRAMMING

Summary:
SIGNAL_STAGING.md now documents terminal outcomes (ACHIEVED/STOPPED/INVALIDATED/
EXPIRED/LOST/COMPLETED/SHADOW_CLOSED) so CONFIRMED cannot stay live after lunch.
Paper daily + pre-prod via desk_intel nightly — do not rewrite live strategy.

Artifacts:
- teams/04_quant/docs/SIGNAL_STAGING.md (outcomes section)
- teams/00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md

What the next team must do:
- Keep UNVALIDATED. Consume nightly JSON later. No 1-minute omniscience.

What the next team must not do:
- Treat recon param hints as validated. Place orders.

Blockers: same packet; F&O close VERIFY.

Review: five-pass pending
```

---

```text
From:     teams/04_quant
To:       09_review / 06_backtesting (later) / 07_coding (blocked)
Date:     2026-09-01
Status:   HYPOTHESIS / UNVALIDATED / WAITING_FOR_EDIT
Gate:     Still NOT RESEARCH_READY_FOR_PROGRAMMING

Summary:
Wrote SIGNAL_STAGING.md: WATCH/EARLY/CONFIRMED/EXPIRED/VETOED, color spec,
mix-and-match (impulse/range/OI/news lead; 5m ST/MACD confirm or kill).
~1m EARLY lead is a target not a guarantee. EMA_9 not in annexure; ST/RSI/MACD/EMA9
series computed from OHLC later — not this ticket. No live math.

Artifacts:
- teams/04_quant/docs/SIGNAL_STAGING.md
- teams/04_quant/docs/MASTER_STRATEGY_PLAN.md (pointer)

What the next team must do:
- Keep UNVALIDATED. Leave WAITING_FOR_EDIT.

What the next team must not do:
- Implement staged signals as live. Claim 1-minute omniscience. Invent REST fields.

Blockers: same as v0.1 packet; live DHAN_* TODO on orchestrator ticket.

Review: five-pass pending
```

---

```text
From:     teams/04_quant
To:       02_phd_math / 06_backtesting (later)
Date:     2026-09-01
Status:   HYPOTHESIS / UNVALIDATED / topic files now cite official Dhan defs
Gate:     Still NOT RESEARCH_READY_FOR_PROGRAMMING

Summary:
Clubbed official indicator catalog into MASTER_STRATEGY_PLAN and every topics/*.md.
RSI is API-named RSI_14 (triggers only). Supertrend/VWAP series remain chart-only.

Artifacts:
- teams/04_quant/docs/MASTER_STRATEGY_PLAN.md
- teams/04_quant/docs/topics/*.md

What the next team must do:
- Keep STRAT-* UNVALIDATED. 3m/2m bars are resample hypotheses (not HQ intervals).

What the next team must not do:
- Invent REST indicator fields. Live-trade. Implement apps/.

Blockers: same as v0.1 packet.

Review: five-pass pending
```

---

```text
From:     teams/04_quant
To:       teams/06_backtesting (later) and teams/09_review (notes only)
Date:     2026-08-30
Status:   HYPOTHESIS / UNVALIDATED / DRAFT v0.1
Gate:     Strategy spec DRAFT — NOT RESEARCH_READY_FOR_PROGRAMMING

Summary:
Merged 01–03 into 12 Phase-1-relevant candidates + 2 WAITING sell specs.
Primary buy systems: STRAT-001 (HAUS dual-TF) and STRAT-003 (Gokul 3m futures).
Filters 007–009; overlays 002/004/005/010/012. No P&L claimed. No Python strategies.

Artifacts:
- teams/04_quant/docs/MASTER_STRATEGY_PLAN.md
- teams/04_quant/docs/candidates/STRAT-001.md … STRAT-014.md

What the next team must do:
- 06: engine with costs, no look-ahead, date-stamped lots — when scheduled.
- 09: open issues only (KEEP_ALL_REVIEW / COALITION_REVIEW). Do not pass.

What the next team must not do:
- Implement in apps/ or packages/.
- Code 013–014 as buy signals.
- Hardcode lots/expiry.
- Optimize on the test set.

Blockers: English transcripts; timedtext 429; order-flow history; Super Scalper EMA lengths.

Review: five-pass pending
```
