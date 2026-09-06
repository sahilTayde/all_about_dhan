# packages/desk-intel

**PRE_MARKET** news + VERIFY tape (GIFT/SGX/pre-open/global) + DhanHQ option chain → `MARKET_SIGNAL` (bias / risk regime).  
**POST_MARKET** nightly recon: paper + shadow P/L, outcomes, PhD handoff.

Not advice. **No orders.** Shadow “platform takes the trade for learning” is a **paper ledger**, not live execution.

Owned with team 05_analysis. Tickets: [`TASK_DESK_INTELLIGENCE.md`](../../teams/00_orchestrator/docs/TASK_DESK_INTELLIGENCE.md), [`TASK_CUSTOMER_DESK.md`](../../teams/00_orchestrator/docs/TASK_CUSTOMER_DESK.md), [`TASK_PRE_POST_MARKET_JOBS.md`](../../teams/00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md), [`TASK_RETUNE_GATE.md`](../../teams/00_orchestrator/docs/TASK_RETUNE_GATE.md). How-to: [`teams/05_analysis/docs/DESK_INTELLIGENCE.md`](../../teams/05_analysis/docs/DESK_INTELLIGENCE.md). Persona: [`PERSONA_DESK.md`](../../teams/00_orchestrator/docs/PERSONA_DESK.md).

## Dry-run

```bash
cd /Users/sahiltayde/Documents/all_about_dhan
pip install -e packages/dhan-client -e packages/desk-intel -e packages/docs-auditor
python -m desk_intel status
python -m desk_intel morning --offline
python -m desk_intel pre-market --offline
python -m jobs pre-market --offline
python -m desk_intel nightly --offline
python -m jobs post-market --offline
python -m desk_intel audit-docs
python -m desk_intel poll-chain --interval 3m --offline
```

Empty `DHAN_*` ⇒ chain fixtures. `--offline` ⇒ news + GIFT/pre-open/global fixtures. Never prints tokens.

## Modules

| Module | Role |
|--------|------|
| `news_ingest` | RSS/Atom/official feeds from `sources.news[]`. `MACRO_EVENT` + risk_bias. Surprise UNKNOWN. |
| `premarket` | GIFT/SGX/pre-open/global tape. RSS fetched; `kind: verify` is documented URL only (no HTML scrape). |
| `option_chain_poller` | Morning/**3m** `POST /optionchain` (remembers last snapshot; OI/PCR/ATM Δ vs last); optional 1m ATM±N quote/cached delta. |
| `fusion` | News + chain → `MARKET_SIGNAL`. Directional lean is **EARLY** at most (no 5m ST/MACD yet). Sentiment windows 10m/15m/30m/1h are **mock schema**. |
| `outcomes` | Live stage **IN-PROGRESS** after CONFIRMED. Terminal labels: ACHIEVED / STOPPED / INVALIDATED / EXPIRED / LOST / COMPLETED / SHADOW_CLOSED. Never leave CONFIRMED/IN-PROGRESS still valid after a terminal event. |
| `ledger` | Paper + shadow P/L JSON. Execution refused. |
| `nightly` | POST_MARKET recon JSON + PhD markdown. Emits `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`. Loads `cas_calls[]` from `teams/03_phd_market/cas/calls/` (empty if missing). **Never** writes production params. CLI then runs **Docs Auditor**. |
| `docs_audit` | Wrapper for `packages/docs-auditor` (`python -m desk_intel audit-docs`). |
| `retune_gate` | Session tag `NEWS_DAY` / `EXPIRY` / `NORMAL`. Default keep current strategy. |
| `paper_signal` | Adapter toward `/paper/signal` (directional leans only). |
| `store` | JSON under `data/desk_intel/` and `data/recon/` (gitignored payloads). |

ROOM TO EDIT: keyword maps and poll intervals in `config/workspace.yaml`; fusion weights in `fusion.py`; job clocks in `jobs.*` (session close is **VERIFY**).
