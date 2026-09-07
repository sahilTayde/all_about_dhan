# CUSTOMER_TALK.md — review the signal, then talk

**Team:** 05_analysis (desk-intel)  
**Status:** `DRAFT` / `HYPOTHESIS` / `UNVALIDATED` / `WAITING_FOR_EDIT`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Date:** 2026-09-03  
**Surface:** customer `/` only. Indicator soup and STRAT IDs stay on internal `/desk`.

Education ≠ advice. **No live orders.** The product is **not** only algo / indicator / quant. An agent **reviews the ticket** against trend, option chain, and latest big news, then **suggests and talks**. **BIG_NEWS** is a **hold**; routine/fixture news is pre-market sentiment — not a new STRAT, not secret alpha.

**Suggested ticket UI:** [`CUSTOMER_TICKET.md`](CUSTOMER_TICKET.md) — CE/PE + stop/target + right-rail **agreement** confidence (capped; not a win rate). Customer Yes/No.

---

## Cited packets (coalition)

| Team | File | On disk? |
|------|------|----------|
| 05 overlay | [`SIGNAL_FUSION.md`](SIGNAL_FUSION.md) | yes |
| 05 how-to | [`DESK_INTELLIGENCE.md`](DESK_INTELLIGENCE.md) | yes |
| 00 persona | [`PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md) | yes |
| 06 gate | [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) | yes |
| 04 mix (exists) | [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) | yes — 14 IDs + default |
| **04 MIX_CATALOG** | [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) | **yes** — KEEP_ALL + MIX-* |
| **03 CAS_STRATEGIES** | [`CAS_STRATEGIES.md`](../../03_phd_market/cas/CAS_STRATEGIES.md) | **yes** — CAS-001–005 UNVALIDATED |
| **06 EVENT_MEMORY** | [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md) | **yes** — analog payloads **empty** today |
| **00 boss** | [`BOSS_AGENT.md`](../../00_orchestrator/docs/BOSS_AGENT.md) | yes — mandate ≠ claimed P/L |

Schema (reference only): `packages/desk-intel` `NewsEvent` (`headline`, `cited_url` / `source_url`, `tags`), `MarketSignal.vetoes[]`, `MarketSignal.stage`, `SessionKind`, `SentimentWindow.mock`.

---

## 1. Honesty

| Slot | Today |
|------|--------|
| Layer | **`HYPOTHESIS`**. Teacher STRATs stay **`UNVALIDATED`**. This talk loop does not validate them. |
| Sentiment 10m / 15m / 30m / 1h | **MOCK.** Copy of current lean. Not a measured window. Not edge. Do not speak them as “the last 15 minutes of sentiment.” |
| Option chain | Empty `DHAN_*` → **fixtures**. Say so if the chain is dry-run. Live `POST /optionchain` is TODO. |
| News | RSS / official XML from `config/workspace.yaml` `sources.news[]`. Parser **skips HTML**. Cite `headline` + `cited_url` (fallback `source_url`). Do not scrape Moneycontrol HTML. `surprise_vs_consensus` = **UNKNOWN**. |
| Analog memory | **Empty.** Schema in 06 [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md). Copy below is mandatory until a real analog row exists. **Do not invent a past P/L.** |
| CAS daily book | **`UNVALIDATED`**. Close-bias only. Not a CE/PE ticket. |
| Customer P/L on `/` | **MOCK**. Not a track record. |

Do **not** invent PCR numeric thresholds. Do **not** invent win rates. Do **not** call live Dhan from this spec. Do **not** start npm.

---

## 2. Talk loop (customer `/` language)

The agent **reviews** three books, then **speaks**. Order is fixed. Skip a book only if it is UNKNOWN — then say UNKNOWN. Do not fill with vibe.

**Forbidden on `/`:** `MACD`, `RSI`, `Supertrend` as product nouns, `STRAT-001`…`014`, `PROJECT_MIX`, yaml keys, `PCR > 1.2`, “win rate,” fill prices on EARLY, “entry now,” presenting confidence % as “sure this trade will win.”

**Allowed confidence language:** “desk agreement,” “playbooks that agree,” “you decide,” “not a fill,” “orders refused.” See [`CUSTOMER_TICKET.md`](CUSTOMER_TICKET.md).

### Step A — What the lean is

Speak the **state word** + direction chip + honesty line ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md) copy, customer-facing):

| Schema `stage` | Customer hears |
|----------------|----------------|
| WATCH | “WATCH — mixing. Not a signal.” |
| EARLY | “EARLY — not confirmed, wait about two minutes. Not a guaranteed fill.” |
| CONFIRMED | “CONFIRMED call-side / put-side lean. Stack agrees. Still not a fill promise.” (05 never promotes this.) |
| IN-PROGRESS | “Ticket is live. Target / stop not hit yet.” |
| EXPIRED | “Window closed. Do not chase.” |
| **VETOED** | **HOLD** — “Holding this ticket. Overlay, not a deleted strategy. Do not take this print.” See §3. |

On `NEWS_DAY` (**BIG_NEWS only**) / `EXPIRY`: **no EARLY, no CONFIRMED.** Stay WATCH or HOLD. Suggest wait until the print is digested **and** one **3m** chain has printed (PERSONA_DESK). That is a **ticket hold**, not a catalog delete. Routine MACRO fixtures do **not** force this.

### Step B — Trend in plain words

Review the **futures / tape stack** (04 mix). Translate without indicator IDs:

| Desk fact (internal) | Customer sentence |
|----------------------|-------------------|
| Futures direction and the session stack **agree** | “Index futures and the session trend are pointing the same way.” |
| They **disagree** (chop / 003-style ST vs VWAP skip, spoken without those names) | “Trend tools do not agree with the session average. We are not forcing a side.” |
| Opening 09:15–09:45 | “First half-hour is discovery. We wait for the open drive to fail or finish.” |
| UNKNOWN / no OHLC | “Trend book is UNKNOWN this pass.” |

Do not say “MACD crossed.” Do not name STRAT IDs. Catalog: [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md). Default engine ticket: [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md).

### Step C — Chain in plain words (positioning, not oracle)

3m last snapshot: OI change, PCR, ATM call–put Δ vs last. **Positioning language:**

- “Calls added open interest with premium participating” / “puts added while the index held” — buildup **with** price.
- “Open interest rose while the premium died — writers may be capping. Not an automatic fade.”
- “Put/call open-interest ratio moved vs the last snapshot. That is positioning, not a law.”

**Never:** “PCR is extreme so buy puts.” No numeric PCR threshold. Extreme PCR without price is **not** a signal ([`CHAIN_METRICS.md`](../../03_phd_market/docs/CHAIN_METRICS.md)). Walls are a **heuristic**, not a magnet proof. If chain is fixture: “Chain is a dry-run snapshot until live tokens.”

### Step D — News (cite RSS; **BIG_NEWS = hold only**)

Gather/score news **mostly in PRE_MARKET** for sentiment and market-impact talk. Mid-session: soft context unless **BIG_NEWS**.

Pull the latest items already in schema (`NewsEvent.headline`, `cited_url` or `source_url`, `time_ist`, `tags`). Speak:

> “Latest cited headline: **{headline}** ({source_id}). Link: {cited_url}. Tagged {BIG_NEWS / MACRO_EVENT / RISK_OFF / …}.”

| Tag | Talk | Not |
|-----|------|-----|
| `BIG_NEWS` / session `NEWS_DAY` (big only) | **Hold the customer ticket.** No EARLY / CONFIRMED. “Shock or hard print is in the window. We wait for one 3-minute chain after it.” | “Secret alpha.” New STRAT. Delete teacher strategies. |
| Fixture / `ROUTINE` / soft `MACRO_EVENT` (Brent chatter, RBI watch without policy print) | **Pre-market sentiment / impact context only.** Do **not** hold the live ticket all day. | Treating dry fixtures as a live MACRO_EVENT veto. |
| RISK_OFF vs call-side spray (or RISK_ON vs put-side spray) | Soft caution; hard hold only with BIG_NEWS or `NO_TRADE`. | Automatic put buy on crude language. |
| `NO_TRADE` / halt language | Hold (treated as BIG_NEWS). | |

YAML sources to cite (do not scrape HTML): Fed press, BLS, EIA, BBC business, RBI (XML when verified), Moneycontrol RSS **if stable**. Disable a yaml row if it 404s. `surprise_vs_consensus` stays UNKNOWN unless a calendar adapter exists.

### Step E — Analog memory (mandatory copy)

Always say this block. Fill the middle **only** if 06 `EVENT_MEMORY.md` has a **dated, sourced** analog row. **Today it does not.**

> “We tagged days like this as NEWS_DAY; we do not use them to claim a win rate; if memory exists, describe path. **Today memory empty.**”

If memory later exists: describe **path** (what was tagged, what was held, what the chain did in words). **Do not** attach a P/L, expectancy, or “last time we made X.” Event days are **not** a retune sample ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)). Analog ≠ promote.

### Step F — CAS (only in the close window)

If clock is **15:15–15:40 IST** (cash CAS 15:15–15:35; F&O tail **VERIFY** to 15:40):

> “Cash stocks in the F&O list are in the **Closing Auction Session** — a close auction, not the ordinary tape. Index futures and options **may still trade** into ~15:40. Our close-bias from that book is **UNVALIDATED**. It does not confirm a call or put ticket.”

Cite 03 [`CAS_STRATEGIES.md`](../../03_phd_market/cas/CAS_STRATEGIES.md) and windows in [`cas/METHODOLOGY.md`](../../03_phd_market/cas/METHODOLOGY.md). Do not treat CAS volume as NIFTY option lean. Outside this window, skip CAS talk.

### Step G — Suggest

One suggestion, matching the hold map:

| Review result | Suggest |
|---------------|---------|
| Mixing, overlay clean, not news/expiry | “Stay on WATCH. Not a signal.” |
| Leading mix agrees, `NORMAL` session | EARLY honesty copy. Still not a fill. |
| 04 stack confirms (internal) | CONFIRMED honesty copy. 05 did not promote. |
| `NEWS_DAY` / `BIG_NEWS` / analog empty | **Hold ticket.** Teacher strategies remain in the backtest catalog. |
| Trend vs chain vs headline conflict | Hold. Name the conflict in plain words. |
| 15:15–15:40 | CAS sentence + no new size from CAS bias. |

Then **stop talking**. Do not stack mock sentiment windows as extra clocks.

---

## 3. Fusion language — ticket hold ≠ catalog delete

SIGNAL_FUSION and `schema.MarketSignal` already use `vetoes[]` and stage `VETOED`. **Do not rename the code field in this write.** Map in **this spec**:

| Code / staging (keep) | Spec name | Means |
|------------------------|-----------|--------|
| `vetoes[]` | conceptually **`holds[]`** | Reasons the **customer ticket** is held. |
| `tags` / nightly `SessionKind` | **`session_tags[]`** | `NEWS_DAY` / `EXPIRY` / `NORMAL`. |
| stage `VETOED` | customer **HOLD** | Do not take **this** print. |

**Hard rule:** a hold on a ticket **must not** delete a teacher strategy from the 04 catalog or the 06 backtest book. `NEWS_DAY` excludes the **day** from the retune **sample**; it does **not** drop STRAT-001–014 from [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) / future [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md). Nightly default remains **keep current strategy** ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)).

| Action | Ticket (`/`) | Catalog (04/06) |
|--------|----------------|-----------------|
| `MACRO_EVENT` / `NEWS_DAY` | HOLD — no EARLY, no CONFIRMED | **Keep** teacher STRATs |
| `EXPIRY` (03/nightly tag) | HOLD / no new size into pin | **Keep**; do not retune expiry from 05 |
| Mixed-index / trend-tools disagree | HOLD this ticket | Filter already in the mix; still not a delete |
| Circuit / halt | HOLD | Keep |
| Nightly recon on an event day | — | `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`; **not** a catalog wipe |

Purple `VETOED` in the color spec may stay for `/desk`. Customer `/` copy is **HOLD**.

---

## 4. Experts review (05 must cite, not invent)

05 **reads** these before talking. If a file is missing, say WAITING / DATA_INSUFFICIENT. Do not hallucinate analog rows, CAS recipes, or mix IDs onto `/`.

1. **04 [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md)** — named mix of existing 14 IDs only. **Not on disk (2026-09-03).** Until it lands, review [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) + [`MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md). Trend talk is a **plain-language translation** of that mix, not a 15th STRAT.
2. **03 [`cas/CAS_STRATEGIES.md`](../../03_phd_market/cas/CAS_STRATEGIES.md)** — close-window strategies. **Not on disk.** Until then [`METHODOLOGY.md`](../../03_phd_market/cas/METHODOLOGY.md) clocks. Daily `BOUNCE|SIDEWAYS|FALL` stays **UNVALIDATED**. 05 may mention CAS in 15:15–15:40; 05 may not confirm from it.
3. **06 [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md)** — analog NEWS_DAY paths. **Not on disk. Today memory empty.** When it exists: describe path only; never invent P/L; never retune from that sample.

05 comments back:

- **TO 04:** MIX_CATALOG when written must stay 14 IDs. Customer `/` never lists those IDs. A 05 HOLD is not a request to drop 003/001/006 from the catalog.
- **TO 03:** CAS_STRATEGIES when written must stay UNVALIDATED close-bias. 05 will not scrape HTML for CAS.
- **TO 06:** EVENT_MEMORY when written is path memory, not a win-rate table. Empty is honest. `NEWS_DAY` days stay out of the retune sample; strategies stay in the catalog.

---

## 5. What this loop must NEVER do

- Turn a headline into an entry STRAT.
- Delete or auto-retune teacher strategies because of news.
- Promote CONFIRMED from news + chain agreement.
- Invent PCR laws, analog P/L, or win rates.
- Scrape HTML. Speak mock sentiment as measured. Call live Dhan. Start npm.

---

## HANDOFF (05)

**Accepted:** Talk loop = trend (plain) + chain (positioning) + cited RSS. `NEWS_DAY` **holds the ticket**. Catalog keeps STRATs. `vetoes[]` / `VETOED` map to `holds[]` / HOLD. Analog copy with **today memory empty**. CAS sentence only in 15:15–15:40, UNVALIDATED.

**Rejected:** News-as-alpha. Catalog delete on event days. PCR-threshold talk. Invented analog P/L. MACD/RSI/STRAT IDs on `/`. HTML scrape.

**UNKNOWN / DATA_INSUFFICIENT:** `MIX_CATALOG.md`, `CAS_STRATEGIES.md`, `EVENT_MEMORY.md` not on disk. Live chain until `DHAN_*`. Moneycontrol RSS VERIFY IF STABLE. F&O 15:30 vs 15:40 VERIFY.

---

## Compliance one-liner

The agent **talks a review**, not a guaranteed call. Holding a ticket on a news day is **not** investment advice and **not** a claim that the teacher book is wrong. See [`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md).
