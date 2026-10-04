# Round 9 — improvement sprint (paper-only NIFTY option buyer)

**Status:** HYPOTHESIS / PAPER / **NO_PROMOTE**.  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`.  
Playbook stays `enabled: false`. `config/v2/exits/defaults.yaml` is not touched.  
Legacy `CANCEL_AGAINST` / `COVER_LONG_UNWIND` are comparison/tapes only — never the design base.

Founder index: [`SUMMARY.md`](SUMMARY.md).

---

## 0. Sources, layers, frozen holdout

| Layer | What | Path / URL |
|-------|------|------------|
| SOURCE_FACT (this checkout) | V2 default exits = house ₹30k + native invalidation; other primitives off | `config/v2/exits/defaults.yaml` |
| SOURCE_FACT (this checkout) | 2026-09-25 paper book + last-20 closed tickets + 22 cancel-reason rows | `teams/06_backtesting/docs/ML_PAPER_DASHBOARD.md` |
| SOURCE_FACT (this checkout) | ML-001/002 are overlays, not buy engines; 2-day holiday fit | `teams/04_quant/docs/ML_001_LOCAL_PATTERN.md`, `teams/06_backtesting/docs/BOOK_MODEL_TUNE.md` |
| SOURCE_FACT (this checkout) | FWD-BAR coded: n=30 gross-kill, n=60 halves, n=120 t≥2.13 | `packages/strategies/src/strategies/forward/bars.py` |
| VALIDATION (other branch, cited) | Exit Lab 3b: 0/654 pass; 3,546 hist / 419 live; 12 folds; 5,000 look-ahead | [PR #69](https://github.com/sahilTayde/all_about_dhan/pull/69) `docs/research/exit_lab/ROUND3.md` |
| VALIDATION (merged) | Round 8: 120 buyer variants all lost; p* 55–60%; BRK-BUY closed | `docs/research/ROUND8_STRATEGY_REDESIGN.md` |
| VALIDATION (merged) | SSRN/arXiv harvest: 51 papers, 32 codable; IDs are `P01`… not H18 | `docs/research/SSRN_HARVEST.md` |
| FOUNDER-STATED (not in this tree) | Harvest leads H18 / S07 / H22 / H19 failed deep1 OOS bars; `HOLDOUT_SPEC` frozen | No file named `HOLDOUT_SPEC`. No H18/S07/H22/H19 rows in `ssrn_harvest.json`. Treat as burned. Do not invent their P/L. |
| DATA_INSUFFICIENT | last3d parquets, dual-tape sqlite, bid/ask book, primary deep1 harvest tables | This cloud workspace has none of those files |

**Operating holdout (frozen — do not retune).** There is no `HOLDOUT_SPEC.md` on `main` or on PR #69. The contract already hashed in-repo is:

1. **Exit Lab 3b live holdout** = the 12 dual-tape days already used (419 entries: random 278 / v2_boss 60 / legacy 81). Rank on **1-lot**. Report the three sets separately. Do not mix as-traded lots.
2. **Hist** = last3d 154-expiry files when attached (3,546 entries / 750,079 min / 149 weeks). Expanding **12** expiry-week folds. Last3d is expiry-week only; hist `normal` stays `DATA_INSUFFICIENT`.
3. **Entry FWD** = Round 8 FWD-BAR in `bars.py` (n=30 gross-kill, n=60 both halves net>0, n=120 day-clustered t≥2.13 + stress). Sep 2025–Jul 2026 chain is burned.
4. **DSR** = Φ((SR−SR*)/se) in [0, 1] with N = cumulative variants (654 already, plus every new Oct 10 cell).
5. **Costs** = V2 half-spread (ATM 0.20 / ITM100 0.35 / ITM200 0.55) + founder charges; always publish ×2 stress.
6. Harvest IDs H18/S07/H22/H19 stay off this holdout. A retest, if ever, is FWD-only after the founder points at the original spec file.

A bug-fix that changes labels, fills, or the holdout split **restarts the count**.

---

## 1. Prioritized improvement steps

Priority is **drain first, then models that do not pick a wing, then entries that can pay cost**. Each step has a protocol, a pass bar, and a falsifier. None of these write production params.

### Shared validation protocol (every step)

Run only on paper/replay. No peeking.

1. **Lock features before the minute.** Features at bar `i` use `minutes[:i]` only (entry strike `strike_ltp`; missing strike = hole). Labels may use hindsight. Labels are never columns.
2. **Look-ahead test.** 5,000 random minutes: `features_before(i)` vs a rotated tail. **0 mismatches** required (PR #69 already 5,000/5,000).
3. **Label permutation.** Shuffle `GOOD_EXIT` **within day**, remine on train only. If the named pair is still #1 or lift stays ≥ 1.10, the rule is clock/leak — **kill**.
4. **Train / test.** Expanding 12 expiry-week folds on last3d when attached. Thresholds and pair cuts fit on **train only**.
5. **Live rank.** Random 1-lot first. Then v2_boss 1-lot. Then legacy 1-lot. Never mix as-traded ₹.
6. **Costs.** Base V2 half-spread and ×2. Kill if ×2 flips the sign vs hold.
7. **Legacy overlap.** Count same-moment fires vs `CANCEL_AGAINST` / `COVER_LONG_UNWIND` (±180 s). Kill if overlap share of 1-lot gain ≥ 0.30.
8. **Slices.** CE/PE, trend/chop, expiry-day vs normal. Hist `normal` is `DATA_INSUFFICIENT` on last3d.
9. **Params.** ≤ 4 tunables per `PlanSpec`. Every cell counts toward DSR N.
10. **Playbook / defaults.** Off. A pass goes to 09 five-pass, not to `defaults.yaml`.

### 1a. Exits (P0 — the drain)

| # | Step | Why this, not something else | Protocol (exact) | Pass bar | What falsifies it |
|---|------|------------------------------|------------------|----------|-------------------|
| E0 | Keep V2 defaults. Do not re-enable tight cancels. | Round 11 + PR #69: no tested exit passed. `time_edge` / `atr_opt` / `shape_exit` reprint `CANCEL_AGAINST`. | Diff `config/v2/exits/defaults.yaml` against this commit. Grep `packages/oms` for `CANCEL_AGAINST` / `COVER_LONG_UNWIND` must stay empty. | File hash unchanged. Playbook `enabled: false`. | Any silent default edit, or a playbook enable without 09 pass. |
| E1 | Oct 10 non-clock cells only (X1–X4 in §3). | Clock lift 1.212 is theta. Path combos are the only unused residual. | §3 command. Clock feature ban list. Rank random 1-lot. | CI_lo > 0 on random 1-lot **and** DSR ≥ 0.9 **and** ≥ 8/12 folds beat hold **and** overlap share < 0.30 **and** ×2 still beats hold. | CI_lo ≤ 0 (this is `peak_hazard_p10` today). Label-perm remine still names clock. Overlap ≥ 0.30. |
| E2 | Score **hold-to-15:15 vs native invalidation only** on new dual-tape days (shadow). | V2 default already equals hold on 1-lot random (−₹82,565). Need a **normal-week** (non-last3d) measurement. | Nightly shadow: each new paper fill, price (a) hold to 15:15, (b) strategy invalidation, (c) ₹30k house stop. 1-lot. | After 60 new random-like fills: (b) or (c) has CI_lo > 0 vs (a). | After 60 fills, neither beats hold, or only expiry-days are green. |
| E3 | Do **not** ship clock-profit T=45. | T=45 is the only clock-profit green on random (+₹10,063) and v2, but CI_lo −₹70,103. Last3d is expiry-week theta. | If someone reruns T, report it as a diagnostic, not a candidate. | None. Closed. | Treating T=45 as an edge. |
| E4 | Label every paper close GOOD / BAD / HOLE on the **entry strike**. | 2026-09-25 dashboard is as-traded lots and mixed reasons. Need 1-lot path labels for E1. | §2.2 steps 1–6. Window = 15 min + EOD. Prominence ≥ 1.5 × half-spread. | Labels exist for every closed paper ticket since 2026-09-17 with `hole_rate` reported. | Using ATM/ITM roll as the mark. Using as-traded ₹ to rank. |

**Do not do:** retune overlay stops from one green day; add `CANCEL_*` under a new name; promote `peak_hazard_p10` on the point estimate.

### 1b. ML models (P1 — overlays, not tickets)

ML-001 / ML-002 / MIX-ML-LOGIT do **not** pick CE/PE for the customer ticket. SOD still one `MIX-DEFAULT-BUY` ITM fill. Known bugs stay: same-session `_hold_series` leak, degenerate cluster 1723/1/1/1, `k_pe` 52,685, unreachable ML-1 (≥30 same-session closes). Holiday fit is 598 rows (2026-09-09..10).

| # | Step | Why | Protocol | Pass bar | Falsifier |
|---|------|-----|----------|----------|-----------|
| M0 | Freeze ML-001 seed 14, embargo 5, no MIX write. | KEEP_ALL overlay. Book-tune already `BACKTEST_REQUIRED`. | `python -m desk_ml book-tune` cache only. `production_params_written=false`. | No param write. Cluster sizes reported as counts, `win_rate=null`. | Writing MIX-DEFAULT-BUY from a cluster. |
| M1 | **Prior-session-only** logit / KMeans. | Phase-2 leak: train on first 60% of *same* session. | Fit on sessions `< D`. Embargo last 5 bars of D−1. Score D after each 1m close. Features = `idx_ret, ce_ret, pe_ret, spread_chg, abs_residual` on **closed** bars. | OOS AUC on next-15m **index** sign ≥ 0.56 with 95% CI lo > 0.52, **and** a 15m option-premium net (1-lot, costs) CI_lo > 0 vs a side-flip placebo. | Same-session train. AUC CI includes 0.50. Premium net ≤ 0 after costs. |
| M2 | FOLLOW-GAP HOLD only on DIVERGE + \|z\|≥2, not on recovery bars. | 2026-09-16 replay: HOLD was the wrong way (bleed worse when held). | `replay-hold --horizon-bars 15` on ITM 1m. Two books: (A) current FOLLOW-GAP, (B) DIVERGE∩\|z\|≥2. | Book B mean 15m straddle bleed **worse avoided** than A (more negative path skipped) on ≥ 2 NORMAL sessions, p<0.2 vs random-skip. | B skips winners more than losers. ATM-day n_hold used as evidence (must PASS / skip). |
| M3 | Shadow-score logit / XR / greeks vs picker. Do not recode until ≥ 10 NORMAL sessions. | Founder 2026-09-19: signal desk ≠ booking. | Daily `model_signals` MATCH/DISSENT only. After 10 NORMAL days, one pre-registered recode. | Recode only if MATCH-when-picker-wrong beats DISSENT-when-picker-right on 1-lot premium, CI_lo>0. | Recode after 1–2 days. Using win rate. |
| M4 | Kill same-session IsolationForest / k=4 as a buy signal. | 4-cluster 1723/1/1/1 is not a regime. | Keep as observe-log. | No CE/PE from cluster id. | `TREND_UP` → BUY_CE. |

**Do not do:** blocking LLM on the open path; sklearn as a hard dep; promoting AUC 0.55 peak models from Exit Lab (they fire, they do not rank peaks).

### 1c. Entry strategies (P1 — edge has to come from here)

Round 8: 120 active-buyer variants all lost, **gross**. 46% of coil breaks continue 15 min. Unseen mean move after a break is **against**. E1 COIL-SIDE / E2 P5-HV / E3 HV-GATE remain the only forward specs. Harvest H18/S07/H22/H19 stay closed on burned deep1 bars.

| # | Step | Why | Protocol | Pass bar | Falsifier |
|---|------|-----|----------|----------|-----------|
| N0 | Do not reopen BRK-BUY, long ATM holds, every-day premium selling, or H18/S07/H22/H19 on last3d / deep1. | Closed in Round 8 §3.5. Founder: those four harvest IDs failed OOS. | Reject any ticket that reuses those IDs on a burned window. | — | A “small tweak” of H18 on the same bars. |
| N1 | Shadow-log E1 COIL-SIDE (OI-before-break, exit **at** the break). | Only OOS direction signal (AUC 0.561 with OI strictly before the bar). Follow-through AUC 0.50. | Exact table in `ROUND8_STRATEGY_REDESIGN.md` §3.1. Frozen q10/q90 hashed before any new FWD look. Fill next snapshot. ITM100, not expiry day, no 09:15–10:00. | FWD-BAR in `bars.py`. Plus confident-tail side-hit ≥ p* at realised D and τ (Round 8 §2.2). | Using OI on the breakout bar (0.595 is the leaky number). Holding after the break. Gross ≤ 0 at n=30. |
| N2 | Shadow-log E2 P5-HV (gap fade, high HAR **before open**). | Post-hoc +₹3.8L / +₹4.2L; needs a clean pre-open vol cut. | HAR from **yesterday** only. 09:30 close, against the gap. VERIFY lab8 HARI timestamp — if it was 09:59, that is look-ahead; kill that variant. | FWD-BAR. Low-HAR days must be worse (placebo). | 09:59 tercile used for a 09:30 entry. Low-HAR days beat high-HAR. |
| N3 | E3 HV-GATE as a **skip flag only**. | Loss reducer. Quiet-third skip helped R5 in every slice, still negative. | Flag bottom-tercile HAR days. Never block. | After 40 flagged trades: flagged mean net < unflagged. Kill if not, or if a 20-trade half disagrees. | Promoting E3 as alpha. |
| N4 | Mesfin gates on Nifty 1m (SSRN `P01`/`P02`) as a **kill test**, not a buy. | US futures already fail 2-pt friction. If Nifty ORB also fails, stop buying open-range. | Rebuild 5m from 1m index. Expanding 66.7th percentile through **prior day**. Option book: 1-lot ITM100, same-day exit, V2 costs. | Kill the family if OOS net T<2 or year sign flips. A fail is a useful result. | Shipping ORB because the index proxy was green. |

**Do not do:** 5m Supertrend/MACD as entry (`SIGNAL_STAGING.md`: confirm-or-kill). News / extreme PCR as alpha (`EVENT_MEMORY.md`: hold/analog only). Writer-side E4 without a founder decision.

---

## 2. Minute-by-minute remine (steps + what this box could actually do)

### 2.1 What was available

| Needed | Here? |
|--------|-------|
| last3d `opt1m_last3d_part1-3.parquet` + `index_last3d.parquet` | **No** |
| Dual-tape / paper sqlite | **No** |
| PR #69 published univariate + top-20 combos + holdout table | **Yes** (ROUND3.md on the PR) |
| 2026-09-25 closed tickets + cancel log | **Yes** (`ML_PAPER_DASHBOARD.md`) |
| Bid/ask size | **No** (fills stay V2 half-spread) |

So this remine is **desk math on published tables + one paper day**. It does not replace a last3d rerun. The steps below are what Oct 10 must run when the tapes are attached.

### 2.2 Exact mining steps (no-peeking)

Do these in order. Do not skip to a “rule we like.”

1. **Build the entry set.** Seed 7. Reuse `entries.json` if the hash matches PR #69. Else: ≥5 tickets/day target, ATM / ITM100 / ITM200, CE+PE, first snapshot after 09:50. Cap V2-boss proxies at 8/session, 30 min apart. **Do not** spray.
2. **Lock the strike.** Every mark is `strike_ltp(entry.strike)`. If that strike is missing → HOLE (not a roll to ATM).
3. **Fill.** Buy at LTP + half-spread; sell at LTP − half-spread. Lot = 1 for rank. Book 65. Also write as-traded but do not rank it.
4. **Label `GOOD_EXIT` (hindsight only).** On the entry-strike path, a minute is GOOD if it is a local peak with prominence ≥ 1.5 × half-spread and no higher print later in the window {5, 15, 30, EOD}. Holes stay HOLD. Base rate on last3d 15-min labels was **0.0891** (66,864 / 750,079).
5. **Label `BAD_EXIT` for paper tickets.** A close is BAD if (reason in `{CANCEL_AGAINST, COVER_LONG_UNWIND, CANCEL_ADVERSE, CANCEL_STALL}` **or** net 1-lot < 0) **and** a later minute in the same window printed at least +1.5 × half-spread above the exit. A close is GOOD if it is within 1.5 × half-spread of the window max after costs. Otherwise HOLD / uninformative.
6. **Features at `i` use `minutes[:i]` only.** Allowed: option ret/pts since entry, peak-to-now DD, mom 1/3/5/10, body/wick, range expansion, minutes since last high, volume/OI change, index 1/5/15, VWAP and day high/low **truncated to `ts < now`**, first-hour break, round 100/50, opposite-strike 3-min mom, `delta_proxy = opt_mom_1 / idx_mom_1`. **Banned as features:** `tod_min`, `mins_to_1515`, `age_min`, expiry flag, any `label_*` / `GOOD_EXIT` / `HOLD`.
7. **Univariate.** On train minutes only, q25/q75 tails. Lift = P(GOOD \| tail) / base. Drop any feature whose best tail is a banned clock column.
8. **Pairs / triples.** Top combinations by lift, **then** by hist 1-lot pts vs `hold_to_1515`. Require fire rate ≥ 0.10 so a 1% toy tail cannot win.
9. **Look-ahead.** 5,000 minutes, 0 mismatches.
10. **Within-day label shuffle + remine.** Kill if remine #1 is clock-named or lift ≥ 1.10.
11. **Walk-forward.** 12 expanding expiry-week folds. Remine pairs + calibrate any model threshold on train. Replay test 1-lot.
12. **Holdout.** Random / v2 / legacy separately. Pass only if random 1-lot CI_lo > 0 and DSR ≥ 0.9.
13. **Overlap.** Same-moment ±180 s vs legacy `CANCEL_AGAINST` (32) and `COVER_LONG_UNWIND` (22) on the live legacy set. Kill at share ≥ 0.30.
14. **Write** `univariate.json`, `combos.json`, `lookahead_test.json`, `legacy_overlap.json`, `holdout.json`. Do not enable YAML.

### 2.3 Desk remine of the published last3d top-20 (this pass)

Clock columns = `{tod_min, mins_to_1515, age_min}` (PR #69 definition). Re-rank of the published 20 combos:

**Banned (clock or clock-tainted)**

| # | feats | lift | pts vs hold |
|---:|---|---:|---:|
| 1 | mins_to_1515:low + tod_min:high | 1.212 | +0.10 |
| 9 | mins_to_1515:low + age_min:high | 1.230 | +0.17 |
| 10 | tod_min:high + age_min:high | 1.230 | +0.17 |
| 13 | age_min:high + mins_since_high:high | 1.063 | +0.03 |
| 15–17 | tod / mins_to_1515 × lower_highs_4 | 1.317 | +0.45 |

Highest lift in the published table (1.317) is clock-tainted. That is why Oct 10 bans it.

**Non-clock, hist pts > 0, lift > 1.10, fire ≥ 0.13** (the only residual)

| rank | # | feats | lift | pts | fire |
|---:|---:|---|---:|---:|---:|
| 1 | 11 | mom_10:high + mom_5:high | 1.105 | +2.61 | 0.151 |
| 2 | 3 | lower_highs_4:low + mom_5:high | 1.134 | +2.21 | 0.170 |
| 3 | 5 | mom_1:high + lower_highs_4:low | 1.233 | +2.20 | 0.141 |
| 4 | 8 | lower_highs_4:low + mom_10:high | 1.171 | +2.13 | 0.138 |
| 5 | 4 | lower_highs_4:low + mom_3:high | 1.135 | +1.89 | 0.169 |
| 6 | 14 | mom_1:high + mom_3:high | 1.134 | +1.60 | 0.135 |
| 7 | 7 | lower_highs_4:low + opp_mom3:low | 1.118 | +1.43 | 0.152 |

**Rejected even among non-clock:** combo 2 (ret+pts high, −0.84 pts — “in profit” is not a peak) and combo 19 (lower_highs + ret high, −0.81 pts). Combo 12 (opp_mom3+mom_3) stays as a **diversity** cell (other-wing), not a lift leader.

**Honesty on this remine.** PR #69 already shuffled labels within day: top lift **1.212 → 1.023**, remine #1 still clock. Non-clock remine lifts were **≤ 1.05**. So the table above is a **candidate list**, not a finding. If Oct 10’s label-perm remine cannot push a non-clock pair above 1.10, **stop**. There is no path edge in these features.

### 2.4 Paper-ticket labels (2026-09-25, committed dashboard)

Session (as written): filled 43, W 14 / L 29, gross ₹80,762.50, charges ₹41,286.92 (**51.1% of gross**), net ₹39,475.58. TARGET hits 9. TIME exits 0. This is **one TREND day**, mixed lots, **not** 1-lot rank, **not** a promote.

Last-20 closed rows in that file (the only complete ticket table on `main`):

| reason | n | sum ₹ | mean ₹ | label (step 5, path unknown) |
|--------|--:|------:|-------:|---|
| `CANCEL_AGAINST` | 7 | −73,327 | −10,475 | BAD_EXIT candidate (legacy drain) |
| `COVER_LONG_UNWIND` | 6 | −50,479 | −8,413 | BAD_EXIT candidate (legacy drain) |
| `STOP` | 1 | −24,398 | −24,398 | BAD unless window max was the stop |
| `CANCEL_BOOK_NEAR` | 1 | +9,924 | +9,924 | uninformative without path |
| `CANCEL_NO_PROGRESS` | 1 | +16,677 | +16,677 | uninformative without path |
| `TARGET` | 4 | +138,596 | +34,649 | GOOD_EXIT if within 1.5× spread of window max |

Drain families (`CANCEL_*` + `COVER_LONG_UNWIND`) = **15/20**, sum **−₹97,205**. The four TARGETs more than offset that slice — and charges still took half the day’s gross on the full 43.

Cancel-reason log (same file): `CANCEL_AGAINST` 15, `CANCEL_NO_PROGRESS` 5, `CANCEL_BOOK_NEAR` 2 (**22** flatten-as-cancel events). Copy on AGAINST: “filled wing is against INDEX last-3 / 15m TREND / opposite ITM flow.” That is the cluster PR #69 measured at 32 AGAINST + 22 UNWIND on the 81-ticket legacy holdout.

**What we cannot label here:** minute-of-path GOOD/BAD (no 1m LTP series in git). Impulse notes on those tickets are almost all `wait_pause_after_impulse` / `pause_wait_continuation` / `no_raw_impulse` — so the desk was already unsure, then the cancel fired. That is a **booking** problem, not an ML-001 problem (ML books filled 0 that day).

### 2.5 No-peeking checks (this pass)

| Check | Result | Evidence |
|-------|--------|----------|
| No new tape features invented | PASS | Only published combo columns + dashboard fields. |
| Clock filtered before ranking | PASS | §2.3 banned set. |
| Labels not used as features | PASS | Remine did not fit a model. |
| Holdout not used to pick the Oct 10 four | PASS | X1–X4 chosen from **hist** non-clock table + overlap note, not from live +₹58k hazard. |
| `peak_hazard_p10` not promoted | PASS | CI_lo −₹16,545, DSR 0.043. |
| One-day paper net not a pass | PASS | Charges 51% of gross; mixed lots; n=43. |
| Harvest IDs not re-fit | PASS | No H18/S07/H22/H19 numbers invented. |

---

## 3. Sat 10 Oct weekly Exit Lab (non-clock only)

**Goal:** one more hashed round. Not a promote. Playbook stays off.

### 3.1 Command (when last3d + live tapes are on the lab box)

```bash
python -m exitlab round3 \
  --data .local_data \
  --out /tmp/exitlab-r4-oct10 \
  --seed 7 \
  --reuse-entries /tmp/exitlab-fix/entries.json
```

Then **restrict** the plan list to X1–X4 below (or a `--plans` allowlist if the harness grows one). Do not rerun the 654-cell clock/time/atr/shape grid. Those cells still count in DSR N.

If the harness on PR #69 cannot filter plans without a code change, **do not** patch V2. A tiny `packages/exitlab` allowlist is the only permitted code, in a follow-up draft PR, playbook still off.

### 3.2 Banned

- Any feature in `{tod_min, mins_to_1515, age_min}` or an expiry-clock dummy.
- `time_edge_*`, `clock_profit_*`, `clock_open_0915_0930`, `mid_1130`, `eu_1330`, `expiry_1430_1515`, `freeze_1515_1528`.
- `atr_opt_*`, `shape_exit`.
- Partials / ladders on 1-lot.
- Enabling `config/v2/exits/exitlab_playbook.yaml`.
- Editing `config/v2/exits/defaults.yaml`.

### 3.3 Four cells (≤ 4 tunables each)

Fixed, not swept, except the one listed cut. Cuts come from **train** q75 / q25 only.

| ID | Thesis | Fire rule (all must hold) | Tunables (≤4) | Why this and not clock |
|----|--------|---------------------------|---------------|------------------------|
| **X1 MOM-HH** | A one-minute up-print while the option is **not** making lower highs is a local peak, not a start. | `mom_1` ≥ train q75 **and** `lower_highs_4` ≤ train q25 → EXIT | (1) mom window=1, (2) hh lookback=4, (3) mom quantile, (4) hh quantile | Combo 5: lift 1.233, +2.20 pts, fire 0.141. Highest non-clock lift. |
| **X2 MOM10-5** | Medium momentum, not the 1-min tick. | `mom_10` ≥ q75 **and** `mom_5` ≥ q75 → EXIT | (1) w=10, (2) w=5, (3–4) two quantiles | Combo 11: **+2.61 pts** hist, fire 0.151. Best hist pts among non-clock. |
| **X3 OTHER-WING** | Opposite-strike 3-min mom against us + our 3-min mom with us. | `opp_mom3` ≤ q25 **and** `mom_3` ≥ q75 → EXIT | (1) opp window=3, (2) own window=3, (3–4) two quantiles | Combo 7/12 family. PR #69 `other_side` had **10/32** AGAINST overlap (33% — **borderline**; kill if live share ≥ 0.30). |
| **X4 HAZARD-NOCLOCK** | Peak-hazard with clock columns dropped from the design matrix. | Hazard score ≥ train p10 → EXIT | (1) label window=5, (2) p=10, (3) feature set=no-clock, (4) min age=0 **unused** — do not add age | Same model that was least-bad on live (+₹58k) but **with clock removed**. If it dies, the live green was theta. |

**Not a fifth cell.** Combo 3 (`lower_highs_4`+`mom_5`) is an X1/X2 cousin — if X1 and X2 both fail, do not sneak it in the same Saturday.

### 3.4 Pass / fail (Saturday night)

A cell **passes** only if **all** of these hold on the **random 1-lot** set:

1. Bootstrap **CI_lo > 0** vs `hold_to_1515` (founder bar; `peak_hazard_p10` fails this today).
2. **DSR ≥ 0.9** with N = 654 + 4 (or +k if any extra cell was run — count them).
3. **≥ 8/12** expanding folds beat hold on 1-lot.
4. Legacy overlap share of 1-lot gain **< 0.30**.
5. Spread ×2 still beats hold.
6. Label-permutation remine of **that cell’s features** has lift **< 1.10**.
7. Look-ahead mismatches = 0.

A cell **fails** (expected) if CI_lo ≤ 0, DSR ≪ 0.9, overlap ≥ 0.30, or the perm remine still names the pair. **Write `passing=[]` and stop.** Do not average the three live sets to rescue a random-set fail.

v2_boss (n=60) and legacy (n=81) are **report-only**. A green v2_boss and a red random set is a **fail**.

### 3.5 What we will not spend Saturday on

Re-fitting T=45. Re-running 654. Re-opening H18/S07/H22/H19. Training LightGBM (not in env; PR #69 already said so). Any “early 0.35 pt by minute 2” clone of `time_edge`.

---

## 4. Self-audit of every claim

| # | Claim | Layer | Verdict | Evidence |
|---|-------|-------|---------|----------|
| 1 | Exits are the drain | VALIDATION | **Supported** | 2026-09-25: charges ₹41,287 / gross ₹80,763 = 51%. Last-20: 15/20 drain-family exits, −₹97,205. PR #69: random hold 1-lot −₹82,565; 32 AGAINST + 22 UNWIND on legacy live. |
| 2 | Legacy cancels are not the design base | SOURCE_FACT | **Supported** | `packages/oms` must not contain those strings (REG-18). V2 defaults: atr/time/grace/flip/target/partials/trail = null. |
| 3 | Exit Lab 0/654 pass OOS | VALIDATION (PR #69) | **Supported, other branch** | PR body + ROUND3.md: `passing=[]`, `n_variants=654`. Not in this `main` tree. |
| 4 | Clock/theta dominates | VALIDATION (PR #69) | **Supported** | Univariate #1 `mins_to_1515` lift 1.212. Label-perm remine still clock, lift 1.023. T=45 least-bad clock-profit, CI crosses 0. last3d = expiry-week only. |
| 5 | Do not promote clock-only or early-bailout | HYPOTHESIS / policy | **Supported** | `time_edge` 78% overlap share; `shape_exit` 80%; `atr_opt_1.2` 55% + 23/32 AGAINST. |
| 6 | `peak_hazard_p10` is least-bad, not a pass | VALIDATION | **Supported** | +₹58,243 / +4.34 pts, capture 0.097 of +₹5,97,500 oracle, DSR 0.043, CI_lo −₹16,545. AUC 0.546. |
| 7 | H18/S07/H22/H19 failed deep1 OOS | FOUNDER-STATED | **Not independently re-verified** | No tables in this checkout. IDs not in `ssrn_harvest.json`. **Do not invent numbers.** Treat as burned. |
| 8 | `HOLDOUT_SPEC` frozen | FOUNDER-STATED | **File missing here** | Operating contract restated in §0 from PR #69 + `bars.py` + Round 8. Do not write a second competing spec. |
| 9 | Buyer needs 55–60% direction after costs | ARITH on lab8 | **Supported as arithmetic** | `ROUND8_STRATEGY_REDESIGN.md` §2.2. Not a measured desk hit rate. |
| 10 | Round 8 closed breakout-follow-through | VALIDATION | **Supported** | 120 variants all negative; unseen 15-min move after break −2 to −3.7 pts. |
| 11 | ML-001/002 are not buy engines | SOURCE_FACT | **Supported** | `ML_001_LOCAL_PATTERN.md`: TREND_UP ≠ BUY_CE. 2026-09-25 ML books filled 0. |
| 12 | Same-session ML leak / degenerate models | VALIDATION (gap matrix) | **Supported as documented bug** | `docs/01_CURRENT_STATE_AND_GAPS.md` known bugs. Not re-run in this sprint. |
| 13 | Cost is binding | VALIDATION | **Supported** | 2026-09-25 51% of gross. Round 8: losses were **gross**. PR #69 ×2 stress worse on both books. |
| 14 | Non-clock combos 11/3/5/8 are edges | HYPOTHESIS | **Not supported** | Hist pts look fine; label-perm already collapsed non-clock lift to ≤ 1.05. They are Oct 10 **tests**, not findings. |
| 15 | This box re-mined 750k minutes | — | **False if claimed** | We did **not**. We re-ranked published rows. Stated in §2.1. |
| 16 | Playbook / defaults unchanged | SOURCE_FACT | **Supported** | This PR does not edit those files. |
| 17 | 5m ST/MACD as entry | POLICY | **Rejected** | `SIGNAL_STAGING.md` confirm-or-kill. |
| 18 | News / extreme PCR as alpha | POLICY | **Rejected** | `EVENT_MEMORY.md` hold + analog. |

---

## Handoff block (section 106)

### Accepted

- PR #69 contract: 1-lot rank, three live sets, 12 expanding folds, DSR in [0,1], fixed-strike holes, playbook off.
- Round 8: entry edge is binding; exits choose hold time; FWD-BAR as coded.
- Founder: exits are the drain; legacy cancels are comparison only; H18/S07/H22/H19 stay burned; Oct 10 must be non-clock and require CI_lo > 0 on random 1-lot.
- Desk remine: clock-tainted combos out; seven non-clock pairs are the only Saturday candidates; they are **unvalidated**.

### Rejected

- Enable playbook. Edit live V2 defaults. Promote `peak_hazard_p10`, T=45, `time_edge`, `atr_opt`, `shape_exit`.
- Retest H18/S07/H22/H19 on deep1 / last3d.
- Treat 2026-09-25 net ₹39k as a pass (charges ate 51%; mixed lots; one day).
- Invent harvest P/L or a new `HOLDOUT_SPEC` that competes with the frozen contract.

### Unknown / Data Insufficient

- last3d parquets and dual-tape sqlite in this environment.
- Primary deep1 tables for H18/S07/H22/H19.
- A file literally named `HOLDOUT_SPEC`.
- Hist `normal` (non-expiry-week) slice.
- True bid/ask size / staleness.
- Whether lab8 P5 high-HARI used 09:59 (look-ahead) or pre-open HAR.

### Gap addressed

- Founder asked for a prioritized next list, a spelled remine, an Oct 10 card, and an audit. This file is that list. It does **not** close the “no passing exit” gap.

### Evidence

- PR #69 ROUND3.md / PR body (654, passing=[], CI_lo, DSR, overlap shares).
- `ML_PAPER_DASHBOARD.md` 2026-09-25 session + last-20 + 22 cancel rows.
- `ROUND8_STRATEGY_REDESIGN.md` §1–§3, `bars.py` FWD-BAR.
- Desk remine arithmetic in §2.3–2.4 (computed 2026-10-04 from those published numbers).

### Known risks

- Re-ranking published combos can still overfit the *choice* of X1–X4. The label-perm kill is what stops that.
- last3d bias: any hist-green path pair may still be expiry-week only.
- A tiny harness allowlist, if added later, must not become a playbook enable.

### Next steps

1. Sat 10 Oct: run X1–X4 only. Keep playbook off.
2. Attach last3d + live tapes on the lab box (not in git).
3. Founder: point at the original `HOLDOUT_SPEC` / harvest-ID file if it lives outside this repo, so 06 can cite it instead of restating.

---

## Coalition notes

| Team | Used |
|------|------|
| 01 | `SSRN_HARVEST.md` (P01/P02 kill-test only; no H-ids) |
| 02 | Round 8 p* arithmetic; DSR N |
| 03 | Expiry-week vs normal; last3d = last-3-days-before-expiry |
| 04 | `SIGNAL_STAGING.md` confirm-or-kill; ML-001 overlay only |
| 05 | `CUSTOMER_TALK.md` — no indicator soup; this file is `/desk` research |
| 06 | PR #69 Exit Lab; `EVENT_MEMORY.md` (news ≠ alpha); FWD-BAR |
| 09 | No five-pass. Docs auditor after this edit. KEEP_ALL STRAT-001–014 |
