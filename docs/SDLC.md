# docs/SDLC.md — phases 0–7

Enforced by [`AGENT.md`](../AGENT.md) and root [`PLAN.md`](../PLAN.md). **Never skip a phase** to “just code the strategy.”

**Morning score:** [`docs/MASTER_REQUIREMENTS.md`](MASTER_REQUIREMENTS.md). Reviewer brief: [`teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md`](../teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md).

**Honest phase:** **0–2 overlap**, with a **Phase 6 mock** and **Phase 1 skeleton**. Not a finished paper gate. **Not** `RESEARCH_READY_FOR_PROGRAMMING`. No coded strategies. No live orders.

---

## Phase 0 — Research infra

**Mostly done.** Repo tree, master docs, Cursor routing, YouTube catalog (`@DhanHQ`, 2,034), transcript collector, English companions (45 `ENGLISH_VERIFIED`). Customer config [`config/workspace.yaml`](../config/workspace.yaml).

Out: structure, `data/youtube/` + `data/transcripts/` payloads.  
**Still open:** catalog `STOCK_ONLY` **9** (no English transcript). OPTIONS_INDEX + remaining verified-EN equity extract **done** 2026-09-03. `.git` absent.  
**Not a claim:** catalog re-fetch (still 2026-08-31).

Ticket: [`TASK_YOUTUBE_TRANSCRIPT_RETRY.md`](../teams/00_orchestrator/docs/TASK_YOUTUBE_TRANSCRIPT_RETRY.md) **DONE**.

---

## Phase 1 — Dhan data

**Skeleton only.** Token-shaped client in `packages/dhan-client`. FastAPI dry-run in `apps/api`. `ExecutionClient` **refuses** all order methods. Option-chain poller exists in `packages/desk-intel` (fixtures if `DHAN_*` empty).

Out required for “done”: reproducible **live** market data access (instrument master, lots from exchange files).  
**TODO / BLOCKED:** live token validation (§10 of MASTER_REQUIREMENTS). Lots and F&O close 15:30 vs 15:40 **VERIFY**. SENSEX/BSE scrips in yaml are **VERIFY FROM instrument master**.

Still no live orders.

---

## Phase 2 — Knowledge corpus

**DRAFT / PARTIAL.** Three-layer records started (`SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`). Official Dhan indicator catalog **done** (API names vs chart-only; **no Supertrend series API**). Transcript indicator KB still stub. 14 STRAT candidates **UNVALIDATED**.

Out required for “done”: audited research docs with status labels from [`RESEARCH.md`](RESEARCH.md).  
**Not done:** full 45-video SOURCE_FACT; five-pass review; `RESEARCH_READY_FOR_PROGRAMMING`.

CAS research packet (Closing Auction Session) lives under `teams/03_phd_market/cas/` — **PARTIAL**, `UNVALIDATED`, no win rates.

---

## Phase 3 — Backtest engine

**Not started** (stubs only). Historical option contracts, costs, slippage, no look-ahead. Walk-forward, regime, robustness. Owned by `teams/06_backtesting`.

**Retune gate (docs + nightly stub — 2026-09-01):** [`RETUNE_GATE.md`](../teams/06_backtesting/docs/RETUNE_GATE.md). Nightly recon **must not** overwrite the book. Tag `NEWS_DAY` / `EXPIRY` / `NORMAL`. Emit `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`. Promote only if more profitable **OOS on NORMAL days** (expectancy / PF / DD) **or** a documented glitch fix that backtests clean. Default: **keep current strategy**. Empty engine ⇒ **nothing promotes**. Do not invent results.

Out required: engine + reports. Ranking is risk-adjusted, not headline return.

---

## Phase 4 — Strategies

**Specs only (v0.1 DRAFT).** Quant hypotheses in `teams/04_quant` (`STRAT-001`–`014`). NIFTY / BANKNIFTY / SENSEX index options CE/PE buy first. Stock and swing/positional stay out.

Staged-signal **spec** (WATCH → EARLY → CONFIRMED → IN-PROGRESS → outcomes): [`SIGNAL_STAGING.md`](../teams/04_quant/docs/SIGNAL_STAGING.md) — `UNVALIDATED` / `WAITING_FOR_EDIT`. **Not implemented** as live math.

Out required: versioned specs **after** validation. **Not** coded in `apps/` or `packages/`.

---

## Phase 5 — Validation + review

**Notes only.** Independent checks started (`VALIDATION_MATH.md`, `VALIDATION_MARKET.md`). Scorecards not a pass. Five-pass + red-team (`teams/09_review`) **not** passed. Gate: **`RESEARCH_READY_FOR_PROGRAMMING`** — **unset**.

---

## Phase 6 — Paper UI

**Mock exists; paper gate not passed.** Thin Vite+React desk in `apps/web`: underlying, BUY CE/PE, strike/entry/stop/target, (i) legend, mock book, mock sentiment windows, CasPanel, “Did you take this trade?”, shadow paper. Internal `/desk` holds indicator soup. FastAPI still mock JSON.

This is **not** a live strategy, not Dhan in the browser, not Phase 7. Book P/L is **MOCK**. See [`apps/web/README.md`](../apps/web/README.md). **Do not restart npm until asked.**

Desk-intel PRE/POST jobs + paper/shadow ledger: **dry-run stubs**. Quality bar (up to 30% capital penalty) is a **product requirement**, not a measured backtest.

---

## Phase 7 — Production

**Not started.** Live signals (and only later, if ever, live orders) after paper gate, audit trail, risk override. AI must never guarantee returns. Conditional Trigger `/alerts/orders` stays **off**.

---

## Gate reminder

```text
Research → Independent validation → Strategy spec → Backtest → Review → Paper UI → Live
```

Overlap is allowed for **infra** (collector, SafeMode client, mock UI, recon stubs). Overlap is **not** a license to skip review or to treat mocks as performance.
