# PAPER productionization tranche 1

**Status:** `PAPER_ONLY` / `UNVALIDATED` / `NO_PROMOTE`  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`; STRAT-001–014 remain unchanged.  
**Scope:** auditable signal, shadow-paper, customer-action, fee, and EOD
contracts around the existing sequential agent graph.

## Shipped safely

- Versioned typed contracts: `SignalRecord`, `PaperTrade`, `CustomerAction`,
  `FeeAssessment`, and `EODReconciliation`.
- SQLite append-only events with a stable SHA-256 event key and a JSONL mirror.
  Replaying a session is idempotent; restart does not duplicate events.
- Customer fee semantics: customer net is gross P/L less known buy/sell broker
  charges, known exchange/statutory components, and configured service charges.
  Service charge per lot is configurable and initially unset. Unresolved
  service/statutory values remain `PENDING` and are never treated as zero.
  The separate company API owns the 5% commission; this repository records
  `external_commission_owner` for integration but does not calculate or charge
  that commission. The legacy commission output remains null. Gross costs,
  commission ownership, and customer net are separate fields.
- HOLD/VETOED/SKIPPED signals receive a separately marked shadow-paper outcome.
  Shadow outcomes do not create customer commission events.
- Provenance, layer, freshness status, and data-gap fields are carried by
  signal/trade records. Existing fixture/live-data refusal behavior remains.
- Global `PAPER` pause and unknown-calendar pause hooks force deterministic
  HOLD/veto behavior in the market-hours runner.

## Deliberate limits

No real fills, live orders, external OpenAI/Grok calls, vector embeddings,
exchange calendar claims, or validated profitability are added. Option contract
identity, lot size, statutory fees, and freshness thresholds remain
`UNKNOWN`/`DATA_INSUFFICIENT` until authoritative adapters and fixtures exist.
The customer UI is not rewired in this tranche.

## Coalition handoff

**Accepted:** 00 orchestrator accepts the ledger boundary, deterministic
clock/pause vetoes, and the existing sequential graph. 01 research provenance,
02 math cost validation, 03 market calendar/contract validation, 04 quant
signal staging, 05 desk-intel snapshots, 06 backtest cost/reconciliation, and
09 review remain the authoritative review surfaces:
[`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md),
[`DHAN_INDICATOR_API_MAP.md`](../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md),
[`CHAIN_METRICS.md`](../../03_phd_market/docs/CHAIN_METRICS.md),
[`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md),
[`DESK_INTELLIGENCE.md`](../../05_analysis/docs/DESK_INTELLIGENCE.md),
[`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md), and
[`FIVE_PASS_HONEST_2026-09-06.md`](../../09_review/docs/FIVE_PASS_HONEST_2026-09-06.md).

**Rejected:** live execution, auto-promotion, silent zero fees, and any change
to STRAT-001–014.

**UNKNOWN / DATA_INSUFFICIENT:** authoritative statutory fee schedule, exchange
holiday/calendar adapter, real OPTIDX fills, customer-reported reconciliation
quality, and NORMAL-session performance sample.

**Grok:** `PENDING_INTEGRATION`; no external Grok call or product dependency in
this tranche. **Astra:** advisory review only, **NOT a product gate**; the
existing 09 five-pass and 06 OOS+NORMAL gates remain binding.

## Next safe tranche

Implemented in `packages/trading_agents_india` (candidate-audit tranche; still
`PAPER_ONLY`):

- `paper_fixture.PaperFixtureAdapter` records `TOOK`, `SKIPPED`, `UNKNOWN`, and
  append-only `CORRECTED` declarations by signal ID; declarations are not fills.
- `PaperLedger.replay_jsonl()` replays the JSONL mirror into a reopened SQLite
  ledger idempotently without duplicating mirror rows.
- `PaperLedger.export_eod()` emits deterministic counts, action counts, fee
  status/unresolved fields, available gross/cost/commission/net totals,
  external commission ownership metadata, duplicate/mirror indicators, and
  explicit `PAPER` / `NO_PROMOTE` metadata.
- Focused tests cover adapter actions, SQLite restart plus JSONL replay, and
  EOD fee totals. No live endpoint, order path, promotion, or UI wiring was
  added.
- `candidate_audit.py` emits one append-only `CANDIDATE_OBSERVATION` for every
  existing `STRAT-001`–`STRAT-014` and current PAPER `MIX-*` row per
  underlying/tick. The aggregate default mix is the only currently bound
  evaluator; all other rows are retained as `DATA_INSUFFICIENT` rather than
  silently skipped. Raw and final leans, `VETOED`/`STALE`/`HOLD` outcomes,
  provenance/freshness, vetoes, bounded data/consensus confidence components,
  and `execution=refused` are recorded.
- `agent_rag eod-recon` now reads the candidate audit mirror and reports row
  counts/outcomes only. It does not fabricate marks, P/L, or promotion evidence;
  the retune status remains `BACKTEST_REQUIRED`.

Do not wire live orders or promote until the existing 06/09 gates pass.
