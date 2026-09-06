# STRAT-001–014 — independent VALIDATION (math)

## Live INDEX 5m OHLC (2026-09-03)

**Status:** `UNVALIDATED`. **Not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Full note:** [`LIVE_OHLC_2026-09-03.md`](LIVE_OHLC_2026-09-03.md).

Live `/charts/intraday` **5m INDEX** `IDX_I` 13/25/51 returned `has_volume: true`. 06 ran VWAP+VWMA+ST all-three on that **INDEX** volume. Spoken STRAT-003 is **FUTIDX 3m**. **INDEX volume for VWAP = `UNKNOWN` — do not treat as FUTIDX tape.** HQ-native **5m** ≠ spoken **3m**. NIFTY **425** bars / CE **108** / PE **137** / SKIP **130** are **compute counts, not win rates**.

---

## KEEP_ALL re-sign

**Date:** 2026-09-03  
**Layer:** `VALIDATION`. Catalog is 04 `HYPOTHESIS`.  
**Status:** `DRAFT` / `UNVALIDATED`. **Not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Reads:** [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) (honesty + KEEP_ALL + MIX IDs); [`cas/CAS_STRATEGIES.md`](../../03_phd_market/cas/CAS_STRATEGIES.md) header (CAS-* = close-bias, not CE fills). 06 [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md): **score `NORMAL` only** — 02 invents no metrics.

| Choice | 02 | Note |
|--------|----|------|
| KEEP_ALL (STRAT-001–014 never deleted) | **ACCEPT** | Disagreement = extra **MIX / grid**, not a kill. `BACKTEST_BOOK` / `WAITING` / `PARKED` are catalog states, not math proofs. |
| `MIX-*` as test IDs | **ACCEPT** as **HYPOTHESIS** | A MIX is **not** a theorem and **not** a STRAT. `MIX-DEFAULT-BUY` stays `PROJECT_MIX`. Same-video `MIX-GOKUL-003` may be DHAN-DERIVED **clubbing**, still UNVALIDATED. |
| `MIX-SCALP-004` | **ACCEPT as grid** | Lengths still `UNKNOWN` / `NOT_IN_EN`. **Do not invent 9/21.** PARKED ≠ deleted. |
| 003 Supertrend **“103”** | still **WEAK** | Compute 10,3 remains **inference**, not spoken “ten comma three.” |
| 007 ∧ 009 AND | still **`PROJECT_MIX`** | Backtest **007 alone**, **009 alone**, **and** the AND (`MIX-DEFAULT-BUY`). Do not freeze the intersection as spoken. |
| `CAS-*` | **not 02 theorems** | Close-bias / microstructure (03). No IEP / imbalance **series** in HQ. Must not promote to CE/PE fill. Pointer `MIX-CAS` only. |

No win rates. No STRAT-015+. 06 may **queue** MIX IDs on fixtures; scoring sample = **`NORMAL`** only (06). This section does **not** issue `RESEARCH_READY_FOR_PROGRAMMING`.

---

## Transcript bind re-sign (English)

**Date:** 2026-09-03  
**Layer:** `VALIDATION` only. Bind tags stay 01 `SOURCE_FACT`. Mix stays 04 `HYPOTHESIS`.  
**Status:** `DRAFT` / `UNVALIDATED`. **Not** `RESEARCH_READY_FOR_PROGRAMMING`. No win rates.  
**SOURCE_FACT authority:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md). English `normalized_en/` **wins**. **Do not cite STRAT-file timestamps as spoken.** ENGINE_MIX default ticket: [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) § Transcript bind + default BULL/BEAR.

This pass **re-signs** math against that bind + the named mix. CONFIRMED in the bind is **not** a math theorem. WEAK / CONFLICT / NOT_IN_EN stay **grids or park**. `PROJECT_MIX` is **not** a spoken recipe and is **not** a 02 theorem.

| Item | Bind (01) | 02 re-sign (VALIDATION) |
|------|-----------|-------------------------|
| **003 spoken 3m** futures all-three | **CONFIRMED** (`2RnBT9DDDNI` 20:57–22:28, 25:13–26:07) | Spoken TF **accepted as SOURCE_FACT**. HQ charts enum `{1, 5, 15, 25, 60}` — **3m remains a VALIDATION gap**. Compute later = resample `HYPOTHESIS` (do not pick a winner). Do **not** freeze `signal: 5m` as if it were Gokul’s primary. |
| **003 Supertrend “103”** | **WEAK** (`2RnBT9` 21:53–21:57). Digits **10, 3 inferred**, not spoken “ten comma three.” `H_6kee` “10 3” is CONFIRMED on **stock/gold**, not this futures class. | **ACCEPT WITH GRID.** A later FUTIDX compute of TV-style ATR(10)×3 is **inference**, **not** a frozen 2Rn quote. Do not present 10,3 as spoken on 003. Chart mismatch → `partially_supported`, no silent swap. **7,3** stays equity / not imported. |
| **003 VWAP + VWMA 20** | Structure CONFIRMED; VWMA length **20** spoken | Session VWAP + VWMA_20 `supported` as math **on FUTIDX volume**. Cash-index VWAP `unsupported`. Typical-price vs close `UNKNOWN`. |
| **004 Super Scalper lengths** | Structure CONFIRMED; lengths **NOT_IN_EN** / `UNKNOWN` | **Park.** Do **not** invent 9/21. 1m premium EMA cross is defined; identity of Dhan Super Scalper is `UNKNOWN` without lengths. |
| **001 MACD ×3 vs ×4** | Recipe CONFIRMED; multiplier **WEAK** (`HAUSZx` 45:37–46:04) | **Search grid.** Do not freeze 48/104/36. Signal **9** not clearly spoken — Appel 12/26/9 is VALIDATION convention, not Dhan-spoken. Staging 12/26/9 (if used) stays **labeled convention** on the `PROJECT_MIX` confirm path. |
| **001 MA 100 vs 300** | **CONFLICT** (same speaker, same video) | **Search grid.** Do **not** silently correct. 9 vs 10 trail is **WEAK** — same rule. `EMA_9` is not an annexure token. |
| **001 2h parent** | **NOT_IN_EN** on HAUS (15m child alt **is** spoken) | Do not validate a 2h HAUS parent. 2h lives on `gA5` (different recipe). |
| **005 vs 002 strike** | 005 ITM/ATM CONFIRMED; 002 slightly-OTM CONFIRMED; overlay 002-on-003 **CONFLICT** | Pairing 003→005, 001→002 **accepted**. Merge **rejected**. 005 delta **0.60–0.75** is bind **WEAK** — grid, not identity. Delta ≠ win rate. |
| **007 ∧ 009** (no new 09:15–**10:00**, no new after **14:30**, flatten **15:15**) | **PROJECT_MIX** — two speakers; Gokul **starts 09:45** | **Not a math theorem.** Intersection is a third clock hypothesis. 02 does not freeze it as spoken. |
| **5m ST/MACD confirm-or-kill** | **PROJECT_MIX** (desk). HAUS child MACD **is entry**. Gokul entry is **3m** all-three. | **Not a math theorem.** Keep `H-STAGING-CONFIRM` ≠ `H-001-HAUS-ENTRY`. Do not average. |
| **011 / 012 / 010 gate** | **PROJECT_MIX** (stock/gold → index; pattern overlay; OF-as-003-gate) | Transfers are not theorems. 011 ST 10,3 CONFIRMED on **H_6kee stock/gold**, not as 003’s spoken digits. 010 history `DATA_INSUFFICIENT`. |
| **013 / 014** | **CONFIRMED sell** | Structure math only. **WAITING.** Not Phase-1 buy. POP / win-rate claims `unsupported`. |

**Default ENGINE_MIX ticket** (`003 + 007/008/009 + staging 5m ST/MACD + 005`): Gokul same-video **003/005/008/009** may be one class; adding Himanshu **007** and desk staging is **`PROJECT_MIX`**. 02 will not sign that AND as a transcript or as a theorem.

---

## 02 SIGN-OFF ON ENGINE_MIX (2026-09-03)

**Status:** `DRAFT` / `UNVALIDATED`. Notes ≠ pass. **Not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Reads:** [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md), [`STRAT_001_014_MARKET.md`](../../03_phd_market/docs/STRAT_001_014_MARKET.md), [`SIGNAL_FUSION.md`](../../05_analysis/docs/SIGNAL_FUSION.md).  
**No params invented. No series REST claimed.**

| Mix choice | 02 verdict | Why (math only) |
|------------|------------|-----------------|
| **003 primary** (FUTIDX VWAP+VWMA20+ST compute) | **ACCEPT WITH GRID** | See § Transcript bind re-sign. Spoken **3m CONFIRMED**; HQ enum gap remains. ST digits **“103” WEAK** — 10,3 is **inference**, not spoken “ten comma three.” Cash-index VWAP `unsupported`. **7,3** not imported. |
| **5m ST/MACD confirm-or-kill** vs **001 HAUS child-MACD entry** | **ACCEPT** split; **REJECT** collapse | Staging 5m ST/MACD = **PROJECT-DERIVED** desk hypothesis (`SIGNAL_STAGING`). HAUS 5m/10m MACD hist + buy-the-candle-high = **001-alt entry** (`H-001-HAUS-ENTRY`). Different objects. Customer CONFIRMED gate must **not** be HAUS entry. 001 **1h parent** as WATCH-only on the 003 ticket: **ACCEPT**. Staging MACD named **12/26/9**: **ACCEPT WITH GRID** as *one labeled Appel compute* — **9 was not spoken**; do **not** freeze as “Dhan said.” HAUS ×3/×4 and 6E 24/52 stay **001-alt grids**, not this mix. Histogram construction `UNKNOWN`. |
| **005 strike with 003**; **002 only on 001-alt** | **ACCEPT** pairing; **REJECT** merge | Spoken conflict (ITM/ATM vs OTM). Delta ≠ win rate. Vendor `greeks.*` `UNKNOWN`. 005 band 0.60–0.75 vs spoken 0.63–0.74 stays **grid**, not a frozen unique. Never 002+005 on one ticket. |
| **Park 004 and 010** | **ACCEPT** | 004 Super Scalper lengths `UNKNOWN` — do not invent 9/21. 010 OF history `DATA_INSUFFICIENT`; volume-delta ≠ Greek delta. |

**Will not let 04 freeze (math contradictions):**

1. **3m as an HQ `interval`**, or YAML `signal: 5m` silently rewriting 003’s spoken 3m primary.  
2. **HAUS child-MACD entry = staging confirm-or-kill** (one hypothesis, averaged params, or CONFIRMED from 5m MACD with no leading pair).  
3. **One “Dhan strike”** (002+005, or 005 delta band treated as identity).  
4. **MACD ×3/×4 integers, MA 100 vs 300 / 9 vs 10, MACD signal=9 as spoken, ST 7,3 on the index book, Super Scalper 9/21.**  
5. **Cash-index volume VWAP**; `average_price`/ATP as session VWAP series; `EMA_9` / `SUPERTREND_10_3` as annexure tokens.  
6. **007 AND 009 as “speakers agreed.”** Conservative intersection (no new 09:15–10:00, no new after 14:30, flatten 15:15) is a **third clock hypothesis** — **ACCEPT WITH GRID** only if labeled that way; 14:30 vs 14:45 vs 15:00 and flatten 15:15 vs F&O 15:40 stay 03’s parameters, not 02 freeze.  
7. **Win rates, POP, conviction=delta, 70/30, 93/7** as theorems. **013/014 as Phase-1 buy.** Relabeling **011/012** DHAN-DERIVED.

**Compute path 02 will own later (not this ticket):** FUTIDX OHLC+volume → session VWAP, VWMA(20), ST(10,3), Appel MACD — compared to Dhan **charts**, never claimed as hidden REST. 04 mix is **not** rejected for lacking series REST.

**05 fusion:** news / extreme PCR as **veto** is outside 02; no math objection. 05 must not invent PCR numeric laws or promote CONFIRMED.

---

**Team:** 02_phd_math  
**Date:** 2026-09-03  
**Status:** `DRAFT` / `UNVALIDATED`. Concepts only. **Not** a strategy approval.  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. 09 five-pass has **not** passed. Notes ≠ pass.  
**Layers (do not collapse):** `SOURCE_FACT` (01 packets + 04 STRAT files) / `VALIDATION` (this file) / `HYPOTHESIS` (04 freeze — not this ticket).

No live trading. No coded signals. No Dhan calls. No win rates. No `STRAT-015+`. Books (`config/workspace.yaml` `sources.books`: Murphy *TA of the Financial Markets*; Natenberg *Option Volatility and Pricing*) are **VALIDATION tags only** — they do **not** create new STRATs and they do **not** license a non-Dhan Supertrend as “the Dhan indicator.”

Hard HQ facts used below (do not violate):

- No Supertrend / RSI / MACD / EMA9 **series** REST. Annexure EMA set is `{5,10,20,50,100,200}` — **`EMA_9` is not in the annexure.**
- Charts intervals **1, 5, 15, 25, 60**. Spoken **2m / 3m** = resample `HYPOTHESIS`.
- Conditional Trigger names (if any) are **Equities and Indices** conditions, not a historical series, **not** documented for OPTIDX scanners, **not** live `/alerts/orders`.

Companions: [`TA_FROM_TRANSCRIPTS.md`](TA_FROM_TRANSCRIPTS.md), [`DHAN_INDICATOR_API_MAP.md`](DHAN_INDICATOR_API_MAP.md), [`VALIDATION_MATH.md`](VALIDATION_MATH.md). Spoken TA: [`TA_STRUCTURE_PACKET.md`](../../01_research/docs/handoffs/TA_STRUCTURE_PACKET.md). Layer C pointers only: [`OPTIONS_INDEX_PACKET.md`](../../01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md) §Layer C. **English bind (SOURCE_FACT authority):** [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md). Specs: [`MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md), [`ALGO_HANDOFF.md`](../../04_quant/docs/ALGO_HANDOFF.md), [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md), `teams/04_quant/docs/candidates/STRAT-001.md` … `STRAT-014.md`.

**Spoken timestamps:** use [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) only. **Do not copy STRAT-file timestamps as English.** Per-ID sections below that still quote STRAT yaml times are **historical**; the bind + § Transcript bind re-sign win on conflict.

---

```text
HANDOFF
From:     teams/02_phd_math
To:       teams/04_quant ; teams/03_phd_market ; teams/09_review
Date:     2026-09-03
Status:   DRAFT / UNVALIDATED (independent math pass on existing 14 IDs)
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted:
- Fourteen existing IDs only. No new STRATs from Murphy/Natenberg or from this pass.
- VWAP/VWMA/ST/MACD/EMA/RSI series = our later OHLC compute, never a hidden REST field.
- STRAT-011 / 012 stay PROJECT-DERIVED transfers.
- STRAT-013 / 014: structure math only; WAITING sell; not Phase-1 buy.
- STRAT-010 OF history: DATA_INSUFFICIENT.

Rejected:
- Freezing MACD ×3 vs ×4, MA 100 vs 300, Super Scalper lengths, 2m/3m as HQ intervals.
- Cash-index volume as a VWAP tape.
- Conviction = delta; POP 80–85%; 70% seller-win as theorems.
- Promoting 013/014 into the buy UI; relabeling 011/012 as DHAN-DERIVED index recipes.

UNKNOWN / DATA_INSUFFICIENT:
- Dhan chart Supertrend ATR seed / HL2 vs close; MACD signal length; RSI Wilder vs Cutler.
- Super Scalper fast/slow EMA periods (004).
- Order-flow historical footprint on HQ (010).
- Vendor IV / Greeks engine (005, 002, 013, 014).
- 2m/3m resample method; F&O flatten 15:15 vs 15:30/15:40 (03 owns clocks).

What 04 must do: treat freeze vs grid vs do-not-use per ID below. Do not pick a grid winner on IS.
What 03 must do: confirm the market object named per ID (FUTIDX vs OPTIDX premium vs chain vs cash index).
What 09 must do: this file is notes, not a five-pass. Do not issue RESEARCH_READY_FOR_PROGRAMMING from it.
```

---

## Index (math only — not an edge ranking)

| ID | Math verdict | HQ surface (primary) | Compute later? | 04 comment |
|----|--------------|----------------------|----------------|------------|
| STRAT-001 | `partially_supported` | `OHLC_COMPUTE` (+ MACD trigger names, not series) | Yes, **with grid** | **grid** — do not freeze ×N / 100 vs 300 |
| STRAT-002 | `context-dependent` | chain LTP/delta — not a TA token | Overlay yes; delta engine `UNKNOWN` | **grid** OTM vs 005; do not merge strikes |
| STRAT-003 | `partially_supported` | `CHART_ONLY` ST/VWAP; compute from FUTIDX | Yes on **FUTIDX** volume; 3m = resample | **grid** resample; **do-not-use** cash-index VWAP |
| STRAT-004 | `UNKNOWN` | `CHART_ONLY` Super Scalper | **No** until lengths exist | **do-not-use** (do not invent 9/21) |
| STRAT-005 | `context-dependent` | chain `greeks.delta` — methodology `UNKNOWN` | Strike map yes; delta identity no | **grid** 0.60–0.75 vs 0.63–0.74; ablate vs 002 |
| STRAT-006 | `partially_supported` | `OHLC_COMPUTE`; **2m = unsupported HQ interval** | Yes, **with resample grid** | **grid** 1m/5m vs 2m resample; no `EMA_9` |
| STRAT-007 | `context-dependent` | n/a (bar timestamps) | Yes (clock filter) | **grid** 14:30 / 14:45 / 15:00; **do not merge** with 009 |
| STRAT-008 | `context-dependent` | n/a (three FUTIDX signs) | Partial: skip-if-disagree yes; “dominant” `UNKNOWN` | **freeze** no-both-sides; **grid** / do-not-use silent “dominant” |
| STRAT-009 | `context-dependent` | n/a (bar timestamps) | Yes (clock filter) | **do not merge** with 007; flatten clock → 03 |
| STRAT-010 | `partially_supported` (delta def) / `DATA_INSUFFICIENT` (history) | `DATA_INSUFFICIENT` | **No** on HQ history | **do-not-use** for backtest |
| STRAT-011 | `context-dependent` | `OHLC_COMPUTE` (RSI/ST not series REST) | Yes as **PROJECT-DERIVED** compute | **grid**; keep transfer label; not Phase-1 “Dhan NIFTY recipe” |
| STRAT-012 | `context-dependent` | `OHLC_COMPUTE` (no pattern REST) | Hammer yes; four patterns `WAITING_FOR_EDIT` | **grid** wick 2–3×; keep **PROJECT-DERIVED** |
| STRAT-013 | `supported` (vertical payoff) | chain (not TA) | Structure yes; **WAITING sell** | **do-not-use** Phase-1 buy; do not convert to 011 |
| STRAT-014 | `supported` (1-3-2 payoff if basket) | chain (not TA) | Structure yes; **WAITING sell** | **do-not-use** Phase-1 buy; POP **unsupported** |

Desk staging (04, not a transcript theorem): 5m Supertrend / MACD / RSI = **confirm or kill**, not entry ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)). HAUS **child-TF MACD as entry filter** (001) is a **different hypothesis** — do not collapse.

---

## STRAT-001 — Dual-TF MACD + MA stack, long premium

- **strategy_id:** `STRAT-001`  
- **Origin tag (04):** `DHAN-DERIVED`  
- **Spoken recipe (from STRAT file):** `HAUSZx-hYdY` 41:32–01:03:10. Parent 1h: MACD histogram > 0 **and** MA(10) > MA(30) > MA(100); child 5m same; buy CE on break of that 5m candle high. Bear: invert histogram and MA stack; buy PE. MACD spoken 12/26 then ×3 or ×4 all params, histogram only. 10m child / 2h·15m parent spoken as alts in the YAML.  
- **Math verdict:** `partially_supported`  
  - Appel MACD = EMA_fast − EMA_slow; hist = MACD − signal is **supported** as definition (Murphy / Appel). Histogram **sign** as a complete regime classifier is only `partially_supported` ([`VALIDATION_MATH.md`](VALIDATION_MATH.md)).  
  - MA stack 10 > 30 > 100 as a **trend heuristic** is `supported` as language, **no optimality**.  
  - Linear ×3 / ×4 of periods is `context-dependent` (filter choice, not a theorem). Signal length **9** is a VALIDATION convention — **not clearly spoken** in HAUS.  
- **HQ surface:** `OHLC_COMPUTE`. Trigger names `MACD_12` / `MACD_26` / `MACD_HIST` exist as **conditions**, not a series. **No** `MACD_9` / `MACD_SIGNAL`. SMA/EMA annexure includes 10, 100 — **not** 30. Do not send `EMA_9` or `SMA_30` as `indicatorName`. Parent **60** and child **5** are in the HQ interval enum; **10m / 2h / 15m-as-child-of-2h** are resample `HYPOTHESIS`.  
- **Implementable compute:** **FUTIDX** OHLC close (NIFTY/BANKNIFTY NSE_FNO; SENSEX BSE_FNO). Speaker examples were stocks/spot — that does **not** license cash-index **volume**. This ID does not need volume. Execution hypothesis = **OPTIDX** premium (04).  
- **Search grid (`[UNCERTAIN_TRANSCRIPT]` / SOURCE_UNCERTAIN — do not pick a winner):** MACD `{12/26/9, 36/78/27, 48/104/36}`; MA fast `{9, 10}`; slow stack `{100, 300}`; child `{5m, 10m}`. Do **not** merge with `6E_K1wVkHyw` 24/52 (different spoken recipe).  
- **TO 04_quant:** **grid**. Do not freeze ×4 or MA 300. Do not treat 5m MACD as both HAUS **entry** and desk **confirm-or-kill** without naming two hypotheses. Attach 002 / 007 as overlays only.  
- **TO 03_phd_market:** Assume **FUTIDX** as the MACD/MA object; **OPTIDX** as the vehicle. Hourly = HQ `60`. Universe in HAUS was also NIFTY-100 **stocks** — Phase-1 index book must not silently use that universe.

---

## STRAT-002 — Slightly OTM, 20–30% premium target (overlay)

- **strategy_id:** `STRAT-002`  
- **Origin tag (04):** `DHAN-DERIVED`  
- **Spoken recipe (from STRAT file):** `HAUSZx` 57:40–01:02:19. Select **1 or 2 strikes OTM**; speaker: ATM most “pumped”; OTM gets long gamma if it becomes ATM. Adverse-case delta ~0.40. Target **20–30%** of entry premium. Trail: MA 9 or 10 vs 30 against. Beginner rupee stop **1500–1700 vs 2500** target — `[UNCERTAIN_TRANSCRIPT]`. Overlay on 001 (or 003), not standalone. **Conflict:** 2RnBT9 / pvmvki prefer ITM.  
- **Math verdict:** `context-dependent`  
  - Qualitative gamma/time-value story is `partially_supported` as Natenberg **risk language** (OTM can reprice sharply if it becomes ATM; ATM often richer in time value). It is **not** a strike-selection theorem.  
  - 20–30% of premium and rupee stops are **spoken parameters**, not expectancy proofs ([`VALIDATION_MATH.md`](VALIDATION_MATH.md)).  
  - “Conviction = delta” is `unsupported` as identity (delta ≠ frequentist win probability of the setup).  
- **HQ surface:** not a TA token. Needs option-chain **LTP / bid / ask** (and delta if used). Vendor `greeks.*` / IV methodology = `UNKNOWN`. Trail MA-9 = **`unsupported` token** on Conditional Trigger (`EMA_9` absent). Trail compute = `OHLC_COMPUTE` on the **underlying**, not on a random OTM premium unless a separate spec says so.  
- **Implementable compute:** **OPTIDX** premiums for target/stop in rupees; **FUTIDX or index** OHLC for the MA trail. **Forbidden:** cash-index volume. Do not VWAP the strike.  
- **Search grid (do not pick a winner):** OTM **1 vs 2** strikes; target **20% vs 30%**; trail **MA 9 vs 10** vs 30; rupee stop band as tagged uncertain; **ablate OTM vs ATM vs ITM** against 005/006 — do **not** merge into one “Dhan strike.”  
- **TO 04_quant:** **grid** (strike overlay). Freeze nothing that collapses 002 vs 005. Do not ship `EMA_9` as an HQ trigger.  
- **TO 03_phd_market:** Assume **OPTIDX** as the P/L object; moneyness vs **spot** (HAUS pedagogy) vs futures basis is yours. Index options are **European, cash-settled** — “exercise now into NIFTY” is teaching, not a mechanic ([`VALIDATION_MATH.md`](VALIDATION_MATH.md)). SENSEX = BSE chain.

---

## STRAT-003 — Futures VWAP + VWMA(20) + Supertrend(10,3)

- **strategy_id:** `STRAT-003`  
- **Origin tag (04):** `DHAN-DERIVED`  
- **Spoken recipe (from STRAT file):** `2RnBT9DDDNI` 20:57–40:56. Chart = **index futures**, **3m**. Session VWAP (default); VWMA length **20**; Supertrend ATR **10**, multiplier **3**. Call if close > VWAP **and** VWMA **and** Supertrend; put if close < all three. If Supertrend side ≠ VWAP side → **no new** entry. Exit: 3m close through Supertrend. Ignore 09:15–09:45; flatten before 15:15. Strike overlay = 005 (ITM/ATM; OTM not recommended **in this video**).  
- **Math verdict:** `partially_supported`  
  - Session VWAP = Σ(P·V)/ΣV from session open is `supported` **on a traded tape** (Murphy volume-weighted price language; [`TA_FROM_TRANSCRIPTS.md`](TA_FROM_TRANSCRIPTS.md)). **Typical price vs last vs trade print** used by Dhan charts = `UNKNOWN`.  
  - VWMA_20 is `supported` as a definition and is **not** session VWAP.  
  - Supertrend ATR(10)×3 close-flip is `supported` as a **common TV-style default**, **not** unique truth and **not** an HQ field. Alternate 10×1 / 10×2 exist in the same education corpus.  
  - Cash **NIFTY 50 / SENSEX index volume VWAP** = `unsupported` / misuse.  
- **HQ surface:** `CHART_ONLY` (Supertrend, session VWAP, VWMA — **not** annexure names). Do **not** invent `SUPERTREND_10_3`. Quote `average_price` = day VWAP **snapshot** (`partially_supported`) — identity vs chart session VWAP = `UNKNOWN`. Charts OHLC+volume = input to `OHLC_COMPUTE`. Interval **3** is an **unsupported HQ token**; resample from **1m** is `HYPOTHESIS`.  
- **Implementable compute:** **FUTIDX OHLC + that future’s volume**. Never IDX_I / cash-index volume. Strike mapping may use spot **level** (spoken) without using spot **volume**. Execution = **OPTIDX**.  
- **Search grid (do not pick a winner):** 3m resample method (OHLC from 1m) — do not freeze one resample as “Dhan 3m.” ST **10,3** is the **repeated** spoken default in this video; `_byuht38r5s` “7 is 3” is a **different** stock-scanner line — **do not silently swap**, and do not freeze 7,3 on this ID. Typical-price vs close for VWAP. Flatten 15:15 vs F&O close (03).  
- **TO 04_quant:** **grid** the 3m resample; **do-not-use** any cash-index VWAP path. ST(10,3) may be a **working compute default** only after chart `VERIFY` vs Dhan — mismatch → `partially_supported` / `SOURCE_UNCERTAIN`, no silent library swap. Attach 008 / 009. 5m ST as desk confirm-or-kill is **not** this video’s 3m entry.  
- **TO 03_phd_market:** Market object = **FUTIDX** (NSE_FNO NIFTY/BANKNIFTY; **BSE_FNO** SENSEX). Vehicle = **OPTIDX**. Spoken flatten **15:15** vs docs F&O **15:40** / CAS **15:15–15:35** on cash names = your clock `VERIFY`. Do not combine NSE+BSE volume.

---

## STRAT-004 — Premium Super Scalper Fast/Slow EMA (confirm)

- **strategy_id:** `STRAT-004`  
- **Origin tag (04):** `DHAN-DERIVED`  
- **Spoken recipe (from STRAT file):** `2RnBT9DDDNI` 47:16–55:15. Confirmation **after** 003 (or 001) direction. **1-minute option LTP.** Long call: price above both EMAs; take **buy** signals only when fast > slow; ignore “sell the call” as a short. Stop below slow EMA. **Numeric fast/slow periods NOT spoken.** STRAT file already `DATA_INSUFFICIENT` (lengths UNKNOWN).  
- **Math verdict:** `UNKNOWN` (identity of the product). Fast/slow EMA cross as a **definition** is `supported`; without lengths there is **no unique series** to validate against Dhan Super Scalper.  
- **HQ surface:** `CHART_ONLY` (Dhan Super Scalper product). **Not** annexure. 1m **is** in `{1,5,15,25,60}`. Inventing `EMA_9` / 9/21 / 8/21 as “what Dhan used” = **unsupported token**.  
- **Implementable compute:** **OPTIDX 1m OHLC** (premium tape) **if and only if** lengths are recovered from chart export / Tier 2. **Forbidden:** cash-index volume; using FUTIDX EMA as a silent substitute for the premium indicator.  
- **Search grid:** **none that picks a winner.** Lengths stay `UNKNOWN`. A later chart-read may **record** what tv.dhan.co Super Scalper shows — that recording is still `UNVALIDATED`, not a freeze.  
- **TO 04_quant:** **do-not-use** until lengths are documented. Do **not** invent 9/21. Invalidation already in the STRAT file: cannot reproduce indicator → stay `DATA_INSUFFICIENT`.  
- **TO 03_phd_market:** Market object for the EMA pair = **OPTIDX premium** (1m). Direction lock remains **FUTIDX** from 003/001. Spread/wick vs futures stop disagreement is microstructure, not a 02 theorem.

---

## STRAT-005 — High-delta ITM / ATM buy (0.60–0.75)

- **strategy_id:** `STRAT-005`  
- **Origin tag (04):** `DHAN-DERIVED`  
- **Spoken recipe (from STRAT file):** `2RnBT9` 38:06–39:20, 01:02:16–01:03:50. Call |delta| in **[0.60, 0.75]** (spoken 0.63–0.74; RSI analogy 50–75). Puts = negative of same. Avoid |delta| > 0.74. Fallback: nearest ATM or 1 ITM. Avoid 50-multiples = `TEST_ON_OFF` (host vs guest). If history lacks delta: map **1–2 strikes ITM from spot** at signal time. OTM **not** recommended **in this video** (conflicts 002).  
- **Math verdict:** `context-dependent`  
  - Delta = ∂premium/∂underlying is `supported` (Natenberg / Hull). Call delta typically in (0,1).  
  - Band 0.60–0.75 as “the” buy zone is a **spoken heuristic**, not a theorem. RSI 50–75 **mapped onto** delta is `unsupported` as an identity.  
  - Delta ≠ win rate (`unsupported` as conviction%; [`VALIDATION_MATH.md`](VALIDATION_MATH.md)).  
- **HQ surface:** chain `greeks.delta` / `implied_volatility` — **not** a TA annexure token. Vendor model = `UNKNOWN`. Fallback ITM count is a **strike map**, not `OHLC_COMPUTE`.  
- **Implementable compute:** **OPTIDX chain** at signal time. Underlying **level** from spot (spoken) or futures — 03 must name which; do **not** use cash-index **volume**.  
- **Search grid (do not pick a winner):** |delta| `[0.60, 0.75]` vs spoken `0.63–0.74`; avoid-`>0.74` on/off; 50-multiples on/off; delta-from-vendor vs 1–2 ITM from **spot**. Ablate vs 002 on the **same** 001/003 signals.  
- **TO 04_quant:** **grid** / ablate vs 002. Do not freeze 0.63–0.74 as unique. Do not treat Dhan chain delta as a proven Black–76 number.  
- **TO 03_phd_market:** Market object = **OPTIDX** contract (NSE vs BSE). Spoken strike-from-**spot**, not from futures, is a basis choice you own. Liquidity fallback is a tape fact, not math.
- **Premium path (charter, not a run):** first option-OHLC book is ATM vs ATM-2/ATM+2 only — [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md). Do not p-hack ST 10,3 on that path.

---

## STRAT-006 — 2-minute EMA 10/20 ITM scalp

- **strategy_id:** `STRAT-006`  
- **Origin tag (04):** `DHAN-DERIVED`  
- **Spoken recipe (from STRAT file):** `pvmvkiS1cx4` (no timestamps in the STRAT file — none invented here). NIFTY / BANKNIFTY / SENSEX. Analysis on **spot OHLC** (speaker); execution **index option buy**. TF **2m**. EMA **10 and 20** only. Strike **ITM 100–200 points** on all three. Delta **[0.55, 0.60]** `[UNCERTAIN_TRANSCRIPT]`. Same speaker: beginners should **not** scalp **buying** options — keep both statements.  
- **Math verdict:** `partially_supported`  
  - EMA 10 / EMA 20 on close is `supported` as definition (Murphy MAs). Annexure includes `EMA_10` and `EMA_20` as **trigger names**. Seed / α convention on Dhan charts = `UNKNOWN`.  
  - 2m as an HQ interval is `unsupported` (enum is 1/5/15/25/60).  
  - 100–200 pt ITM as a universal ATM proxy across three indices is `context-dependent` (different strike steps / levels — 03).  
- **HQ surface:** `OHLC_COMPUTE`. Trigger enums `EMA_10` / `EMA_20` exist; **not** a series REST. **2m = unsupported token** as `interval`. No oscillators in this recipe — do not add RSI/MACD.  
- **Implementable compute:** Close series of **IDX_I (spot)** as spoken **or** **FUTIDX** as an honesty test (04 YAML already says TEST). Neither path needs **cash-index volume**. Execution = **OPTIDX**.  
- **Search grid (do not pick a winner):** TF `{1m, 5m, 2m-resample-from-1m}` — do not invent a 2m REST. Delta `[0.55, 0.60]` vs 100–200 pt ITM map. Spot vs FUTIDX as the EMA object.  
- **TO 04_quant:** **grid**. Do not freeze 2m as official. After costs this ID is allowed to go `REJECTED` honestly — 02 does not invent that result. Do not mix `mPKASwm6Oqk` DEMA 100 into this ID.  
- **TO 03_phd_market:** Speaker analysis object = **cash index (spot)**; trade object = **OPTIDX**. Futures vs spot basis can flip EMA crosses — name the object per test. SENSEX = BSE. 100–200 pt ITM is **not** the same moneyness on NIFTY vs BANKNIFTY vs SENSEX.

---

## STRAT-007 — Clock filter (HAUS session)

- **strategy_id:** `STRAT-007`  
- **Origin tag (04):** `DHAN-DERIVED`  
- **Spoken recipe (from STRAT file):** `HAUSZx` 55:18–55:42, 01:00:22–01:00:35. New entries **after 10:00**, **before 14:30**, hard ban **after 15:00**. Spoken best window 11:00–13:00. EOD flatten true. **14:45 vs 15:00** wording messy (`UNCERTAIN_TRANSCRIPT`). Filter only — attach to 001/003.  
- **Math verdict:** `context-dependent`  
  - A session window is a **defined construction**, not an exchange law and not a theorem. No unique “optimal” T in the English corpus (HAUS 10:00 vs 2Rn 09:45 vs ORB-to-10:00).  
- **HQ surface:** n/a — **not** an indicator token. Implement from chart **timestamps** (`OHLC_COMPUTE` of bar time only).  
- **Implementable compute:** Bar `timestamp` in `Asia/Kolkata` on whichever object 001/003 uses (**FUTIDX** preferred). No volume.  
- **Search grid (do not pick a winner):** new-entry cutoff `{14:30, 14:45, 15:00}`. Do **not** merge with STRAT-009’s 09:15–09:45 skip / 15:15 flatten (different speaker clocks).  
- **TO 04_quant:** **grid** the afternoon cutoff. **Do not merge** with 009. Filter is not a standalone edge.  
- **TO 03_phd_market:** Clocks are **trader heuristics**. F&O session **09:15–15:40** (VERIFY) vs spoken 15:00 new-entry ban vs 009’s 15:15 flatten — keep as separate parameters. CAS is about **cash names**, not this filter.

---

## STRAT-008 — Mixed-index avoid / dominant only

- **strategy_id:** `STRAT-008`  
- **Origin tag (04):** `DHAN-DERIVED`  
- **Spoken recipe (from STRAT file):** `2RnBT9` 01:08:37–01:11:19. If 003 (or 001) is **long** on NIFTY and **short** on BANKNIFTY (or any pair of {NIFTY, BANKNIFTY, SENSEX}): **no new trades** that day, **or** trade only a pre-declared **dominant** index — never both sides. Optional 1-lot-each vs 3-lots-in-one is a **size test**, not an edge claim. SENSEX alignment uses **that market’s future**.  
- **Math verdict:** `context-dependent`  
  - “Do not hold opposite index bets” is a **portfolio filter**, not a cointegration theorem. Observing sign(NIFTY setup) ≠ sign(BANKNIFTY setup) is well-defined **once** each setup is defined.  
  - Choosing “dominant” **after** the close is look-ahead (`unsupported` as a backtest rule). Pre-declared dominant is a **parameter**, not math.  
- **HQ surface:** n/a. Needs **three** FUTIDX series (or whatever 001/003 used). Not an annexure indicator.  
- **Implementable compute:** **FUTIDX per index** (SENSEX = **BSE_FNO**). **Forbidden:** a fake combined volume or cash-index volume to “align” the three.  
- **Search grid:** how “dominant” is declared (pre-session vs first-signal vs not used). Do not pick a winner on IS. The **no-both-sides** clause needs no grid.  
- **TO 04_quant:** **freeze** the skip-if-disagree rule as a filter; **do-not-use** a silent post-hoc dominant. Size 1×3 vs 3×1 is a later test, not an edge.  
- **TO 03_phd_market:** Three **separate** market objects: NSE NIFTY FUTIDX, NSE BANKNIFTY FUTIDX, BSE SENSEX FUTIDX. Do not reuse one chain client. Alignment is on **futures signs**, not OPTIDX premiums.

---

## STRAT-009 — Open skip 09:15–09:45 + flatten 15:15

- **strategy_id:** `STRAT-009`  
- **Origin tag (04):** `DHAN-DERIVED`  
- **Spoken recipe (from STRAT file):** `2RnBT9` 23:48–24:03. Ignore bars **09:15–09:45**; flatten all **before 15:15** Asia/Kolkata; no overnight. Complements 007 — **do not silently merge**. F&O close 15:30 vs 15:40: `VERIFY`.  
- **Math verdict:** `context-dependent`  
  - Opening skip is a **chosen IST box**, not an exchange mandate ([`TA_FROM_TRANSCRIPTS.md`](TA_FROM_TRANSCRIPTS.md) OR section). Other videos name 09:15–09:30, ORB to 10:00, skip 15m — **not one T**.  
- **HQ surface:** n/a (timestamps). Box from **1m or 5m** OHLC = `supported` as construction. Treating 09:45 as “Dhan’s official ORB” = `unsupported`.  
- **Implementable compute:** **FUTIDX** bar times for the skip (same object as 003). Flatten applies to **OPTIDX** positions. No cash-index volume.  
- **Search grid:** do **not** invent a merged 007+009 clock. Optional later tests of `{15, 30, 45}`-minute skips are **other videos**, not this ID’s spoken rule — if 04 tests them, they are **separate hypotheses**, not a silent correction of 009.  
- **TO 04_quant:** Attach to 003. **Do not merge** with 007. Flatten-before-15:15 is a **preference parameter** until 03 signs the F&O clock.  
- **TO 03_phd_market:** Spoken **15:15** flatten vs equity-derivatives **15:40** vs CAS **15:15** on F&O **cash names** — parameterize; do not hardcode one close. Overnight false = no weekend gap on this ID.

---

## STRAT-010 — Order-flow volume-delta / POC overlay

- **strategy_id:** `STRAT-010`  
- **Origin tag (04):** `DHAN-DERIVED` tool (`YUXJv_xBStw`) + `PROJECT-DERIVED` rules (video has **no** entry recipe)  
- **Spoken recipe (from STRAT file):** Overlay: only take 003/001 entries if **futures** footprint **volume-delta** agrees on the signal candle (or last closed 1m/5m); optional POC not to be faded; imbalance ≥ **3×** as spoken default. **Greek delta ≠ volume delta.** STRAT status already `DATA_INSUFFICIENT`.  
- **Math verdict:** volume-delta = buy volume − sell volume is `supported` as a **microstructure definition** ([`VALIDATION_MATH.md`](VALIDATION_MATH.md)). Imbalance ≥3× and VAH/VAL ~70% are `context-dependent` heuristics (DzT product defaults), **not** theorems. Using OF as an entry **recipe** is `UNKNOWN` in `YUXJv_xBStw` (04 already tagged PROJECT overlay).  
- **HQ surface:** `DATA_INSUFFICIENT`. No documented HQ **historical footprint / delta / POC** series. Charts `volume` is **not** signed buy-vs-sell. Do not proxy with cash-index ticks.  
- **Implementable compute:** **Not** from `POST /charts/*` OHLC. If a DEXT export ever exists, the object is **FUTIDX** tape (YUX demo named NIFTY futures; DzT demo was Reliance — do not collapse). **Forbidden:** IDX_I volume as OF.  
- **Search grid:** moot until history exists. Product imbalance settings 3 vs 10 vs 20 (DzT) must **not** be frozen as “the” Dhan OF law.  
- **TO 04_quant:** **do-not-use** for backtest / engine. Stay `DATA_INSUFFICIENT`. Overlay must not block 001/003 design. Never collapse volume-delta with STRAT-005 Greek delta.  
- **TO 03_phd_market:** Assumed object = **FUTIDX** aggressive-buy vs aggressive-sell prints. HQ history likely absent — confirm. Not OPTIDX premium OF unless a separate data product appears.

---

## STRAT-011 — RSI divergence + Supertrend child (**PROJECT-DERIVED** transfer)

- **strategy_id:** `STRAT-011`  
- **Origin tag (04):** **`PROJECT-DERIVED`** from `DHAN-DERIVED` pieces (`H_6keeRUCDM`, `gA5FtEnSABM`). **Not** “Dhan said trade NIFTY options this way.”  
- **Spoken recipe (from STRAT file):** Parent: RSI **divergence** or RSI **oversold + green candle**; child: Supertrend **10,3** close-through. Phase-1 test: 1h or 2h RSI vs price LL/HH; 5m/15m ST; **buy** CE/PE with 005 or 002. gA5: 2h RSI divergence on **NIFTY** then bullish **view**; **executed** example was a **credit spread** (013). H_6kee: stock/gold examples; ST default 10,3. RSI **period not spoken** in these two videos (Wilder 14 is VALIDATION default — tag as convention, not Dhan-spoken).  
- **Math verdict:** `context-dependent`  
  - Wilder RSI_14 + band ~30 is `supported` as **common convention** (Murphy / Wilder). Period unnamed here → transferring 14 is `SOURCE_UNCERTAIN` relative to these videos.  
  - Divergence vs price LL/HH is a **pattern**, not a proven predictor (`context-dependent` / not an edge theorem).  
  - Supertrend 10,3: same as 003 — common default, not HQ.  
  - Mapping gA5’s **sell** execution onto Phase-1 **buy** is a **project transfer**, not a transcript identity.  
- **HQ surface:** `OHLC_COMPUTE`. Trigger `RSI_14` exists as a **condition**, not a series. Supertrend = `CHART_ONLY`. **2h is not** in `{1,5,15,25,60}` → resample `HYPOTHESIS` from `60`. ScanX RSI 75/25 is **not** Wilder law — do not import.  
- **Implementable compute:** **FUTIDX** (or index close if 03 insists on gA5’s NIFTY chart) OHLC. **Not** cash-index volume. Child ST on 5m/15m (both HQ-legal). Execution hypothesis = **OPTIDX buy** for this ID — that **is** the transfer.  
- **Search grid (do not pick a winner):** RSI period unnamed → do **not** silently freeze 14 as “what H_6kee said”; if 14 is used, label **VALIDATION convention**. Parent `{1h, 2h-resample}`; child ST `{5m, 15m}`; oversold+green vs divergence as **two** tests. Do not freeze `_byuht` 7,3 ST onto this ID.  
- **TO 04_quant:** **grid**. Keep **`PROJECT-DERIVED`**. Do not relabel DHAN-DERIVED index-options. Do not promote swing **sell** (013) into this buy ID. Desk 5m ST confirm-or-kill ≠ H_6kee child-TF **entry**. Horizon vs theta: swing options vs HAUS “intraday buyer” is a **conflict to keep**, not to paper over.  
- **TO 03_phd_market:** gA5 chart object = **NIFTY** (index). Transfer assumes **FUTIDX** for ST/RSI continuity with 003, **or** IDX_I close — pick one per test and write it down. Executed video object was a **put credit** (OPTIDX short+long). Phase-1 011 object is **long OPTIDX**.

---

## STRAT-012 — Candlestick + S/R confluence (**PROJECT-DERIVED** overlay)

- **strategy_id:** `STRAT-012`  
- **Origin tag (04):** **`PROJECT-DERIVED`** (`njqeZc_tYy8` + `wDZXqzdGBDc` tool).  
- **Spoken recipe (from STRAT file):** Patterns are **not** standalone; need trend + S/R + optional RSI < 30 for hammer. Only **hammer** fully extracted this pass (wick **2–3×** body — `[UNCERTAIN_TRANSCRIPT]`). Four other patterns (bullish engulfing, morning star, dark cloud cover, inside bar): `WAITING_FOR_EDIT`. HYPOTHESIS: allow 001/003 entry only if last closed 5m/15m pattern agrees. Auto-detect is a **Dhan tool**, not an API.  
- **Math verdict:** `context-dependent`  
  - Pattern **geometry** is `supported` as language (Murphy candlesticks). Predictive power is `unsupported` without a test.  
  - “Candles leading vs indicators lagging” is pedagogy, `context-dependent` — patterns are still functions of the same OHLC.  
  - Inside bar is not inherently bullish or bearish (speaker; keep).  
- **HQ surface:** `OHLC_COMPUTE` from candles. **No** pattern series REST. Auto-detect = `CHART_ONLY` product (skip as strategy evidence). Optional RSI = `OHLC_COMPUTE` / trigger `RSI_14` only.  
- **Implementable compute:** **FUTIDX** OHLC for the overlay (index transfer). **Do not** detect hammers on a random OTM **OPTIDX** LTP unless 04 writes a separate spec. No cash-index volume required.  
- **Search grid (do not pick a winner):** hammer wick `{2×, 3×}` body; TF `{5m, 15m}`; RSI<30 on/off. Do not invent the four unextracted patterns.  
- **TO 04_quant:** **grid** hammer only. Keep **`PROJECT-DERIVED`**. Do not treat auto-detect as HQ. Four patterns stay `WAITING_FOR_EDIT` — not silently filled from blogs. Overlay, not a fourteenth edge.  
- **TO 03_phd_market:** Structure object = **FUTIDX** (transfer). Stock open=low / auction identity does **not** carry to a **constructed cash index** the way it does to a single-stock print.

---

## STRAT-013 — Bull put credit spread (**WAITING sell** — structure only)

- **strategy_id:** `STRAT-013`  
- **Origin tag (04):** `DHAN-DERIVED` (`gA5FtEnSABM`)  
- **Spoken recipe (from STRAT file):** 2h/1h bullish view (e.g. RSI divergence) → **sell** nearer put, **buy** further OTM put; skip 0 DTE; skip event weeks (budget example). Max loss known; margin from broker. Rupee figures `[UNCERTAIN_TRANSCRIPT]`. Sideways-to-mild-up. **Do not code for paper UI (BUY CE/PE) until Phase selling is opened.**  
- **Math verdict:** `supported` **as a defined-risk vertical payoff**; `context-dependent` as a **when-to-sell** rule  
  - Bull put credit: short put K2 + long put K1 < K2. Max profit = net credit; max loss = (K2−K1) − credit (Natenberg verticals). That algebra is `supported`.  
  - Index options European cash-settled: no stock assignment; still a defined cash payoff at expiry — `supported` with that market caveat (03).  
  - Skip 0 DTE / skip event weeks: **heuristics**, `context-dependent`. Rupee/margin toys: `SOURCE_UNCERTAIN`.  
  - 93/7, seller 70% win: `unsupported` as math ([`VALIDATION_MATH.md`](VALIDATION_MATH.md)) — do not attach.  
- **HQ surface:** option chain (strikes, bid/ask, margin is **broker**, not annexure TA). RSI/ST view shares 011’s `OHLC_COMPUTE` surface.  
- **Implementable compute:** **OPTIDX** two legs (short nearer put + long further put). View may use **NIFTY** / **FUTIDX** OHLC. **Forbidden:** cash-index volume.  
- **Search grid:** rupee figures stay tagged uncertain — **do not freeze**. Width / expiry weekday = `FROM_CONTRACT` (03), not a 02 winner.  
- **TO 04_quant:** **do-not-use** as Phase-1 buy. Validate structure; **do not promote** to buy-first UI; **do not** rewrite as STRAT-011. Same RSI view, opposite product (credit vs long premium) — keep the split.  
- **TO 03_phd_market:** Object = **OPTIDX put vertical** on NIFTY (video). Margin/SPAN policy is broker/exchange, not a 02 formula. Event-week skip is a **calendar** object you own. Expiry weekday `FROM_CONTRACT` — do not freeze gA5’s dated week.

---

## STRAT-014 — Hedged 1-3-2 call ratio, Monday 09:45 (**WAITING sell** — structure only)

- **strategy_id:** `STRAT-014`  
- **Origin tag (04):** `DHAN-DERIVED` (`6el9Jqnrdz8` 41:29–46:35)  
- **Spoken recipe (from STRAT file):** NIFTY. Entry **Monday 09:45**; exit Friday EOD; no weekend carry; expiry **next Tuesday weekly** (`VERIFY` calendar). Structure at spot S: buy **1** × (S+200) call, sell **3** × (S+400) call, buy **2** × (S+600) call. Target/stop **1% of capital** each; avoid 50-strikes; no adjustments. BANKNIFTY monthly-only caveat in video. POP 80% **unsupported** (STRAT file already). Margin ~1.3–1.4L `[UNCERTAIN_TRANSCRIPT]`. **Not Phase-1 buy UI.**  
- **Math verdict:** `supported` **as a basket payoff if all legs fill**; `unsupported` as POP / win rate  
  - Net contracts: +1 − 3 + 2 = **0**. As U → ∞ the linear U terms cancel; with **equal 200-pt spacing** the constant also cancels, so the far wing **caps** the upside **if** the 1-3-2 is filled as specified (defined-risk **call-side** structure, plus initial net debit/credit). Unequal fills / missing hedge legs → **undefined** short-call risk (`context-dependent` on execution).  
  - 1% of capital stop/target is money-management, `context-dependent`, not a theorem.  
  - Spoken POP 80–85% / “success > 50%” = `unsupported` without a specified vol model + surface ([`VALIDATION_MATH.md`](VALIDATION_MATH.md)).  
- **HQ surface:** chain + **basket** (product, not TA annexure). Monday 09:45 is a clock, not an indicator.  
- **Implementable compute:** **OPTIDX** three NIFTY call legs; S from **spot or futures** (03 names which). No cash-index volume. 09:45 is after the 009 open skip but this ID is **not** attached to 003.  
- **Search grid:** do **not** freeze Tuesday expiry (dated vs current SEBI weekly regime — 03). Margin rupees stay `[UNCERTAIN_TRANSCRIPT]`. Avoid-50-strikes on/off is a liquidity flag, not math. Do **not** grid toward a POP number.  
- **TO 04_quant:** **do-not-use** Phase-1 buy. Structure may be specified for a later sell book; **do not** copy POP into YAML `metrics`. Leg risk if not a basket = invalidation, not an optimization knob.  
- **TO 03_phd_market:** Object = **NIFTY OPTIDX** 1-3-2. Expiry **`FROM_CONTRACT`**, not frozen Tuesday. BANKNIFTY weekly-off is a **contract list** fact (`VERIFY`). Monday 09:45 vs F&O 09:15 open is a session parameter. SENSEX is **out of this spoken recipe**.

---

## Cross-cutting (02 only)

| Topic | VALIDATION | 04 / 03 implication |
|-------|------------|---------------------|
| Murphy / Natenberg | Tags for MA/MACD/RSI/candles and for option **risk** (delta, verticals, ratios) | **No new STRAT IDs** |
| Supertrend / RSI / MACD / EMA9 **series** REST | Does not exist | Compute later or don’t; never invent enums |
| `EMA_9`, `SMA_30`, Super Scalper lengths, `SUPERTREND_10_3` | **unsupported** as HQ tokens | Grid or `UNKNOWN`; do not send to `/alerts/orders` |
| 2m / 3m / 2h | Not in charts enum `{1,5,15,25,60}` | Resample `HYPOTHESIS` or use 1/5/60 |
| Cash-index volume VWAP | `unsupported` | FUTIDX or option tape only |
| Quote `average_price` / ATP | Day snapshot; identity vs session VWAP `UNKNOWN` | Do not substitute for 003 VWAP |
| 001 child MACD vs desk 5m confirm-or-kill | Two different hypotheses | Do not collapse |
| 002 vs 005 vs 006 strikes | Spoken **conflict** | Ablate; one “Dhan strike” is `unsupported` |
| 007 vs 009 clocks | Spoken **conflict** | Do not merge |
| 011 / 012 | **PROJECT-DERIVED** | Say so in every freeze |
| 013 / 014 | Structure `supported`; product is **sell** | WAITING; not Phase-1 buy |
| 010 | Definition `supported`; HQ history `DATA_INSUFFICIENT` | do-not-use |
| Win rates / POP / 70% / 93/7 | `unsupported` as constants | `metrics.*` stay `null` |

**This file does not freeze STRAT params. It does not approve P&L. Empty `packages/indicators` remains correct until review.**
