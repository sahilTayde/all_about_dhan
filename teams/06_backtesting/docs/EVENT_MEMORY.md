# EVENT_MEMORY — two tracks: score without outliers, remember the outliers

**Team:** 06_backtesting (owns the split + analog schema)  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / **schema only**  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. Engine **exists**; SCORE_SAMPLE still empty (news calendar `DATA_INSUFFICIENT`).  
**Date:** 2026-09-03  

Education ≠ advice. **No live orders.** This file has **no backtest results**. Do **not** invent P/L, expectancy, profit factor, drawdown, win rates, or analog path numbers. Today every analog payload is **empty** / `DATA_INSUFFICIENT`.

**Customer ticket (2026-09-07):** Soft-default ``NEWS_VETO_ENABLED=false`` — news / BIG_NEWS / NEWS_DAY do **not** HOLD the paper customer ticket (notes/analog only). Set env true to restore mid-session BIG_NEWS HOLD. Fixture/routine MACRO rows remain pre-market sentiment. SCORE_SAMPLE still requires honest `NORMAL`.

Extends — does not replace — [`RETUNE_GATE.md`](RETUNE_GATE.md): session tags `NEWS_DAY` / `EXPIRY` / `NORMAL`; nightly `RETUNE_PROPOSAL` stays `BACKTEST_REQUIRED`; default **keep current strategy**; no auto-retune.

---

## Why this exists (founder ask)

News / event / expiry / circuit / gap days **fake an edge** if they sit in expectancy / PF / DD ranking. They must **not** score the book.

Those same days are still **learning**. Later, if similar news arrives, the boss / customer agent may say: we have seen this *type* of event before; the market *may* act like that. That sentence is a **hypothesis** once a real analog store exists — never a promised P/L.

Layer: **`HYPOTHESIS`**. Do not collapse into SOURCE_FACT. Session tags from nightly stay 05/desk-intel VALIDATION-of-tag; **use** of analogs as customer copy stays 05 overlay + this schema.

---

## Cited packets (coalition)

| Team | File | What 06 takes |
|------|------|----------------|
| 06 gate | [`RETUNE_GATE.md`](RETUNE_GATE.md) | `NORMAL` = retune / score sample. `NEWS_DAY` / `EXPIRY` excluded from ranking. Promote only OOS + `NORMAL` on expectancy / PF / DD vs current, or a documented glitch fix. |
| 05 overlay | [`SIGNAL_FUSION.md`](../../05_analysis/docs/SIGNAL_FUSION.md) | News / calendar → `NEWS_DAY` **veto**, not alpha. Extreme PCR-only = veto. Chain poll **3m**. |
| 00 persona | [`PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md) | Event window, expiry afternoon, circuit/halt → `NO_TRADE`. Analog copy must not become a ticket. |
| 04 mix | [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) · [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) | KEEP_ALL. 14 IDs + MIX-*. Conflicts stay extra MIX rows. Metrics **null**. |
| 04 book | [`MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md) | Index options Phase-1 vs `EQ-*` / `SO-*` other book. Nightly cannot auto-retune. |
| 04 staging | [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md) | 5m ST/MACD = confirm-or-kill. Customer `/` vs `/desk`. |
| 01 bind | [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) | Spoken English wins. `PROJECT_MIX` stays labeled. |
| 02 math | [`STRAT_001_014_VALIDATION.md`](../../02_phd_math/docs/STRAT_001_014_VALIDATION.md) | Disagreement = extra test, not a kill. |
| 03 market | [`STRAT_001_014_MARKET.md`](../../03_phd_market/docs/STRAT_001_014_MARKET.md) | Expiry / lots `FROM_CONTRACT`. Circuit halt is market structure. 3m is not HQ. |
| 03 CAS | [`cas/CAS_STRATEGIES.md`](../../03_phd_market/cas/CAS_STRATEGIES.md) · [`cas/RESEARCH.md`](../../03_phd_market/cas/RESEARCH.md) | CAS-* hypotheses. Daily `BOUNCE\|SIDEWAYS\|FALL` is `UNVALIDATED`. Index circuit can skip CAS. |
| 00 board | [`EXPERT_COALITION.md`](../../00_orchestrator/docs/EXPERT_COALITION.md) | 06 fixture engine later. No live orders. No nightly auto-retune. |
| Schema only | `packages/desk-intel` `schema.py` | `SessionKind` = `NEWS_DAY` \| `EXPIRY` \| `NORMAL`. `NewsEvent` citation fields. Nightly `retune_proposal.status` = `BACKTEST_REQUIRED`. |

---

## 1. Two tracks (must not collapse)

Every session recon may be **written**. Ranking and analog memory **split**.

| Track | Membership | What it is for | What it is not |
|-------|------------|----------------|----------------|
| **SCORE_SAMPLE** | `session_kind == NORMAL` **and** no analog outlier flags (`CIRCUIT`, `GAP`, halt) | Expectancy, profit factor, max drawdown, OOS ranking, retune comparison vs current spec | News-day hero P/L. Expiry pin. Circuit/gap one-offs. One-day paper/shadow. |
| **ANALOG_MEMORY** | `NEWS_DAY` and/or `EXPIRY` **or** `CIRCUIT` / `GAP` / halt flags, **stored anyway** | Later “days like this” lookup for boss/customer copy. Learning packet. | A ranking sample. A promote. A win-rate. An entry STRAT. |

**Align RETUNE_GATE:** if a day is not `NORMAL`, it is **out** of SCORE_SAMPLE. A day can carry both `NEWS_DAY` and `EXPIRY` in `session_flags` — still not `NORMAL`, still analog-only.

**Stricter than nightly `SessionKind`:** desk-intel today stamps only `NEWS_DAY` / `EXPIRY` / `NORMAL`. Circuit / gap / halt may occur on a session tagged `NORMAL`. 06 still **excludes** those from SCORE_SAMPLE and **writes** them to ANALOG_MEMORY. Do not retune `schema.SessionKind` in this file; add analog flags.

**SCORE_SAMPLE still empty** (2026-09-06 honest run) because the news calendar has no dated rows. ANALOG_MEMORY path fields stay null. Persist nightly JSON as recon; do not backfill invented analogs.

```text
POST_MARKET recon (session_kind + session_flags + news + chain + cas_calls)
        │
        ├─ SCORE_SAMPLE  ◄── NORMAL ∧ ¬CIRCUIT ∧ ¬GAP ∧ ¬halt
        │     ranking metrics (expectancy / PF / DD) — null until engine
        │     OOS + NORMAL promote test — still BACKTEST_REQUIRED
        │
        └─ ANALOG_MEMORY ◄── NEWS_DAY ∨ EXPIRY ∨ CIRCUIT ∨ GAP ∨ halt
              event analog records — observed_path_fields null until engine
              customer analog copy = HYPOTHESIS after data exists
```

A session is **never** scored as if the outlier were a typical day. A session is **never** dropped from memory because it would hurt the score.

---

## 2. Event analog record (schema — no numbers filled)

One record per `(session_date, analog_id)` when the session is analog-eligible. YAML and JSON share these keys. **Do not populate numeric path fields until an engine exists.**

```yaml
kind: EVENT_ANALOG
schema_version: 1                  # bump when keys change; not a metric
layer: HYPOTHESIS
status: DATA_INSUFFICIENT          # today: always. Later: RECORDED | MATCHED | STALE
engine_ran: false                  # stay false until 06 engine exists

session_date: null                 # YYYY-MM-DD IST session; null until written
session_kind: null                 # NEWS_DAY | EXPIRY | NORMAL (nightly SessionKind)
session_flags: []                  # may include NEWS_DAY, EXPIRY, and analog flags
analog_flags: []                   # CIRCUIT | GAP | HALT | EXPIRY | NEWS_DAY
                                   # SCORE_SAMPLE requires analog_flags empty
                                   #   and session_kind NORMAL

news_citations: []                 # cite, do not scrape HTML
# news_citations[] item:
#   source_id: null                # workspace.yaml sources.news[] id
#   cited_url: null
#   headline: null
#   time_ist: null
#   tags: []                       # calendar-style, not yaml feed stamp alone
#   keywords_hit: []
#   event: null                    # e.g. RBI_WATCH / CPI_PRINT — from NewsEvent
#   surprise_vs_consensus: null    # UNKNOWN on RSS; do not invent
#   layer: HYPOTHESIS

keywords: []                       # normalized analog type labels (see §2.1)
underlyings: []                    # subset of [NIFTY, BANKNIFTY, SENSEX];
                                   # equity analog uses EQ-* book ids — not STRAT-015+

observed_path_fields:              # null until engine — do not invent
  open_gap: null                   # vs prior close / pre-open; DATA_INSUFFICIENT
  CAS_close_vs_ref: null           # vs 03 REF_VWAP / IEP / 15:15 — not a hit rate
  CE_PE_lean: null                 # BUY_CE | BUY_PE | NEUTRAL | NO_TRADE | null

similar_to: []                     # later: analog_id refs. Empty until a matcher exists.

# Honesty — never filled as proof
score_sample_member: false         # analog records are false by definition
pnl: null
expectancy: null
profit_factor: null
max_drawdown: null
win_rate: null
backtest_results: null
```

JSON is the same object. Nightly recon may *point* at an analog file later (`analog_records: []`); until then the field is omitted or `[]`. Do not emit fake `observed_path_fields`.

### 2.1 `keywords[]` (type labels, not alpha)

Use **types**, not “this CPI print made +X pts.” Suggested vocabulary (extend, do not invent outcomes):

| Keyword (example) | Origin | Analog use |
|-------------------|--------|------------|
| `CPI` `RBI` `MPC` `FOMC` `GDP` `NFP` `BUDGET` | 05 / `retune_gate` calendar tags | `NEWS_DAY` type |
| `EXPIRY` `PIN` `GAMMA` | 03 / nightly sheet date = session date | `EXPIRY` type |
| `CIRCUIT` `HALT` | PERSONA_DESK / 03 index circuit | outlier flag |
| `GAP` `OPEN_GAP` | 03 / later OHLC vs prior close | outlier flag |
| `CAS_SKIP` | 03: CAS skipped on full-day index circuit | CAS style analog |

Keyword match is **hypothesis** for “similar news.” It is not a STRAT entry. 05 still **vetoes** EARLY on `NEWS_DAY` / `EXPIRY` ([`SIGNAL_FUSION.md`](../../05_analysis/docs/SIGNAL_FUSION.md)). Analog memory does **not** override that veto.

### 2.2 `observed_path_fields` (null until engine)

| Field | Meaning when engine exists | Today |
|-------|----------------------------|-------|
| `open_gap` | Signed gap vs prior official close (or documented pre-open ref). Construction `UNKNOWN` until 02/03 sign the ref. | `null` / `DATA_INSUFFICIENT` |
| `CAS_close_vs_ref` | CAS match / last vs 03 `REF_VWAP` / `IEP` / 15:15 note. Not a validated direction. CAS book stays `UNVALIDATED`. | `null` / `DATA_INSUFFICIENT` |
| `CE_PE_lean` | Observed staged lean or chain CE/PE bias **as recorded**, not a recommended ticket. | `null` |

Do not fill these from mock `apps/web` tickets. Mock ACHIEVED is not a path.

### 2.3 `similar_to[]` (later)

When a matcher exists: list `{ analog_id, overlap_keywords[], note }`. Overlap is **keyword/type**, not “same P/L.” Empty until then. Do not k-NN invent neighbors.

---

## 3. Promotion (unchanged from RETUNE_GATE)

| Rule | Status |
|------|--------|
| Nightly `retune_proposal.status` | **`BACKTEST_REQUIRED`** only |
| Auto-retune / write `config/workspace.yaml` knobs / 04 candidates / `packages/indicators/` | **Forbidden** |
| Invented metrics in analog or score payloads | **Forbidden** (`null`) |
| Promote | Only after a **real** engine run: **OOS + SCORE_SAMPLE (`NORMAL`, no analog flags)** beats **current** on expectancy, profit factor, max drawdown — **or** a documented glitch fix that passes the same test |
| One-day paper / shadow / analog path | **Not evidence** |
| Default | **Keep current strategy** |
| 02 PhD `NIGHTLY_YYYY-MM-DD.md` | **REVIEW**, not apply |
| Analog “we have seen this type” | **Not a promote.** Not a retune sample. |

06 later statuses (not emitted by nightly): `REJECTED`, `PROMOTE_CANDIDATE`. Freeze into spec is still 04 + 09.

**Empty engine ⇒ nothing promotes. Analog store empty ⇒ no customer analog copy with a path.**

---

## 4. Kill a MIX / STRAT only after real OOS + NORMAL

**Never** delete or “kill” a `MIX-*` / `STRAT-001`–`014` at spec time because 02 and 03 **disagreed**. Disagreement is a **test grid**, not a funeral.

| Spec disagreement (examples already on disk) | 06 action | Forbidden |
|----------------------------------------------|-----------|-----------|
| 007 vs 009 clocks; Phase-1 **AND** is `PROJECT_MIX` | Extra MIX rows: `007-only`, `009-only`, `007∧009` | Delete 007 or 009 from the catalog |
| 002 vs 005 strike | Keep `MIX-BULL` (005 on 003) **and** `BULL_ALT_001` (002 on 001). CONFLICT if merged | Merge onto one ticket |
| Spoken 3m vs HQ `{1,5,15,25,60}` | Extra MIX / ablation: resample 3m vs native 5m | Pick a winner in this file |
| Staging 5m ST/MACD confirm-or-kill vs HAUS MACD **entry** | Two test IDs — already `PROJECT_MIX` | Average them into soup |
| 011/012 `PROJECT_MIX` transfer; 09 Q4 FAIL if treated as Dhan NIFTY law | Keep labeled alt/overlay rows | Kill at spec because 03 rejected index transfer |
| 004 parked (`NOT_IN_EN` lengths); 010 OF `DATA_INSUFFICIENT` | Stay parked / extra row when data exists | Invent lengths or kill the ID |
| 013 / 014 WAITING sell vs Phase-1 buy | Separate **style** score (`OPTION_SELLER`), not deletion | Fold sell into buy ticket |

**Kill / `REJECTED` (06)** is allowed **only after** a real **OOS + SCORE_SAMPLE (`NORMAL`)** backtest on that named MIX/STRAT (costs, slippage, no look-ahead) and a 09 look. Spec conflict ≠ `REJECTED`.

04 already named alts (`BULL_ALT_001`, `BULL_ALT_006`, `BULL_ALT_011`, `MIX-BEAR`, `MIX-SIDEWAYS`). 06 consumes those as **rows**. 06 does not invent `STRAT-015+`.

---

## 5. Styles — score separately when the engine exists

Do **not** pool these into one expectancy number. Each style is its own SCORE_SAMPLE ranking (still `NORMAL` only) and may have its own analog notes. **Metrics stay `null` until the engine runs that style.**

| Style id | What it scores | On-disk home | Analog note |
|----------|----------------|--------------|-------------|
| **OPTION_BUYER** | Phase-1 CE/PE **buy** mixes (`MIX-BULL` / `MIX-BEAR` / alts on 001–012) | [`ENGINE_MIX.md`](../../04_quant/docs/ENGINE_MIX.md) | News/expiry still veto EARLY (05). Outliers out of score. |
| **OPTION_SELLER** | STRAT-013 / 014 **WAITING** sell class | same; not Phase-1 buy ticket | Selling anecdotes in 01 packets are not win rates. |
| **SCALPER** | Short-hold alts (e.g. STRAT-006); Super Scalper 004 **parked** until lengths exist | ENGINE_MIX alts | Gap/circuit days especially toxic for score — analog only. |
| **POSITION** | Multi-hour / swing-style index-option holds (001/003 trend books, not 2m scalp) | ENGINE_MIX primaries | Same SCORE_SAMPLE rule. Do not mix with scalp PF. |
| **EQUITY** | `EQ-*` / `SO-*` / `ETF-*` **other book** | [`EQUITY_ETF_BACKLOG.md`](../../04_quant/docs/candidates/EQUITY_ETF_BACKLOG.md) | **Never** pool with NIFTY/BN/SENSEX option SCORE_SAMPLE. |
| **CAS** | Closing Auction Session daily book (`BOUNCE\|SIDEWAYS\|FALL`) | [`cas/RESEARCH.md`](../../03_phd_market/cas/RESEARCH.md) | `UNVALIDATED`. `CAS_close_vs_ref` analog field. Circuit skip → analog flag `CAS_SKIP`. Not a CONFIRMED lean. |

Customer `/` still does not show style IDs or indicator soup. Style ranking is **06 + `/desk`**.

---

## 6. Honesty — analog language to the customer

| When | Allowed copy | Forbidden copy |
|------|----------------|----------------|
| **Today** (no engine, empty store) | Silence, or explicit `DATA_INSUFFICIENT`. No analog payload. | “Last CPI we were right.” Any pts / PF / DD. Mock ticket as analog. |
| **Later, after real ANALOG_MEMORY rows exist** | **Hypothesis:** “Days like this, *in sample*, the path was X.” Cite `keywords[]` / `session_date` / `news_citations[]`. Cap confidence. | “The market **will** do X.” “Our edge on news days is …” Promoting from analog. Overriding 05 `NEWS_DAY` veto. |

Boss / customer agent (05 + 00 persona) **may** use analog **type** after data exists. 06 supplies the record; 05 does not turn it into EARLY/CONFIRMED. Overlay remains veto / WATCH.

**In-sample path ≠ OOS score.** Analog sentences must not quote SCORE_SAMPLE metrics. SCORE_SAMPLE metrics must not include analog days.

Compliance: education ≠ advice. See [`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md).

---

## 7. What nightly will / will not (analog addendum)

| Nightly **will** (today + later) | Nightly **will not** |
|----------------------------------|----------------------|
| Keep stamping `session_kind` + `session_flags` | Fill `observed_path_fields` with invented gaps/leans |
| Keep `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` | Move analog days into SCORE_SAMPLE |
| Leave room for `analog_records: []` | Auto-retune from “similar CPI” |
| Copy CAS `cas_calls[]` as UNVALIDATED notes | Treat CAS daily bias as analog P/L |

06 engine (later): ingest recon, split tracks, write analog YAML/JSON under `teams/06_backtesting/` (or a gitignored data path named in a later ticket). **This spec does not code that engine.**

---

## HANDOFF (06 schema freeze — still UNVALIDATED)

**Accepted**

- Two tracks: SCORE_SAMPLE = `NORMAL` ∧ no circuit/gap/halt; ANALOG_MEMORY stores NEWS_DAY / EXPIRY / circuit / gap anyway.
- Analog record keys as specified; path fields **null** until engine.
- Promotion still `BACKTEST_REQUIRED`; no auto-retune; no invented metrics.
- MIX/STRAT kill only after real OOS + SCORE_SAMPLE; 02/03 disagreement → extra MIX row.
- Six styles scored separately when engine exists.
- Analog customer language = hypothesis after data; today `DATA_INSUFFICIENT`.

**Rejected**

- Ranking on news/expiry/circuit/gap days. Fake analog P/L or filled `open_gap` / `CAS_close_vs_ref` / `CE_PE_lean`. Killing STRAT/MIX at spec because PhDs disagreed. Analog as entry alpha. Pooling EQUITY or CAS into index-option SCORE_SAMPLE. Customer copy that the market *will* repeat.

**UNKNOWN / DATA_INSUFFICIENT**

- Engine. Historical option path. Gap construction (prior close vs pre-open vs GIFT). Analog matcher (`similar_to[]`). Live Dhan. All analog payloads.

Next: 05 may later *read* analog types for WATCH copy; 04 keeps extra MIX rows; 09 does not treat this file as a five-pass. 06 still does not code live STRATs.
