# TV-EP paper session tuner (NO_PROMOTE)

**Team:** 06 backtesting (CLI) · 05 dual-tape dealer (`PREMIUM_DIVERGENCE`) · 04 MIX ids · 00 routing  
**Status:** `HYPOTHESIS` / coded / **UNVALIDATED**  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** refused. `ExecutionClient` stays SafeMode. Zero LLM on this path.  
**IDs:** `MIX-TV-EP-*` KEEP_ALL. Customer default `MIX-DEFAULT-BUY` **untouched** in production. No `STRAT-015+`.

Retune law: [`RETUNE_GATE.md`](RETUNE_GATE.md). Factory: [`TV_EP_BACKTEST_FACTORY.md`](TV_EP_BACKTEST_FACTORY.md). Dual-tape sibling: `python -m trading_agents_india dual-tape` (when that branch is present).

---

## What humans used to do (TV / Pine)

On TradingView a person sat the session, changed **Inputs**, hit **Replay** on the **same** 1m chart, and kept the combo that “looked green.” That is in-sample fiddling. It is **not** an OOS backtest. It is **not** a promote.

This CLI copies that *loop* in Python:

1. One MIX at a time (default shortlist `MIX-TV-EP-005`, `010`, `016`, `MIX-DEFAULT-BUY`).
2. Each 1m bar (cache, or clock-aligned INDEX+CE+PE when calendars differ) → `BUY_CE` / `BUY_PE` / `HOLD`.
3. Score vs the **next premium** close on that side (1% RT hypothesis haircut).
4. Append `mistake_note` when next-premium ≤ 0.
5. Try at most **2–3 param tweaks** from the adapter `input_schema` on **that same tape**.
6. Write `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` plus a **local** paper param file under `data/recon/`.

It does **not** write `config/workspace.yaml`, `teams/04_quant/docs/candidates/`, or `MIX-DEFAULT-BUY` production knobs.

---

## Dual-tape (sibling)

If `judge_tick` says `PREMIUM_DIVERGENCE` (or `allow_new_paper_ce_pe=False`), **do not open a new paper ticket**. MIX lean that wants CE while dual-tape confirms PE is also blocked. Fallback rule (if `desk_divergence` is not importable): PE leading a CE lean, or both premiums rising. No LLM.

---

## Why one green day is not a promote

- Same-session replay **is** the sample that suggested the tweak. RETUNE_GATE requires **OOS + `NORMAL`**.
- INDEX points ≠ option P/L. Clock-aligned INDEX vs a later ATM CE/PE day is **not** the same trading day.
- After-cost 1% RT is **HYPOTHESIS**, statutory UNKNOWN.
- Paper ledger rows stay `NO_PROMOTE`.

---

## CLI

```bash
PYTHONPATH=packages/backtest/src:packages/dhan-client/src:packages/trading_agents_india/src \
  python -m backtest_engine tv-ep-paper-tune --underlying NIFTY --max-ticks 90 --max-tweaks 3
```

Alias: `python -m trading_agents_india paper-tune`.

Stop if no INDEX+CE+PE tape. Do not loop forever. Do not start npm / paper market-hours unless the founder asks.

Artifacts (gitignored `data/recon/`):

- `RETUNE_PROPOSAL_TV_EP_PAPER_<MIX>_<day>.json`
- `tv_ep_paper_params_<MIX>_<day>.json` (local paper only)
- `tv_ep_paper_tune_<day>.json`
- leaderboard JSON `paper_sessions[]` — still `NO_PROMOTE`

---

## 09:15 IST (next open)

1. Confirm `paper_ops_STOPPED.flag` — do **not** restart the old 30s LLM gather unless asked.
2. Optional sibling dual-tape poll if the founder started it.
3. `python -m backtest_engine tv-ep-paper-tune --max-ticks 90`
4. Counsel stays **async / off**. Fast path has **zero blocking LLM**.
5. Still **no live Super Orders**. Still **NO_PROMOTE**.
