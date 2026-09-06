# BACKTEST_PAPER_AGENTS — 2026-09-06

**Team:** 06_backtesting (+ agent_rag rollup)
**Status:** `HYPOTHESIS` / **UNVALIDATED** / **not a promote**
**Gate:** `keep_current_strategy: true` · **not** `RESEARCH_READY_FOR_PROGRAMMING`

Artifact: `data/recon/BACKTEST_PAPER_AGENTS_2026-09-06.json`
Command: `python -m agent_rag paper-backtest --day 2026-09-06`

## Verdict

- status: **NO_PROMOTE**
- promote: **False**
- RETUNE_PROPOSAL: **BACKTEST_REQUIRED**

Reasons:

- Existing CF / club / SLTP / honest books remain FAIL or WEAK / UNVALIDATED
- SCORE_SAMPLE empty (EVENT_MEMORY / news calendar DATA_INSUFFICIENT)
- trading_agents_india is paper skeleton only
- KEEP_ALL — do not delete STRAT-001–014

## Sources rolled up

| Source | books | ratings | promote |
|--------|------:|---------|---------|
| `BACKTEST_HONEST_2026-09-06.json` | 78 | DATA_INSUFFICIENT:37, FAIL:40, WEAK:1 | false |
| `BACKTEST_SLTP_2026-09-06.json` | 4 | DATA_INSUFFICIENT:1, FAIL:3 | false |
| `BACKTEST_CF_FABIO_2026-09-06.json` | 3 | FAIL:2, WEAK:1 | false |
| `BACKTEST_CF_MARCO_MAYNE_2026-09-06.json` | 4 | FAIL:1, WEAK:3 | false |
| `BACKTEST_CF_MARCI_TORI_2026-09-06.json` | 4 | FAIL:4 | false |
| `BACKTEST_CF_TG_KANE_2026-09-06.json` | 4 | FAIL:3, WEAK:1 | false |
| `BACKTEST_CF_UMAR_FOREST_2026-09-06.json` | 4 | DATA_INSUFFICIENT:1, FAIL:2, WEAK:1 | false |
| `BACKTEST_CF_CARMINE_JADECAP_2026-09-06.json` | 6 | DATA_INSUFFICIENT:3, FAIL:2, WEAK:1 | false |
| `BACKTEST_CF_USMAN_BRANDO_2026-09-06.json` | 9 | DATA_INSUFFICIENT:6, FAIL:2, WEAK:1 | false |
| `BACKTEST_CF_ANDREA_OMOR_2026-09-06.json` | 8 | DATA_INSUFFICIENT:4, FAIL:3, WEAK:1 | false |
| `BACKTEST_CLUB_2026-09-03.json` | 34 | DATA_INSUFFICIENT:5, FAIL:28, WEAK:1 | false |

## trading_agents_india dry

- ok: `True`
- ticket leans: `[{"underlying": "NIFTY", "lean": "BUY_CE", "stage": "EARLY", "session_kind": "NORMAL", "risk_veto": false}, {"underlying": "BANKNIFTY", "lean": "HOLD", "stage": "WATCH", "session_kind": "NORMAL", "risk_veto": false}, {"underlying": "SENSEX", "lean": "HOLD", "stage": "VETOED", "session_kind": "NEWS_DAY", "risk_veto": true}]`
- LIVE orders: refused (package policy)

```text
HANDOFF
From: 06 / agent_rag
To:   00 / 09
Accepted: rollup of existing CF/club/sltp/honest JSON + agents dry;
  RETUNE_PROPOSAL BACKTEST_REQUIRED; KEEP_ALL; no promote.
Rejected: promote on thin samples; invent win rates; auto-retune;
  live orders; rewrite trading_agents_india pipeline.
UNKNOWN: SCORE_SAMPLE (empty calendar); option premium path;
  statutory costs.
```
