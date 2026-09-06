# SL/TP EXTERNAL HARVEST — IQCapital + classic exits

**Team:** 01_research  
**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (transcripts / API metadata) · `HYPOTHESIS` (NIFTY transfer) · `EXTERNAL` / `PROJECT-DERIVED`  
**Not** `DHAN-DERIVED`. **Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. No win rates claimed.

Channel discovered via YouTube Data API: **IQCapital** `UCa8rgzIMKFx2uJHVsf0oqjg` · handle **`@iqcapital_io`** · ~41k subs · 78 videos listed (77 uploads paged).

Artifacts: `data/recon/iqcapital_upload_list.json`, `data/recon/iqcapital_transcript_attempt.json`, `data/transcripts/external_iqcapital/*.en.txt`.

---

## 1. Videos fetched (attempt inventory)

| Video ID | Title | Channel | Views (approx) | Published | Transcript | Why / notes |
|----------|-------|---------|---------------:|-----------|------------|-------------|
| `PL7LKUsCgIQ` | Trading WORLD CHAMPION Reveals the Orderflow Strategy That Won the Robbins Cup (Step-by-Step) | @iqcapital_io | **1,136,248** | 2026-08-11 | **full** (~58k chars) | Robbins Cup + orderflow + **GEX/naive GEX** spoken |
| `2hyqdVF0JVk` | 12x CHAMPION Reveals His “3-TOUCH” Strategy That Won Robbins Cup (Step-by-Step) | @iqcapital_io | 246,422 | 2026-08-28 | **full** (~37k) | Patrick Nill; structure → stops/targets; RR example |
| `XWJlBBikUc0` | Ex-Hedge Fund Manager Trades His $150M VWAP Strategy Live (Full Breakdown) | @iqcapital_io | 169,427 | 2026-08-14 | **full** (~45k) | VWAP; host line “10 tick stop / 10–15 tick target” (DESCRIPTION + spoken) |
| `HUYBdYnXUNc` | World's #1 Scalper Just Gave Away His ENTIRE New Strategy for FREE (Live On Chart) | @iqcapital_io | 166,615 | 2026-08-19 | **full** (~31k) | Fabio Valentini; scalping ticks / absorption |
| `2ZmIn274eds` | Best Trader in the World Reveals His Exact Strategy LIVE on Charts! — Patrick Nill | @iqcapital_io | 158,743 | 2026-06-26 | **full** (~29k) | Targets vs stops as separate decisions; impulse targets |
| `hxr27ckfOqA` | Ex-Hedge Fund Manager Reveals His $150M Scalping Strategy (Live On Chart) | @iqcapital_io | 99,786 | 2026-07-17 | **full** (~46k) | VWAP anchor; accept stop then reverse |
| `401McJbow6o` | I Challenged Fabio Valentini’s Trading Method (It Didn’t Go Well) | @iqcapital_io | 98,263 | 2026-08-21 | **full** (~69k) | Automation / 1:1 R:R trigger tests; GEX confluence mentioned |
| `EjRoPJgs_Dg` | He MADE the World's BEST Trader. THIS is his Strategy! (LIVE on Charts) | @iqcapital_io | 26,488 | 2026-07-03 | **not fetched this pass** | Listed in search; deferred |
| `r7c7HeTXuC4` | This Stupid Simple Strategy Made Him a Top 5 Trader in the World (Live on Chart) | @iqcapital_io | 18,238 | 2026-07-10 | **full** (~38k) | 2–3 touches; targets/stops asked on tape |
| `sjsM8BC5jnc` | Do Algorithms Hunt Your Stops? | @iqcapital_io | 9,719 | 2026-08-14 | **partial** (~481 chars) | Short / auto-caption thin |
| `CdUwmz-yB5s` | I Ranked 5 Trading Styles for Prop Trading | @iqcapital_io | 5,121 | 2026-06-02 | **not fetched this pass** | Search hit only |
| `Hs_JmvWrLJw` | The EXACT Strategy Behind a Six Figure Gamma Trader | @iqcapital_io | 4,440 | 2026-05-29 | **full** (~44k) | **Positive/negative gamma**; RR ≥ 2; dynamic target = next option wall / gamma flip |
| `cAE63SSQF0Y` | Stop Trading Naked Charts — Use This Instead | @iqcapital_io | 3,863 | 2026-08-28 | **not fetched** | Keyword hit only |
| `b6X0mmBjqRg` | STOP Trading With Naked Charts! | @iqcapital_io | 3,394 | 2026-08-09 | **not fetched** | Keyword hit only |
| `A7fS0YbwHww` | Nobody is Hunting your Stop Loss! | @iqcapital_io | 3,001 | 2026-08-07 | **partial** (~683) | Thin captions |
| `7AO3dSH9HKw` | This Trader NEVER Looks at Charts – And Trades Six Figures | @iqcapital_io | 2,767 | 2026-06-05 | **not fetched** | Search hit |
| `BZsX5yy7--s` | Stop Making This Trading Mistake | @iqcapital_io | 2,145 | 2026-08-31 | **not fetched** | Keyword hit |
| `Dgn2M3ZgzdU` | THIS is how you REALLY get Funded in 2026 | @iqcapital_io | 1,853 | 2026-06-16 | **not fetched** | Search hit |
| `bioVf3Ex74o` | Stop paying for trading signals. | @iqcapital_io | 553 | 2026-05-31 | **not fetched** | Keyword hit |

**Transcript method:** `youtube_transcript_api` (en). Shorts → partial. No fabricated quotes.

**Blockers / honesty:** yt-dlp not installed in workspace; pip needed `--user` + unrestricted FS. GEX spoken is **US-index / futures dealer gamma** context — **not** a NIFTY OPTIDX GEX feed (`DATA_INSUFFICIENT` for India transfer).

URLs: `https://www.youtube.com/watch?v=<id>`.

---

## 2. SOURCE_FACT extracts (spoken — not params for NIFTY)

### `PL7LKUsCgIQ` (Robbins Cup orderflow + GEX) — SOURCE_FACT

- Process named on tape: market structure → **gamma / GEX (naive GEX)** for volatility → volume profile for location → **order flow** for entry timing.
- Stop placement example: stop on the **other side of failed sellers** (invalidation of the trade idea).
- GEX flavors mentioned: **naive GEX** vs **inferred GEX** (spoken distinction; formulas not fully frozen here).

### `Hs_JmvWrLJw` (gamma trader Manuel) — SOURCE_FACT

- Distinguishes **positive gamma** vs **negative gamma**.
- **No fixed stop** preferred; sizes risk so **risk:reward ≥ ~2:1** (“more than two to one is always good for me”).
- Profit target **dynamic**: next option level / **call wall** / **gamma flip**.
- Confirmation: order-flow **absorption** at area of interest.

### `2hyqdVF0JVk` / `2ZmIn274eds` (Patrick Nill) — SOURCE_FACT

- Model uses structure of the move for **entries, stops, and targets**.
- Example spoken: large target vs ~30–40 point stop → RR **> 3** (illustration, not a NIFTY recipe).
- “3-touch” / multi-touch structure discussed across interviews.

### `XWJlBBikUc0` / `hxr27ckfOqA` (VWAP scalp) — SOURCE_FACT / DESCRIPTION_ONLY mix

- VWAP as main anchor; mean-reversion reactions to VWAP.
- Host packaging line cites **10 tick stop** and **10–15 tick target** (verify as host voice vs guest — treat tick sizes as **UNDERDEFINED** for NIFTY points).

### Fabio interviews — SOURCE_FACT

- Scalp style: small tick targets vs one stop; order-flow absorption / value migration. Tick geometry is **NQ/futures context**, not NIFTY OPTIDX lots.

---

## 3. HYPOTHESIS (desk — clearly separated)

| Hypothesis | Tag |
|------------|-----|
| Club VWAP/session lean (existing stack) + **ATR(14)×k stop** + **RR≥2 target** as computable proxy for “structure invalidation + RR≥2” when NIFTY OF/GEX absent | `PROJECT-DERIVED` → `MIX-DESK-IQ-ATR-RR2` |
| Naive/inferred GEX as **hold filter** only on NIFTY until an India GEX source exists | `DATA_INSUFFICIENT` transfer |
| Map “ticks” → NIFTY index points via ATR multiple, not 1:1 tick | `HYPOTHESIS` |

---

## 4. Teacher STRAT exits already on book (inventory — DHAN-DERIVED)

| ID | Exit (from candidates) | Layer |
|----|------------------------|-------|
| STRAT-001 | Underlying **recent swing**; EOD flatten | SOURCE_FACT bind |
| STRAT-002 | Target **20–30% entry premium**; swing stop; MA trail | SOURCE_FACT; never on 003 |
| STRAT-003 | Exit **3m close through Supertrend**; prefer RR 2.0; ATR inside ST only | SOURCE_FACT + WEAK “103” |

Hardcoded `STOP_PTS` in `ticket_confidence.py` was **desk placeholder**, not a named teacher method.

---

## 5. HANDOFF

```text
HANDOFF
From:     01 research
To:       02 / 03 / 04 / 06 / 09 / 00
Accepted: @iqcapital_io channel ID + 11 transcript attempts (9 full, 2 partial);
  Robbins Cup OF+GEX video >1M views; gamma RR≥2 + call-wall targets as SOURCE_FACT;
  KEEP_ALL teacher exits unchanged.
Rejected: Invented quotes; claiming GEX works 1:1 on NIFTY; STRAT-015+; win rates.
UNKNOWN: India GEX tape; exact naive-GEX formula; tick→NIFTY point map; Fabio/Nill
  as customer default.
```
