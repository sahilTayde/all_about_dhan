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
| STRAT-001 | OPTION_BUYER, POSITION | WAITING proxy `MIX-HAUS-001` | no | Dual-TF (hourly+5/10m). INDEX 1m ≠ parent/child. **Not deleted.** |
| STRAT-002 | OPTION_BUYER | WAITING overlay on 001 only | no | **Never silently on 003** |
| STRAT-003 | OPTION_BUYER | primary (Gokul 3m) | yes inside `MIX-GOKUL-003` / `MIX-DEFAULT-BUY` | ST “103” **WEAK**. Paper tape = INDEX resample **PROJECT** — not frozen as FUT 3m |
| STRAT-004 | OPTION_BUYER, SCALPER | confirm / scalp | no — `PARKED` lengths `NOT_IN_EN` | **Not deleted.** `MIX-SCALP-004` |
| STRAT-005 | OPTION_BUYER | strike overlay | with 003 | ITM/max ATM. OTM not recommended in-video. PAPER overlay **unbound** (needs chain/greeks) |
| STRAT-006 | OPTION_BUYER, SCALPER | WAITING proxy `MIX-SCALP-006` | no | Spoken **2m**. HQ `{1,5,15}` — do not pretend INDEX 1m is 2m |
| STRAT-007 | OPTION_BUYER | filter (Himanshu clock) | in HAUS mix; AND with 009 is `PROJECT_MIX` | Keep as its own filter |
| STRAT-008 | OPTION_BUYER | filter (mixed-index) | in Gokul mix | DHAN-DERIVED same video as 003 |
| STRAT-009 | OPTION_BUYER | filter (09:45 / 15:15) | in Gokul mix | Start **09:45**, not 10:00 |
| STRAT-010 | OPTION_BUYER (overlay) | OF gate | no — `PARKED` `DATA_INSUFFICIENT` | **Not dropped.** `MIX-OF-010`. HQ OF history never |
| STRAT-011 | OPTION_BUYER (+ equity-native pieces) | WAITING reversal alt | no — `MIX-REV-011` | Origin **`PROJECT_MIX`**. stocks/gold; gA5 **fill was sell** |
| STRAT-012 | OPTION_BUYER (overlay) | WAITING candle/S/R | optional | **`PROJECT_MIX`** on 001/003. `MIX-PA-012` |
| STRAT-013 | **OPTION_SELLER**, POSITION | bull put credit | no — `WAITING` not buy UI | **Keep ID 013.** `MIX-SELL-013` |
| STRAT-014 | **OPTION_SELLER**, POSITION | 1-3-2 call ratio | no — `WAITING` not buy UI | **Keep ID 014.** `MIX-SELL-014` |

**Working-path scoring (PAPER catalog, 2026-09-08):** bound = `MIX-DEFAULT-BUY` + STRAT-003/007/008/009 + `MIX-TA-*` + `MIX-LEAN-*`. MIX-CF removed. Unbound KEEP_ALL IDs collapse to one `KEEP_ALL-UNBOUND-DI` observation. `MIX-CLUB-GR` PARKED off confidence (not killed).

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
working_path: WAITING
proxy_note: "INDEX 1m is not HAUS hourly+5m. Dual-TF adapter not on PAPER tick."
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
working_path: WAITING
proxy_note: "HQ charts enum {1,5,15,25,60} — not spoken 2m. Do not pretend INDEX 1m is Mukul 2m."
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
origin_note: "GAP ∧ RANGE-EXP. Optimistic 2y NIFTY 69.4% wr n=36 WEAK. After-cost 44.4% FAIL promote. SCORE_SAMPLE empty → PARK working path, not kill. Not customer default."
styles: [OPTION_BUYER]
customer_default: false
paper_watch: false
working_path: PARKED
kill: false
kill_note: "After-cost FAIL promote. SCORE_SAMPLE empty — PARK not kill."
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

## 10–18. Chart Fanatics / MIX-CF — REMOVED

Founder reset 2026-09-09: all `MIX-CF-*` (including Okala-IN) deleted from the working book. Not a STRAT-001–014 delete. Rebuild later from **@DhanHQ** only.

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

## 20. Gather lean MIX (`MIX-LEAN-*` / PROXY / HOLD) — WAITING, NO_PROMOTE

**Date:** 2026-09-08  
**Short specs:** [`candidates/MIX-LEAN-SPOT-ATM.md`](candidates/MIX-LEAN-SPOT-ATM.md) · [`MIX-IMPULSE-1M.md`](candidates/MIX-IMPULSE-1M.md) · [`MIX-003-INDEX-PROXY.md`](candidates/MIX-003-INDEX-PROXY.md) · [`MIX-006-INDEX-PROXY.md`](candidates/MIX-006-INDEX-PROXY.md) · [`MIX-PCR-EXTREME-HOLD.md`](candidates/MIX-PCR-EXTREME-HOLD.md) · [`MIX-SELL-CREDIT-PARK.md`](candidates/MIX-SELL-CREDIT-PARK.md) · [`MIX-DUAL-INDEX-MASTER.md`](candidates/MIX-DUAL-INDEX-MASTER.md)  
**Code:** `packages/trading_agents_india/lean_mix.py`  
**Policy:** KEEP_ALL. **Not** customer default. **No** `STRAT-015+`. `MIX-DEFAULT-BUY` stays `UNVALIDATED` customer default. EARLY is valid. Never `CONFIRMED` from these rows.

```yaml
mix_id: MIX-LEAN-SPOT-ATM
origin: PROJECT-DERIVED
customer_default: false
status: WAITING
NO_PROMOTE: true
```

```yaml
mix_id: MIX-IMPULSE-1M
origin: PROJECT-DERIVED
customer_default: false
status: WAITING
NO_PROMOTE: true
```

```yaml
mix_id: MIX-003-INDEX-PROXY
recipe_origin: DHAN-DERIVED
path_origin: PROJECT-DERIVED
proxy_label: INDEX_RESAMPLE_NE_FUTIDX
customer_default: false
status: WAITING
```

```yaml
mix_id: MIX-006-INDEX-PROXY
recipe_origin: DHAN-DERIVED
path_origin: PROJECT-DERIVED
proxy_label: INDEX_RESAMPLE_NE_OPTIDX
customer_default: false
status: WAITING
```

```yaml
mix_id: MIX-PCR-EXTREME-HOLD
origin: PROJECT-DERIVED
role: HOLD_overlay
customer_default: false
status: WAITING
```

```yaml
mix_id: MIX-SELL-CREDIT-PARK
origin: DHAN-DERIVED
attached: [STRAT-013, STRAT-014]
evaluate_as_buy: false
customer_default: false
status: WAITING
```

```yaml
mix_id: MIX-DUAL-INDEX-MASTER
origin: PROJECT-DERIVED
styles: [OPTION_BUYER, SCALPER]
markets: [SENSEX]
excluded_markets: [NIFTY, BANKNIFTY]
role: current_testing_backtest_candidate
status: BACKTEST_REQUIRED
paper_watch: true
paper_watch_role: audit/blocker_observation_only
customer_default: false
NO_PROMOTE: true
docs: teams/04_quant/docs/candidates/MIX-DUAL-INDEX-MASTER.md
latest_shadow_report: teams/06_backtesting/docs/MRR_BACKTEST_2026-09-10.md
```

---

## 21. Dhan algo-marketplace study clubs (`MIX-ALGO-*`) — WEB-DERIVED concepts, PROJECT construction

**Date:** 2026-09-10  
**Source study:** [`teams/01_research/docs/DHAN_ALGO_MARKETPLACE_STRATZY.md`](../../01_research/docs/DHAN_ALGO_MARKETPLACE_STRATZY.md) (Stratzy, 79 algos on algos.dhan.co, SEBI RA INH000009180).  
**Policy:** marketplace return displays are marketing, `UNVALIDATED`, never customer claims. Exact algo rules are `DATA_INSUFFICIENT` — these rows club the *concepts* with cited open literature onto our own Dhan-direct inputs. KEEP_ALL. No `STRAT-015+`. Feed-sensitivity lesson (SkewHunter CE-on-Dhan vs PE-on-Stratzy, 23-Jun-2026) ⇒ every threshold alpha in this family requires a dead-band/hysteresis.

```yaml
mix_id: MIX-ALGO-SKEW-BUY
origin: WEB-DERIVED concept / PROJECT construction
role: buy-first directional candidate (skew tilt picks side, premium tape confirms)
blocked_on: IV-stat history depth (gather chain_iv.py landed + live-validated 2026-09-10; no Dhan backfill, needs weeks of snapshots)
customer_default: false
status: BACKTEST_REQUIRED
NO_PROMOTE: true
docs: teams/04_quant/docs/candidates/MIX-ALGO-SKEW-BUY.md
```

```yaml
mix_id: MIX-ALGO-IV-REGIME-HOLD
origin: WEB-DERIVED concept / PROJECT construction
role: HOLD_overlay (flat/low-entropy IV surface + quiet morning RV => decay day => suppress premium buys)
family: joins MIX-PCR-EXTREME-HOLD overlay family
blocked_on: IV-stat history depth (gather chain_iv.py landed 2026-09-10)
customer_default: false
status: WAITING
NO_PROMOTE: true
```

```yaml
mix_id: MIX-ALGO-RR-SHELL
origin: WEB-DERIVED (marketplace-common exit shells) / PROJECT construction
role: exit-shell overlay (fixed RR 1:2 / 1:3, 25-40% SL or TSL, one-position-at-a-time, entry cutoff, EOD flat)
family: joins SL/TP MIX family (see section 9)
customer_default: false
status: WAITING
NO_PROMOTE: true
```

```yaml
mix_id: MIX-ALGO-CREDIT-PARK
origin: WEB-DERIVED (credit spreads / strangles / kurtosis straddle sell family)
role: parked seller book with citations (India short-vol evidence recorded; not the buy-first mandate; margin + tail risk unmodeled)
family: joins MIX-SELL-CREDIT-PARK
evaluate_as_buy: false
customer_default: false
status: PARKED
NO_PROMOTE: true
```

---

## HANDOFF

**Accepted:** KEEP_ALL. STRAT-001–014 all `BACKTEST_BOOK`. MIX-* namespace. 013/014 seller tags, IDs unchanged. 010 parked-not-dropped. **2026-09-08 working-path:** 001/002/006 WAITING proxies (INDEX 1m ≠ HAUS MTF / Mukul 2m); unbound STRATs collapse to `KEEP_ALL-UNBOUND-DI`; `MIX-CLUB-GR` PARKED off confidence (SCORE_SAMPLE empty → not kill). MIX-CONFLICT-STRIKE labeled CONFLICT. §8 scan IDs (`WEB-DERIVED` / `PROJECT_MIX`) named including MIX-CLOCK-CAS overlay and MIX-ML-LOGIT / MIX-ML-LOGIT-XR; metrics null; `customer_default: false`. `MIX-DEFAULT-BUY` unchanged. **§9 SL/TP MIX rows** including own `MIX-DESK-IQ-ATR-RR2` (`PROJECT_MIX`). **§10 `MIX-CF-FABIO-TREND-NY` + `MIX-CF-FABIO-MR-RANGE`** (`EXTERNAL_RESEARCH`, PARKED OF, proxy BACKTEST_BOOK). **§11 `MIX-CF-MARCO-LIQ-TRAP` + `MIX-CF-MARCO-INT-EXT` + `MIX-CF-MAYNE-ICT-HTF` + `MIX-CF-MAYNE-BREAKER`** (`EXTERNAL_RESEARCH`, ASR caveat, separate from Fabio). **§12 `MIX-CF-MARCI-RIZZY` + `MIX-CF-MARCI-BB-REALITY` + `MIX-CF-TORI-TL-BOUNCE` + `MIX-CF-TORI-TL-BREAK`** (`EXTERNAL_RESEARCH`, ASR caveat, separate from Fabio/Marco/Mayne). **§13 `MIX-CF-TG-TRIDENT` + `MIX-CF-TG-EMA-WAVE` + `MIX-CF-KANE-EQ50` + `MIX-CF-KANE-PO3-SMT`** (`EXTERNAL_RESEARCH`, ASR caveat, separate from prior CF guests; title 90% not product metric). **§14 `MIX-CF-UMAR-MORNING-TOP` + `MIX-CF-UMAR-OPENING-DRIVE` + `MIX-CF-FOREST-VPE-EDGE` + `MIX-CF-FOREST-POC-RETEST`** (`EXTERNAL_RESEARCH`, ASR caveat; opening drive DI; separate from prior CF guests). **§15 `MIX-CF-CARMINE-ABSORB` + `MIX-CF-CARMINE-FAIL-BREAK` + `MIX-CF-CARMINE-OPEN-HOLD` + `MIX-CF-JADECAP-SWING-FAIL` + `MIX-CF-JADECAP-SESSION-LIQ` + `MIX-CF-JADECAP-FVG-DRAW`** (`EXTERNAL_RESEARCH`, ASR caveat; Carmine absorb OF PARKED/DI; Jade session-liq DI; separate from prior CF guests). **§16 `MIX-CF-USMAN-*` + `MIX-CF-BRANDO-*`** (`EXTERNAL_RESEARCH`, ASR caveat; Usman mostly DI options literacy; Brando HTF proxies BACKTEST_BOOK; size-zero vs price-stop KEEP_ALL; separate from prior CF guests). **§17 `MIX-CF-ANDREA-*` + `MIX-CF-OMOR-*`** (`EXTERNAL_RESEARCH`, ASR caveat; Andrea ≠ Fabio; OF absorb PARKED; Omor KZ/ADR DI; structure proxies BACKTEST_BOOK; separate from prior CF guests). **§18 `MIX-CF-OKALA-*`** (`EXTERNAL_RESEARCH`, ASR; catalog only / not CF×8; magnets observable|searchable; portability observation-gated; miss/recovery + BT grid in BIND; OpenAI suggest HYPOTHESIS only; win_rate=null; NO_PROMOTE). **§18b `MIX-CF-OKALA-IN-*`** FOUNDER_PAPER_ACCEPT PAPER only. **§18c overnight OpenAI+India IN rollup** (ok=17/fail=0; Tori SKIP). **§18d `MIX-CF-YUSH-*`**. **§18e `MIX-CF-MARCO-DAV-*`** (separate from §11 Marco). **§19 `MIX-TA-FLOW-RISK` + `MIX-TA-EVENT-HOLD` + `MIX-TA-EXEC-SANITY`** (`EXTERNAL_RESEARCH` / TradingAgents Apache-2.0; PAPER_WATCH / WAITING; not promote). **§20 `MIX-LEAN-*` / INDEX-PROXY / PCR-HOLD / SELL-CREDIT-PARK** WAITING UNVALIDATED `customer_default: false` NO_PROMOTE; DEFAULT-BUY not rewritten. **`MIX-DUAL-INDEX-MASTER`** PROJECT-DERIVED SENSEX CALL premium candidate `BACKTEST_REQUIRED` paper-watch audit only; NIFTY/BANKNIFTY excluded; NO_PROMOTE. **§21 `MIX-ALGO-SKEW-BUY` + `MIX-ALGO-IV-REGIME-HOLD` + `MIX-ALGO-RR-SHELL` + `MIX-ALGO-CREDIT-PARK`** (`WEB-DERIVED` concepts from the algos.dhan.co Stratzy study, PROJECT construction; marketplace returns marketing-only; dead-band mandatory on threshold alphas; skew-buy/IV-hold blocked on `chain_iv_stats` gather ticket; all `customer_default: false` NO_PROMOTE).

**Rejected:** Deleting teacher recipes. Silent 002-on-003. Invented fills/lots/win rates. STRAT-015+. Relabeling ORB 09:15–09:30 or CPR as `DHAN-DERIVED`. Promoting a scan onto the customer ticket. Claiming US GEX = NIFTY edge. Silent hardcoded `STOP_PTS` as named strategy. Clubbing Fabio/Marco/Mayne/Marci/Tori/TG/Kane/Umar/Forest/Carmine/Jadecap/Usman/Brando/Andrea/Omor/Okala/Yush/Marco-DAV into DEFAULT-BUY / IQCapital / each other. Inventing Carmine DOM fields, Jade Asia/London NSE boxes, Usman OI/greeks, Brando India headlines, Andrea ES footprint fields, Omor IST killzones, or Okala NIFTY digit clocks without magnet-observation adaptation MIX. Merging Andrea into `MIX-CF-FABIO-*` or Marco-DAV into `MIX-CF-MARCO-LIQ-TRAP`. Promoting title $6k→$10M / 30M funding rhetoric / Okala 65% / Yush 74% title WR. Promoting `MIX-TA-*` or treating TradingAgents US equity stack as India SOURCE_FACT. Claiming OpenAI fixes Okala/CF backtest WR. Live agent orders. Re-enabling soft news veto overnight.

**UNKNOWN / DATA_INSUFFICIENT:** 004 EMA lengths. 010 HQ OF history. 003 “103.” 006 delta. Live IEP feed (CAS). Analog memory empty. Scan params (BB k, Keltner, SAR AF, ADX period, body/range windows). No HQ ORB/CPR/ADX series. **NIFTY GEX / naive GEX construction. OF footprint history. Fabio NQ OF → NSE map; Marco/Mayne NY/Asia/London/crypto clocks → IST; Marci NY-open avoid / Tori 4H week → NSE; TG London KZ NY → IST; Kane EST 9:15–11 / SMT NQ–ES → single NIFTY; Umar ET open/cut + OF tape; Forest overnight H/L + true VAP → NSE; Carmine DOM/heatmap/delta + ET open-hold → NSE; Jadecap Asia/London/midnight open → NSE; Usman OPTIDX OI/greeks + US Fri 0DTE → NIFTY weekly; Brando Fed/tariff news join + size-zero premium ledger; Andrea ES footprint/VP/Deep Charts + NY OR → NSE; Omor London/NY/Asia KZ + ADR + FX SMT → NSE. ASR noun errors (Buma Ashraf; Osman Astra; brand-a-k-a-leaf; Andrea Chimney; Omore/MBB; boat≈close; PLC≈POC; Car mine; rate≈raid; Markime Commodule≈MMM). TG EMA 13 vs 15.** DhanHQ news API surface absent in client; Moneycontrol RSS VERIFY IF STABLE; India social sentiment unwired; LIVE founder+gate flags default refuse.

Next: 06 may **schedule** books; it may not claim an edge. 03 owns `CAS-*`. Scan queue is **not** a promote. SL/TP overlays score on fixtures before any promote. CF remaining **fail=32** need ASR/caption later — do not deep-analyze the fail queue. `MIX-TA-*` stay paper-watch only.
