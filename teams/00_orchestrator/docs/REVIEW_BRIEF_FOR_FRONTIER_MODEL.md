# REVIEW_BRIEF — for the frontier model (morning)

**Date frozen:** 2026-09-01. User slept. You are auditing against [`docs/MASTER_REQUIREMENTS.md`](../../../docs/MASTER_REQUIREMENTS.md). That sheet is the score. This brief is what **not** to trust.

**Do not** restart `npm` / re-run catalog / call live Dhan / invent win rates / mark `RESEARCH_READY_FOR_PROGRAMMING`.

---

## What to audit (real requirements)

1. **Honesty of status.** Tickets labeled `DONE` are often **docs + dry-run**. Confirm MASTER_REQUIREMENTS row status (DONE / PARTIAL / TODO / BLOCKED) against files, not against AGENT checkboxes.
2. **SDLC not skipped.** Research → validation → spec → backtest → review → paper → live. Gate still **not** `RESEARCH_READY_FOR_PROGRAMMING`. [`docs/REVIEW.md`](../../../docs/REVIEW.md).
3. **Broker / orders.** DhanHQ only. `packages/dhan-client` `ExecutionClient` must still refuse `place_order`. No `/alerts/orders` client. Browser must not hold Dhan tokens.
4. **Indicators.** Official catalog says **no Supertrend/RSI/MACD/EMA9 series API**. `EMA_9` not in annexure. `packages/indicators` empty is **correct**, not a bug. [`DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md).
5. **Desk intel.** Default full chain **3m** + last snapshot. 1m full-chain is the wrong default. News via RSS/official, not Moneycontrol HTML scrape. PRE/POST jobs dry-run only. GIFT/SGX/pre-open = VERIFY pages, not Dhan REST.
6. **Retune gate.** [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md). Nightly emits `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`, `keep_current_strategy: true`, `production_params_written: false`. Promote only after OOS + `NORMAL` (non-event) backtest on expectancy / PF / DD, **or** a documented glitch fix that backtests clean. News/expiry days are **not** a retune sample. Engine **does not exist** — nothing can promote.
7. **CAS.** Official term = **Closing Auction Session** (F&O cash names, 15:15–15:35 IST, live 3 Aug 2026). Not pre-open, not PCA. Home [`teams/03_phd_market/cas/`](../../03_phd_market/cas/). Daily `BOUNCE|SIDEWAYS|FALL` is **`UNVALIDATED`**. Recon `cas_calls[]`. UI `CasPanel`. **No win rates.** First day SIDEWAYS / `DATA_INSUFFICIENT`.
8. **Staged signals.** Spec WATCH → EARLY → CONFIRMED → IN-PROGRESS → outcomes. Customer UI must not show indicator soup. `/desk` is internal. EARLY ≠ fill. ~1 min lead is a **target**. 5m ST/MACD confirm-or-kill.
9. **Dashboard.** Ticket SL/target, (i) legend, book, sentiment windows, CasPanel, `/desk`. All **mock** unless proven otherwise.
10. **Provenance.** Three layers: `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`. Education ≠ advice ([`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md)). 14 STRATs stay DRAFT. Spoken-rule authority is [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) (English `normalized_en/`). A mix that only copied STRAT timestamps is stale. Spoken SEBI RA / “Star Trader” is affiliation, not edge.

---

## What **not** to trust

| Artifact | Why |
|----------|-----|
| **`STRAT-001`–`014`** | [`MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md) v0.1 **DRAFT / UNVALIDATED**. No backtests. **No win rates.** Do not rank them. |
| **Dashboard numbers** | [`apps/web`](../../../apps/web/README.md) book, sentiment, levels, P/L, mock tabs (NIFTY IN-PROGRESS / BANKNIFTY ACHIEVED / SENSEX INVALIDATED) are **MOCK**. |
| **`CasPanel` bias** | Bound to mock `cas.byUnderlying`. Analyst JSON for 2026-09-01 is research-only SIDEWAYS, confidence 0.20, `realized_bias: null`. |
| **Nightly recon P/L** | [`NIGHTLY_2026-09-02.md`](../../02_phd_math/docs/handoffs/NIGHTLY_2026-09-02.md) is a **stub run** (zeros / EXPIRED fixtures) and **predates** the retune-gate schema. Not a track record. |
| **`RETUNE_PROPOSAL`** | Status `BACKTEST_REQUIRED` means **queue for 06**, not “params updated.” `backtest_results` must stay `null` until an engine exists. |
| **Sentiment 10m/15m/30m/1h** | Schema slots. **Not** measured rolling windows. |
| **GIFT Nifty / SGX / pre-open** | YAML VERIFY URLs + `--offline` fixtures. Not live quotes. |
| **Lot sizes / F&O close** | **VERIFY**. 15:30 vs 15:40 unknown. Do not hardcode. |
| **Spoken Supertrend 10,3 / EMA 9 / MACD×3** | Transcript `SOURCE_FACT` or `SOURCE_UNCERTAIN` — **not** HQ API fields. |
| **Missed-PE “24100 ce”** | `SOURCE_UNCERTAIN`. Do not invent a fill. |
| **English captions** | YouTube `tlang=en`, not LLM translation — still not a substitute for Hindi `SOURCE_FACT` timestamps. |
| **AGENT.md `[x]` vs this brief** | Prefer MASTER_REQUIREMENTS. A checked ticket can still be stub-scoped. |
| **PLAN.md phase table** | Reconciled 2026-09-01 to MASTER_REQUIREMENTS + [`docs/SDLC.md`](../../../docs/SDLC.md). If they disagree, **the score sheet wins**. |

---

## Do not “complete” in review

- Do not implement strategies, `/alerts/orders`, or TA in `packages/indicators`.
- Do not scrape disabled YouTube rows.
- Do not call `--live` desk_intel / chain.
- Do not auto-apply nightly hints to yaml or STRAT files.
- Do not publish a CAS or strategy win rate.
- Do not treat mock ACHIEVED as a backtest.

---

## Suggested pass order

1. [`docs/MASTER_REQUIREMENTS.md`](../../../docs/MASTER_REQUIREMENTS.md) — every row.  
2. [`AGENT.md`](../../../AGENT.md) golden rules + current phase.  
3. Tickets under `teams/00_orchestrator/docs/TASK_*.md` vs their artifacts.  
4. `packages/dhan-client` execution refuse; `packages/indicators` empty; `apps/web` customer vs `/desk`.  
5. `teams/03_phd_market/cas/` + `RETUNE_GATE.md` + one `STRAT-00x.md` header (`UNVALIDATED`).  
6. Write findings as gaps against the sheet. Label invented performance as **reject**.
