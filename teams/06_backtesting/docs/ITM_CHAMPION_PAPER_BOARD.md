# ITM champions — paper leaderboard (NO_PROMOTE)

**Status:** PAPER watch ready · **not** customer default · **live orders refused**  
**Updated:** 2026-09-13  

## Remembered strategies (board catalog)

| ID | Plain English | Why kept |
|----|---------------|----------|
| `MIX-CHAMP-EMA-ST-5M` | 5m EMA9×EMA21 + Supertrend(10,3) | Lab strike-sweep winner (~41% WR aggregate) |
| `MIX-CHAMP-EMA-ST-VWAP-5M` | Same + price above session VWAP | Tuesday-ready VWAP gate |
| `MIX-CHAMP-SMA-CROSS-5M` | 5m SMA10×50 + 15%/30% SL/TP | Runner-up; most strikes green |
| `MIX-CHAMP-VWAP-RSI-5M` | Pine VWAP + RSI + EMA3×WMA21 | Founder path; needs live VWAP |
| `MIX-CHAMP-EMA-VWAP-5M` | EMA9×21 gated by session VWAP | Simple live VWAP comparator |
| `MIX-CHAMP-BB-5M` | BB(20,2.5) mean-revert | High WR challenger; lost on full strike sweep |
| `MIX-CHAMP-FV-V1-10M-BB15` | Flawless v1 · 10m BB(20,×1.5) RSI 42/70 | Top Flawless grid cell on premiums |
| `MIX-CHAMP-FV-V1-5M-BB20` | Flawless v1 · 5m BB(20,×2.0) | Best 5m Flawless cell |
| `MIX-CHAMP-FV-V1-10M-BB20` | Flawless v1 · 10m BB(20,×2.0) | Wider-band 10m companion |
| `MIX-CHAMP-FV-V1-1M-RSI60` | Flawless v1 · 1m RSI exit 60 | Only green 1m Flawless cell |
| `MIX-CHAMP-FV-V1-15M-BB17` | Flawless v1 · 15m BB(17,×1) | Best 15m Flawless cell |

**Not boarded:** Flawless Pine **v2/v3** defaults (high win rate, negative ₹ — SL≫TP). Full grid: `data/recon/itm_flawless_victory.json`.

Code: [`itm_champions.py`](../../../packages/backtest/src/backtest_engine/itm_champions.py)  
Runner: `python -m backtest_engine.run_itm_champions`  
Board JSON: `data/recon/itm_champion_leaderboard.json`  
Desk UI: `/desk` → **ITM champion leaderboard**  
API: `GET /paper/backtests/itm-champions`

## VWAP assume (offline) vs live Tuesday

| Mode | Behavior |
|------|----------|
| Offline / sparse volume | IST **session** VWAP; zero-volume bars use **equal-weight** (PROJECT assume) |
| Live market hours | Same code path; OPTIDX **volume > 0** fills true session VWAP |

VWAP day reset is **Asia/Kolkata session date** (not UTC midnight).

## Leaderboard metrics

Ranked by **after-cost P/L (1 lot)**:

- wins / losses  
- **success %** (win rate)  
- current streak (`W`/`L` + length)  
- max win streak  
- gross vs after-cost ₹  

## Next action items (founder)

1. **Freeze** top recipe only after ≥1 live PAPER session on this board (evidence, not lab alone).  
2. **Walk-forward** same champions on another expiry / OOS week.  
3. Longer paper book discussion — still **NO_PROMOTE**, no live Super Orders.

## Hard rules

- No `STRAT-015+`. Champions stay `MIX-CHAMP-*`.  
- No auto Dhan orders / Super Orders.  
- Do not promote from this board to customer `/`.  
- 1m cross families from strike sweep **bled** — not on the Tuesday board.

## HANDOFF

| Accepted | Rejected | UNKNOWN |
|----------|----------|---------|
| Champion registry + desk leaderboard + IST VWAP assume | Live auto-trade Tuesday | Whether live VWAP gate beats lab EMA×ST alone |
| Prefer ITM PE near spot for first paper watch | Claiming OOS edge from Aug–Sep sweep | Brokerage/STT exact costs |
