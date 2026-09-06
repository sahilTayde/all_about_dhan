# Desk intelligence — news + option chain → MARKET_SIGNAL

**Status:** `DRAFT` / `HYPOTHESIS`. Bias and risk regime only. **Education ≠ advice.** Not a live strategy. No orders.

Ticket: [`teams/00_orchestrator/docs/TASK_DESK_INTELLIGENCE.md`](../../00_orchestrator/docs/TASK_DESK_INTELLIGENCE.md) · customer poll cadence [`TASK_CUSTOMER_DESK.md`](../../00_orchestrator/docs/TASK_CUSTOMER_DESK.md)  
Persona (how an operator **confirms** CE/PE): [`teams/00_orchestrator/docs/PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md)  
Chain metric definitions (VALIDATION vs HYPOTHESIS): [`teams/03_phd_market/docs/CHAIN_METRICS.md`](../../03_phd_market/docs/CHAIN_METRICS.md)  
Code: [`packages/desk-intel/`](../../../packages/desk-intel/)  
Customer knobs: [`config/workspace.yaml`](../../../config/workspace.yaml) `sources.news[]` and `desk_intel`

---

## What this is

A morning (and **3m**) fusion of:

1. **Global + national economic headlines** (RSS / official feeds — Moneycontrol RSS *if stable*, RBI, Fed, BLS, EIA, BBC business). Tag `MACRO_EVENT` when keywords match (GDP, PMI, CPI, RBI, crude, USDINR, …).
2. **DhanHQ option chain** for enabled index underlyings (NIFTY, BANKNIFTY, SENSEX). OI change, PCR, max-pain **stub**, ATM±N CE/PE buildup.
3. **PRE_MARKET tape (this ticket):** GIFT Nifty / SGX / NSE pre-open / extra US-close+Asia RSS. GIFT/SGX/pre-open are **VERIFY/TODO** public pages — **not Dhan endpoints**. `--offline` uses fixtures. Do not HTML-scrape quotes as the only path.

Jobs: `python -m desk_intel morning|pre-market --offline` (before 09:15 IST).  
`python -m desk_intel nightly|post-market --offline` or `python -m jobs post-market` (after close — **VERIFY** 15:30 vs 15:40; yaml `after_ist: "15:40"`).

Output: `MARKET_SIGNAL` — `underlying`, CE/PE lean (`BUY_CE` / `BUY_PE` / `NEUTRAL` / `NO_TRADE`), `confidence`, `reasons[]`, `vetoes[]`, `stage` (EARLY at most until lagging TA exists; **IN-PROGRESS** after CONFIRMED while a ticket is live), `outcome` (terminal; never leave CONFIRMED/IN-PROGRESS still valid after target/SL/invalidation), `sentiment_windows` (10m/15m/30m/1h **mock** slots). Adapter JSON matches later `GET /paper/signal` **shape** for directional leans only (`packages/desk-intel` `paper_signal.py`). `apps/api` is still mock — not wired.

Nightly: `data/recon/YYYY-MM-DD.json` + `teams/02_phd_math/docs/handoffs/NIGHTLY_YYYY-MM-DD.md`. Shadow paper P/L vs user P/L. Execution refused. Session tag + `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` — **no production param write**. Gate: [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md).

This does **not** replace independent validation or backtests. It must **not** depend only on canned topic strategies.

---

## How to run dry (no Dhan token)

From repo root:

```bash
cd /Users/sahiltayde/Documents/all_about_dhan
python3 -m venv .venv
source .venv/bin/activate
pip install -e packages/dhan-client -e packages/desk-intel

python -m desk_intel status
python -m desk_intel morning --offline
python -m desk_intel pre-market --offline
python -m jobs pre-market --offline
python -m desk_intel nightly --offline
python -m jobs post-market --offline
python -m desk_intel poll-chain --interval 3m --offline
python -m desk_intel poll-chain --interval 1m --offline
```

`--offline` skips RSS and uses packaged fixtures (including the crude 90→95 **hypothesis** example).  
Without `--offline`, news ingest **tries public RSS** (no Dhan token). Chain still dry-runs to fixtures if `DHAN_CLIENT_ID` / `DHAN_ACCESS_TOKEN` are empty.

`--dry-run` forces no Dhan HTTP. `--no-save` skips `data/desk_intel/**`. `--loop` on `poll-chain` sleeps the real interval until Ctrl-C.

---

## What needs tokens

| Call | Token? | Notes |
|------|--------|--------|
| News RSS / Fed / BLS / EIA / BBC | no | Public feeds. Moneycontrol historical RSS: **VERIFY IF STABLE** — disable the yaml row if it 404s/HTML. |
| Morning / **3m** `POST /optionchain` + expiry list | **yes** | Data API. Empty token → dry-run fixtures. 1 unique / 3s; 3m between **full** calls is OK. |
| 1m ATM±N `POST /marketfeed/quote` | **yes** | Quote 1 req/s. OI field on quote: **VERIFY FROM DOCS**; if missing → `DATA_INSUFFICIENT` for buildup. |
| Orders | — | **Never.** `dhan_client.execution` refuses `place_order`. |

Names only in `.env`: `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN`. Never log values.

Live (later):

```bash
python -m desk_intel --live morning
python -m desk_intel --live poll-chain --interval 3m
```

Underlying scrips are in `config/workspace.yaml` `markets[]` (`dhan_underlying_scrip`). Official option-chain example uses `13` unnamed. **VERIFY FROM the instrument master.** Do not treat 13/25/51 as eternal.

---

## 3m vs 1m design

Dhan: *Rate limit for Option Chain API is one unique request every 3 seconds* because OI updates slowly ([option-chain docs](https://dhanhq.co/docs/v2/option-chain/)). `OptionChainClient` waits 3s between live expiry-list/chain calls (`dhan_client.rate_limit.MinIntervalGate`). **3 minutes between full chain calls is inside that budget.**

Each full poll **remembers the last snapshot** (`data/desk_intel/snapshots/<UNDERLYING>/last.json` plus a timestamped file). The next poll computes **OI / PCR / ATM CE–PE Δ vs last** so trend and buildup can feed signals. First poll of a name has no memory — it falls back to Dhan `previous_oi` (day).

| Cadence | What we call | Why |
|---------|----------------|-----|
| **3m default** | Full `POST /optionchain` per enabled underlying (nearest expiry). 3 names × (expiry list + chain) is a handful of unique requests, gated 3s. | Whole strike sheet: PCR, walls, max-pain stub, day OI vs `previous_oi`, **3m Δ vs last snapshot**. |
| **1m optional** | **Not** full chain. Last snapshot’s ATM±`atm_wing` `security_id`s → `POST /marketfeed/quote`. Dry-run: synthetic OI bump on cached ids. | Stay inside quote’s 1 req/s. Chain REST is the wrong tool for 1m OI (slow update + heavy payload). |
| `--full-chain` on 1m | Still gated 1/3s. Logged as **not recommended**. | Technically a few unique chains/minute is under 20/min, but OI does not refresh that fast; yaml default `strike_buildup_enabled: false`. |

Customer edits: `desk_intel.poll.chain_interval`, `strike_buildup_interval`, `strike_buildup_enabled`, `remember_last_snapshot`, `atm_wing`.

### Sentiment windows (schema only)

Fusion attaches **10m / 15m / 30m / 1h** slots (`desk_intel.sentiment.windows`) so a dashboard can bind later. **Today those slots are mock** — they copy the current news+chain lean; they are **not** measured rolling windows and **not** edge.

---

## News sources (cite, don’t scrape)

Configured in `sources.news[]`. Parser accepts RSS 2.0 / Atom and **skips HTML**. RBI’s RSS index page is HTML — it is listed as `kind: official` so the parser skip is expected until a direct XML URL is verified.

| id | URL (as of ticket) | Cite |
|----|---------------------|------|
| moneycontrol_economy / latest | `https://www.moneycontrol.com/rss/….xml` | Historical community RSS. Official [moneycontrol.com/news/rss](https://www.moneycontrol.com/news/rss/) currently empty — **VERIFY IF STABLE**. |
| rbi_rss_index | [rbi.org.in/Scripts/rss.aspx](https://rbi.org.in/Scripts/rss.aspx) | Official RSS explainer. Press: [BS_PressReleaseDisplay](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx). |
| fed_press | [federalreserve.gov/feeds/press_all.xml](https://www.federalreserve.gov/feeds/press_all.xml) | Official Fed. |
| bls_latest | [bls.gov/feed/bls_latest.rss](https://www.bls.gov/feed/bls_latest.rss) | Official BLS. |
| eia_today | [eia.gov/rss/todayinenergy.xml](https://www.eia.gov/rss/todayinenergy.xml) | Official EIA. |
| bbc_business | [feeds.bbci.co.uk/news/business/rss.xml](https://feeds.bbci.co.uk/news/business/rss.xml) | Public BBC. |

**VERIFY/TODO tape** (not Dhan): `sources.gift_nifty[]` (NSE GIFT HTML + SGX delayed HTML), `sources.pre_open[]` (NSE pre-open page), `sources.global_tape[]` (Yahoo Finance news RSS, Moneycontrol international RSS). Parser still **skips HTML**. Fixtures when `--offline`.

`surprise_vs_consensus` is **UNKNOWN** on RSS. `CalendarPlaceholder` is the edit point for a real calendar.

Keyword maps (`MACRO_EVENT`, RISK_ON/OFF, NO_TRADE) are in yaml `desk_intel.keywords`. Crude spike language → RISK_OFF **hypothesis** for energy/INR; fusion **vetoes automatic PE**.

---

## Fusion (not canned STRAT-*)

`fusion.py` runs the persona checklist: event window, tape vs headline, opening drive, expiry-day pin, crude overlay, fake-breakdown stub. Agreement of news + chain can produce `BUY_CE` / `BUY_PE` with confidence **capped** (~0.72). Conflict → `NEUTRAL` / `NO_TRADE`. Reasons and vetoes are always attached.

ROOM TO EDIT: weights, veto minutes, opening-drive cutoff.

---

## Compliance

Never present this as investment advice or a guaranteed profit. Layer label is `HYPOTHESIS`. See [`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md).
