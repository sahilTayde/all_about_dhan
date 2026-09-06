# MIX SCAN VALIDATION — WEB/PATTERN expanding windows (charter, not a run)

**Team:** 02_phd_math  
**Layer:** `VALIDATION` (charter). P/L numbers do **not** exist in this file.  
**Status:** `DRAFT` / `UNVALIDATED`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. Notes ≠ five-pass.  
**KEEP_ALL.** No `STRAT-015+`. No code this ticket. No live Dhan. No invented win rates, lots, or fills.

Founder authorized a **WEB/PATTERN scan** beyond Supertrend / MACD / RSI. That is **not** a delete of STRAT-001–014, **not** a customer-default swap, and **not** a license to relabel folklore as `DHAN-DERIVED`. Customer default remains `MIX-DEFAULT-BUY` ([`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md)).

**P/L object, fill, 005 ITM strike, 15:15 flatten, OOS split inside a frozen window, and cost honesty** copy [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md). Do not re-litigate next-bar-open or ATM-2/ATM+2 here. This charter **freezes the scan protocol**: expanding windows, SCREEN vs score, multiple testing, ORB `skip_open` exception, origin tags, and **no lookback p-hack after 2y wr**.

**Lean tape is INDEX** (OHLC constructions named per MIX). That is **not** FUTIDX VWAP ([`LIVE_OHLC_2026-09-03.md`](LIVE_OHLC_2026-09-03.md)). This file does **not** re-sign INDEX volume. Money is **OPTIDX** rollingoption OHLC.

**Universe for 06:** **NIFTY** and **SENSEX** OPTIDX `POST /charts/rollingoption`. BANKNIFTY is not this charter (KEEP_ALL; later MIX row if 04 names it).

---

```text
HANDOFF
From:     teams/02_phd_math
To:       teams/06_backtesting ; teams/04_quant ; teams/03_phd_market ; teams/09_review ; teams/05_analysis
Date:     2026-09-03
Status:   VALIDATION charter / UNVALIDATED / not a run
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted:
- Founder WEB/PATTERN scan beyond ST/MACD/RSI. Namespace MIX-WEB-* / MIX-PATTERN-*.
  Origin PROJECT_MIX or WEB-DERIVED. Not DHAN-DERIVED. Not customer default.
- Expanding windows from now: 30d, 90d, 180d, 365d, 730d. 5y ONLY if that recipe
  already passed 730d OOS wr>=45% AND optimistic exp>0.
- 30d/90d = SCREEN only (n often <30). A 30d screen pass is NOT a promote.
- P/L = OPTION_PREMIUM_VALIDATION.md (rollingoption OPTIDX; NIFTY+SENSEX; 005 ITM;
  INDEX leans; flatten 15:15). ORB books may enter 9:30–9:45 (skip_open off).
- Multiple testing: many MIX IDs inflate false positives. Costs UNKNOWN ⇒ no CANDIDATE.
- Freeze lookbacks before seeing 2y wr. KEEP_ALL. No STRAT-015+.

Rejected:
- Relabel WEB/PATTERN DHAN-DERIVED. Swap MIX-DEFAULT-BUY. STRAT-015+.
- Promote or CANDIDATE from a 30d/90d screen. Run 5y on 730d FAILs.
- P-hack a winner's lookback after seeing 730d/2y wr (search 500d/800d, new start date).
- INDEX points as option_pnl. Invented costs then CANDIDATE. P/L numbers in this file.
- Silent AND of 003 ST / 5m MACD/RSI into a scan winner after wr. RESEARCH_READY.

UNKNOWN / DATA_INSUFFICIENT:
- Family-wise error rate (k recipes × m windows) until 06 names k. Costs. Q12.
- INDEX volume as FUTIDX VWAP. SENSEX strike step. session_kind NORMAL strip.
- Which ORB T is “official” (none). CPR/Donchian/BB as Dhan series (they are not).

What 06 must do: inherit OPTION_PREMIUM fill/exit/ITM; expanding windows as frozen;
SCREEN-label 30d/90d; 5y only after 730d pass; skip_open off on ORB books only;
label exp OPTIMISTIC; no CANDIDATE. Say multiple testing.

What 06 must not do: p-hack lookback after 2y wr; promote a screen; run 5y to
rescue a 730d FAIL; invent costs; publish INDEX points as option_pnl.

What 04 must do: name MIX-WEB-* / MIX-PATTERN-* rows (not STRAT-015+). Origin
PROJECT_MIX or WEB-DERIVED. Not default. Freeze recipe params before 06 runs.

What 03 must do: same OPTIDX / 15:15 ≠ F&O close as OPTION_PREMIUM_VALIDATION.md.
ORB 9:15–9:30 is a chosen box, not an exchange law.

What 09 must do: notes, not a pass. Multiple testing stays a FAIL-class honesty
item. Q8/Q12 not waived. Origin stays WEB-DERIVED / PROJECT_MIX.

What 05 must do: news / extreme PCR remain hold/veto, not a lookback retune.
```

---

## 1. Why this exists (math, not a promote)

[`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) scored **frozen 003** leans → 005 ITM option OHLC. [`MIX_PROJECT_VALIDATION.md`](MIX_PROJECT_VALIDATION.md) added two **PROJECT_MIX** clubs still inside Supertrend / MACD. Teacher books and those two clubs **FAIL** on premium; that is **not** a license to hunt a new indicator until wr ≥ 45%.

The founder still authorized a **separate scan** of popular WEB/PATTERN recipes (ORB, CPR, Donchian, BB, Keltner, candles, ROC, SAR, NR7, ADX, pivots, EMA stack, streaks, range expansion — 04 names the IDs in [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) / [`MIX_SCAN_2026-09-03.md`](../../04_quant/docs/MIX_SCAN_2026-09-03.md)). 02 will **not** sign any of them as theorems. 02 **will** freeze how 06 is allowed to look, so a hot 30-day ORB does not become the product ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)).

| Question | Answer this charter allows |
|----------|----------------------------|
| What is money? | Rollingoption **OPTIDX** OHLC, 005 **ITM**, NIFTY+SENSEX — same as [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md). |
| What is a lean? | INDEX OHLC **per named MIX**. Not INDEX points as P/L. Not FUTIDX VWAP. |
| How far back? | Expanding **30d → 90d → 180d → 365d → 730d**. **5y only** after a **730d OOS** pass. |
| What is a pass? | At **730d**: OOS wr ≥ 45% **and** optimistic exp > 0. Still **not** CANDIDATE (costs UNKNOWN + multiple testing). |
| What is a screen? | **30d / 90d**. n often < 30. **Not** a promote. |

Answering the scan does **not** prove ORB or CPR, does **not** make INDEX volume a FUTIDX VWAP, and does **not** set `RESEARCH_READY_FOR_PROGRAMMING`.

---

## 2. Layers (do not collapse)

| Layer | What |
|-------|------|
| `SOURCE_FACT` | Dhan **ORB product** exists on charts; speaker boxes disagree (`eApl0SfVBBY` 09:15–10:00 vs 09:15–09:30 / 09:15–09:45). CPR named as **chart product**. Bind: [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md), [`TA_STRUCTURE_PACKET.md`](../../01_research/docs/handoffs/TA_STRUCTURE_PACKET.md). Popular Indian **09:15–09:30 ORB** and **CPR bias** as *the* recipe = **folklore / WEB**, not a DhanHQ video freeze ([`TA_FROM_TRANSCRIPTS.md`](TA_FROM_TRANSCRIPTS.md)). HQ: **no** ORB / CPR / Donchian / BB **series** REST ([`DHAN_INDICATOR_API_MAP.md`](DHAN_INDICATOR_API_MAP.md)). |
| `VALIDATION` | **This file** + [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md). Pattern geometry = `supported` as construction. Predictive power = `unsupported` until a honest test. Expanding windows + multiple-testing honesty = this charter. ST/MACD/RSI remain **confirm-or-kill** on the desk ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)), **not** this scan’s entry. |
| `HYPOTHESIS` | 04 naming `MIX-WEB-*` / `MIX-PATTERN-*` ([`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md)). Origin **`PROJECT_MIX` or `WEB-DERIVED`**. Not `DHAN-DERIVED`. Not `STRAT-015+`. |

Books (Murphy / Natenberg) tag risk language only. They do **not** license a web ORB as a Dhan edge.

---

## 3. Origin and namespace (freeze)

```yaml
book_policy: KEEP_ALL
status: UNVALIDATED
origin: PROJECT_MIX | WEB-DERIVED   # never DHAN-DERIVED on this scan
research_ready_for_programming: false
customer_default: false              # MIX-DEFAULT-BUY unchanged
markets: [NIFTY, SENSEX]
overlay_strike: STRAT-005            # ITM only — OPTION_PREMIUM cell B
flatten: STRAT-009                   # 15:15 IST
skip_open_009: true                  # default; ORB books: false (see §6)
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
not: STRAT-015+
```

| Tag | Use on this scan |
|-----|------------------|
| `WEB-DERIVED` | Folklore / public-web pattern (Indian ORB 09:15–09:30, CPR, Donchian-20, BB break, …). Not a `@DhanHQ` spoken recipe. |
| `PROJECT_MIX` | Desk club of those pieces (e.g. CPR **and** ORB as `MIX-CPR-ORB`). Still not a teacher club. |
| `DHAN-DERIVED` | **Forbidden** here. Same-video Gokul/HAUS stay on `MIX-GOKUL-*` / `MIX-HAUS-001`. Do not steal `eApl` ORB-product mention to relabel this scan. |

A MIX is a **new test ID**. STRAT-001–014 stay `BACKTEST_BOOK`. Do not mint `STRAT-015+` because the scan is “beyond Supertrend.” Conflicts stay extra MIX rows.

04’s named scan IDs (pointer — 04 owns the yaml): `MIX-ORB-15`, `MIX-ORB-VWAP`, `MIX-PDH-PDL`, `MIX-CPR-BIAS`, `MIX-CPR-ORB`, `MIX-DONCHIAN-20`, `MIX-BB-BREAK`, `MIX-KELTNER`, `MIX-INSIDE-BRK`, `MIX-ENGULF`, `MIX-MOM-BODY`, `MIX-ROC-10`, `MIX-SAR`, `MIX-GAP`, `MIX-NR7-BRK`, `MIX-ADX-DI`, `MIX-PIVOT-R1`, `MIX-EMA-20-50`, `MIX-STREAK-3`, `MIX-RANGE-EXP`. If 04 adds more `MIX-WEB-*` / `MIX-PATTERN-*` rows, **k rises** — multiple testing gets worse (§5). Do not AND 002 / 006 / 007 / 008 / 5m ST into a winner after wr.

---

## 4. Expanding windows (freeze before 06 runs)

Anchor = last ingested session on the rollingoption book (“from now”). Walk **outward**. Do not shuffle. Do not pick a pretty start date after seeing wr.

| Step | Window | Role | 5y allowed? |
|------|--------|------|-------------|
| 1 | **30d** | **SCREEN only** | no |
| 2 | **90d** | **SCREEN only** | no |
| 3 | **180d** | Score (may still be n < 30 → `DATA_INSUFFICIENT`) | no |
| 4 | **365d** | Score | no |
| 5 | **730d** (2y) | **Promote-gate window** for this scan | no, until this row passes |
| 6 | **5y** | Confirmation **only** | **only** if that **same recipe** passed step 5 |

**730d pass (necessary, not sufficient):** OOS last **20%** of trades **inside the 730d window** (trade-sequence split, not a shuffle). OOS **win_rate ≥ 45%** **and** optimistic expectancy **> 0**. Else **FAIL** — **do not** run 5y on that recipe. n_OOS < 30 → `DATA_INSUFFICIENT` (cannot pass into 5y).

**30d / 90d SCREEN:**

- Purpose: kill obvious non-starters and check the engine path.  
- **n often < 30.** The ≥30 IS / ≥30 OOS gate from [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) §7 **does not apply** as a pass. Report n. Label `SCREEN`.  
- A hot 30d wr is the **most** overfit window. **Passing a 30d screen is NOT a promote**, not CANDIDATE, not a reason to skip 180/365/730, not a customer-ticket change.  
- A cold 30d screen is **not** a catalog delete (KEEP_ALL).

**180d / 365d:** apply OOS 20% and FAIL wr < 45% or optimistic exp ≤ 0 **when n_OOS ≥ 30**. If n_OOS < 30, write `DATA_INSUFFICIENT` — do not call it a 730d-style pass. These windows **do not** unlock 5y.

**5y:** confirmation sample for recipes that **already** passed 730d. Not a fishing pond to rescue 730d FAILs. Not a second lookback search.

Do **not** invent wr / PF / DD in this file. 06 writes measured numbers in a **dated 06** artifact, labeled **UNVALIDATED**, `validated: false`, `promote: false`, and **SCREEN** vs **SCORE** vs **5Y_CONFIRM**.

---

## 5. Multiple testing (say so)

Scanning many `MIX-WEB-*` / `MIX-PATTERN-*` (and several windows each) **inflates false positives**. Under a true wr near a coin-flip, the **best of k** recipes will look like a 730d “pass” with non-trivial probability. That is sampling, not edge.

| Honesty | Rule |
|---------|------|
| Family-wise error | Rises with **k recipes × m windows**. 02 does **not** invent a Bonferroni / FDR number here (`DATA_INSUFFICIENT` until 06 names k and the dependence). **Say the inflation exists.** |
| Best-of-k | The winner of the scan is **not** a theorem. Rank is `UNVALIDATED`. |
| Screen → score | Using 30d/90d to **choose** which recipes get 730d, then treating 730d as an independent test, is a **second** selection bias. Frozen protocol: **every named ID** walks the same expanding ladder; do not drop losers at 30d then pretend 730d was pre-registered on a shortlist. |
| Costs | Still `UNKNOWN`. Optimistic exp > 0 on the winner **cannot CANDIDATE** ([`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) §8). Multiple testing makes that bound **more** optimistic, not less. |
| Promote | **Forbidden** from this charter. Need OOS + `NORMAL` + **after-cost** vs current **and** a 09 pass that names the multiple-testing remainder. |

Do not “fix” this by scanning fewer IDs after seeing which ones won.

---

## 6. Objects, clocks, ORB `skip_open`

| Object | Role | Forbidden |
|--------|------|-----------|
| **INDEX** `IDX_I` | **Lean only** — ORB box, CPR, Donchian, BB, … per MIX | INDEX/FUTIDX **points** as `option_pnl`. Cash-index volume as FUTIDX VWAP. |
| **rollingoption OPTIDX** OHLC | **P/L + fill** — NIFTY + SENSEX | Inventing bid/ask. BANKNIFTY as this charter. |
| **FUTIDX** | Spoken 003 tape. **Not** required for this scan’s lean. Continuous history still `DATA_INSUFFICIENT`. | Pretending a web ORB re-signs Gokul futures VWAP. |

Fill, lean-leave, overnight ban, P/L unit (option points, long CE/PE), Q12 honesty: **copy** [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) §4. Entry fill = next option **open**. Exit = lean-leave at next option open, or flatten **15:15**. 15:15 is a **filter**, not F&O close (`VERIFY` 15:40). CAS 15:15–15:35 is cash Closing Auction Session, not this exit.

**Strike:** 005 **ITM only** (CE **ATM-2**, PE **ATM+2**). Not 002 OTM, not ATM cell A, not 006 100–200 pts.

**009 flatten:** **on** for every scan book.

**009 skip_open (09:15–09:45 IST):** **on** by default (same as the premium 003 book).

**ORB exception (founder freeze):** ORB books **may enter 09:30–09:45**. `skip_open` **off** for those IDs only (`MIX-ORB-15`, `MIX-ORB-VWAP`, `MIX-CPR-ORB`, and any later `MIX-ORB-*` 04 names). Construction: range **09:15–09:30**, break after the box is **closed** — entries in 09:30–09:45 are the point of the recipe. Do **not** treat 09:45 as “Dhan’s official ORB” ([`TA_FROM_TRANSCRIPTS.md`](TA_FROM_TRANSCRIPTS.md): several T; HQ **no ORB REST**). Do **not** turn `skip_open` off on non-ORB scan books after seeing wr. Do **not** AND 007 (10:00 start) into an ORB book to “fix” open noise.

---

## 7. Do not p-hack a winner’s lookback after 2y wr

Freeze the window **schedule** and each recipe’s **params** **before** 06 prints 730d wr. After seeing 2y (730d) wr, **forbidden** ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)):

- Search lookbacks `{400, 500, 600, 800, 900}` d, or “the last N that looks good,” because 730d wr < 45% or to fatten a winner.  
- Move the anchor date, drop a crash month, or switch calendar-days vs session-days to lift wr.  
- Run **5y first**, then keep whichever of {730d, 5y} looks better. 5y is **locked** behind a 730d pass.  
- Grid ORB T `{15, 30, 45, 10:00}` on the **winner** after wr. T is 04’s named ID (`MIX-ORB-15` vs a later `MIX-ORB-30`). Extra T = extra MIX row **before** the run, not a retune.  
- Grid Donchian n, BB k, Keltner ATR, ROC length, EMA 20/50 → 9/21, SAR AF, ADX period, NR7 definition, engulf wick rules **after** wr.  
- Soup 003 Supertrend, 5m MACD/RSI confirm-or-kill, 007, or 008 onto the scan winner because wr failed or because wr passed. Those are **other MIX rows**.  
- Relabel the winner `DHAN-DERIVED`. Swap `MIX-DEFAULT-BUY`.  
- Nightly `RETUNE_PROPOSAL` auto-apply — default **keep current**.

Failing 730d wr on a frozen recipe is a **result**, not a license to search. A passing 730d wr is also **not** a license to search a prettier lookback.

5m Supertrend / MACD / RSI stay **confirm or kill**, not this scan’s entry ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)).

---

## 8. Score rules (06 executes; 02 names the math gate)

Inherit win definition and cost honesty from [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) §7–§8. Overrides for **this scan only**:

| Rule | Value |
|------|--------|
| Universe | **NIFTY**, **SENSEX** |
| Windows | §4 ladder. Do not skip to 5y. |
| OOS (180d / 365d / 730d / 5y) | Last **20%** of trades **inside that window** |
| Minimum for a **SCORE** pass | **≥ 30** OOS trades **per underlying × MIX × window**. Else `DATA_INSUFFICIENT` (cannot unlock 5y) |
| Win | `exit_open > entry_open` on the **option** (005 ITM) |
| **FAIL** (score windows) | OOS **win_rate < 45%**, **or** n_OOS < 30, **or** optimistic expectancy ≤ 0 |
| **SCREEN** (30d / 90d) | Report n + optimistic wr/exp. **Not** FAIL/PASS in the promote sense. **Not** a promote. |
| **5y unlock** | That MIX × underlying passed **730d** OOS wr ≥ 45% **and** optimistic exp > 0 |
| Not CANDIDATE | Costs `UNKNOWN` **and** multiple testing (§5). wr ≥ 45% with optimistic exp > 0 is **at most WEAK** / `UNVALIDATED` |
| Promote | **Forbidden** from this charter |
| SCORE_SAMPLE | `NORMAL` only when session tags exist ([`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md)). Until then `session_kind: UNKNOWN` |

Raw `(exit − entry)` expectancy is an **upper bound**. Optimistic exp ≤ 0 ⇒ **FAIL** (true exp worse). Optimistic exp > 0 does **not** pass after-cost invalidation. Do not invent brokerage / STT / half-spread to rank the scan. **Cannot CANDIDATE.**

Do **not** pick a scan MIX vs `MIX-GOKUL-003-009` vs `MIX-MTF-TREND` on in-sample or 30d wr.

---

## 9. What this does **not** do

- Does not waive Q8, Q12, Q4, Q19. Does not re-sign INDEX volume as FUTIDX VWAP.  
- Does not freeze 09:15–09:30 as HQ ORB. Does not freeze 3m as an HQ `interval`.  
- Does not code `packages/backtest` or live orders. Does not restart npm.  
- Does not score CAS-* / EQ-* / SO-* / BANKNIFTY. Does not delete STRAT-001–014.  
- Does not replace `MIX-DEFAULT-BUY`. Does not treat Docs Auditor PASS as a product gate.  
- Does not put P/L numbers in this file.

---

## 10. Coalition cites

| Team | File | Use |
|------|------|-----|
| **02** | [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) | P/L object, fill, 005 ITM cell B, 15:15 flatten, OOS/FAIL, costs optimistic |
| 02 | [`MIX_PROJECT_VALIDATION.md`](MIX_PROJECT_VALIDATION.md) · [`TA_FROM_TRANSCRIPTS.md`](TA_FROM_TRANSCRIPTS.md) · [`LIVE_OHLC_2026-09-03.md`](LIVE_OHLC_2026-09-03.md) | Later MIX vs this scan; ORB construction; INDEX VWAP UNKNOWN |
| 01 | [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) · [`TA_STRUCTURE_PACKET.md`](../../01_research/docs/handoffs/TA_STRUCTURE_PACKET.md) | 005 / 009; ORB/CPR spoken vs folklore |
| 03 | [`STRAT_001_014_MARKET.md`](../../03_phd_market/docs/STRAT_001_014_MARKET.md) · [`ROLLING_OPTION.md`](../../03_phd_market/docs/ROLLING_OPTION.md) | OPTIDX; 15:15 ≠ 15:40; NIFTY/SENSEX rollingoption |
| 04 | [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) · [`MIX_SCAN_2026-09-03.md`](../../04_quant/docs/MIX_SCAN_2026-09-03.md) · [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) · [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md) | Named MIX-WEB/PATTERN rows; default unchanged; ST/MACD/RSI confirm-or-kill |
| 05 | [`CUSTOMER_TALK.md`](../../05_analysis/docs/CUSTOMER_TALK.md) | News hold, not alpha |
| 06 | [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) · [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md) | No lookback p-hack; NORMAL score |
| 09 | [`ENGINE_MIX_REVIEW.md`](../../09_review/docs/ENGINE_MIX_REVIEW.md) | Notes ≠ pass |
| 00 | [`BOSS_AGENT.md`](../../00_orchestrator/docs/BOSS_AGENT.md) | Mandate ≠ claimed wr. Kill MIX only after 06 OOS+NORMAL |

**Still not `RESEARCH_READY_FOR_PROGRAMMING`.**
