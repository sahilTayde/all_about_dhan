# all_about_dhan

Private workspace for a DhanHQ-only research and (later) paper-trading system on **NIFTY, BANKNIFTY, and SENSEX index options**. Working folder name only — no product brand yet.

**No live trading. No scraper or broker client in this bootstrap.** Structure and documents first.

---

## How to navigate

1. Agents start at [`AGENT.md`](AGENT.md).
2. Task → path map: [`docs/INDEX.md`](docs/INDEX.md).
3. Company board: [`PLAN.md`](PLAN.md).
4. YouTube Stage 1 plan (Codex, long): [`teams/01_research/youtube/PLAN.md`](teams/01_research/youtube/PLAN.md).

| Path | What it is |
|------|------------|
| `teams/00_orchestrator` … `teams/09_review` | Team-owned research, specs, notebooks |
| `apps/api`, `apps/web` | Product (empty until coding phase) |
| `packages/dhan-client`, `contracts`, `indicators` | Shared libraries (empty until coding phase) |
| `data/` | Catalogs and transcripts (payloads gitignored) |
| `secrets/` | Local secrets only — never commit |
| `docs/` | SDLC, research charter, review, security, handoffs |

---

## Rules of the road

- **Broker:** Dhan / DhanHQ only.
- **First markets:** index options CE/PE buy. Stocks, swing, and live orders are out of scope until later phases.
- **SDLC gate:** Research → independent validation → strategy spec → backtest → review → paper UI → live. Never skip.
- **Secrets:** copy `.env.example` to `.env`. Never put tokens in git or in chat. See [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Setup (humans)

```text
cp .env.example .env
# fill names in .env locally — do not commit .env
```

YouTube API key is required before Stage 1 catalog/transcript work. Dhan credentials are not needed until Phase 1 data infra.
