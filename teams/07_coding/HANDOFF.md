# Handoff log — Team 07 Coding

## As of now (2026-09-06) — customer `/` paper dashboard (Astra UX)

Single-ticket hero + index chart (`lightweight-charts`) + confidence rail + paper book. MOCK/PAPER only. Orders refused. `npm install` once for chart dep — do not restart npm until asked.

Newest first.

---

```text
From:     teams/07_coding
To:       00 / 05 / 09
Date:     2026-09-06
Status:   customer paper dashboard MOCK / NOT RESEARCH_READY
Gate:     No live orders. Do not restart npm until asked.

Summary:
Astra+desk APPROVE_WITH_GUARDRAILS. Honesty labels on `/`.
Index chart (index units only). Confidence (i) = HYPOTHESIS detail.
Paper book + ledger field list for nightly review.
Sentiment/CAS collapsed below ticket.

Artifacts:
- teams/07_coding/docs/ASTRA_DASHBOARD_REVIEW.md
- apps/web/src/components/IndexChart.jsx
- apps/web/src/components/{SignalCard,ConfidenceBox,TodaysBook}.jsx
- apps/web/public/mock/{signal,paper_agents}.json
- apps/web package: lightweight-charts@4.2.1

Ledger fields (nightly later):
signal_id, trade_id, raw_status, displayed_status, spot, entry/SL/target premium,
lots=1 PAPER, realized_points, outcome, confidence_score, is_mock, execution_mode=PAPER
```

---

```text
From:     teams/07_coding
To:       00 / 05 / 09
Date:     2026-09-06
Status:   paper ticket UI / NOT RESEARCH_READY
Gate:     No live orders. Do not restart npm.

Summary:
SignalCard + ConfidenceBox. App merges live ticket/confidence.
ticket_confidence.py builds levels + agreement score.

Artifacts:
- apps/web/src/components/SignalCard.jsx
- apps/web/src/components/ConfidenceBox.jsx
- packages/backtest/src/backtest_engine/ticket_confidence.py
```

---

## As of now (2026-09-03) — paper signal WS

Customer `/` may overlay `/ws/signals` paper BUY CALL/PUT/HOLD. Browser never calls Dhan. **No live orders.** Do not restart npm until asked.

Copy the template from [`docs/HANDOFF.md`](../../docs/HANDOFF.md). Newest first.

---

```text
From:     teams/07_coding
To:       00 / 05 / 09
Date:     2026-09-03
Status:   paper /ws/signals / MOCK desk default / NOT RESEARCH_READY
Gate:     No live orders. Do not restart npm.

Summary:
API /ws/signals?live=1 fans Dhan index ticks through PaperSignalEngine.
apps/web subscribePaperSignals when VITE_API_URL is set. HOLD/CE/PE copy
only — no indicator soup. ExecutionClient still refuses.

Artifacts:
- apps/api/src/api/ws.py
- apps/web/src/lib/liveSignals.js

What the next team must not do:
- Call Dhan from the browser. Place orders. Restart npm unless asked.
```

---

```text
From:     teams/00_orchestrator
To:       teams/07_coding
Date:     2026-09-01
Status:   Customer / vs /desk + CasPanel mock / NOT RESEARCH_READY_FOR_PROGRAMMING
Gate:     No live Dhan. No strategy code. Do not restart npm.

Summary:
Customer desk is `/` (ticket, IN-PROGRESS, CasPanel, MOCK book P/L).
Internal `/desk` keeps indicator soup. Keep CasPanel imported on App.jsx.
Orders refused. STRATs UNVALIDATED.

Artifacts:
- apps/web/src/App.jsx
- apps/web/src/InternalDesk.jsx
- apps/web/src/components/CasPanel.jsx
- apps/web/README.md
- teams/07_coding/README.md

What the next team must do:
- Keep customer vs /desk split. Keep CasPanel on `/`.
- Keep Dhan tokens server-side.

What the next team must not do:
- Call live Dhan from the browser. Place orders. Code strategies.
- Restart npm unless the user asks.

Blockers: RESEARCH_READY_FOR_PROGRAMMING still closed.

Review: n/a
```

---

```text
From:     teams/00_orchestrator
To:       teams/07_coding
Date:     2026-09-01
Status:   Paper dashboard outcomes mock / jobs CLI dry-run
Gate:     No live Dhan. No strategy code.

Summary:
Dashboard now shows lifecycle outcomes (INVALIDATED not leftover CONFIRMED;
ACHIEVED; STOPPED/LOST; EXPIRED). Took Yes = local lots/spot/P-L. Skip =
shadow paper. GET /paper/signal shape includes lifecycle. Jobs/recon:
python -m desk_intel nightly --offline (dry-run only).

Artifacts:
- apps/web/src/components/StagedSignal.jsx
- apps/web/public/mock/signal.json
- apps/api/src/api/models.py

What the next team must do:
- Keep dashboard + jobs dry-run aligned. Keep Dhan tokens server-side.

What the next team must not do:
- Call live Dhan from the browser. Place orders. Code strategies.

Blockers: RESEARCH_READY_FOR_PROGRAMMING still closed.

Review: n/a
```

---

_(no older handoffs)_
