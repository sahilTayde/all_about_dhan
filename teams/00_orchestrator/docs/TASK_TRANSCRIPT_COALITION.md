# TASK — Transcript coalition (SOURCE_FACT by slice)

**Date opened:** 2026-09-03  
**Assigned:** 01_research (sliced) → 02/03 VALIDATION → 04 HYPOTHESIS  
**Status:** `IN_PROGRESS` (OPTIONS_INDEX **done**; EQUITY English **second pass** 2026-09-03; STRAT English bind **applied** to ENGINE_MIX 2026-09-03; catalog `STOCK_ONLY` titles still no EN)  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

English transcripts live in `data/transcripts/normalized_en/`. Prefer those over Hindi ASR. Do **not** overwrite Hindi `SOURCE_FACT`. No LLM translation. No algos. No fake win rates.

---

## Slices

| Slice | Owner intent | Status | Artifact |
|-------|--------------|--------|----------|
| **OPTIONS_INDEX** | NIFTY / BANKNIFTY / SENSEX index options, CE/PE buy, chain, expiry, selling corpus, OF overlay | **EXTRACTED** 2026-09-03 | [`OPTIONS_INDEX_PACKET.md`](../../01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md) |
| **STRAT bind** | Re-read English tape vs STRAT-001–014 + ENGINE_MIX clubs | **EXTRACTED** 2026-09-03; 04 **applied** | [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) |
| EQUITY / STOCK_ONLY | Scanners, BTST, swing-stock, same-stock intraday | **EXTRACTED** (EN on disk) 2026-09-03; catalog `STOCK_ONLY` **9** still `TRANSCRIPT_PENDING` | [`EQUITY_ETF_PACKET.md`](../../01_research/docs/handoffs/EQUITY_ETF_PACKET.md) |
| TRANSFERABLE_TA | RSI/ST, candles, VWAP scalp, 43 indicators | **EXTRACTED** | [`TA_STRUCTURE_PACKET.md`](../../01_research/docs/handoffs/TA_STRUCTURE_PACKET.md) · [`TRANSFERABLE_AND_SKIPPED.md`](../../01_research/docs/handoffs/TRANSFERABLE_AND_SKIPPED.md) |

---

## OPTIONS_INDEX (this slice)

**Priority IDs (English files present):**

| video_id | role | Per-video |
|----------|------|-----------|
| `HAUSZx-hYdY` | Option **buying** masterclass | [`HAUSZx-hYdY.en.md`](../../01_research/docs/handoffs/HAUSZx-hYdY.en.md) (Hindi file kept) |
| `_exmJYgFwFA` | Option **selling** masterclass (was PENDING) | [`_exmJYgFwFA.md`](../../01_research/docs/handoffs/_exmJYgFwFA.md) |
| `DzT_681GThA` | Order-flow A–Z (Reliance demo; volume-delta ≠ Greek) | [`DzT_681GThA.md`](../../01_research/docs/handoffs/DzT_681GThA.md) |
| `8h9SYvQWKMA` | Dhan Charts walkthrough (chain-on-chart, ATM CE/PE UI) | [`8h9SYvQWKMA.md`](../../01_research/docs/handoffs/8h9SYvQWKMA.md) |

**Also in packet (EN deltas, Hindi not overwritten):** `2RnBT9DDDNI`, `6el9Jqnrdz8`, `gA5FtEnSABM`, `pvmvkiS1cx4`, `YUXJv_xBStw`, `6WZxLShiUT8`.

**Skipped here (equity / other):** `4TT8IV5S1_A`, `_byuht38r5s`, `pBQ1oVDVe3M`, `G31RFueZLvk`, `dEvF8biE02M` — **now in the equity packet** (per-video files). Do **not** use them as Phase-1 index evidence.

### What 02/03/04 must do (OPTIONS_INDEX)

- **02:** `VALIDATION` only — do not rewrite quotes.
- **03:** expiry/lots **now**; VWAP-on-index pitfall.
- **04:** existing STRAT-001–014 stay `UNVALIDATED`. No new IDs. Selling stays **WAITING**. Cite [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md); keep `PROJECT_MIX` labeled (003+007+009 AND, 5m MACD confirm-or-kill).

---

## EQUITY (second pass, 2026-09-03)

Per-video: `_byuht38r5s`, `4TT8IV5S1_A`, `pBQ1oVDVe3M`, `G31RFueZLvk`, `dEvF8biE02M`, `EVk_Wa_1cm0`.  
04 slots `EQ-014` / `SO-003` stay `UNVALIDATED`. Catalog `STOCK_ONLY` titles still have **no** English file.

### What 02/03/04 must do (EQUITY)

- **02:** RSI 50–75 vs “5 to 75”; Hull 32; ST 7×3 vs 10×3; three different “40%” in `dEv`.
- **03:** F&O stock list dated; delivery % series; overnight option gap SL.
- **04:** keep `EQ-*` / `SO-*` **out** of the index book. No STRAT-015+.

### Must not

- Invent win rates or algos.
- Treat Dex OF history as HQ REST (`DATA_INSUFFICIENT`).
- Use STOCK_ONLY English files as Phase-1 index-option evidence.
- Copy G31 / dEv guest percents into a performance table.

---

## Ticket hygiene

Coalition is **research extraction**, not a live-Dhan or npm task. Nightly / CAS / 3m chain unchanged.
