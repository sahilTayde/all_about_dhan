# MIX_PROJECT_2026-09-03 — two PROJECT MIX IDs (not STRAT-015+)

**Team:** 04_quant (research analyst / strategy architect)  
**Date:** 2026-09-03  
**Layer:** `HYPOTHESIS`  
**Status:** `UNVALIDATED` / `DRAFT` / `KEEP_ALL` — **06 ran 2026-09-03: all four NIFTY/SENSEX cells FAIL** ([`BACKTEST_PROJECT_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_PROJECT_2026-09-03.md)). This file still does **not** claim wr.  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. 09 five-pass has **not** passed. Notes ≠ pass.  
**IDs this ticket:** `MIX-MTF-TREND` · `MIX-CONFIRM-5M` only.  
**Origin (both):** `PROJECT_MIX` / `PROJECT-DERIVED`. **Not** `DHAN-DERIVED`.  
**Customer default:** unchanged. This file does **not** edit [`ENGINE_MIX.md`](ENGINE_MIX.md). `MIX-DEFAULT-BUY` stays the Phase-1 lean.

Education ≠ edge. Mandate ≠ claimed P/L ([`BOSS_AGENT.md`](../../00_orchestrator/docs/BOSS_AGENT.md)). No live orders. No `/alerts/orders`. Empty `DHAN_*` does not block this spec (fixtures later).

---

## Honesty banner

```text
layer:                  HYPOTHESIS
status:                 UNVALIDATED
research_ready_for_programming: false
gate:                   09 five-pass has NOT passed. Notes ≠ pass.
metrics:                win_rate=null  expectancy=null  profit_factor=null  max_drawdown=null
profitability:          NOT CLAIMED
ids:                    MIX-MTF-TREND, MIX-CONFIRM-5M
                        STRAT-001 … STRAT-014 stay BACKTEST_BOOK. No STRAT-015+.
origin:                 PROJECT_MIX / PROJECT-DERIVED  (NOT DHAN-DERIVED)
customer_default:       false   # ENGINE_MIX / MIX-DEFAULT-BUY not touched
live code:              forbidden (no apps/, no packages/ strategies)
fills / lots / quotes:  NOT INVENTED
supertrend_grid:        forbidden this ticket (do not grid 10,3 / 7,3 / 10,1 / 10,2)
```

Prior option-premium books on disk ([`BACKTEST_OPTION_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_OPTION_2026-09-03.md)) are a **different** object. Those ratings are **FAIL / not a promote**. This ticket does **not** copy them as metrics for the two new IDs. Metrics stay **null**.

---

## Coalition cites (do not collapse layers)

| Team | File | What this ticket takes |
|------|------|------------------------|
| 00 | [`BOSS_AGENT.md`](../../00_orchestrator/docs/BOSS_AGENT.md) · [`EXPERT_COALITION.md`](../../00_orchestrator/docs/EXPERT_COALITION.md) | New tests = `MIX-*`. Kill only after 06 OOS+`NORMAL`. Mandate ≠ wr. |
| 01 | [`TRANSCRIPT_ANALYST.md`](../../01_research/docs/handoffs/TRANSCRIPT_ANALYST.md) | **Authority that these two IDs are not DHAN-DERIVED.** One-speaker clubs stay `MIX-GOKUL-003` / `MIX-HAUS-001`. Two-speaker AND, desk staging, universe transfer = `PROJECT_MIX`. |
| 01 | [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) | English `normalized_en/` wins. 003 3m all-three CONFIRMED. 001 hourly+5m/10m CONFIRMED; **2h parent `NOT_IN_EN`**. 005 ITM/max ATM CONFIRMED. 009 09:45 / 15:15 CONFIRMED. 002-on-003 = `CONFLICT`. |
| 02 | [`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md) · [`VALIDATION_MATH.md`](../../02_phd_math/docs/VALIDATION_MATH.md) · [`DHAN_INDICATOR_API_MAP.md`](../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md) | P/L = OPTIDX premium, not INDEX points. Costs UNKNOWN → expectancy optimistic if ever scored. ST 10,3 = WEAK inference — **do not p-hack**. MACD series = compute; annexure has `MACD_HIST`, signal length UNKNOWN. |
| 03 | [`ROLLING_OPTION.md`](../../03_phd_market/docs/ROLLING_OPTION.md) · [`TRANSCRIPT_MARKET_NOTES.md`](../../03_phd_market/docs/TRANSCRIPT_MARKET_NOTES.md) · [`STRAT_001_014_MARKET.md`](../../03_phd_market/docs/STRAT_001_014_MARKET.md) | 005 ITM proxy CE `ATM-2` / PE `ATM+2`. SENSEX = BSE. 3m not HQ `{1,5,15,25,60}`. Flatten 15:15 ≠ F&O 15:40 (`VERIFY`). Lots / expiry `FROM_CONTRACT`. |
| 04 | [`SIGNAL_STAGING.md`](SIGNAL_STAGING.md) · [`MIX_CATALOG.md`](MIX_CATALOG.md) · [`ALGO_HANDOFF.md`](ALGO_HANDOFF.md) · candidates `STRAT-001` / `003` / `005` / `009` | 5m Supertrend/MACD = **confirm or kill, not entry**. Catalog KEEP_ALL. YAML shape only — do not code. |
| 05 | [`CUSTOMER_TALK.md`](../../05_analysis/docs/CUSTOMER_TALK.md) · [`DESK_INTELLIGENCE.md`](../../05_analysis/docs/DESK_INTELLIGENCE.md) | Talk = trend + **3m** chain + cited news. News / extreme PCR = **hold**, not alpha, not a catalog delete. No indicator soup on `/`. |
| 06 | [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md) · [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) | Score `NORMAL` only when tags exist. Analog payloads **empty**. Nightly `BACKTEST_REQUIRED`; keep current until OOS+NORMAL after costs. |
| 09 | [`KEEP_ALL_REVIEW.md`](../../09_review/docs/KEEP_ALL_REVIEW.md) | `NOTES_ONLY`. Do not issue the programming gate from this file. |

**Workspace books** (`config/workspace.yaml` `sources.books[]`, `use: VALIDATION` — not proof of edge; **do not paste chapters**):

| Book | VALIDATION tag used here | Forbidden |
|------|--------------------------|-----------|
| John J. Murphy, *Technical Analysis of the Financial Markets* | Multiple timeframe: **higher TF names the trend; lower TF times the entry**. Mapped as 001 **60m+5m lean** (higher) vs 003 **3m all-three** (lower). | Treating Murphy as a Dhan recipe. Inventing a Supertrend REST. Relabeling MTF as `DHAN-DERIVED`. |
| Sheldon Natenberg, *Option Volatility and Pricing* | Long vanilla **pays theta**. Do **not** buy calls into a **larger downtrend** (direction + time both against the long). Same-day flatten (009) is the theta clock on this book, not a CAS close. | Using Natenberg as a win-rate. Overnight long premium. Buying CE while 001 parent is bear. |

---

## Why these two IDs exist (and why they are not teacher clubs)

[`TRANSCRIPT_ANALYST.md`](../../01_research/docs/handoffs/TRANSCRIPT_ANALYST.md) § “What NO video taught as one system”:

- Gokul (`2RnBT9DDDNI`) taught **3m futures all-three** as **entry**. He did **not** teach “wait for HAUS 60m+5m lean.”
- Himanshu (`HAUSZx-hYdY`) taught child **MACD as entry** (buy that candle’s high) on **hourly + 5m/10m**. He did **not** teach Gokul 3m VWAP/VWMA/ST as the entry.
- Desk [`SIGNAL_STAGING.md`](SIGNAL_STAGING.md) 5m MACD/Supertrend **confirm-or-kill** is already tagged **`PROJECT_MIX`**. Analyst: “Two test IDs. Do not average” with HAUS entry.

Therefore **both** IDs below are **`PROJECT_MIX` / `PROJECT-DERIVED`**. 01 already forbids relabeling desk staging or two-speaker ANDs as `DHAN-DERIVED`. This ticket obeys that.

KEEP_ALL: STRAT-001–014 stay `BACKTEST_BOOK`. `WAITING`/`PARKED` = not this ticket’s default, **not deleted**. Conflicts stay extra MIX rows (`MIX-CONFLICT-STRIKE`, `MIX-ABL-CLOCKS`). No `STRAT-015+`.

---

## Shared freeze (both MIX IDs)

```yaml
book_policy: KEEP_ALL
status: UNVALIDATED
research_ready_for_programming: false
customer_default: false          # do not write ENGINE_MIX
origin: PROJECT_MIX              # alias PROJECT-DERIVED (ALGO_HANDOFF)
styles: [OPTION_BUYER]
book: INDEX_OPTIONS
instrument: {type: INDEX_OPTION, side: BUY, exchange: FROM_CONTRACT}
lot_size: FROM_INSTRUMENT_MASTER
expiry: FROM_CONTRACT
session_tz: Asia/Kolkata
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}

universe_this_ticket:
  required: [NIFTY, SENSEX]      # option premium (OPTIDX rollingoption)
  optional_later: [BANKNIFTY]    # not scored on this ticket
  not: [NIFTY_100_STOCKS]        # 001 spoken universe stays on MIX-HAUS-001

pnl_object: OPTION_PREMIUM       # not INDEX points
fill: next_bar_open              # no look-ahead on signal close; still not a true fill (Q12)
costs: UNKNOWN                   # any later expectancy is OPTIMISTIC
session_score: NORMAL_when_tagged
news_pcr: HOLD_not_alpha         # 05 veto; not a catalog delete

strike_overlay: STRAT-005
strike_cell_frozen:
  CE: ATM-2                      # 03 ROLLING_OPTION / 02 2-ITM cell
  PE: ATM+2
# This freezes THIS MIX's first book to the 2-ITM cell.
# It does not rewrite STRAT-005's spoken ATM / 1-ITM fallback as deleted.
# It does not merge STRAT-002 (ATM+2 CE / ATM-2 PE OTM).

clock_filter: STRAT-009          # ignore 09:15–09:45; start 09:45; flatten before 15:15
overnight: false                 # theta — Natenberg tag; same-day only

supertrend_003:
  spoken_raw: "103"              # WEAK [UNCERTAIN_TRANSCRIPT]
  inferred: {atr: 10, multiplier: 3}
  this_ticket: FREEZE_INFERENCE_DO_NOT_GRID
  forbidden_grid: [10_3_search, 7_3, 10_1, 10_2]

not_attached_both:
  - STRAT-002                    # CONFLICT on 003 (MIX-CONFLICT-STRIKE)
  - STRAT-007                    # Himanshu clock; 007∧009 is a different PROJECT mix
  - STRAT-004                    # lengths NOT_IN_EN
  - STRAT-006                    # Mukul scalp — other book
  - STRAT-010                    # OF DATA_INSUFFICIENT
  - STRAT-011                    # PROJECT transfer / gA5 fill was sell
  - STRAT-012                    # optional PA — not this freeze
  - STRAT-013                    # WAITING sell
  - STRAT-014                    # WAITING sell
```

**008 on the first book:** **not attached.** Mixed NIFTY vs SENSEX is **not** a veto on these two IDs. 008 stays KEEP_ALL on `MIX-GOKUL-003`. Do not delete it.

**HQ charts:** intervals `{1,5,15,25,60}`. **60m exists.** **3m does not** — 003 remains a resample of 1m (same gap as existing Gokul books). Supertrend / MACD series REST: **none** — compute from OHLC ([`DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md)).

**Customer `/`:** staged lean only. No MACD / Supertrend / STRAT IDs. **Internal `/desk`:** IDs + origin tags.

---

## 1. MIX-MTF-TREND

**Hypothesis (not a result):** a 003 **3m all-three** CE (PE) ticket is taken **only when** STRAT-001 **60m + 5m lean** already agrees. Higher TF = trend (Murphy tag). Lower TF = 003 entry. Do **not** buy CE into a 001 parent downtrend (Natenberg tag). Flatten same day (009) because long premium pays theta.

**Not** HAUS entry: do **not** buy the child-candle high. 001 supplies **lean sign only** (histogram + MA stack as in [`STRAT-001.md`](candidates/STRAT-001.md)). 003 supplies **entry**.

**Not** `MIX-HAUS-001` (001 primary + 002 + 007). **Not** `MIX-GOKUL-003` (no 001 gate; 008 attached). **Not** `MIX-DEFAULT-BUY` (007∧009 + staging ST/MACD).

```yaml
mix_id: MIX-MTF-TREND
name: mtf_001_lean_gates_003_entry
origin: PROJECT_MIX
origin_alias: PROJECT-DERIVED
origin_note: >
  Two speakers + Murphy MTF mapping + Natenberg theta/trend tag.
  No @DhanHQ video taught 003-entry AND 001-60m/5m-lean as one recipe.
  TRANSCRIPT_ANALYST.md: not DHAN-DERIVED.
origin_videos:                   # pointers only — club is still PROJECT
  - {video_id: 2RnBT9DDDNI, role: STRAT-003_entry, ts: "20:57-40:56"}
  - {video_id: 2RnBT9DDDNI, role: STRAT-005_strike, ts: "38:06-39:20"}
  - {video_id: 2RnBT9DDDNI, role: STRAT-009_clock, ts: "23:48-24:06"}
  - {video_id: HAUSZx-hYdY, role: STRAT-001_lean_only, ts: "41:32-01:03:10"}
dhan_derived: false
customer_default: false

attached:
  primary: [STRAT-003]           # 3m all-three CE/PE
  lean_gate: [STRAT-001]         # 60m parent + 5m child LEAN; not entry
  overlay_strike: [STRAT-005]    # ATM-2 CE / ATM+2 PE
  filter: [STRAT-009]
not_attached: [STRAT-002, STRAT-007, STRAT-008]

001_role: LEAN_GATE
001_timeframes_frozen: {parent: 60m, child: 5m}
001_forbidden_on_this_book:
  - buy_child_candle_high        # that is MIX-HAUS-001 macd_role: HAUS_ENTRY
  - parent_2h                    # NOT_IN_EN on HAUS
  - child_10m_alt                # spoken alt; not this freeze
  - overlay_STRAT-002
001_params:                      # WEAK/CONFLICT stay search — do not silent-correct
  macd_12_26_xN: DO_NOT_FREEZE   # ×3 vs ×4 WEAK
  ma_100_vs_300: DO_NOT_SILENT_CORRECT
  ma_9_vs_10: DO_NOT_SILENT_CORRECT

lean_agree_rule:
  CE: 003_all_three_bull AND 001_parent_bull AND 001_child_5m_bull
  PE: 003_all_three_bear AND 001_parent_bear AND 001_child_5m_bear
  else: SKIP                     # no 003 ticket if 001 lean disagrees or is mixed
  # 001 bull = MACD hist > 0 AND MA(10) > MA(30) > MA(100)  [STRAT-001]
  # 001 bear = invert

macd_role: NOT_USED_AS_ENTRY     # 001 MACD is lean only; staging MACD is MIX-CONFIRM-5M
staging_5m_st_macd: not_attached # first book = MTF lean gate, not desk ST/MACD confirm
```

| Layer | Claim |
|-------|--------|
| `SOURCE_FACT` | 003 3m all-three. 001 1h + 5m/10m lean + child-high **entry** (we **drop** the entry). 009 flatten. 005 ITM/max ATM. |
| `VALIDATION` | Murphy MTF (higher TF trend / lower TF entry). Natenberg: long premium pays theta; do not buy calls into a larger downtrend. HQ 60m interval exists; 3m resample UNKNOWN method. |
| `HYPOTHESIS` | AND of 001 lean with 003 entry improves the **option-premium** book vs 003-alone. **Not measured. Metrics null.** |

---

## 2. MIX-CONFIRM-5M

**Hypothesis (not a result):** 003 **3m all-three** is still the **entry**. 5m **MACD histogram same sign** as that lean **promotes or kills** — desk [`SIGNAL_STAGING.md`](SIGNAL_STAGING.md), **not** HAUS entry. Same 005 2-ITM overlay and 009 flatten.

**MACD here is not HAUS entry.** Do **not** buy the child-candle high. Do **not** use 5m MACD as the first reason a side exists. If 003 has not printed all-three, stay idle / WATCH — do not invent a MACD ticket.

**Histogram same sign** is the freeze (not a signal-line **cross**, not a Supertrend **flip**). Staging’s “ST and/or MACD, and do not CONFIRMED if they contradict” is the **desk** machine; this MIX **first book** uses **MACD_HIST sign only** so 06 can score one object. Supertrend 10,3 stays the 003 **entry** inference — **not** a confirm grid.

```yaml
mix_id: MIX-CONFIRM-5M
name: gokul_003_entry_macd_hist_confirm_or_kill
origin: PROJECT_MIX
origin_alias: PROJECT-DERIVED
origin_note: >
  Desk SIGNAL_STAGING confirm-or-kill attached to Gokul 003 entry.
  TRANSCRIPT_ANALYST.md: 5m MACD/ST confirm-or-kill is PROJECT_MIX.
  HAUS child MACD is a different test ID (HAUS_ENTRY). Do not average.
origin_videos:
  - {video_id: 2RnBT9DDDNI, role: STRAT-003_entry, ts: "20:57-40:56"}
  - {video_id: 2RnBT9DDDNI, role: STRAT-005_strike, ts: "38:06-39:20"}
  - {video_id: 2RnBT9DDDNI, role: STRAT-009_clock, ts: "23:48-24:06"}
  # no HAUS video as recipe — staging is desk
dhan_derived: false
customer_default: false

attached:
  primary: [STRAT-003]           # 3m all-three = ENTRY
  confirm_or_kill: [STAGING_5M_MACD_HIST_SIGN]
  overlay_strike: [STRAT-005]    # ATM-2 CE / ATM+2 PE
  filter: [STRAT-009]
not_attached: [STRAT-001, STRAT-002, STRAT-007, STRAT-008]

macd_role: STAGING_CONFIRM_OR_KILL
macd_not: HAUS_ENTRY
do_not: buy_child_candle_high

confirm_rule:
  timeframe: 5m                  # HQ interval; compute from close
  object: MACD_HIST              # annexure name; signal length UNKNOWN
  CE_promote: 003_all_three_bull AND macd_hist_5m > 0
  PE_promote: 003_all_three_bear AND macd_hist_5m < 0
  kill: opposite_sign            # EARLY → VETOED / EXPIRED — not a PE/CE flip ticket
  hist_zero: SKIP                # do not invent a deadband
  supertrend_5m_as_confirm: not_this_book
  supertrend_003_entry: inferred_10_3_WEAK_DO_NOT_GRID

forbidden:
  - idle_to_CONFIRMED_on_macd_alone
  - 5m_macd_as_entry
  - haus_buy_child_high
  - grid_supertrend_10_3
```

| Layer | Claim |
|-------|--------|
| `SOURCE_FACT` | Gokul 3m entry is all-three, **not** 5m MACD. HAUS 5m/10m MACD **is entry** (buy that high). Desk staging is **not** on tape as one recipe. |
| `VALIDATION` | `MACD_HIST` is an annexure **condition** name, not a series REST. Histogram sign is computable from closes; signal-line 9 UNKNOWN. Natenberg: a “correct” lean can still lose premium to theta if the 5m confirm is late — staging already labels that CONFIRMED-late → EXPIRED. |
| `HYPOTHESIS` | Same-sign 5m hist as confirm-or-kill filters 003 option-premium tickets. **Not measured. Metrics null.** |

Staging reminder (must hold): 5m Supertrend/MACD **promote or kill**. They are **not** the customer-facing entry. This MIX does not put MACD names on `/`.

---

## Backtest universe (this ticket)

| Underlying | This ticket | Note |
|------------|-------------|------|
| **NIFTY** OPTIDX premium | **in** | NSE. Strike step 50 `partially_supported` (03). |
| **SENSEX** OPTIDX premium | **in** | **BSE**. Early rollingoption history has **empty chunks** (06). Do not read a thin SENSEX sample as a theorem. |
| **BANKNIFTY** OPTIDX | **optional later** | Monthly-only regime `VERIFY`. Not required to queue these two IDs. |
| INDEX / FUTIDX **points** | **not** P/L | Lean tape only (003 all-three; 001 60m+5m). Money = option OHLC. |
| NIFTY 100 **stocks** | **not** this book | Spoken 001 universe stays on `MIX-HAUS-001`. Index transfer remains `PROJECT_MIX`. |

06 may **schedule** these MIX IDs on fixtures. 06 may **not** claim an edge, invent costs then CANDIDATE, or grid Supertrend. Promote only OOS + `NORMAL` after costs — that path does **not** exist for these IDs yet.

---

## What this file does not do

- Edit [`ENGINE_MIX.md`](ENGINE_MIX.md) or change `MIX-DEFAULT-BUY`.
- Mint `STRAT-015+`. Delete or park-as-drop 001–014.
- Attach 002 to 003. Attach 007. Attach 008 on the **first** book.
- Relabel either ID `DHAN-DERIVED`. Average HAUS entry with staging confirm.
- Freeze Supertrend 10,3 as a **search** (inference stays WEAK; **no grid**).
- Publish win rates, expectancy, or “this MIX is profitable.”
- Place orders or wire Conditional Trigger.

---

## HANDOFF

```text
From:     teams/04_quant (research analyst)
To:       01_research / 02_phd_math / 03_phd_market / 05_analysis / 06_backtesting / 09_review / 00_orchestrator
Date:     2026-09-03
Status:   HYPOTHESIS / UNVALIDATED / KEEP_ALL
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
```

**Accepted**

- Exactly two new test IDs: `MIX-MTF-TREND`, `MIX-CONFIRM-5M`. Namespace `MIX-*`. Origin **`PROJECT_MIX` / `PROJECT-DERIVED`**.
- [`TRANSCRIPT_ANALYST.md`](../../01_research/docs/handoffs/TRANSCRIPT_ANALYST.md): these clubs were **not** taught as one `@DhanHQ` recipe. **Not DHAN-DERIVED.** Teacher clubs stay `MIX-GOKUL-003` / `MIX-HAUS-001` / `MIX-MUKUL-006`.
- KEEP_ALL. STRAT-001–014 stay `BACKTEST_BOOK`. No `STRAT-015+`.
- `MIX-MTF-TREND`: 003 3m all-three CE/PE **only if** 001 **60m+5m lean** agrees. 001 = lean gate, **not** buy-child-high. Overlay 005 **ATM-2 CE / ATM+2 PE**. Flatten 009 (same-day; theta). **Not 007. Not 002. Not 008** on the first book.
- `MIX-CONFIRM-5M`: 003 3m **entry**; 5m **MACD_HIST same sign** = confirm-or-kill ([`SIGNAL_STAGING.md`](SIGNAL_STAGING.md)). Same 005 ITM + 009. MACD **not** HAUS entry.
- Supertrend 10,3: freeze **inference**, **do not grid**.
- Universe this ticket: **NIFTY** and **SENSEX** option premium. BANKNIFTY optional later.
- Customer default **unchanged**. [`ENGINE_MIX.md`](ENGINE_MIX.md) **not edited**. Metrics **null**. Profitability **not claimed**. No live orders.
- Murphy MTF + Natenberg theta/trend = `VALIDATION` tags only (`sources.books[]`).

**Rejected**

- Relabeling either MIX as `DHAN-DERIVED` or “the Dhan book.”
- Averaging HAUS `macd_role: HAUS_ENTRY` (buy child-candle high) with desk confirm-or-kill.
- Silent 002-on-003. AND 007∧009 into these IDs. 008 veto on this first book.
- Gridding Supertrend 10,3 (or 7,3 / 10,1 / 10,2) after seeing premium wr.
- Invented win rates, fills, lots, Dhan quotes. Copying 2026-09-03 FAIL wr onto these new IDs as if they were scored.
- `STRAT-015+`. Deleting 001–014 because a MIX is the test. Changing `MIX-DEFAULT-BUY`.
- `RESEARCH_READY_FOR_PROGRAMMING` from this file. Live code / `/alerts/orders`.
- BANKNIFTY as required for this ticket. Overnight long premium. Indicator soup on customer `/`.

**UNKNOWN / DATA_INSUFFICIENT**

- 3m resample method vs HQ `{1,5,15,25,60}`. Continuous FUTIDX 003 tape.
- 001 MACD ×3 vs ×4; MA 100 vs 300; trail 9 vs 10 (WEAK/CONFLICT — do not silent-correct).
- `MACD_HIST` signal length (annexure UNKNOWN). Hist≈0 deadband.
- Whether 5m ST **flip** should later AND with hist sign (staging full machine) — **not this freeze**.
- SENSEX strike step; SENSEX rollingoption empty 2021 chunks; bid/ask / Q12 true fills; costs / STT / half-spread.
- F&O 15:40 vs 009 15:15 (`VERIFY`). Analog memory empty. `session_kind` often UNKNOWN on prior runs.
- ATM (0-ITM) as a second 005 cell on **these** IDs — first book is ATM-2/ATM+2 only; 02’s two-cell charter still applies to `MIX-GOKUL-003-009`, not a silent merge here.

**What 06 must do:** may queue `MIX-MTF-TREND` and `MIX-CONFIRM-5M` on NIFTY + SENSEX option-premium fixtures. Keep metrics null until a real OOS+`NORMAL` after-cost book exists. Freeze ST inference. No promote.

**What 06 must not do:** grid Supertrend. Attach 002/007/008. Score BANKNIFTY as required. Invent wr. Treat INDEX points as `option_pnl`.

**What 09 must do:** notes ≠ pass. Origin tags must stay `PROJECT_MIX`. Do not issue the programming gate.

**What 01 must do:** no rewrite of teacher clubs. Confirm (already on disk) that desk MTF/staging ANDs are **not** DHAN-DERIVED.

**What 02 / 03 must do:** 02 — MACD_HIST sign is computable; do not freeze ×N. 03 — NSE vs BSE OPTIDX names; 15:15 ≠ 15:40; SENSEX gap stays visible.

**What 05 must do:** news / extreme PCR remain hold/veto. Do not retune ST or MACD from a `NEWS_DAY`. Customer talk stays trend + 3m chain + cited headline — no MACD names on `/`.
