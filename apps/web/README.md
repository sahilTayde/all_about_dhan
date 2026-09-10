# apps/web — customer paper desk

Thin **Vite + React** UI for all_about_dhan. The default route is a **customer trading desk**: one live ticket, issued levels, take/skip, shadow paper, session book, and tape sentiment. **Not investment advice.** Owned by team 07_coding.

Engineers can open [`/desk`](http://localhost:5173/desk) for the research view (honesty stages, indicator lights, factor checklist). That route is **not** the customer product. Founder `/pm` is specified but **not built** yet.

Stack: Vite + React (JavaScript). No server render. No Dhan in the browser.

UX standard: [`docs/CUSTOMER_PORTAL_UX.md`](../../docs/CUSTOMER_PORTAL_UX.md). Architecture standard: [`docs/PRODUCT_ARCHITECTURE_STANDARDS.md`](../../docs/PRODUCT_ARCHITECTURE_STANDARDS.md).

## How to run

Needs **Node 18+** (`node -v`). If you only have conda and `node` is missing:

```bash
conda install -c conda-forge nodejs
```

Or install from [nodejs.org](https://nodejs.org). Then from repo root:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) (customer desk) or [http://localhost:5173/desk](http://localhost:5173/desk) (internal).

| Command | What it does |
|---------|----------------|
| `npm run dev` | Vite dev server on port 5173 |
| `npm run build` | Production bundle → `dist/` |
| `npm run preview` | Serve the production bundle locally |

Copy `.env.example` to `.env` only if you want a remote API later. Leave `VITE_API_URL` empty to use mock JSON.

## What the customer sees

- **NIFTY / BANKNIFTY / SENSEX** switcher
- **BUY CE / BUY PE** on one primary ticket card
- **Strike, entry, stop-loss, target** always shown on launch (from mock / API fields — never left blank in the mock)
- Ticket status: **WATCH / EARLY / CONFIRMED / IN-PROGRESS**, plus outcomes **ACHIEVED / STOPPED / INVALIDATED / EXPIRED / LOST**. After a live signal is issued (levels present, no close), status is **IN-PROGRESS**
- **(i)** opens a legend for colors and states. The legend is not dumped on the canvas
- **Market sentiment** last **1h / 30m / 15m / 10m**: BULLISH / BEARISH / SIDEWAYS (mock fusion; not an indicator list)
- **Close auction / cash bias** (`CasPanel`): **BOUNCE / SIDEWAYS / FALL** + last update (`cas` in mock JSON). Official CAS = Closing Auction Session. Not RSI/MACD.
- **Today’s book** (labeled **MOCK**): trades, strike, points, win/loss, **customer-taken vs platform shadow** counts
- Took-trade **Yes / No** with lots / spot / P-L; skip still shows **shadow paper**
- Stale-signal outcomes so lunch-return is not a leftover live ticket
- Disclaimer: not advice

The customer payload should stay compact and precomputed. No raw chain, no LLM call, and no Dhan call from the browser.

## What was removed from the customer page

- Supertrend / RSI / EMA / MACD **status lights**
- Contributing-factor checklist (news, chain OI, PA, Supertrend, MACD)
- On-canvas stage/outcome chip dump
- Research headlines that name lagging indicators

Those internals stay on **`/desk`** only.

## What this is / is not

- **Is:** customer paper desk UI with modular components and labeled mock data.
- **Is not:** a live strategy, a DhanHQ client, investment advice, or guaranteed returns.
- The browser never calls Dhan. Tokens stay out of this app.
- **IN-PROGRESS** means a ticket was issued. It is **not** a fill.
- **EARLY** is an honesty label, not a guaranteed trade.
- Closed tickets show a **lifecycle outcome**. A withdrawn lean is **INVALIDATED**, not leftover **CONFIRMED**.
- Book P/L and sentiment are **MOCK**. Do not treat them as production marks.

## Mock tabs

| Tab | Customer status | Notes |
|-----|-----------------|-------|
| **NIFTY** | **IN-PROGRESS** | Open PE ticket; levels 24850 / 95 / 62 / 155 |
| **BANKNIFTY** | **ACHIEVED** | Closed at mock target |
| **SENSEX** | **INVALIDATED** | Withdrawn after reversal |

WATCH / EARLY / CONFIRMED still render when JSON has no outcome and no issued levels. STOPPED / LOST / EXPIRED render when `lifecycle.outcome` is set.

## Data

Default: [`public/mock/signal.json`](public/mock/signal.json) via `GET /mock/signal.json`.

Shape the customer desk reads:

- `signals[UNDERLYING].strike|entry|stop|target`
- `signals[UNDERLYING].customer.headline|note` (no indicator names)
- `signals[UNDERLYING].lifecycle.outcome` + `shadowPaper`
- `sentiment.byUnderlying[UNDERLYING]` for `1h|30m|15m|10m`
- `cas.byUnderlying[UNDERLYING]` (`bias` BOUNCE|SIDEWAYS|FALL, `asOf`, `headline`, `layer`)
- `todaysBook.summary` + `todaysBook.rows` (always labeled MOCK)

`staged.lights` and `staged.factors` are **internal only**. `staged.state` stays `WATCH|EARLY|CONFIRMED|EXPIRED|VETOED` for `apps/api` compatibility. The customer UI maps an issued open ticket to **IN-PROGRESS**.

Later: set `VITE_API_URL` (for example `http://127.0.0.1:8000`). The loader will `GET ${VITE_API_URL}/paper/signal`. Do not put Dhan credentials in Vite env.

## Main files

| Path | Role |
|------|------|
| `src/App.jsx` | Customer desk |
| `src/InternalDesk.jsx` | `/desk` research view |
| `src/lib/signalApi.js` | Mock vs `VITE_API_URL` loader |
| `src/lib/status.js` | Customer status + legend copy |
| `src/components/SignalCard.jsx` | One primary ticket (side + levels + status) |
| `src/components/MarketSentiment.jsx` | 1h / 30m / 15m / 10m bias |
| `src/components/CasPanel.jsx` | Close auction / cash bias (BOUNCE / SIDEWAYS / FALL) |
| `src/components/TodaysBook.jsx` | Mock session ledger |
| `src/components/LegendDialog.jsx` | (i) legend |
| `src/components/TookTrade.jsx` | Yes / No + lots / spot / P-L |
| `src/components/SystemOutcome.jsx` | User fill or shadow paper |
| `src/components/Disclaimer.jsx` | Not advice |
| `src/components/StatusLights.jsx` | Internal only |
| `src/components/FactorChecklist.jsx` | Internal only |
| `public/mock/signal.json` | Placeholder payload |

## Extension points (not built)

- `TODO(api)` — `GET /paper/signal` should include `sentiment`, `todaysBook`, and `customer` copy
- `TODO(desk_intel)` — map `packages/desk-intel` MARKET_SIGNAL into sentiment (not indicator names)
- `TODO(jobs)` — nightly recon stamps `lifecycle.outcome` (not live Dhan from this UI)
- `TODO(signals)` — more than one active signal
- `TODO(auth)` — paper-user session
- `TODO(charts)` — premium / spot chart
- `TODO(strategy)` — real side/levels only after `RESEARCH_READY_FOR_PROGRAMMING`
- `TODO(pm)` — founder `/pm` health canvas (vendor keys, rate limits, chain freshness, API, RAG, nightly, auditor)
- `TODO(dealer)` — `FEASIBILITY_REJECTED` / `DEALER_KILLED` state so fantasy SL/target never stays live

See [`teams/07_coding/README.md`](../../teams/07_coding/README.md).
