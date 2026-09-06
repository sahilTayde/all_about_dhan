# Rolling option history — STRAT-005 / STRAT-002 strike map

**Team:** 03_phd_market  
**Date:** 2026-09-03  
**Layer:** `SOURCE_FACT` (HQ page) / `VALIDATION` (this map) / `HYPOTHESIS` (fill + ATM±N proxy) — do not collapse  
**Status:** `DRAFT` / `UNVALIDATED`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**No Python in this ticket. No live orders. No invented fills, lots, or win rates.**

Official page (fetched 2026-09-03): [Expired Options Data](https://dhanhq.co/docs/v2/expired-options-data/).  
Annexure enums: [Annexure](https://dhanhq.co/docs/v2/annexure/).  
Rate table: [`packages/dhan-client/docs/RATE_LIMITS.md`](../../../packages/dhan-client/docs/RATE_LIMITS.md).  
Scrips: [`config/workspace.yaml`](../../../config/workspace.yaml) `markets[]` — **VERIFY FROM instrument master**, not eternal. Live IDX_I probe: [`LIVE_DATA_2026-09-03.md`](LIVE_DATA_2026-09-03.md).

Coalition cites (do not skip):

| Team | File |
|------|------|
| 01 | [`DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) § Expired options; [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) STRAT-002 / 005 |
| 02 | [`STRAT_001_014_VALIDATION.md`](../../02_phd_math/docs/STRAT_001_014_VALIDATION.md) — delta ≠ win rate; ablate 002 vs 005; vendor greeks `UNKNOWN`. Premium path: [`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md) (rollingoption OHLC = P/L object; Q8 not waived; not a promote) |
| 04 | [`STRAT-002.md`](../../04_quant/docs/candidates/STRAT-002.md), [`STRAT-005.md`](../../04_quant/docs/candidates/STRAT-005.md), [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) (002 **never** on 003), [`ALGO_HANDOFF.md`](../../04_quant/docs/ALGO_HANDOFF.md) `fill` |
| 05 | [`CHAIN_METRICS.md`](CHAIN_METRICS.md) ATM = closest to `last_price` on a **live** chain snapshot — different object from rolling ATM |
| 06 | [`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md) — option P/L still null; this file is the **map**, not a book |
| 09 | [`BACKTEST_REVIEW_2026-09-03.md`](../../09_review/docs/BACKTEST_REVIEW_2026-09-03.md) Q8 not waived |

Skeleton `OptionChainClient.rolling_expired` still raises. Founder override: `packages/dhan-client` `HistoricalClient.rolling_option` **is** the wired path. 03 still writes no Python in this file. KEEP_ALL: STRAT-001–014 stay `BACKTEST_BOOK`.

---

```text
HANDOFF
From:     teams/03_phd_market
To:       00_orchestrator / 02_phd_math / 04_quant / 06_backtesting / 09_review
Date:     2026-09-03
Status:   DRAFT / UNVALIDATED — live rollingoption expiryCode VALIDATION
Gate:     NOT RESEARCH_READY_FOR_PROGRAMMING

Accepted:
- SOURCE_FACT unchanged: annexure lists expiryCode 0=near, 1=next, 2=far.
- VALIDATION 2026-09-03 live POST /charts/rollingoption: JSON expiryCode `0`
  → DhanApiError "expiryCode is required". expiryCode `1` → data
  (NIFTY OPTIDX ATM CALL WEEK, 1617 5m bars for 2026-08).
- Layers stay split. Annexure 0 is not rewritten as 1=near.
- Founder override: HistoricalClient.rolling_option is wired.
  OptionChainClient.rolling_expired still raises.
- 02 charter [`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md):
  P/L object = rollingoption OHLC; not a book; Q8 not waived.
- KEEP_ALL: 002 and 005 stay alternative books. 002 never on a 003 ticket.

Rejected:
- Collapsing SOURCE_FACT (annexure 0) with VALIDATION (API rejects JSON 0).
- Invented fills, lots, win rates. Live orders. RESEARCH_READY_FOR_PROGRAMMING.
- Deleting STRAT-002/005. Treating 1617 bars as option P/L or a promote.

UNKNOWN / DATA_INSUFFICIENT:
- Whether annexure 0=near is a docs bug or a JSON-zero drop. Whether working
  `1` is annexure “next” or the only accepted near-week sheet.
- BANKNIFTY / SENSEX rollingoption. Bid/ask. Costs. Files ingested on disk.

Review: notes only
```

---

```text
HANDOFF
From:     teams/03_phd_market
To:       00_orchestrator / 02_phd_math / 04_quant / 06_backtesting / 09_review
Date:     2026-09-03
Status:   DRAFT / UNVALIDATED — rollingoption map only
Gate:     NOT RESEARCH_READY_FOR_PROGRAMMING

Accepted:
- POST /charts/rollingoption is the HQ expired/rolling OPTIDX tape (5y, 30d/call).
- STRAT-005 ITM proxy: CE ATM-2, PE ATM+2.
- STRAT-002 OTM proxy: CE ATM+1, PE ATM-1.
- Fill: next option open. Exit: option close. Costs UNKNOWN.
- Data API rate 5/s. NIFTY 13 NSE_FNO, BANKNIFTY 25 NSE_FNO, SENSEX 51 BSE_FNO.
- 002 and 005 stay alternative books. 002 never on a 003 ticket.

Rejected:
- Merging 002+005 into one strike. Treating rolling ATM±N as a locked security_id hold.
- Invented brokerage/STT/spread rupees. Live orders. Python fetcher in this ticket.
- Cash-index volume. 3m as an HQ interval. Frozen lots / expiry weekdays.

UNKNOWN / DATA_INSUFFICIENT:
- Ingested rolling bars in this repo (endpoint documented; files not pulled).
- Whether each bar is a held contract or a moneyness bucket that rolls with spot
  (docs: stored relative to spot). Vendor IV methodology. Bid/ask (not in requiredData).
- BANKNIFTY WEEK series (monthly-only regime VERIFY). ATM±10 vs ATM±3 cutoff
  (“near expiry”) as an exchange clock. securityId JSON type string vs int.

Review: notes only
```

---

## 1. SOURCE_FACT — DhanHQ `POST /charts/rollingoption`

Path: `/charts/rollingoption` (v2). Docs title: expired options on a **rolling** basis (ATM relative to spot, up to 10 strikes above/below). Index **and** stock options exist on the page; Phase-1 uses **`instrument: OPTIDX` only**.

| Request field | Documented values | 03 note |
|---------------|-------------------|---------|
| `exchangeSegment` | annexure enum; example `NSE_FNO` | SENSEX options: **`BSE_FNO`**. Not `IDX_I`. |
| `interval` | `1`, `5`, `15`, `25`, `60` | Same HQ chart enum as other `/charts/*`. **No 3m / 2m token.** |
| `securityId` | underlying exchange-standard ID; example `13` | Table type **string**; example is a number. **VERIFY**. |
| `instrument` | annexure; example `OPTIDX` | Do not send `OPTSTK` for this book. |
| `expiryFlag` | `WEEK` \| `MONTH` | BANKNIFTY weekly discontinued under one-weekly-per-exchange — **VERIFY**; prefer `MONTH` until the master says otherwise. |
| `expiryCode` | `0` current/near, `1` next, `2` far ([annexure](https://dhanhq.co/docs/v2/annexure/)) | **SOURCE_FACT stays 0=near.** Do not rewrite annexure. Live VALIDATION 2026-09-03: JSON `0` rejected — see §2. Do not freeze 1/2 as the spoken recipe. |
| `strike` | `ATM` … `ATM+10` / `ATM-10` (index options **near expiry**); **`ATM±3`** for all other contracts | 005 `ATM-2` / 002 `ATM+1` sit inside **both** caps. |
| `drvOptionType` | `CALL` \| `PUT` | One side per call. Sample response puts the unused side `null`. |
| `requiredData` | `open`, `high`, `low`, `close`, `iv`, `volume`, `strike`, `oi`, `spot` | Request **all nine**. Response *parameter table* lists only OHLC / volume / timestamp — extra arrays are in the **request enum + sample**; types **VERIFY**. |
| `fromDate` / `toDate` | `YYYY-MM-DD` | **`toDate` is non-inclusive** (page). Sample `2021-08-01` → `2021-09-01` is August, not 1 Sep. |
| Window / depth | **30 days per call**; history **up to 5 years**; minute-level | Chunk dates. Do not invent a sixth year. |

**Not on this page:** bid, ask, greeks, lot, `security_id` of the option, brokerage. Live chain remains `POST /optionchain` (1 unique / 3 s) — a **different** budget and object.

---

## 2. VALIDATION — live `POST /charts/rollingoption` (2026-09-03)

This layer is **not** the annexure. Do **not** collapse it into §1.

| Probe | Result | Layer |
|-------|--------|-------|
| JSON `expiryCode`: **`0`** | `DhanApiError` **"expiryCode is required"** | `VALIDATION` |
| JSON `expiryCode`: **`1`** | **Data returned** — NIFTY `OPTIDX` **ATM** **CALL** **WEEK**, **1617** 5m bars for **2026-08** | `VALIDATION` |
| Annexure still lists **0=near, 1=next, 2=far** | Unchanged HQ enum | `SOURCE_FACT` (§1) |

03 does **not** conclude that annexure `0` was never “near,” or that working `1` is the near-week sheet. Possible readings stay `UNKNOWN`: docs bug, JSON-zero drop, or “next” is the only accepted code on this POST. Spoken 002/005 overlay still does not freeze far-month (`2`).

This is **not** option P/L, not a fill, not lots, not a win rate. KEEP_ALL: 002 and 005 stay separate books. Gate stays **not** `RESEARCH_READY_FOR_PROGRAMMING`. 02 charter for scoring this tape: [`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md).

Wired client (founder override): `HistoricalClient.rolling_option`. Skeleton `OptionChainClient.rolling_expired` still raises. 03 wrote no Python here. No live orders.

---

## 3. VALIDATION — underlyings (rolling body ≠ chain body)

Yaml `markets[]` maps cash-index **IDX_I** scrips 13 / 25 / 51. The rollingoption **example** is `exchangeSegment: NSE_FNO` + `securityId: 13`. 03 map for this endpoint:

| Underlying | `securityId` | `exchangeSegment` | Yaml option quote seg | Do not send |
|------------|--------------|-------------------|------------------------|-------------|
| NIFTY | **13** | **`NSE_FNO`** | `NSE_FNO` | Mixing BSE volume into NSE |
| BANKNIFTY | **25** | **`NSE_FNO`** | `NSE_FNO` | Assuming a live WEEK sheet |
| SENSEX | **51** | **`BSE_FNO`** | `BSE_FNO` | NIFTY strike step / lot / client |

**CONFIRMED 2026-09-03** as working **IDX_I** ids for LTP/chain (`LIVE_DATA_2026-09-03.md`). That LTP/chain probe did **not** call rollingoption. A later **2026-09-03** rollingoption POST did (NIFTY 13 / `NSE_FNO` / expiryCode `1` — §2). Re-read the instrument master before treating 13/25/51 as forever.

Chain poll still uses `UnderlyingSeg: IDX_I`. Rollingoption uses **FNO segment + same integer**. Do not collapse the two request shapes.

Lots / expiry weekday: **`FROM_CONTRACT`**. Index options are **European, cash-settled**. VWAP on **cash index volume** stays unsupported; this tape is **OPTIDX** premium (+ documented `spot` / `strike` arrays).

---

## 4. VALIDATION — moneyness geometry (spot, not futures)

Call ITM = strike **below** spot. Put ITM = strike **above** spot. HQ `ATM` is **relative to spot** on this API (page copy). Spoken 005: strike from **spot at signal**, not the futures chart ([`STRAT_001_014_MARKET.md`](STRAT_001_014_MARKET.md)).

| Overlay | Side | HQ `strike` | Spoken bind (01) | What this is |
|---------|------|-------------|------------------|--------------|
| **STRAT-005** ITM | CE / `CALL` | **`ATM-2`** | ITM / max ATM; “two in the money”; fallback nearest ATM or 1 ITM; \|delta\| ~0.60–0.75 **WEAK** | **2-strike ITM** end of the 1–2 ITM grid. **Not** a proven 0.60–0.75 print. |
| **STRAT-005** ITM | PE / `PUT` | **`ATM+2`** | Puts = negative of the call band | Same 2-step ITM, opposite wing. |
| **STRAT-002** OTM | CE / `CALL` | **`ATM+1`** | Slightly OTM **1 or 2** strikes; ATM “pumped”; adverse ~0.40 delta | **1-strike OTM** end of the 1–2 OTM grid. |
| **STRAT-002** OTM | PE / `PUT` | **`ATM-1`** | Same 1–2 OTM | Same 1-step OTM, opposite wing. |

**Keep separate (03 already objected to a merge):**

- 005 **ATM-1 CE / ATM+1 PE** (1 ITM fallback) and 002 **ATM+2 CE / ATM-2 PE** (2 OTM) stay **06 search-grid rows**, not this default map.
- **STRAT-006** 100–200 pt ITM is a third hypothesis — **not** ATM-2. Do not encode it here.
- **002 never overlays 003.** 003 default strike is **005 only** (`ENGINE_MIX`). A 002 rolling series on a 003 signal is a spec fail, not a test.

ATM on the **3m chain** (`CHAIN_METRICS.md`) is closest strike to `last_price` on that snapshot. Rolling `ATM` is HQ’s **spot-relative bucket**. They can disagree by a step when spot vs futures basis is wide — **UNKNOWN** magnitude; do not invent a basis haircut.

---

## 5. HYPOTHESIS — fill, exit, costs (06)

This is the **paper/backtest convention** for this tape. It is **not** a live fill, not an ask, not a futures open.

| Leg | Rule | Object |
|-----|------|--------|
| **Entry** | **Next option open** | After the **closed** signal bar, take `open` on the **next** rollingoption bar for the mapped `strike` + `drvOptionType`. Not index/FUTIDX open. Not LTP. |
| **Exit** | **Option close** | `close` of the rollingoption bar on which the host book flattens (ST flip, 20–30% premium, clock, EOD). Not a touch-stop. |
| **Costs** | **`UNKNOWN`** | Do **not** subtract brokerage, STT, GST, stamp, or half-spread. [`DESK_EXECUTION_NOTES.md`](DESK_EXECUTION_NOTES.md) names those classes; this repo has **no** rupee model. 04 YAML `fill: next_bar_open_or_conservative_ask` is **stricter** than this map (ask is `DATA_INSUFFICIENT` here — not in `requiredData`). |

Look-ahead on an unclosed bar: **forbidden** (same as `ALGO_HANDOFF.md`).

**Moneyness bucket vs held contract (do not collapse):** HQ stores bars by strike **relative to spot** (ATM, ATM+1, …). If spot walks one step, `ATM-2` on bar T+10 may be a **different strike** than the contract whose `open` you used at entry. `requiredData.strike` tells you the printed strike **that minute**. Locked-`security_id` hold path = **`DATA_INSUFFICIENT`** on this endpoint until 06 proves otherwise. Score this map as **bucket P/L** unless a later VALIDATION says the series is sticky.

09 Q8 stays open until option premium (this tape or better) actually scores. INDEX/FUTIDX proxy points are **not** this map.

---

## 6. Rate, chunking, clocks

| Rule | Value |
|------|--------|
| Bucket | **Data APIs — 5 requests / second** (official intro). Same gate as `/charts/historical` and `/charts/intraday`. **Not** the option-chain 1 unique / 3 s. **Not** Order APIs (unused; `place_order` refused). |
| Day cap | Data APIs **100000 / day** (intro). Do not burst. |
| Chunk | ≤ **30 calendar days** per call; `toDate` exclusive. 5y ≈ many windows per (underlying × interval × flag × code × strike × CALL/PUT). |
| Signal TF | 003 spoken **3m** is **not** in the enum — fetch **1m** option bars if 06 resamples; do not send `interval: 3`. 004’s 1m **is** native. |

Expiry afternoon: OTM (002) theta + CAS cash 15:15–15:35 vs F&O **15:40 VERIFY** — risk comment, not a new HQ field ([`STRAT_001_014_MARKET.md`](STRAT_001_014_MARKET.md)). Flatten clock stays parameterized.

---

## 7. What 06 may request (shape only — 03 writes no Python)

Wired path is `HistoricalClient.rolling_option` (founder override). Skeleton `OptionChainClient.rolling_expired` still raises. This section is **annexure-shaped** (§1), not a claim that JSON `0` works.

One CE 005 window (illustrative field names from the docs page; **not** a live call):

```text
exchangeSegment  NSE_FNO          # BSE_FNO if SENSEX
interval         1                # or 5 / 15 / 25 / 60
securityId       13               # 25 BANKNIFTY; 51 SENSEX
instrument       OPTIDX
expiryFlag       WEEK             # MONTH if that is the listed sheet
expiryCode       0                # SOURCE_FACT annexure near; live VALIDATION: JSON 0 rejected, working probe used 1 (§2)
strike           ATM-2            # 005 CE; PUT uses ATM+2
drvOptionType    CALL
requiredData     open,high,low,close,iv,volume,strike,oi,spot
fromDate / toDate  (toDate non-inclusive, ≤30d span)
```

Mirror for 002 CE: `strike: ATM+1`. Puts: flip `drvOptionType` and the ATM sign in §4.

Empty `DHAN_*` → **fixtures only**. Do not invent OHLC. Do not place orders when tokens exist.

---

## 8. UNKNOWN / leave for other teams

| Item | Owner |
|------|--------|
| Vendor IV / whether `iv[]` matches chain `implied_volatility` | 02 |
| Delta band 0.60–0.75 vs ATM-2 identity | 02 — **WEAK**; this map does **not** prove it |
| Ingest + score OOS + `NORMAL` on **option** P/L | 06 — `HistoricalClient.rolling_option` is wired; 06 still must ingest+score. Not a promote. |
| Annexure `expiryCode` 0 vs live JSON-0 reject | 03 — layers stay split; do not rewrite annexure. 02 [`OPTION_PREMIUM_VALIDATION.md`](../../02_phd_math/docs/OPTION_PREMIUM_VALIDATION.md) still names this tape as the P/L object |
| 002 vs 005 ablation on the **same** 001 signals | 04 spec already; 06 runs; do not merge here |
| Bid/ask conservative fill | `DATA_INSUFFICIENT` on this endpoint |
| `RESEARCH_READY_FOR_PROGRAMMING` | 09 five-pass — **not** this file |
