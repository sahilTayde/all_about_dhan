# BIND — `6Bdv-_YUQ0s` · Usman Ashraf (Chart Fanatics)

**Team:** 01_research  
**Date:** 2026-09-06 (rev: OpenAI+India overnight 2026-09-07)
**Layer:** `SOURCE_FACT` (`ASR_WHISPER` — **not** YouTube captions)  
**Video:** https://www.youtube.com/watch?v=6Bdv-_YUQ0s  
**Title marketing:** “Options for Beginners” / “verified seven-figure” / host “profitable strategies” PDFs — **education + marketing**; product metrics stay null  
**MD transcript:** [`6Bdv-_YUQ0s_TRANSCRIPT.md`](6Bdv-_YUQ0s_TRANSCRIPT.md)  
**Raw ASR:** `data/transcripts/external_chart_fanatics/6Bdv-_YUQ0s.asr.txt`  
**Timed VTT:** `DATA_INSUFFICIENT` — anchors are **ASR paragraph order**, not clocks.  
**Origin tag for any MIX:** `EXTERNAL_RESEARCH` / Chart Fanatics guest — **not** `DHAN-DERIVED`.  
**OpenAI aid (HYPOTHESIS only):** [`../../../../data/recon/CF_OPENAI_USMAN_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_USMAN_BIND_SUGGEST_2026-09-07.md) — does **not** fix win rates.
**KEEP_ALL:** do **not** club into STRAT-001–014, IQCapital MIXes, prior `MIX-CF-*`, Brando/Leaf MIXes, or `MIX-DEFAULT-BUY`.

---

## Honesty banner

```text
layer: SOURCE_FACT
guest: Usman Ashraf (description + Options Hub founder; ASR "Osman Astra" / "Osman Ashraf" UNKNOWN — proper-noun caveat)
source: ASR_WHISPER faster-whisper base/cpu/int8 — [ASR] caveat
asset_spoken: US equity options (AMD, Amazon, Meta LEAPS anecdotes); SPY/SPX 0DTE liquidity examples
framework: options buyer-first education — contract (strike/premium/expiry), CE/PE, ITM/ATM/OTM, Greeks, IV, chain OI/volume, weekly sizing, price-level stops
tools_spoken: options chain; OI; volume; Greeks (delta/gamma/theta/vega); implied volatility; Thinkorswim on-demand anecdote
session: US weekly options Mon–Fri theta/size; 0DTE named for indexes (SPY/SPX) — not NSE clocks
india_transfer: HYPOTHESIS only — not spoken
win_rates_spoken: host/guest leverage anecdotes + “50%/100% return” premium examples — product metrics stay null
education: not edge
optidx_greeks_oi: required for full recipes — DATA_INSUFFICIENT without chain/greeks path
```

---

## What this is **not** (SOURCE_FACT negatives)

| Claim | Verdict |
|-------|---------|
| Stock up → always buy calls / down → puts without Greeks/IV | **Rejected** — teacher’s early mistake; strike/time/IV matter |
| Size-to-zero / no stop as *his* method | **Rejected** — “need a seatbelt”; prefers stops; contrasts other guests |
| Premium % auto-stop as reliable | **Rejected alone** — sideways can bleed premium without price against thesis; he prefers **price/level** stops |
| Frozen OHLC entry pattern (ORB, PDH reclaim, etc.) | **Not spoken** as a named chart recipe — “chart must make sense” only |
| NIFTY / BANKNIFTY / SENSEX / DhanHQ | **Not spoken** |
| Host “profitable strategy” PDF / seven-figure verify as product wr | **Rejected** |

**ASR UNKNOWN:** “Osman Astra”≈Usman Ashraf; “exploration”≈expiration; “Vega”/“delta” garbles possible; “trade seller”≈TradeZella; do **not** invent India OPTIDX greek fields or NSE 0DTE calendars from US Friday rhetoric.

---

## Psychology / process (SOURCE_FACT)

| # | Claim | Notes |
|---|--------|-------|
| P1 | Buyer max loss = premium paid; seller risk asymmetric / “infinite” framed | Education |
| P2 | Majority of *his* crowd: don’t sell options aggressively | Process preference |
| P3 | Flip premium (trade the option) vs exercise — he flips | Style |
| P4 | Day-trade strength; swing/LEAPS sized from day-trade profits so overnight size feels “earned” | Sizing psychology |
| P5 | Scale-out **30 / 20 / 20 / 30**; day-trade ITM goal ~**50%** out then slow rest; **no fixed $ target** (Dogecoin caution) | Management |
| P6 | Reject hero-zero / size-to-zero mentality for himself | Conflict vs Brando theme — keep separate MIX |
| P7 | Prop / TradeZella / channel ads | Marketing — not metrics |

---

## Technical model A — **Strike pick by chain liquidity (OI / volume)**

**Teacher name:** how to know what strike to pick — liquidity.

| Step | SOURCE_FACT | UNKNOWN / gaps |
|------|-------------|----------------|
| **Chain** | Calls left / puts right / strike center | US broker UI |
| **OI** | Open interest = contracts still open from prior close; morning volume may be ~0 | Real-time OI DI |
| **Volume** | Day’s traded contracts; resets at open | |
| **Rule** | Avoid taking a large % of thin OI (example: 70 contracts vs OI 100 — hard fill); prefer OI thousands+ | Exact ratio not frozen |
| **Buy CE/PE** | Direction still from thesis/chart; strike from liquid line | Chart entry not frozen |
| **India** | Needs OPTIDX chain OI/volume | **DATA_INSUFFICIENT** without chain book |

---

## Technical model B — **0DTE / near-expiry gamma + IV for premium velocity**

**Teacher name:** gamma + implied volatility to catch “crazy moves”; 0DTE named.

| Step | SOURCE_FACT | UNKNOWN / gaps |
|------|-------------|----------------|
| **Delta** | Premium change ≈ delta × underlying $1 move | |
| **Gamma** | Rate of change of delta; adds/subtracts as price moves toward/away ATM | |
| **0DTE** | Near expiry + aggressive gamma → large % premium moves (minutes); SPY/SPX daily 0DTE; other names often Fri weekly = de-facto 0DTE | Instrument calendar US-specific |
| **IV** | Expected move / seller risk → premium expensive when IV up | SD “68%” education |
| **Select** | Prefer names with more aggressive gamma for same underlying move | Rank rule not numeric-frozen |
| **India** | Needs greeks + true weekly/0DTE map | **DATA_INSUFFICIENT**; US Fri ≠ NIFTY weekly auto |

---

## Technical model C — **Weekly options day-of-week sizing (theta awareness)**

**Teacher name:** weekly options Mon–Wed vs Thu/Fri size.

| Step | SOURCE_FACT | UNKNOWN / gaps |
|------|-------------|----------------|
| **Mon–Wed** | Premiums hold closer to stop; example ~**10–15%** premium loss at his stop | Illustrative % |
| **Thu–Fri** | Less time → same stop can mean ~**20–30%+** premium loss; size **down** (e.g. $1000 Mon → ~$750–$500 Fri) so $ risk similar | |
| **Fri / 0DTE** | Same underlying move can move premium far more (example rhetoric 50% vs 200%) | Transfer risk |
| **Still** | All size still references **price/chart confirmation** — not OI alone | Entry DI |
| **India** | NSE weekly weekday ≠ US Fri automatically | **DATA_INSUFFICIENT** as promote; management recipe only |

---

## Technical model D — **Stops on underlying price/levels (not premium choke)**

**Teacher name:** price-and-level stops; go home with stops.

| Step | SOURCE_FACT | UNKNOWN / gaps |
|------|-------------|----------------|
| **Problem** | Premium auto-stop (e.g. −10%) can stop out on sideways theta while price thesis intact | |
| **His stop** | Set on **price / chart levels**; trigger when price hits level | Exact LOI catalog not frozen |
| **Reject** | Size-to-zero as *his* seatbelt substitute | Keep conflict with Brando as separate row |
| **Scale** | 30/20/20/30; ITM day-trade ~50% then slow | Management |
| **LEAPS anecdote** | Meta far OTM LEAPS / gap-fill narrative — **education case**, not frozen day entry | Do not promote anecdote wr |
| **India** | Level stops need named INDEX levels + OPTIDX exit | Entry pattern **DATA_INSUFFICIENT**; management noted |

---

## Shared language (SOURCE_FACT)

| Theme | Claim |
|-------|-------|
| Contract | Strike + premium + expiration; 1 contract ≈ 100 shares (US stock options) |
| CE / PE | Buy calls if expect rise; buy puts if expect fall |
| Moneyness | ITM / ATM / OTM — time decay / coverage tradeoffs spoken |
| Greeks | Delta, gamma, theta (“daily commission”), vega (IV→premium) |
| Buyer vs seller odds | Seller “two of three” rhetoric — education, not product wr |

---

## Transfer risk (01 flag for 03/04)

| Risk | Status |
|------|--------|
| US equity / SPY 0DTE → NIFTY weekly OPTIDX | **Transfer HYPOTHESIS** — high |
| Contract multiplier 100 / Thinkorswim chain UI | US-specific |
| Greeks / OI on Dhan OPTIDX historical | **DATA_INSUFFICIENT** for full recipes |
| Fri weekly = 0DTE → NSE weekday | **DATA_INSUFFICIENT** |
| Seven-figure / % return anecdotes | Not product metrics |
| GEX | **Not in recipe** |

---

## HANDOFF (01)

**Accepted:** Buyer-first options literacy; CE/PE; ITM/ATM/OTM; Greeks+IV; chain OI/volume strike liquidity; weekly Mon–Wed vs Thu/Fri size; price/level stops; scale-out; reject size-to-zero *for him*; ASR name caveat.  
**Rejected:** Inventing frozen chart entry; inventing India greeks/OI; treating host PDFs / % flips as wr; clubbing into prior CF / STRAT / IQ / Brando; claiming NIFTY weekly = SPY 0DTE.  
**UNKNOWN / DATA_INSUFFICIENT:** Timed VTT; OPTIDX greeks+OI history; NSE 0DTE calendar; chart entry LOI catalog; ASR “Osman Astra”.

**Next:** 04 names `MIX-CF-USMAN-*` only. 02/03 comment (no veto). 06: chain/greeks/sizing arms = DI unless a named INDEX proxy is explicitly marked weak — no promote.
---

## OpenAI + India refresh — 2026-09-07

**OpenAI aid (HYPOTHESIS only):** [`../../../../data/recon/CF_OPENAI_USMAN_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_USMAN_BIND_SUGGEST_2026-09-07.md) — does **not** fix win rates.  
**India decision:** `PARTIAL` · of_required=True · ohcl_proxy_ok=True  
**Rationale:** Transcript provides general rules (strike selection via OI/volume liquidity; manage exits via underlying price/level invalidation; understand time/IV/Greeks). However, exact US-specific mechanics (Thinkorswim exercise window, US Friday/0DTE calendar, and any explicit numeric strike/tenor filters) are not directly mapped to NSE OPTIDX without India chain/greeks data validation. Therefore we port the framework but skip hard timing/0DTE equivalents until re-observed on India.  
**India analogs:** US 'option chain OI/volume liquidity' => India OPTIDX option chain OI/volume liquidity filter (OBSERVATION, to be implemented with Dhan chain fields if available)., Underlying price/level invalidation stop => NSE index level stop using NIFTY/BANKNIFTY/SENSEX OHLC levels (BT parameterized)., Near-expiry premium velocity via Greeks/IV => India 'tenor bucket' (near vs weekly) chosen by re-observation; Greeks may be optional (OHLC proxy) if greeks history missing.  
**KEEP_ALL / NO_PROMOTE** · `win_rate=null` · no STRAT-015+ · soft news veto stays parked.

### Honesty banner (rev)

```text
openai_suggest: HYPOTHESIS aid only — does not fix WR / does not VALIDATION
magnet_or_level: observable|searchable — not sacred
market_scope: teacher_examples=US/NQ/etc; portable_if_observed=HYPOTHESIS
india_decision: PARTIAL
catalog_win_rate: null
NO_PROMOTE: true
SOURCE_FACT only: this BIND encodes Usman Ashraf’s spoken education/logic (buyer-first, liquidity-based strike selection, time/IV/Greeks awareness, and underlying-level stops). Any India OPTIDX implementation details (OI/volume fields, near-expiry definition, availability of Greeks/IV in Dhan) are hypotheses until validated by data.
```

### Core edge (formalization · HYPOTHESIS)

Education-gated framework: pick liquid strikes using chain OI/volume; understand premium velocity via Greeks/IV (time + volatility), and manage exits with underlying price/level stops (not premium-only choke). Win_rate remains null (no backtested metrics spoken).

### Observation protocol (HYPOTHESIS)

Observation-gated, non-sacred constants. For any candidate trade: (1) Verify direction on underlying chart (index/stock). (2) Select CE/PE first from directional thesis. (3) Select strike using chain liquidity proxies (OI and today’s volume) rather than distance-from-ATM alone. (4) Choose expiry/tenor mindful of time decay effects (avoid assuming US weekly/0DTE timings map 1:1). (5) Define exit as underlying price/level invalidation (stop on underlying/level). (6) Manage position with scale-out plan (spoken example: 30/20/20/30) and do NOT mix in 'premium -X% auto stop' unless re-validated.

### Entry models (HYPOTHESIS)

[
  {
    "model_id": "MIX-CF-USMAN-ENTRY-01",
    "teacher_basis": "Strike selection by liquidity (OI/volume) once direction is known.",
    "hypothesis_params": [
      "direction_source (chart/level confirmation - generic)",
      "opt_type (CE/PE) determined by direction",
      "expiry_selection (weekly/near-tenor chosen manually or via re-observation)",
      "liquidity_filter_metric (OI_threshold or OI_rank proxy)",
      "prefer_liquid_strike_near_ATM (bool; keep as observation not constant)"
    ],
    "validation_needed": true,
    "win_rate": null
  },
  {
    "model_id": "MIX-CF-USMAN-ENTRY-02",
    "teacher_basis": "Premium velocity: time left + IV/Greeks explains why near-expiry/ATM premium moves faster.",
    "hypothesis_params": [
      "moneyness_bucket (ATM/near-ATM chosen from chain pricing)",
      "tenor_bucket (near-expiry vs weekly; India mapping requires re-observation)",
      "IV_regime_filter (high IV vs low IV; threshold TBD by chain history)"
    ],
    "validation_needed": true,
    "win_rate": null
  },
  {
    "model_id": "MIX-CF-USMAN-ENTRY-03",
    "teacher_basis": "Buyer-first: prefer taking long options exposure; avoid 'selling options aggressively' (process preference, not a hard constraint unless specified).",
    "hypothesis_params": [
      "strategy_side (BUY CE/BUY PE only)",
      "avoid_seller_only (bool; default true)"
    ],
    "validation_needed": true,
    "win_rate": null
  }
]

### Miss-entry / recovery (HYPOTHESIS)

{
  "principle_from_speech": "Do not chase; if price invalidates before confirmation, stand down. If you miss the first trigger, wait for the next underlying level confirmation; do not rely on premium percent stop behavior.",
  "recovery_rules": [
    {
      "rule_name": "NO_CHASE_NEXT_CANDLE",
      "trigger": "Entry signal fires but underlying does not follow-through / fails level",
      "action": "Cancel entry; wait for a fresh level re-test and confirmation (do not increase strike size or widen stop by default)."
    },
    {
      "rule_name": "RECOVERY_AT_RETEST",
      "trigger": "Underlying revisits the invalidation-adjacent level and then re-confirms",
      "action": "Re-select strike using liquidity filter again (do not reuse stale strike assumptions across expiry/roll)."
    },
    {
      "rule_name": "RECOVERY_LIMIT_PER_DAY",
      "trigger": "More than 2 recovery attempts for same directional thesis within the defined trading session",
      "action": "Stop trading for that thesis; reassess next session."
    }
  ],
  "notes": "Transcript mentions 'need a seatbelt' conceptually and that his own approach uses underlying price/level stops vs premium-only stop; explic

### Risk shell (HYPOTHESIS)

{
  "position_risking": "Long CE/PE: define risk by underlying stop/level invalidation (not by premium -X% auto stop). Premium loss-to-premium may vary with theta/IV; treat as stochastic.",
  "stop_logic": [
    "Underlying level stop: exit when underlying crosses the predefined invalidation level.",
    "No premium-only choke: do not auto-stop solely on premium percentage unless validated."
  ],
  "scale_out": [
    "Scale-out example (spoken): 30/20/20/30. Treat as a re-observation template, not sacred constants."
  ],
  "hedge_selling_constraint": "Process preference: avoid aggressive optio

### Market portability

{
  "scope": [
    "India index options (NIFTY / BANKNIFTY / SENSEX) CE/PE BUY-first only"
  ],
  "transferability_assessment": "High for literacy/logic (liquidity-based strike selection + underlying-level stops). Medium for tenor mapping (US weekly vs India weekly/near-expiry needs re-observation). Low for any US-specific 0DTE calendar assumptions."
}

### Backtest search grid (for 06)

{
  "reco_strategy": "Long CE or Long PE (BUY-first) with strike liquidity filter and underlying-level stop; optional scale-out.",
  "parameters": {
    "market": [
      "NIFTY",
      "BANKNIFTY",
      "SENSEX"
    ],
    "option_type": [
      "CE",
      "PE"
    ],
    "expiry_bucket_india": [
      "weekly_only",
      "near_expiry_only (re-observe definition)",
      "weekly_vs_near_expiry_two_bucket"
    ],
    "moneyness_bucket": [
      "near_ATM",
      "slightly_ITM",
      "slightly_OTM"
    ],
    "strike_liquidity_filter": [
      "OI_rank_top_k (k in {1,3,5})",
      "OI_min_threshold (threshold in {low, mid, high} quantiles by day)",
      "OI_volume_confluence (OI filter AND today volume > quantile)"
    ],
    "entry_confirmation_type": [
      "breakout_of_level",
      "retest_and_hold_level",
      "trend_pullback_to_level"
    ],
    "underlying_stop_distance_levels": [
      "fixed_tick_levels (re-observe tick size)",
      "previous_swing_low/high invalidation

### Proposed MIX ids (KEEP_ALL)

| mix_id | role | note |
|--------|------|------|
| `MIX-CF-USMAN-ENTRY-01` | teacher | CE/PE direction chosen by chart thesis; strike chosen via option chain OI/volume liquidity filter. |
| `MIX-CF-USMAN-ENTRY-02` | teacher | Premium velocity model: time-to-expiry + IV/Greeks explain fast premium movement; choose tenor/moneyness accordingly. |
| `MIX-CF-USMAN-IN-STRIKE-LIQ` | india | India adaptation: strike selection for NIFTY/BANKNIFTY/SENSEX CE/PE using re-observed OPTIDX chain liquidity (OI/volume) around chosen moneyness. |
| `MIX-CF-USMAN-IN-LEVEL-STOP` | india | India adaptation: exit long CE/PE when underlying breaks predefined price/level invalidation; avoid premium % auto-stop. |
| `MIX-CF-USMAN-IN-TENOR-TIME-REOBS` | india | India adaptation: compare weekly vs near-expiry tenor buckets using OHLC + chain pricing proxies; no US 0DTE calendar assumptions. |

**Accepted:** observation-gated formalization; India `PARTIAL`; teacher WR claims null.  
**Rejected:** auto-inherit US digits/clocks/OF thresholds; STRAT-015+; claiming OpenAI fixed BT.  
**UNKNOWN / DATA_INSUFFICIENT:** timed VTT; Dhan historical OF/tape when of_required.
