# all_about_dhan

Private workspace for a DhanHQ-only **index-options signal** company. First book: **NIFTY, BANKNIFTY, SENSEX** CE/PE **buy** tickets. Working folder name only — no product brand yet.

**No live orders.** Paper and research only. Gate is **not** `RESEARCH_READY_FOR_PROGRAMMING`. Do not treat dashboard P/L as a real book.

---

## How to read this repo

1. Agents: [`AGENT.md`](AGENT.md) → [`CONTINUE_NEXT_CHAT.md`](teams/00_orchestrator/docs/CONTINUE_NEXT_CHAT.md) → [`docs/FILE_CREATION.md`](docs/FILE_CREATION.md).
2. Score sheet: [`docs/MASTER_REQUIREMENTS.md`](docs/MASTER_REQUIREMENTS.md).
3. Task → file: [`docs/INDEX.md`](docs/INDEX.md).
4. Company board: [`PLAN.md`](PLAN.md).
5. Knobs (URLs, books, sources): [`config/workspace.yaml`](config/workspace.yaml). Secrets stay in `.env`.

**Founder talks to D4 PM.** Teams `00`–`09` stay numbered. Do not glob the whole tree.

---

## Strategy book (we hold these — not a promote)

One catalog: [`teams/04_quant/docs/MIX_CATALOG.md`](teams/04_quant/docs/MIX_CATALOG.md). Teacher files: `teams/04_quant/docs/candidates/STRAT-001.md` … `STRAT-014.md`. TV list: [`refernece_tradingview/editors_picks/INDEX.md`](refernece_tradingview/editors_picks/INDEX.md).

| Source | IDs we keep | Notes |
|--------|-------------|--------|
| **Dhan platform** (`@DhanHQ` videos) | `STRAT-001`–`014` | `BACKTEST_BOOK`. Never delete. Seller 013/014 stay parked off the buy UI. |
| **Dhan clubs / marketplace concepts** | `MIX-DEFAULT-BUY`, Gokul/Haus mixes, `MIX-ALGO-*` | Algo marketplace = concepts only. Returns on algos.dhan.co are marketing. |
| **TradingView Editors’ Picks** | `MIX-TV-EP-001`–`023` plus factory `024`–`025` | Pine not in git. KEEP_ALL. Not the customer ticket. |
| **ML models** | `ML-001`, `ML-002`, `MIX-FORM-*`, scan `MIX-ML-LOGIT*` | Overlays HOLD/WATCH. Empty window ≠ delete. |
| **Paper lab** | `MIX-CHAMP-*`, `MIX-LEAN-*`, `MIX-TA-*` | Closed-premium P/L still missing. **NO_PROMOTE.** |
| **Not the working book** | `CAS-001`–`005` / `MIX-CAS` | **PARKED** 2026-09-16 (founder). Exchange clocks stay in `cas/RESEARCH.md`. STRAT-009 stays. |
| **Not the working book** | Chart Fanatics / `MIX-CF-*` / Okala | Removed 2026-09-09 (DhanHQ-only reset). |

---

## Map (keep this picture)

```text
Founder  →  D4 PM  (00)
              │
   Factory (ideas)              Machine (code)
   teams/00 … 09                apps/ + packages/
   01 facts → 02 math → 03 market
        → 04 MIX/STRAT spec → 05 dealer talk
        → 06 backtest → 09 review
   07/08 ship the product
```

| Path | What it is |
|------|------------|
| `teams/00_orchestrator` … `09_review` | Pipeline: tickets, research, specs, review. **Team 02 lives in `02_phd_math` only.** |
| `apps/web` | Customer `/`, research `/desk`, founder `/pm` (UI still MOCK in places) |
| `apps/api` | FastAPI. Dhan **data** allowed when token is set. **Orders refused.** |
| `packages/dhan-client` | DhanHQ client + SafeMode |
| `packages/desk-intel` | News + 3m chain → desk signal / nightly jobs |
| `packages/desk-ml` | Local ML overlay (HOLD/WATCH). **NO_PROMOTE** |
| `packages/backtest` | Historical + TV-EP factory / paper tune |
| `packages/warehouse` | SQLite warehouse schema (do not git-add live sqlite) |
| `packages/agent_rag` | FTS5 research store |
| `packages/trading_agents_india` | Paper dual-tape / dealer roles |
| `packages/docs-auditor` | `python -m docs_auditor` |
| `packages/contracts` | Shared schemas |
| `packages/indicators` | Empty **on purpose** (no fake Supertrend REST) |
| `config/` | `workspace.yaml` — customers change this |
| `data/` | Catalogs, transcripts, paper recon (payloads gitignored) |
| `scripts/` | Operator loops (dual-tape, monitor). Not the product UI |
| `refernece_tradingview/` | TV Editors’ Picks inventory (`MIX-TV-EP-*`). Folder name is a typo; **do not rename this week** (code + docs paths) |
| `research/` | Pointers only. Indicator KB + how to clone TradingAgents. **Not product code** |
| `secrets/` | Local only — never commit |
| `docs/` | SDLC, compliance, departments, file-creation rules |

---

## Rules of the road

- **Broker:** Dhan / DhanHQ only.
- **First markets:** index options CE/PE buy. Stocks and live fills stay later.
- **SDLC:** Research → independent validation → strategy spec → backtest → review → paper UI → live. Never skip.
- **KEEP_ALL:** `STRAT-001`–`014` stay in the book. No `STRAT-015+`.
- **Secrets:** copy `.env.example` to `.env`. Never paste tokens in git or chat. [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Setup (humans)

```text
cp .env.example .env
# fill names in .env locally — do not commit .env
```

YouTube catalog work needs `YOUTUBE_API_KEY`. Live Dhan **quotes** need `DHAN_*` in `.env`; **orders stay refused** in code. Empty `DHAN_*` → fixtures.
