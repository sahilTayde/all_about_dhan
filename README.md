# all_about_dhan

Private workspace for a DhanHQ-only **index-options signal** company. First book: **NIFTY, BANKNIFTY, SENSEX** CE/PE **buy** tickets. Working folder name only — no product brand yet.

**No live orders.** Paper and research only. Gate is **not** `RESEARCH_READY_FOR_PROGRAMMING`. Do not treat dashboard P/L as a real book.

**Mac operations boundary:** on the founder's Mac, agents may start/stop services and tune the **legacy** engine. They must not edit V2. Paths: [`scripts/mac/protected_paths.txt`](scripts/mac/protected_paths.txt), [`AGENT.md`](AGENT.md) (top), [`.cursor/rules/mac-ops-boundary.mdc`](.cursor/rules/mac-ops-boundary.mdc).

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
| `apps/web` | Desk `/desk` (`/` redirects), founder `/pm`, customer preview `/customer` (DEMO panels badged) |
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

---

## Mac session night (paper only)

From the repo root on the Mac. **No live orders.** The legacy desk uses `.venv` (may be Python 3.9). V2 recorder + optional shadow use `.venv-v2` (3.11+) and never write into `.venv`. A missing recorder or shadow never blocks the legacy desk. Legacy dual-tape still owns the live paper book.

```bash
cd ~/Documents/all_about_dhan

# 1. Token — DHAN_CLIENT_ID + DHAN_ACCESS_TOKEN in repo-root .env
#    Optional daily mint (Mac TOTP, after one-time web.dhan.co setup):
#      ./scripts/mint_dhan_token.sh --check
#      ./scripts/desk.sh mint-token
#    morning does not mint. Never commit .env. Never print the token.
#    cp .env.example .env   # first time only

# 2. One-time (or whenever main gains recorder packages): isolated v2 venv
./scripts/mac_setup_v2.sh

# 3. Website (API :8000 + Vite :5173). Capture off.
./scripts/desk.sh website

# 4. Dual-tape at the cash open (Mon–Fri 09:30 IST)
./scripts/desk.sh watch-open

# 5. V2 recorder (caffeinate on macOS; screen v2-recorder; auto-stops 15:30 IST)
./scripts/desk.sh recorder-start

# 5b. Optional V2 shadow (paper log-only; screen v2-shadow; does not replace legacy)
./scripts/desk.sh shadow-start

# 6. Checks
./scripts/desk.sh status
./scripts/desk.sh recorder-status
./scripts/desk.sh shadow-status
# Desk:    http://127.0.0.1:5173/desk
# Founder: http://127.0.0.1:5173/pm

# 7. After 15:40 IST — stop capture + recorder + shadow, keep website, honesty + nightly
./scripts/desk.sh close
```

Same-morning shortcut: `./scripts/desk.sh morning` (runs `preflight`, then API + website + arms `watch-open`). `./scripts/desk.sh preflight` is also callable on its own. Details: [`SESSION_PREP_ML.md`](teams/06_backtesting/docs/SESSION_PREP_ML.md).

---

## 5-customer paper night checklist (C5-04)

Paper/shadow only. **Never live.** Shared `runtime signal` starts once. Each enabled `kind: customer` row gets its own `runtime exec --account`. Cap is **5 customer execs**. Founder and `v2-shadow` stay off unless you pass flags. C5 state lives under `data/c5/` and must not reuse legacy dual-tape (`data/recon/paper_watch`) or shadow (`data/shadow`) book paths.

```bash
# 0. Isolated V2 python (does not touch legacy .venv)
./scripts/mac_setup_v2.sh

# 1. Enable up to 5 paper customers (C5-01 templates already in accounts.yaml)
#    python -m accounts enable --account customer-01
#    Disabled rows are skipped. Never broker: dhan / live. No tokens in yaml.

# 2. Create paper state dirs (fail-closed if missing)
mkdir -p data/c5/signal
# one dir per enabled customer id, plus founder / v2-shadow if you will pass flags:
# mkdir -p data/c5/exec/cust-01 data/c5/exec/founder data/c5/exec/v2-shadow

# 3. Dry-run the plan (must print live_broker=false)
./scripts/desk.sh c5-start --dry-run
# optional: --with-founder --with-shadow

# 4. Start shared signal + customer execs (paper --once stubs)
./scripts/desk.sh c5-start

# 5. Checks
./scripts/desk.sh c5-status
# Backup the paper state dirs (no secrets; no legacy books)
./scripts/desk.sh c5-backup
# Restore smoke: list + verify tarball, do not write
./scripts/desk.sh c5-restore --dry-run --snapshot data/c5-backups/c5-paper.tgz

# 6. Stop C5 (ledgers kept). Does not stop legacy dual-tape.
./scripts/desk.sh c5-stop
```

If `c5-start` refuses: too many active customers (>5), an account is disabled/halted when you asked for it, broker is live, or a state dir is missing / points at a legacy book. Details: [`packages/accounts/README.md`](packages/accounts/README.md).
