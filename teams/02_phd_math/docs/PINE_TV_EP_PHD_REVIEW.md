# 02 VALIDATION — TV-EP adapters vs Pine MRR (VWMA) vs MIX-DUAL

**Date:** 2026-09-14  
**Layer:** `VALIDATION` (code tweaks are paper-only overlays; they do not promote).  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE.** No live orders.  
**Books:** Kakushadze *151* (taxonomy / KEEP_ALL drawer); AFML (purged labels, no same-bar leak); Tulchinsky (one expression, one gate); Bouchaud (costs eat listed “edges”); desk playbook `book_kb/08_EXAM_DESK_PLAYBOOK.md`.  
**Must-load:** `SKILL.md`, `PRO_QUANT_AGENT_PROMPT.md`, dual-tape, `MIX-FORM-*`, ML-002.  
**KEEP_ALL:** STRAT-001–014 stay `BACKTEST_BOOK`. MIX-DUAL is not customer default.

---

## Claim

Founder coded (1) TradingView Editors’ Picks as `MIX-TV-EP-*` Python ports, (2) Pine MRR as VWMA on premium / residual (ML-002), (3) `MIX-DUAL-INDEX-MASTER` as index lean + CALL-premium confluence. Question: what is **backtestable without live orders**, and what should we keep / change / kill.

---

## Layer

`SOURCE_FACT` — TV public rules (ports, not Pine paste); HQ has no Supertrend/RSI/MACD series REST; rolling ATM tape is not a fixed contract.  
`VALIDATION` — this note.  
`HYPOTHESIS` — MIX-TV-EP, ML-002, MIX-DUAL remain `BACKTEST_REQUIRED` / `UNVALIDATED`.

---

## Verdict

| Family | Verdict | One line |
|--------|---------|----------|
| TV-EP adapters `MIX-TV-EP-001`–`023` | `partially_supported` | Keep as a **151-style drawer**. Most equity/FX cards are not option math. Factory + next-bar-open sim is the honest test. |
| Pine MRR / ML-002 VWMA+OU | `context-dependent` | VWMA(MRR) is a **filter**, not an entry. OU half-life is a snap-back metaphor, not vega. Overlay HOLD is the product. |
| `MIX-DUAL-INDEX-MASTER` | `unsupported` as a promote; `partially_supported` as a **strict paper filter** | Dual-gate idea is right. Stacked 1m Supertrend/EMA/volume on CALL is indicator soup + same-bar confluence. NIFTY arm already FAIL in shadow book. **Do not promote.** |

---

## Math / stats reason

### Dual-gate (index lean + premium confirm)

Oral rule (`08_EXAM_DESK_PLAYBOOK`): **lead on index, confirm on CE/PE, skip on FOLLOW-GAP**. That is the only structure that survives 151-style lists.

- Index-only TV-EP / INDEX proxy P/L is **not** option expectancy (02 already: proxy FAIL).
- Premium-only Pine (close > VWMA20 + VWAP + ST + EMA9>21 + volume) **omits** the index last-bar lean. That is one-tape confirmation of itself.
- FOLLOW-GAP is the cheap dual-tape veto: `idx↓ & r_PE≤0` or `idx↑ & r_CE≤0`. Do not buy the option because the index printed.

### AFML leakage (what was wrong, what we changed)

| Leak | Where | Status |
|------|--------|--------|
| z includes current residual in the window | `mix_form_diverge_z`, ML-002 `rolling_z` | **Changed:** history-only z. Current ε is the score. |
| Full-sample OLS `k` on the same tape used to decide | `apply_named_formulas`, `mrr_fit_underlying` | **EDA / fit report only.** Paper overlay now uses **expanding `k` before the decision bar**. Fit JSON still in-sample — do not promote from it. |
| Signal-close entry on the bar that made the lean | TV-EP `paper_tune` | **Changed:** fill = **next bar open**, mark next close. Matches `simulate.simulate_leans` and the MRR shadow harness note. |
| Overlapping 1m labels | all three families | **Unchanged risk.** One session / walk-forward without embargo is not SCORE_SAMPLE. NEWS_CALENDAR empty → `DATA_INSUFFICIENT` for promote. |
| Rolling ATM strike follow | `premium_tape` | **Unchanged.** Replay is not one OPTIDX sid. 06 must not treat ATM JSON as a continuous contract. |

Kakushadze-151 mapping: Editors’ Picks are a **taxonomy**. Coding 23 Super Orders is the exam trap. Premium `TESTED_FAIL` after 1% RT is the **expected** Bouchaud outcome, not a catalog delete.

### Fills and costs (backtestable now)

| Path | Fill | Cost | Honest use |
|------|------|------|------------|
| `simulate_leans` (TV-EP grid) | next bar **open** | PREMIUM: 1% each way on entry+exit (`costs.DEFAULT_COST`). INDEX: **no** option haircut | INDEX = points proxy. PREMIUM = one cached OPTIDX. |
| TV-EP `paper_tune` | next bar **open**, mark that bar’s close | 1% × (\|entry\|+\|exit\|) | One-session search only. `keep_current_strategy: true`. |
| MIX-DUAL `dual_master_gate` | **no fill** (last-bar booleans) | none | Paper-watch observation. Not a P/L model. |
| MRR shadow `scripts/backtest_mrr.py` | next bar open (doc) | **gross** in the 2026-09-10 report | After-cost still required before any WATCH→promote talk. |

Statutory brokerage/STT remain `UNKNOWN`. Hypothesis 1% RT is a **conservative band**, not a tick table.

### ML-002 |z| HOLD (cheap overlay — landed)

`Z_HOLD = 2.0` already existed on the ML-002 fit path. It was **not** wired into TV-EP paper tickets.

Paper tuner now HOLDs a new CE/PE when:

1. dealer `PREMIUM_DIVERGENCE`, or  
2. `MIX-FORM-FOLLOW-GAP`, or  
3. causal residual \|z\| ≥ 2 (expanding k).

This is **meta-label skip** (AFML), not a new MIX and not STRAT-015.

MIX-DUAL SENSEX path now HOLDs CALL when last-bar index is down, or index is up and CALL did not follow. Missing two bars → HOLD (no BUY_CE without confirm).

---

## Keep / change / kill

### TV-EP adapters

| ID / class | Action | Why |
|------------|--------|-----|
| Factory + board + KEEP_ALL 001–023 | **KEEP** | 151 drawer. Status PARK/FAIL/DI stays on the board. |
| Ports that are MA/MACD/pivot/oscillator on OHLC | **KEEP** (test) | Implementable from bars. Dual-gate + costs required on PREMIUM. |
| `csv_replay`, harvest-calendar `ag_sell`, TQQQ `one_pct_week` | **CHANGE** (park for NSE options) | Recipe is not NIFTY CE/PE. Leave ported for honesty; do not shortlist. |
| `macd_martingale`, grid/qty/money-management cards | **KILL as entry** (keep row) | Martingale/grid is not CE/PE buy-first. Adapter may exist; never customer `/`. |
| TV SL/TP/commission fields on adapters | **KILL as Dhan fields** | HYPOTHESIS notes only. |
| INDEX-tape “win” without PREMIUM | **KILL as evidence** | Proxy ≠ premium. |
| Paper tuner 3-tweaks/day + RETUNE_GATE | **KEEP** | Bounded search. One-day P/L is not OOS. |
| Factory 5m ST/MACD as **entry** | **KILL** | Staging: confirm-or-kill only. |

### Pine MRR (VWMA)

| Piece | Action | Why |
|-------|--------|-----|
| VWMA as **confirm/kill** vs premium close | **KEEP** | Named MRR. Volume=0 → equal-weight (already coded). |
| ML-002 OU on residual + windows 40/60/90 | **KEEP** (fit only) | Max 3 tweaks. `production_params_written: false`. |
| OU half-life as a trade / vega | **KILL** | Metaphor. Not IV. |
| \|z\| ≥ 2 HOLD overlay | **KEEP** (now on paper tuner) | Cheap skip. |
| Full-sample preferred-window picker | **CHANGE** | In-sample min half-life is a beauty contest. 06: embargoed walk-forward on **one** frozen window. |
| Pine copies as live strategy | **KILL** | Indicators ≠ Super Order. |

### MIX-DUAL

| Piece | Action | Why |
|-------|--------|-----|
| Dual-gate *idea* (spot lean + premium confirm + FOLLOW-GAP) | **KEEP** (research) | Matches the oral. |
| Promote / `MIX-DEFAULT-BUY` rewrite | **KILL** | Explicit founder + 00 rule. |
| NIFTY arm | **KEEP PARKED** | Shadow OOS expectancy negative. |
| BANKNIFTY | **KEEP out of spec** | No dual-index rule. |
| SENSEX paper-watch with tape | **CHANGE** | Last-bar AND of MRR/VWAP/ST/EMA9/vol/time is **confluence overfitting**. Next 06 grid: **ablate** to (spot VWAP/EMA **or** index last-bar lean) + (premium VWMA **or** FOLLOW-GAP) only. |
| 1m Supertrend as entry | **CHANGE → confirm-or-kill** | `SIGNAL_STAGING`. |
| Shadow wr / expectancy in `lean_mix` provenance | **CHANGE** | Numbers are **not** a claim; still look like a win rate on the ticket. Prefer pointer to the md only. |
| CALL-only book | **CHANGE** | PE gate unwritten. Do not invent PE Supertrend. HOLD CALL on idx↓ is the cheap PE-less rule (landed). |

---

## What changes next

1. 06: TV-EP PREMIUM grid **with** `allow_entry` from FOLLOW-GAP + \|z\| (needs aligned INDEX+CE+PE, not one OPTIDX). INDEX cells stay proxy.  
2. 06: MIX-DUAL ablation (2–3 conditions, not 6) + **after-cost** + embargo; SCORE_SAMPLE = NORMAL only.  
3. 04: do not add STRAT-015+ from leftover Pine scripts. Extra clubs stay `MIX-*`.  
4. 03: rolling ATM vs fixed sid — label every premium replay.

---

## Backtest request to 06

```text
GRID: MIX-TV-EP shortlist 005/010/016 + MIX-DEFAULT-BUY paper proxy
  tape = aligned INDEX 1m + ATM CE + ATM PE (same ts)
  entry = lean AND NOT FOLLOW-GAP AND NOT |z|≥2
  fill = next_bar_open; exit = next_bar_open of flatten OR 1-bar mark
  cost = HYPOTHESIS 1% RT; statutory UNKNOWN
  split = purged/embargo by session; drop NEWS_DAY/EXPIRY from SCORE_SAMPLE

ABLATION: MIX-DUAL SENSEX CALL
  A = spot>VWAP & spot>EMA21
  B = premium close > VWMA20
  C = FOLLOW-GAP HOLD
  Compare A+B+C vs current 6-way AND. After-cost. NO_PROMOTE.

Do not kill STRAT-001–014. Do not promote MIX-DUAL.
```

---

## Cheap code landed this ticket (paper only)

- Causal `mix_form_diverge_z` + ML-002 `rolling_z` (exclude current).  
- TV-EP `causal_overlay_block` + next-bar-open fill + two-sided 1% haircut.  
- MIX-DUAL `_call_side_follow_gap` before `BUY_CE`.  
- Tests: `test_tv_ep_paper_tune`, `test_ml002`, `test_lean_mix`, `test_index_ce_pe_formulas`.

Not changed: STRAT catalog, customer `/`, live orders, MIX-DUAL promote flag.

---

## UNKNOWN / DATA_INSUFFICIENT

- Statutory costs; true bid/ask at next open.  
- ATM-tape ∩ INDEX after 2026-09-03.  
- Continuous IV / HQ greeks (null).  
- Whether OU is mean-reverting **OOS** on residual (fit is in-sample).  
- Counsel LLM: one pass only if keys exist; models do not generate the ticket.

---

## HANDOFF

```text
From:     teams/02_phd_math
To:       00 / 04 / 06 / 09 / founder
Date:     2026-09-14
Status:   VALIDATION + cheap paper overlays / UNVALIDATED / NO_PROMOTE
Accepted: KEEP TV-EP drawer; KEEP MRR as filter; KEEP dual-gate idea;
  HOLD FOLLOW-GAP + |z|≥2; next-bar-open + 1% RT; causal z.
Rejected: Promote MIX-DUAL; delete STRAT-001–014; Pine as Super Order;
  INDEX proxy as option P/L; OU as vega; 151 live tournament.
UNKNOWN: statutory costs; ATM∩INDEX depth; OOS OU.
```

## Counsel (one pass)

Provider `gemini` / `ONE_ONLY`. REVIEW only. Not a promote.

```text
AGREE with 02 verdict under PAPER NO_PROMOTE constraints.
KEEP: STRAT-001-014, TV-EP drawer, MRR=filter, and FOLLOW-GAP+|z| HOLD (next-bar-open causal z).
KILL: MIX-DUAL and DUAL promote.
DATA_INSUFFICIENT for exact win rates (PAPER only).
Apply 1% RT hypothesis costs; note INDEX proxy != premium.
No live orders.
```

