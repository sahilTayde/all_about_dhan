# BIND — `6Bdv-_YUQ0s` · Usman Ashraf (Chart Fanatics)

**Team:** 01_research  
**Date:** 2026-09-06  
**Layer:** `SOURCE_FACT` (`ASR_WHISPER` — **not** YouTube captions)  
**Video:** https://www.youtube.com/watch?v=6Bdv-_YUQ0s  
**Title marketing:** “Options for Beginners” / “verified seven-figure” / host “profitable strategies” PDFs — **education + marketing**; product metrics stay null  
**MD transcript:** [`6Bdv-_YUQ0s_TRANSCRIPT.md`](6Bdv-_YUQ0s_TRANSCRIPT.md)  
**Raw ASR:** `data/transcripts/external_chart_fanatics/6Bdv-_YUQ0s.asr.txt`  
**Timed VTT:** `DATA_INSUFFICIENT` — anchors are **ASR paragraph order**, not clocks.  
**Origin tag for any MIX:** `EXTERNAL_RESEARCH` / Chart Fanatics guest — **not** `DHAN-DERIVED`.  
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
