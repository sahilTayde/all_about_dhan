# Handoff log — CAS analyst (03)

## As of now (2026-09-08) — CAS-* off PAPER candidate scoring

```text
From:     teams/03_phd_market/cas
To:       00 / 04 / 09
Date:     2026-09-08
Status:   DRAFT / UNVALIDATED
Gate:     NOT RESEARCH_READY_FOR_PROGRAMMING

Accepted: CAS-001–005 stay UNVALIDATED; no DHAN-DERIVED CAS recipe;
  not in PAPER working-score list.
Rejected: CONFIRMED from CAS; STRAT-015+.
```

Newest first.

---

## As of now (2026-09-01)

CAS = **Closing Auction Session**. YouTube **45** verified + **45** English. `config/workspace.yaml`. Dhan **dry-run, no orders**. Customer `/`: ticket + **IN-PROGRESS** + **CasPanel**; book P/L **MOCK**. Internal **`/desk`**. Chain **3m**. Nightly `cas_calls[]` retune **BACKTEST_REQUIRED**. Daily book **UNVALIDATED** / `DATA_INSUFFICIENT`. STRATs **UNVALIDATED**. Not `RESEARCH_READY_FOR_PROGRAMMING`.

Newest first.

---

```text
From:     teams/03_phd_market/cas
To:       00_orchestrator / 04_quant / 05_analysis / 06_backtesting / 09_review
Date:     2026-09-03
Status:   DRAFT / UNVALIDATED — CAS-* hypotheses defined
Gate:     NOT RESEARCH_READY_FOR_PROGRAMMING

Summary:
Defined CAS-001 CLOSE_BIAS, CAS-002 FNO_TAIL, CAS-003 NO_NEW_OPT_DURING_AUCTION,
CAS-004 EXPIRY_SETTLEMENT_MARK, CAS-005 PRE_OPEN_GAP. Namespace CAS-* not
STRAT-015+. English Dhan transcripts do not name Closing Auction Session —
DATA_INSUFFICIENT for DHAN-DERIVED CAS STRATs. Gokul 009 stays its own STRAT.
SENSEX = BSE auction. No live IEP. Customer WATCH only, never CONFIRMED.

Artifacts:
- teams/03_phd_market/cas/CAS_STRATEGIES.md

What the next team must do:
- 05/00: CAS bias = WATCH reason. 06: fixtures only; do not invent settlement math.
- 04: optional PROJECT-DERIVED cas_filters; do not add STRAT-015+.

What the next team must not do:
- Code a CAS option-buy recipe as Dhan-taught. Collapse PRE_OPEN into CAS.
- Freeze 15:40 without circular. Invent lots, IEP, fills, or win rates.

Blockers / UNKNOWN / DATA_INSUFFICIENT:
- No live IEP/imbalance/indicative index in workspace.
- 74467 F&O 15:40 PDF not stored.

Review: notes only
```

---

```text
From:     teams/03_phd_market/cas
To:       00_orchestrator · 05_analysis (nightly) · 07_coding (CasPanel) · 04_quant (read-only)
Date:     2026-09-01
Status:   RESEARCH started · daily call DATA_INSUFFICIENT · UNVALIDATED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Summary:
Official CAS on nseindia.com is Closing Auction Session (Phase 1 = F&O cash
stocks), live 3 Aug 2026, 15:15–15:35 IST, equilibrium close, ±3% band.
SENSEX = same idea on BSE (notice 20260610-41). Pre-open, periodic call
auction, and “cash vs F&O” are tracked as other tags — not frozen as CAS.
No live indicative-index feed in-repo. First daily bias is SIDEWAYS /
DATA_INSUFFICIENT, not a fake tape.

Artifacts:
- teams/03_phd_market/cas/RESEARCH.md
- teams/03_phd_market/cas/METHODOLOGY.md
- teams/03_phd_market/cas/notes/2026-09-01.md
- teams/03_phd_market/cas/calls/2026-09-01.json
- teams/00_orchestrator/docs/TASK_CAS_ANALYST.md
- apps/web/src/components/CasPanel.jsx
- nightly key cas_calls[] (packages/desk-intel nightly.py)

What the next team must do:
- 05: keep cas_calls in the same recon book; never retune from it.
- 07: keep CasPanel on the customer desk (no indicator list).
- 06: if a CAS pattern is proposed, backtest OOS — do not invent metrics.
- 03: file official circular PDFs when downloaded; refresh RESEARCH.md.

What the next team must not do:
- Treat PCA illiquid auctions as index CAS.
- Hardcode 15:30 as F&O close.
- Publish a win rate.

Blockers: no Dhan/NSE live CAS book in this workspace; timings HTML page stale.

Review: n/a
```
