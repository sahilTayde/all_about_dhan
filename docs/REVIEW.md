# docs/REVIEW.md — five-pass + red-team gates

No strategy is coded, paper-traded, or shown in the UI until review passes. Gate label: **`RESEARCH_READY_FOR_PROGRAMMING`**.

Owned by team **09_review**. Source checklist: Codex plan §§68–69 in [`teams/01_research/youtube/PLAN.md`](../teams/01_research/youtube/PLAN.md).

---

## Five-pass review

Perform **five separate** passes before publishing a research packet or coding a strategy.

### PASS 1 — Source integrity

- Correct channel (`@DhanHQ` only)
- Correct video / playlist
- Transcript exists and was not invented
- Timestamp and URL accuracy

### PASS 2 — Technical accuracy

- Indicator mathematics
- Terminology
- Options concepts (Greeks, IV, OI, CE/PE)
- API concepts vs current DhanHQ docs

### PASS 3 — Market accuracy

- Exchange (NSE vs BSE)
- Instrument (index vs futures vs options)
- Expiry, lot size (never assume current lots historically)
- Strike rules, trading hours
- SENSEX / BSE special handling

### PASS 4 — Quant accuracy

- Backtest methodology
- Look-ahead, leakage, overfitting
- Costs, slippage, bid/ask, fill assumptions
- Out-of-sample, walk-forward, robustness
- Statistical validity (not headline return)

### PASS 5 — Red-team

Try to **disprove** the conclusions. Use the checklist below.

---

## Red-team checklist

If any answer is **yes** (meaning a failure): `RESEARCH STATUS = FAILED REVIEW`.

1. Did we skip or invent a transcript?
2. Did we invent any Dhan recommendation?
3. Did we misinterpret a number?
4. Did we use a stock-only concept for options?
5. Did we confuse underlying data with option data?
6. Did we use future information?
7. Did we use current lot size historically?
8. Did we use unavailable historical option data?
9. Did we optimize against the test set?
10. Did we ignore transaction costs?
11. Did we ignore bid/ask?
12. Did we assume fills?
13. Did we confuse correlation with causation?
14. Did we overfit indicators?
15. Did we pick the winner by highest backtest return?
16. Did we ignore losing regimes?
17. Did we ignore liquidity?
18. Did we use another YouTube channel?
19. Did we treat education as expert endorsement of a live strategy?
20. Can another researcher **not** reproduce the result?

---

## After a pass

- Fail → hand back with [`HANDOFF.md`](HANDOFF.md); status `REJECTED` or `FAILED REVIEW`.
- Pass → `RESEARCH_READY_FOR_PROGRAMMING` to team 07_coding. Still no live orders.
