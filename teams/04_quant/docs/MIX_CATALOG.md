# MIX_CATALOG.md — KEEP_ALL books (STRAT + MIX + EQ + CAS pointer)

**Team:** 04_quant  
**Date:** 2026-09-03  
**Policy:** `KEEP_ALL`  
**Bind:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)  
**Default customer ticket (engine):** [`ENGINE_MIX.md`](ENGINE_MIX.md)  
**Equity slots:** [`candidates/EQUITY_ETF_BACKLOG.md`](candidates/EQUITY_ETF_BACKLOG.md)  
**CAS IDs:** [`CAS_STRATEGIES.md`](../../03_phd_market/cas/CAS_STRATEGIES.md) — CAS-001–005. This file **pointers only**.

---

## 1. Honesty banner

```text
layer:                  HYPOTHESIS
status:                 UNVALIDATED
research_ready_for_programming: false
gate:                   09 five-pass has NOT passed. Notes ≠ pass.
metrics:                win_rate=null  expectancy=null  profit_factor=null  max_drawdown=null
profitability:          NOT CLAIMED
live code:              forbidden (no apps/, no packages/ strategies)
fills / lots / dhan quotes: NOT INVENTED
empty DHAN_*:           does not block this spec
```

**ID namespaces (forever):**

| Prefix | Who | Forbidden |
|--------|-----|-----------|
| `STRAT-001` … `STRAT-014` | Index-option video recipes. **IDs never reused, never deleted.** | `STRAT-015+` |
| `MIX-*` | Named clubs / ablations / style books. **New test IDs.** | Pretending a MIX is a STRAT |
| `EQ-*` / `SO-*` / `ETF-*` | Other book | Bleed into NIFTY/BN/SENSEX blotter |
| `CAS-*` | 03 writes | 04 inventing CAS strategy IDs |

Education ≠ edge. Guests (Gokul spoken SEBI RA; Himanshu “star trader” not spoken SEBI RA) are affiliation only.

---

## 2. Policy: KEEP_ALL

**Do not veto teacher recipes.** Disagreement becomes a **named MIX**, not a deleted STRAT.

| Word on a STRAT | Means | Does **not** mean |
|-----------------|-------|-------------------|
| `BACKTEST_BOOK` | 06 may queue this ID on fixtures. Metrics still **null**. | Validated, profitable, or customer default |
| `WAITING` | **Not** the Phase-1 **buy** customer default. Still in the catalog. | Deleted / skipped / forgotten |
| `PARKED` | Blocked on data or UNKNOWN params (e.g. 004 lengths, 010 HQ OF history). Still in the catalog. | Dropped from KEEP_ALL |
| Customer default | `MIX-DEFAULT-BUY` only (see §4) | The only book that exists |

**Status on every DHAN-video STRAT is `BACKTEST_BOOK`** even if it is not the customer default.

---

## 3. Style tags

One book can carry several tags. MIX rows pick a subset.

| Tag | Use |
|-----|-----|
| `OPTION_BUYER` | Index CE/PE **buy** (Phase-1 UI language) |
| `OPTION_SELLER` | Credit / ratio / hedge **sell**. IDs stay **013 / 014** |
| `SCALPER` | 1m premium or 2m EMA books |
| `POSITION` | Multi-day / dual-TF / weekly structure |
| `EQUITY_INTRADAY` | Cash / ScanX intraday — **EQ-*** only |
| `EQUITY_SWING` | Multi-day stock — **EQ-*** only |
| `STOCK_OPTION` | Single-stock options — **SO-*** only |

EQ / SO / ETF slots are **not copied** here. Pointer: [`EQUITY_ETF_BACKLOG.md`](candidates/EQUITY_ETF_BACKLOG.md).

---

## 4. STRAT-001–014 — all BACKTEST_BOOK

IDs **stay these IDs forever**. `WAITING` / `PARKED` = not default ticket.

| ID | Style tags | Ticket role | Default? | Notes |
|----|------------|-------------|----------|-------|
| STRAT-001 | OPTION_BUYER, POSITION | primary (HAUS) | no — `MIX-HAUS-001` | Index-only yaml = `PROJECT_MIX`. 2h parent `NOT_IN_EN` |
| STRAT-002 | OPTION_BUYER | strike overlay | with 001 only | **Never silently on 003** |
| STRAT-003 | OPTION_BUYER | primary (Gokul 3m) | yes inside `MIX-GOKUL-003` / `MIX-DEFAULT-BUY` | ST “103” **WEAK** |
| STRAT-004 | OPTION_BUYER, SCALPER | confirm / scalp | no — `PARKED` lengths `NOT_IN_EN` | **Not deleted.** `MIX-SCALP-004` |
| STRAT-005 | OPTION_BUYER | strike overlay | with 003 | ITM/max ATM. OTM not recommended in-video |
| STRAT-006 | OPTION_BUYER, SCALPER | primary (Mukul 2m) | no — `MIX-SCALP-006` / `MIX-MUKUL-006` | VIX>15–16 caution. Delta **WEAK** |
| STRAT-007 | OPTION_BUYER | filter (Himanshu clock) | in HAUS mix; AND with 009 is `PROJECT_MIX` | Keep as its own filter |
| STRAT-008 | OPTION_BUYER | filter (mixed-index) | in Gokul mix | DHAN-DERIVED same video as 003 |
| STRAT-009 | OPTION_BUYER | filter (09:45 / 15:15) | in Gokul mix | Start **09:45**, not 10:00 |
| STRAT-010 | OPTION_BUYER (overlay) | OF gate | no — `PARKED` `DATA_INSUFFICIENT` | **Not dropped.** `MIX-OF-010` |
| STRAT-011 | OPTION_BUYER (+ equity-native pieces) | reversal alt | no — `MIX-REV-011` | Origin **`PROJECT_MIX`**. gA5 **fill was sell** |
| STRAT-012 | OPTION_BUYER (overlay) | candle/S/R | optional | **`PROJECT_MIX`** on 001/003. `MIX-PA-012` |
| STRAT-013 | **OPTION_SELLER**, POSITION | bull put credit | no — `WAITING` not buy UI | **Keep ID 013.** `MIX-SELL-013` |
| STRAT-014 | **OPTION_SELLER**, POSITION | 1-3-2 call ratio | no — `WAITING` not buy UI | **Keep ID 014.** `MIX-SELL-014` |

**Confirmation:** STRAT-001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014 are all **`BACKTEST_BOOK`**. None deleted.

---

## 5. Named MIX IDs (new test IDs)

A MIX is a **new test ID**. Conflicts **stay conflicts inside the mix**. 002 never silently on 003.

Same-video Gokul stack = **`DHAN-DERIVED`**. Two-speaker AND, desk staging, index transfers = **`PROJECT_MIX`**. Indian web folklore (ORB **09:15–09:30**, CPR) and generic web patterns = **`WEB-DERIVED`**. A Dhan chart-product mention is **not** a recipe — do not relabel folklore as `DHAN-DERIVED`.

Shared YAML defaults (every mix):

```yaml
book_policy: KEEP_ALL
status: UNVALIDATED
research_ready_for_programming: false
lot_size: FROM_INSTRUMENT_MASTER
expiry: FROM_CONTRACT
session_tz: Asia/Kolkata
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

### MIX-GOKUL-003

Same class (`2RnBT9DDDNI`). **Not** `PROJECT_MIX`.

```yaml
mix_id: MIX-GOKUL-003
origin: DHAN-DERIVED
origin_videos: [{video_id: 2RnBT9DDDNI}]
styles: [OPTION_BUYER]
attached: {primary: [STRAT-003], overlay_strike: [STRAT-005], filter: [STRAT-008, STRAT-009]}
not_attached: [STRAT-002, STRAT-007]   # 007 is Himanshu; 002 is HAUS OTM
optional_same_video_confirm: [STRAT-004]  # lengths UNKNOWN — also MIX-SCALP-004
customer_default: false
```

### MIX-GOKUL-003-009

02 first **option-premium** charter ([`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md)). 003 + **009 only**. No 007, no 008. Not the customer default. Same as `MIX-ABL-CLOCKS` arm A.

```yaml
mix_id: MIX-GOKUL-003-009
origin: DHAN-DERIVED
origin_videos: [{video_id: 2RnBT9DDDNI}]
styles: [OPTION_BUYER]
attached: {primary: [STRAT-003], overlay_strike: [STRAT-005], filter: [STRAT-009]}
not_attached: [STRAT-002, STRAT-007, STRAT-008]  # 008 is same-video Gokul; 02 first premium run excludes it
also: MIX-ABL-CLOCKS arm A
customer_default: false
```

### MIX-HAUS-001

Same speaker (`HAUSZx-hYdY`). Recipe DHAN-DERIVED; **index-only universe** on 001 remains `PROJECT_MIX`.

```yaml
mix_id: MIX-HAUS-001
origin: DHAN-DERIVED              # 001+002+007 same speaker
origin_note: "001 market:[NIFTY,BANKNIFTY,SENSEX] is PROJECT_MIX vs spoken NIFTY 100 stocks"
origin_videos: [{video_id: HAUSZx-hYdY}]
styles: [OPTION_BUYER, POSITION]
attached: {primary: [STRAT-001], overlay_strike: [STRAT-002], filter: [STRAT-007]}
not_attached: [STRAT-003, STRAT-005]  # do not soup Gokul strike onto HAUS
macd_role: HAUS_ENTRY                 # buy child-candle high — not staging confirm
customer_default: false
```

### MIX-DEFAULT-BUY

Current Phase-1 **customer** ticket. **`PROJECT_MIX`**.

```yaml
mix_id: MIX-DEFAULT-BUY
origin: PROJECT_MIX
styles: [OPTION_BUYER]
attached:
  primary: [STRAT-003]
  overlay_strike: [STRAT-005]
  filter: [STRAT-007, STRAT-008, STRAT-009]  # 007∧009 = two speakers
  confirm: [STAGING_5M_ST_MACD]            # desk; not HAUS entry
not_attached: [STRAT-002]                  # CONFLICT if added
customer_default: true                     # UI lean only; still UNVALIDATED
```

### MIX-SCALP-006

Speaker-named alias **`MIX-MUKUL-006`** (01 transcript analyst). Same STRAT-006 book. **Not** `STRAT-015+`.

```yaml
mix_id: MIX-SCALP-006
alias: MIX-MUKUL-006
origin: DHAN-DERIVED
origin_videos: [{video_id: pvmvkiS1cx4}]
styles: [OPTION_BUYER, SCALPER]
attached: {primary: [STRAT-006]}
not_attached: [STRAT-001, STRAT-002, STRAT-003, STRAT-005, STRAT-007, STRAT-009]
caution: VIX_above_15_to_16_beginners_skip_buy_scalp   # conditional, not blanket
delta: WEAK
customer_default: false
```

### MIX-SCALP-004

**Do not invent 9/21.** Lengths `NOT_IN_EN` / `UNKNOWN` — grid later, not a frozen pair.

```yaml
mix_id: MIX-SCALP-004
origin: DHAN-DERIVED               # structure + 1m premium; same video as 003
origin_videos: [{video_id: 2RnBT9DDDNI}]
styles: [OPTION_BUYER, SCALPER]
attached: {primary_or_confirm: [STRAT-004]}
ema_fast_slow: UNKNOWN             # NOT_IN_EN — search grid, never 9/21 invented
parked_reason: DATA_INSUFFICIENT until chart-export VERIFY
customer_default: false            # PARKED ≠ deleted
```

### MIX-REV-011

Keep for **backtest**. Origin **`PROJECT_MIX`**. gA5 **executed sell** — do not map that fill to buy CE as if the tape said so. Still **backtest** as a transfer hypothesis.

```yaml
mix_id: MIX-REV-011
origin: PROJECT_MIX
styles: [OPTION_BUYER]             # transfer hypothesis only
attached: {primary: [STRAT-011]}
do_not: map_gA5_bull_put_fill_to_buy_CE
gA5_executed: STRAT-013            # seller book — MIX-SELL-013
h6kee_universe: stocks_gold_silver
customer_default: false
backtest: true                     # KEEP_ALL transfer book
```

### MIX-SELL-013

Seller book. **ID stays STRAT-013.**

```yaml
mix_id: MIX-SELL-013
origin: DHAN-DERIVED
origin_videos: [{video_id: gA5FtEnSABM}]
styles: [OPTION_SELLER, POSITION]
attached: {primary: [STRAT-013]}
phase1_buy_ui: false               # WAITING = not default ticket, not deleted
customer_default: false
```

### MIX-SELL-014

Seller book. **ID stays STRAT-014.**

```yaml
mix_id: MIX-SELL-014
origin: DHAN-DERIVED
origin_videos: [{video_id: 6el9Jqnrdz8}]
styles: [OPTION_SELLER, POSITION]
attached: {primary: [STRAT-014]}
expiry_weekday: FROM_CONTRACT      # Tuesday in video is recording-dated
phase1_buy_ui: false
customer_default: false
```

### MIX-OF-010

**Do not drop.** HQ order-flow history `DATA_INSUFFICIENT`. Overlay recipe vs 003/001 is `PROJECT_MIX`.

```yaml
mix_id: MIX-OF-010
origin: PROJECT_MIX                # tool DHAN-DERIVED; 003-gate is ours
origin_videos: [{video_id: YUXJv_xBStw}, {video_id: DzT_681GThA}]
styles: [OPTION_BUYER]             # overlay only
attached: {overlay: [STRAT-010]}
data: {order_flow: DATA_INSUFFICIENT}
customer_default: false            # PARKED ≠ deleted
```

### MIX-PA-012

```yaml
mix_id: MIX-PA-012
origin: PROJECT_MIX                # no spoken "filter Gokul/HAUS"
origin_videos: [{video_id: njqeZc_tYy8}]
styles: [OPTION_BUYER]
attached: {overlay: [STRAT-012]}
patterns_named_en: [hammer, bullish_engulfing, morning_star, dark_cloud_cover, inside_bar]
rule_detail: WAITING               # existence named; entry/stop tables not all extracted
customer_default: false
```

### MIX-CONFLICT-STRIKE

Explicit **ablation**. Label **`CONFLICT`**. Not a silent merge.

```yaml
mix_id: MIX-CONFLICT-STRIKE
origin: CONFLICT                   # not DHAN-DERIVED as one recipe
styles: [OPTION_BUYER]
arms:
  - {strike: STRAT-002, primary: STRAT-001, video: HAUSZx-hYdY}   # slightly OTM
  - {strike: STRAT-005, primary: STRAT-003, video: 2RnBT9DDDNI}   # ITM/max ATM
  - {strike: STRAT-006, primary: STRAT-006, video: pvmvkiS1cx4}   # ITM 100–200; delta WEAK
forbidden: attach_002_on_003
customer_default: false
```

### MIX-ABL-CLOCKS

007 vs 009 vs PROJECT AND. Arms A/B are teacher clocks. Arm C is `MIX-DEFAULT-BUY`.

```yaml
mix_id: MIX-ABL-CLOCKS
origin: PROJECT_MIX               # the AND is ours; arms A/B are teacher clocks
styles: [OPTION_BUYER]
arms:
  - {id: A, filter: [STRAT-009], primary: STRAT-003, origin: DHAN-DERIVED}  # MIX-GOKUL-003-009
  - {id: B, filter: [STRAT-007], primary: STRAT-001, origin: DHAN-DERIVED}  # MIX-HAUS-001
  - {id: C, filter: [STRAT-007, STRAT-009], primary: STRAT-003, origin: PROJECT_MIX}
forbidden: cite_one_timestamp_for_the_AND
customer_default: false
```

### MIX-MTF-TREND

**`PROJECT_MIX`.** Murphy-style higher-TF gate on 003. Not a teacher club. Not customer default.

```yaml
mix_id: MIX-MTF-TREND
origin: PROJECT_MIX
styles: [OPTION_BUYER]
primary: [STRAT-003]
gate: [STRAT-001]                 # 1h parent MACD hist + MA 10/30/100 only
overlay_strike: [STRAT-005]       # ITM ATM-2 / ATM+2
filter: [STRAT-009]
not_attached: [STRAT-002, STRAT-006, STRAT-007, STRAT-008]
markets: [NIFTY, SENSEX]
customer_default: false
```

### MIX-CONFIRM-5M

**`PROJECT_MIX`.** Desk 5m MACD hist confirm-or-kill. Not HAUS buy-the-high. Not 5m Supertrend AND.

```yaml
mix_id: MIX-CONFIRM-5M
origin: PROJECT_MIX
styles: [OPTION_BUYER]
primary: [STRAT-003]
confirm: 5m_MACD_HIST_sign
overlay_strike: [STRAT-005]
filter: [STRAT-009]
not_attached: [STRAT-002, STRAT-006, STRAT-007, STRAT-008, 5m_Supertrend]
markets: [NIFTY, SENSEX]
customer_default: false
```

### MIX-EQ-* (pointer — do not copy yaml)

```yaml
mix_id: MIX-EQ
origin: pointer
styles: [EQUITY_INTRADAY, EQUITY_SWING, STOCK_OPTION]
slots_file: candidates/EQUITY_ETF_BACKLOG.md
slot_ids_on_disk:
  EQUITY_INTRADAY: [EQ-001, EQ-002, EQ-003, EQ-004, EQ-005, EQ-006, EQ-007, EQ-008, EQ-010]
  EQUITY_SWING: [EQ-009, EQ-011, EQ-012, EQ-014]   # EQ-013 REJECTED in backlog until transcript
  STOCK_OPTION: [SO-001, SO-002, SO-003]
  ETF: [ETF-001]
not: STRAT-015+
do_not: copy_eq_yaml_into_index_book
```

### MIX-CAS (pointer only)

```yaml
mix_id: MIX-CAS
origin: pointer
owner: 03_phd_market
ids: CAS-*                         # 03 writes; 04 does not invent
note: Closing Auction Session ≠ F&O 15:40. Daily BOUNCE|SIDEWAYS|FALL is UNVALIDATED.
```

### MIX-GOKUL-CLASS (optional same-video full stack)

Teacher class as one backtest book — **do not veto 004**.

```yaml
mix_id: MIX-GOKUL-CLASS
origin: DHAN-DERIVED
origin_videos: [{video_id: 2RnBT9DDDNI}]
styles: [OPTION_BUYER, SCALPER]
attached: {primary: [STRAT-003], confirm: [STRAT-004], overlay_strike: [STRAT-005], filter: [STRAT-008, STRAT-009]}
004_lengths: UNKNOWN
customer_default: false
```

---

## 6. Clubbing rule

1. A MIX is a **new test ID**. Do not rename a STRAT into a MIX.  
2. One live **customer** ticket still = one primary + filters + confirm/kill + optional overlay ([`ENGINE_MIX.md`](ENGINE_MIX.md)).  
3. If two teachers disagree, **name a MIX** (`MIX-DEFAULT-BUY`, `MIX-CONFLICT-STRIKE`). Do not delete a STRAT.  
4. **002 never silently on 003.** That ablation is `MIX-CONFLICT-STRIKE`.  
5. `PROJECT_MIX` stays labeled. Same-video Gokul (`MIX-GOKUL-003`, `MIX-GOKUL-CLASS`) is `DHAN-DERIVED`. **`WEB-DERIVED`** = folklore / web pattern, not a `@DhanHQ` recipe.  
6. 06 queues MIX IDs on **fixtures**. Metrics stay **null** until a real engine + 09 pass.  
7. Scan IDs in §8 are **`MIX-*`**, not `STRAT-015+`. They do **not** change `MIX-DEFAULT-BUY`.

---

## 7. What 06 / 09 must not do

- Drop 004, 010, 011, 012, 013, or 014 because they are not `MIX-DEFAULT-BUY`.  
- Invent Super Scalper 9/21.  
- Map gA5’s bull-put **fill** to a CE buy inside `MIX-REV-011`.  
- Issue `RESEARCH_READY_FOR_PROGRAMMING` from this catalog.  
- Add `STRAT-015+`.  
- Relabel §8 ORB 09:15–09:30 or CPR as `DHAN-DERIVED`.  
- Promote a scan MIX onto `MIX-DEFAULT-BUY`.

---

## 8. MIX-WEB / MIX-PATTERN (scan, not STRAT-015+)

**Scan queue only.** Not teacher clubs. Not customer default. **`MIX-DEFAULT-BUY` is unchanged.** Full ticket: [`MIX_SCAN_2026-09-03.md`](MIX_SCAN_2026-09-03.md).

These IDs are **pattern scans** for a later 06 fixture pass. They are **not** `STRAT-015+`. They do **not** attach to 003/001 as silent overlays. `MIX-ENGULF` / `MIX-INSIDE-BRK` are **standalone scans**, not a rewrite of `MIX-PA-012` (STRAT-012 overlay).

**Folklore vs tape:** popular Indian **ORB 09:15–09:30 IST** and **CPR** (Central Pivot Range) are **web folklore**, origin **`WEB-DERIVED`**. They are **not** a `@DhanHQ` video recipe. 01 already records (`eApl0SfVBBY` OR-01): speaker ORB product setting is **09:15–10:00**; **09:15–09:30** is “some people.” CPR is a chart product / “spread on YouTube” (`G31RFueZLvk`) — not an index-options STRAT. Do **not** cite those videos as the origin of these MIX IDs.

Shared YAML (every scan mix):

```yaml
book_policy: KEEP_ALL
status: UNVALIDATED
research_ready_for_programming: false
role: scan
live_code: false
customer_default: false          # MIX-DEFAULT-BUY not touched
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
not: STRAT-015+
```

### WEB-DERIVED (Indian folklore / web, not DhanHQ recipe)

```yaml
mix_id: MIX-ORB-15
origin: WEB-DERIVED
origin_note: "Popular Indian ORB 09:15–09:30 IST folklore. Not DhanHQ video. Not speaker 09:15–10:00 product ORB."
styles: [OPTION_BUYER]
scan: opening_range_break_0915_0930_IST
customer_default: false
```

```yaml
mix_id: MIX-ORB-VWAP
origin: WEB-DERIVED
origin_note: "Web combo: 09:15–09:30 ORB then VWAP side. Not Gokul 3m all-three (STRAT-003)."
styles: [OPTION_BUYER]
scan: orb_then_vwap
customer_default: false
```

```yaml
mix_id: MIX-PDH-PDL
origin: WEB-DERIVED
origin_note: "Prior-day high/low break folklore. Chart PDH/PDL is not a DhanHQ STRAT."
styles: [OPTION_BUYER]
scan: prev_day_high_low_break
customer_default: false
```

```yaml
mix_id: MIX-CPR-BIAS
origin: WEB-DERIVED
origin_note: "CPR (TC/BC/pivot) bias folklore, not a DhanHQ index-options recipe."
styles: [OPTION_BUYER]
scan: cpr_above_tc_ce_below_bc_pe
customer_default: false
```

```yaml
mix_id: MIX-CPR-ORB
origin: WEB-DERIVED
origin_note: "Folklore AND of CPR bias + 09:15–09:30 ORB. Not one DhanHQ class."
styles: [OPTION_BUYER]
scan: cpr_and_orb_15
customer_default: false
```

```yaml
mix_id: MIX-NR7-BRK
origin: WEB-DERIVED
origin_note: "NR7 (narrowest of last 7) breakout as web folklore, not DhanHQ."
styles: [OPTION_BUYER]
scan: nr7_break
customer_default: false
```

```yaml
mix_id: MIX-PIVOT-R1
origin: WEB-DERIVED
origin_note: "Classic floor pivot R1 / S1 break. Folklore, not DhanHQ."
styles: [OPTION_BUYER]
scan: pivot_r1_s1_break
customer_default: false
```

```yaml
mix_id: MIX-GAP
origin: WEB-DERIVED
origin_note: "Session gap-go / gap-fill folklore. Not a DhanHQ STRAT."
styles: [OPTION_BUYER]
scan: gap_go_or_fill
customer_default: false
```

### PROJECT_MIX (named TA scans; not teacher clubs)

```yaml
mix_id: MIX-DONCHIAN-20
origin: PROJECT_MIX
origin_note: "20-bar Donchian break. Desk-named scan, not DhanHQ."
styles: [OPTION_BUYER]
scan: donchian_20_break
customer_default: false
```

```yaml
mix_id: MIX-BB-BREAK
origin: PROJECT_MIX
origin_note: "Bollinger close-beyond-band. Length/k UNKNOWN — do not invent."
styles: [OPTION_BUYER]
scan: bollinger_band_break
bb_length_k: UNKNOWN
customer_default: false
```

```yaml
mix_id: MIX-KELTNER
origin: PROJECT_MIX
origin_note: "Keltner channel break. EMA/ATR lengths UNKNOWN."
styles: [OPTION_BUYER]
scan: keltner_break
keltner_lengths: UNKNOWN
customer_default: false
```

```yaml
mix_id: MIX-INSIDE-BRK
origin: PROJECT_MIX
origin_note: "Inside-bar break as standalone scan. Not MIX-PA-012 / STRAT-012 overlay."
styles: [OPTION_BUYER]
scan: inside_bar_break
not_attached: [STRAT-012]
customer_default: false
```

```yaml
mix_id: MIX-ENGULF
origin: PROJECT_MIX
origin_note: "Engulfing as standalone scan. Not MIX-PA-012 / STRAT-012 overlay."
styles: [OPTION_BUYER]
scan: engulfing
not_attached: [STRAT-012]
customer_default: false
```

```yaml
mix_id: MIX-MOM-BODY
origin: PROJECT_MIX
origin_note: "Large-body momentum candle. Threshold UNKNOWN."
styles: [OPTION_BUYER]
scan: momentum_body
body_threshold: UNKNOWN
customer_default: false
```

```yaml
mix_id: MIX-ROC-10
origin: PROJECT_MIX
origin_note: "10-bar rate of change sign. Not a DhanHQ recipe."
styles: [OPTION_BUYER]
scan: roc_10
customer_default: false
```

```yaml
mix_id: MIX-SAR
origin: PROJECT_MIX
origin_note: "Parabolic SAR flip. AF params UNKNOWN."
styles: [OPTION_BUYER]
scan: parabolic_sar_flip
sar_af: UNKNOWN
customer_default: false
```

```yaml
mix_id: MIX-ADX-DI
origin: PROJECT_MIX
origin_note: "ADX +DI/−DI directional. Period UNKNOWN. No ADX REST."
styles: [OPTION_BUYER]
scan: adx_di
adx_period: UNKNOWN
customer_default: false
```

```yaml
mix_id: MIX-EMA-20-50
origin: PROJECT_MIX
origin_note: "EMA 20/50 cross scan. Not Super Scalper. Do not invent 9/21 (MIX-SCALP-004)."
styles: [OPTION_BUYER]
scan: ema_20_cross_50
not_attached: [STRAT-004]
customer_default: false
```

```yaml
mix_id: MIX-STREAK-3
origin: PROJECT_MIX
origin_note: "Three same-color closes. Desk-named scan."
styles: [OPTION_BUYER]
scan: three_bar_streak
customer_default: false
```

```yaml
mix_id: MIX-RANGE-EXP
origin: PROJECT_MIX
origin_note: "Range expansion vs recent median range. Window UNKNOWN."
styles: [OPTION_BUYER]
scan: range_expansion
range_window: UNKNOWN
customer_default: false
```

```yaml
mix_id: MIX-CLOCK-CAS
origin: PROJECT_MIX
origin_note: "Founder overlay 2026-09-03: drop 09:00–09:30 and 15:00–15:30 IST (pre-open + CAS). Flatten session end. Not a STRAT. Applies to scan books. customer_default false."
styles: [OPTION_BUYER]
scan: dead_band_0900_0930_1500_1530
customer_default: false
```

```yaml
mix_id: MIX-ML-LOGIT
origin: PROJECT_MIX
origin_note: "Walk-forward logistic on INDEX 3m features. Train before 730d cutoff. Label = next INDEX close, not option premium. Not DHAN-DERIVED."
styles: [OPTION_BUYER]
scan: walk_forward_logit_index_direction
customer_default: false
```

```yaml
mix_id: MIX-ML-LOGIT-XR
origin: PROJECT_MIX
origin_note: "MIX-ML-LOGIT AND MIX-RANGE-EXP. Named before wr. Not a soup of prior 730d winners."
styles: [OPTION_BUYER]
scan: logit_and_range_expansion
customer_default: false
```

```yaml
mix_id: MIX-CLUB-EG
origin: PROJECT_MIX
origin_note: "ENGULF ∧ GAP after clock scan. Founder club of WEAK books. Not a promote."
styles: [OPTION_BUYER]
customer_default: false
```

```yaml
mix_id: MIX-CLUB-GR
origin: PROJECT_MIX
origin_note: "GAP ∧ RANGE-EXP. Optimistic 2y NIFTY 69.4% wr n=36 WEAK. After-cost 44.4% FAIL promote. KEEP + PAPER_WATCH in market hours. Not customer default."
styles: [OPTION_BUYER]
customer_default: false
paper_watch: true
paper_watch_doc: teams/04_quant/docs/PAPER_WATCH_CLUB_GR.md
recorded:
  optimistic_2026-09-03: {underlying: NIFTY, wr: 0.694, n: 36, rating: WEAK}
  after_cost_2026-09-06: {underlying: NIFTY, wr: 0.444, n: 36, rating: FAIL}
```

```yaml
mix_id: MIX-GRID-RSI
origin: PROJECT_MIX
origin_note: "Nested grid RSI_14 bands {(20,80),(25,75),(30,70)}. Lock on first 60% of 2y by IS exp. Annexure RSI_14 computed from OHLC — no HQ series REST."
styles: [OPTION_BUYER]
customer_default: false
```

### §9 SL/TP exit overlays (2026-09-06) — never STRAT-015+

Exit/level books. Entry lean may reuse `MIX-DEFAULT-BUY` / STRAT-003 stack. Metrics null until 06 scores. **Not** customer default.

```yaml
mix_id: MIX-SLTP-ATR-R2
origin: WEB-DERIVED
origin_note: "Classic Wilder ATR(14)×k stop from entry + R-multiple target (default R=2). Cite StockCharts/Wilder family. Not DHAN-DERIVED. Paper levels method_id when ATR seed exists."
styles: [OPTION_BUYER]
role: exit_overlay
atr_period: 14
atr_mult_grid: [1.0, 1.5, 2.0, 3.0]
rr_prefer: 2.0
customer_default: false
status: WAITING
```

```yaml
mix_id: MIX-SLTP-ST-FLIP
origin: DHAN-DERIVED
origin_note: "Teacher-faithful STRAT-003 exit: 3m close through Supertrend. Prefer RR 2.0 is ticket preference only — exit is ST flip, not fixed points."
styles: [OPTION_BUYER]
role: exit_overlay
attached: [STRAT-003]
customer_default: false
status: WAITING
```

```yaml
mix_id: MIX-SLTP-PREM-PCT
origin: DHAN-DERIVED
origin_note: "STRAT-002 premium target 20–30% of entry premium + swing stop. Overlay on STRAT-001 only — never silent on 003."
styles: [OPTION_BUYER]
role: exit_overlay
attached: [STRAT-001, STRAT-002]
not_attached: [STRAT-003]
customer_default: false
status: WAITING
```

```yaml
mix_id: MIX-SLTP-SWING
origin: DHAN-DERIVED
origin_note: "STRAT-001 underlying recent-swing stop. Lookback UNDERDEFINED — grid required."
styles: [OPTION_BUYER]
role: exit_overlay
customer_default: false
status: PARKED
```

```yaml
mix_id: MIX-DESK-IQ-ATR-RR2
origin: PROJECT_MIX
origin_note: |
  Own desk club 2026-09-06 from @iqcapital_io harvest (EXTERNAL transcripts) + computable ATR.
  SOURCE_FACT borrowed: (1) structure/invalidation stop language + OF timing (PL7LKUsCgIQ);
  (2) RR ≥ ~2 and dynamic option-wall targets (Hs_JmvWrLJw gamma interview);
  (3) VWAP as anchor (XWJlBBikUc0 / hxr27ckfOqA).
  PROJECT recipe: ENTRY = existing all_three VWAP/VWMA/ST lean (proxy — no NIFTY OF tape);
  STOP = ATR(14)×1.5 from entry (proxy for structure distance when OF absent);
  TARGET = R×2 from stop distance; GEX positive/negative = HOLD filter only — NIFTY GEX DATA_INSUFFICIENT.
  Transfer risk: US GEX ≠ NSE NIFTY 1:1. Not a promote. Not STRAT-015+.
styles: [OPTION_BUYER]
role: entry_plus_exit
entry_lean: MIX-DEFAULT-BUY_stack_proxy
exit: MIX-SLTP-ATR-R2
gex_filter: PARKED_DATA_INSUFFICIENT
customer_default: false
status: WAITING
paper_watch: false
docs:
  - teams/01_research/docs/SL_TP_EXTERNAL_HARVEST.md
  - teams/02_phd_math/docs/SL_TP_MATH_NOTES.md
  - teams/03_phd_market/docs/SL_TP_MARKET_NOTES.md
```

```yaml
mix_id: MIX-IQ-GEX-HOLD
origin: PROJECT_MIX
origin_note: "GEX regime hold-only from IQCapital gamma/OF interviews. No NIFTY GEX series → PARKED. Conflict stays as named MIX — do not delete."
styles: [OPTION_BUYER]
role: filter_hold
customer_default: false
status: PARKED
```

---

## 10. Chart Fanatics — Fabio Valentini (`MIX-CF-*` only)

**Bind:** [`../../01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md`](../../01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md)  
**Candidates:** [`candidates/MIX-CF-FABIO-TREND-NY.md`](candidates/MIX-CF-FABIO-TREND-NY.md), [`candidates/MIX-CF-FABIO-MR-RANGE.md`](candidates/MIX-CF-FABIO-MR-RANGE.md)  
**Do not** merge into `MIX-DEFAULT-BUY`, IQCapital SL/TP rows, or STRAT-001–014. **No STRAT-015+.**

```yaml
mix_id: MIX-CF-FABIO-TREND-NY
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics tvERE-Beu2U guest Fabio Valentini — New York imbalance / trend scalp.
  SOURCE_FACT: AMT out-of-balance + volume profile LVN + OF aggression bubbles + break/test;
  target prior POC/balance; PDH common first target; NQ ~20–40 contract filter.
  Teacher asset NQ futures. India OF/CVD/footprint DATA_INSUFFICIENT → status PARKED.
  OHLC structure proxies (failed auction / break-retest) = BACKTEST_BOOK only — not the guest trigger.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: PARKED
proxy_status: BACKTEST_BOOK
of_required: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-DESK-IQ-ATR-RR2]
docs:
  - teams/01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md
  - teams/02_phd_math/docs/CF_FABIO_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_FABIO_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-FABIO-MR-RANGE
origin: EXTERNAL_RESEARCH
origin_note: |
  Same video — distinct mean-revert / London-compression model (separate theme).
  SOURCE_FACT: balance/consolidation; first breakout then second swing back to POC;
  not opposite range extreme; OF aggression trigger; summer chop spoken.
  PARKED on OF; OHLC MR_TO_POC proxy BACKTEST_BOOK only.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: PARKED
proxy_status: BACKTEST_BOOK
of_required: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY]
docs:
  - teams/01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md
```

---

## 11. Chart Fanatics — Marco + Trader Mayne (`MIX-CF-MARCO-*` / `MIX-CF-MAYNE-*`)

**ASR caveat:** Phase-3B `ASR_WHISPER` / `[ASR]` — **not** YouTube captions.  
**Binds:** [`DAnXM7C16h0_BIND.md`](../../01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md), [`coBMd1vk2Lo_BIND.md`](../../01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md)  
**Candidates:** [`MIX-CF-MARCO-LIQ-TRAP.md`](candidates/MIX-CF-MARCO-LIQ-TRAP.md), [`MIX-CF-MARCO-INT-EXT.md`](candidates/MIX-CF-MARCO-INT-EXT.md), [`MIX-CF-MAYNE-ICT-HTF.md`](candidates/MIX-CF-MAYNE-ICT-HTF.md), [`MIX-CF-MAYNE-BREAKER.md`](candidates/MIX-CF-MAYNE-BREAKER.md)  
**Do not** merge into Fabio rows, `MIX-DEFAULT-BUY`, IQCapital SL/TP, STRAT-001–014, or each other. **No STRAT-015+.**

```yaml
mix_id: MIX-CF-MARCO-LIQ-TRAP
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics DAnXM7C16h0 guest Marco — liquidity trap.
  SOURCE_FACT: resting-stop liquidity after respect+move-away; buy below lows / sell above highs
  after take; retail BOS/OB/FVG as induce only; strict opposing-sweep wait.
  Teacher assets US futures/FX. ASR transcript. OHLC sweep-reclaim proxy = BACKTEST_BOOK.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-MAYNE-ICT-HTF]
docs:
  - teams/01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md
  - teams/02_phd_math/docs/CF_MARCO_MAYNE_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_MARCO_MAYNE_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-MARCO-INT-EXT
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Marco video — distinct internal→external + equal-high/low + NY session theme.
  SOURCE_FACT: enter after internal taken; target external; equal highs/lows pools;
  NY 9:30 focus; Asia/London often engineer liquidity.
  Session map NSE = DATA_INSUFFICIENT; equal-extreme OHLC proxy BACKTEST_BOOK.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-FABIO-TREND-NY]
docs:
  - teams/01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md
```

```yaml
mix_id: MIX-CF-MAYNE-ICT-HTF
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics coBMd1vk2Lo guest Trader Mayne — simplified ICT HTF bias.
  SOURCE_FACT: ≥2 TFs; 3-candle swings; close MSB; range + OB POI; ~50% premium/discount;
  draw external↔internal. Crypto/FX/futures spoken. ASR. MSB-discount OHLC proxy BACKTEST_BOOK.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-FABIO-TREND-NY, MIX-CF-MAYNE-BREAKER]
docs:
  - teams/01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md
  - teams/02_phd_math/docs/CF_MARCO_MAYNE_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_MARCO_MAYNE_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-MAYNE-BREAKER
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Mayne video — distinct LTF breaker entry theme.
  SOURCE_FACT: inside HTF POI; sweep engineered swing then close-break structure;
  stop beyond stop-run; min 2:1 RR guest rule; optional 2R de-risk; FVG sponsorship tell.
  Breaker OHLC proxy BACKTEST_BOOK — HTF OB gate often missing on single TF.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MAYNE-ICT-HTF, MIX-CF-MARCO-LIQ-TRAP]
docs:
  - teams/01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md
```

---

## 12. Chart Fanatics — Marci + Tori (`MIX-CF-MARCI-*` / `MIX-CF-TORI-*`)

**ASR caveat:** Phase-3C `ASR_WHISPER` / `[ASR]` — **not** YouTube captions.  
**Binds:** [`AVVM-FyewLg_BIND.md`](../../01_research/docs/chart_fanatics/AVVM-FyewLg_BIND.md), [`VTEQ2fhGLqE_BIND.md`](../../01_research/docs/chart_fanatics/VTEQ2fhGLqE_BIND.md)  
**Candidates:** [`MIX-CF-MARCI-RIZZY.md`](candidates/MIX-CF-MARCI-RIZZY.md), [`MIX-CF-MARCI-BB-REALITY.md`](candidates/MIX-CF-MARCI-BB-REALITY.md), [`MIX-CF-TORI-TL-BOUNCE.md`](candidates/MIX-CF-TORI-TL-BOUNCE.md), [`MIX-CF-TORI-TL-BREAK.md`](candidates/MIX-CF-TORI-TL-BREAK.md)  
**Do not** merge into Fabio/Marco/Mayne rows, `MIX-DEFAULT-BUY`, IQCapital SL/TP, STRAT-001–014, or each other. **No STRAT-015+.**

```yaml
mix_id: MIX-CF-MARCI-RIZZY
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics AVVM-FyewLg guest Marci Silfrain — little-rizzie measured move.
  SOURCE_FACT: drop→bounce→TL; measure extreme→TL; project next leg; close beyond TL invalidates;
  prefer early 1–2 rizies. Teacher assets US index/equity/BTC. ASR. OHLC dual-swing proxy BACKTEST_BOOK.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-TORI-TL-BREAK]
docs:
  - teams/01_research/docs/chart_fanatics/AVVM-FyewLg_BIND.md
  - teams/02_phd_math/docs/CF_MARCI_TORI_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_MARCI_TORI_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-MARCI-BB-REALITY
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Marci video — distinct Bollinger 2σ “reality” location / crash mid-reclaim theme.
  SOURCE_FACT: middle=reality; prefer early shorts near upper/mid BB; crash long via projected
  bottom or close above mid. BB mid-reclaim OHLC proxy BACKTEST_BOOK.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MARCI-RIZZY, MIX-CF-FABIO-TREND-NY]
docs:
  - teams/01_research/docs/chart_fanatics/AVVM-FyewLg_BIND.md
```

```yaml
mix_id: MIX-CF-TORI-TL-BOUNCE
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics VTEQ2fhGLqE guest Tori Trades — trendline bounce (action=safety).
  SOURCE_FACT: naked TL; 2–3 touches; ~week data on 4H; low risk at line; trail/exit on break.
  Commodity swing spoken. ASR. Swing-line bounce OHLC proxy BACKTEST_BOOK.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-TORI-TL-BREAK, MIX-CF-MARCI-RIZZY, MIX-CF-MAYNE-ICT-HTF]
docs:
  - teams/01_research/docs/chart_fanatics/VTEQ2fhGLqE_BIND.md
  - teams/02_phd_math/docs/CF_MARCI_TORI_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_MARCI_TORI_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-TORI-TL-BREAK
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Tori video — distinct trendline break theme (action ≠ opposing safety).
  SOURCE_FACT: need broken TL + opposing safety; 2-touch vs 3+ playbooks; skip far-from-safety;
  fan/top-down; no forced 4H close. Break+safety OHLC proxy BACKTEST_BOOK.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-TORI-TL-BOUNCE, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-MARCI-RIZZY]
docs:
  - teams/01_research/docs/chart_fanatics/VTEQ2fhGLqE_BIND.md
```

---

## 13. Chart Fanatics — TG Capital + Trader Kane (`MIX-CF-TG-*` / `MIX-CF-KANE-*`)

**ASR caveat:** Phase-3D `ASR_WHISPER` / `[ASR]` — **not** YouTube captions.  
**Binds:** [`ADnslyKOwFE_BIND.md`](../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md), [`HNuRp9Z1bMs_BIND.md`](../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md)  
**Candidates:** [`MIX-CF-TG-TRIDENT.md`](candidates/MIX-CF-TG-TRIDENT.md), [`MIX-CF-TG-EMA-WAVE.md`](candidates/MIX-CF-TG-EMA-WAVE.md), [`MIX-CF-KANE-EQ50.md`](candidates/MIX-CF-KANE-EQ50.md), [`MIX-CF-KANE-PO3-SMT.md`](candidates/MIX-CF-KANE-PO3-SMT.md)  
**Do not** merge into Fabio/Marco/Mayne/Marci/Tori rows, `MIX-DEFAULT-BUY`, IQCapital SL/TP, STRAT-001–014, or each other. **No STRAT-015+.** Title “90%” = marketing, not product metric.

```yaml
mix_id: MIX-CF-TG-TRIDENT
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics ADnslyKOwFE guest TG Capital / Tyler — London FVG trident entry.
  SOURCE_FACT: London KZ 3–6:30 NY; 30m FVG + doji at CE + confirm close below doji high;
  long-bias A+; min 1:20 personal. ASR. FVG+doji OHLC proxy BACKTEST_BOOK. London→NSE DI.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-TG-EMA-WAVE, MIX-CF-KANE-EQ50]
docs:
  - teams/01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md
  - teams/02_phd_math/docs/CF_TG_KANE_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_TG_KANE_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-TG-EMA-WAVE
origin: EXTERNAL_RESEARCH
origin_note: |
  Same TG video — distinct EMA stack / 200 EMA bias theme.
  SOURCE_FACT: 5/9/13|15/21 stacked wave; above 200 long bias; daily narrative.
  ASR mid-EMA 13 vs 15 UNKNOWN. EMA-stack OHLC proxy BACKTEST_BOOK.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-TG-TRIDENT, MIX-CF-FABIO-TREND-NY, MIX-CF-MAYNE-ICT-HTF]
docs:
  - teams/01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md
```

```yaml
mix_id: MIX-CF-KANE-EQ50
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics HNuRp9Z1bMs guest Trader Kane — 50% EQ base-hit.
  SOURCE_FACT: redeliver into ~50% of dealing range; take base hit not mandatory extreme;
  MM theory framing; not breakout retest. ASR. Mid-touch OHLC proxy BACKTEST_BOOK.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-KANE-PO3-SMT, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-TG-TRIDENT]
docs:
  - teams/01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md
  - teams/02_phd_math/docs/CF_TG_KANE_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_TG_KANE_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-KANE-PO3-SMT
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Kane video — distinct PO3 fractal + SMT/inversion entry theme.
  SOURCE_FACT: daily/H4/H1 AMD align; ~10AM EST manipulate; SMT NQ vs ES + inversion.
  ASR. Sweep-reclaim OHLC proxy BACKTEST_BOOK; true SMT = DATA_INSUFFICIENT on single NIFTY.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-KANE-EQ50, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-MAYNE-BREAKER]
docs:
  - teams/01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md
```

---

## 14. Chart Fanatics — Umar Ashraf + Forest Knight (`MIX-CF-UMAR-*` / `MIX-CF-FOREST-*`)

**ASR caveat:** Phase-3E `ASR_WHISPER` / `[ASR]` — **not** YouTube captions. Guest ASR “Buma Ashraf” = UNKNOWN garble → **Umar Ashraf**.  
**Binds:** [`IUo5AwmsE9A_BIND.md`](../../01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md), [`q_MdVlZ1SH4_BIND.md`](../../01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md)  
**Candidates:** [`MIX-CF-UMAR-MORNING-TOP.md`](candidates/MIX-CF-UMAR-MORNING-TOP.md), [`MIX-CF-UMAR-OPENING-DRIVE.md`](candidates/MIX-CF-UMAR-OPENING-DRIVE.md), [`MIX-CF-FOREST-VPE-EDGE.md`](candidates/MIX-CF-FOREST-VPE-EDGE.md), [`MIX-CF-FOREST-POC-RETEST.md`](candidates/MIX-CF-FOREST-POC-RETEST.md)  
**Do not** merge into Fabio/Marco/Mayne/Marci/Tori/TG/Kane rows, `MIX-DEFAULT-BUY`, IQCapital SL/TP, STRAT-001–014, or each other. **No STRAT-015+.** Rhetoric “100% react” / payout ads ≠ product metrics.

```yaml
mix_id: MIX-CF-UMAR-MORNING-TOP
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics IUo5AwmsE9A guest Umar Ashraf — morning top (gap-down fade).
  SOURCE_FACT: gap down; first ~5–60m; weak upside no follow-through → short.
  ASR. OF preferred by teacher; OHLC proxy BACKTEST_BOOK. ET→NSE DI.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-UMAR-OPENING-DRIVE, MIX-CF-FOREST-VPE-EDGE, MIX-CF-TG-TRIDENT, MIX-CF-KANE-EQ50]
docs:
  - teams/01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md
  - teams/02_phd_math/docs/CF_UMAR_FOREST_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_UMAR_FOREST_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-UMAR-OPENING-DRIVE
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Umar video — opening drive named only; OF deep-dive deferred.
  SOURCE_FACT: playbook name exists; entry rules DATA_INSUFFICIENT this transcript.
  Do not invent ORB from other guests.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-UMAR-MORNING-TOP, MIX-CF-FABIO-TREND-NY]
docs:
  - teams/01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md
```

```yaml
mix_id: MIX-CF-FOREST-VPE-EDGE
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics q_MdVlZ1SH4 guest Forest Knight — VPE edge + relative-volume signal candle.
  SOURCE_FACT: PDH/PDL/ONH/ONL + HVN edge; vol>prior + doji/hammer/star; wait for close; edge-to-edge TP.
  ASR. PDH/PDL+relvol OHLC proxy BACKTEST_BOOK; overnight + true VAP = DI.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FOREST-POC-RETEST, MIX-CF-FABIO-MR-RANGE, MIX-CF-UMAR-MORNING-TOP]
docs:
  - teams/01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md
  - teams/02_phd_math/docs/CF_UMAR_FOREST_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_UMAR_FOREST_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-FOREST-POC-RETEST
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Forest video — distinct prior POC / VAL retest theme.
  SOURCE_FACT: uptrend pullback to prior POC or VAL; TP highs / next shelf.
  ASR. PROJECT bin POC/VAL proxy BACKTEST_BOOK — not exchange VAP.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FOREST-VPE-EDGE, MIX-CF-KANE-EQ50, MIX-CF-FABIO-MR-RANGE]
docs:
  - teams/01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md
```

---

## 15. Chart Fanatics — Carmine Rosato + Jadecap (`MIX-CF-CARMINE-*` / `MIX-CF-JADECAP-*`)

**ASR caveat:** Phase-3F `ASR_WHISPER` / `[ASR]` — **not** YouTube captions.  
**Binds:** [`UhkRRqO1gQM_BIND.md`](../../01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md), [`8OX-mcSHWhg_BIND.md`](../../01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md)  
**Candidates:** [`MIX-CF-CARMINE-ABSORB.md`](candidates/MIX-CF-CARMINE-ABSORB.md), [`MIX-CF-CARMINE-FAIL-BREAK.md`](candidates/MIX-CF-CARMINE-FAIL-BREAK.md), [`MIX-CF-CARMINE-OPEN-HOLD.md`](candidates/MIX-CF-CARMINE-OPEN-HOLD.md), [`MIX-CF-JADECAP-SWING-FAIL.md`](candidates/MIX-CF-JADECAP-SWING-FAIL.md), [`MIX-CF-JADECAP-SESSION-LIQ.md`](candidates/MIX-CF-JADECAP-SESSION-LIQ.md), [`MIX-CF-JADECAP-FVG-DRAW.md`](candidates/MIX-CF-JADECAP-FVG-DRAW.md)  
**Do not** merge into prior CF guests, `MIX-DEFAULT-BUY`, IQCapital SL/TP, STRAT-001–014, or each other. **No STRAT-015+.** Dollar P/L / Apex payout ads ≠ product metrics. True OF absorb + Asia/London sessions = DI/PARKED.

```yaml
mix_id: MIX-CF-CARMINE-ABSORB
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics UhkRRqO1gQM guest Carmine Rosato — absorption at LOI (aggressors, no follow-through).
  SOURCE_FACT: CLC + DOM/heatmap/footprint. ASR. True OF required — PARKED / DATA_INSUFFICIENT without India tape.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: true
of_parked: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-CARMINE-OPEN-HOLD, MIX-CF-FABIO-TREND-NY]
docs:
  - teams/01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md
  - teams/02_phd_math/docs/CF_CARMINE_JADECAP_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_CARMINE_JADECAP_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-CARMINE-FAIL-BREAK
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Carmine video — stop-hunt / failed breakdown (sweep extreme + reclaim).
  SOURCE_FACT: consolidate near low/high; sweep; reclaim. OF preferred; OHLC PDH/PDL proxy BACKTEST_BOOK.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-CARMINE-ABSORB, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-JADECAP-SWING-FAIL]
docs:
  - teams/01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md
  - teams/02_phd_math/docs/CF_CARMINE_JADECAP_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_CARMINE_JADECAP_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-CARMINE-OPEN-HOLD
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Carmine video — hold opening print on early pullback (aggression without follow-through).
  SOURCE_FACT: hold open; tight stop; nearby magnet TP. ASR. OHLC open-hold proxy BACKTEST_BOOK; ET→NSE DI.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-CARMINE-ABSORB, MIX-CF-UMAR-MORNING-TOP]
docs:
  - teams/01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md
```

```yaml
mix_id: MIX-CF-JADECAP-SWING-FAIL
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics 8OX-mcSHWhg guest Jadecap — PDH/PDL swing failure (raid + close reclaim).
  SOURCE_FACT: wait for close back; SL beyond new extreme; TP opposing PDH/PDL. ASR. OHLC proxy BACKTEST_BOOK.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-JADECAP-SESSION-LIQ, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-MARCO-LIQ-TRAP]
docs:
  - teams/01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md
  - teams/02_phd_math/docs/CF_CARMINE_JADECAP_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_CARMINE_JADECAP_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-JADECAP-SESSION-LIQ
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Jadecap video — Asia/London session liquidity before NY; midnight open multiples.
  SOURCE_FACT: prefer session low taken on bull day; both sides taken → consolidation lean.
  Asia/London/NY → NSE = DATA_INSUFFICIENT. Do not invent session boxes.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-FABIO-TREND-NY]
docs:
  - teams/01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md
```

```yaml
mix_id: MIX-CF-JADECAP-FVG-DRAW
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Jadecap video — distinct draw: liquidity taken → inefficiency (FVG primary).
  SOURCE_FACT: daily thesis; LTF FVG/MSS/turtle soup/breaker; his reps mostly FVG.
  ASR. 3-candle FVG-after-sweep OHLC proxy BACKTEST_BOOK — full ICT stack not frozen.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-TG-TRIDENT, MIX-CF-MAYNE-ICT-HTF]
docs:
  - teams/01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md
```

---

## 16. Chart Fanatics — Usman Ashraf + Brando/Leaf (`MIX-CF-USMAN-*` / `MIX-CF-BRANDO-*`)

**ASR caveat:** Phase-3G `ASR_WHISPER` / `[ASR]` — **not** YouTube captions. Guest ASR “Osman Astra” → **Usman Ashraf**; “brand-a-k-a-leaf” → **Brando / Leaf**.  
**Binds:** [`6Bdv-_YUQ0s_BIND.md`](../../01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md), [`yLuH8YZXORQ_BIND.md`](../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md)  
**Candidates:** [`MIX-CF-USMAN-OI-STRIKE.md`](candidates/MIX-CF-USMAN-OI-STRIKE.md), [`MIX-CF-USMAN-0DTE-GAMMA.md`](candidates/MIX-CF-USMAN-0DTE-GAMMA.md), [`MIX-CF-USMAN-WEEKLY-SIZE.md`](candidates/MIX-CF-USMAN-WEEKLY-SIZE.md), [`MIX-CF-USMAN-PRICE-STOP.md`](candidates/MIX-CF-USMAN-PRICE-STOP.md), [`MIX-CF-BRANDO-HTF-RECLAIM.md`](candidates/MIX-CF-BRANDO-HTF-RECLAIM.md), [`MIX-CF-BRANDO-ROUND-BREAK.md`](candidates/MIX-CF-BRANDO-ROUND-BREAK.md), [`MIX-CF-BRANDO-HTF-BOUNCE.md`](candidates/MIX-CF-BRANDO-HTF-BOUNCE.md), [`MIX-CF-BRANDO-SIZE-ZERO.md`](candidates/MIX-CF-BRANDO-SIZE-ZERO.md), [`MIX-CF-BRANDO-NEWS-ALIGN.md`](candidates/MIX-CF-BRANDO-NEWS-ALIGN.md)  
**Do not** merge into prior CF guests, `MIX-DEFAULT-BUY`, IQCapital SL/TP, STRAT-001–014, or each other. **No STRAT-015+.** Title $6k→$10M / “80%” / seven-figure rhetoric ≠ product metrics. US 0DTE/weeklies ≠ NIFTY weekly auto. Usman price-stop vs Brando size-zero = KEEP_ALL conflict rows.

```yaml
mix_id: MIX-CF-USMAN-OI-STRIKE
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics 6Bdv-_YUQ0s guest Usman Ashraf — strike pick by chain OI/volume liquidity.
  SOURCE_FACT: morning OI availability; avoid thin OI vs size; direction still needs chart.
  ASR. OPTIDX OI book = DATA_INSUFFICIENT. Do not invent OI from INDEX OHLC.
styles: [OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
optidx_oi_required: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-USMAN-0DTE-GAMMA, MIX-CF-BRANDO-HTF-RECLAIM]
docs:
  - teams/01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md
  - teams/02_phd_math/docs/CF_USMAN_BRANDO_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_USMAN_BRANDO_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-USMAN-0DTE-GAMMA
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Usman video — 0DTE / near-expiry gamma + IV for premium velocity.
  SOURCE_FACT: delta/gamma/IV; SPY/SPX 0DTE; Fri weekly de-facto 0DTE. ASR.
  Greeks + US→NSE expiry map = DATA_INSUFFICIENT. Not auto NIFTY weekly.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
greeks_required: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-USMAN-OI-STRIKE, MIX-CF-USMAN-WEEKLY-SIZE]
docs:
  - teams/01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md
```

```yaml
mix_id: MIX-CF-USMAN-WEEKLY-SIZE
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Usman video — weekly Mon–Wed vs Thu/Fri position size by theta.
  SOURCE_FACT: size down into Fri so $ risk matches; chart still required.
  Management / premium% = DATA_INSUFFICIENT as INDEX entry.
styles: [OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
management_only: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-USMAN-PRICE-STOP, MIX-CF-BRANDO-SIZE-ZERO]
docs:
  - teams/01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md
```

```yaml
mix_id: MIX-CF-USMAN-PRICE-STOP
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Usman video — stops on underlying price/levels; scale 30/20/20/30; reject size-to-zero for him.
  SOURCE_FACT: premium% stops can false-out on sideways. Entry LOI not frozen → DI.
  KEEP_ALL conflict vs MIX-CF-BRANDO-SIZE-ZERO.
styles: [OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
management_only: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-BRANDO-SIZE-ZERO, MIX-DESK-IQ-ATR-RR2]
docs:
  - teams/01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md
```

```yaml
mix_id: MIX-CF-BRANDO-HTF-RECLAIM
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics yLuH8YZXORQ guest Brando/Leaf — HTF major-level reclaim → buy calls.
  SOURCE_FACT: daily/weekly majors; reclaim after selloff; react. ASR.
  Multi-day swing reclaim OHLC proxy BACKTEST_BOOK; multi-year SPX majors not modeled.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-BRANDO-ROUND-BREAK, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-USMAN-OI-STRIKE]
docs:
  - teams/01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md
  - teams/02_phd_math/docs/CF_USMAN_BRANDO_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_USMAN_BRANDO_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-BRANDO-ROUND-BREAK
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Brando video — round-number break (news preferred).
  SOURCE_FACT: SPX 6000 puts example; catalyst align. ASR.
  Round100 OHLC proxy BACKTEST_BOOK; news join = separate DI row.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
news_teacher_preferred: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-BRANDO-HTF-RECLAIM, MIX-CF-BRANDO-NEWS-ALIGN, MIX-CF-TORI-TL-BREAK]
docs:
  - teams/01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md
```

```yaml
mix_id: MIX-CF-BRANDO-HTF-BOUNCE
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Brando video — HTF level defend / quick bounce (+ gap-fill bounce mention).
  SOURCE_FACT: major level should bounce fairly quickly. ASR.
  Swing touch+reject OHLC proxy BACKTEST_BOOK — separate from Tori TL-bounce.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-BRANDO-HTF-RECLAIM, MIX-CF-TORI-TL-BOUNCE, MIX-CF-KANE-EQ50]
docs:
  - teams/01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md
```

```yaml
mix_id: MIX-CF-BRANDO-SIZE-ZERO
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Brando video — size-for-zero on options (max risk = premium).
  SOURCE_FACT: not for shares; rejects tight 20% premium stops. ASR.
  OPTIDX premium ledger = DATA_INSUFFICIENT. KEEP_ALL vs MIX-CF-USMAN-PRICE-STOP.
styles: [OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
management_only: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-USMAN-PRICE-STOP, MIX-CF-USMAN-WEEKLY-SIZE]
docs:
  - teams/01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md
```

```yaml
mix_id: MIX-CF-BRANDO-NEWS-ALIGN
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Brando video — align HTF level with news/data catalyst (Fed/tariffs/sentiment).
  SOURCE_FACT: breakout without catalyst weaker. ASR.
  India news join = DATA_INSUFFICIENT. Do not invent headlines.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
news_required: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-BRANDO-ROUND-BREAK, MIX-CF-BRANDO-HTF-RECLAIM]
docs:
  - teams/01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md
```

---

## 17. Chart Fanatics — Andrea Cimi + Omor/NBB (`MIX-CF-ANDREA-*` / `MIX-CF-OMOR-*`)

**ASR caveat:** Phase-3H `ASR_WHISPER` / `[ASR]` — **not** YouTube captions. Guest ASR “Andrea Chimney” → **Andrea Cimi**; “Omore aka MBB” → **Omor / NBB Trader**. Inventory stub for `TvoQr6ObjnU` wrongly said Fabio — **Fabio is mentor only**; do **not** merge into `MIX-CF-FABIO-*`.  
**Binds:** [`TvoQr6ObjnU_BIND.md`](../../01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md), [`IB-fyWI5j8w_BIND.md`](../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md)  
**Candidates:** [`MIX-CF-ANDREA-FAIL-AUCTION.md`](candidates/MIX-CF-ANDREA-FAIL-AUCTION.md), [`MIX-CF-ANDREA-ORB-ACCEPT.md`](candidates/MIX-CF-ANDREA-ORB-ACCEPT.md), [`MIX-CF-ANDREA-STOP-FADE.md`](candidates/MIX-CF-ANDREA-STOP-FADE.md), [`MIX-CF-ANDREA-ABSORB.md`](candidates/MIX-CF-ANDREA-ABSORB.md), [`MIX-CF-OMOR-MMM-FRAME.md`](candidates/MIX-CF-OMOR-MMM-FRAME.md), [`MIX-CF-OMOR-OTE.md`](candidates/MIX-CF-OMOR-OTE.md), [`MIX-CF-OMOR-PDH-REVERSAL.md`](candidates/MIX-CF-OMOR-PDH-REVERSAL.md), [`MIX-CF-OMOR-KZ-ADR.md`](candidates/MIX-CF-OMOR-KZ-ADR.md)  
**Do not** merge into prior CF guests (incl. Fabio), `MIX-DEFAULT-BUY`, IQCapital SL/TP, STRAT-001–014, or each other. **No STRAT-015+.** Live $ / “70%” VA / “8/10” fade / 30M+1.1M payout rhetoric ≠ product metrics. Andrea OF absorb PARKED; Omor KZ/ADR DI.

```yaml
mix_id: MIX-CF-ANDREA-FAIL-AUCTION
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics TvoQr6ObjnU guest Andrea Cimi — failed auction at value / VA ping-pong.
  SOURCE_FACT: probe outside VA; absorb+initiative; target opposite VA; OF preferred.
  ASR. Prior-day range reclaim OHLC proxy BACKTEST_BOOK; true VP/OF DI.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-FABIO-MR-RANGE, MIX-CF-ANDREA-ORB-ACCEPT, MIX-CF-CARMINE-FAIL-BREAK]
docs:
  - teams/01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md
  - teams/02_phd_math/docs/CF_ANDREA_OMOR_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_ANDREA_OMOR_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-ANDREA-ORB-ACCEPT
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Andrea video — ORB with OF acceptance (not wick absorption).
  SOURCE_FACT: early OR; break only when aggressors accept outside; may anticipate with bubbles.
  ASR. IST OR hold OHLC proxy BACKTEST_BOOK; NY→NSE clock DI.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-ANDREA-FAIL-AUCTION, MIX-CF-UMAR-OPENING-DRIVE]
docs:
  - teams/01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md
```

```yaml
mix_id: MIX-CF-ANDREA-STOP-FADE
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Andrea video — stop-run book-resilience fade (short-term; not full-day reverse).
  SOURCE_FACT: PDH/PDL stop cascade; fade emptied book; OF distinguishes absorb vs stop-run.
  ASR. PDH/PDL quick fade OHLC proxy BACKTEST_BOOK. “8/10” anecdote null metrics.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-ANDREA-FAIL-AUCTION, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-MARCO-LIQ-TRAP]
docs:
  - teams/01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md
```

```yaml
mix_id: MIX-CF-ANDREA-ABSORB
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Andrea video — true footprint/DOM/bubble absorption filter.
  SOURCE_FACT: Deep Charts bubbles (ES ≥150 ex.); heatmap; distinguishes stop-run vs absorb.
  ASR. OF required — PARKED / DATA_INSUFFICIENT without India tape. Not Fabio MIX.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: true
of_parked: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-ANDREA-FAIL-AUCTION, MIX-CF-CARMINE-ABSORB, MIX-CF-FABIO-TREND-NY]
docs:
  - teams/01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md
  - teams/02_phd_math/docs/CF_ANDREA_OMOR_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_ANDREA_OMOR_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-OMOR-MMM-FRAME
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics IB-fyWI5j8w guest Omor/NBB — Market Maker Model / PO3 FRAMEWORK (not entry).
  SOURCE_FACT: HTF PD arrays; AMD; SMR/breaker + displacement; bias-predetermined.
  ASR. Bias+PDH/PDL sweep+displace OHLC proxy BACKTEST_BOOK. Separate from Mayne/Kane/Jade.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OMOR-OTE, MIX-CF-MAYNE-ICT-HTF, MIX-CF-KANE-PO3-SMT, MIX-CF-JADECAP-FVG-DRAW]
docs:
  - teams/01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md
  - teams/02_phd_math/docs/CF_ANDREA_OMOR_MATH_NOTES.md
  - teams/03_phd_market/docs/CF_ANDREA_OMOR_MARKET_NOTES.md
```

```yaml
mix_id: MIX-CF-OMOR-OTE
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Omor video — Optimal Trade Entry fib (~0.62) on distribution swing.
  SOURCE_FACT: graded swing; 62% entry; SL at 1 / refine 0.9; TP at 0; first leg often ≤50%.
  ASR. Fib62 OHLC proxy BACKTEST_BOOK. RR podcast numbers null metrics.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OMOR-MMM-FRAME, MIX-CF-KANE-EQ50, MIX-CF-MAYNE-BREAKER]
docs:
  - teams/01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md
```

```yaml
mix_id: MIX-CF-OMOR-PDH-REVERSAL
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Omor video — open near PDH/PDL then sweep reverse (sell/buy day template).
  SOURCE_FACT: patience for open-near key level; manipulation then reverse with bias.
  ASR. Open-near+sweep OHLC proxy BACKTEST_BOOK; Asia/London profile missing.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OMOR-MMM-FRAME, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-CARMINE-FAIL-BREAK]
docs:
  - teams/01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md
```

```yaml
mix_id: MIX-CF-OMOR-KZ-ADR
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Omor video — London/NY/London-close killzones + ADR(5) remaining range.
  SOURCE_FACT: session profiling; skip when ADR spent. ASR clocks inconsistent.
  London/NY → NSE = DATA_INSUFFICIENT. Do not invent IST boxes.
styles: [POSITION, OPTION_BUYER]
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OMOR-MMM-FRAME, MIX-CF-TG-TRIDENT, MIX-CF-JADECAP-SESSION-LIQ]
docs:
  - teams/01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md
```

---

## 18. Chart Fanatics — Okala (`MIX-CF-OKALA-*`)

**ASR caveat:** Phase-3J `ASR_WHISPER` / `[ASR]` — **not** YouTube captions. Guest ASR “O'Cala” / “a call” → **Okala** (description / Twitter `OkalaNQT`).  
**Bind:** [`jsUTbjwpFVk_BIND.md`](../../01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md)  
**Candidates:** [`MIX-CF-OKALA-8020-LEVEL.md`](candidates/MIX-CF-OKALA-8020-LEVEL.md), [`MIX-CF-OKALA-FORK.md`](candidates/MIX-CF-OKALA-FORK.md), [`MIX-CF-OKALA-H-CROSS.md`](candidates/MIX-CF-OKALA-H-CROSS.md), [`MIX-CF-OKALA-REPAIR.md`](candidates/MIX-CF-OKALA-REPAIR.md)  
**Do not** merge into prior CF guests, `MIX-DEFAULT-BUY`, IQCapital SL/TP, STRAT-001–014, or each other. **No STRAT-015+.**  
**Title “65% WR” / host “70%” / guest “mid to low 70s” = marketing / self-report CLAIMS only** — `win_rate=null`. **NO_PROMOTE.**  
**Magnet honesty (founder 2026-09-07 + BIND rev):** `magnet_modulus=observable|searchable` — 80/20 are **observations**, not sacred core.  
**Market scope:** `teacher_examples=NQ` · `portable_if_magnets_observed=HYPOTHESIS` — India = separate adaptation MIX later (not auto-inherit; not forbidden forever).  
**Miss/recovery:** BIND captures ASR no-chase + next-magnet / H-continuation paths; BT grid searchable.  
**OpenAI suggest:** `data/recon/CF_OPENAI_OKALA_BIND_SUGGEST_2026-09-07.md` = HYPOTHESIS aid only — does **not** fix win rates.  
**Evaluator:** sibling CF×8 runners do **not** include Okala teacher NQ books. **India adaptation BT (2026-09-07):** `python -m backtest_engine okala-in` → `MIX-CF-OKALA-IN-*` grid on local INDEX OHLC — **HYPOTHESIS port** / **VALIDATION WR only** / **NO_PROMOTE** (see §18b). Teacher catalog rows stay `win_rate: null`.

```yaml
mix_id: MIX-CF-OKALA-8020-LEVEL
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics jsUTbjwpFVk guest Okala — observed-magnet mean-reversion (NQ seed xx80/xx20).
  SOURCE_FACT: magnets noticed on NQ; reaction+structure; 10m+200s; 10pt SL / ~15 TP1 / BE; NY open prefer; no OF/indicators.
  miss/recovery + magnet observation protocol + BT search grid in BIND (rev 2026-09-07).
  magnet_modulus=observable|searchable · market_scope=teacher_examples_NQ;portability=observation_gated · win_rate=null · NO_PROMOTE.
  ASR. India digit map = separate adaptation MIX-CF-OKALA-IN-* (PROJECT_MIX port; not auto-inherit). Catalog win_rate null.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: WAITING
of_required: false
asr_caveat: true
evaluator_bound: false
magnet_modulus: observable|searchable
market_scope: teacher_examples_NQ;portability=observation_gated
win_rate: null
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-OMOR-PDH-REVERSAL, MIX-CF-OKALA-FORK, MIX-DESK-IQ-ATR-RR2, MIX-CF-OKALA-IN-LEVEL]
docs:
  - teams/01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md
```

```yaml
mix_id: MIX-CF-OKALA-FORK
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Okala video — fork mean-reversion long after capitulation.
  SOURCE_FACT: test prior low without break on 200s; 10/15 risk; confluence with levels/repair; late-short cleanup.
  magnet_modulus=observable|searchable · market_scope=teacher_examples_NQ;portability=observation_gated · win_rate=null · NO_PROMOTE.
  ASR. India port = MIX-CF-OKALA-IN-FORK (not in CF×8).
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: WAITING
of_required: false
asr_caveat: true
evaluator_bound: false
magnet_modulus: observable|searchable
market_scope: teacher_examples_NQ;portability=observation_gated
win_rate: null
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OKALA-8020-LEVEL, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-OKALA-IN-FORK]
docs:
  - teams/01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md
```

```yaml
mix_id: MIX-CF-OKALA-H-CROSS
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Okala video — lowercase-H structure + cross-section short continuation.
  SOURCE_FACT: bounce 20→80; H rollover; retest cross (±80); 10/15; not blind short 80; miss-long recovery path.
  magnet_modulus=observable|searchable · market_scope=teacher_examples_NQ;portability=observation_gated · win_rate=null · NO_PROMOTE.
  ASR. India port = MIX-CF-OKALA-IN-H-CROSS. Exact cross geometry remains underdefined.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: WAITING
of_required: false
asr_caveat: true
evaluator_bound: false
magnet_modulus: observable|searchable
market_scope: teacher_examples_NQ;portability=observation_gated
win_rate: null
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OKALA-8020-LEVEL, MIX-CF-OKALA-FORK, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-OKALA-IN-H-CROSS]
docs:
  - teams/01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md
```

```yaml
mix_id: MIX-CF-OKALA-REPAIR
origin: EXTERNAL_RESEARCH
origin_note: |
  Same Okala video — repair / no-wick magnet (target + confluence, not blind entry).
  SOURCE_FACT: body-open no wick = unfilled participation magnet until touched.
  magnet_modulus=observable|searchable · market_scope=teacher_examples_NQ;portability=observation_gated · win_rate=null · NO_PROMOTE.
  ASR. India port = MIX-CF-OKALA-IN-REPAIR (confluence gate only).
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
proxy_status: DATA_INSUFFICIENT
of_required: false
asr_caveat: true
evaluator_bound: false
magnet_modulus: observable|searchable
market_scope: teacher_examples_NQ;portability=observation_gated
win_rate: null
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OKALA-8020-LEVEL, MIX-CF-OKALA-FORK, MIX-CF-OKALA-H-CROSS, MIX-CF-OKALA-IN-REPAIR]
docs:
  - teams/01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md
```

---

## 18b. Chart Fanatics — Okala India adaptation (`MIX-CF-OKALA-IN-*`)

**Date:** 2026-09-07 (rev: **FOUNDER_PAPER_ACCEPT** paper CE/PE notify)  
**Origin:** `PROJECT_MIX` / observation-gated port of §18 teacher book — **not** NQ identity; **not** `DHAN-DERIVED`; **not** STRAT-015+.  
**Bind:** [`jsUTbjwpFVk_BIND.md`](../../01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md)  
**Runner:** `python -m backtest_engine okala-in` · package `packages/backtest` (`okala_in_proxy.py`, `run_okala_in.py`)  
**Paper detector:** `backtest_engine.okala_in_paper` → wired in `live_signals.PaperSignalEngine` + `paper_evaluators` (`okala_in_paper` bind)  
**Artifacts:** `data/recon/OKALA_IN_BACKTEST_2026-09-07.md` + `.json` · enable note [`OKALA_IN_PAPER_SIGNAL_ENABLE_2026-09-07.md`](../../../data/recon/OKALA_IN_PAPER_SIGNAL_ENABLE_2026-09-07.md)  
**Honesty:** India BT is **HYPOTHESIS adaptation**. WR cells = **VALIDATION** research only. Catalog `win_rate: null`. **NO_PROMOTE** live.  
**Founder accept (PAPER only):** cells with **robust WR > 50%** and **n ≥ 20** are a **starter** for generating **PAPER** buy CE/PE notifies. Optimize next quarter. Still **UNVALIDATED** for live. Do **not** flip `RESEARCH_READY_FOR_PROGRAMMING`. Do **not** treat cell WR as product marketing.

### Paper-eligible cells (recon 2026-09-07 · wr_robust > 0.50 · n≥20)

| Cell | MIX | n | wr_robust |
|------|-----|---|-----------|
| `NIFTY\|1m\|bearish\|30:40\|H_CROSS` | `MIX-CF-OKALA-IN-H-CROSS` | 87 | 59.5% |
| `NIFTY\|1m\|choppy\|10:0\|H_CROSS` | `MIX-CF-OKALA-IN-H-CROSS` | 252 | 51.1% |
| `NIFTY\|1m\|sideways\|30:80\|H_CROSS` | `MIX-CF-OKALA-IN-H-CROSS` | 125 | 50.8% |
| `NIFTY\|5m\|sideways\|60:50\|REPAIR` | `MIX-CF-OKALA-IN-REPAIR` | 285 | 50.2% |

Runtime rule (same gate): any future recon cell with `wr_robust > 0.50` and `n ≥ 20` is paper-eligible. BANKNIFTY had **no** cells above the gate in this run — detector still watches BN, emits only if a cell qualifies.  
CE vs PE: pattern lean from coded rules (H_CROSS → PE; FORK → CE; LEVEL/REPAIR → long-residue CE / short-residue PE). BIG_NEWS mid-session still holds.

```yaml
mix_id: MIX-CF-OKALA-IN-LEVEL
origin: PROJECT_MIX
origin_note: |
  India INDEX adaptation of MIX-CF-OKALA-8020-LEVEL.
  Magnet residues searchable (seed 20260907; 10 pairs; 80/20 not fixed).
  ATR-scaled SL/TP from NQ 10/15 (HYPOTHESIS). Regimes: ADX+SMA slope+Kaufman ER.
  Unit: INDEX points proxy ≠ option premium. NO_PROMOTE live.
  FOUNDER_PAPER_ACCEPT: paper_enable when robust WR>50% cell matches; starter only.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: PAPER_WATCH
proxy_status: BACKTEST_BOOK
paper_enable: true
founder_paper_accept: true
evaluator_bound: true
evaluator: backtest_engine.okala_in_paper
win_rate: null
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
promote: false
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OKALA-8020-LEVEL, STRAT-001, STRAT-003]
docs:
  - teams/01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md
  - data/recon/OKALA_IN_BACKTEST_2026-09-07.md
  - data/recon/OKALA_IN_PAPER_SIGNAL_ENABLE_2026-09-07.md
```

```yaml
mix_id: MIX-CF-OKALA-IN-FORK
origin: PROJECT_MIX
origin_note: |
  India fork long proxy — FOUNDER_PAPER_ACCEPT when robust cell qualifies.
  No eligible FORK cell in 2026-09-07 recon (gate wr_robust>50%). NO_PROMOTE.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: PAPER_WATCH
paper_enable: true
founder_paper_accept: true
win_rate: null
promote: false
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OKALA-FORK]
```

```yaml
mix_id: MIX-CF-OKALA-IN-H-CROSS
origin: PROJECT_MIX
origin_note: |
  India H+cross short stand-in — three NIFTY 1m cells FOUNDER_PAPER_ACCEPT.
  Exact cross geometry still underdefined. NO_PROMOTE live.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: PAPER_WATCH
paper_enable: true
founder_paper_accept: true
win_rate: null
promote: false
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OKALA-H-CROSS]
```

```yaml
mix_id: MIX-CF-OKALA-IN-REPAIR
origin: PROJECT_MIX
origin_note: |
  LEVEL + repair confluence — NIFTY 5m sideways 60:50 cell FOUNDER_PAPER_ACCEPT.
  Not blind repair entry. NO_PROMOTE live.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: PAPER_WATCH
paper_enable: true
founder_paper_accept: true
win_rate: null
promote: false
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OKALA-REPAIR]
```

### HANDOFF (04 · founder paper accept)

**Accepted:** Paper-enable `MIX-CF-OKALA-IN-*` for robust WR>50% / n≥20 cells as **FOUNDER_PAPER_ACCEPT** starter CE/PE notify; detector reuse of `okala_in_proxy`; BIG_NEWS still holds; catalog `win_rate=null`; optimize next quarter.  
**Rejected:** Live promote; `/alerts/orders`; flipping `RESEARCH_READY_FOR_PROGRAMMING`; claiming 09 five-pass; marketing cell WR as product; STRAT-015+; merging into `MIX-DEFAULT-BUY`.  
**UNKNOWN / DATA_INSUFFICIENT:** BANKNIFTY paper cells (none above gate this run); premium bind when chain missing (directional intent + DI on levels); next-quarter retune.  
**NO_PROMOTE.**

---

## 18c. Chart Fanatics — OpenAI BIND + India overnight rollup (`MIX-CF-*-IN-*`)

**Date:** 2026-09-07 (workstream C)  
**Scope:** All usable CF transcripts (**yes=18**): OpenAI suggest → BIND refresh → India `MIX-*-IN-*` where portable.  
**OpenAI batch:** `data/recon/CF_OPENAI_BATCH_STATUS_2026-09-07.json` — **ok=17** / **fail=0** (Okala suggest already existed).  
**Skips:** [`data/recon/CF_OVERNIGHT_SKIPS_2026-09-07.md`](../../../data/recon/CF_OVERNIGHT_SKIPS_2026-09-07.md) — hard **SKIP** = Tori TL geometry (no India options wrapper); others **PARTIAL** (OHLC proxy OK; OF-native PARKED).  
**Scripts:** `scripts/cf_openai_bind_batch.py` · `scripts/cf_openai_materialize.py`  
**Runners:** primary `python -m backtest_engine cf-overnight` · Okala unchanged `okala-in` · sibling probe `backtest_engine.cf_india_proxy` (**does not rewrite** `okala_in_proxy`)  
**Honesty:** observation-gated levels; miss/recovery in BINDs; teacher WR claims null; catalog `win_rate=null`; soft news veto stays parked; **NO_PROMOTE**; no STRAT-015+.

Representative India adaptation MIX ids (full set under `teams/04_quant/docs/candidates/MIX-CF-*-IN-*.md`):

| Family | Example IN MIX | Decision |
|--------|----------------|----------|
| Fabio | `MIX-CF-FABIO-IN-TREND-OHLC` / `MIX-CF-FABIO-IN-MR-OHLC` | PARTIAL |
| Marco | `MIX-CF-MARCO-IN-01`…`03` | PARTIAL |
| Mayne | `MIX-CF-MAYNE-IN-OHLC-03` | PARTIAL |
| Marci | `MIX-CF-MARCI-IN-RIZZY-NIFTY` | PARTIAL |
| Tori | — | **SKIP** |
| TG / Kane | `MIX-CF-TG-IN-*` / `MIX-CF-KANE-IN-*` | PARTIAL |
| Umar / Forest | `MIX-CF-UMAR-IN-*` / `MIX-CF-FOREST-IN-*` | PARTIAL |
| Carmine / Jade | `MIX-CF-CARMINE-IN-*` / `MIX-CF-JADECAP-IN-*` | PARTIAL |
| Usman / Brando | `MIX-CF-USMAN-IN-*` / `MIX-CF-BRANDO-IN-*` | PARTIAL |
| Andrea / Omor | `MIX-CF-ANDREA-*-IN-*` / `MIX-CF-OMOR-*-IN-*` | PARTIAL |
| Okala | `MIX-CF-OKALA-IN-*` (§18b) | PORT (prior) |
| Yush | `MIX-CF-YUSH-IN-*` (§18d) | PARTIAL |
| Marco DaVinci | `MIX-CF-MARCO-DAV-IN-OHLC-SWEEP-CEPE` (§18e) | PARTIAL |

---

## 18d. Chart Fanatics — Trader Yush (`MIX-CF-YUSH-*`)

**ASR caveat:** Phase-3I `ASR_WHISPER` / `[ASR]`. Guest **Trader Yush**. Title **74%** = CLAIM only.  
**Bind:** [`hvyf6frvCcA_BIND.md`](../../01_research/docs/chart_fanatics/hvyf6frvCcA_BIND.md)  
**OpenAI:** `data/recon/CF_OPENAI_YUSH_BIND_SUGGEST_2026-09-07.md`  
**Candidates:** [`MIX-CF-YUSH-AOI-REACTION.md`](candidates/MIX-CF-YUSH-AOI-REACTION.md), [`MIX-CF-YUSH-IN-OHLC-PARTIAL.md`](candidates/MIX-CF-YUSH-IN-OHLC-PARTIAL.md), [`MIX-CF-YUSH-IN-RETRY-RETEST.md`](candidates/MIX-CF-YUSH-IN-RETRY-RETEST.md), [`MIX-CF-YUSH-IN-RANGE-TREND-SWITCH.md`](candidates/MIX-CF-YUSH-IN-RANGE-TREND-SWITCH.md)  
**Do not** merge into Fabio/Carmine OF books or STRAT-001–014. **No STRAT-015+.**

```yaml
mix_id: MIX-CF-YUSH-AOI-REACTION
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics hvyf6frvCcA guest Trader Yush — AOI (≥2 of PDH/PDL/ORB/VP/big-trades/delta)
  + reaction gate; miss → retest only. ASR. OF preferred; India OHLC PARTIAL.
  Title 74% CLAIM · win_rate=null · NO_PROMOTE.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
of_teacher_preferred: true
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-CARMINE-ABSORB]
docs:
  - teams/01_research/docs/chart_fanatics/hvyf6frvCcA_BIND.md
```

```yaml
mix_id: MIX-CF-YUSH-IN-OHLC-PARTIAL
origin: PROJECT_MIX
origin_note: |
  India observation-gated OHLC proxy of Yush AOI/reaction (VP/OF approximated).
  PARTIAL · win_rate=null · NO_PROMOTE.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
india_decision: PARTIAL
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-YUSH-AOI-REACTION]
docs:
  - teams/01_research/docs/chart_fanatics/hvyf6frvCcA_BIND.md
```

---

## 18e. Chart Fanatics — Marco DaVinci return (`MIX-CF-MARCO-DAV-*`)

**ASR caveat:** Phase-3I `ASR_WHISPER`. Guest **Marco** return ep — **KEEP_ALL separate** from §11 `MIX-CF-MARCO-LIQ-TRAP` / `INT-EXT`.  
**Bind:** [`T_djSNBmV00_BIND.md`](../../01_research/docs/chart_fanatics/T_djSNBmV00_BIND.md)  
**OpenAI:** `data/recon/CF_OPENAI_MARCO-DAV_BIND_SUGGEST_2026-09-07.md`  
**Candidates:** [`MIX-CF-MARCO-DAV.md`](candidates/MIX-CF-MARCO-DAV.md), [`MIX-CF-MARCO-DAV-IN-OHLC-SWEEP-CEPE.md`](candidates/MIX-CF-MARCO-DAV-IN-OHLC-SWEEP-CEPE.md)  
**No STRAT-015+.** **NO_PROMOTE.**

```yaml
mix_id: MIX-CF-MARCO-DAV
origin: EXTERNAL_RESEARCH
origin_note: |
  Chart Fanatics T_djSNBmV00 Marco return — DaVinci engineered-liquidity + fractal sweep/take.
  ASR. Separate from DAnXM7C16h0 MIX-CF-MARCO-LIQ-TRAP. win_rate=null · NO_PROMOTE.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
asr_caveat: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-MARCO-INT-EXT]
docs:
  - teams/01_research/docs/chart_fanatics/T_djSNBmV00_BIND.md
```

```yaml
mix_id: MIX-CF-MARCO-DAV-IN-OHLC-SWEEP-CEPE
origin: PROJECT_MIX
origin_note: |
  India OHLC proxy: engineered liquidity + sweep/take → directional CE/PE.
  PARTIAL · observation-gated · win_rate=null · NO_PROMOTE.
styles: [SCALPER, OPTION_BUYER]
customer_default: false
status: BACKTEST_BOOK
india_decision: PARTIAL
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MARCO-DAV, MIX-CF-MARCO-LIQ-TRAP]
docs:
  - teams/01_research/docs/chart_fanatics/T_djSNBmV00_BIND.md
```

---

## 19. TradingAgents India — `MIX-TA-*` (EXTERNAL_RESEARCH, PAPER_WATCH)

**Date:** 2026-09-06  
**Origin:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0) adapted for NSE index options.  
**Council:** [`OPENAI_DESIGN_COUNCIL_2026-09-06.md`](../../00_orchestrator/docs/OPENAI_DESIGN_COUNCIL_2026-09-06.md)  
**Adopt:** [`ADOPT_TRADINGAGENTS.md`](../../00_orchestrator/docs/ADOPT_TRADINGAGENTS.md)  
**Package:** `packages/trading_agents_india`  
**Policy:** KEEP_ALL. **Not** customer default. Paper-watch **alongside** `MIX-DEFAULT-BUY`. No STRAT-015+. Metrics **null**. Not a promote.

Council aliases: `MIX-TA-001`→`MIX-TA-FLOW-RISK`, `MIX-TA-002`→`MIX-TA-EVENT-HOLD`, `MIX-TA-003`→`MIX-TA-EXEC-SANITY`.

```yaml
mix_id: MIX-TA-FLOW-RISK
origin: EXTERNAL_RESEARCH
origin_note: |
  TradingAgents-style bull/bear + risk triad wrapper around CE/PE buy-first lean.
  HYPOTHESIS only. India: NIFTY/BANKNIFTY/SENSEX expiry + premium decay awareness.
  Paper session via packages/trading_agents_india. Not a coded live strategy.
styles: [OPTION_BUYER]
customer_default: false
status: PAPER_WATCH
proxy_status: WAITING
of_required: false
not_merged_into: [MIX-DEFAULT-BUY, STRAT-001, STRAT-002, STRAT-003]
docs:
  - teams/00_orchestrator/docs/ADOPT_TRADINGAGENTS.md
  - teams/00_orchestrator/docs/OPENAI_DESIGN_COUNCIL_2026-09-06.md
```

```yaml
mix_id: MIX-TA-EVENT-HOLD
origin: EXTERNAL_RESEARCH
origin_note: |
  Index regime + event-risk overlay that may only HOLD / downgrade — never invent alpha.
  SOURCE_FACT path: desk_intel Moneycontrol RSS when wired; else DATA_INSUFFICIENT.
  Aligns EVENT_MEMORY: news = ticket hold, not catalog delete.
styles: [OPTION_BUYER, POSITION]
customer_default: false
status: PAPER_WATCH
proxy_status: WAITING
of_required: false
not_merged_into: [MIX-DEFAULT-BUY, MIX-TA-FLOW-RISK]
docs:
  - teams/06_backtesting/docs/EVENT_MEMORY.md
  - teams/00_orchestrator/docs/OPENAI_DESIGN_COUNCIL_2026-09-06.md
```

```yaml
mix_id: MIX-TA-EXEC-SANITY
origin: EXTERNAL_RESEARCH
origin_note: |
  PAPER execution sanity: spread / liquidity / slippage checks as HYPOTHESIS gates.
  LIVE path = DhanHQ-only stub; mode=LIVE always refuses orders until founder+gate
  (default refuse). DATA_INSUFFICIENT for live fill model.
styles: [OPTION_BUYER]
customer_default: false
status: WAITING
proxy_status: DATA_INSUFFICIENT
of_required: false
not_merged_into: [MIX-DEFAULT-BUY, MIX-TA-FLOW-RISK]
docs:
  - packages/trading_agents_india/src/trading_agents_india/mode.py
  - packages/dhan-client/src/dhan_client/execution.py
```

```yaml
mix_id: MIX-TA-MARKET-HOURS
origin: PROJECT_MIX
origin_note: |
  Market-hours paper agent poll loop (IST 09:30–15:00 active; MIX-CLOCK-CAS
  dead-bands 09:00–09:30 + 15:00–15:30 → HOLD). Ledger:
  data/recon/paper_watch/MIX-TA-MARKET-HOURS/ + trading_agents_india.sqlite.
  Default tick 45s (30–60 band); path toward 15s documented, not default.
  Not a promote. Not customer default. Orders refused.
styles: [OPTION_BUYER]
customer_default: false
status: PAPER_WATCH
proxy_status: WAITING
of_required: false
not_merged_into: [MIX-DEFAULT-BUY, MIX-TA-FLOW-RISK, STRAT-001]
docs:
  - teams/00_orchestrator/docs/PLAN_MARKET_HOURS_PAPER_AGENTS.md
  - packages/trading_agents_india/src/trading_agents_india/session_runner.py
```

---

## HANDOFF

**Accepted:** KEEP_ALL. STRAT-001–014 all `BACKTEST_BOOK`. MIX-* namespace. 013/014 seller tags, IDs unchanged. 010 parked-not-dropped. MIX-CONFLICT-STRIKE labeled CONFLICT. §8 scan IDs (`WEB-DERIVED` / `PROJECT_MIX`) named including MIX-CLOCK-CAS overlay and MIX-ML-LOGIT / MIX-ML-LOGIT-XR; metrics null; `customer_default: false`. `MIX-DEFAULT-BUY` unchanged. **§9 SL/TP MIX rows** including own `MIX-DESK-IQ-ATR-RR2` (`PROJECT_MIX`). **§10 `MIX-CF-FABIO-TREND-NY` + `MIX-CF-FABIO-MR-RANGE`** (`EXTERNAL_RESEARCH`, PARKED OF, proxy BACKTEST_BOOK). **§11 `MIX-CF-MARCO-LIQ-TRAP` + `MIX-CF-MARCO-INT-EXT` + `MIX-CF-MAYNE-ICT-HTF` + `MIX-CF-MAYNE-BREAKER`** (`EXTERNAL_RESEARCH`, ASR caveat, separate from Fabio). **§12 `MIX-CF-MARCI-RIZZY` + `MIX-CF-MARCI-BB-REALITY` + `MIX-CF-TORI-TL-BOUNCE` + `MIX-CF-TORI-TL-BREAK`** (`EXTERNAL_RESEARCH`, ASR caveat, separate from Fabio/Marco/Mayne). **§13 `MIX-CF-TG-TRIDENT` + `MIX-CF-TG-EMA-WAVE` + `MIX-CF-KANE-EQ50` + `MIX-CF-KANE-PO3-SMT`** (`EXTERNAL_RESEARCH`, ASR caveat, separate from prior CF guests; title 90% not product metric). **§14 `MIX-CF-UMAR-MORNING-TOP` + `MIX-CF-UMAR-OPENING-DRIVE` + `MIX-CF-FOREST-VPE-EDGE` + `MIX-CF-FOREST-POC-RETEST`** (`EXTERNAL_RESEARCH`, ASR caveat; opening drive DI; separate from prior CF guests). **§15 `MIX-CF-CARMINE-ABSORB` + `MIX-CF-CARMINE-FAIL-BREAK` + `MIX-CF-CARMINE-OPEN-HOLD` + `MIX-CF-JADECAP-SWING-FAIL` + `MIX-CF-JADECAP-SESSION-LIQ` + `MIX-CF-JADECAP-FVG-DRAW`** (`EXTERNAL_RESEARCH`, ASR caveat; Carmine absorb OF PARKED/DI; Jade session-liq DI; separate from prior CF guests). **§16 `MIX-CF-USMAN-*` + `MIX-CF-BRANDO-*`** (`EXTERNAL_RESEARCH`, ASR caveat; Usman mostly DI options literacy; Brando HTF proxies BACKTEST_BOOK; size-zero vs price-stop KEEP_ALL; separate from prior CF guests). **§17 `MIX-CF-ANDREA-*` + `MIX-CF-OMOR-*`** (`EXTERNAL_RESEARCH`, ASR caveat; Andrea ≠ Fabio; OF absorb PARKED; Omor KZ/ADR DI; structure proxies BACKTEST_BOOK; separate from prior CF guests). **§18 `MIX-CF-OKALA-*`** (`EXTERNAL_RESEARCH`, ASR; catalog only / not CF×8; magnets observable|searchable; portability observation-gated; miss/recovery + BT grid in BIND; OpenAI suggest HYPOTHESIS only; win_rate=null; NO_PROMOTE). **§18b `MIX-CF-OKALA-IN-*`** FOUNDER_PAPER_ACCEPT PAPER only. **§18c overnight OpenAI+India IN rollup** (ok=17/fail=0; Tori SKIP). **§18d `MIX-CF-YUSH-*`**. **§18e `MIX-CF-MARCO-DAV-*`** (separate from §11 Marco). **§19 `MIX-TA-FLOW-RISK` + `MIX-TA-EVENT-HOLD` + `MIX-TA-EXEC-SANITY`** (`EXTERNAL_RESEARCH` / TradingAgents Apache-2.0; PAPER_WATCH / WAITING; not promote).

**Rejected:** Deleting teacher recipes. Silent 002-on-003. Invented fills/lots/win rates. STRAT-015+. Relabeling ORB 09:15–09:30 or CPR as `DHAN-DERIVED`. Promoting a scan onto the customer ticket. Claiming US GEX = NIFTY edge. Silent hardcoded `STOP_PTS` as named strategy. Clubbing Fabio/Marco/Mayne/Marci/Tori/TG/Kane/Umar/Forest/Carmine/Jadecap/Usman/Brando/Andrea/Omor/Okala/Yush/Marco-DAV into DEFAULT-BUY / IQCapital / each other. Inventing Carmine DOM fields, Jade Asia/London NSE boxes, Usman OI/greeks, Brando India headlines, Andrea ES footprint fields, Omor IST killzones, or Okala NIFTY digit clocks without magnet-observation adaptation MIX. Merging Andrea into `MIX-CF-FABIO-*` or Marco-DAV into `MIX-CF-MARCO-LIQ-TRAP`. Promoting title $6k→$10M / 30M funding rhetoric / Okala 65% / Yush 74% title WR. Promoting `MIX-TA-*` or treating TradingAgents US equity stack as India SOURCE_FACT. Claiming OpenAI fixes Okala/CF backtest WR. Live agent orders. Re-enabling soft news veto overnight.

**UNKNOWN / DATA_INSUFFICIENT:** 004 EMA lengths. 010 HQ OF history. 003 “103.” 006 delta. Live IEP feed (CAS). Analog memory empty. Scan params (BB k, Keltner, SAR AF, ADX period, body/range windows). No HQ ORB/CPR/ADX series. **NIFTY GEX / naive GEX construction. OF footprint history. Fabio NQ OF → NSE map; Marco/Mayne NY/Asia/London/crypto clocks → IST; Marci NY-open avoid / Tori 4H week → NSE; TG London KZ NY → IST; Kane EST 9:15–11 / SMT NQ–ES → single NIFTY; Umar ET open/cut + OF tape; Forest overnight H/L + true VAP → NSE; Carmine DOM/heatmap/delta + ET open-hold → NSE; Jadecap Asia/London/midnight open → NSE; Usman OPTIDX OI/greeks + US Fri 0DTE → NIFTY weekly; Brando Fed/tariff news join + size-zero premium ledger; Andrea ES footprint/VP/Deep Charts + NY OR → NSE; Omor London/NY/Asia KZ + ADR + FX SMT → NSE. ASR noun errors (Buma Ashraf; Osman Astra; brand-a-k-a-leaf; Andrea Chimney; Omore/MBB; boat≈close; PLC≈POC; Car mine; rate≈raid; Markime Commodule≈MMM). TG EMA 13 vs 15.** DhanHQ news API surface absent in client; Moneycontrol RSS VERIFY IF STABLE; India social sentiment unwired; LIVE founder+gate flags default refuse.

Next: 06 may **schedule** books; it may not claim an edge. 03 owns `CAS-*`. Scan queue is **not** a promote. SL/TP overlays score on fixtures before any promote. CF remaining **fail=32** need ASR/caption later — do not deep-analyze the fail queue. `MIX-TA-*` stay paper-watch only.
