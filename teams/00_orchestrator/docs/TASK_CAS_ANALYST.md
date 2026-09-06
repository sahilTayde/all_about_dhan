# TASK — CAS special analyst (Closing Auction Session)

**Date opened:** 2026-09-01  
**Date closed:**  
**Assigned team:** `03_phd_market` (owner)  
**Informed:** `05_analysis` (nightly recon book) · `07_coding` (CasPanel) · `06_backtesting` (gate only) · `00_orchestrator` (roster)  
**Owner path:** `teams/03_phd_market/cas/`  
**Status:** `IN_PROGRESS` (research + skeleton; **no live Dhan**; **no orders**)  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`

---

## Requirement

A **special analyst** for the Indian-market term **CAS** — the close mechanism that can **reprice** NIFTY / BANKNIFTY / SENSEX after continuous cash looks flat.

Do **not** guess one acronym and freeze it. Verify on **nseindia.com**, BSE (SENSEX), circulars, then blogs. Track **all** relevant mechanisms, tagged.

## What research found (2026-09-01)

| Tag | Meaning | Index flip? |
|-----|---------|-------------|
| **CAS** | **Closing Auction Session** (SEBI/NSE/BSE, live **3 Aug 2026**) | **Yes** — official close = equilibrium of F&O-cash names; indicative index during 15:20–15:30 |
| PRE_OPEN | Pre-open call auction | Open, not the CAS acronym |
| PCA | Periodic call auction (illiquid) | **No** for these indices |
| CASH_BASIS | Trader “cash vs F&O” | Overlay only |

Sources and URLs: [`teams/03_phd_market/cas/RESEARCH.md`](../../03_phd_market/cas/RESEARCH.md).

## Constraints (kept)

- **DhanHQ only** for chain. No live orders.
- Daily output: **BOUNCE / SIDEWAYS / FALL** + confidence + **`UNVALIDATED`**. No fake win rates.
- Nightly: same recon file, separate **`cas_calls[]`**. Proposals through **backtest gate**. Never auto-retune.
- Customer UI: close-auction / cash bias only. **No RSI/MACD list.**
- If `App.jsx` is mid-rewrite: ship `CasPanel.jsx` + README “wire into App”; do not fight a huge rewrite. *(This pass: App was stable — panel is imported.)*

## Done

- [x] This ticket + roster line in `AGENT.md`
- [x] Team home `teams/03_phd_market/cas/` (README, RESEARCH, METHODOLOGY, HANDOFF, notes, calls)
- [x] First `RESEARCH.md` from fetched NSE/BSE pages + circular mirrors
- [x] Nightly `cas_calls[]` loader (`packages/desk-intel` `nightly.py`)
- [x] `apps/web/src/components/CasPanel.jsx` + mock `cas` in `signal.json`
- [x] CasPanel on customer `App.jsx`

## Not this ticket

- Live orders
- Downloading every NSE PDF into git
- A coded CAS strategy or win rate
- HTML-scraping NSE indicative index as the only path
- Rewriting `InternalDesk` indicator soup onto the customer page

## How to run dry

```bash
python -m desk_intel nightly --offline
```

Expect `cas_calls` in `data/recon/YYYY-MM-DD.json` when `teams/03_phd_market/cas/calls/YYYY-MM-DD.json` exists. PhD markdown section **CAS calls**.
