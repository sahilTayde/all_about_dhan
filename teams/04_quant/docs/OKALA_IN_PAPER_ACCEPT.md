# Okala India — PAPER notify note (04 / 06)

**Date:** 2026-09-07 (rev: simple path + news park)  
**Layer:** `HYPOTHESIS` (rules) / `VALIDATION` (cell WR research only)  
**Gate:** `FOUNDER_PAPER_ACCEPT` · PAPER · **NO_PROMOTE**

Founder accepts robust WR > 50% (n≥20) Okala-IN cells as a **starter** for PAPER buy CE/PE notifies. BN/SENSEX use the **same pattern rules** under `FOUNDER_STARTER_EXTEND`. Optimize later. Still UNVALIDATED for live.

- Detector: `backtest_engine.okala_in_paper` — `detect_okala_signal` (bars → CE/PE → premium levels)
- Wire: `live_signals.PaperSignalEngine`, `paper_evaluators` bind `okala_in_paper`
- Premium starter: Entry=LTP, Target=entry×1.25, Stop=entry×0.75 (`NEWS_VETO_ENABLED=false` soft-default)
- Plain English: [`HOW_SIGNALS_WORK.md`](../../00_orchestrator/docs/HOW_SIGNALS_WORK.md)
- Catalog: `MIX_CATALOG.md` §18b · recon `SIMPLE_SIGNAL_PATH_2026-09-07.md`
- Catalog `win_rate` stays **null**. Cell WR ≠ product claim.

**HANDOFF:** Accepted paper starter + news park; rejected live promote / RESEARCH_READY flip; UNKNOWN = next-quarter retune / swing stop map.
