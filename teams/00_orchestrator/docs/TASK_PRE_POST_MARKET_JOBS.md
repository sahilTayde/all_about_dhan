# TASK — PRE_MARKET / POST_MARKET jobs + signal outcomes + nightly recon

**Date opened:** 2026-09-01  
**Date closed:** 2026-09-01  
**Assigned:** 05_analysis (`packages/desk-intel`) · 00_orchestrator (this ticket)  
**Informed:** 02_phd_math (nightly handoff) · 04_quant (outcomes on staging) · 06_backtesting · 08_testing · 07_coding (paper JSON stubs only)  
**Status:** `DONE` (skeleton; dry-run; **no live Dhan**; **no orders**)  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`

---

## Requirement (ops)

Customer returning from lunch must **not** see a stale CONFIRMED. The firm must **paper + shadow P/L** before 30% capital pain. Two scheduled jobs, nightly recon handed to PhD as **REVIEW** (not auto-apply). Retune gate: [`TASK_RETUNE_GATE.md`](TASK_RETUNE_GATE.md).

## Cross-check — what `desk_intel morning` already did

| Source | Already in morning? | This ticket |
|--------|---------------------|-------------|
| News / govt-calendar **keywords** (GDP, PMI, CPI, RBI, Fed, BLS, EIA, BBC) | **Yes** (`sources.news[]` + `news_ingest`) | Still RSS/official. Surprise UNKNOWN. |
| Dhan option-chain snapshot | **Yes** (`POST /optionchain` or fixtures) | Unchanged. Token → live; empty → fixtures. |
| US close / Asia as **headlines** | **Partial** (Fed/BLS/EIA/BBC; `moneycontrol_global` was disabled) | Added `sources.global_tape[]` (Yahoo Finance RSS VERIFY + Moneycontrol international RSS VERIFY). |
| GIFT Nifty / SGX | **Missing** | Added `sources.gift_nifty[]` as **VERIFY/TODO** (NSE GIFT page + SGX delayed HTML). **Not** a Dhan endpoint. `--offline` fixtures only. |
| NSE pre-open grid | **Missing** | Added `sources.pre_open[]` **VERIFY**. No documented Dhan pre-open REST. |
| Regime note | Fusion reasons only | Premarket `regime_note` + tape missing flags. |

Do **not** call live Dhan without tokens. Dry-run / fixtures OK.

## Done

- [x] `config/workspace.yaml` `jobs.pre_market` / `jobs.post_market` (session close **UNKNOWN** — VERIFY 15:30 vs 15:40)
- [x] CLI: `python -m desk_intel morning|pre-market` and `python -m desk_intel nightly|post-market`; `python -m jobs pre-market|post-market`
- [x] Outcomes: `ACHIEVED` `STOPPED` `INVALIDATED` `EXPIRED` `LOST` `COMPLETED` `SHADOW_CLOSED`
- [x] Paper + shadow ledger (never live orders)
- [x] Nightly JSON `data/recon/YYYY-MM-DD.json` + PhD `teams/02_phd_math/docs/handoffs/NIGHTLY_YYYY-MM-DD.md`
- [x] PERSONA_DESK stale-signal rule; SIGNAL_STAGING outcomes; 06/08 prerequisites

## CLI (dry)

```bash
pip install -e packages/dhan-client -e packages/desk-intel
python -m desk_intel status
python -m desk_intel morning --offline
python -m jobs pre-market --offline
python -m desk_intel nightly --offline
python -m jobs post-market --offline
```

Nightly recon path: `data/recon/YYYY-MM-DD.json` (gitignored). Handoff: `teams/02_phd_math/docs/handoffs/NIGHTLY_YYYY-MM-DD.md`.  
Additive key **`cas_calls[]`**: loaded from `teams/03_phd_market/cas/calls/YYYY-MM-DD.json` (03 CAS analyst). Pattern notes only; **BACKTEST_REQUIRED**; never auto-retune. Ticket [`TASK_CAS_ANALYST.md`](TASK_CAS_ANALYST.md).

**Docs Auditor (follow-on, standing):** nightly / `python -m jobs post-market` **ends with** `python -m docs_auditor`. Cadence `jobs.docs_auditor: daily`. Ticket [`TASK_DOCS_AUDITOR.md`](TASK_DOCS_AUDITOR.md). Exit 1 if docs are stale; recon files are still written.

## Not this ticket

- Live orders (execution remains **refused**)
- Full pytest suite (smoke only)
- Rewriting live strategy math
- Inventing Dhan GIFT/SGX/pre-open REST
- Hardcoding F&O close 15:30 vs 15:40 forever
- Auto-applying nightly param hints (follow-on: [`TASK_RETUNE_GATE.md`](TASK_RETUNE_GATE.md))
