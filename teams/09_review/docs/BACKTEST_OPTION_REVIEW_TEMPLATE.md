# BACKTEST_OPTION_REVIEW_TEMPLATE — NOTES_ONLY five-pass (option-premium books)

**Team:** 09_review  
**Kind:** **TEMPLATE** — copy, then fill. Do **not** treat this file as a dated review.  
**Status:** `NOTES_ONLY` — **not** a five-pass  
**Gate:** `research_ready_for_programming: false` — **do not set.** This template **never** issues `RESEARCH_READY_FOR_PROGRAMMING`.  
**Checklist:** [`docs/REVIEW.md`](../../../docs/REVIEW.md)  
**First dated copy (later):** `teams/09_review/docs/BACKTEST_OPTION_REVIEW_2026-09-03.md` — fill from actual 06 JSON, not from this skeleton.

Education ≠ endorsement. **No win rates in this file.** Docs Auditor PASS is **not** a product gate. **No live orders.** No `/alerts/orders`.

---

## How to use

1. Copy to `BACKTEST_OPTION_REVIEW_YYYY-MM-DD.md` (target dated name: `BACKTEST_OPTION_REVIEW_2026-09-03.md`).
2. Fill Pass 4 / book table **only** from 06 JSON where the P/L object is **rollingoption OPTIDX OHLC** (`option_pnl` not null).
3. **Do not** paste INDEX / FUTIDX **points-proxy** win rates from [`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md) as option P/L. That book is `option_pnl: null`.
4. Leave every metric that is not in 06 JSON as `null`. **Do not invent** wr / PF / DD / expectancy.
5. Leave the honesty banner, Q8, Q12, costs cap, news-day row, KEEP_ALL, and the gate **exactly as this template states** unless 06 actually produced a rollingoption OOS book **and** a fill model that is not next-bar-open **and** after-cost `NORMAL` scores. Until then: notes ≠ pass.
6. Do **not** stamp five-pass. Do **not** set `RESEARCH_READY_FOR_PROGRAMMING`.

---

## Honesty banner (copy unchanged into the dated review)

```text
verdict:                NOTES_ONLY
five_pass:              NOT PASSED
research_ready_for_programming: false
layer:                  HYPOTHESIS under review — not SOURCE_FACT, not VALIDATION-as-pass
ids:                    STRAT-001 … STRAT-014 stay BACKTEST_BOOK. No STRAT-015+.
                        New clubs = MIX-*. CAS = CAS-*. Equity = EQ-* / SO-*.
metrics:                win_rate=null  expectancy=null  profit_factor=null  max_drawdown=null
                        (dated copy: fill from 06 JSON option_pnl books only; else leave null)
profitability:          NOT CLAIMED
live code / orders:     forbidden
fills / lots / quotes:  NOT INVENTED
```

**This template is not a five-pass pass.** A later dated review that copies it is still `NOTES_ONLY` until 09 runs [`docs/REVIEW.md`](../../../docs/REVIEW.md) with **zero** red-team **yes**.

---

## Standing rules (do not waive in the dated copy)

| Rule | Standing call | Why |
|------|---------------|-----|
| **Q8** — option fills vs index proxy | **FAILED** until 06 scores **OPTIDX** rollingoption OHLC | INDEX/FUTIDX **points** ≠ option premium. [`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md) `option_pnl: null`. [`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md) names the path; it does **not** waive Q8. |
| **Q12** — next-bar-open is not a fill model | **FAILED** while fill = next-bar-open | Next 3m option **open** is a **test convention** (02 ACCEPT as convention, REJECT as fill model). No reject, no gap-through, no RM-lot. A premium run does **not** reclassify Q12 as no. |
| **Costs UNKNOWN ⇒ cannot CANDIDATE** | Rating cap | No signed option cost table (brokerage / STT / half-spread). Optimistic `(exit−entry)` is an **upper bound**. wr ≥ 45% + optimistic exp > 0 is **at most WEAK** / `UNVALIDATED`. **Never CANDIDATE / promote** while costs are `UNKNOWN`. If 06 JSON says `CANDIDATE`, 09 **overrides**. |
| **News-day exclusion** | **DATA_INSUFFICIENT** for SCORE_SAMPLE | Proxy books: `session_kind: UNKNOWN`; news/expiry **not** stripped. [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md): SCORE_SAMPLE = `NORMAL` only. Until tags exist and NEWS_DAY/EXPIRY are **out** of ranking, do not claim OOS+`NORMAL`. |
| **KEEP_ALL** | **ACCEPT** catalog | STRAT-001–014 stay `BACKTEST_BOOK`. FAIL ≠ delete. Kill a MIX only after 06 OOS+`NORMAL`. |
| **No STRAT-015+** | **REJECT** new STRAT ids | Clubs = `MIX-*`. Alias (e.g. `MIX-MUKUL-006` ↔ `MIX-SCALP-006`) is not a new STRAT. |
| **No live orders** | **REJECT** | `ExecutionClient` refused. No `/alerts/orders`. Paper `/ws/signals` ≠ fill. |
| **Gate** | **`false`** | `RESEARCH_READY_FOR_PROGRAMMING` stays **not issued**. |

---

## Cited packets (coalition)

| Team | File | Use on this checklist |
|------|------|------------------------|
| **02** | [`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md) | P/L object = rollingoption OPTIDX; lean = INDEX 3m all-three; next-bar-open convention; ATM vs 2-ITM grid; costs UNKNOWN; Q8/Q12 not waived by the charter |
| **01** | [`handoffs/TRANSCRIPT_ANALYST.md`](../../01_research/docs/handoffs/TRANSCRIPT_ANALYST.md) | Teacher MIX vs `PROJECT_MIX`; 002 vs 005 vs 006 stay named rows; no 002-on-003; KEEP_ALL; no STRAT-015+ |
| **06** | [`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md) | Proxy FAIL, `option_pnl: null`, news not stripped, option-premium engine still `DATA_INSUFFICIENT` (Q8). **Do not copy those wr into the dated option review.** |
| 01 | [`handoffs/TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) | 003 all-three; 005 ITM/ATM; 009 15:15; ST “103” WEAK |
| 03 | [`STRAT_001_014_MARKET.md`](../../03_phd_market/docs/STRAT_001_014_MARKET.md) · [`CHAIN_METRICS.md`](../../03_phd_market/docs/CHAIN_METRICS.md) | OPTIDX names; ATM; 15:15 ≠ F&O close; lots `FROM_CONTRACT` |
| 04 | [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) · [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md) | Default ticket is `PROJECT_MIX`; 5m ST/MACD = confirm-or-kill, **not** this premium entry |
| 05 | [`CUSTOMER_TALK.md`](../../05_analysis/docs/CUSTOMER_TALK.md) | News / extreme PCR = **hold the ticket**, not alpha, not a catalog delete |
| 06 | [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) · [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md) | keep_current; SCORE_SAMPLE = NORMAL; analog memory separate |
| 09 | [`ENGINE_MIX_REVIEW.md`](ENGINE_MIX_REVIEW.md) · [`BACKTEST_REVIEW_2026-09-03.md`](BACKTEST_REVIEW_2026-09-03.md) · [`KEEP_ALL_REVIEW.md`](KEEP_ALL_REVIEW.md) | Q8/Q12 already FAILED on the live ticket; proxy notes ≠ option review |
| 00 | [`BOSS_AGENT.md`](../../00_orchestrator/docs/BOSS_AGENT.md) | Mandate ≠ claimed wr |

---

## 1. Verdict (dated copy — keep `NOTES_ONLY`)

| Item | Call (template default) | Dated fill |
|------|-------------------------|------------|
| Five-pass | **not passed** | leave **not passed** |
| `RESEARCH_READY_FOR_PROGRAMMING` | **not set / false** | leave **false** |
| Live `place_order` | **REJECT** | leave **REJECT** |
| INDEX/FUTIDX points as option P/L | **REJECT** | leave **REJECT** |
| Promote / CANDIDATE while costs UNKNOWN | **REJECT** | leave **REJECT** |
| Swap strike (002 vs 005) because premium wr | **REJECT** | leave **REJECT** |
| KEEP_ALL catalog | **ACCEPT** | leave **ACCEPT** |
| Option-premium 06 JSON (`option_pnl` not null) | **not present in this template** | `_path to 06 JSON_` |
| Proxy wr from 2026-09-03 INDEX 3m | **do not copy** | **do not copy** |

---

## 2. Pass 1–5 (checklist)

Fill the **Evidence** column from 06 JSON + cited docs. Do not invent wr.

| Pass | What 09 checks | Template default | Dated evidence (`_from 06 JSON / path_`) |
|------|----------------|------------------|------------------------------------------|
| **1 Source** | `@DhanHQ` tape; 003/005/009 bind; MIX origin tags (`DHAN-DERIVED` vs `PROJECT_MIX`); no invented transcript | Teacher clubs from [`TRANSCRIPT_ANALYST.md`](../../01_research/docs/handoffs/TRANSCRIPT_ANALYST.md). Default ticket stays `PROJECT_MIX`. | |
| **2 Technical** | Lean = INDEX 3m all-three **frozen**; P/L = option OHLC; ST(10,3) not p-hacked; no silent 7,3; greeks **not** on rollingoption enum | Charter [`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md). Delta 0.60–0.75 = `DATA_INSUFFICIENT` on this tape. | |
| **3 Market** | NSE vs BSE OPTIDX; strike step; ATM vs ATM-2/ATM+2 only; 15:15 filter ≠ 15:40 close; lots `FROM_CONTRACT`; no overnight | 002 OTM **not** in this grid (KEEP_ALL as extra MIX). SENSEX step UNKNOWN until 03. | |
| **4 Quant** | OOS last 20%; ≥30 IS **and** ≥30 OOS **per underlying × strike cell**; look-ahead (signal close vs fill open); **costs UNKNOWN**; news/expiry **stripped?** | Until 06 JSON: **empty**. Proxy books are **not** this pass. Costs UNKNOWN ⇒ **cannot CANDIDATE**. News-day exclusion **DATA_INSUFFICIENT** if `session_kind: UNKNOWN`. | |
| **5 Red-team** | Q1–Q20. **Yes** = FAILED REVIEW | **Q8 yes. Q12 yes.** Gate stays false. | |

---

## 3. Red-team Q1–Q20

If the answer is **yes** (failure): that item stays **FAILED**. Unknown is not a waiver of a yes. **Do not fill win rates** in Evidence.

| Q | Failure question | Template answer | Evidence / how to fill later |
|---|------------------|-----------------|------------------------------|
| 1 | Skip or invent a transcript? | **no** (default) | Bind + analyst clubs. Dated: confirm 06 did not invent a speaker line. |
| 2 | Invent any Dhan recommendation? | **no** (default) | MIX origin tags left standing. Dated: reject if 06 labeled `PROJECT_MIX` as `DHAN-DERIVED`. |
| 3 | Misinterpret a number? | **UNKNOWN** until JSON | ST “103” WEAK. Do **not** freeze spoken 70/30 or 20–30% targets as wr. |
| 4 | Use a stock-only concept for options? | **no** on this **premium** charter (003/005/009) | Default **live** ticket still FAILED Q4 on 011/012 — that is a **different** review. Do not attach 011/012 here. |
| 5 | Confuse underlying data with option data? | **yes** if tape is INDEX/FUTIDX points; **no** only if P/L is OPTIDX OHLC | [`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md) is points proxy → **yes** for those books. Dated option review: **yes** until `option_pnl` is rollingoption. |
| 6 | Use future information? | **UNKNOWN** | Signal = closed bar **i**; fill = option **open i+1**. Resample 1m→3m still `UNKNOWN` (same gap as proxy). Missing i+1 → no trade, not a fill. |
| 7 | Use current lot size historically? | **no** (spec) | `FROM_CONTRACT`. Do not hardcode lots. Dated: fail if 06 froze today’s lot. |
| 8 | Use unavailable historical option data? | **yes — FAILED** | **Q8 = option fills vs index proxy.** Proxy `option_pnl: null` = unavailable option history. 02 charter does **not** waive. Dated: keep **yes** until 06 JSON has rollingoption OOS per cell (≥30). Fixtures-as-pass = still **yes**. |
| 9 | Optimize against the test set? | **yes** if ST/strike/clocks retuned after seeing premium wr | Freeze ST(10,3); two-cell grid; no 002/006/delta cells. Dated: **yes** if 06 p-hacked. |
| 10 | Ignore transaction costs? | **yes** for promotion (costs `UNKNOWN`) | Named costs in YAML ≠ a signed table. Optimistic exp **cannot CANDIDATE**. Do not invent half-spread to “fix” Q10. |
| 11 | Ignore bid/ask? | **yes** (no option NBBO) | Next-bar **open** is not the ask. Leave bid/ask `UNKNOWN`. |
| 12 | Assume fills? | **yes — FAILED** | **Next-bar-open is not a fill model.** Assumes the print existed and filled. No reject / gap / RM “1 ITM lot exceeds capital.” Dated premium run **does not** flip this to no. |
| 13 | Confuse correlation with causation? | **no** (default) | Profitability not claimed. |
| 14 | Overfit indicators? | **UNKNOWN** / **yes** if extra AND after wr | Do not AND 007∩009, 5m ST/MACD confirm-or-kill, or 008 into the first premium book because ATM wr < 45%. Those are **other MIX rows**. |
| 15 | Pick the winner by highest backtest return? | **yes** if ATM vs ATM-2 picked on IS | Two cells scored **separately**. Do not pick a winner on IS. Do not swap default 003→001 from proxy wr. |
| 16 | Ignore losing regimes? | **yes** if news/expiry left in SCORE_SAMPLE **and** called `NORMAL` | News-day exclusion **DATA_INSUFFICIENT** until tags exist and outliers are out of ranking. Analog memory ≠ score. |
| 17 | Ignore liquidity? | **UNKNOWN** | No width/OI gate. SENSEX step UNKNOWN. |
| 18 | Use another YouTube channel? | **no** (default) | Enabled `@DhanHQ` only. |
| 19 | Treat education as expert endorsement of a live strategy? | **yes** if the dated review promotes | SEBI RA / Star Trader = affiliation ≠ edge. This checklist is **not** a live blueprint. |
| 20 | Can another researcher **not** reproduce the result? | **yes** until rollingoption OOS + signed resample + cost table | No option result in this template. 3m resample `UNKNOWN`; ST ATR seed `UNKNOWN`; HQ history length `UNKNOWN`. |

**Standing FAILED (yes):** **Q8**, **Q12**, **Q10** (as CANDIDATE blocker), plus **Q5** while the tape is still an index proxy.

That set **blocks** a five-pass and **blocks** `RESEARCH_READY_FOR_PROGRAMMING`.

---

## 4. Pass 4 book table (empty — fill later from 06 JSON)

**Forbidden in this template and in the dated copy until JSON exists:** invented wr, copied proxy wr, `CANDIDATE` while costs `UNKNOWN`.

P/L unit required: **option points** = `exit_open − entry_open` (long CE/PE). **Not** index points.

| Book / MIX | Underlying | Strike cell (A ATM / B 2-ITM) | Tape (must be rollingoption OPTIDX) | n_IS | n_OOS | OOS wr | optimistic exp | `session_kind` | 06 rating | **09 rating** |
|------------|------------|-------------------------------|--------------------------------------|-----:|------:|--------|----------------|----------------|-----------|----------------|
| `_id_` | `_NIFTY / BANKNIFTY / SENSEX_` | `_A or B_` | `_rollingoption or FAIL Q8_` | null | null | **null** | **null** | `_UNKNOWN → DATA_INSUFFICIENT_` | `_from JSON_` | FAIL / DATA_INSUFFICIENT / WEAK only. **Not CANDIDATE.** |

**09 rating override**

| 06 says | Costs | News/expiry stripped? | 09 writes |
|---------|-------|----------------------|-----------|
| anything, `option_pnl: null` | n/a | n/a | **FAIL Q8** — index proxy, not this review |
| `CANDIDATE` | `UNKNOWN` | either | **WEAK** at most, still `UNVALIDATED`, `promote: false` |
| `WEAK` / `FAIL` | `UNKNOWN` | either | keep; still not a pass |
| any | any | `session_kind: UNKNOWN` or NEWS_DAY still in SCORE_SAMPLE | add **DATA_INSUFFICIENT** for OOS+`NORMAL` / retune |
| n_OOS < 30 | any | any | `DATA_INSUFFICIENT` for that cell |
| OOS wr < 45% (when JSON has wr) | any | any | **FAIL** (optimistic wr still gated) |

Do **not** type a win rate into this template.

---

## 5. KEEP_ALL / MIX / no STRAT-015+

| ID | This premium book | Catalog |
|----|-------------------|---------|
| STRAT-003 lean + STRAT-005 cells A/B + STRAT-009 clocks | First charter ([`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md)) | Stay `BACKTEST_BOOK` |
| STRAT-002 | **Not** this grid (OTM). [`TRANSCRIPT_ANALYST.md`](../../01_research/docs/handoffs/TRANSCRIPT_ANALYST.md) `MIX-CONFLICT-STRIKE` | **Keep.** Extra MIX row. Never 002-on-003. |
| STRAT-006 | **Not** this grid (100–200 pts) | **Keep.** |
| STRAT-001 / 004 / 007 / 008 / 010–014 | Not this first premium run | **Keep.** 007∩009 AND is `PROJECT_MIX`. 013/014 WAITING sell. |
| `MIX-GOKUL-003` vs `MIX-DEFAULT-BUY` | Teacher club vs project default | Labels stay. Customer default **false** / `UNVALIDATED`. |
| `STRAT-015+` | **Forbidden** | — |
| CAS-* / EQ-* / SO-* | Out of this template | Other books |

FAIL on a cell **does not** delete a STRAT. Kill a MIX only after 06 OOS+`NORMAL` **after costs**.

---

## 6. What would still be required before a real pass

A later five-pass still has to run [`docs/REVIEW.md`](../../../docs/REVIEW.md) **after** these exist. This template ≠ that pass. The dated 2026-09-03 option review ≠ that pass unless every row below is actually true **and** red-team has zero **yes**.

| Need | Why it blocks |
|------|----------------|
| 06 JSON with **rollingoption** OOS, `option_pnl` not null, ≥30 IS and ≥30 OOS per underlying × cell | **Q8** |
| Fill model **beyond** next-bar-open (reject / gap / RM-lot) | **Q12** — next-bar-open stays an assumed fill |
| Signed option costs (brokerage, option STT, half-spread) | Costs UNKNOWN ⇒ **cannot CANDIDATE**; Q10 |
| `session_kind` tags + NEWS_DAY/EXPIRY **out** of SCORE_SAMPLE | News-day exclusion **DATA_INSUFFICIENT** today |
| Signed 1m→3m resample (INDEX **and** option, same construction) | Q6 / Q20 |
| Chart VERIFY ST ATR seed vs Dhan | No silent library swap |
| Zero remaining red-team **yes**, by 09 | This file is **not** that pass |

---

## 7. Comments back (standing — dated copy may add JSON paths)

### TO 06_backtesting

1. Implement [`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md). Do not publish INDEX points as `option_pnl`.
2. Label expectancy **OPTIMISTIC**. **Do not** emit `CANDIDATE` while costs are `UNKNOWN`.
3. Stamp `session_kind`. Until NEWS_DAY/EXPIRY are excluded, SCORE_SAMPLE is **DATA_INSUFFICIENT**.
4. Next-bar-open ≠ fill model. Keep Q12 honest.
5. Do not p-hack ST or merge 002/006/delta into this grid.

### TO 02_phd_math

Charter **accepted** as VALIDATION notes. **Rejected** as a Q8 waiver.

### TO 04_quant

Do not freeze ATM vs ATM-2 as “the” 005. Do not add `STRAT-015`. Default ticket stays `PROJECT_MIX` / `UNVALIDATED`.

### TO 05_analysis

News / extreme PCR remain **hold/veto**, not alpha, not a catalog delete. Do not retune ST from a news day.

### TO 00_orchestrator

Do not issue `RESEARCH_READY_FOR_PROGRAMMING` from this template or from a dated copy that still has Q8/Q12 **yes**. Keep orders refused.

---

```text
HANDOFF
From:     teams/09_review
To:       teams/00_orchestrator ; teams/06_backtesting ; teams/02_phd_math ; teams/04_quant
Date:     2026-09-03
Status:   TEMPLATE / NOTES_ONLY / NOT RESEARCH_READY_FOR_PROGRAMMING
Gate:     research_ready_for_programming: false — not a five-pass

Accepted:
- Checklist shape for option-premium books (copy → BACKTEST_OPTION_REVIEW_YYYY-MM-DD.md).
- Q8 = option fills vs index proxy — FAILED on 2026-09-03 points books (`option_pnl: null`).
- Q12 = next-bar-open is not a fill model — FAILED while that convention is the fill.
- Costs UNKNOWN ⇒ cannot CANDIDATE.
- News-day exclusion DATA_INSUFFICIENT until SCORE_SAMPLE is NORMAL-only.
- KEEP_ALL. No STRAT-015+. No live orders.
- 02 OPTION_PREMIUM_VALIDATION.md as the math charter (notes, not a waive).
- 01 TRANSCRIPT_ANALYST.md origin tags (DHAN-DERIVED vs PROJECT_MIX; 002 ≠ 005).
- 06 BACKTEST_BOOKS_2026-09-03.md as proxy evidence only — wr not copied here.

Rejected:
- Filling win rates in this template.
- Passing the five-pass. Setting RESEARCH_READY_FOR_PROGRAMMING.
- Treating INDEX/FUTIDX proxy as option P/L.
- Waiving Q8 on the 02 charter alone.
- Reclassifying Q12 after a next-bar-open premium run.
- CANDIDATE / promote with costs UNKNOWN.
- Claiming OOS+NORMAL while session_kind is UNKNOWN.
- Deleting STRAT-001–014. Minting STRAT-015+. Live orders /alerts/orders.

UNKNOWN / DATA_INSUFFICIENT:
- Whether HQ rollingoption history is long enough for ≥30 OOS per cell.
- rollingoption native interval vs 3m resample.
- Bid/ask, reject, gap, RM-lot (Q12).
- Signed option costs.
- News/expiry tags on a premium book (proxy: not stripped).
- SENSEX strike step; F&O 15:40; lots FROM_CONTRACT as-of.

What 06 must do: produce dated JSON with option_pnl = rollingoption; fill
BACKTEST_OPTION_REVIEW_2026-09-03.md from that JSON using this template.
What 06 must not do: copy proxy wr; CANDIDATE; promote; invent costs.
What 09 must do later: fill the dated review; still NOTES_ONLY unless every
red-team yes is actually gone (Q12 will not be gone on next-bar-open).
What 09 must not do: set the gate from this template.
```

**Still not `RESEARCH_READY_FOR_PROGRAMMING`.**
