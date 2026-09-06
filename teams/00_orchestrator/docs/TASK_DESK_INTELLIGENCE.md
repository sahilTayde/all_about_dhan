# TASK — Desk intelligence (morning news + option-chain signals)

**Date opened:** 2026-09-01  
**Date closed:** 2026-09-01  
**Assigned team:** 05_analysis (owner) + `packages/dhan-client` + 03_phd_market  
**Owner path:** `packages/desk-intel/` + `teams/05_analysis/docs/DESK_INTELLIGENCE.md`  
**Status:** DONE (skeleton; dry-run; no orders)

---

## Requirement

Morning analysis for **global + national economic news** (Moneycontrol *or similar*, via RSS/official feeds — not an HTML scrape as the only path) fused with the **NSE/BSE option chain** from DhanHQ.

Output is **MARKET_SIGNAL**: bias / risk regime that can lean BUY CE or BUY PE. Not a canned-strategy dump. Not a guaranteed call. Agents watch major news, govt data (GDP, PMI, CPI, RBI, crude, USDINR), and chain OI / PCR / buildup.

Persona: expert tape-reader / operator. **Confirm** means checklist + data, not omniscience. See [`PERSONA_DESK.md`](PERSONA_DESK.md).

## Constraints (kept)

- Broker/data: **DhanHQ only** for the chain (`packages/dhan-client`). Official option-chain REST: **1 unique request / 3 seconds** ([docs](https://dhanhq.co/docs/v2/option-chain/)). Default poll **3m** (updated [`TASK_CUSTOMER_DESK.md`](TASK_CUSTOMER_DESK.md); was 15m). **1m** is optional ATM±N / cached delta — do not poll the full chain every minute as the default. Remember last snapshot for OI/PCR/ATM Δ.
- News: RSS / public / documented feeds. Cite sources. Tag `MACRO_EVENT`.
- Education ≠ advice ([`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md)). Crude 90→95 → energy/INR/risk-off **hypothesis**, not automatic PE spray.
- Tokens from `.env`. Never log secrets. Dry-run without `DHAN_*`.
- Do **not** place orders. Leave room for edits.

## Done

- [x] This ticket + persona
- [x] `packages/desk-intel` — `news_ingest`, `option_chain_poller`, `fusion`, CLI
- [x] `dhan_client.rate_limit.MinIntervalGate` on option-chain REST
- [x] `config/workspace.yaml` `sources.news[]` + `desk_intel.poll` (chain default **3m**; see [`TASK_CUSTOMER_DESK.md`](TASK_CUSTOMER_DESK.md))
- [x] Docs: [`teams/05_analysis/docs/DESK_INTELLIGENCE.md`](../../05_analysis/docs/DESK_INTELLIGENCE.md)
- [x] Market-metrics note: [`teams/03_phd_market/docs/CHAIN_METRICS.md`](../../03_phd_market/docs/CHAIN_METRICS.md)
- [x] AGENT.md / INDEX pointers

## Not this ticket

- Live orders, strategy coding, wiring `apps/api` `/paper/signal` to this feed (adapter JSON exists; FastAPI still mock)
- Moneycontrol HTML scrape
- Economic-calendar consensus prints (schema field is UNKNOWN until a calendar adapter is filled)

## How to run dry

See [`teams/05_analysis/docs/DESK_INTELLIGENCE.md`](../../05_analysis/docs/DESK_INTELLIGENCE.md) and [`packages/desk-intel/README.md`](../../../packages/desk-intel/README.md).
