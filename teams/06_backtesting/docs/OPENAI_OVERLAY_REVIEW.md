# OPENAI_OVERLAY_REVIEW — paper overlay counsel

**Team:** 06_backtesting · 07 `packages/desk-ml`  
**Date:** 2026-09-15 (IST)  
**Status:** paper overlay / **NO_PROMOTE** / `production_params_written: false`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** refused. No Super Order. No `ExecutionClient`.

Education ≠ advice. Notes ≠ five-pass. Cluster/OU counts are not a win rate.

Counsel was **not** written to a `COUNSEL_*.md` dump (allowlist). Round 1 lived in `counsel-job` stdout on this agent run. `SESSION_PREP_ML.md` is the 09:15 runbook, not the reject log.

---

## Round 1 — why OpenAI said REJECT

**Job:** `REVIEW_NOTES` · **together flag:** `ALIGNED` (both first-line tokens mapped to `OTHER`) · **substance:** SPLIT  
**Models:** Gemini `gemini-3.5-flash-lite` ACCEPT · OpenAI `gpt-5.4-nano` REJECT  
**Truncation:** the OpenAI paragraph was complete (not a mid-(c) cut). The refuse was a **content** refuse, not a nano clip.

Gemini (verbatim, first sentence):

> ACCEPT. The changes implement a desk-level ML warehouse join of OHLC bars, 1-minute bars, and ATM symbols against premium tape, alongside ML-001 embargo logic adhering to an AFML analog without out-of-sample claims, dual-tape follow-gap/hold scoring, and a 09:15 IST session prep routine, while leaving production parameters unwritten, the execution client unused, MRR windows restricted to 40/60/90, existing strategies STRAT-001 through STRAT-014 untouched, and MIX-DEFAULT-BUY unchanged.

OpenAI (verbatim):

> REJECT — Based on JOB REVIEW_NOTES, this is explicitly “09 notes — not a five-pass,” and the required desk_ml details are incomplete for a paper-only acceptance: while the what_changed slot describes joining `warehouse ohlc_bars + bars_1m + ATM symbols join premium_tape`, applying “ML-001 fit embargo last 5 1m rows (AFML analog, cpcv=false, oos_claim=false), score --source dual-tape FOLLOW-GAP HOLD,” “ML-002 score_mrr_last,” and “SESSION_PREP_ML 09:15 IST dual-tape then desk_ml score,” it also states `production_params_written false` and includes a “ExecutionClient unused” plus “MRR windows still 40/60/90 only,” but there is no provided HANDOFF block evidence that the desk_ml output is validated end-to-end for NIFTY/BANKNIFTY/SENSEX (paper-only constraints, no win-rate claims) nor confirmation that the “follow-gap hold” logic actually compiles/runs in the target environment. Keep_all_ok is “yes” and promote_claimed is “no NO_PROMOTE BACKTEST_REQUIRED,” but because the review gate requires founder+five-pass to stay unset and this is not a five-pass, acceptance is not supported. DATA_INSUFFICIENT for final approval.

**Engineering reading (not a prompt rewrite):**

| OpenAI gap | Meaning |
|------------|---------|
| Notes-not-five-pass treated as refuse | Job template said ACCEPT/REJECT with “gate stays unset unless five-pass,” so nano refused *any* accept. Five-pass still must stay unset. Paper overlay may be `ACCEPT_WITH_CAVEATS`. |
| No e2e NIFTY/BANKNIFTY/SENSEX | Overlay must score all three names. |
| Follow-gap not shown compiling/running | Dual-tape persist must write overlay; pytest must run HOLD. |
| DATA_INSUFFICIENT for *final approval* | Correct for RESEARCH_READY. Do not claim that gate. |

---

## What we recoded (paper overlay only)

- Causal residual **z** (`rolling_z(..., causal=True)`): mean/std from **past** bars only. `oos_claim: false`.
- Thin dual-tape (<2 INDEX+CE+PE ticks) → `session_action=HOLD`, `allow_new_paper_ce_pe=false`.
- `python -m desk_ml overlay` scores NIFTY / BANKNIFTY / SENSEX.
- Dual-tape persist writes `overlay_last.json` (fail-soft; no orders).
- Counsel CLI: `--openai-model` / `--max-tokens` so nano is not required; `ACCEPT`/`REJECT`/`ACCEPT_WITH_CAVEATS` tokens.
- `REVIEW_NOTES` output: paper overlay may be `ACCEPT_WITH_CAVEATS`; still not a five-pass; REJECT if look-ahead, missing tests, live orders, or a promote.
- Pytest: embargo, warehouse join, FOLLOW-GAP HOLD, thin HOLD, causal z, overlay three names, dual-tape `overlay_last.json`.

---

## Round 2 verdict

**Job:** `REVIEW_NOTES` · `--openai-model gpt-4.1` · `--max-tokens 1200` · compact JSON in `--route`  
**together:** `ALIGNED` on `ACCEPT_WITH_CAVEATS`  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`. Still **NO_PROMOTE**.

Gemini (`gemini-3.5-flash-lite`), first line + gist: **ACCEPT_WITH_CAVEATS**. Paper overlay only; 28 tests; embargo `oos_claim: false`; KEEP_ALL; `production_params_written` false; gate unset until five-pass + founder.

OpenAI (`gpt-4.1`), first line + gist: **ACCEPT_WITH_CAVEATS**. Notes-only, not a five-pass; pytest 28/28; wiring named; causal z / thin dual-tape HOLD remain as caveats; no Dhan production push.

Honest: this is **not** a five-pass pass. OpenAI no longer REJECTS the *paper overlay*. A REJECT on five-pass / RESEARCH_READY would still be correct if anyone asked for that gate.

---

## Round 3 — trail SL / target lock-shift (2026-09-17)

**Job:** `REVIEW_NOTES` · `--openai-model gpt-4.1` · `--max-tokens 1200`  
**What changed:** After fill, soft `CANCEL_*` (bin-roll, thesis, strike-roll, sideways, greeks) trails stop 4–12 premium ₹ (spike/vol) and may lock BE including Groww+STT. First TARGET touch locks SL and shifts target (`TARGET_STEP_MAX=2`). Hard STOP/TIME/FLATTEN/CANCEL_ADVERSE. Unfilled ₹0. Tests: trail-not-flatten, target lock, STOP, unfilled. KEEP_ALL. `production_params_written` false.

**together:** `ALIGNED` on `ACCEPT_WITH_CAVEATS` (Gemini `gemini-3.5-flash-lite` + OpenAI `gpt-4.1`).

Gemini gist: trail/BE lock/target shift with 68 tests; HARD exits; not five-pass; not RESEARCH_READY.

OpenAI gist: paper overlay acceptable to run; KEEP_ALL; production params not written; further gate blocked until five-pass.

**Caveat we already accept:** notes ≠ five-pass; trail is HYPOTHESIS to cut churn, not a wr claim.

---

## Round 4 — path SL / ITM OI covering / T1-T2 (2026-09-17 night)

**Job:** `REVIEW_NOTES` · `--openai-model gpt-4.1` · `--max-tokens 1200`  
**What changed:** Keep original path SL until T1 (60s still at/above target) then lock+T2. Floor stop ≥₹8 or 6% entry. Skip CE vs PE ITM-bin. OI on selected ITM: SHORT_COVER vs LONG_UNWIND. Book `COVER_LONG_UNWIND` after T1/BE. pytest paper_scalp 72. Dual-tape replay 2026-09-17 `write=false`: live STOP 153/175 vs overlay STOP 25/83 (unique STOP 77→13). KEEP_ALL. `production_params_written` false.

**together:** `ALIGNED` on `ACCEPT_WITH_CAVEATS` (Gemini `gemini-3.5-flash-lite` + OpenAI `gpt-4.1`).

Gemini gist: risk-management refinements + replay tests; FOLLOW-GAP HOLD; gate unset; NO_PROMOTE.

OpenAI gist: paper overlay acceptable; tests exist; not RESEARCH_READY; not a five-pass; not live.

**Caveat we already accept:** overlay wr 74.7% / COVER 54 is one-day learning, not a promote. Next grid: COVER only after T1 or SIDEWAYS+BE.

---

## Round 5 — impulse pause-continue / 3-vs-5 (2026-09-17 night)

**Job:** `REVIEW_NOTES` · `--openai-model gpt-4.1` · `--max-tokens 1200`  
**What changed:** Do not pick 3 vs 5 candles. First impulse never overrides the ITM bin. Pause then volume continuation may. COVER after T1 or SIDEWAYS+BE. BANKNIFTY+SENSEX wait continuation. pytest paper_scalp. KEEP_ALL. `production_params_written` false.

**together:** `ALIGNED` on `ACCEPT_WITH_CAVEATS` (Gemini `gemini-3.5-flash-lite` + OpenAI `gpt-4.1`).

Gemini gist: rule refinements stay paper-only; 17 Sep still net negative; NO_PROMOTE.

OpenAI gist: notes-only paper overlay; not five-pass; not RESEARCH_READY.

**Replay (write=false, not a promote):** live 17 Sep −93745. Pause+wide −18104 wr 28.6%. Confirm-only −49888 wr 31.8%. NIFTY-only ablation −9738 wr 40%. 14 Sep DI; 15 Sep no ITM wings.

---

## Round 6 — strict TARGET, no lock-shift (2026-09-17 night)

Founder: do not chase T2. First TARGET flattens. Trail SL stays. `apply_target_shift` default false. pytest 72. 17 Sep write=false table in `QUANT_SELF_REVIEW_LOOP.md`. KEEP_ALL. `production_params_written` false. **NO_PROMOTE.**

---

## Round 7 — NIFTY vs SENSEX point R:R (2026-09-17 night)

**Job:** `REVIEW_NOTES` · gpt-4.1 + gemini-3.5-flash-lite · **together:** `ALIGNED` `ACCEPT_WITH_CAVEATS`.

**What changed:** Drop BANKNIFTY NEW. Separate NIFTY/SENSEX premium-point ATR+fib stops and dynamic R:R. pytest 74. 17 Sep NS write=false unique net +2696 one-day. Not RESEARCH_READY. **NO_PROMOTE.**

---

## Round 8 — NIFTY-only PE overlay (2026-09-17 night)

**Job:** `REVIEW_NOTES` · `--openai-model gpt-4.1` · `--max-tokens 1200`  
**together:** `ONE_ONLY` (Gemini `HTTP 0` / DATA_INSUFFICIENT). OpenAI `ACCEPT_WITH_CAVEATS`.

**What changed:** Founder does not trade NIFTY+SENSEX same time. Permutations on 17 Sep **full tape**. Ship PE + strength + max 4 fills/book. Skip SENSEX NEW. No T2. pytest 80. Live dashboard not overwritten.

OpenAI extras beyond desk list: (a) first-hour/session lean instead of hard PE — **coded, 17 Sep −1185** (CE still printed); (b) VWAP banding — not wired (DATA_INSUFFICIENT vs 10s LTP); (c) do not rebuy CE after CE STOP — **coded** `nifty_skip_ce_after_stop`; (d) two-STOP session halt — **coded**, both-wings still red vs PE+max4.

**Caveat:** PE-only is 17 Sep directional. max4 matches 13:30 on this tape; we ship the cap, not the clock. Not RESEARCH_READY. **NO_PROMOTE.**

---

## Round 9 — CANCEL_STALL vs constant TIME (2026-09-18)

**Job:** `REVIEW_NOTES` · `--openai-model gpt-4.1` · `--max-tokens 1200`  
**together:** `ALIGNED` `ACCEPT_WITH_CAVEATS` (Gemini `gemini-3.5-flash-lite` + OpenAI `gpt-4.1`).

**What changed:** Hard `CANCEL_STALL` when age≥20m, premium Kaufman ER≤0.18, not true TREND (index ER≥0.35 / last-3 with the wing / ≥55% to target), and either LTP tags the ticket high (failed-break fade) or the high is ≥8m stale with LTP≥entry. Soft greeks/strike trail cannot skip STALL. 9m TIME only if stall state missing; else 45m hard TIME. pytest paper_scalp 86. write=false: 18 Sep unique −6952; 17 Sep TARGET PE 153→182 kept. KEEP_ALL. `production_params_written` false.

**Caveat:** notes ≠ five-pass. 45m TIME still not the founder 159-book on a ticket already dead. One-day nets are not a promote. **NO_PROMOTE.**

---

## Round 10 — FIX-FIRST chop profit book (2026-09-18)

**Job:** `REVIEW_NOTES` · gpt-4.1 + gemini-3.5-flash-lite · **together:** `ALIGNED` `ACCEPT_WITH_CAVEATS`.

**Measured (not assumed):** NIFTY 1m dual-tape. 16 Sep incomplete. 17 Sep jsonl from ~12h (`DATA_INSUFFICIENT` morning); 13h range 78 max_1m 17; 15h max_1m 23.75. 18 12h ER 0.043 max_1m 10.45; 13h ER 0.019 max_1m 11.1; 14h ER 0.492. write=false after recode MIX-DEFAULT-BUY: 17 TARGET CE + STALL; 18 three STALL greens + one chop UNWIND. Board wr on 18 is one incomplete day — not 70% proof.

**What changed:** Chop = INDEX ER < 0.35 even if itm_bin TREND. Stall 8m / stale 3m; ≥40% of target then fade books. Chop target cap +10 premium (149.7→159.7). CANCEL_AGAINST needs last3_raw against AND ≥3pt underwater or ER≥0.35 opposite. LONG_UNWIND only T1 or chop+3pt underwater. Dual-tape **not** restarted (live to close). pytest 89. Lots unchanged. KEEP_ALL. `production_params_written` false.

**Caveat:** 17 PE 153→182 still not recovered on this jsonl slice. 70% wr / 30–40 lots not coded. ML tune parked. **NO_PROMOTE.**

---

## Weekend queue — COVER_LONG_UNWIND (2026-09-22) · **not recoded**

**Room:** desk booking overlay on `MIX-DEFAULT-BUY` only. Same gate for **CE and PE** (`CE_LONG_UNWIND` / `PE_LONG_UNWIND`). Not analyst, not picker, not observer.  
**Status:** `HYPOTHESIS` / `BACKTEST_REQUIRED` / **NO_PROMOTE**. Live overlay **unchanged** until weekend replay + founder confirm.  
**Counsel:** not run this round. Notes only.

### Why this is on the list

22 Sep NIFTY **CE 23200** `paper-MIX-DEFAULT-BUY-NIFTY-1790054974-CE`: open 10:59:34 → close 11:00:42 IST (~68s). `COVER_LONG_UNWIND`, `target_step=0`, `target_hit=false`, sl_hit=false. Entry 191.7 → exit 185.85 (−5.85 pts). Net **−₹10,270** (25×65, charges ₹764). Stop was 175.85, T1 201.7.

Ticket **word** was `index_regime=TREND` (`itm_bin_ce_confirm`). Path was **not** ER-trend: `market_kind` VOLATILE, ER open **0.0988** / close **0.0026**, flip ~0.54–0.62, `last3=none`. Flatten used ER&lt;0.35 + &gt;₹3 underwater. Same-day PE also printed `COVER_LONG_UNWIND` (e.g. 23600 ~11:10). One day is not a retune.

### Current live rule (do not change until replay)

1. After T1: `LONG_UNWIND` → flatten. **Keep this** unless replay proves it cuts winners.  
2. Before T1: flatten only if LTP+3 &lt; entry **and** INDEX ER &lt; 0.35.  
3. Twin **entry** skip: `BIN_LONG_UNWIND` (do not open that wing).

### Proposed A/B (weekend `write=false` only)

| # | Change | Why | Keep / kill after replay |
|---|--------|-----|--------------------------|
| W1 | No unwind flatten in the **first two finished 1m bars** after fill (`target_step=0`) | 68s is one noisy OI+px print | Kill if sitting to stop is worse on ≥2 NORMAL days |
| W2 | Founder-facing label: show `market_kind` + ER, not itm_bin **TREND**, on unwind tickets | TREND word made this look like a trend cut | Display only; not a P/L change |
| W3 | Before T1, require chop **and** last-3 against the wing (or two bars of OI+px down). **VOLATILE ≠ CHOPPY** | Wide/flip tape can still print T1 | Kill if CE/PE then bleed to stop |
| W4 | After T1, keep flatten on `LONG_UNWIND` | Do not give T1 back | Default keep |

**Bounds on the 22 Sep 23200 CE only** (qty 1625; path after 11:00:42 is `UNKNOWN`):

| Sit until | Premium | Rough book |
|-----------|---------|------------|
| What we did | 191.7 → 185.85 | **−₹10,270** known |
| Paper stop | 191.7 → 175.85 (~−15.85 pts) | worse, ~−₹26k gross |
| Paper T1 | 191.7 → 201.7 (+10 pts) | win, ~+₹16k gross |

Replay must say which of stop / T1 / other exit the **same tape** would have printed with W1/W3 off.

### Weekend replay recipe

```text
python -m desk_ml paper-scalp --replay --source dual-tape --underlyings NIFTY \
  --session-date 2026-09-22 --no-write
```

Also run **17 / 18 / 21** Sep (already in FIX-FIRST) plus 22 Sep. Score only `NORMAL`. Compare unique MIX-DEFAULT-BUY: n `COVER_LONG_UNWIND`, net ₹, n STOP, n TARGET, time-to-exit. Flag `--no-write` always. Do not write MIX params. Do not restart npm / paper.

**Verdict after weekend:** `KEEP` / `KILL` / `DATA_INSUFFICIENT` per W1–W4. Still **NO_PROMOTE.**
