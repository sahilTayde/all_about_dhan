# STRAT-001–014 — market VALIDATION (NSE/BSE, chain, clocks, lots, VWAP object)

## Transcript bind re-sign (English)

**Date:** 2026-09-03  
**Authority:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) (01 `SOURCE_FACT`; English `normalized_en/` wins). Mix: [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) after bind rewrite. This file = **VALIDATION**. Do **not** re-sign from a stale STRAT copy.

**Status:** `DRAFT` / `UNVALIDATED`. Gate: **not** `RESEARCH_READY_FOR_PROGRAMMING`. Affiliation ≠ edge. No lots frozen. No fills invented.

| Bind / mix claim | 03 re-sign | Market object |
|------------------|------------|---------------|
| **Guests.** Gokul (`2RnBT9DDDNI` 01:57–02:50): spoken **SEBI registered Research Analyst**. Himanshu (`HAUSZx` 00:54–01:02): **“Star Trader of this Dhan Platform”** — **not** spoken SEBI RA in that EN file. Mukul: no RA in the open. | **ACCEPT as affiliation only** | Not VALIDATION. Not a reason to code 003, freeze lots, or treat a recipe as exchange law. |
| **007 vs 009** stay **separate speakers**. Gokul: ignore 09:15–09:45, **start 09:45**, flatten **15:15**. Himanshu: new entries after **10:00**, mostly not after **14:30**. Phase-1 **AND** = **`PROJECT_MIX`**. | **ACCEPT WITH CLOCK GRID** | Keep two IDs. AND is 04 clubbing, not NSE/BSE. Do not cite one timestamp as if both agreed. |
| **002 never on 003.** Gokul: OTM **not recommended** (`2Rn` 38:06–38:13). 002 = HAUS slightly OTM. | **ACCEPT** (`CONFLICT` if attached) | Strike follows the **primary’s video**. 003 ticket = **005 only**. |
| **005** ITM / max ATM / strike-from-spot | **CONFIRMED** (EN) | **OPTIDX** moneyness vs **spot level**. OTM ban is this video, not HAUS. |
| **005** delta **0.60–0.75** | **WEAK** (EN digits) | Not an exchange band. Do not freeze 0.63–0.74 as market law. Host vs guest **50-multiples** stays `TEST_ON_OFF`. |
| **001** spoken universe = **NIFTY 100 stocks** (+ options application) | **PROJECT_MIX** if yaml is index-only `{NIFTY, BANKNIFTY, SENSEX}` | Stock cash volume is real; **does not transfer** to cash-index volume. Index-options book is a **transfer**, not HAUS’s taught universe. SENSEX still **BSE** if that book is tested. HAUS **2h parent** = `NOT_IN_EN`. |
| **011** index-option reversal | **PROJECT_MIX** | `H_6kee` = stocks / gold. **gA5 fill = bull put SELL (013), not buy CE.** Do not map that fill onto Phase-1 long premium. |
| **013 / 014** | **CONFIRMED SELL** — stay **WAITING** | Credit / 1-3-2 = **OPTIDX sell**. Not buy UI. 014 Tuesday NIFTY expiry stays `FROM_CONTRACT` (dated). |
| **15:15 flatten** vs F&O **15:40** | **Still a market-structure gap** | Spoken 15:15 = Gokul filter **and** CAS CTS end on F&O-cash names. Equity derivatives **09:15–15:40 VERIFY**. Bind does **not** close this. Keep `flatten_ist ∈ {15:15_spoken, 15:40_fo}`. |
| Spoken **3m** futures (`2Rn`, CONFIRMED) vs HQ `{1, 5, 15, 25, 60}` | **Keep** — 3m is **not** an HQ interval | `resample_hypothesis`. Staging 5m confirm = **`PROJECT_MIX`**, not Gokul’s 3m entry. |

**Same-video Gokul stack (not PROJECT_MIX):** 003 + 004 + 005 + 008 + 009 on `2RnBT9DDDNI` is one class. 03 already mapped that stack to **FUTIDX** signal / **OPTIDX** buy. Splitting IDs is bookkeeping.

**Would still REJECT the mix:** 002 on a 003 ticket; 007+009 collapsed and labeled DHAN-DERIVED; 013/014 as buy; cash-index VWAP; 3m as official HQ `interval`; frozen lots/weekdays; SEBI RA / Star Trader as edge.

---

## 03 SIGN-OFF ON ENGINE_MIX (2026-09-03)

**Read:** [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) (04 HYPOTHESIS), [`SIGNAL_FUSION.md`](../../05_analysis/docs/SIGNAL_FUSION.md) (05 overlay), [`STRAT_001_014_VALIDATION.md`](../../02_phd_math/docs/STRAT_001_014_VALIDATION.md) (02 math). This file remains **VALIDATION**. Mix remains **UNVALIDATED**. Gate: **not** `RESEARCH_READY_FOR_PROGRAMMING`. No lots frozen. No fills invented.

**Overall:** **ACCEPT WITH CLOCK GRID** — default BULL/BEAR ticket `003 + 007/008/009 + 5m ST/MACD confirm-or-kill + 005` does **not** reintroduce cash-index volume, does **not** merge strike IDs, and does **not** treat 3m as an HQ interval. Flatten **15:15** and the 007∩009 AND stay **filters**, not exchange close. Keep `close_model` parameterized.

| Item | Verdict | Market note |
|------|---------|-------------|
| `ohlc: FUTURES` + `vwap_tape: FUTURES_OR_OPTION` + SENSEX **BSE** | **ACCEPT** | Mix YAML does not reintroduce cash-index volume. NIFTY/BN = NSE FUTIDX; SENSEX = BSE FUTIDX / `BSE_FNO`. |
| **003 as primary**; spoken **3m** vs HQ-native **5m** confirm | **ACCEPT** | 003 object = **FUTIDX** VWAP+VWMA+ST. 3m stays `resample_hypothesis` (not in `{1,5,15,25,60}`). Staging 5m ST/MACD is **confirm/kill**, not the 2RnBT9 3m entry. Ablate 3m-resample vs 5m-native vs 1m-lead — do not pick a winner here. |
| **009 flatten 15:15** vs F&O **15:40** VERIFY | **ACCEPT WITH CLOCK GRID** | 15:15 = speaker filter **and** CAS CTS end on F&O-cash names — **not** equity-derivatives close. F&O still **09:15–15:40 VERIFY**. Parameterize `flatten_ist ∈ {15:15_spoken, 15:40_fo}`. YAML `cas: false` is correct (do not fuse cash-CAS into the option lean). Circuit days can skip CAS — do not assume 15:15 always prints. |
| **007 vs 009 not merged**; Phase-1 **AND** (no new 09:15–10:00, no new after 14:30, flatten 15:15) | **ACCEPT WITH CLOCK GRID** | AND is a **conservative intersection**, not speaker agreement. Keep two IDs. Grid 007 afternoon `{14:30, 14:45, 15:00}`. Do **not** freeze the AND as “the” session. 014 Monday 09:45 still fights 009 — irrelevant while 014 is WAITING. |
| **005 strike on 003**; 002 only on 001-alt; 006 only on 006-alt | **ACCEPT** | Matches 2RnBT9 (ITM/max ATM). **Do not merge** with 002 (slightly OTM) or 006 (100–200 pts). NIFTY 50-multiples = liquidity `TEST_ON_OFF`; SENSEX step **UNKNOWN**; BANKNIFTY monthly-only **VERIFY**. Not a merged strike. |
| **008** mixed-index → Phase-1 **no-trade** | **ACCEPT** | Three **separate** FUTIDX signs (NSE NIFTY, NSE BANKNIFTY, BSE SENSEX). Do not pick dominant after the close. Do not combine venue volume. |
| **NEWS_DAY** / `MACRO_EVENT` / extreme PCR-only = **veto** | **ACCEPT** | 05 overlay, not a STRAT. No EARLY while `NEWS_DAY` or `EXPIRY`. Event wins until **one 3m chain**. Extreme PCR without price is **not** a signal. CAS daily `BOUNCE\|SIDEWAYS\|FALL` stays **UNVALIDATED** (WATCH reason only). |
| `expiry` / `lot_size` `FROM_CONTRACT` | **ACCEPT** | Do not freeze HAUS Thursday, 6el9/014 Tuesday, or lot 65. `EXPIRY` tag = nearest sheet date equals session date (03/nightly); 05 consumes, does not retune weekday. |
| Chain poll **3m** as EARLY L3; not 1m full-chain | **ACCEPT** | HQ 1 unique / 3s. Strike-pick (005 on this ticket) **needs** a chain snapshot to name the contract. 003 VWAP math does not. |
| HQ historical option quotes / 010 OF | **ACCEPT** (fixtures / parked) | Option history **DATA_INSUFFICIENT** → 06 **fixtures only**. 010 stays parked. Do not proxy cash-index ticks. |
| 013 / 014 on Phase-1 buy ticket | **REJECT** (already out of mix — keep out) | WAITING sell. `_exm` OI-wall / max-pain is **not** a buy STRAT. |
| 004 Super Scalper lengths invented / 7,3 imported | **REJECT** if coded | 004 stays `DATA_INSUFFICIENT`. `_byuht` 7,3 is equity — not index. |

**Rejected from this sign-off (would flip to REJECT the mix):** cash-index VWAP; 3m as an HQ `interval`; 002+005 on one ticket; 007+009 collapsed into one ID; 15:15 hardcoded as F&O close; frozen lots/weekdays; 05 promoting CONFIRMED; 013/014 as buy UI.

---

```text
From:     teams/03_phd_market
To:       02_phd_math / 04_quant / 05_analysis / 09_review
Date:     2026-09-03
Status:   DRAFT / UNVALIDATED / WAITING_FOR_EDIT
Gate:     NOT RESEARCH_READY_FOR_PROGRAMMING
Layer:    VALIDATION (this file). Transcript lines remain SOURCE_FACT on 01 packets.
          STRAT specs remain HYPOTHESIS on 04. Do not collapse layers.

Summary:
Independent market map of the 14 index IDs onto legal tape (FUTIDX vs OPTIDX vs
forbidden cash-index volume), NSE vs BSE, FROM_CONTRACT lots/expiry, option-chain
use, and CAS 15:15–15:35 vs F&O 15:40 VERIFY. Strike 002 vs 005 vs 006 stay
alternative hypotheses. _exm OI-wall / max-pain is a selling-class heuristic —
not a buy STRAT.

What 02 must do:
- Run VWAP/VWMA/volume-delta only on FUTIDX or the option tape.
- Treat 2m / 3m / 2h as resample UNKNOWN (HQ intraday enum is 1, 5, 15, 25, 60).

What 04 must do:
- Attach 007≠009 clocks as separate filters. Do not freeze video weekdays/lots.
- Keep 002 / 005 / 006 as ablations. Do not code 013–014 into Phase-1 buy UI.

What 05 must do:
- Desk full-chain poll stays 3m. That snapshot is required before CONFIRMED when
  the ticket needs strike/delta/OI, or after MACRO_EVENT — not for clock filters.

What 09 must not do:
- Treat this file as a five-pass. Notes ≠ pass. No win rates. No live Dhan.

Blockers / UNKNOWN / DATA_INSUFFICIENT:
- Official lot circular PDF and F&O 15:40 circular not in-repo.
- BSE SENSEX strike step / tick not extracted.
- HQ historical option quotes and DEXT order-flow history: DATA_INSUFFICIENT.
- HAUS Thursday NIFTY weekly vs 6el9 Tuesday: dated vs partially_supported —
  both stay SOURCE_FACT; engine reads expiry_date.

Review: notes only
```

**Team:** 03_phd_market  
**Date:** 2026-09-03  
**Status:** `DRAFT` / `UNVALIDATED` / `WAITING_FOR_EDIT`  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**No profitability claimed. No invented lots, fills, or win rates. No live Dhan.**

Cites: [`VALIDATION_MARKET.md`](VALIDATION_MARKET.md), [`TRANSCRIPT_MARKET_NOTES.md`](TRANSCRIPT_MARKET_NOTES.md), [`CHAIN_METRICS.md`](CHAIN_METRICS.md), [`DESK_EXECUTION_NOTES.md`](DESK_EXECUTION_NOTES.md), [`../cas/RESEARCH.md`](../cas/RESEARCH.md), [`../../01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md`](../../01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md), [`../../04_quant/docs/MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md), [`../../04_quant/docs/SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md), candidates `STRAT-001.md`–`STRAT-014.md`.

---

## Shared market facts (apply to every ID)

| Fact | VALIDATION |
|------|------------|
| NIFTY 50 / BANKNIFTY | **NSE**. Index options + futures. Quotes typically `NSE_FNO`; chain body underlying seg usually `IDX_I`. **VERIFY** scrip from instrument master. |
| SENSEX | **BSE**. Different strike step, lot, tick, host, weekly weekday. Do not reuse a NIFTY chain client, lot, or calendar. |
| Cash index | **Calculation, not a tradable lot.** No authentic trade volume. Vendor “index volume” is **unsupported** for VWAP / VWMA / volume-delta. |
| Legal split | **FUTIDX** = signal tape when the rule needs volume or a traded series. **OPTIDX** = Phase-1 execution (CE/PE **buy**). Cash-index **price** may be used as a level (spot for strike mapping). Cash-index **volume** is forbidden. |
| Expiry / lot | **`FROM_CONTRACT` / instrument master at as-of date.** Never freeze a speaker weekday or lot (HAUS Thursday sequence **dated**; 6el9 Tuesday **partially_supported** post-Sep-2025; 2RnBT9 “65 × premium” is one vintage). |
| HQ bar enum | Intraday `{1, 5, 15, 25, 60}` min. **3m (STRAT-003) and 2m (STRAT-006) are not native.** 2h (gA5 / STRAT-011 parent) is also not in that enum. |
| CAS | Official **Closing Auction Session** on F&O **cash** names: CTS ends **15:15**; CAS **15:15–15:35** IST; close = **equilibrium**, not last-30-min VWAP. Live **3 Aug 2026**. Circuit-breaker days can **skip** CAS. |
| Equity derivatives | **09:15–15:40** IST (NSE CAS page + timings). **VERIFY** — official 74467 PDF not stored in-repo. Not the cash auction. |
| Chain plumbing | `POST /optionchain`; **1 unique / 3s**; desk full-chain poll **3m** (Δ vs last snapshot). CE/PE wall and max-pain stub = definitions ([`CHAIN_METRICS.md`](CHAIN_METRICS.md)); operator “wall = S/R” = **HYPOTHESIS**. |
| Phase-1 | CE/PE **buy first**. 013–014 stay **WAITING** sell. `_exm` OI-wall / max-pain selling class is **not** a buy STRAT (see §OI walls). |
| Staging clocks | 5m Supertrend/MACD **promote or kill**, not entry ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)). EXPIRED close clock is **VERIFY** 15:30 vs 15:40. Flatten **before 15:15** is trader `SOURCE_FACT`, not F&O close. |

```yaml
session_tz: Asia/Kolkata
expiry: FROM_CONTRACT
lot_size: FROM_INSTRUMENT_MASTER
sensex_exchange: BSE
vwap_tape: FUTURES_OR_OPTION    # never CASH_INDEX
close_model:
  cas_cash_names: 15:15-15:35_equilibrium
  equity_derivatives: 15:40      # VERIFY circular
  non_cas_cash: 15:30
```

**Chain-use vocabulary in this file:** `none` | `strike pick` | `OI heuristic` | `DATA_INSUFFICIENT`.

**3m snapshot vs CONFIRMED (how 05 should read the per-ID line):** desk mix uses OI buildup as a **leading** ingredient and **MACRO_EVENT** as a veto until one 3m chain ([`PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md), SIGNAL_STAGING). That overlay is **global**. Per ID below, “required” means the **STRAT’s own** ticket cannot name a contract or honor the operator checklist without a chain snapshot. Clock-only filters do not.

---

## STRAT-001 — Dual-TF MACD × MA stack, long premium

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | Signal on **underlying OHLC** (04 prefers **FUTIDX** for a tradable series; speaker HAUS also used stocks/spot). Execution **OPTIDX BUY**. Cash-index **volume** forbidden (this ID does not need volume). Cash-index **price** is a constructed series — do not treat it as a lot. |
| **Exchange** | NIFTY / BANKNIFTY **NSE**; SENSEX **BSE**. Separate tokens. |
| **Expiry / lot** | `FROM_CONTRACT`. HAUS-EN-07 Thursday NIFTY weekly list (19 Jun / 26 Jun / 3 Jul …) is **dated** — do not freeze. Screen premium × lot examples **ephemeral**. |
| **Chain use** | `none` (direction only). Strike is STRAT-002 if attached. |
| **Clock vs CAS / 15:40** | No own flatten. Attach 007 (entries after 10:00, not after 14:30 / 15:00). EOD flatten default ≠ CAS equilibrium and ≠ F&O **15:40**. Parameterize; do not hardcode 15:30. |

- **TO 02:** MACD histogram + MA stack on **underlying close** (prefer FUTIDX). Not on random OTM premium. Not on cash-index volume. MACD ×3/×4 and MA 9 vs 10 / 100 vs 300 stay `SOURCE_UNCERTAIN` search — 03 has no exchange object that resolves them.
- **TO 04:** Attach 002 (strike) and 007 (clock) as **overlays**, not a merged “Dhan system.” Do not freeze HAUS Thursday expiry. Accept as UNVALIDATED direction candidate on `{NIFTY, BANKNIFTY, SENSEX}` with BSE isolated for SENSEX. 5m child **is** in the HQ enum; 1h parent is 60m.
- **TO 05:** 001’s own CONFIRMED path is lagging MACD/MA on the underlying — **3m chain not required for that math.** If the desk mix uses OI/news, the **global** 3m overlay still applies. Strike-attached tickets need 002’s chain line.

---

## STRAT-002 — Slightly OTM, 20–30% premium scale-out

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | **OPTIDX** strike/exit overlay on 001 (or 003). Signal remains the host underlying. Forbidden: cash-index volume as liquidity proof. |
| **Exchange** | Same as host. NIFTY strike step “multiples of 50” is **partially_supported** (HAUS-EN-05); SENSEX/BANKNIFTY steps **UNKNOWN here**. |
| **Expiry / lot** | `FROM_CONTRACT`. Illiquid 50-point NIFTY strikes are a **desk liquidity** issue, not a frozen lot. |
| **Chain use** | `strike pick` (1–2 strikes OTM; spoken adverse ~0.40 delta). Bid/ask on the option. **Not** OI-wall. Rolling HQ proxy: CE **`ATM+1`** / PE **`ATM-1`** — [`ROLLING_OPTION.md`](ROLLING_OPTION.md). |
| **Clock vs CAS / 15:40** | Inherits 001/007. OTM theta into expiry afternoon / CAS-sensitive index close — risk comment, not a new clock. |

- **TO 02:** Moneyness and Greek **delta on the option**. Underlying stop = swing on FUTIDX or spot **level**. 20–30% of **entry premium** is an option-LTP object, not futures points.
- **TO 04:** Overlay only — **reject as standalone.** **Do not merge** with 005 or 006 (see §Strike conflicts). Ablate OTM vs ATM vs ITM on the **same** 001/003 signals.
- **TO 05:** **Yes** — a CONFIRMED ticket that uses 002 must have a chain (or quote) snapshot to **name the strike** and see spread. 3m full-chain is the desk default; do not invent 1m full-chain.

---

## STRAT-003 — 3m futures VWAP + VWMA(20) + Supertrend(10,3)

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | Signal **FUTIDX only** (session VWAP + VWMA + ST). Execution **OPTIDX BUY**. **Cash-index VWAP = unsupported** (2RnBT9 English: analyse futures for true volume; pick strike from spot; trade premium). |
| **Exchange** | NIFTY/BANKNIFTY **NSE** futures; SENSEX **BSE** futures. Do not mix tapes. |
| **Expiry / lot** | `FROM_CONTRACT`. 2RnBT9 capital toy **65 × premium** (~16:55) matches **one** vintage — **never freeze lot 65.** BANKNIFTY weekly discontinued (one-weekly-per-exchange regime) — monthly liquidity **VERIFY**. |
| **Chain use** | `none` for the VWAP signal. Strike default in 04 spec is STRAT-005 → then `strike pick`. |
| **Clock vs CAS / 15:40** | Ignore 09:15–09:45 (trader heuristic). `flatten_before: 15:15` is **speaker SOURCE_FACT**, coinciding with **CAS CTS end** on F&O-cash names, **not** equity-derivatives close. F&O still prints **to 15:40 VERIFY**. Scalps after 15:15 face cash auction + later F&O. Circuit days can skip CAS — do not assume 15:15 flatten always exists as an exchange event. |

- **TO 02:** Session VWAP = Σ(P·V)/ΣV and VWMA(20) on **FUTIDX OHLC+volume**. Supertrend on that same futures close. Quote `average_price` / feed ATP = day snapshot, **not** VWAP bands. **3m is not in HQ enum** — resample method `UNKNOWN`.
- **TO 04:** **Reject 3m as a native HQ interval.** Attach only as a resample HYPOTHESIS (e.g. from 1m). Do **not** hardcode flatten 15:15 as F&O close — parameterize `{spoken_1515, fo_1540 VERIFY}`. Default strike 005 **conflicts** 002 — keep as the 2RnBT9 video’s strike, not a merge. Attach 008 on mixed-index days.
- **TO 05:** 003’s own confirm is futures ST vs VWAP — **3m chain not required for that.** If 005 is attached, strike-pick **is** required. Global event overlay: one 3m chain after `MACRO_EVENT` before treating CONFIRMED as live.

---

## STRAT-004 — Premium Super Scalper EMA confirm

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | Confirm on **option LTP** (1m premium chart). Direction from 003/001 (**FUTIDX** or dual-TF underlying). Execution **OPTIDX**. Cash-index volume N/A. |
| **Exchange** | Option on NSE (`NSE_FNO`) or BSE (`BSE_FNO`) matching the underlying. |
| **Expiry / lot** | `FROM_CONTRACT`. |
| **Chain use** | `none` for the EMA rule. Super Scalper fast/slow lengths **UNKNOWN** → candidate already `DATA_INSUFFICIENT` (04). |
| **Clock vs CAS / 15:40** | Inherits 003/009 if attached. 1m premium wicks into 15:15–15:40 are **spread + CAS/basis**, not a new edge. |

- **TO 02:** Fast/slow EMA on **option close**, not futures. Do not invent 9/21. 1m **is** in the HQ enum. Premium-chart stop ≠ futures stop ([`DESK_EXECUTION_NOTES.md`](DESK_EXECUTION_NOTES.md)).
- **TO 04:** Keep `DATA_INSUFFICIENT` until Dhan Super Scalper lengths are documented from charts (Tier 2). Attach as **confirm after** 003/001 — not a standalone entry. Do not short the call.
- **TO 05:** **Not required** for 004 math. Spread check from chain is desk hygiene, not this ID’s CONFIRMED gate.

---

## STRAT-005 — High-delta ITM / ATM buy (0.60–0.75)

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | **OPTIDX** strike overlay. Spoken: strike from **spot** at signal, not futures. Spot = **price level** (allowed). Futures = signal tape for 003. Forbidden: cash-index volume. |
| **Exchange** | NSE vs BSE per underlying. SENSEX delta/strike grid **UNKNOWN** this pass. |
| **Expiry / lot** | `FROM_CONTRACT`. `avoid_50_multiples` is host-vs-guest — test flag, not an exchange law. 1 ITM lot may exceed RM (discrete lots). |
| **Chain use** | `strike pick` (abs delta ~0.60–0.75; spoken 0.63–0.74 `[UNCERTAIN_TRANSCRIPT]`; fallback nearest ATM or 1 ITM). Greeks from documented `POST /optionchain` fields. **Not** OI-wall. Rolling HQ proxy: CE **`ATM-2`** / PE **`ATM+2`** — [`ROLLING_OPTION.md`](ROLLING_OPTION.md). |
| **Clock vs CAS / 15:40** | Inherits 003/009. |

- **TO 02:** **Greek delta on the option** (not volume-delta). If history lacks greeks: map “1–2 strikes ITM” from **spot**. Delta ≠ win rate. Deep >0.74 “not that much logic” is speaker opinion.
- **TO 04:** Default strike for **2RnBT9 / 003** — **do not merge** with 002 (slightly OTM) or 006 (100–200 pts ITM). Ablate on the same signals. OTM **not** recommended **in this video** — keep the conflict.
- **TO 05:** **Yes** — CONFIRMED tickets using 005 need chain/greeks (or a documented spot-ITM fallback) to pick the contract. 3m poll is the default; greeks can be stale between snapshots.

---

## STRAT-006 — 2m EMA 10/20 ITM scalp

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | Analysis: speaker used **spot OHLC** (price allowed). 04: futures may be more honest — **TEST**, do not silently swap. Execution **OPTIDX BUY**. EMA does not need volume; if anyone puts VWAP on this ID, tape must be FUTIDX or the option — **never cash index**. |
| **Exchange** | NIFTY / BANKNIFTY **NSE**; SENSEX **BSE**. Speaker applied **100–200 pts ITM on all three** — that is **NIFTY-scale folklore**, not a proven SENSEX moneyness (different step/lot). |
| **Expiry / lot** | `FROM_CONTRACT`. Video did not freeze a lot. Do not freeze 100–200 pts as eternal or venue-identical. |
| **Chain use** | `strike pick` (ITM 100–200 pts; delta spoken “555 to 6” / 0.55 `[UNCERTAIN_TRANSCRIPT]`). |
| **Clock vs CAS / 15:40** | No own flatten. 2m scalps into last minutes face **CAS cash** effects **and** F&O to **15:40**. If 009 attached, flatten **15:15** kills the late scalp by design. Speaker: beginners should **not** buy-scalp — keep both claims. |

- **TO 02:** EMA 10/20 on **spot close or FUTIDX close** (ablate). **2m not in HQ enum** — resample `UNKNOWN`. Object is **price**, not cash-index volume.
- **TO 04:** **Reject 2m as a native HQ interval** (same class of problem as 003’s 3m). **Do not merge** strike with 002 or 005. Flag internal buy-scalp vs “beginners should not.” SENSEX 100–200 pts ≠ NIFTY 100–200 delta. Highest cost sensitivity in the set ([`DESK_EXECUTION_NOTES.md`](DESK_EXECUTION_NOTES.md)).
- **TO 05:** Strike-pick **yes** if the ticket uses 006. **Mismatch:** 2m decision vs **3m** full-chain poll — chain **cannot** honestly confirm a 2m scalp in lockstep. Do not pretend a 3m snapshot is a 2m lead. ATM±N quote path is VERIFY; full-chain 1m remains the **wrong** default.

---

## STRAT-007 — HAUS session clock (filter)

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | Filter only. No tape of its own. Attaches to 001/003/006 **OPTIDX** buys. |
| **Exchange** | IST clocks; NSE and BSE cash/F&O sessions share the same IST skeleton unless a circular says otherwise. |
| **Expiry / lot** | n/a (host contract `FROM_CONTRACT`). |
| **Chain use** | `none`. |
| **Clock vs CAS / 15:40** | New entries **after 10:00**, mostly **not after 14:30**, **hard ban after 15:00**. Trader heuristic — **not** CAS and **not** F&O close. 15:00 ban is **before** CAS 15:15. `eod_flatten: true` does **not** name 15:15 vs 15:40 — do not silently copy 009. 14:45 vs 15:00 wording `UNCERTAIN_TRANSCRIPT`. |

- **TO 02:** No indicator object.
- **TO 04:** Attach to 001. **Do not merge with 009** (different speaker). Ablate 14:30 vs 14:45 vs 15:00. Do not treat 15:00 as exchange close.
- **TO 05:** **No** for this filter. Event-day 3m overlay remains global.

---

## STRAT-008 — Mixed-index avoid / dominant only (filter)

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | Alignment on **each index’s FUTIDX**, never a fake combined **cash-index volume**. Execution still **OPTIDX** on the chosen name. |
| **Exchange** | NIFTY + BANKNIFTY **NSE**; SENSEX **BSE**. Three hosts — do not compare “index volume” across vendors. |
| **Expiry / lot** | `FROM_CONTRACT` **per product**. BANKNIFTY monthly-only caveat **VERIFY**. |
| **Chain use** | `none` for the avoid rule. Do not pick “dominant” from PCR/OI (that would be an `OI heuristic` 04 did not spec). |
| **Clock vs CAS / 15:40** | “That day” — no flatten. CAS can **diverge** NSE vs BSE constituent closes (two order books) — mixed-index days into 15:15–15:40 are extra-dirty, not a new alpha. |

- **TO 02:** Sign of 003/001 on **three FUTIDX** series, independently. No cross-venue VWAP.
- **TO 04:** Attach to 003/001 as **risk overlay**, not edge. **Pre-declare** dominant (look-ahead if chosen after the close — 04 already flags). Accept. Optional 1-lot-each vs 3-in-one is a size test, not a market fact.
- **TO 05:** **No** for 008 itself. Do not substitute 3m PCR for futures alignment.

---

## STRAT-009 — Open skip 09:15–09:45 + flatten 15:15 (filter)

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | Filter only. Host tape unchanged. |
| **Exchange** | IST; both venues. |
| **Expiry / lot** | n/a. |
| **Chain use** | `none`. |
| **Clock vs CAS / 15:40** | **Open skip:** context-dependent (auction + open volatility), **not** an exchange mandate. **Flatten before 15:15:** speaker heuristic **and** CAS CTS end on F&O-cash names. Equity **derivatives still trade to 15:40 VERIFY** → 25 minutes unused if 009 is law. Index “spike” at ~15:30 may be **auction discovery**, not trend continuation ([`cas/RESEARCH.md`](../cas/RESEARCH.md)). MWCB / early close: CAS skipped; working orders cancelled — **do not assume flatten at 15:15 always prints** ([`DESK_EXECUTION_NOTES.md`](DESK_EXECUTION_NOTES.md)). Complements 007 — **do not silently merge.** |

- **TO 02:** Session windows only. No VWAP object in this ID (003’s VWAP is a different object).
- **TO 04:** **Attach to 003.** Parameterize `flatten_ist ∈ {15:15_spoken, 15:40_fo VERIFY}`. **Reject** treating 15:15 as F&O close. **Reject** merge with 007. SIGNAL_STAGING EXPIRED close is the same VERIFY pair — do not stamp F&O EXPIRED at 15:15 unless this filter is attached.
- **TO 05:** **No** for the filter. POST_MARKET `after_ist: 15:40` is the derivatives clock; do not close the desk book at 15:15 unless 009 is on.

---

## STRAT-010 — Futures order-flow delta / POC overlay

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | **FUTIDX** footprint: executed buy−sell **volume-delta**, POC, VAH/VAL, imbalance. YUXJv demo = **NIFTY futures**. DzT demo = **Reliance cash** (stock volume is real; **does not transfer** to cash index). **Forbidden:** cash-index ticks as OF proxy. VWAP in these videos = traded name. **Greek delta ≠ volume delta.** |
| **Exchange** | NIFTY/BANKNIFTY NSE FUTIDX. SENSEX BSE OF coverage **DATA_INSUFFICIENT** this pass. |
| **Expiry / lot** | n/a overlay. |
| **Chain use** | `none`. HQ/DEXT OF **history** = `DATA_INSUFFICIENT` (do not proxy with chain OI). |
| **Clock vs CAS / 15:40** | Inherits host. OF into CAS: cash names have **no continuous match** 15:15–15:30; F&O still trades — do not read a flat cash chart as OF on the index. |

- **TO 02:** Object = **futures (or stock) trade prints**, not option-chain OI, not IDX_I volume. Imbalance ≥3× is a spoken default, not an exchange law.
- **TO 04:** Overlay only. **Stay `DATA_INSUFFICIENT`.** Do not block engine design. Do not invent a buy STRAT from DzT four rules. Do not attach as Phase-1 CONFIRMED gate.
- **TO 05:** **No** — OF is not the 3m chain. Do not substitute PCR/walls for footprint. Desk 3m chain still runs as the **separate** OI overlay.

---

## STRAT-011 — RSI divergence → Supertrend child (index transfer)

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | `PROJECT-DERIVED`. gA5 **view** on **NIFTY** (2h); **executed** example was a **bull put credit (sell)**. Phase-1 test = **OPTIDX BUY** CE/PE — that mapping is **not** the video fill. RSI on index **price** (allowed). Execution OPTIDX. Cash-index volume forbidden. |
| **Exchange** | Video: NSE Index → NIFTY. Transfer to SENSEX = **BSE** (do not reuse NSE chain). |
| **Expiry / lot** | `FROM_CONTRACT`. gA5 skipped same-day (23 Jan) / used 30 Jan / budget week — **dated**. Do not freeze those dates or “~1 week.” |
| **Chain use** | `none` for RSI/ST. `strike pick` if 002 or 005 attached. Video’s put-spread strikes belong to **013**, not this buy transfer. |
| **Clock vs CAS / 15:40** | Intraday buy vs swing sell (gA5). No 15:15 flatten in this ID. Intraday TFs spoken 15m / 5m / 10m; 5m/15m **are** in HQ enum; **2h parent is not**. |

- **TO 02:** RSI on **index or FUTIDX close**. Child Supertrend on 5m/15m OHLC (compute; not an HQ series). RSI 14 = EXTERNAL/standard unless a Dhan-spoken period appears. 2h resample `UNKNOWN`.
- **TO 04:** Accept as **PROJECT-DERIVED buy transfer** only. **Reject** coding the executed credit spread as this ID (that is 013 WAITING). Attach **002 xor 005**, not a merged strike. Not “Dhan said trade NIFTY options this way.”
- **TO 05:** RSI/ST confirm **does not** require chain. If 002/005 attached, strike-pick **yes**. Event overlay: 3m after print.

---

## STRAT-012 — Candle + S/R confluence overlay

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | Overlay on 001/003. Patterns on **underlying OHLC** (prefer **FUTIDX** so volume is real if a later pattern needs it; hammer wick/body is price-only). Cash-index **price** allowed; cash-index **volume** forbidden. |
| **Exchange** | Per host. |
| **Expiry / lot** | `FROM_CONTRACT` on host. |
| **Chain use** | `none`. |
| **Clock vs CAS / 15:40** | Inherits host. |

- **TO 02:** Object = **OHLC of FUTIDX (prefer) or index price**. Hammer 2–3× wick is a definition, not a predictor. Dhan auto-detect vs textbook = `SOURCE_UNCERTAIN` (04).
- **TO 04:** Overlay only. Four non-hammer patterns stay `WAITING_FOR_EDIT`. Do not promote to entry.
- **TO 05:** **No** for 012 itself.

---

## STRAT-013 — Bull put credit (weekly) — WAITING sell

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | **OPTIDX credit** (sell nearer put, buy further OTM put). **Not** Phase-1 buy. Index options **European, cash-settled** — no American exercise into the basket. Margin / SPAN = broker+exchange; rupee figures `[UNCERTAIN_TRANSCRIPT]`. |
| **Exchange** | Video NIFTY **NSE**. |
| **Expiry / lot** | `FROM_CONTRACT`. Skip 0 DTE; skip event weeks (budget example) — **dated calendar**. Do not freeze weekday. |
| **Chain use** | `strike pick` (put spread). **Not** `_exm` OI-wall. |
| **Clock vs CAS / 15:40** | Multi-day swing — not 15:15 flatten. **Settlement / marks / NAV** for names that use the official close are **CAS-equilibrium sensitive**. F&O still 15:40. |

- **TO 02:** Two **OPTIDX** puts. Defined max loss is premium/structure, not a cash-index VWAP. Do not use cash-index volume.
- **TO 04:** **Reject for Phase-1 buy UI.** Keep `WAITING`. Do **not** convert into a buy STRAT. Do not attach `_exm` OI walls as the entry.
- **TO 05:** N/A until selling is opened. If ever: strike-pick snapshot + 3m after `MACRO_EVENT`. Extreme PCR remains **veto / no-trade**, not alpha.

---

## STRAT-014 — Hedged 1-3-2 call ratio, Monday 09:45 — WAITING sell

| Field | VALIDATION |
|-------|------------|
| **Legal instrument** | **OPTIDX** 1-3-2 (buy 1 / sell 3 / buy 2 calls) as **basket**. Short 3 vs long 3 is defined **if** filled as a basket; **leg risk** otherwise ([`DESK_EXECUTION_NOTES.md`](DESK_EXECUTION_NOTES.md)). **Not** Phase-1 buy. NIFTY only in spec. |
| **Exchange** | NIFTY **NSE**. Video BANKNIFTY weekly “removed November 2020” is **dated**; current regime is **monthly-only** under one-weekly-per-exchange — **VERIFY**. |
| **Expiry / lot** | `FROM_CONTRACT`. Video froze **next Tuesday weekly** and Mon→Tue hold — Tuesday NIFTY is **partially_supported** post-Sep-2025; HAUS Thursday list is **dated**. **Do not freeze Tuesday or lot.** Structure S+200 / S+400 / S+600 is **index points**, not lots. `avoid_50_strikes` is speaker preference. Exit Friday EOD vs Tuesday expiry: calendar **VERIFY**. |
| **Chain use** | `strike pick` (three calls). Rule-based, no chart (6el9). **Not** OI heuristic. |
| **Clock vs CAS / 15:40** | Entry **Monday 09:45** sits **inside** STRAT-009’s 09:15–09:45 skip — **conflict; do not silently merge.** Hold across sessions → CAS-sensitive settlement if held to expiry. Spoken “bi-weekly” because of “that one day” — do not freeze. |

- **TO 02:** Three **OPTIDX** calls; basket vs leg fills. 1% of capital stop/target is a money object, not futures VWAP. POP 80% in 04 spec is **unsupported** — 03 adds no market proof.
- **TO 04:** **Reject for Phase-1 buy UI.** **Reject freezing Tuesday expiry.** Flag Monday 09:45 vs 009. Do not convert `_exm` selling OI into this ID. Spoken success-rate >50% is **not** a backtest.
- **TO 05:** N/A Phase-1. If selling opens: chain to list the three strikes; do not CONFIRMED off OI walls.

---

## Strike conflicts — alternative hypotheses (do not merge)

These are **three strike/moneyness hypotheses** from **three videos**. 04 already forbids a single “Dhan strike.” 03 **objects to any merge** at the market layer: strike step, liquidity, and delta are **not** interchangeable across NIFTY 50-pt grids vs SENSEX/BSE vs BANKNIFTY monthly.

| ID | Origin | Moneyness as spoken | Market comment |
|----|--------|---------------------|----------------|
| **STRAT-002** | HAUSZx | **Slightly OTM** (1–2 strikes); ATM “pumped”; adverse ~**0.40** delta | Needs chain **strike pick**. Rolling proxy CE `ATM+1` / PE `ATM-1` ([`ROLLING_OPTION.md`](ROLLING_OPTION.md)). OTM can be worthless on a correct-but-slow move (theta). 50-pt NIFTY may be wider than 100s — measure, don’t assume. |
| **STRAT-005** | 2RnBT9 | **ITM, maximum ATM; OTM not recommended.** Abs delta **~0.60–0.75** (spoken 0.63–0.74) | Needs chain **strike pick** / spot ITM map. Rolling proxy CE `ATM-2` / PE `ATM+2`. Higher debit; 1 lot may exceed RM. Default for **003**. |
| **STRAT-006** | pvmvki | **ITM only**, **100–200 points** on NIFTY **and** BANKNIFTY **and** SENSEX; not ATM/OTM/deep ITM; delta ~**0.55–0.60** `[UNCERTAIN]` | Needs chain **strike pick**. **100–200 pts is not a BSE SENSEX law** — different step/lot. Overlaps 005’s “ITM” language **numerically** but **not** as the same hypothesis (fixed points vs delta band vs 2m EMA scalp). |

**Verdict:** keep as **alternative hypotheses**. Ablate OTM vs high-delta ITM/ATM vs 100–200 ITM on the **same** direction signals (001/003). Do not average deltas. Do not ship one strike engine.

---

## OI wall / max-pain — selling class, not a buy STRAT

| Source | What it is | What 03 will not do |
|--------|------------|---------------------|
| `_exmJYgFwFA` EXM-C09 | Speaker **assumption**: highest OI + rising OI ≈ level “they” do not expect breached (call OI resistance / put OI support). Snapshot + dated geopolitics. | **Not** a Phase-1 **buy** STRAT. Not STRAT-015. Not silently attached as 002/005/006. |
| [`CHAIN_METRICS.md`](CHAIN_METRICS.md) | PCR, ATM, CE/PE wall, max-pain **stub**, gamma-load stub = **definitions** on a 3m snapshot. | Operator talk (pin, writing into rally) stays **HYPOTHESIS**. |
| Coalition / PERSONA_DESK | Extreme PCR / news = **veto / no-trade**, not alpha. | Do not convert walls into CE/PE **buy** entries. |

Phase-1 remains CE/PE **buy first**. Selling corpus (013, 014, `_exm` hedge catalog) stays **WAITING**.

---

## Clock / chain / VWAP — one-page for 04 / 05 / 09

| Verdict | Apply |
|---------|--------|
| **VWAP object** | **FUTIDX or the option.** Cash NIFTY/SENSEX calculation = **unsupported**. Only 003 (and 010’s traded-name VWAP) have a coherent VWAP object. 006 EMAs are not VWAP; do not “fix” them onto cash-index volume. |
| **3m / 2m bars** | **Not in HQ enum.** 003 and 006 are resample hypotheses. 004’s 1m **is** native. 011’s 2h parent is not. |
| **007 vs 009** | Two speaker clocks. 007: 10:00–14:30 / ban 15:00. 009: skip 09:15–09:45 / flatten **15:15**. **014 Monday 09:45** fights 009. Do not merge. |
| **15:15 vs 15:40** | 15:15 = CAS CTS end + 003/009 flatten heuristic. **15:40 = F&O VERIFY.** CAS 15:15–15:35 = cash **equilibrium**, not F&O close. Do not hardcode 15:30 for all products. |
| **3m chain before CONFIRMED** | **Required** when the ticket **picks a strike** (002, 005, 006, and 013/014 if selling opens) or after **MACRO_EVENT**. **Not** required for 001/003/004/007/008/009/010/012 **math objects**. Desk still polls 3m globally. **006** cannot treat 3m chain as a 2m confirm. |
| **SENSEX** | Always **BSE**. Never NIFTY lot/step/expiry/chain client. |

---

## UNKNOWN / blockers (unchanged + this pass)

- Official lot circular PDF not stored.
- Official F&O 15:40 circular (NSE/FAOP/74467) not stored.
- BSE SENSEX strike interval / tick: not extracted.
- Historical option quotes: endpoint documented ([`ROLLING_OPTION.md`](ROLLING_OPTION.md) `POST /charts/rollingoption`, 5y / 30d/call). **Ingested bars in this repo still `DATA_INSUFFICIENT`.** Rolling ATM is a spot-relative **bucket**, not a proven locked-contract hold.
- DEXT / HQ order-flow history (010): `DATA_INSUFFICIENT`.
- Super Scalper EMA lengths (004): `DATA_INSUFFICIENT`.
- Whether quote JSON includes `oi` for ATM±N 1m path: **VERIFY FROM DOCS**.

**No fills invented. No lots frozen. Not `RESEARCH_READY_FOR_PROGRAMMING`.**
