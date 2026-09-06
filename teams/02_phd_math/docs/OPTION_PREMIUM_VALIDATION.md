# OPTION PREMIUM VALIDATION — rollingoption OHLC vs INDEX 3m all-three

**Team:** 02_phd_math  
**Layer:** `VALIDATION` (charter). P/L numbers do **not** exist in this file.  
**Status:** `DRAFT` / `UNVALIDATED`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. Notes ≠ five-pass. Q8 **not** waived until 06 actually scores this tape.  
**No code this ticket.** No live Dhan. No invented win rates, lots, or fills.

This is the honest **option-premium** path that the 2026-09-03 INDEX/FUTIDX **points proxy** is not ([`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md) `option_pnl: null`). Lean stays the existing **INDEX 3m all-three**. Money is **OPTIDX** OHLC from HQ `POST /charts/rollingoption`.

---

```text
HANDOFF
From:     teams/02_phd_math
To:       teams/06_backtesting ; teams/03_phd_market ; teams/04_quant ; teams/09_review ; teams/05_analysis
Date:     2026-09-03
Status:   VALIDATION charter / UNVALIDATED / not a run
Gate:     not RESEARCH_READY_FOR_PROGRAMMING — Q8 not waived by this file

Accepted:
- P/L object = rollingoption OHLC (OPTIDX), aligned to INDEX 3m all-three leans.
- Fill = next 3m option bar OPEN (no look-ahead on the signal close).
- Exit = lean leave (SKIP or opposite) at next option OPEN, or flatten 15:15 IST (009 spoken filter).
- Strike grid ONLY two cells from STRAT-005 no-delta fallback: ATM vs two-strikes ITM
  (CE → ATM-2, PE → ATM+2). Do not pick a winner on IS.
- OOS = last 20% of trades. Need ≥30 IS and ≥30 OOS. OOS wr < 45% → FAIL.
- Supertrend 10,3 stays WEAK inference. Do not p-hack ATR/period after seeing premium wr.
- Costs UNKNOWN → any expectancy is optimistic (upper bound). Cannot CANDIDATE / promote.

Rejected:
- Treating INDEX VWAP as FUTIDX 003. Treating this charter as a backtest result.
- Gridding Supertrend 10,3 / 7,3 / 10,1 / 10,2 to chase wr. Silent ST swap vs Dhan charts.
- Merging 002 OTM (ATM+2 CE / ATM-2 PE) or 006 100–200 pts into this grid.
- Delta-band 0.60–0.75 as identity on this tape (rollingoption request has no greeks).
- AND-ing 007∩009, 5m ST/MACD confirm-or-kill, or 008 into the first premium run.
- Inventing brokerage/STT/half-spread then ranking on after-cost exp. Invented wr.
- STRAT-015+. Fixtures-as-pass. RESEARCH_READY_FOR_PROGRAMMING from this file.

UNKNOWN / DATA_INSUFFICIENT:
- Whether HQ rollingoption history is long enough for ≥30 OOS trades per underlying.
- rollingoption native interval vs 3m resample method (same gap as INDEX 3m).
- Bid/ask, reject, gap, RM-lot (Q12). Costs / statutory / option STT (optimistic exp).
- Vendor IV methodology; identity of rollingoption `spot` vs IDX_I last vs FUTIDX.
- SENSEX BSE strike step. F&O 15:40 circular. Lots FROM_CONTRACT.
- INDEX volume as VWAP tape (still UNKNOWN — this path does not re-sign it).

What 06 must do: implement this charter (later); freeze ST(10,3); two-cell strike grid;
next-bar-open; OOS 20% / min 30; FAIL wr<45%; label expectancy OPTIMISTIC; score NORMAL
when tags exist. Keep_current until OOS+NORMAL after costs exists.

What 06 must not do: p-hack ST; add 002/006/delta cells; promote; invent costs then
CANDIDATE; use INDEX points as option_pnl.

What 03 must do: name NSE vs BSE OPTIDX; strike step per underlying; confirm rollingoption
is the historical option object; keep 15:15 as filter ≠ F&O close.

What 04 must do: do not freeze ATM vs ATM-2 as “the” 005; do not merge 002; do not add
STRAT-015. This is not a mix freeze.

What 09 must do: notes, not a pass. Q8 stays FAIL until a real rollingoption OOS book
exists. Q12 stays FAIL (next-bar open still assumes fill). Do not waive on this charter.

What 05 must do: news / extreme PCR remain hold/veto, not alpha, not a catalog delete.
Do not retune ST from a news day.
```

---

## 1. Why this exists (math, not a promote)

09 red-team **Q8** FAILED: default ticket needs option fills; 06 has INDEX/FUTIDX **points** only ([`ENGINE_MIX_REVIEW.md`](../../09_review/docs/ENGINE_MIX_REVIEW.md)). Proxy OOS wr on INDEX 3m 003 is already **FAIL** (~27–28% NIFTY — [`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md)). That is **not** option P/L.

A long vanilla’s P/L is **premium change**, not underlying points × 1. Theta, vega, and discrete strike can make a “correct” lean a premium loss. This charter asks one well-posed question:

> Given the **frozen** INDEX 3m all-three leans, what did **ATM** (and **two-strikes ITM**) option OHLC do, filled at **next bar open**, exited when the lean left or at **15:15**?

Answering it does **not** prove 003, does **not** re-sign INDEX volume as FUTIDX VWAP ([`LIVE_OHLC_2026-09-03.md`](LIVE_OHLC_2026-09-03.md)), and does **not** set `RESEARCH_READY_FOR_PROGRAMMING`.

---

## 2. Layers (do not collapse)

| Layer | What |
|-------|------|
| `SOURCE_FACT` | 003 all-three on **3m futures** (`2RnBT9DDDNI` 20:57–26:07). 005 ITM / max ATM; OTM not recommended this video; no-delta fallback **1–2 strikes ITM from spot** ([`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)). 009 flatten **before 15:15** (23:48–24:06). HQ `POST /charts/rollingoption` `requiredData`: `open,high,low,close,iv,volume,strike,oi,spot` ([`DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) Expired options). |
| `VALIDATION` | **This file.** Lean tape = INDEX 3m all-three **as already computed** (volume `UNKNOWN` vs FUTIDX). P/L tape = rollingoption OHLC. ST **10,3** = WEAK inference, **not** a search grid. Costs `UNKNOWN` ⇒ expectancy **optimistic**. |
| `HYPOTHESIS` | 04 strike pairing 003→005 ([`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md), [`STRAT-005.md`](../../04_quant/docs/candidates/STRAT-005.md)). 1m→3m resample. Next-bar-open fill (04 YAML `fill: next_bar_open_or_conservative_ask`). |

Books (Murphy / Natenberg in `config/workspace.yaml`) tag risk language only. They do **not** license a non-Dhan Supertrend or a new STRAT.

---

## 3. Objects (03 owns the names; 02 will not swap them)

| Object | Role | Forbidden |
|--------|------|-----------|
| **INDEX** `IDX_I` 3m (1m resampled) | **Lean only** — VWAP + VWMA(20) + ST all-three ([`STRAT_001_014_VALIDATION.md`](STRAT_001_014_VALIDATION.md) STRAT-003). | Cash-index **volume** as a claimed FUTIDX VWAP. Publishing lean counts as wr. |
| **rollingoption OPTIDX** OHLC | **P/L + fill**. Same IST 3m buckets as the lean. Strike from `spot` (spoken) at signal bar. | Using INDEX/FUTIDX points as `option_pnl`. Inventing bid/ask. |
| **FUTIDX** | Spoken 003 tape. Not required for **this** alignment (INDEX leans are the given). Continuous FUTIDX still `DATA_INSUFFICIENT`. | Pretending this charter is the Gokul futures book. |
| **Live `POST /optionchain`** | Desk 3m poll ([`CHAIN_METRICS.md`](../../03_phd_market/docs/CHAIN_METRICS.md)). Not historical fills. | Substituting today’s chain for expired OHLC. |

**Lean definition (frozen — copy 003, do not retune):**

- **CE** iff close > session VWAP **and** VWMA_20 **and** Supertrend.  
- **PE** iff close < all three.  
- **SKIP** iff Supertrend side ≠ VWAP side (no new entry; if in a trade, this **is** lean-leave).

009 **open skip** 09:15–09:45 IST applies to **entries** (same as the proxy book). Flatten **15:15** applies to **exits**. Do **not** merge Himanshu 007 into this first run ([`STRAT_001_014_MARKET.md`](../../03_phd_market/docs/STRAT_001_014_MARKET.md): 007 ≠ 009). Do **not** attach 5m ST/MACD confirm-or-kill ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md) is a **different** hypothesis). Do **not** attach 008 mixed-index veto on the first premium book — that changes n; it is a later MIX row, not a silent AND.

**15:15 vs 15:40:** spoken flatten is a **filter**, not F&O close (`VERIFY` 15:40). CAS 15:15–15:35 is cash **Closing Auction Session**, not this exit ([`cas/CAS_STRATEGIES.md`](../../03_phd_market/cas/CAS_STRATEGIES.md)). Parameter `close_model` stays 03’s. This charter uses **spoken 15:15** only.

---

## 4. Alignment (no look-ahead)

HQ charts enum is `{1, 5, 15, 25, 60}`. Spoken **3m** is still a VALIDATION gap. **Rule:** resample INDEX 1m → 3m and rollingoption 1m → 3m with the **same** OHLC construction 06 already used for the proxy. Do not mix 3m INDEX leans with native **5m** option bars.

| Clock | Rule |
|-------|------|
| Signal | INDEX 3m bar **i** is **closed**. Lean ∈ {CE, PE}. 009 skip not active. Not already in a position (one ticket at a time). |
| Strike lock | From rollingoption `spot` on bar **i** (fallback: INDEX close on bar i). 03: spoken strike-from-**spot**, not futures. |
| Entry fill | rollingoption **open of bar i+1**. If i+1 missing → no trade (`DATA_INSUFFICIENT` for that signal). |
| Exit, lean leave | First bar **j ≥ i+1** where lean ∉ {position} (SKIP or opposite). Fill = rollingoption **open of bar j+1**. If no next bar → flatten path. |
| Exit, 15:15 | No new hold through 15:15 IST. Flatten at the first option **open** with timestamp ≥ 15:15, or the last open strictly before 15:15 if that is the session’s last printable. Do not use the signal bar’s option **close** as a fill. |
| Overnight | Forbidden (009). |

**P/L unit:** option points = `exit_open − entry_open` for long CE/PE (both are buys). Win iff points > 0. **Not** index points. **Not** rupee P/L until lots `FROM_CONTRACT` (03) — do not hardcode lots.

**Q12 honesty:** next-bar open **assumes the print existed and filled**. No reject, no gap-through, no RM “1 ITM lot exceeds capital.” 09 keeps Q12 FAILED. 02 **ACCEPT** next-bar-open as the **test convention**; **REJECT** calling it a fill model.

---

## 5. Strike grid — ATM vs ATM-2 / ATM+2 only (STRAT-005)

rollingoption `requiredData` lists OHLC / IV / volume / strike / OI / spot — **not** `greeks.delta`. Vendor delta on this history = `DATA_INSUFFICIENT`. 005’s spoken band 0.60–0.75 stays **WEAK** / not this tape ([`STRAT_001_014_VALIDATION.md`](STRAT_001_014_VALIDATION.md) STRAT-005; 03: if history lacks greeks, map 1–2 ITM from spot).

ATM ([`CHAIN_METRICS.md`](../../03_phd_market/docs/CHAIN_METRICS.md)): listed strike **closest** to `spot` at signal time. Ties: 03 names the rule (lower strike vs nearer in absolute points) **before** the run — do not peek at premium wr.

**Two cells only** (do not pick a winner on in-sample):

| Cell | CE lean (buy CE) | PE lean (buy PE) | 005 mapping |
|------|------------------|------------------|---------------|
| **A — ATM** | nearest ATM CE | nearest ATM PE | fallback “nearest ATM” |
| **B — 2-ITM** | **ATM-2** CE (two listed strikes **below** ATM) | **ATM+2** PE (two listed strikes **above** ATM) | no-delta “2 strikes ITM from spot” |

Strike **step** is exchange/listed (NIFTY 50 is `partially_supported`; BANKNIFTY / SENSEX **UNKNOWN** until 03 extracts). ATM-2 means **two strikes on that grid**, not “100 index points.”

**Forbidden on this charter (not “later in the same grid”):**

| Temptation | Why no |
|------------|--------|
| ATM+2 **CE** / ATM-2 **PE** (OTM) | STRAT-**002**. Spoken conflict. Keep as extra MIX row, not this book. |
| ATM-1 / ATM+1 (1 ITM) | User grid is ATM vs **2** ITM only. 1 ITM is a later cell if 04 asks — not silent. |
| Delta 0.60–0.75 / 0.63–0.74 / avoid >0.74 | No greeks on rollingoption request enum. |
| 50-multiples on/off | 005 `TEST_ON_OFF`. Extra dimension = p-hack. |
| 006 100–200 pt ITM | Different video, different moneyness; SENSEX folklore. |
| Same ticket 002+005 | Already REJECT merge. |

KEEP_ALL: 002 stays in the catalog. This file does **not** delete it.

---

## 6. Do not p-hack Supertrend 10,3

003 Supertrend digits **“103”** are bind **WEAK** — not spoken “ten comma three” ([`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)). TV-style ATR(10)×3 is **inference** / common default ([`VALIDATION_MATH.md`](VALIDATION_MATH.md)), **not** an HQ token (`SUPERTREND_10_3` unsupported — [`DHAN_INDICATOR_API_MAP.md`](DHAN_INDICATOR_API_MAP.md)). `_byuht` **7,3** is equity — **not imported**.

**Freeze for this path:** the **same** ST(10,3) series already used to print INDEX 3m leans. Recompute leans **only** if 06 must rebuild bars; then use the identical ATR seed / HL2-vs-close as the proxy run. Chart mismatch vs Dhan → `partially_supported`, **no silent library swap**.

**Forbidden after seeing option wr (RETUNE_GATE):**

- Grid ATR period / multiplier `{7,10,11,14} × {1,2,3,4}`.  
- Swap 7,3 because 10,3 “failed premium.”  
- Drop VWMA or VWAP to lift wr.  
- Add 5m MACD confirm-or-kill, 007 afternoon cut, or 008 veto **because** ATM wr < 45%. Those are **other MIX rows**, after a **new** OOS+`NORMAL` charter — not a retune of this book.  
- Nightly `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` — default **keep current** ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)).

Failing premium wr on frozen 10,3 is a **result**, not a license to search.

---

## 7. Score rules (06 executes; 02 names the math gate)

Match the proxy book’s **split**, tighten the **premium** fail line as asked.

| Rule | Value |
|------|--------|
| OOS | Last **20%** of trades (trade-sequence split, not a random shuffle). |
| Minimum | **≥ 30** IS trades **and** **≥ 30** OOS trades **per underlying × strike cell**. Else `DATA_INSUFFICIENT` for that cell. |
| Win | `exit_open > entry_open` on the **option**. |
| **FAIL** | OOS **win_rate < 45%**, **or** n_OOS < 30, **or** optimistic expectancy ≤ 0. |
| Not CANDIDATE | Costs `UNKNOWN` (below). wr ≥ 45% with optimistic exp > 0 is **at most WEAK** / `UNVALIDATED`. |
| Promote | **Forbidden** from this charter. Need OOS + `NORMAL` + **after-cost** robust metrics vs current ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)). |
| SCORE_SAMPLE | `NORMAL` only when session tags exist ([`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md)). Until then `session_kind: UNKNOWN` — say so; do not pretend NEWS_DAY was stripped. |

Do **not** invent wr / PF / DD in docs. 06 writes measured numbers in a dated 06 artifact, labeled **UNVALIDATED**, `validated: false`, `promote: false`.

Proxy INDEX wr already < 45% does **not** skip this run (premium can differ) and does **not** waive FAIL if premium wr is also < 45%.

---

## 8. Costs UNKNOWN ⇒ expectancy optimistic

04 YAML names `brokerage, statutory, half_spread` ([`ALGO_HANDOFF.md`](../../04_quant/docs/ALGO_HANDOFF.md)). This workspace has **no** signed option cost table (brokerage slab, option STT, exchange/GST, typical OPTIDX half-spread by moneyness). Therefore:

- Raw `(exit − entry)` expectancy is an **upper bound**. True after-cost expectancy ≤ optimistic expectancy.  
- Optimistic exp ≤ 0 ⇒ **FAIL** even before costs (true exp worse).  
- Optimistic exp > 0 does **not** pass 04 invalidation “expectancy ≤ 0 after costs.”  
- Do not invent a half-spread in rupees to “fix” Q10. Leave costs `UNKNOWN`.  
- wr is computed on raw premium points (sign of trade). Costs can turn a small win into a loss — so wr itself is **optimistic** vs a costed book. The **FAIL if wr < 45%** line still applies to this optimistic wr. A pass of that line is **not** a costed pass.

Natenberg: long premium pays theta. A 45% wr with small wins and large losers can still have negative expectancy. wr is a **gate**, not a theorem of edge ([`VALIDATION_MATH.md`](VALIDATION_MATH.md): delta ≠ win rate; spoken 20–30% targets are parameters, not proofs).

---

## 9. What this does **not** do

- Does not waive Q8, Q12, Q4, Q19, Q20.  
- Does not make INDEX volume a FUTIDX VWAP.  
- Does not freeze 3m as an HQ `interval`.  
- Does not code `packages/backtest` (07/06 later). `packages/dhan-client` rollingoption helper stays unwired until a later ticket.  
- Does not restart npm, place orders, or write `/alerts/orders`.  
- Does not score CAS-* or EQ-* / SO-*.  
- Does not treat Docs Auditor PASS as a product gate.

---

## 10. Coalition cites

| Team | File | Use |
|------|------|-----|
| 01 | [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) | 003 all-three; 005 ITM/ATM; 009 15:15; ST “103” WEAK |
| 01 | [`DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) | `POST /charts/rollingoption` request enum |
| 01 | [`OPTIONS_INDEX_PACKET.md`](../../01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md) | Layer C pointer only |
| 02 | [`STRAT_001_014_VALIDATION.md`](STRAT_001_014_VALIDATION.md) · [`LIVE_OHLC_2026-09-03.md`](LIVE_OHLC_2026-09-03.md) · [`VALIDATION_MATH.md`](VALIDATION_MATH.md) | INDEX VWAP UNKNOWN; 005 grid; ST inference |
| 03 | [`STRAT_001_014_MARKET.md`](../../03_phd_market/docs/STRAT_001_014_MARKET.md) · [`CHAIN_METRICS.md`](../../03_phd_market/docs/CHAIN_METRICS.md) | OPTIDX; ATM def; 15:15 ≠ 15:40; HQ option history was DATA_INSUFFICIENT — this charter **names** rollingoption as the object to try, not a proof it is long enough |
| 04 | [`STRAT-005.md`](../../04_quant/docs/candidates/STRAT-005.md) · [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) · [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md) | 005 overlay; do not collapse confirm-or-kill into entry |
| 05 | [`CUSTOMER_TALK.md`](../../05_analysis/docs/CUSTOMER_TALK.md) · [`DESK_INTELLIGENCE.md`](../../05_analysis/docs/DESK_INTELLIGENCE.md) | News hold; 3m chain is desk, not 003 math |
| 06 | [`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md) · [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) · [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md) | Proxy FAIL; OOS 20% / min 30; NORMAL score |
| 09 | [`ENGINE_MIX_REVIEW.md`](../../09_review/docs/ENGINE_MIX_REVIEW.md) · [`BACKTEST_REVIEW_2026-09-03.md`](../../09_review/docs/BACKTEST_REVIEW_2026-09-03.md) | Q8/Q12; NOTES_ONLY |
| 00 | [`BOSS_AGENT.md`](../../00_orchestrator/docs/BOSS_AGENT.md) | Mandate ≠ claimed wr. Kill MIX only after 06 OOS+NORMAL |

**Still not `RESEARCH_READY_FOR_PROGRAMMING`.**
