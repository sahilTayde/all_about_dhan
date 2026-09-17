# BACKTEST — desk ₹70k split + dual wr (PAPER / NO_PROMOTE)

**As of IST:** 2026-09-17 ~08:52. Gate **not** `RESEARCH_READY_FOR_PROGRAMMING`.

## What ran

- Unit: `packages/desk-ml/tests/test_paper_scalp.py` + dual-tape + greeks (34 passed in that slice).
- Smoke: `python -m desk_ml paper-scalp --replay --source dual-tape --live-session --session-date 2026-09-17 --no-write`
- Smoke: same for `2026-09-16 --max-closes 5` (not today’s tape).

## 17 Sep IST (today cash, PRE-MARKET)

| Fact | Result |
|------|--------|
| INDEX 1m today | **DATA_INSUFFICIENT** (warehouse 0 bars; dual-tape 0 triples) |
| UP-TREND claim | **not-uptrend / DI** — no 1m path. Dhan chain `last_price` NIFTY **23217.6** is a single POST `/optionchain` spot, not a TREND classifier |
| Chain | Live Dhan POST `/optionchain`: 236 strikes parsed by `parse_oc` |
| Greeks | `implied_volatility` on 236; delta/theta on 96. First-strike `greeks.{delta,theta,gamma,vega}` keys present. Not invented |
| Volume | Field present; **0** positive volume on this pre-open parse — do not invent pickup |
| Desk capital | ₹70,000. MIX-ML-GREEKS **₹0** (no greeks on empty tape). Seven tradable books **₹10,000** each. Not 10k×8=80k |
| wr gross / net | null (0 filled) |
| `production_params_written` | false |

16 Sep max-5: greeks present on jsonl → equal **₹8750 × 8**. wr 0/0 on the truncated walk. **Not** today’s live tape.

## Rejected

Live orders. Super Orders. MIX-DEFAULT-BUY production write. STRAT-015+. Treating 16 Sep replay as 17 Sep trend.
