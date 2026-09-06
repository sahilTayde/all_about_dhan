# SIGNAL_FUSION.md — news + 3m chain + sentiment overlay on the 14 STRAT mix

**Team:** 05_analysis (desk-intel)  
**Status:** `DRAFT` / `HYPOTHESIS` / `UNVALIDATED` / `WAITING_FOR_EDIT`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. Overlay only. **Not a new STRAT.**  
**Date:** 2026-09-03  

Education ≠ advice. **No live orders.** Do **not** invent win rates. Do **not** invent PCR numeric thresholds as “the Dhan law.” Do **not** treat headlines as alpha.

This spec says **how 05 holds or biases the customer ticket** on the existing mix ([`MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md), KEEP_ALL [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md)). A hold (`vetoes[]` / stage `VETOED`) is **not** a catalog delete. Talk: [`CUSTOMER_TALK.md`](CUSTOMER_TALK.md). It does **not** add `STRAT-015+`. It does **not** replace 04 primaries.

---

## Cited packets (coalition)

| Team | File | What 05 takes |
|------|------|----------------|
| 05 how-to | [`DESK_INTELLIGENCE.md`](DESK_INTELLIGENCE.md) | RSS cite-don’t-scrape; 3m full chain; mock sentiment; dry-run CLI |
| 03 VALIDATION | [`CHAIN_METRICS.md`](../../03_phd_market/docs/CHAIN_METRICS.md) | PCR(OI), ATM, buildup vs last snapshot, walls, max-pain **stub**. Extreme PCR without price is **not** a signal. |
| 03 CAS | [`cas/README.md`](../../03_phd_market/cas/README.md) | Daily `BOUNCE\|SIDEWAYS\|FALL` is **`UNVALIDATED`**. Closing Auction Session ≠ PCA. |
| 04 staging | [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md) | WATCH / EARLY / CONFIRMED / IN-PROGRESS / EXPIRED / VETOED. 5m ST/MACD **promote or kill**. |
| 04 book | [`MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md) | 14 IDs only. 003 ST vs VWAP disagree = sideways skip. 008 mixed-index avoid. |
| 00 persona | [`PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md) | Event window, tape-vs-headline, opening drive, expiry afternoon. Overlay **vetoes**; it does not license lag-only entries. |
| 01 OI | [`OPTIONS_INDEX_PACKET.md`](../../01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md) § B `_exmJYgFwFA` EXM-C09 | Highest OI + **rising** OI ≈ writers’ “won’t breach” **heuristic**. Selling class. Phase-1 remains CE/PE **buy first**. |
| 06 gate | [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) | `NEWS_DAY` / `EXPIRY` / `NORMAL`. Nightly does **not** auto-retune. |
| Schema only | `packages/desk-intel` `schema.py` | `NewsEvent`, `ChainBias`, `SentimentWindow` (`mock=True`), `MarketSignal.stage`, `SessionKind` |

Poll cadence: `config/workspace.yaml` `desk_intel.poll.chain_interval: **3m**`. **Must stay 3m.** Do not retune this file into 1m full-chain.

---

## 1. Honesty (what is true on disk today)

| Slot | Today | Later (TODO) |
|------|-------|----------------|
| Sentiment windows `10m` / `15m` / `30m` / `1h` | **MOCK.** Schema `SentimentWindow.mock = True`. They copy the current news+chain lean. **Not** measured rolling windows. **Not** edge. | Rolling windows only after a measured series exists. Until then, dashboard bind is decorative. |
| Option chain | Empty `DHAN_CLIENT_ID` / `DHAN_ACCESS_TOKEN` → **fixtures** / `--offline`. `MarketSignal.dry_run` stays true. | Live `POST /optionchain` **TODO** until tokens **and** a user ask. This spec does **not** call Dhan. |
| News RSS | Public feeds (no Dhan token). HTML skipped. Moneycontrol historical RSS = **VERIFY IF STABLE**. `surprise_vs_consensus` = **UNKNOWN**. | Real calendar adapter (`CalendarPlaceholder`). |
| CAS daily book | 03 publishes `BOUNCE\|SIDEWAYS\|FALL` with **`UNVALIDATED`**. Nightly `cas_calls[]` is a recon row, not a lean. | Still cannot promote CONFIRMED from CAS. |
| 14 STRATs | All `UNVALIDATED`. Fusion is a **risk overlay**, not a coded engine mix. | 04 freeze → 06 backtest. 05 still only vetoes / biases. |

Layer: **`HYPOTHESIS`**. Do not collapse into SOURCE_FACT. PCR/OI **definitions** stay 03 VALIDATION; **use** of those numbers as veto/bias stays 05 HYPOTHESIS.

---

## 2. Fusion inputs (not a 15th STRAT)

05 fuses **three books** into `MARKET_SIGNAL` bias (`schema.MarketSignal`: `lean`, `vetoes[]`, `reasons[]`, `stage`, `sentiment_windows`). Directional lean without 04 lagging confirm is **EARLY at most** — usually **WATCH** while mixing.

### A. News RSS / official + calendar → `NEWS_DAY`

- Sources: `config/workspace.yaml` `sources.news[]` (Fed, BLS, EIA, BBC, RBI, Moneycontrol RSS *if stable*). Parser **skips HTML**.
- Keyword maps: yaml `desk_intel.keywords` (`MACRO_EVENT`, RISK_ON/OFF, NO_TRADE).
- Session tag: nightly `SessionKind` = `NEWS_DAY` when a **print/calendar** row hits — not merely “any item from a MACRO_EVENT-stamped feed” ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)).
- **Role:** `NEWS_DAY` = **no-trade / VETO overlay**, not an entry. Shock can *start* a WATCH mix; it **cannot** be the reason a customer sees BUY_CE / BUY_PE as a ticket.
- Crude 90→95-style language → RISK_OFF **hypothesis** for energy/INR; **veto automatic PE** (PERSONA_DESK). Not alpha.

### B. Chain last snapshot (3m) — OI, PCR, ATM CE–PE Δ

Default poll: full `POST /optionchain` per enabled underlying, **3m**, remember `last.json` (`remember_last_snapshot: true`). First poll of a name has no 3m memory — falls back to Dhan `previous_oi` (day).

| Field (`ChainBias`) | VALIDATION (03) | 05 use |
|---------------------|-----------------|--------|
| PCR(OI), PCR Δ vs last | Σ PE OI / Σ CE OI; undefined if CE OI = 0 | Mixing **reason** at WATCH. **Never** an entry from extreme PCR alone. **No numeric law** in this file. |
| ATM CE–PE Δ / wing buildup vs last | `oi - last snapshot oi` | Leading ingredient (with price). Writers capping (OI up, premium dying) is a **veto**, not a fade-entry. |
| CE/PE wall | Max CE OI / max PE OI on this expiry sheet | `_exm` EXM-C09 **heuristic** (call OI ≈ resistance, put OI ≈ support). Origin `DHAN-DERIVED` selling class. Phase-1 **buy first** — do not convert walls into a naked-sell STRAT. |
| Max-pain / gamma-load | Stubs | Reasons only. Not dealer books. |

1m path (yaml, **off**): ATM±`atm_wing` quote on cached ids — **not** full chain. Quote `oi` field = **VERIFY FROM DOCS**.

### C. CAS daily book — `UNVALIDATED`

03 CAS analyst daily `BOUNCE | SIDEWAYS | FALL` may appear as a **reason** on WATCH (“CAS book says SIDEWAYS — UNVALIDATED”). It **must not**:

- Promote EARLY or CONFIRMED.
- Override a `NEWS_DAY` / `EXPIRY` veto.
- Be treated as validated index direction.

CAS = **Closing Auction Session** (F&O cash names 15:15–15:35). Index options tape is still F&O (**VERIFY** 15:40). Do not fuse cash-CAS volume into NIFTY option lean.

---

## 3. Attach to staging (04 machine; 05 overlay)

04 owns the state machine. 05 **attaches** vetoes and mixing reasons. Named mix of **existing** IDs only (001–014) + origin tags. Conflicts stay conflicts (e.g. 002 vs 005 strike) — 05 does not pick a winner.

```text
idle
  └─ 05 chain Δ and/or news print visible ──► WATCH   (mixing; not a signal)
        │
        ├─ NEWS_DAY or EXPIRY still hot ──► stay WATCH or VETOED (no EARLY)
        ├─ ≥2 leading ingredients agree, overlay clean ──► EARLY (04 target)
        │     │
        │     ├─ 04 5m ST/MACD agree + PERSONA checklist ──► CONFIRMED
        │     │     (05 may only VETO from here — never promote)
        │     └─ overlay fires ──► VETOED
        └─ overlay fires before EARLY ──► VETOED
```

### WATCH — chain + news mixing

**05 may:** stamp WATCH when any leading ingredient is present — first impulsive bar (04), range break (04), **OI/PCR/ATM Δ vs last 3m snapshot**, or a news/calendar print.

**Customer copy:** “WATCH — mixing. Not a signal.”

**05 must not:** pick CE vs PE from PCR level, from a headline verb, or from mock 10m/15m/30m/1h slots.

Sentiment windows on WATCH: still mock copies of the current lean. Display as schema, not as a second clock.

### EARLY — still no-trade if `NEWS_DAY` / `EXPIRY`

04’s lead threshold (two independent leading ingredients, opening-drive not failing) is **blocked** while the session tag is `NEWS_DAY` or `EXPIRY`.

| Tag | Who stamps it | 05 rule | Retune |
|-----|---------------|---------|--------|
| **NEWS_DAY** | Nightly from RSS/calendar **print** (not feed stamp) | No EARLY. Stay WATCH or go **VETOED**. PERSONA: wait until the print **plus one 3m chain**. | **Not** a retune sample |
| **EXPIRY** | **03 / nightly** — nearest-expiry sheet date **equals** session date. 05 **consumes** the tag. **Do not retune** expiry weekday, lot, or pin math in this file. | No EARLY. Size to **NO_TRADE** / VETOED into expiry afternoon (gamma/pin). | **Not** a retune sample |

Expiry weekday / “Tuesday NIFTY” folklore stays `FROM_CONTRACT` (03). 05 does not invent a new expiry clock.

If the overlay is clean **and** the tag is `NORMAL`, 05 may allow 04 to promote WATCH → EARLY. 05 still does **not** confirm.

### CONFIRMED — require 04 primary; 05 may only VETO

Promotion EARLY → CONFIRMED is **04 only**: 5m Supertrend flip **and/or** 5m MACD cross **in the same direction**, after the EARLY stamp; RSI/EMA9 are filters; PERSONA CE/PE checklist still applies.

**05 must not promote to CONFIRMED.** Not from chain agreement, not from news+chain agreement, not from CAS, not from mock sentiment.

After CONFIRMED, 05 **may only VETO** (late shock, mixed-index, 003 ST vs VWAP disagree, circuit/halt). Late news after confirm: event wins until **one 3m chain** (PERSONA_DESK / SIGNAL_STAGING).

04 primary IDs 05 is overlaying (not replacing): **001, 003, 006** as trend/scalp primaries; **007–009** as filters already in the book; **008** as mixed-index filter. 013–014 remain **WAITING sell** — Phase-1 buy-first; 05 does not “help” them with OI-wall sell language from `_exm`.

### VETOED — 05 overlay kills

| Trigger | State | Notes |
|---------|-------|--------|
| News shock (`MACRO_EVENT` undigested; RISK_OFF vs CE spray or RISK_ON vs PE spray) | **VETOED** | Can also *start* WATCH. Shock ≠ entry. Crude overlay ≠ auto PE. |
| Mixed-index **STRAT-008** (NIFTY vs BANKNIFTY vs SENSEX leans disagree) | **VETOED** (or no new risk) | Origin `DHAN-DERIVED` (2RnBT9). Desk default: reduce / no trade. Do not “pick one and size up.” |
| Supertrend vs VWAP **disagree** and **STRAT-003 is the 04 primary** | **VETOED** | 003 `no_new_entry_if: Supertrend_direction != VWAP_side`. Sideways skip in the 14-ID mix. 05 does not invent a new chop STRAT. |
| Opening drive 09:15–09:45 IST (PERSONA / STRAT-009) | **VETOED** / wait | Filter already in the book. 05 does not fade the first spike. |
| Circuit / halt / `NO_TRADE` keywords | **VETOED** | `news_bias == NO_TRADE`. |
| `NEWS_DAY` or `EXPIRY` while a lean is forming | **VETOED** or stay **WATCH** | Never EARLY. Never CONFIRMED from 05. |
| Fake-breakdown reclaim (spot through PE wall, PE covering not confirmed) | **VETOED** | PERSONA checklist. Stub in fusion. |
| Late shock **after** CONFIRMED | **VETOED** | Event wins until one 3m chain. |

WATCH → VETOED is allowed (overlay before EARLY). CONFIRMED → VETOED is allowed (late overlay). 05 does not stamp ACHIEVED / STOPPED — those are 04 outcomes.

**Ticket hold ≠ catalog delete** (customer talk: [`CUSTOMER_TALK.md`](CUSTOMER_TALK.md)): schema keeps `vetoes[]` and stage `VETOED`. Spec maps them to **`holds[]` / `session_tags[]`**. Customer `/` copy is **HOLD** (no EARLY/CONFIRMED on `NEWS_DAY`). That **must not** delete teacher STRATs from the 04/06 catalog. Event days stay out of the retune **sample** only.

---

## 4. What 05 must NEVER do

1. **Entry from PCR extreme alone.** CHAIN_METRICS HYPOTHESIS: extreme PCR as contrarian **without price** is not a signal. No “PCR > X ⇒ BUY_PE” row in yaml, fusion, or this spec. PCR Δ vs last snapshot is a **WATCH mixing reason** only.
2. **Scrape Moneycontrol HTML** (or GIFT/SGX/pre-open HTML) as the news path. Cite RSS / official XML. Skip HTML. Disable a yaml row if it 404s.
3. **1m full-chain.** Default is **3m** (`desk_intel.poll.chain_interval`). 1m = ATM±N quote on cached ids, and that switch is **off**. OI does not refresh that fast; HQ cap is 1 unique / 3s.
4. **Auto-retune.** Nightly emits `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`. Default **keep current strategy**. 05 does not write `config/workspace.yaml` knobs, 04 candidate params, or `packages/indicators/` from recon. `NEWS_DAY` / `EXPIRY` are **excluded** retune samples — 05 does not “fix” the book after a print.
5. **New STRAT IDs / headline alpha / win rates.** Clubbing = named mix of **001–014** + `DHAN-DERIVED` vs `PROJECT-DERIVED`. `_exm` OI walls stay heuristic + selling-class corpus. Phase-1 **buy first**.
6. **Promote CONFIRMED** from 05 inputs. **Call live Dhan** from this write. **Start npm.** **Invent Dhan REST fields, lots, or fills.**

---

## 5. Comments TO other teams

### TO 04_quant

- **Attach point:** 05 vetoes bind at **WATCH and EARLY**. **CONFIRMED requires your primary** (5m ST/MACD same-direction after EARLY). 05 will **never** promote CONFIRMED; after CONFIRMED we **only VETO**.
- On `NEWS_DAY` / `EXPIRY`, **do not** let leading mix print EARLY. Overlay is cheaper than a confident miss (30% capital-penalty bar in PERSONA_DESK).
- If **003** is the session primary and ST vs VWAP disagree → treat as **VETOED** (your own `no_new_entry_if`), not as a 05-invented chop ID.
- **008** mixed-index is a **filter overlay** 05 will fire as VETOED. Do not ask 05 to pick the “dominant” index after the close (look-ahead).
- Do not fold PCR extremes or mock sentiment windows into ALGO_HANDOFF as entry predicates. Chain Δ vs **last 3m snapshot** may sit in the **leading** mix next to impulse/range — still not PCR-only.
- 013–014 stay WAITING sell. Do not take `_exm` OI-wall sell language as Phase-1 product.

### TO 03_phd_market

- Keep PCR/OI **definitions** in CHAIN_METRICS as VALIDATION. **Do not** hand 05 a numeric PCR threshold and call it exchange law. If you later validate a band, label it VALIDATION with the sample; until then 05 will not invent one.
- **`EXPIRY` is your (and nightly’s) tag** — nearest sheet date = session date. 05 consumes it. **Do not retune** expiry weekday from this overlay. Lots / Tuesday folklore stay `FROM_CONTRACT`.
- `_exm` EXM-C09 OI walls = **heuristic**, dated snapshot, selling class. Do not upgrade to SOURCE_FACT as “institutions will not let this strike break.”
- CAS daily book stays **`UNVALIDATED`**. 05 will show it on WATCH only. Index F&O close **15:30 vs 15:40** remains VERIFY — 05 will not flatten from cash-CAS clocks.
- Quote `oi` on 1m ATM±N = **VERIFY FROM DOCS**. Until then, 3m full chain vs last snapshot is the only buildup 05 will trust as a mixing ingredient.

### TO 09_review

- This file is an **overlay spec**, not alpha from headlines, not a five-pass, not `RESEARCH_READY_FOR_PROGRAMMING`.
- Fail the review if anyone: (a) codes PCR-extreme entry, (b) scrapes Moneycontrol HTML, (c) defaults 1m full-chain, (d) auto-retunes from nightly, (e) adds STRAT-015, (f) lets 05 promote CONFIRMED, (g) treats mock sentiment windows as measured edge, (h) invents win rates.
- Docs Auditor PASS on HANDOFF/requirements is **not** product-ready. Dashboard P/L remains MOCK.
- Layers: 01 OI walls = SOURCE_FACT *as spoken* + heuristic tag; 03 PCR math = VALIDATION; 05 attach table = HYPOTHESIS. Keep them uncollapsed.

---

## HANDOFF (05)

**Accepted**

- News + 3m chain-vs-last + (mock) sentiment as **bias / veto** on the **existing 14** IDs.
- `NEWS_DAY` / `EXPIRY` block EARLY; `EXPIRY` owned by 03/nightly — not retuned here.
- CONFIRMED is 04-only; 05 veto-only after that.
- VETOED: news shock, 008 mixed-index, 003 ST vs VWAP disagree when 003 is primary.
- `_exm` OI = heuristic, selling class, Phase-1 buy-first.

**Rejected**

- Headline-as-entry STRAT. PCR-extreme-as-entry. New index IDs. Auto-retune. 1m full-chain default. Moneycontrol HTML scrape. CAS book as confirmed direction. Invented PCR numeric “Dhan law.” Invented win rates.

**UNKNOWN / DATA_INSUFFICIENT**

- Live chain until `DHAN_*`. Quote OI on 1m path. Moneycontrol RSS stability. `surprise_vs_consensus`. F&O close 15:30 vs 15:40. GIFT/SGX/pre-open public tape. Whether mock sentiment windows will ever become measured. 14 STRATs remain UNVALIDATED — no mix freeze.

---

## Compliance one-liner

`MARKET_SIGNAL` is a **bias / risk regime**. News is a **veto**, not a signal. Extreme PCR without price is **not** a signal. Sentiment slots are **mock**. See [`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md).
