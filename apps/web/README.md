# apps/web — customer paper desk

Thin **Vite + React** UI for all_about_dhan. One site, three dashboards:

| Route | Who | Job |
|-------|-----|-----|
| [`/`](http://localhost:5173/) (`/customer` alias) | Customer (5 paper seats) | C5-03: CALL / PUT / HOLD hero · one ticket · risk strip · today book labeled PAPER / SHADOW / MOCK. No live orders. No win rate. |
| [`/desk`](http://localhost:5173/desk) | Desk | Alert bar · Current trade (entry, LTP, stop, T1/T2, trailing, P&L, elapsed, MFE/MAE) + paper target/stop override · Account (all recorded days; add funds / min capital) · Current market · Founder controls (compact) · Decision trace · Trade history (day picker, filters, columns) · Why days spilled |
| [`/pm`](http://localhost:5173/pm) | Founder | KPIs · System health (red/amber/green) + issues + next action · Account · START/STOP trade desk · Founder controls (start/stop, pause, blocked windows, lots, per-index, capital, cut loss, go for T2, kill switch + re-arm, command history) · Charts: cumulative P&L, daily/weekly/monthly P&L + win %, trades per day, per-model win % + trend, loss by stage · Now open · Decision trace · Compare fills · Honesty exam · Discarded · Roster (DEMO) |

Every panel shows `—` (or a greyed decision-trace step) when the data does not exist yet; nothing is invented. Panels still fed by static `public/mock` demo JSON (roster, STRAT lights, indicator pills) carry a **DEMO · mock** badge.

**Founder controls.** `POST /founder/controls/*` (localhost only) appends one timestamped command (who, why) to the durable founder log; the paper engine applies it from that timestamp on its next cycle and the history shows pending → applied / rejected. Kill switch, cut loss and re-arm ask for confirmation (a single-use token). PAPER only; no order leaves the box.

**Data flow.** Desk and Founder open one server-sent-events stream, `GET /ui/stream`, which pushes the whole read-only snapshot (`apps/api/src/api/ui_feed.py`) only when it changes. If the stream drops they fall back to one batched `GET /ui/snapshot` every 2 s; if the API is down they show the static mock board with a CRITICAL "Website lost the API" alert. Past days (`/paper/history?day=`) and the decision trace (`/paper/trace?trade_id=`) are fetched on click. The alert bar can play a sound and raise a browser notification for CRITICAL / EMERGENCY alerts after you press **Enable alarm**.

**Size.** Each page is its own chunk. Desk loads about 66 KB gzip of JS + 11 KB CSS; the chart library (lightweight-charts, 52 KB gzip) loads only on Founder and Customer.

**Not investment advice.** PAPER / MOCK. Orders refused. Owned by team 07_coding.

Stack: Vite + React (JavaScript). No server render. No Dhan in the browser.

UX standard: [`docs/CUSTOMER_PORTAL_UX.md`](../../docs/CUSTOMER_PORTAL_UX.md). Architecture standard: [`docs/PRODUCT_ARCHITECTURE_STANDARDS.md`](../../docs/PRODUCT_ARCHITECTURE_STANDARDS.md). Competitive baseline: [`docs/COMPETITIVE_PRODUCT_BASELINE.md`](../../docs/COMPETITIVE_PRODUCT_BASELINE.md).

## How to run

**Founder (whole desk, one command):** from repo root `./scripts/desk.sh morning`. After close `./scripts/desk.sh close` (website stays; capture + v2 recorder stop; honesty + nightly). `desk.sh` finds `node` on PATH, then `~/Documents/anaconda3/bin`, Homebrew, `/usr/local/bin`, or newest `~/.nvm`. Review: http://127.0.0.1:5173/desk and http://127.0.0.1:5173/pm. Details: [`SESSION_PREP_ML.md`](../../teams/06_backtesting/docs/SESSION_PREP_ML.md).

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

Open [http://localhost:5173/desk](http://localhost:5173/desk) (desk), [http://localhost:5173/pm](http://localhost:5173/pm) (founder), or [http://localhost:5173/customer](http://localhost:5173/customer) (customer preview).

| Command | What it does |
|---------|----------------|
| `npm run dev` | Vite dev server on port 5173 |
| `npm run build` | Production bundle → `dist/` |
| `npm run preview` | Serve the production bundle locally |
| `npm run ui:snapshots` | Playwright layout check on a synthetic fixture (see below) |

Copy `.env.example` to `.env` only if you want a remote API later. With `VITE_API_URL` empty, the pages reach the API through the Vite proxy (`/ui`, `/paper`, `/founder`, `/health`).

## Layout check (Playwright)

```bash
npx playwright install chromium   # once
npm run ui:snapshots              # or: node scripts/ui_snapshots/run.mjs --out /tmp/shots --widths 390,1280
```

Builds the app, serves the production bundle with `vite preview`, and answers every data URL from `scripts/ui_snapshots/fixture.mjs` (invented numbers on a fake past session; no market data, no network, no API) through a tiny in-process fixture API that includes a real `/ui/stream` push. It screenshots Desk, Founder, Customer and Cleanup at 390 / 1280 / 1440 / 1920 px into `scripts/ui_snapshots/out/` and exits 1 if:

- the page scrolls sideways, or any element is cut off at the viewport edge;
- the trade table's P/L / Status columns are not visible at 1280 px or wider;
- `NaN` / `undefined` shows on screen, or the page throws;
- a Desk / Founder panel is missing (alert bar, health rows, 7 trace steps, charts, account, current-trade fields, disabled next-PR controls);
- a pushed update takes 200 ms or more to reach the DOM, or the no-ticket state does not read ON HOLD.

It prints first-contentful-paint and data-ready times per page. `--root <dir> --no-features` runs the layout checks against another checkout (used for the before/after gallery).

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
- Future risk counsel feed: `RISK_REVIEW` / `PARTIAL_BOOK_REVIEW` / `EXIT_REVIEW` as review warnings, not executed orders
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
| `src/App.jsx` | Customer `/customer` |
| `src/InternalDesk.jsx` | Desk `/desk` live book |
| `src/FounderPm.jsx` | Founder `/pm` money board |
| `src/components/AppNav.jsx` | Customer / Desk / Founder switch |
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
- `TODO(alerts)` — in-app sound/toast first; Telegram/webhook later
- `TODO(counsel)` — async live risk counsel feed from compact state, token-budgeted

See [`teams/07_coding/README.md`](../../teams/07_coding/README.md).
