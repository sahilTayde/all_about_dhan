# Team 06 — Backtesting

## Mission

Historical tests on realistic index-option contracts: costs, slippage, no look-ahead, OOS, walk-forward, regime and robustness. Reject strategies that only look good on in-sample return.

## In artifacts

- Versioned strategy specs from `teams/04_quant/` (`BACKTEST_PENDING`)
- Historical fields available via Dhan/exchange (Phase 1+)

## Out artifacts

- Engine and run reports under `teams/06_backtesting/`
- Status updates: `BACKTESTED`, `OOS_VALIDATED`, `WALK_FORWARD_VALIDATED`, `ROBUSTNESS_VALIDATED`, or `REJECTED`
- Handoff to 05_analysis and 09_review

## Owned paths

- `teams/06_backtesting/**`

## Do not own

- `packages/dhan-client/**` (may *call* it later; do not fork tokens here)
- `apps/web/**` (signals UI)
- Live order routing

## Current status

Engine **stub exists** at `packages/backtest` (`python -m backtest_engine --live`). **Not** OOS validated. Nothing promotes.

**2026-09-03 INDEX 5m** (`data/recon/BACKTEST_INDEX_5M_2026-09-03.json`): 425 bars each on NIFTY / BANKNIFTY / SENSEX. CE/PE/SKIP bar counts only. `win_rate` **null**, `option_pnl` **null**. FUTURES_PROXY on INDEX OHLC — not option fills. **Do not invent PF/DD.**

SCORE_SAMPLE vs ANALOG still **schema-only** ([`EVENT_MEMORY.md`](docs/EVENT_MEMORY.md)). 2026-09-03 is **SENSEX expiry** → ANALOG_MEMORY / `EXPIRY`, **not** a SCORE_SAMPLE promote.

Data API: **5/s** ([`RATE_LIMITS.md`](../../packages/dhan-client/docs/RATE_LIMITS.md)). Do not burst past that.

### Prerequisites (from desk intel — do not skip)

Paper **daily** + **pre-prod** learning comes from `packages/desk-intel` nightly recon **before** any live strategy rewrite.

| Need | Where |
|------|--------|
| Nightly JSON | `data/recon/YYYY-MM-DD.json` (gitignored). Schema keys: `desk_intel.nightly.RECON_JSON_KEYS` (`schema_version`, `job`, `day`, `counts`, `records`, `shadow_pnl_pts_sum`, `user_pnl_pts_sum`, `param_review_unvalidated`, `session_kind`, `session_flags`, `retune_proposal`, `production_params_written`, `cas_calls`, …). `cas_calls[]` is UNVALIDATED pattern notes — **BACKTEST_REQUIRED**, never a one-day promote. |
| PhD notes | `teams/02_phd_math/docs/handoffs/NIGHTLY_YYYY-MM-DD.md` — **REVIEW**, not auto-apply. Param review is **UNVALIDATED**. Gate: [`RETUNE_GATE.md`](docs/RETUNE_GATE.md). |
| Fixtures | `python -m desk_intel nightly --offline` (or `python -m jobs post-market --offline`). Chain/news fixtures; no live Dhan required. |
| Outcomes | ACHIEVED / STOPPED / INVALIDATED / EXPIRED / LOST / COMPLETED / SHADOW_CLOSED. Shadow P/L is paper, not a fill. |
| Session close | `jobs.post_market.session_close_ist: UNKNOWN` — VERIFY 15:30 vs 15:40. Do not hardcode lots or close in the engine. |

**TODO (engine, later):** costs, slippage, no look-ahead, date-stamped lots, option fills; ingest nightly JSON as a paper path, not as live alpha. Do not declare production from one recon file or this INDEX 5m stub. **Retune gate:** [`docs/RETUNE_GATE.md`](docs/RETUNE_GATE.md) — tag `NEWS_DAY`/`EXPIRY`/`NORMAL`; backtest OOS + `NORMAL` only; promote on robust metrics vs current or a documented glitch fix. Default: keep current strategy. **Event memory:** [`docs/EVENT_MEMORY.md`](docs/EVENT_MEMORY.md) — SCORE_SAMPLE = NORMAL (no circuit/gap); ANALOG_MEMORY stores outliers anyway; analog path fields **null**; no invented metrics. Tickets: [`TASK_PRE_POST_MARKET_JOBS.md`](../00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md), [`TASK_RETUNE_GATE.md`](../00_orchestrator/docs/TASK_RETUNE_GATE.md).

## As of now (2026-09-03) / your prerequisite

YouTube **45** verified + **45** English. `config/workspace.yaml`. Dhan **dry-run, no orders**. Engine **stub exists** (`packages/backtest`) — **not** OOS. INDEX 5m 425 bars × 3 underlyings; CE/PE/SKIP counts; `win_rate`/`option_pnl` **null**. SENSEX **expiry** day. SCORE_SAMPLE vs ANALOG **schema-only**. Nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. STRATs **UNVALIDATED**. Still **not** `RESEARCH_READY_FOR_PROGRAMMING`.
