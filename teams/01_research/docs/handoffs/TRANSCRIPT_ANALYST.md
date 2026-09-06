# TRANSCRIPT_ANALYST — teacher MIX clubs vs PROJECT_MIX

**Team:** 01_research (transcript analyst)  
**Date:** 2026-09-03  
**Layer:** `SOURCE_FACT` for *what one speaker taught as one recipe*. MIX IDs are **proposals** to 04 (`HYPOTHESIS` namespace). Not `VALIDATION`.  
**Status:** `EXTRACTED` / `DRAFT`. Gate: **not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Authority:** [`TRANSCRIPT_STRATEGY_BIND.md`](TRANSCRIPT_STRATEGY_BIND.md) — English `normalized_en/` wins.  
**Read-only 04:** [`MIX_CATALOG.md`](../../../04_quant/docs/MIX_CATALOG.md), [`ENGINE_MIX.md`](../../../04_quant/docs/ENGINE_MIX.md), `STRAT-001` / `002` / `003` / `005` / `006` / `007` / `009`.  
**KEEP_ALL.** No `STRAT-015+`. No win rates. No live orders. No apps.

Education ≠ edge. Spoken SEBI RA / “Star Trader” is affiliation only.

---

## Honesty banner

```text
layer:                  SOURCE_FACT (clubbing from tape) + MIX proposals for 04
status:                 UNVALIDATED
research_ready_for_programming: false
metrics:                win_rate=null  expectancy=null  profit_factor=null  max_drawdown=null
profitability:          NOT CLAIMED
ids:                    STRAT-001 … STRAT-014 stay BACKTEST_BOOK. New test IDs = MIX-* only.
live code / orders:     forbidden
fills / lots / quotes:  NOT INVENTED
```

01 does **not** edit `teams/04_quant/**`. 04 already cataloged `MIX-GOKUL-003` and `MIX-HAUS-001`. This file is the **tape reason** those IDs exist, plus `MIX-MUKUL-006` (speaker-named; 04 currently lists the same book as `MIX-SCALP-006` — alias, not a new STRAT).

---

## Rule: one recipe vs PROJECT_MIX

A MIX is **`DHAN-DERIVED`** only if **one speaker, one video** taught the attached IDs as **one class**. Splitting that class into STRAT rows is bookkeeping, not clubbing two teachers.

A MIX is **`PROJECT_MIX`** if 04 ANDs two speakers, transfers a stock/gold recipe onto index options, or uses desk staging as if a guest said it. Keep the label. Do not backfill a fake timestamp.

Conflicts stay as **named MIX / ablation rows**. Do not delete a STRAT.

| Origin tag | Use when | Forbidden |
|------------|----------|-----------|
| `DHAN-DERIVED` | Same speaker, same `@DhanHQ` video, taught as one recipe | Citing two men as one clock |
| `PROJECT_MIX` | Two speakers, desk spec, or universe transfer | Relabeling as DHAN-DERIVED |
| `CONFLICT` | Speakers disagree on the **same object** (e.g. strike) | Silent merge (002 on 003) |

---

## Teacher clubs (DHAN-DERIVED)

### MIX-GOKUL-003

**One class:** Dr. Gokul Chhabra / Gokul Jhabra, `2RnBT9DDDNI`.  
**Not** `PROJECT_MIX`. **Not** Himanshu’s clock.

Gokul taught **3-minute index futures** VWAP + VWMA(20) + Supertrend, **ITM / max ATM** (OTM not recommended), **mixed-index avoid**, and **ignore 09:15–09:45 / start 09:45 / flatten before 15:15** in the **same** masterclass. Bind: 003 / 005 / 008 / 009 **CONFIRMED** as same-video. Supertrend digits **“103”** stay **WEAK**.

**Do not attach 007.** 007 is Himanshu (`HAUSZx-hYdY`): new entries after **10:00**, mostly not after **14:30**. Gokul **starts 09:45**. ANDing them is `MIX-DEFAULT-BUY` / `MIX-ABL-CLOCKS` arm C — **`PROJECT_MIX`**.

**Do not attach 002.** Slightly OTM is HAUS. Gokul: OTM **not recommended** (`CONFLICT`).

```yaml
mix_id: MIX-GOKUL-003
origin: DHAN-DERIVED
origin_videos: [{video_id: 2RnBT9DDDNI}]
styles: [OPTION_BUYER]
attached:
  primary: [STRAT-003]
  overlay_strike: [STRAT-005]
  filter: [STRAT-008, STRAT-009]
not_attached: [STRAT-002, STRAT-007]   # 002 = HAUS OTM; 007 = Himanshu clock
optional_same_video: [STRAT-004]       # Super Scalper; lengths NOT_IN_EN — PARKED, not deleted
customer_default: false
status: UNVALIDATED
```

004 is the **same class** (Super Scalper on 1m premium, AND with 3m all-three in-video). Lengths are **`NOT_IN_EN` / `UNKNOWN`**. Keep 004 on KEEP_ALL via `MIX-SCALP-004` / `MIX-GOKUL-CLASS`. Do **not** freeze 9/21. Do **not** require 004 inside `MIX-GOKUL-003`.

### MIX-HAUS-001

**One speaker:** Himanshu Arora, `HAUSZx-hYdY`.  
Recipe **`DHAN-DERIVED`**. Phase-1 **index-only** yaml `market: [NIFTY, BANKNIFTY, SENSEX]` on 001 remains **`PROJECT_MIX`** vs spoken **NIFTY 100 stocks** + options application.

Himanshu taught **hourly parent + 5 or 10 minute child**, MACD histogram + MA 10/30/100, **buy above that child candle’s high**, **slightly OTM** (1–2 strikes) with ~40 delta adverse and 20–30% premium target, and **clock after 10:00 / mostly not after 14:30**. Bind: 001 / 002 / 007 **CONFIRMED** (params WEAK/CONFLICT stay search, not silent-correct).

**Do not attach 003 or 005.** Those are Gokul’s 3m futures stack and ITM/ATM strike. MACD here is **HAUS entry**, not desk 5m confirm-or-kill (`PROJECT_MIX` — see ablations).

**Do not attach 009.** Flatten-15:15 / skip-until-09:45 is Gokul.

```yaml
mix_id: MIX-HAUS-001
origin: DHAN-DERIVED              # 001+002+007 same speaker
origin_note: "001 market:[NIFTY,BANKNIFTY,SENSEX] is PROJECT_MIX vs spoken NIFTY 100 stocks"
origin_videos: [{video_id: HAUSZx-hYdY}]
styles: [OPTION_BUYER, POSITION]
attached:
  primary: [STRAT-001]
  overlay_strike: [STRAT-002]
  filter: [STRAT-007]
not_attached: [STRAT-003, STRAT-005, STRAT-009]
macd_role: HAUS_ENTRY             # buy child-candle high — not SIGNAL_STAGING confirm
customer_default: false
status: UNVALIDATED
```

001 recap **100 vs 300** MA is **CONFLICT** same video. MACD ×3 vs ×4 and trail MA 9 vs 10 are **WEAK**. 2h parent is **`NOT_IN_EN`** on HAUS (15m child alt **is** spoken). 01 does not pick a winner.

### MIX-MUKUL-006

**One speaker:** Mukul Choudhary, `pvmvkiS1cx4`.  
**`DHAN-DERIVED`.** Standalone primary — not an overlay on 001 or 003.

Mukul taught **NIFTY / BANKNIFTY / SENSEX**, analysis on **spot**, execution on **options**, **2-minute** chart, **EMA 10 and 20 only**, strike **ITM 100–200 points** (not ATM, not OTM, not deep ITM). Bind: structure **CONFIRMED**. Delta “555 to 6” / “0.55 to six” stays **WEAK**. Beginner line is **conditional**: if **India VIX > 15–16**, beginners should **not** scalp by **buying** options — not a blanket ban.

**Do not attach 002, 005, 007, or 009.** Different teachers, different strike and clocks.

04 currently catalogs this book as `MIX-SCALP-006`. 01’s speaker-named ID is **`MIX-MUKUL-006`**. Same STRAT-006. **Alias, not `STRAT-015+`.**

```yaml
mix_id: MIX-MUKUL-006
alias_in_04_catalog: MIX-SCALP-006    # do not mint a second STRAT
origin: DHAN-DERIVED
origin_videos: [{video_id: pvmvkiS1cx4}]
styles: [OPTION_BUYER, SCALPER]
attached: {primary: [STRAT-006]}
not_attached: [STRAT-001, STRAT-002, STRAT-003, STRAT-005, STRAT-007, STRAT-009]
caution: VIX_above_15_to_16_beginners_skip_buy_scalp   # conditional, not blanket
delta: WEAK
customer_default: false
status: UNVALIDATED
```

---

## Two ablations (named MIX, KEEP_ALL)

Ablations are **new test IDs**. They do **not** delete 001–014. Metrics stay **null**. 06 may queue them on fixtures later. 01 does not score them.

### MIX-ABL-CLOCKS

**Why:** no video taught “skip until **10:00** **and** flatten **15:15**” as one clock. Bind row STRAT-007 AND STRAT-009 = **`PROJECT_MIX`**. 00 already sent 007∩009 to 06 as a project AND.

| Arm | Clock | Speaker | Origin |
|-----|-------|---------|--------|
| A | **009 only** — ignore 09:15–09:45, **start 09:45**, flatten before 15:15 | Gokul `2RnBT9DDDNI` | `DHAN-DERIVED` (use on `MIX-GOKUL-003`) |
| B | **007 only** — new after 10:00, mostly not after 14:30, hard ban after 15:00 | Himanshu `HAUSZx-hYdY` | `DHAN-DERIVED` (use on `MIX-HAUS-001`) |
| C | **007 ∧ 009** — no new 09:15–**10:00**, no new after **14:30**, flatten **15:15** | two speakers | **`PROJECT_MIX`** (`MIX-DEFAULT-BUY` clock) |

Arm C is stricter than either teacher. Do not cite one timestamp as if both agreed. Do not relabel C as `DHAN-DERIVED`.

```yaml
mix_id: MIX-ABL-CLOCKS
origin: PROJECT_MIX               # the AND is ours; arms A/B are teacher clocks
styles: [OPTION_BUYER]
arms:
  - {id: A, filter: [STRAT-009], primary: STRAT-003, origin: DHAN-DERIVED}
  - {id: B, filter: [STRAT-007], primary: STRAT-001, origin: DHAN-DERIVED}
  - {id: C, filter: [STRAT-007, STRAT-009], primary: STRAT-003, origin: PROJECT_MIX}
forbidden: cite_one_timestamp_for_the_AND
customer_default: false           # arm C is on MIX-DEFAULT-BUY, still UNVALIDATED
status: UNVALIDATED
```

### MIX-CONFLICT-STRIKE

**Why:** strike follows the **primary’s video**. HAUS slightly OTM (**002**) **conflicts** with Gokul “OTM not recommended” (**005**). Mukul’s ITM 100–200 (**006**) is a third object. Bind: STRAT-002 overlay on 003 = **CONFLICT**. 04 already named this mix — 01 **confirms from tape**, does not invent a merge.

| Arm | Strike | Primary | Video | Origin |
|-----|--------|---------|-------|--------|
| A | **002** slightly OTM, ~40Δ adverse, 20–30% premium | STRAT-001 | `HAUSZx-hYdY` | `DHAN-DERIVED` on HAUS book |
| B | **005** ITM / max ATM; OTM not recommended | STRAT-003 | `2RnBT9DDDNI` | `DHAN-DERIVED` on Gokul book |
| C | **006** ITM 100–200 pts (delta **WEAK**) | STRAT-006 | `pvmvkiS1cx4` | `DHAN-DERIVED` on Mukul book |

**Forbidden:** attach **002 on 003**. That is a spec fail, not a test. Host vs guest **50-multiples** on 005 stays `TEST_ON_OFF` (**CONFLICT** in-video), not a fourth silent strike.

```yaml
mix_id: MIX-CONFLICT-STRIKE
origin: CONFLICT                  # not DHAN-DERIVED as one recipe
styles: [OPTION_BUYER]
arms:
  - {strike: STRAT-002, primary: STRAT-001, video: HAUSZx-hYdY}
  - {strike: STRAT-005, primary: STRAT-003, video: 2RnBT9DDDNI}
  - {strike: STRAT-006, primary: STRAT-006, video: pvmvkiS1cx4}
forbidden: attach_002_on_003
customer_default: false
status: UNVALIDATED
```

---

## What NO video taught as one system (`PROJECT_MIX`)

Keep labeled. Do not call these transcript theorems. 04 may still **test** them as `HYPOTHESIS`.

| Mix claim | Tape | Bind |
|-----------|------|------|
| **`MIX-DEFAULT-BUY`** = 003 + **007** + 008 + 009 + desk 5m ST/MACD + 005 | Gokul 003/005/008/009 **plus** Himanshu 007 **plus** desk staging | **`PROJECT_MIX`**. Customer default in 04 is still this — UI lean only, **UNVALIDATED**, **not** DHAN-DERIVED |
| 007 ∧ 009 as one clock | Two speakers, two opens | **`PROJECT_MIX`** → `MIX-ABL-CLOCKS` arm C |
| 5m MACD / Supertrend **confirm-or-kill** ([`SIGNAL_STAGING.md`](../../../04_quant/docs/SIGNAL_STAGING.md)) | HAUS: child MACD **is entry** (buy that candle’s high). Gokul entry is **3m** all-three, not 5m MACD | **`PROJECT_MIX`**. Two test IDs. Do not average |
| 002 overlay on 003 | HAUS OTM vs Gokul “OTM not recommended” | **`CONFLICT`** → `MIX-CONFLICT-STRIKE` |
| 001 as NIFTY/BN/SENSEX-only book | Spoken universe = NIFTY 100 **stocks** + options application | **`PROJECT_MIX`** on the yaml universe, inside `MIX-HAUS-001` |
| 010 OF as 003/001 gate | YUX/DzT = tool + OF rules. No CE/PE / 003-filter recipe | **`PROJECT_MIX`**. HQ OF history `DATA_INSUFFICIENT` |
| 011 index-option reversal primary | `H_6kee` = stocks/gold. `gA5` **executed bull put sell** | **`PROJECT_MIX`**. Do not map that fill to buy CE |
| 012 as 001/003 pattern gate | Stock patterns; no spoken “filter Gokul/HAUS” | **`PROJECT_MIX`** |

013 / 014 stay **SELL** / `WAITING`. EN confirms. Do not rewrite into Phase-1 buy. IDs stay 013/014.

---

## KEEP_ALL map (01 → 04)

| ID | 01 clubbing | Default ticket? |
|----|-------------|-----------------|
| STRAT-001–014 | All stay `BACKTEST_BOOK` | Only 04’s `MIX-DEFAULT-BUY` is customer lean — still `PROJECT_MIX` / `UNVALIDATED` |
| `MIX-GOKUL-003` | Teacher club | no |
| `MIX-HAUS-001` | Teacher club | no |
| `MIX-MUKUL-006` | Teacher club (`MIX-SCALP-006` alias) | no |
| `MIX-ABL-CLOCKS` | Ablation | no |
| `MIX-CONFLICT-STRIKE` | Ablation | no |
| `MIX-SCALP-004` / `MIX-GOKUL-CLASS` | Same-video 004 optional | no — PARKED lengths |
| `MIX-REV-011` / `MIX-PA-012` / `MIX-OF-010` | PROJECT overlays | no |
| `MIX-SELL-013` / `MIX-SELL-014` | SELL corpus | no — not buy UI |
| `STRAT-015+` | **Forbidden** | — |

`WAITING` / `PARKED` = not customer default. **Not deleted.**

---

## Must-rewrite (01 → 04; 01 does not edit 04)

Bind already listed these. Analyst restates only what MIX IDs force:

1. **STRAT-002.md** “Overlay on 001 **(or 003)**” — **CONFLICT**. 002 only on `MIX-HAUS-001`.
2. **ENGINE_MIX default ticket** — keep **`PROJECT_MIX`**. Do not cite Gokul or HAUS as having taught 007∧009 + 5m confirm-or-kill.
3. **`MIX-SCALP-006` vs `MIX-MUKUL-006`** — alias the same STRAT-006 book. Do not mint `STRAT-015`.
4. **001 2h parent** still `NOT_IN_EN` on HAUS. **004 lengths** still `NOT_IN_EN`.

---

## HANDOFF (01 transcript analyst)

**Accepted**

- `MIX-GOKUL-003` = 003 + 005 + 008 + 009, **not** 007, **not** 002. Same video `2RnBT9DDDNI`. `DHAN-DERIVED`.
- `MIX-HAUS-001` = 001 + 002 + 007, **not** 003, **not** 005. Same speaker `HAUSZx-hYdY`. Recipe `DHAN-DERIVED`; index-only universe on 001 stays `PROJECT_MIX`.
- `MIX-MUKUL-006` = STRAT-006 only (`pvmvkiS1cx4`). `DHAN-DERIVED`. Alias of 04’s `MIX-SCALP-006`. VIX>15–16 caution **conditional**.
- Two ablations: `MIX-ABL-CLOCKS` (007 vs 009 vs PROJECT AND) and `MIX-CONFLICT-STRIKE` (002 vs 005 vs 006; **never 002 on 003**).
- KEEP_ALL. STRAT-001–014 stay `BACKTEST_BOOK`. 004/010/011/012/013/014 not dropped. No `STRAT-015+`.

**Rejected**

- Treating SEBI RA / “star trader” as edge.
- Merging 007 into Gokul’s recipe, or 003/005 onto HAUS.
- Silent 002-on-003. Averaging 002/005/006 into one “Dhan strike.”
- Relabeling `MIX-DEFAULT-BUY` or 5m MACD confirm-or-kill as `DHAN-DERIVED`.
- Inventing Super Scalper lengths, win rates, fills, lots, or live orders.
- Mapping `gA5` bull-put **fill** to a CE buy. Mapping 009 flatten-15:15 to CAS.

**UNKNOWN / DATA_INSUFFICIENT**

- Super Scalper EMA lengths (`NOT_IN_EN`). 2Rn Supertrend **“103.”** Mukul delta “555 to 6.” HAUS MACD ×3 vs ×4; MA 100 vs 300; trail 9 vs 10.
- HQ order-flow history (010). 012 pattern **rule detail** still WAITING (patterns **named** in EN).
- F&O 15:30 vs 15:40 flatten vs close — 03 VERIFY, not a transcript pick.

**What 04 / 06 / 09 must do**

- 04: keep teacher clubs tagged `DHAN-DERIVED`. Keep `MIX-DEFAULT-BUY` tagged `PROJECT_MIX`. Alias `MIX-MUKUL-006` ↔ `MIX-SCALP-006`. Catalog `MIX-ABL-CLOCKS` if not already queued as 007 vs 009.
- 06: may **schedule** these MIX IDs on fixtures. May not claim an edge. Metrics stay null.
- 09: notes ≠ pass. Conflicts stand. **Not** `RESEARCH_READY_FOR_PROGRAMMING`.

**What they must not do**

- Delete a STRAT because a MIX is the customer lean.
- Code live strategies or `/alerts/orders`.
- Print win rates from spoken “70/30” anecdotes.
