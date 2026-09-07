# BIND — `T_djSNBmV00` · Marco (DaVinci return) (Chart Fanatics)

**Team:** 01_research  
**Date:** 2026-09-07 (OpenAI suggest + India portability pass)  
**Layer:** `SOURCE_FACT` (`ASR_WHISPER` — **not** YouTube captions) → formalization / grids = **`HYPOTHESIS`** until 06 validates  
**Video:** https://www.youtube.com/watch?v=T_djSNBmV00  
**MD transcript:** [`T_djSNBmV00_TRANSCRIPT.md`](T_djSNBmV00_TRANSCRIPT.md)  
**Timed VTT:** `DATA_INSUFFICIENT` — anchors are **ASR paragraph order**, not clocks.  
**OpenAI aid (HYPOTHESIS only):** [`../../../../data/recon/CF_OPENAI_MARCO-DAV_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_MARCO-DAV_BIND_SUGGEST_2026-09-07.md) — does **not** fix win rates.  
**Origin tag for any MIX:** `EXTERNAL_RESEARCH` / Chart Fanatics guest — **not** `DHAN-DERIVED`.  
**KEEP_ALL:** do **not** club into STRAT-001–014, IQCapital MIXes, prior `MIX-CF-*` (unless same guest refine), or `MIX-DEFAULT-BUY`. **No STRAT-015+.**  
**India decision:** `PARTIAL`

---

## Honesty banner

```text
layer: SOURCE_FACT (transcript) / HYPOTHESIS (named MIX formalization + BT grid)
guest: Marco (DaVinci return)
source: ASR_WHISPER faster-whisper — [ASR] caveat
india_transfer: HYPOTHESIS only — observation-gated; decision=PARTIAL
win_rates_spoken: CLAIMS only — product win_rate=null
education: not edge
openai_suggest: HYPOTHESIS aid only
NO_PROMOTE: true
```

---

## What this is **not**

| Claim | Verdict |
|-------|---------|
| Title / guest WR as product metric | **Rejected** — `win_rate=null` |
| Silent NIFTY inherit of US levels/OF thresholds | **Rejected** |
| STRAT-015+ | **Rejected** |
| Clubbing into unrelated prior MIX without founder ask | **Rejected** |
| “OpenAI fixed the backtests” | **Rejected** |
---

## OpenAI + India refresh — 2026-09-07

**OpenAI aid (HYPOTHESIS only):** [`../../../../data/recon/CF_OPENAI_MARCO-DAV_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_MARCO-DAV_BIND_SUGGEST_2026-09-07.md) — does **not** fix win rates.  
**India decision:** `PARTIAL` · of_required=True · ohcl_proxy_ok=True  
**Rationale:** Transcript is chart-pattern/timeframe logic and can be mapped to index underlying sweeps and directional option selection. However, specific execution mechanics (order types, liquidity map granularity, and exact intra-option mapping from swept underlying level to CE/PE pricing/strike delta) are not provided for India options. Therefore, we implement OHLC-only proxy: detect underlying sweep/take + engineered liquidity on index futures/spot OHLC, then translate to CE/PE buy-first direction with strike selection as a BT parameter grid (no invented lot/fill).  
**India analogs:** NIFTY/BANKNIFTY/SENSEX underlying (use spot or futures OHLC as proxy for sweep/take detection), Engineered liquidity swing highs/lows (use prior swing extremes on OHLC chart), Entry on liquidity sweep/take (use underlying low/high take event), CE/PE buy-first direction from underlying bias (bull => CE, bear => PE)  
**KEEP_ALL / NO_PROMOTE** · `win_rate=null` · no STRAT-015+ · soft news veto stays parked.

### Honesty banner (rev)

```text
openai_suggest: HYPOTHESIS aid only — does not fix WR / does not VALIDATION
magnet_or_level: observable|searchable — not sacred
market_scope: teacher_examples=US/NQ/etc; portable_if_observed=HYPOTHESIS
india_decision: PARTIAL
catalog_win_rate: null
NO_PROMOTE: true
{
  "what_is_traced": [
    "Engineered liquidity is a required gate; if missing, skip.",
    "Entry occurs after the opposite-side liquidity low/high is taken/swept ('once this low is taken… enter').",
    "Stop is beyond swept extreme; target is engineered liquidity extreme.",
    "Avoid over-refinement; missing entries is a key failure mode.",
    "If invalidated/early, wait for a fresh inducing/take event; direction idea not necessarily wrong."
  ],
  "what_is_not_in_transcript": [
    "No numeric thresholds (max tries, buffer size, exact 'engineered liquidity' candle pattern).",
    "No India/Dhan-specific option strike/expiry/lot/fill mechanics.",
    "No explicit win-rate; guest claims but win_rate remains null."
  ]
}
```

### Core edge (formalization · HYPOTHESIS)

{
  "claim": "Engineered Liquidity gate: only trade after price respects/engineers a liquidity pool (liquidity above highs for longs, liquidity below lows for shorts). Then enter on the sweep/take of the opposite-side low/high with a tight invalidation; avoid over-refinement that causes miss-entries.",
  "win_rate": null,
  "note": "All performance statements kept as guest claims; no win-rate invented."
}

### Observation protocol (HYPOTHESIS)

{
  "timeframe_logic": "Fractal: higher timeframe defines bias; lower timeframe provides entry timing. Common operational pairing mentioned: entry on 1m/5m targeting 15m/1h levels; CFDs can hold to higher timeframe targets (daily examples).",
  "liquidity_definition": {
    "engineered_liquidity_required": true,
    "for_long": [
      "Identify an upside objective liquidity area: a prior swing high that has respect on the left side (high respecting highs to the left).",
      "Wait for price to run up into/through that area and then show betrayal/reaction (sellers enter there; market communicates liquidity).",
      "Treat absence of engineered liquidity as a hard filter: 'If you don't see engineer liquidity, it's not a DaVinci model.'"
    ],
    "for_short": [
      "Invert logic: identify downside liquidity below prior swing lows; wait for price to run down and then react/betray (buyers enter there)."
    ]
  },
  "non_sacred_levels_policy": "Levels/magnets are observation-gated, not sacred constants. Re-observe per market/session."
}

### Entry models (HYPOTHESIS)

[
  {
    "model_id": "M-DAV-ENTRY-ENGINEERED-LIQ-THEN-SWEEP",
    "direction": "LONG",
    "setup_steps": [
      "Bias: determine direction from higher timeframe DaVinci context (engineered liquidity on upside).",
      "Engineered Liquidity gate: confirm price respects/engineers liquidity above prior highs (market reaction at/around that engineered-liquidity high).",
      "After engineered liquidity, wait for downside sweep/take: price must take the prior low/liquidity low (\"once this low right here is taken\").",
      "Entry trigger: enter at the moment the low is swept/taken (guest calls this 'your bi-position' at/around the low after it’s taken).",
      "Stop/invalidation: place stop below that swept low (tight; covers the left-side low).",
      "Target: buy to the engineered liquidity high (the liquidity you wanted to run into)."
    ],
    "entry_style": "Buy on sweep/take of the liquidity low after engineered liquidity is observed; do not over-refine additional imbalance at that low (over-refinement leads to missing entries).",
    "teacher_claim_bounds": "Exact entry price/structure micro-rules are not fully enumerated in transcript; the paper formalization uses only sweep/take + tight invalidation + engineered liquidity gate."
  },
  {
    "model_id": "M-DAV-ENTRY-ENGINEERED-LIQ-THEN-SWEEP",
    "direction": "SHORT",
    "setup_steps": [
      "Bias: determine direction from higher timeframe DaVinci context (engineered liquidity on downside).",
      "Engineer

### Miss-entry / recovery (HYPOTHESIS)

{
  "principles_from_transcript": [
    "No over-refinement at the sweep low/high: the guest warns that seeking extra imbalance/over-refinement can cause missed entries.",
    "If entry is early and price invalidates the sweep context, wait for the market to communicate again: 'I need to wait for something like this to occur again... early buyers inducing the market... taking out.'",
    "Recovery policy centers on re-appearance of the sweep/take event after invalidation, not on chasing current price."
  ],
  "formal_rules": {
    "max_chase": "After invalidation/failed sweep attempt, do NOT re-enter mid-leg; only re-enter on a fresh sweep/take of the relevant liquidity level after engineered liquidity remains valid.",
    "retrigger_event": "A new take/sweep of the liquidity low (for long) or liquidity high (for short) after engineered-liquidity reaction has been observed.",
    "skip_conditions_for_recovery": [
      "Engineered Liquidity gate not present (hard skip).",
      "Stop would be too far relative to target such that risk/reward no longer matches the intended asymmetric profile (risk parameterized in BT grid)."
    ]
  },
  "parameterizable_placeholders": {
    "retrigg

### Risk shell (HYPOTHESIS)

{
  "instrument_scope": "India index options paper/backtest intent: NIFTY/BANKNIFTY/SENSEX index options (CE/PE buy-first).",
  "position_concept_translation": "Use DaVinci direction (long/short underlying) to select CE (bullish underlying) or PE (bearish underlying). Entry occurs after the sweep/take event; target corresponds to prior engineered liquidity high/low; invalidation corresponds to stop beyond swept level.",
  "core_risk_parameters_to_bt": [
    "risk_per_trade_bp (e.g., 50–150 bp) [placeholder for BT]",
    "stop_distance_type: 'beyond swept level' (covers left-side extreme) [in t

### Market portability

{
  "scope_claim_from_transcript": "Works on any asset/timeframe (guest claim).",
  "paper_constraints": "We cannot validate win-rate or fill assumptions. Portability tested via BT on India index options using OHLC proxy mapping."
}

### Backtest search grid (for 06)

{
  "market": [
    "NIFTY index options (CE/PE) with underlying OHLC proxy",
    "BANKNIFTY index options (CE/PE) with underlying OHLC proxy",
    "SENSEX index options (CE/PE) with underlying OHLC proxy"
  ],
  "engineered_liquidity_gate": {
    "swing_lookback": [
      20,
      30,
      45,
      60
    ],
    "reaction_definition": [
      "engineered swing high/low followed by immediate reversal candles (proxy: close back through level or wick rejection)",
      "engineered level touched then subsequent swing break in opposite direction within N bars (BT parameter)"
    ],
    "min_retest_bars": [
      1,
      2,
      3
    ]
  },
  "sweep_take_event": {
    "take_definition": [
      "wick pierces beyond prior extreme then close back",
      "close breaches beyond prior extreme"
    ],
    "extreme_source": [
      "most recent left-side swing extreme",
      "swing extreme within last K bars"
    ],
    "entry_timing": [
      "enter on first take candle",
      "enter on 

### Proposed MIX ids (KEEP_ALL)

| mix_id | role | note |
|--------|------|------|
| `MIX-CF-MARCO-DAV` | teacher | DaVinci Universal Model: engineered-liquidity gate + sweep/take entry with tight invalidation; invert for shorts. |
| `MIX-CF-MARCO-DAV-IN-OHLC-SWEEP-CEPE` | india | India adaptation via OHLC-only proxy: detect engineered liquidity + sweep/take on index OHLC; buy CE/PE directionally with BT strike/expiry parameters. |

**Accepted:** observation-gated formalization; India `PARTIAL`; teacher WR claims null.  
**Rejected:** auto-inherit US digits/clocks/OF thresholds; STRAT-015+; claiming OpenAI fixed BT.  
**UNKNOWN / DATA_INSUFFICIENT:** timed VTT; Dhan historical OF/tape when of_required.
