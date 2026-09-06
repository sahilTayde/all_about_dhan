# CAS special analyst (03_phd_market)

Hidden-to-retail **close mechanism** that can reprice **NIFTY / BANKNIFTY / SENSEX** after the cash tape looks dead.

**Official expansion (2026 NSE/BSE/SEBI):** **Closing Auction Session (CAS)** — not periodic-call-auction, not “cash” slang. Evidence and rejected aliases: [`RESEARCH.md`](RESEARCH.md).

## Mission

- Own the **CAS book**: clocks, equilibrium vs VWAP, indicative index, NSE vs BSE, expiry settlement.
- Publish a **daily** `BOUNCE | SIDEWAYS | FALL` per index with confidence and **`UNVALIDATED`**.
- Feed **`cas_calls[]`** into the existing nightly recon. Patterns may become **backtest proposals** only.
- Customer dashboard shows **close-auction / cash bias**, not RSI/MACD.

Ticket: [`../../00_orchestrator/docs/TASK_CAS_ANALYST.md`](../../00_orchestrator/docs/TASK_CAS_ANALYST.md).

## Layout

| Path | Role |
|------|------|
| [`RESEARCH.md`](RESEARCH.md) | What CAS is, URLs, other mechanisms tagged |
| [`METHODOLOGY.md`](METHODOLOGY.md) | How we call the day |
| [`CAS_STRATEGIES.md`](CAS_STRATEGIES.md) | `CAS-001`…`005` hypotheses (not STRAT-015+) |
| [`HANDOFF.md`](HANDOFF.md) | Newest first |
| [`notes/`](notes/) | Daily narrative |
| [`calls/YYYY-MM-DD.json`](calls/) | Machine `cas_calls[]` for nightly |
| [`notes/_TEMPLATE.md`](notes/_TEMPLATE.md) | Copy for a new session |

## Daily loop (no orders)

1. Before 15:00 — news, expiry flag, chain snapshot (DhanHQ if token; else fixtures).  
2. 15:00–15:15 — `REF_VWAP` + `CASH_BASIS`.  
3. 15:20–15:30 — IEP / imbalance / indicative index if we have a feed; else **DATA_INSUFFICIENT**.  
4. After 15:35 — official close vs ref; write the note + `calls/` JSON.  
5. After 15:40 — `python -m desk_intel nightly` (or `--offline`). Confirm `cas_calls` landed.

## As of now (2026-09-01)

CAS = **Closing Auction Session**. Daily book SIDEWAYS / `DATA_INSUFFICIENT` / **UNVALIDATED**. `cas_calls[]` retune **BACKTEST_REQUIRED**. **CasPanel** on customer `/` (not `/desk`). Book P/L elsewhere on the desk is **MOCK**. YouTube **45** verified + **45** English. `config/workspace.yaml`. Dhan **dry-run, no orders**. Chain **3m**. STRATs **UNVALIDATED**. No live tape. No win rates.

## Dashboard hook

- Component: `apps/web/src/components/CasPanel.jsx`
- Mock: `apps/web/public/mock/signal.json` → `cas.byUnderlying`
- Wired on the **customer** desk (`App.jsx`) as **Close auction / cash bias** (verified 2026-09-01).
- If another agent is mid-rewrite of `App.jsx` and the import disappears: **re-import `CasPanel`**; do not invent a second CAS UI. Do not fight a huge App rewrite.

## Do not

- Place orders.  
- Invent win rates.  
- Auto-retune `04_quant` candidates from one recon file.  
- Collapse PCA / pre-open / “cash volume” into the CAS acronym.
