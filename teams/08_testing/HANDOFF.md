# Handoff log — Team 08 Testing

## As of now (2026-09-03)

Pytest: `packages/backtest/tests/test_algos.py`, `packages/dhan-client/tests/test_futidx.py`. No live-order tests that pass a place_order. Not `RESEARCH_READY_FOR_PROGRAMMING`.

Copy the template from [`docs/HANDOFF.md`](../../docs/HANDOFF.md). Newest first.

---

```text
From:     teams/00_orchestrator
To:       teams/08_testing
Date:     2026-09-01
Status:   INFORMED / full pytest TODO
Gate:     smoke exists; jobs CLI dry-run OK

Summary:
Cheap smoke: packages/desk-intel/tests/test_lifecycle_smoke.py.
Jobs CLI: python -m desk_intel nightly --offline / python -m jobs post-market.
Full paper-trade pytest is TODO. Skip must still get SHADOW_CLOSED paper MTM.

Artifacts:
- packages/desk-intel/tests/test_lifecycle_smoke.py
- teams/08_testing/README.md

What the next team must do:
- Later: still_valid overnight, took-trade lots/spot/pnl, skip→shadow, UI colors.
- Do not require live Dhan.

What the next team must not do:
- Invent live order tests. Implement apps/ features here.

Blockers: apps/api still mock; UI stillValid not fully wired.

Review: n/a
```

---

```text
From:     teams/00_orchestrator
To:       teams/08_testing
Date:     2026-09-01
Status:   INFORMED / tests still stub
Gate:     Automate signal-state transitions; jobs CLI smoke later

Summary:
Paper UI added lifecycle outcomes. Prerequisite: fixture the chain
WATCH→EARLY→CONFIRMED/VETOED→INVALIDATED/ACHIEVED (and STOPPED/LOST/EXPIRED).
Skip = shadow paper still visible. When 07 adds jobs CLI, smoke dry-run only.

Artifacts:
- apps/web/public/mock/signal.json
- apps/web/src/components/StagedSignal.jsx

What the next team must do:
- Cover outcome colors vs EARLY orange; lunch-return must not stay CONFIRMED.

What the next team must not do:
- Hit live Dhan. Invent fills. Implement apps/ features here.

Blockers: jobs CLI not built.

Review: n/a
```

---

_(no older handoffs)_
