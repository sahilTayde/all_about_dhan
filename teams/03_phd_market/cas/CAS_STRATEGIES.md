# CAS-* strategies — Closing Auction Session (not STRAT-015+)

**Team:** 03_phd_market (CAS home)  
**Date:** 2026-09-03  
**Layer:** `HYPOTHESIS` / `UNVALIDATED`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. No coded engine. No live Dhan. No win rates. No invented lots, quotes, or fills.

**Namespace:** `CAS-001` … `CAS-005` only. **Not** `STRAT-015+`. Phase-1 index STRATs stay `STRAT-001`–`014`.

**Companions:** [`RESEARCH.md`](RESEARCH.md), [`METHODOLOGY.md`](METHODOLOGY.md), [`README.md`](README.md), [`../docs/STRAT_001_014_MARKET.md`](../docs/STRAT_001_014_MARKET.md).

---

```text
HANDOFF
From:     teams/03_phd_market/cas
To:       00 / 04 / 05 / 06 / 09
Date:     2026-09-03
Status:   DRAFT / UNVALIDATED
Gate:     NOT RESEARCH_READY_FOR_PROGRAMMING

Accepted:
- CAS-* IDs defined as close-microstructure hypotheses.
- Clocks from NSE/BSE CAS pages + METHODOLOGY windows.
- SENSEX = BSE auction; NSE vs BSE can diverge.
- STRAT-009 (Gokul flatten 15:15) stays its own STRAT. CAS-003 is a separate filter.

Rejected:
- DHAN-DERIVED CAS option-buy recipes (none in English transcripts).
- Promoting CAS bias to CONFIRMED / CE/PE fill.
- Inventing settlement formulas, lots, IEP prints, or win rates.
- Collapsing PRE_OPEN / PCA into the CAS acronym.

UNKNOWN / DATA_INSUFFICIENT:
- No live IEP / imbalance / indicative-index feed in this workspace.
- NSE/FAOP/74467 F&O 15:40 circular PDF not stored — 15:40 stays VERIFY.
- English Dhan transcripts: no “Closing Auction Session” (see §Transcript scan).
```

---

## Origin tags (do not collapse)

| Tag | Means | Allowed on CAS-* |
|-----|--------|------------------|
| **EXCHANGE-DERIVED** | NSE/BSE/SEBI clocks and close rule (circulars / CAS product page). | Clocks, equilibrium vs last-30-min VWAP, CAS skip on MWCB, SENSEX = BSE. |
| **DHAN-DERIVED** | Spoken on an enabled `@DhanHQ` English transcript. | **None of these IDs.** Scan below. Gokul **15:15 flatten** is STRAT-009, not a CAS recipe. |
| **PROJECT-DERIVED** | Our test / filter / analog. Must stay labeled. | Bias labels, F&O-tail flatten, no-new-opt during auction, expiry tag analog, pre-open gap book. |

Education ≠ advice. Affiliation (SEBI RA / Star Trader) ≠ edge.

---

## Transcript scan (English) — DHAN-DERIVED CAS STRATs

Grep of `data/transcripts/normalized_en/` (2026-09-03):

| Query | Result |
|-------|--------|
| `Closing Auction` / `auction session` | **No matches.** |
| `CAS` as the 2026 close auction | **No matches** (not used as that acronym). |
| Timestamp lines `[15:35]` / `[15:40]` | YouTube **offsets**, not IST clocks. |

**Verdict:** **`DATA_INSUFFICIENT` for any `DHAN-DERIVED` CAS STRAT.** Do not pretend a Dhan video taught a Closing Auction Session option-buy recipe. **Working path:** CAS-001–005 stay off PAPER candidate scoring (WATCH reason only; never CONFIRMED).

Related but **not** CAS: Gokul (`2RnBT9DDDNI` 23:48–24:06) flatten **before 15:15** / ignore 09:15–09:45 = **STRAT-009** (`DHAN-DERIVED` trader heuristic). That clock **coincides** with CAS CTS end on F&O-cash names; the speaker did **not** name CAS. Keep 009. Do not rewrite it as CAS-003.

---

## Shared market facts (all CAS-*)

| Fact | VALIDATION |
|------|------------|
| **CAS** | Official **Closing Auction Session** on F&O **cash** names. CTS ends **15:15**; session **15:15–15:35** IST; official close = **equilibrium**, not last-30-min VWAP. Live **3 Aug 2026**. [`RESEARCH.md`](RESEARCH.md). |
| **NIFTY / BANKNIFTY cash names** | **NSE** CAS book. |
| **SENSEX** | **BSE** CAS (notice 20260610-41). Two order books → **index prints can diverge**. Do not reuse NSE indicative index on SENSEX. |
| **Equity derivatives** | **09:15–15:40** IST on NSE CAS page + timings. **VERIFY** — 74467 PDF not in-repo. Not the cash auction. |
| **MWCB** | CAS **skipped** if an index circuit ends the day early → last-30-min VWAP / LTP as before. |
| **Dhan chain** | `POST /optionchain`, desk poll **3m**, 1 unique / 3s. Positioning overlay, **not** a close oracle. Empty `DHAN_*` → fixtures. |
| **IEP / imbalance / indicative index** | Official CAS dissemination (NEAT / MBP / BSE “Closing auction session”). **No live feed in this workspace** → `DATA_INSUFFICIENT` until a fixture or feed exists. |
| **Lots / expiry** | `FROM_CONTRACT`. Never freeze. |
| **Customer** | CasPanel = **close-auction / cash bias**. Stage at most **WATCH** reason. **Never CONFIRMED** from a CAS-* ID ([`SIGNAL_FUSION.md`](../../05_analysis/docs/SIGNAL_FUSION.md)). |

```yaml
session_tz: Asia/Kolkata
namespace: CAS
ids: [CAS-001, CAS-002, CAS-003, CAS-004, CAS-005]
lot_size: FROM_INSTRUMENT_MASTER
expiry: FROM_CONTRACT
sensex_exchange: BSE
fo_close_ist: 15:40          # VERIFY circular
cas_session: 15:15-15:35_equilibrium
status: UNVALIDATED
research_ready_for_programming: false
metrics: { win_rate: null, expectancy: null }
```

---

## CAS-001 — CLOSE_BIAS

**Name:** daily close-bias vs 15:00–15:15 reference VWAP  
**Origin:** **EXCHANGE-DERIVED** clocks + **PROJECT-DERIVED** labels `BOUNCE | SIDEWAYS | FALL`  
**DHAN-DERIVED:** no  
**Already live as research:** [`METHODOLOGY.md`](METHODOLOGY.md) + `notes/` + `calls/*.json`

### Clock (IST) — cite METHODOLOGY windows

| Id | Clock | What we read |
|----|-------|----------------|
| `REF_VWAP` | 15:00–15:15 | Last 15 min of CTS. CAS **reference** = VWAP of these trades (exchange). |
| `TRANSITION` | 15:15–15:20 | No CTS matching on CAS stocks. Chart LTP **stale**. Do not call a spike. |
| `IEP` | 15:20–15:28 | Indicative equilibrium, imbalance, **indicative index**. |
| `RANDOM_CLOSE` | 15:28–15:30 | Book can vanish by design. |
| `MATCH` | 15:30–15:35 | Official cash close. Compare to 15:15 LTP **and** to reference VWAP. |

### Inputs

| Input | Source | If missing |
|-------|--------|------------|
| Reference VWAP 15:00–15:15 | Exchange / later fixture | Do not invent. Default `SIDEWAYS`. |
| IEP, imbalance, indicative index | Official CAS tape | `DATA_INSUFFICIENT` (current workspace). |
| Official index close | NSE/BSE bhav / index file | Needed for `realized_bias` after the fact. |
| Dhan chain 3m | `POST /optionchain` or fixture | Overlay only. Not the bias engine. |
| SENSEX | **BSE** indicative package | Separate call; do not copy NIFTY. |

**Output:** per underlying `{NIFTY, BANKNIFTY, SENSEX}`: `BOUNCE | SIDEWAYS | FALL` + confidence (0–1 = **evidence completeness**, not hit rate) + `UNVALIDATED`.

This is **close-bias for the cash index print**, not a CE/PE fill.

### Must NOT claim

- A CE/PE **entry**. CONFIRMED. Win rate. “CAS always fades.”
- Cash-index **volume** VWAP as the tape (reference VWAP is **stock** CTS 15:00–15:15, not IDX_I volume).
- NSE indicative index as SENSEX.

### UNKNOWN / DATA_INSUFFICIENT

- Live IEP / imbalance / indicative index in-repo. First call `2026-09-01` is SIDEWAYS / 0.20 / clocks only.
- Launch-week “~200 pt Nifty vs 15:15” is press, **not** a repeatable edge.

### 06 backtest (later, fixtures)

1. Fixture: per day, per index — `ref_vwap` (or 15:15 LTP), `official_close`, optional IEP path.  
2. Score: `realized_bias = sign(official_close − ref)`.  
3. Compare to that day’s `cas_calls[].bias`.  
4. OOS + `NORMAL` sessions. `NEWS_DAY` / `EXPIRY` tagged, not retune samples.  
5. Metrics stay **null** until that test. **No invented fills.**

### 05 / 00 customer talk

**WATCH reason only:** “CAS book says SIDEWAYS/BOUNCE/FALL — UNVALIDATED.” CasPanel copy. **Must not** promote EARLY or CONFIRMED. Must not override `NEWS_DAY` / `EXPIRY` veto.

---

## CAS-002 — FNO_TAIL

**Name:** 15:35–15:40 derivatives still open vs new cash equilibrium  
**Origin:** **EXCHANGE-DERIVED** two-clock (CAS match end vs F&O session) + **PROJECT-DERIVED** basis/spread risk  
**DHAN-DERIVED:** no

### Clock (IST)

| Id | Clock | What it is |
|----|-------|------------|
| `MATCH` | 15:30–15:35 | Cash CAS close discovered. |
| `FNO_TAIL` | **15:35–15:40** | Equity **derivatives still open** (NSE CAS page + timings). **VERIFY** — 74467 PDF not stored. Do **not** freeze 15:40 as proven if a later circular moves it. |
| `POST_CLOSE` | 15:50–16:00 | Trade **at** close. Tag `POST_CLOSE`, not a new CAS discovery. |

### Inputs

| Input | Source | If missing |
|-------|--------|------------|
| Official cash close / indicative index at match | Exchange | `DATA_INSUFFICIENT`. |
| FUTIDX / OPTIDX LTP into 15:40 | Dhan charts/quote **if token**; else fixture | Basis vs cash close. **Never** cash-index volume. |
| Chain 3m | Last snapshot before/into tail | Positioning; may be stale vs a 5-minute tail. |

**Hypothesis (PROJECT):** after cash equilibrium prints, remaining F&O minutes are **basis / spread risk**, not a continuation of the 15:15 stale LTP. Phase-1 test knobs (do not freeze a winner): `flatten_into_tail` | `no_new_buy_in_tail` | `allow_until_fo_close`.

### Must NOT claim

- That 15:40 is eternal without the circular on disk.  
- That the tail is an **alpha** scalp.  
- That this **replaces** STRAT-009 (Gokul flattens **before 15:15**, so 009 never sits in this tail).  
- Fills at LTP.

### UNKNOWN / DATA_INSUFFICIENT

- Official F&O 15:40 circular PDF.  
- Historical option quotes on HQ for the tail.  
- Whether Dhan alerts on F&O stop at 15:40 (broker explainers, not HQ REST).

### 06 backtest (later, fixtures)

1. Fixture futures (and option if available) OHLC 15:30–15:40 vs cash close timestamp.  
2. Test: new OPTIDX **buys** opened in `FNO_TAIL` vs flattened-before-15:35, after half-spread.  
3. Invalidation: expectancy ≤ 0 after costs in trend **and** chop, or `DATA_INSUFFICIENT` tape → park.  
4. Parameterize `fo_close_ist`; do not hardcode.

### 05 / 00 customer talk

If a buy lean is still showing after 15:35: **WATCH / EXPIRED / VETOED** — “F&O tail vs new cash close — not a fill.” **Not CONFIRMED.** Do not tell the customer to “fade the auction in options.”

---

## CAS-003 — NO_NEW_OPT_DURING_AUCTION

**Name:** no new index-option **entries** while cash names are in auction  
**Origin:** **PROJECT-DERIVED** filter for OPTION_BUYER books  
**DHAN-DERIVED:** no (Gokul 009 is a **different** ID)

### Clock (IST)

| Id | Clock | Why no new OPTIDX **entry** |
|----|-------|------------------------------|
| `TRANSITION` | 15:15–15:20 | Cash CTS dead; LTP **stale**. Index chart can look flat then jump — auction discovery, not a 5m impulse. |
| `IEP` … `MATCH` | 15:20–15:35 | Cash close still being discovered. F&O may still trade; cash/futures **basis can gap**. |

**Does not delete STRAT-009.** 009 = Gokul flatten **all positions before 15:15** (`DHAN-DERIVED`). CAS-003 = **no new entries 15:15–15:35** (`PROJECT-DERIVED`). A book can attach **both**: 009 exits before auction; 003 blocks late entries if 009 is off.

### Inputs

| Input | Source |
|-------|--------|
| Session clock IST | Calendar + exchange holiday. |
| CAS-eligible day | Skip this filter if MWCB skipped CAS (then last-30-min VWAP regime — different clock). |
| Chain 3m | Optional; **not** required to apply the time filter. |

### Must NOT claim

- That Gokul taught “no entries during Closing Auction Session.” He taught flatten 15:15.  
- That F&O is closed 15:15–15:35 (it is **not**; CAS-002 is the tail after 15:35).  
- Alpha. A CE/PE ticket from a stale 15:15 cash print.

### UNKNOWN / DATA_INSUFFICIENT

- Same missing IEP feed. Filter is **time-based**; it does not need IEP to be testable.

### 06 backtest (later, fixtures)

1. On OPTION_BUYER shadows: flag any **new** OPTIDX buy with `entry_ist ∈ [15:15, 15:35)`.  
2. Ablate vs allowing those entries (costs + next-bar/ask).  
3. Keep 009 on/off as a **separate** switch. Do not merge IDs.

### 05 / 00 customer talk

**VETOED / no new risk** copy: “Cash auction window — no new option entry. UNVALIDATED filter.” Existing IN-PROGRESS tickets are **009’s** problem (flatten or not), not silently closed by 003. **Not CONFIRMED.**

---

## CAS-004 — EXPIRY_SETTLEMENT_MARK

**Name:** on `EXPIRY`, cash CAS close matters for settlement **marks**  
**Origin:** **EXCHANGE-DERIVED** (official close feeds marks / NAV / F&O settlement language in RESEARCH + broker explainers) + **PROJECT-DERIVED** analog tag  
**DHAN-DERIVED:** no

### Clock (IST)

Same CAS windows as CAS-001. **Do not skip CAS on expiry day** ([`METHODOLOGY.md`](METHODOLOGY.md) §Expiry calendar).

`EXPIRY` tag = nearest-expiry **sheet date equals session date** (03/nightly). Weekday folklore (Tue NIFTY / Thu SENSEX) stays `FROM_CONTRACT`.

### Inputs

| Input | Source | If missing |
|-------|--------|------------|
| `EXPIRY` session tag | Instrument master `expiry_date` vs calendar | Do not invent Tuesday. |
| Official CAS close / index close | Exchange | Needed to mark. |
| Chain 3m | Last snapshots | Pin / gamma **heuristic** only — not a formula. |

**Hypothesis:** on expiry, the **cash CAS equilibrium** (constituents) is the print settlement-style marks care about — **not** the stale 15:15 LTP and **not** a vendor index-volume VWAP.

### Must NOT claim

- A **settlement formula** (we do **not** invent exchange settlement math, lot, or contract multiplier).  
- That long premium “pins” to max-pain as a buy STRAT (`_exm` walls stay selling-class heuristic).  
- A CE/PE entry from expiry afternoon.

### UNKNOWN / DATA_INSUFFICIENT

- Exact Dhan/exchange settlement field mapping for index options **not extracted** this pass.  
- Historical option settlement series on HQ.

### 06 backtest (later, fixtures)

1. Tag days `EXPIRY` vs `NORMAL`.  
2. Measure `|official_close − 15:15|` and F&O mark vs 15:15 — **descriptive**, not a trade.  
3. Do **not** simulate assignment on European cash-settled index options.  
4. `RETUNE_PROPOSAL` stays `BACKTEST_REQUIRED`. Expiry days are **excluded** retune samples.

### 05 / 00 customer talk

On `EXPIRY`: **WATCH or VETOED / NO_TRADE** into the auction — “Expiry: cash close is the auction, not 15:15 — UNVALIDATED.” **Never CONFIRMED** from this ID. 05 already blocks EARLY on `EXPIRY`.

---

## CAS-005 — PRE_OPEN_GAP

**Name:** pre-open call auction gap / open print  
**Tag:** **`PRE_OPEN`** — **not** the CAS acronym  
**Origin:** **EXCHANGE-DERIVED** pre-open clocks + **PROJECT-DERIVED** gap book  
**DHAN-DERIVED:** no (009’s 09:15–09:45 skip is Gokul **open noise**, not pre-open CAS)

### Clock (IST)

| Id | Clock | What it is |
|----|-------|------------|
| `PRE_OPEN` | typically **09:00–09:15** (NSE timings / 2026 alignment **VERIFY**) | Cash (and aligned F&O) **call auction** at the **open**. Random close ~09:08–09:10 spoken in broker notes — **VERIFY circular**. |
| Continuous | 09:15– | CTS / F&O open. |

**Must not collapse** `PRE_OPEN` into `CAS`. CAS is the **close** auction 15:15–15:35.

Gokul ignore **09:15–09:45** (STRAT-009) starts **after** pre-open match. 009 ≠ CAS-005.

### Inputs

| Input | Source | If missing |
|-------|--------|------------|
| Pre-open IEP / indicative | Exchange | `DATA_INSUFFICIENT` — no DhanHQ pre-open REST documented. |
| Prior close vs 09:15 open | OHLC fixture | Gap description only. |
| GIFT/SGX | Public delayed **VERIFY** | Overlay, not Dhan. |
| Chain 3m | First poll after 09:15 if token | After open; not a pre-open chain. |

### Must NOT claim

- That this is **CAS**.  
- A CE/PE fill from the pre-open print.  
- Official 09:08/09:10 times without filing the 2026 circular.

### UNKNOWN / DATA_INSUFFICIENT

- Dhan pre-open REST.  
- Exact 2026 F&O pre-open alignment times (broker explainers vs circular PDF not in-repo).

### 06 backtest (later, fixtures)

1. Separate book: overnight gap vs first 15–30m FUTIDX.  
2. Do **not** mix samples with CAS-001 close-bias.  
3. STRAT-009 open skip remains a **different** switch.

### 05 / 00 customer talk

**WATCH reason:** “PRE_OPEN book — not CAS.” Opening drive 09:15–09:45 already vetoes new CE/PE (PERSONA / 009). **Not CONFIRMED.**

---

## How the five IDs attach (not soup)

| ID | Customer stage max | Relates to STRAT-009? | Relates to OPTION_BUYER mix? |
|----|--------------------|----------------------|------------------------------|
| CAS-001 | **WATCH** reason (bias) | No | Overlay only — never primary |
| CAS-002 | **WATCH / EXPIRED / VETO** | 009 already out before 15:15 if on | Tail risk if 009 off |
| CAS-003 | **VETO** new entries 15:15–15:35 | **Complement, not replace** | Filter |
| CAS-004 | **WATCH / VETO** on `EXPIRY` | No | Size to no-trade |
| CAS-005 | **WATCH** (`PRE_OPEN`) | Distinct from 09:15–09:45 skip | Separate book |

**04:** do not add these as `STRAT-015+`. Optional later YAML `cas_filters: [CAS-003]` with origin `PROJECT-DERIVED`.  
**05:** already: CAS daily book on WATCH only; no CONFIRMED from CAS.  
**09:** notes ≠ pass.

---

## UNKNOWN / blockers (workspace)

| Gap | Status |
|-----|--------|
| Live IEP / imbalance / indicative index (Dhan or NSE/BSE) | **DATA_INSUFFICIENT** |
| Official 74467 F&O timing PDF | **TODO** — 15:40 **VERIFY** |
| English Dhan “Closing Auction Session” recipe | **None** — no DHAN-DERIVED CAS STRAT |
| Settlement formula for index options | **Do not invent** |
| SENSEX vs NIFTY close divergence series | Not extracted |

**No coded strategy. No fills. Still `UNVALIDATED`.**
