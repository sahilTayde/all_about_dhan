# MIX PROJECT VALIDATION — two PROJECT_MIX books (charter, not a run)

**Team:** 02_phd_math  
**Layer:** `VALIDATION` (charter). P/L numbers do **not** exist in this file.  
**Status:** `DRAFT` / `UNVALIDATED`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. Notes ≠ five-pass.  
**KEEP_ALL.** No `STRAT-015+`. No code this ticket. No live Dhan. No invented win rates, lots, or fills.

These are the **later MIX rows** that [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) refused to AND into the first premium book (`MIX-GOKUL-003-009`). They stay **`PROJECT_MIX`**: no video taught either club as one recipe. Customer default remains `MIX-DEFAULT-BUY` — this file does **not** replace it.

**P/L object, fill, 009 flatten, 005 ITM strike, OOS split, and cost honesty** copy [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md). Do not re-litigate next-bar-open or ATM-2/ATM+2 here. This charter only **freezes the two clubs** and the **no-p-hack** rule on MACD `(12,26,9)` and Supertrend `10,3`.

**Lean tape is still INDEX 3m all-three.** That is **not** FUTIDX VWAP ([`LIVE_OHLC_2026-09-03.md`](LIVE_OHLC_2026-09-03.md)). This file does **not** re-sign INDEX volume.

**Universe for 06:** **NIFTY** and **SENSEX** OPTIDX `POST /charts/rollingoption` (already ingested). BANKNIFTY is not this charter (KEEP_ALL; later MIX row if 04 names it).

---

```text
HANDOFF
From:     teams/02_phd_math
To:       teams/06_backtesting ; teams/04_quant ; teams/03_phd_market ; teams/09_review ; teams/05_analysis
Date:     2026-09-03
Status:   VALIDATION charter / UNVALIDATED / not a run
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted:
- Two named PROJECT_MIX books, frozen before 06 runs: MIX-MTF-TREND and MIX-CONFIRM-5M.
- MIX-MTF-TREND: 003 AND 001 same-side lean; 005 ITM; 009 flatten; no ST grid.
- MIX-CONFIRM-5M: 003 entry; 5m MACD histogram confirm-or-kill; 005 ITM; 009 flatten.
- Premium path = OPTION_PREMIUM_VALIDATION.md (rollingoption OHLC; next-bar open;
  lean-leave or 15:15; 005 cell B ITM). INDEX 3m leans remain not FUTIDX VWAP.
- Score: OOS last 20%; ≥30 IS and ≥30 OOS per underlying × mix. FAIL if OOS wr<45%
  or optimistic exp≤0. Costs UNKNOWN ⇒ cannot CANDIDATE.
- Freeze MACD (12,26,9) and ST (10,3). Do not p-hack after seeing wr.
- KEEP_ALL. No STRAT-015+. Origin stays PROJECT_MIX.

Rejected:
- Relabeling either MIX DHAN-DERIVED. Collapsing HAUS child-MACD entry with
  MIX-CONFIRM-5M. AND-ing 5m Supertrend into MIX-CONFIRM-5M. AND-ing 007/008/002/006.
- ST ATR/period grid. MACD (12,26,9) search / ×3/×4 / signal≠9 after wr.
- MA 100 vs 300 or MA 9 vs 10 search on MIX-MTF-TREND after wr.
- Treating INDEX volume as FUTIDX VWAP. Invented costs then CANDIDATE. Promote.
- P/L numbers in this file. RESEARCH_READY_FOR_PROGRAMMING from this charter.

UNKNOWN / DATA_INSUFFICIENT:
- INDEX volume as VWAP tape (unchanged). Continuous FUTIDX. Histogram construction
  vs Dhan charts. Bid/ask / Q12. Costs. SENSEX strike step. session_kind NORMAL strip.

What 06 must do: run these two books on NIFTY + SENSEX rollingoption already ingested;
inherit OPTION_PREMIUM fill/exit/ITM; freeze MACD(12,26,9) and ST(10,3); OOS 20% /
min 30; FAIL wr<45% or optimistic exp≤0; label exp OPTIMISTIC; no CANDIDATE.

What 06 must not do: p-hack MACD or ST after wr; soup 5m ST into CONFIRM-5M;
use HAUS buy-the-high as confirm; score BANKNIFTY as this charter; invent costs;
publish INDEX points as option_pnl.

What 04 must do: add MIX-MTF-TREND and MIX-CONFIRM-5M as named PROJECT_MIX rows
(not STRAT-015+). Do not make them customer default. Keep MIX-HAUS-001 separate.

What 03 must do: same OPTIDX / 15:15 ≠ F&O close as OPTION_PREMIUM_VALIDATION.md.
NIFTY + SENSEX only here.

What 09 must do: notes, not a pass. Q8/Q12 not waived. PROJECT_MIX stays labeled.

What 05 must do: news / extreme PCR remain hold/veto, not a MACD or ST retune.
```

---

## 1. Why this exists (math, not a promote)

[`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) asked one well-posed question: frozen INDEX 3m **003** leans → ATM vs **2-ITM** option OHLC. It **REJECTED** AND-ing 001, 5m MACD confirm-or-kill, 007, or 008 into that first book.

04 still clubs those pieces on `MIX-DEFAULT-BUY` ([`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md)). 02 will not sign the default AND as a theorem. 02 **will** freeze **two isolated PROJECT_MIX tests** so 06 does not soup them into 003-009 after seeing premium wr ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)).

| Book | Question |
|------|----------|
| **MIX-MTF-TREND** | When **003** (3m all-three) and **001** (1h parent MACD hist + MA stack) agree on side, what did **005 ITM** option OHLC do? |
| **MIX-CONFIRM-5M** | When **003** prints a side, does a **5m MACD histogram** sign-agree **confirm** the ticket or **kill** it — then what did **005 ITM** option OHLC do? |

Answering them does **not** prove 003 or 001, does **not** make INDEX volume a FUTIDX VWAP, and does **not** set `RESEARCH_READY_FOR_PROGRAMMING`.

---

## 2. Layers (do not collapse)

| Layer | What |
|-------|------|
| `SOURCE_FACT` | 003 all-three on **3m futures** (`2RnBT9DDDNI`). 001 parent **1h** MACD hist + MA 10/30/100 (`HAUSZx-hYdY`). 005 ITM / max ATM. 009 flatten **15:15**. Bind: [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md). Nobody taught 003∧001 or 003+5m-MACD-kill as one recipe → **`PROJECT_MIX`**. |
| `VALIDATION` | **This file** + [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md). Lean tape = INDEX 3m all-three **as already computed** (volume `UNKNOWN` vs FUTIDX). P/L tape = rollingoption OHLC. MACD **(12,26,9)** = Appel **convention**, not a Dhan-spoken freeze. ST **10,3** = WEAK inference, **not** a search grid. |
| `HYPOTHESIS` | 04 naming these MIX IDs ([`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) — add rows; do not invent `STRAT-015+`). Staging confirm-or-kill ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)). 001 index-only universe = already `PROJECT_MIX`. |

Books (Murphy / Natenberg) tag risk language only. They do **not** license a non-Dhan Supertrend or a new STRAT.

---

## 3. Two books (freeze before 06 runs)

Shared YAML honesty (both):

```yaml
book_policy: KEEP_ALL
status: UNVALIDATED
origin: PROJECT_MIX
research_ready_for_programming: false
customer_default: false
markets: [NIFTY, SENSEX]
overlay_strike: STRAT-005          # ITM only — OPTION_PREMIUM cell B
filter: [STRAT-009]
not_attached: [STRAT-002, STRAT-006, STRAT-007, STRAT-008]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

A MIX is a **new test ID**. STRAT-001–014 stay `BACKTEST_BOOK`. Conflicts stay named; nothing is deleted.

### 3.1 MIX-MTF-TREND

```yaml
mix_id: MIX-MTF-TREND
origin: PROJECT_MIX
primary: [STRAT-003, STRAT-001]    # AND same lean — not two tickets
001_role: 1h_parent_same_side      # not HAUS child buy-the-high
macd: {fast: 12, slow: 26, signal: 9}   # labeled Appel convention
ma_stack: {10, 30, 100}            # do not search 300 / MA9 on this book
st_grid: forbidden
```

**Same lean (CE):** 003 lean is **CE** **and** 001 **1h parent** is bullish: MACD histogram **> 0** **and** MA(10) > MA(30) > MA(100).  
**Same lean (PE):** 003 lean is **PE** **and** 001 1h parent is bearish: histogram **< 0** **and** MA(10) < MA(30) < MA(100).  
**Else SKIP** (no new entry). If already in a trade, disagreement **is** lean-leave (same exit path as [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) §4).

**001 object:** MACD/MA on **INDEX close** (HQ `60`). 001 does not need volume. Index-only universe vs spoken NIFTY 100 stocks stays **`PROJECT_MIX`**. Do **not** require HAUS **child 5m** or **buy that candle’s high** — that is `MIX-HAUS-001` / `H-001-HAUS-ENTRY` ([`STRAT_001_014_VALIDATION.md`](STRAT_001_014_VALIDATION.md)).

**1h no look-ahead:** parent bar must be **closed**. Use the last closed 60m bar at or before the 003 3m close.

**Strike:** 005 **ITM only** (CE **ATM-2**, PE **ATM+2**) — not 002 OTM, not ATM cell A, not 006 100–200 pts.

**Clock:** 009 only (skip 09:15–09:45 entries; flatten 15:15). Do **not** AND 007.

### 3.2 MIX-CONFIRM-5M

```yaml
mix_id: MIX-CONFIRM-5M
origin: PROJECT_MIX                 # desk staging — not a transcript theorem
entry: STRAT-003                    # 3m all-three — not 5m MACD entry
confirm: 5m_MACD_HIST_sign          # confirm-or-kill; not HAUS buy-the-high
not_in_this_book: 5m_Supertrend     # ST stays inside 003; do not AND a second ST
macd: {fast: 12, slow: 26, signal: 9}
```

**Entry lean** = frozen 003 (CE / PE / SKIP) on INDEX 3m all-three — same definition as [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) §3.

**Confirm-or-kill (histogram sign, not a fresh-cross hunt):**

| 003 lean | Last **closed** INDEX **5m** MACD hist | Action |
|----------|----------------------------------------|--------|
| CE | `hist > 0` | **Confirm** — take the ticket |
| PE | `hist < 0` | **Confirm** — take the ticket |
| CE or PE | `hist` opposite or `hist == 0` | **Kill** — no trade |
| SKIP | — | No entry (003 already skipped) |

HQ **5m** is a native interval. Do **not** mix an **unclosed** 5m hist with a closed 3m signal. Do **not** require a MACD **cross on this bar** (that is a different hypothesis; adding it after wr is p-hack). Do **not** AND **5m Supertrend** as a second confirm (SIGNAL_STAGING’s ST+MACD pair is **another** MIX if 04 names it). Do **not** use 5m MACD as **entry**.

**Strike / clock:** same as §3.1 (005 ITM; 009 only).

---

## 4. Objects (inherit; do not swap)

| Object | Role | Forbidden |
|--------|------|-----------|
| **INDEX** `IDX_I` 3m (1m resampled) | **003 lean** — VWAP + VWMA(20) + ST all-three | Calling INDEX volume **FUTIDX VWAP**. It is still `UNKNOWN`. |
| **INDEX** `IDX_I` **60** / **5** | **001 parent** (MIX-MTF-TREND) / **MACD hist** (MIX-CONFIRM-5M) | Cash-index VWAP claims (001 does not VWAP; 003 still must not). |
| **rollingoption OPTIDX** OHLC | **P/L + fill** — NIFTY + SENSEX, already ingested | INDEX/FUTIDX points as `option_pnl`. BANKNIFTY as this charter. |
| **FUTIDX** | Spoken 003 tape. **Not** this lean. Continuous history still `DATA_INSUFFICIENT`. | Pretending this charter re-signs Gokul futures VWAP. |

Fill, exit, overnight ban, P/L unit, Q12 honesty: **copy** [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) §4. Entry fill = next 3m option **open**. Exit = lean-leave at next option open, or flatten **15:15**. 15:15 is a **filter**, not F&O close (`VERIFY` 15:40). CAS 15:15–15:35 is cash Closing Auction Session, not this exit.

**003 lean (frozen — do not retune):**

- **CE** iff close > session VWAP **and** VWMA_20 **and** Supertrend.  
- **PE** iff close < all three.  
- **SKIP** iff Supertrend side ≠ VWAP side.

ST series = the **same** ST(10,3) already used to print INDEX 3m leans. Recompute only if 06 rebuilds bars; then identical ATR seed / HL2-vs-close.

---

## 5. Do not p-hack MACD (12,26,9) or ST 10,3

**MACD (12,26,9):** Appel default / annexure-adjacent `MACD_12` / `MACD_26` names. Signal **9** was **not clearly spoken** on HAUS ([`STRAT_001_014_VALIDATION.md`](STRAT_001_014_VALIDATION.md)). Histogram = MACD − signal (labeled construction; chart mismatch → `partially_supported`, **no silent library swap**).

**ST (10,3):** 003 digits **“103”** are bind **WEAK**. TV-style ATR(10)×3 is inference ([`VALIDATION_MATH.md`](VALIDATION_MATH.md)). `_byuht` **7,3** is equity — **not imported**.

**Freeze for both books.** After seeing OOS wr, **forbidden** ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)):

- Grid MACD `{12/26/9, 36/78/27, 48/104/36}` or ×3/×4 because wr < 45%.  
- Change signal length, EMA vs SMA of signal, or hist vs MACD-line sign.  
- Grid ST ATR/period `{7,10,11,14} × {1,2,3,4}` or swap 7,3.  
- Drop VWMA/VWAP from 003, or drop the 001 MA stack, to lift wr.  
- Add 007 / 008 / 5m ST confirm / HAUS buy-the-high **because** wr failed. Those are **other MIX rows**.  
- Search MA 100 vs 300 or MA 9 vs 10 on **MIX-MTF-TREND**.  
- Nightly `RETUNE_PROPOSAL` auto-apply — default **keep current**.

Failing wr on frozen params is a **result**, not a license to search. HAUS ×3/×4 and MA 300 stay on **`MIX-HAUS-001`**, not these books.

---

## 6. Score rules (06 executes; 02 names the math gate)

Same split as [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) §7.

| Rule | Value |
|------|--------|
| Universe | **NIFTY**, **SENSEX** (rollingoption already ingested) |
| OOS | Last **20%** of trades (trade-sequence split, not a shuffle) |
| Minimum | **≥ 30** IS **and** **≥ 30** OOS **per underlying × mix**. Else `DATA_INSUFFICIENT` for that cell. |
| Win | `exit_open > entry_open` on the **option** (005 ITM) |
| **FAIL** | OOS **win_rate < 45%**, **or** n_OOS < 30, **or** optimistic expectancy ≤ 0 |
| Not CANDIDATE | Costs `UNKNOWN`. wr ≥ 45% with optimistic exp > 0 is **at most WEAK** / `UNVALIDATED` |
| Promote | **Forbidden** from this charter. Need OOS + `NORMAL` + **after-cost** vs current |
| SCORE_SAMPLE | `NORMAL` only when session tags exist ([`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md)). Until then `session_kind: UNKNOWN` |

Do **not** invent wr / PF / DD in this file. 06 writes measured numbers in a **dated 06** artifact, labeled **UNVALIDATED**, `validated: false`, `promote: false`.

Do **not** pick MIX-MTF-TREND vs MIX-CONFIRM-5M vs `MIX-GOKUL-003-009` on in-sample wr.

---

## 7. Costs UNKNOWN ⇒ cannot CANDIDATE

Copy [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) §8.

- Raw `(exit − entry)` expectancy is an **upper bound**.  
- Optimistic exp ≤ 0 ⇒ **FAIL** (true exp worse).  
- Optimistic exp > 0 does **not** pass after-cost invalidation.  
- Do not invent brokerage / STT / half-spread to rank books. Leave costs `UNKNOWN`.  
- Therefore **cannot CANDIDATE** / promote from this charter, even if wr ≥ 45%.

---

## 8. What this does **not** do

- Does not waive Q8, Q12, Q4, Q19. Does not re-sign INDEX volume as FUTIDX VWAP.  
- Does not freeze 3m as an HQ `interval`. Does not freeze 12/26/9 as “Dhan said.”  
- Does not code `packages/backtest` or live orders. Does not restart npm.  
- Does not score CAS-* / EQ-* / SO-* / BANKNIFTY. Does not delete STRAT-001–014.  
- Does not treat Docs Auditor PASS as a product gate.

---

## 9. Coalition cites

| Team | File | Use |
|------|------|-----|
| **02** | [`OPTION_PREMIUM_VALIDATION.md`](OPTION_PREMIUM_VALIDATION.md) | P/L object, fill, 005 ITM cell B, 009, OOS/FAIL, costs optimistic, no ST grid on 003 |
| 02 | [`STRAT_001_014_VALIDATION.md`](STRAT_001_014_VALIDATION.md) · [`LIVE_OHLC_2026-09-03.md`](LIVE_OHLC_2026-09-03.md) | 001≠staging; INDEX VWAP UNKNOWN; MACD 12/26/9 convention |
| 01 | [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) | 003 / 001 / 005 / 009; PROJECT_MIX tags |
| 03 | [`STRAT_001_014_MARKET.md`](../../03_phd_market/docs/STRAT_001_014_MARKET.md) · [`ROLLING_OPTION.md`](../../03_phd_market/docs/ROLLING_OPTION.md) | OPTIDX; 15:15 ≠ 15:40; NIFTY/SENSEX rollingoption |
| 04 | [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) · [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) · [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md) | Named MIX rows; confirm-or-kill ≠ entry; KEEP_ALL |
| 05 | [`CUSTOMER_TALK.md`](../../05_analysis/docs/CUSTOMER_TALK.md) | News hold, not alpha |
| 06 | [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) · [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md) | No p-hack; NORMAL score |
| 09 | [`ENGINE_MIX_REVIEW.md`](../../09_review/docs/ENGINE_MIX_REVIEW.md) | Notes ≠ pass |
| 00 | [`BOSS_AGENT.md`](../../00_orchestrator/docs/BOSS_AGENT.md) | Mandate ≠ claimed wr. Kill MIX only after 06 OOS+NORMAL |

**Still not `RESEARCH_READY_FOR_PROGRAMMING`.**
