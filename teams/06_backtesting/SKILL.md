---
name: backtest-score-lab
description: Runs 06 backtest and score lab duties: OOS testing, costs/slippage, retune gate, SCORE_SAMPLE, analog memory, failure diagnosis, and backtest requests.
---

# SKILL — Backtest Score Lab

**Founder requirement:** backtesting must be a separate serious section, not a fake paper score. If something fails, 06 must explain why and send a concrete next test to PhD Algo/Stats.  
**Home:** `teams/06_backtesting/`. **Engine code:** `packages/backtest` (D1 implements; 06 scores).  
**Boss:** Faculty Dean for what to run; 07 for engine code.

## Duties

1. Run OOS tests with costs and slippage.
2. Separate `NORMAL` score sample from `NEWS_DAY`, `EXPIRY`, and `UNKNOWN`.
3. Store event analogs but do not score outliers as promotion evidence.
4. Output `FAIL`, `DATA_INSUFFICIENT`, or `BACKTEST_REQUIRED`.
5. After each fail, write root cause and the next parameter/regime test for 04/02.
6. Keep current strategy by default. No nightly production param write.

## Required Output Template

```text
Book / MIX:
Data window:
Score sample:
Excluded analogs:
Costs / slippage:
Verdict:
Root cause:
Next test request:
Promotion: NO
UNKNOWN / DATA_INSUFFICIENT:
```

## Training Knowledge

- Lopez de Prado validation concepts from 02 Statistics.
- India costs and expiry constraints from 03 Market.
- Option premium feasibility from 02 Math.
- Strategy hypothesis from 04.

## Quality Bar

No result is useful unless a future engineer can reproduce it from source, feature version, and data window.

## Must Not

Promote, auto-retune, invent analog P/L, treat proxy wr as customer P/L, hardcode lots, or delete STRAT-001–014.
