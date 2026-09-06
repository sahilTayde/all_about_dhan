# ENGINE_MIX.md — Phase-1 index-options mix (14 IDs only)

**Team:** 04_quant (strategy architect)  
**Date:** 2026-09-03  
**Book:** NIFTY / BANKNIFTY / SENSEX index options, CE/PE **buy first**  
**Consumers (later):** 06_backtesting (fixtures), 05_analysis (desk overlay), 09_review (notes ≠ pass)  
**YAML shape:** [`ALGO_HANDOFF.md`](ALGO_HANDOFF.md)  
**Staging:** [`SIGNAL_STAGING.md`](SIGNAL_STAGING.md) (5m confirm-or-kill = **`PROJECT_MIX`**, desk — not a video entry)  
**Candidates:** [`candidates/STRAT-001.md`](candidates/STRAT-001.md) … [`STRAT-014.md`](candidates/STRAT-014.md)  
**Transcript bind (SOURCE_FACT, English wins):** [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)  
**Teacher MIX clubs (01 tape):** [`TRANSCRIPT_ANALYST.md`](../../01_research/docs/handoffs/TRANSCRIPT_ANALYST.md) — DHAN-DERIVED vs PROJECT_MIX.  
**02 first option-premium charter:** `MIX-GOKUL-003-009` = 003 + **009 only** (no 007, no 008). [`MIX_CATALOG.md`](MIX_CATALOG.md) / `MIX-ABL-CLOCKS` arm A. Customer default remains `MIX-DEFAULT-BUY` (`PROJECT_MIX`). Do not promote.  
**KEEP_ALL catalog (STRAT + MIX-*):** [`MIX_CATALOG.md`](MIX_CATALOG.md) — `WAITING`/`PARKED` = not default ticket, **not deleted**. No `STRAT-015+`.

---

## Transcript bind (01, English)

**Authority:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md). English `normalized_en/` **wins** if a STRAT, this mix, or a Hindi packet disagrees. Bind tags: `CONFIRMED` | `CONFLICT` | `WEAK` | `NOT_IN_EN` | **`PROJECT_MIX`**. `PROJECT_MIX` is **not** `DHAN-DERIVED`. No video taught the club as one recipe.

**Guests (affiliation only — education ≠ edge):**

| Speaker | Video | Spoken affiliation (EN) | What it is not |
|---------|-------|-------------------------|----------------|
| Dr. Gokul Chhabra / Gokul Jhabra | `2RnBT9DDDNI` 01:57–02:50 | Host: **SEBI registered Research Analyst** / “Also SEBI registered. Practicing” | Not VALIDATION. Not a reason to code 003. Not a win rate. |
| Himanshu Arora | `HAUSZx-hYdY` 00:54–01:02 | Host: **“Star Trader of this Dhan Platform”** | **Not** spoken as SEBI RA in this EN file. “SEBI regulation has come” (~16:27) is expiry-calendar talk, not his registration. |
| Mukul Choudhary | `pvmvkiS1cx4` 00:02–00:04 | Self-intro host | No RA claim in the open. |

**Same-video Gokul stack (not PROJECT_MIX):** 003 + 004 + 005 + 008 + 009 is **one class** (`2RnBT9DDDNI` EN). Splitting IDs is bookkeeping. Origin: **`DHAN-DERIVED`**.

**What no video taught as one system (`PROJECT_MIX` — keep labeled):**

| Mix claim | Bind | Do not |
|-----------|------|--------|
| Default ticket **003 + 007 + 009 AND** (no new 09:15–**10:00**, no new after **14:30**, flatten **15:15**) | **`PROJECT_MIX`** — two speakers. Gokul starts **09:45** + flatten 15:15. Himanshu new entries after **10:00**, mostly not after **14:30**. Intersection is stricter than either. | Cite one timestamp as if both agreed. Relabel DHAN-DERIVED. |
| **5m MACD / Supertrend confirm-or-kill** ([`SIGNAL_STAGING.md`](SIGNAL_STAGING.md)) | **`PROJECT_MIX`** (desk). HAUS uses child 5m/10m **MACD as entry** (buy that candle’s high). Gokul entry is **3m** all-three, not 5m MACD. | Average with HAUS entry. Backfill a fake Gokul/HAUS stamp. |
| Named “Dhan book” = 003+007+009+staging 5m ST/MACD+005 | **`PROJECT_MIX`** | Call it a transcript theorem |
| **002 overlay on 003** | **`CONFLICT`** — Gokul: OTM **not recommended**. 002 is HAUS slightly-OTM. | Ever attach 002 to a 003 ticket |
| **011** as index-option reversal primary | **`PROJECT_MIX`**. `H_6kee` = stocks + gold/silver. **`gA5` executed a bull put (sell / 013)** — do not map that fill to buy CE. | Say Dhan taught NIFTY option **buys** this way |
| **012** as 001/003 pattern gate | **`PROJECT_MIX`**. Patterns named on stock charts. | Claim spoken “filter Gokul/HAUS” |
| **010** OF agrees-with-003 | **`PROJECT_MIX`** + HQ history `DATA_INSUFFICIENT` | Un-park as if DzT taught 003 |

**Other bind facts this mix must not freeze:**

- **004** Super Scalper fast/slow **lengths:** `NOT_IN_EN` / **`UNKNOWN`**. Do not invent 9/21. Parked.
- **Supertrend 10, 3** on 003: 2Rn said setting of **“103”** (`WEAK` / `[UNCERTAIN_TRANSCRIPT]`). **Not** a frozen spoken “ten comma three.” `H_6kee` quiz answer **“10 3”** is CONFIRMED on **stock/gold**, not this futures recipe. Index compute 10,3 is **inference** + 02 later.
- **001** spoken universe = **NIFTY 100 stocks** (+ options application). Phase-1 `market: [NIFTY, BANKNIFTY, SENSEX]` index book = **`PROJECT_MIX`**. HAUS **2h parent** = `NOT_IN_EN` (15m child alt **is** spoken).
- **013 / 014** stay **WAITING sell**. EN confirms. Not buy UI.

---

## 1. Honesty banner

```text
layer:                  HYPOTHESIS
status:                 UNVALIDATED
research_ready_for_programming: false
gate:                   09 five-pass has NOT passed. Notes ≠ pass.
metrics:                win_rate=null  expectancy=null  profit_factor=null  max_drawdown=null
profitability:          NOT CLAIMED
ids:                    STRAT-001 … STRAT-014 only. No STRAT-015+.
fills / dhan quotes:    NOT INVENTED
empty DHAN_*:           does not block this spec (fixtures later)
```

This file is the **founder playbook** for how the existing 14 DRAFT IDs attach to three **engine** regimes. It is **not** a live book. It is **not** a customer catalog. Do not implement in `apps/` or `packages/`.

Education ≠ edge. Coalition packets (`OPTIONS_INDEX` Layer C, `TA_STRUCTURE`) are `SOURCE_FACT` pointers. Math/market files are `VALIDATION`. This mix is `HYPOTHESIS`.

---

## 2. How we club (not soup)

**One live ticket = one primary + attached filters + confirm/kill + optional overlay.**

Never stack 001 + 003 + 006 + 011 as “more confirmation.” That is indicator soup. If two primaries fire the same bar, **do not merge** — pick the pre-declared book (default **003**) or stay WATCH / VETOED.

| Layer | What it is | What it is not |
|-------|------------|----------------|
| **Primary** | The one rule that names direction (CE or PE lean) | A committee of YouTube overlays |
| **Filter** | Clock / mixed-index / open-skip that can **forbid** a new ticket | An edge |
| **Confirm / kill** | 5m Supertrend + 5m MACD **promote or kill** — **`PROJECT_MIX`** ([`SIGNAL_STAGING.md`](SIGNAL_STAGING.md)) | Entry. Not HAUS child-TF buy-the-high (conflict §4) |
| **Overlay** | Strike pick **or** candle/S/R **or** news veto | A second primary |
| **WAITING** / **PARKED** | Still `BACKTEST_BOOK` ([`MIX_CATALOG.md`](MIX_CATALOG.md)). Not the customer default ticket | Deleted / vetoed teacher recipe |

**Customer UI (`/`):** staged lean only — `WATCH → EARLY → CONFIRMED → IN-PROGRESS` (plus `EXPIRED` / `VETOED`). Direction chip + honesty copy. **No** MACD/RSI/Supertrend/EMA names. **No** STRAT IDs. EARLY ≠ fill.

**Internal `/desk`:** indicator names, STRAT IDs, origin tags, conflict flags.

Persona: [`PERSONA.md`](../../00_orchestrator/docs/PERSONA.md) (inventory / tape vs index). Operator checklist: [`PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md) (news + chain + opening drive). Overlay **vetoes**; it does not license lag-only entries.

---

## 3. Three regime books (engine only)

Default Phase-1 **buy** ticket uses **STRAT-003** as primary. Alt primaries are **separate books** — never on the same ticket.

Origin tags do not collapse. `DHAN-DERIVED` = speaker on enabled `@DhanHQ` (same-video Gokul stack is this). `PROJECT_MIX` / `PROJECT-DERIVED` = we transferred or mixed two speakers — **not** a transcript theorem. English bind: [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md).

### 3.1 BULL — long CE

**Testable hypothesis:** a CE lean exists only while the **003** futures stack is all-three bullish (or an *alt* primary is selected for a separate test ID), filters do not forbid, and 5m ST/MACD do not contradict.

| ID | Role | Origin | Origin video | Phase-1 default ticket? |
|----|------|--------|--------------|-------------------------|
| **STRAT-003** | **primary** | DHAN-DERIVED (same-video Gokul stack) | `2RnBT9DDDNI` EN 20:57–40:56 (3m futures CONFIRMED; all-three call/put CONFIRMED). ST digits **“103” WEAK** — not spoken “ten comma three” | **YES — default** |
| STRAT-001 | **primary** (alt book, not same ticket) | DHAN-DERIVED recipe; index-only book **`PROJECT_MIX`** | `HAUSZx-hYdY` 41:32–01:03:10 (hourly + 5/10m CONFIRMED; **15m child alt spoken; 2h parent NOT_IN_EN**). Spoken universe **NIFTY 100 stocks** | no — ablation `BULL_ALT_001` |
| STRAT-011 | **primary** (reversal alt; only if 003/001 trend book is **not** firing) | **`PROJECT_MIX`** | `H_6keeRUCDM` stocks/gold (ST 10,3 CONFIRMED there). `gA5FtEnSABM` NIFTY view then **executed bull put sell** — do **not** map that fill to buy CE | no — ablation `BULL_ALT_011` |
| STRAT-006 | **primary** (scalp alt) | DHAN-DERIVED | `pvmvkiS1cx4` (2m EMA 10/20 + ITM 100–200 CONFIRMED). Beginner caution is **VIX > 15–16**, not a blanket ban (WEAK vs old STRAT line). Delta **WEAK** | no — ablation `BULL_ALT_006` |
| STRAT-007 | **filter** | DHAN-DERIVED (Himanshu only) | `HAUSZx-hYdY` 55:18–55:42, 01:00:22–01:00:35 | YES as **its own** clock. **AND with 009 = `PROJECT_MIX`** |
| STRAT-008 | **filter** (veto if mixed) | DHAN-DERIVED (Gokul same-video) | `2RnBT9DDDNI` 01:08:37–01:11:19 | YES — Phase-1 default = **no-trade** on mixed |
| STRAT-009 | **filter** | DHAN-DERIVED (Gokul same-video) | `2RnBT9DDDNI` 23:48–24:06 (ignore 09:15–09:45; start 09:45; flatten before 15:15) | YES as **its own** clock |
| STRAT-004 | **confirm** | DHAN-DERIVED structure (same-video with 003); lengths **`NOT_IN_EN`** | `2RnBT9DDDNI` 46:59–55:15. Fast/slow EMA **UNKNOWN**. Do not invent 9/21. AND with 003 all-three is **this video**, not HAUS MACD | **parked** until chart-export VERIFY |
| *staging 5m ST/MACD* | **confirm / kill** | **`PROJECT_MIX`** (desk, not a transcript theorem) | [`SIGNAL_STAGING.md`](SIGNAL_STAGING.md). Not HAUS entry. 2Rn ST = **“103” WEAK** | YES — promotion gate on the named mix; keep labeled PROJECT_MIX |
| **STRAT-005** | **overlay** (strike) | DHAN-DERIVED (same-video Gokul) | `2RnBT9DDDNI` 38:06–39:20 (ITM/max ATM CONFIRMED; OTM not recommended). Delta band **WEAK** | **YES with 003-primary** |
| STRAT-002 | **overlay** (strike) | DHAN-DERIVED (HAUS only) | `HAUSZx-hYdY` 57:40–01:02:19 | **Never on 003.** `BULL_ALT_001` only. CONFLICT if overlaid on 003 |
| STRAT-012 | **overlay** (optional confluence) | **`PROJECT_MIX`** on 001/003 | `njqeZc_tYy8`: five named (hammer CONFIRMED; engulfing / morning star / dark cloud / inside bar **named in EN**; rule-detail `WAITING`). `wDZXqzdGBDc` tool | optional — WAITING is **detail**, not existence |
| STRAT-010 | **overlay** | DHAN-DERIVED tool + **`PROJECT_MIX`** gate-on-003 | `YUXJv_xBStw`, `DzT_681GThA` (volume-delta ≠ Greek delta). No 003-filter recipe spoken | **PARKED** `DATA_INSUFFICIENT` |
| STRAT-013 | **WAITING** (not buy default) | DHAN-DERIVED | `gA5FtEnSABM` (bull put **credit**) | **KEEP_ALL** `BACKTEST_BOOK` — `MIX-SELL-013`. Not deleted |
| STRAT-014 | **WAITING** (not buy default) | DHAN-DERIVED | `6el9Jqnrdz8` 41:29–46:35 (1-3-2 call ratio **sell**) | **KEEP_ALL** `BACKTEST_BOOK` — `MIX-SELL-014`. Not deleted |

**Default BULL ticket (named mix):** `003 primary + 007/008/009 filters + staging 5m ST/MACD confirm-or-kill + 005 strike + optional 012`. **This AND is `PROJECT_MIX`** (Gokul same-video 003/005/008/009 + Himanshu 007 + desk staging). News veto from 05 (not a STRAT). **002 never overlays 003.**

**Strike pairing rule (do not soup):** overlay strike follows the **primary’s video**. 003 → 005. 001 → 002. 006 → 006’s own ITM 100–200 (delta **WEAK**). Never 002+005 on one ticket. Never 002 on 003.

### 3.2 BEAR — long PE

**Testable hypothesis:** mirror of BULL. PE lean while 003 all-three bearish (close < VWAP **and** VWMA **and** ST — `2RnBT9` 25:13–25:53), filters clean, 5m ST/MACD do not contradict CE.

| ID | Role (BEAR) | Notes |
|----|-------------|-------|
| STRAT-003 | **primary** (default) | put_if: close < all three |
| STRAT-001 | **primary** (alt) | invert: MACD hist < 0 and MA 10 < 30 < 100; buy PE. Index book **`PROJECT_MIX`** vs spoken NIFTY 100 |
| STRAT-011 | **primary** (reversal alt) | **`PROJECT_MIX`**. Do **not** map gA5 bull-put fill to PE-buy |
| STRAT-006 | **primary** (scalp alt) | EMA 10/20 down; ITM PE. Beginner caution **VIX > 15–16**, not blanket |
| STRAT-007 / 008 / 009 | **filter** | 008/009 Gokul same-video. 007 Himanshu. **007∧009 = `PROJECT_MIX`** |
| STRAT-004 | **confirm** | parked; lengths `NOT_IN_EN` / `UNKNOWN` |
| staging 5m ST/MACD | **confirm / kill** | **`PROJECT_MIX`**. PE promotion; if ST and MACD **contradict**, stay EARLY or VETOED |
| STRAT-005 | **overlay** strike with 003 | put delta = negative of high-delta band (**WEAK** digits) |
| STRAT-002 | **overlay** strike with 001-alt **only** | **Never 003.** 1–2 OTM PE; 20–30% premium |
| STRAT-012 | **overlay** optional | **`PROJECT_MIX`**. Dark-cloud / resistance for PE; hammer at support is **CE**. Four patterns **named in EN**; rule-detail WAITING |
| STRAT-010 | **overlay** PARKED | `DATA_INSUFFICIENT` |
| STRAT-013 / 014 | **WAITING** | sell structures — **not** PE-buy |

**Default BEAR ticket:** same composition as BULL, PE-mirrored. **`PROJECT_MIX`** AND. **002 never overlays 003.**

### 3.3 SIDEWAYS / NO-TRADE

**Testable hypothesis:** the product’s honest output on chop is **no new CE/PE lean**, not a credit spread and not a “small scalp.” Customer sees idle / WATCH decay / VETOED — never a faked CONFIRMED.

| ID | Role | What fires NO-TRADE |
|----|------|---------------------|
| STRAT-003 | **filter** (skip rule of the primary) | Supertrend direction **≠** VWAP side (`2RnBT9` 34:54–36:01). Spoken “70/30” is **SOURCE_FACT anecdote**, not a metric |
| STRAT-008 | **filter** | NIFTY vs BANKNIFTY vs SENSEX leans disagree → **no new trades** that session (Phase-1 default). Dominant-only sizing is a **later** size test, not this mix |
| STRAT-009 | **filter** | 09:15–09:45 no new; flatten before 15:15. Always on |
| STRAT-007 | **filter** | Outside 10:00–14:30: no new entries. **AND with 009 is `PROJECT_MIX`** (two speakers; §4) |
| *news / MACRO_EVENT* | **VETO** (05 overlay, not a STRAT) | Scheduled print ±60m or RISK_OFF vs CE spray — [`PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md). News is **veto / no-trade**, not alpha |
| *extreme PCR-only* | **VETO** | PCR without strike-level Δ vs last 3m snapshot is **not** a primary ([`PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md)) |
| STRAT-001 / 006 / 011 | **WAITING** in this regime | Do not “pick a scalp because trend failed” |
| STRAT-010 | PARKED | would not rescue chop without history |
| STRAT-012 | **overlay** | repeated VWAP crosses / no confluence → do not promote |
| STRAT-013 | **WAITING** | bull put credit = sideways-to-up **sell** — not Phase-1 buy |
| STRAT-014 | **WAITING** | hedged call ratio = sideways **sell** — not Phase-1 buy |

No primary fires a buy ticket in SIDEWAYS. 013/014 stay on the book as **corpus** so 09 can see we did not “forget selling.” They do **not** attach to the customer CE/PE buy UI.

---

## 4. Explicit conflicts (do not paper over)

| Conflict | A | B | C (if any) | Phase-1 mix rule | Ablation |
|----------|---|---|------------|------------------|----------|
| **Strike** | **002** slightly OTM (`HAUSZx`) | **005** ITM/max ATM; OTM **not** recommended (`2RnBT9`) | **006** ITM 100–200; delta **WEAK** | **002 never overlays 003** (`CONFLICT`). Default 003-ticket uses **005 only** | Three mutually exclusive overlays |
| **MACD role** | **001** HAUS: child MACD **is the entry filter** | [`SIGNAL_STAGING.md`](SIGNAL_STAGING.md): 5m MACD = **confirm or kill** | — | Staging path is **`PROJECT_MIX`** (desk). Do not call it HAUS | `H-001-HAUS-ENTRY` vs `H-STAGING-CONFIRM` — two IDs |
| **003 TF vs HQ** | Spoken **3m** FUTIDX (`2RnBT9`) CONFIRMED | HQ enum **{1, 5, 15, 25, 60}**; live **interval 5** works on **IDX_I INDEX** | — | Paper path = **5m INDEX**, tagged **`PROJECT`** — **not** frozen as Gokul. 003 recipe stays 3m FUTIDX (KEEP_ALL). See [`ALGO_HANDOFF.md`](ALGO_HANDOFF.md) | 3m FUTIDX vs 5m INDEX — two constructions |
| **Supertrend params** | 2Rn **“103” WEAK** — not spoken “ten comma three.” `H_6kee` “10 3” CONFIRMED on **stock/gold** | `_byuht38r5s` “7 is 3” equity `[UNCERTAIN]` | — | Index 10,3 = **inference**, not a frozen 2Rn quote. **7, 3 not imported** | 7,3 stays EQ backlog |
| **013 / 014 sell** | Credit / ratio **sell** (`gA5`, `6el9`) | Phase-1 product = CE/PE **buy first** | `_exmJYgFwFA` sell corpus | **WAITING.** Not in the buy mix. Do not convert a bull-put into a CE ticket | Selling book = later charter, other IDs stay 013/014 |

**Clocks:** 007 (Himanshu) vs 009 (Gokul, start **09:45**) vs F&O **15:40**. Phase-1 **AND** (no new 09:15–**10:00**, no new after **14:30**, flatten **15:15**) is **`PROJECT_MIX`**. Conservative intersection, **not** a claim that speakers agreed. Do not cite one timestamp for the AND.

**MACD scale (do not freeze):** HAUS ×3 or ×4 `[UNCERTAIN]`; `6E_K1wVkHyw` 24/52 is a **different** recipe; Appel 12/26/9 is VALIDATION default. Grid already on STRAT-001. Staging confirm uses **one named** 12/26/9 compute until 02 signs otherwise.

**MA 100 vs 300 / 9 vs 10:** HAUS `[UNCERTAIN_TRANSCRIPT]` — search range on 001-alt, not a silent correction.

**004 Super Scalper lengths:** `NOT_IN_EN` / `UNKNOWN`. Do not invent 9/21.

---

## 5. Staged mapping (BULL and BEAR)

EARLY ≠ fill. ~1 minute lead is a **product target**, not an SLA. 5m Supertrend / MACD **confirm or kill** is **`PROJECT_MIX`** (desk) — not HAUS entry.

Ingredients below are **named**. Leading mix can fire WATCH/EARLY **without** waiting on the lagging stack ([`SIGNAL_STAGING.md`](SIGNAL_STAGING.md) mix-and-match).

### 5.1 BULL (CE lean)

| Stage | Ingredients that may fire it | Forbidden |
|-------|------------------------------|-----------|
| **WATCH** | (L1) first impulsive **1m** green on **futures** OHLC; (L2) range break of a **named** box (prior session H/L, or 009 open box after 09:45 — T is a search set, not frozen); (L3) chain **3m** CE OI buildup **or** PE writing vs **last snapshot** (not PCR-only); (L4) 003 close crossing VWAP+VWMA but ST not yet with; (L5) 001 **1h parent** MACD hist>0 **and** MA stack bullish (WATCH only); (L6) 011 RSI divergence printing (reversal-alt book only) | Idle→CONFIRMED skip. Indicator names on customer UI. 013/014 |
| **EARLY** | ≥2 independent **leading** ingredients agree **CE**; 007/009 clocks pass; 008 not mixed; no `MACRO_EVENT` undigested; honesty copy can be shown. 003 all-three just aligned on last **closed** bar **without** 5m ST/MACD agreement still counts as leading, not CONFIRMED | Fill language. Green EARLY. HAUS “buy the 5m high” as if CONFIRMED. 1m omniscience |
| **CONFIRMED** | After EARLY stamp: **5m Supertrend flip** and/or **5m MACD** in CE direction, and the other **does not contradict**. PERSONA_DESK CE checklist (event, headline, opening drive, ATM±N, walls). 004 only if lengths known | Promote on ST **or** MACD **alone while the other contradicts**. Using 5m ST/MACD as **entry** (first reason a side appears). CONFIRMED-late after a spent impulse → prefer **EXPIRED** for new risk |
| **VETOED** | News / `MACRO_EVENT`; RISK_OFF vs CE spray; 008 mixed indices; 003 ST vs VWAP disagree; circuit/halt; chain vs headline contradiction; fake-breakdown reclaim (PERSONA_DESK) | Treating veto as “wait for MACD to catch up” |

**IN-PROGRESS** after CONFIRMED if user took or shadow paper is open — staging file, not a new STRAT.

### 5.2 BEAR (PE lean)

Mirror of §5.1: impulsive **red** 1m; PE OI with spot failing (or CE writing into a wall); 003 all-three bearish; 001 1h parent bearish as WATCH; 5m ST/MACD **PE** confirm-or-kill; RISK_ON + PE spray is a tape-vs-headline veto until one side yields.

The missed-PE postmortem was **lagging-only** — it never earned EARLY. This mix **requires** a leading pair before 5m ST/MACD may promote.

### 5.3 SIDEWAYS mapping

| Stage | What the customer may see |
|-------|---------------------------|
| WATCH | Ingredients mixing, then decay (VWAP cross, mixed 008, open noise) |
| EARLY | **Should not fire** while 003 skip or 008 mixed or news veto holds |
| CONFIRMED | **Does not fire** in this regime |
| VETOED | Default honest output when overlay kills a forming CE/PE lean |

---

## 6. YAML mix objects (ALGO_HANDOFF field names)

One block per regime. Shared instrument/cost/status keys match [`ALGO_HANDOFF.md`](ALGO_HANDOFF.md). `role` here is the **mix composition** (lists of existing IDs). Metrics stay **null**.

Unknown → `UNKNOWN` or `DATA_INSUFFICIENT`. Do not guess Super Scalper lengths, 3m as an HQ `interval`, or OF history.

### 6.1 BULL

```yaml
mix_id: PHASE1_BULL
name: bull_long_ce
strategy_id: MIX-BULL          # not STRAT-015; composition of 001–014
origin:                        # mixed — do not collapse
  - DHAN-DERIVED               # Gokul same-video 003/004/005/008/009
  - PROJECT_MIX                # 003+007+009 AND; 5m MACD confirm-or-kill; 001 index book; 011/012
origin_videos:
  - {video_id: 2RnBT9DDDNI, ts: "20:57-40:56", qa_flag: UNCERTAIN_TRANSCRIPT}   # 003 primary
  - {video_id: 2RnBT9DDDNI, ts: "38:06-39:20", qa_flag: null}                   # 005 strike
  - {video_id: 2RnBT9DDDNI, ts: "23:48-24:03", qa_flag: null}                   # 009
  - {video_id: 2RnBT9DDDNI, ts: "01:08:37-01:11:19", qa_flag: null}             # 008
  - {video_id: HAUSZx-hYdY, ts: "55:18-55:42", qa_flag: UNCERTAIN_TRANSCRIPT}  # 007
  - {video_id: HAUSZx-hYdY, ts: "41:32-01:03:10", qa_flag: UNCERTAIN_TRANSCRIPT}  # 001 alt only
book: INDEX_OPTIONS
market: [NIFTY, BANKNIFTY, SENSEX]
instrument:
  type: INDEX_OPTION
  side: BUY
  exchange: FROM_CONTRACT      # SENSEX = BSE
lot_size: FROM_INSTRUMENT_MASTER
expiry: FROM_CONTRACT
session_tz: Asia/Kolkata

regime:
  bull: true
  bear: false
  sideways: skip

role:
  primary: [STRAT-003]
  primary_alt_not_same_ticket: [STRAT-001, STRAT-011, STRAT-006]
  filter: [STRAT-007, STRAT-008, STRAT-009]
  confirm: [STAGING_5M_ST_MACD]     # PROJECT_MIX desk; not HAUS entry; not a STRAT ID
  confirm_parked: [STRAT-004]       # NOT_IN_EN lengths UNKNOWN
  overlay: [STRAT-005]              # strike with 003; 002 NEVER on this ticket (CONFLICT)
  overlay_optional: [STRAT-012]
  overlay_parked: [STRAT-010]       # DATA_INSUFFICIENT OF history
  WAITING: [STRAT-013, STRAT-014]

timeframe:
  signal: 5m                       # HQ-native confirm path
  confirm: 5m                      # lagging stack = confirm or kill, not entry
  hq_intervals: [1, 5, 15, 25, 60]
  resample_hypothesis: 3m          # STRAT-003 spoken; not an HQ interval
  leading: 1m                      # impulsive candle; not omniscience

indicators:
  - name: VWAP
    surface: OHLC_COMPUTE
    spoken: {session: default, tape: FUTURES}
    hq_trigger: []
    series_api: false
  - name: VWMA
    surface: OHLC_COMPUTE
    spoken: {length: 20}
    hq_trigger: []
    series_api: false
  - name: Supertrend
    surface: OHLC_COMPUTE
    spoken: {raw: "103", bind: WEAK, inferred_atr: 10, inferred_multiplier: 3}  # not spoken "ten comma three"
    hq_trigger: []                 # not annexure; 7,3 NOT imported
    series_api: false
  - name: MACD
    surface: OHLC_COMPUTE
    spoken: {fast: 12, slow: 26, signal: 9}   # staging confirm; HAUS ×3/×4 is 001-alt grid
    hq_trigger: [MACD_12, MACD_26, MACD_HIST]
    series_api: false

data:
  ohlc: FUTURES                    # never CASH_INDEX volume
  chain: true                      # POST /optionchain; poll 3m
  news: true                       # veto / no-trade, not alpha
  cas: false                       # F&O clock ≠ CAS cash names
  order_flow: false                # STRAT-010 DATA_INSUFFICIENT

costs:
  include: [brokerage, statutory, half_spread]
  fill: next_bar_open_or_conservative_ask
  look_ahead: forbidden

invalidation:
  - "expectancy <= 0 after costs in two regimes (trend and chop)"
  - "required history DATA_INSUFFICIENT"
  - "cash-index VWAP used"
  - "002 and 005 attached on the same ticket (strike soup)"

status: UNVALIDATED
research_ready_for_programming: false
metrics:
  win_rate: null
  expectancy: null
  profit_factor: null
  max_drawdown: null
```

### 6.2 BEAR

```yaml
mix_id: PHASE1_BEAR
name: bear_long_pe
strategy_id: MIX-BEAR
origin:
  - DHAN-DERIVED               # Gokul same-video
  - PROJECT_MIX                # 007∧009 clocks; staging 5m confirm-or-kill
  - {video_id: 2RnBT9DDDNI, ts: "38:06-39:20", qa_flag: UNCERTAIN_TRANSCRIPT}
  - {video_id: HAUSZx-hYdY, ts: "41:32-01:03:10", qa_flag: UNCERTAIN_TRANSCRIPT}  # 001 alt PE
book: INDEX_OPTIONS
market: [NIFTY, BANKNIFTY, SENSEX]
instrument:
  type: INDEX_OPTION
  side: BUY
  exchange: FROM_CONTRACT
lot_size: FROM_INSTRUMENT_MASTER
expiry: FROM_CONTRACT
session_tz: Asia/Kolkata

regime:
  bull: false
  bear: true
  sideways: skip

role:
  primary: [STRAT-003]
  primary_alt_not_same_ticket: [STRAT-001, STRAT-011, STRAT-006]
  filter: [STRAT-007, STRAT-008, STRAT-009]
  confirm: [STAGING_5M_ST_MACD]
  confirm_parked: [STRAT-004]
  overlay: [STRAT-005]
  overlay_optional: [STRAT-012]
  overlay_parked: [STRAT-010]
  WAITING: [STRAT-013, STRAT-014]

timeframe:
  signal: 5m
  confirm: 5m
  hq_intervals: [1, 5, 15, 25, 60]
  resample_hypothesis: 3m
  leading: 1m

indicators:
  - name: VWAP
    surface: OHLC_COMPUTE
    spoken: {session: default, tape: FUTURES}
    hq_trigger: []
    series_api: false
  - name: VWMA
    surface: OHLC_COMPUTE
    spoken: {length: 20}
    hq_trigger: []
    series_api: false
  - name: Supertrend
    surface: OHLC_COMPUTE
    spoken: {raw: "103", bind: WEAK, inferred_atr: 10, inferred_multiplier: 3}  # not spoken "ten comma three"
    hq_trigger: []
    series_api: false
  - name: MACD
    surface: OHLC_COMPUTE
    spoken: {fast: 12, slow: 26, signal: 9}
    hq_trigger: [MACD_12, MACD_26, MACD_HIST]
    series_api: false

data:
  ohlc: FUTURES
  chain: true
  news: true
  cas: false
  order_flow: false

costs:
  include: [brokerage, statutory, half_spread]
  fill: next_bar_open_or_conservative_ask
  look_ahead: forbidden

invalidation:
  - "expectancy <= 0 after costs in two regimes"
  - "required history DATA_INSUFFICIENT"
  - "lagging-only PE (no leading pair) promoted to CONFIRMED"

status: UNVALIDATED
research_ready_for_programming: false
metrics:
  win_rate: null
  expectancy: null
  profit_factor: null
  max_drawdown: null
```

### 6.3 SIDEWAYS / NO-TRADE

```yaml
mix_id: PHASE1_SIDEWAYS
name: sideways_no_trade
strategy_id: MIX-SIDEWAYS
origin:
  - DHAN-DERIVED
  - PROJECT_MIX                # news veto path (05); 007∧009 if attached
origin_videos:
  - {video_id: 2RnBT9DDDNI, ts: "34:54-36:01", qa_flag: UNCERTAIN_TRANSCRIPT}  # ST vs VWAP skip
  - {video_id: 2RnBT9DDDNI, ts: "01:08:37-01:11:19", qa_flag: null}            # mixed index
  - {video_id: 2RnBT9DDDNI, ts: "23:48-24:03", qa_flag: null}                  # 009
  - {video_id: gA5FtEnSABM, ts: "07:30-10:00", qa_flag: UNCERTAIN_TRANSCRIPT}  # 013 WAITING
  - {video_id: 6el9Jqnrdz8, ts: "41:29-46:35", qa_flag: UNCERTAIN_TRANSCRIPT}  # 014 WAITING
book: INDEX_OPTIONS
market: [NIFTY, BANKNIFTY, SENSEX]
instrument:
  type: INDEX_OPTION
  side: BUY                    # product remains buy-first; this regime does not fire a ticket
  exchange: FROM_CONTRACT
lot_size: FROM_INSTRUMENT_MASTER
expiry: FROM_CONTRACT
session_tz: Asia/Kolkata

regime:
  bull: false
  bear: false
  sideways: skip               # trade | skip | credit_WAITING → skip for Phase-1 buy

role:
  primary: []                  # no buy primary in this regime
  filter: [STRAT-003, STRAT-008, STRAT-009, STRAT-007]
  confirm: []
  overlay: []
  overlay_parked: [STRAT-010]
  WAITING: [STRAT-013, STRAT-014, STRAT-001, STRAT-006, STRAT-011]

timeframe:
  signal: 5m
  confirm: 5m
  hq_intervals: [1, 5, 15, 25, 60]
  resample_hypothesis: 3m

indicators:
  - name: VWAP
    surface: OHLC_COMPUTE
    spoken: {tape: FUTURES}
    hq_trigger: []
    series_api: false
  - name: Supertrend
    surface: OHLC_COMPUTE
    spoken: {raw: "103", bind: WEAK, inferred_atr: 10, inferred_multiplier: 3}  # not spoken "ten comma three"
    hq_trigger: []
    series_api: false

data:
  ohlc: FUTURES
  chain: true
  news: true                   # veto
  cas: false
  order_flow: false

costs:
  include: [brokerage, statutory, half_spread]
  fill: next_bar_open_or_conservative_ask
  look_ahead: forbidden

invalidation:
  - "a CE/PE CONFIRMED fires while ST vs VWAP disagree"
  - "013/014 coded as buy tickets"
  - "mixed 008 ignored and both sides sized up"

status: UNVALIDATED
research_ready_for_programming: false
metrics:
  win_rate: null
  expectancy: null
  profit_factor: null
  max_drawdown: null
```

---

## 7. Comments FROM 04 TO 02, 03, 05, 09

Sign or **reject**. Do not polite-pass. Silence ≠ pass.

### TO 02_phd_math (`VALIDATION`)

**Need you to sign or reject:**

1. Computing Supertrend from **FUTIDX** OHLC: 2Rn digits are **“103” WEAK**, not spoken “ten comma three.” `H_6kee` “10 3” is stock/gold. Index 10,3 is **inference** — `supported` as TV convention, **not** an HQ field and **not** a frozen 2Rn quote. Chart mismatch → `partially_supported`, do not silent-swap.
2. **7, 3 from `_byuht38r5s` is not imported.** Confirm that as `SOURCE_UNCERTAIN` / equity-only.
3. Staging confirm MACD = Appel **12/26/9** compute from futures close. HAUS ×3/×4 and 6E 24/52 stay **separate** grids on 001-alt — not one “Dhan MACD.”
4. Session VWAP + VWMA(20) on **futures** tape = `supported` math. Cash-index VWAP = `unsupported`.
5. **3m / 2m resample** method (`UNKNOWN` in your open list). Propose one construction for 06 (e.g. 1m→3m OHLC) or reject 003 until native 5m only.
6. Super Scalper fast/slow lengths remain `NOT_IN_EN` / `UNKNOWN` — **004 stays parked**. Do not invent 9/21.
7. Greek **delta** (005/006) vs volume-delta (010): keep symbols distinct.

Reject this mix if you will not own the compute path (no series REST).

### TO 03_phd_market (`VALIDATION`)

**Need you to sign or reject:**

1. `ohlc: FUTURES` + `vwap_tape: FUTURES_OR_OPTION` + SENSEX **BSE** — already your notes. Sign that this mix does not reintroduce cash-index volume.
2. Flatten **15:15** (009 spoken) vs equity derivatives **15:40** (VERIFY). Phase-1 uses spoken 15:15 as **filter**, not as exchange close. Parameterize `close_model`; do not hardcode one clock.
3. Clock **AND** of 007 (10:00–14:30) and 009 (Gokul **starts 09:45**): intersection starts **10:00**. This AND is **`PROJECT_MIX`**. Sign or demand video-specific books instead of AND.
4. Strike conflict **002 vs 005 vs 006** stays three tests. Comment on liquidity / 50-multiple NIFTY / BANKNIFTY monthly-only as **market** constraints, not as a merged strike.
5. `expiry: FROM_CONTRACT` — do not freeze HAUS Thursday or 6el9 Tuesday into this mix.
6. Chain poll **3m** (desk default) as EARLY leading ingredient. Sign that full-chain 1m is the wrong default.
7. Historical option quotes on HQ: if still `DATA_INSUFFICIENT`, 06 is fixtures-only — say so.

### TO 05_analysis (desk-intel)

**Need you to sign or reject:**

1. **News / `MACRO_EVENT` = veto / no-trade**, not a STRAT and not alpha. Extreme PCR-only = veto, not entry.
2. Chain **3m** Δ vs last snapshot is a **leading** EARLY ingredient (L3), owned by the desk, not a new STRAT ID.
3. Customer `/` shows **staged lean only**. Indicator names + mix IDs stay on `/desk`.
4. PERSONA_DESK CE/PE checklist is **required** for CONFIRMED, even if 003 all-three printed.
5. **010 OF overlay stays parked.** Do not block the engine on DEXT history. Volume-delta ≠ Greek delta.
6. Opening drive 09:15–09:45: 009 already filters; your checklist must not **also** invent a different T without naming it as a search param.

### TO 09_review

**Need you to sign or reject (notes, not a five-pass):**

1. This file is **`HYPOTHESIS` / `UNVALIDATED`**. Do **not** issue `RESEARCH_READY_FOR_PROGRAMMING`.
2. Conflicts in §4 are **left standing**. A “pass” that merges 002+005 or HAUS-MACD-entry + staging-confirm is a **fail**.
3. **011 / 012** are **`PROJECT_MIX`** transfers (stock/gold/candles → index options). `gA5` fill was a **sell**. Red-team the transfer, do not relabel as DHAN-DERIVED.
4. **013 / 014** excluded from Phase-1 buy mix on purpose. Selling corpus is not forgotten.
5. No win rates, no fills, no Dhan quotes invented. Spoken 70/30, 93/7, POP 80% stay `SOURCE_FACT` anecdotes.
6. Docs Auditor PASS on this edit is **not** a product gate.

---

## 8. Data (engine, later)

| Need | Use | Do not use |
|------|-----|------------|
| OHLC + true volume | Index **futures** (`POST /charts/historical` + `/intraday`; 1/5/15/25/60) | Cash-index “volume”; vendor index volume |
| Session VWAP / VWMA / Supertrend / MACD series | **Compute** from futures (or option) OHLC | Annexure Supertrend; `EMA_9` trigger; invented REST |
| Option chain | `POST /optionchain` documented fields; poll **3m**; Δ vs last snapshot | 1m full-chain default; invented DEXT OI-profile history |
| Strike / delta | Chain greeks if present; else 005 fallback 1–2 ITM from **spot** at signal (`2RnBT9`) | Frozen lot; frozen Tuesday expiry |
| News | RSS / calendar `MACRO_EVENT` / `NEWS_DAY` as **veto** | Headline alpha STRAT |
| Order-flow (010) | **`DATA_INSUFFICIENT`** on DhanHQ history until proven | Proxy with cash-index ticks; block engine design |
| SENSEX | **BSE** tokens, own chain client | NSE NIFTY client reused blindly |

**010 overlay parked.** Mix YAML `order_flow: false`. When/if HQ history exists, re-open as overlay on 003/001 — still not a primary.

---

## HANDOFF (04 freeze — still UNVALIDATED)

**Accepted**

- English bind as SOURCE_FACT. Same-video Gokul 003/004/005/008/009 = DHAN-DERIVED. 14 IDs, no 015+. Buy-first. 002 never on 003. 013/014 WAITING sell. 004 lengths NOT_IN_EN. ST “103” WEAK. Guests = affiliation only.

**Rejected**

- One Dhan recipe no video taught. 003+007+009 AND or 5m MACD confirm-or-kill as DHAN-DERIVED. 002 overlay on 003. Mapping gA5 bull put to buy CE. Invented 004 lengths. Frozen spoken “ten comma three” from 2Rn. SEBI RA / star trader as edge. Win rates.

**UNKNOWN / DATA_INSUFFICIENT**

- Super Scalper EMA lengths (`NOT_IN_EN`). OF history (010). 3m/2m resample. MACD ×3 vs ×4. HAUS MA 100 vs 300 / 9 vs 10. 2Rn “103.” pvmvki delta. 012 pattern **rule-detail**.

Next: 02/03/05/09 comment on §7. Keep `PROJECT_MIX` labeled. 06 does not code live. Still not a pass.
