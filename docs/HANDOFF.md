# docs/HANDOFF.md — how work moves between teams

Copy this template into the **receiving** team's `HANDOFF.md` (newest first). Do not dump the whole repo; link artifacts.

---

## Template

```text
From:     teams/NN_name
To:       teams/NN_name
Date:
Status:   (use labels from docs/RESEARCH.md)
Gate:     (e.g. SOURCE_FACT ready | VALIDATION ready | RESEARCH_READY_FOR_PROGRAMMING)

Summary:

Artifacts (paths only):
- 

What the next team must do:

What the next team must not do:

Blockers / UNKNOWN / DATA_INSUFFICIENT:

Review:   (n/a | five-pass pending | FAILED REVIEW | passed)
```

---

## Usual flow

```text
00_orchestrator
  → 01_research          (catalog, transcripts, SOURCE_FACT)
  → 02_phd_math
  → 03_phd_market        (VALIDATION; math and market can run in parallel)
  → 04_quant             (HYPOTHESIS + strategy spec)
  → 06_backtesting
  → 05_analysis          (scorecards; can overlap with backtest outputs)
  → 09_review            (five-pass + red-team)
  → 07_coding            (only after RESEARCH_READY_FOR_PROGRAMMING)
  → 08_testing
  → apps/ + packages/
```

Never send 01_research output straight to 07_coding.

---

## Artifact location rules

| Kind | Lives in |
|------|----------|
| Transcripts, catalogs | `data/youtube/`, `data/transcripts/` (gitignored payloads) |
| Research notes | owning team's `docs/` |
| Strategy specs | `teams/04_quant/` |
| Backtest reports | `teams/06_backtesting/` |
| Review verdicts | `teams/09_review/` |
| Product code | `apps/`, `packages/` — not under `teams/01_research` |
