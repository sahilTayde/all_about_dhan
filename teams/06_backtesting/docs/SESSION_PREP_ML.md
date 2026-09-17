# SESSION_PREP_ML — paper start 09:50 IST (cash open 09:15 + 35m)

**Team:** 06_backtesting (runbook) · 07 `packages/desk-ml` · 05 dual-tape  
**Date:** 2026-09-15 (IST)  
**Status:** `HYPOTHESIS` / **NO_PROMOTE** / `production_params_written: false`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** refused. Do **not** enable `ExecutionClient`. No Super Order.

Education ≠ advice. Cluster / OU numbers are cache counts, not a win rate.

This is how to start **paper gather + overlay score**. Dual-tape may poll from the shell; **NEW paper tickets arm only at 09:50 IST**. It is **not** a promote. Customer default stays `MIX-DEFAULT-BUY`. KEEP_ALL STRAT-001–014.

---

## Now (what is true)

| Piece | State |
|-------|--------|
| Dual-tape | `python -m trading_agents_india dual-tape` — INDEX LTP/1m + ATM CE/PE. No LLM. No orders. |
| ML-001 | KMeans k=4 + IsolationForest. Fit on warehouse `ohlc_bars`/`bars_1m` ∪ `premium_tape`. Seed **14**. Embargo last **5** 1m rows from fit (AFML analog, **not** CPCV / **not** OOS). |
| ML-002 | OU on residual + VWMA windows **40 / 60 / 90** only (max 3 tweaks). FOLLOW-GAP HOLD. SENSEX OU may be `DATA_INSUFFICIENT` / not mean-reverting on the thin ATM book. |
| Score CLI | `python -m desk_ml score --underlying NIFTY --source dual-tape` after two ticks with all three LTPs. |
| Live Super Order | **off** |

**FOLLOW-GAP:** index moved and ATM CE/PE did **not** confirm → overlay **HOLD**. Do not open a new paper CE/PE. Dealer note stays deterministic (`desk_divergence`). ML overlay may not override a hard stop.

---

## 09:15 poll / 09:50 first NEW ticket (laptop)

Do **not** restart npm / Vite. Do **not** start the old LLM `market-hours` loop (`paper_ops_STOPPED.flag` stays). Dual-tape only honours `paper_dual_tape_STOPPED.flag`.

```bash
cd /path/to/all_about_dhan

# Optional: cache inventory (no Dhan HTTP)
python -m desk_ml inventory --calendar-days 21

# Fit from warehouse + premium_tape if models missing under data/recon/ml/
python -m desk_ml fit --underlying NIFTY --seed 14 --embargo-bars 5
python -m desk_ml fit --underlying SENSEX --seed 14 --embargo-bars 5
python -m desk_ml mrr-fit --underlying NIFTY
python -m desk_ml mrr-fit --underlying SENSEX

# Paper dual-tape at the open (live chain; 0 = until stop flag)
python -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 10 --max-ticks 0
```

After **two** ticks with `index_ltp` + `atm_ce_ltp` + `atm_pe_ltp` on NIFTY (and SENSEX):

```bash
python -m desk_ml score --underlying NIFTY --source dual-tape
python -m desk_ml score --underlying SENSEX --source dual-tape
python -m desk_ml score --underlying NIFTY --source dual-tape --model-id both
python -m desk_ml overlay --source dual-tape
```

`session_action=HOLD` or `follow_gap=true` → **no new paper CE/PE**. `WATCH_ONLY` is still not a fill and not a MIX write.

Dual-tape persist also writes `paper_watch/DUAL-TAPE/overlay_last.json` (fail-soft). Thin ticks (<2 INDEX+CE+PE) → **HOLD**. Residual z is **causal** (past window only). `oos_claim: false`.

**Stop dual-tape:** `touch data/recon/paper_dual_tape_STOPPED.flag`

---

## HOLD rules (FOLLOW-GAP)

| Case | Action |
|------|--------|
| Index down, PE not up and/or CE not down | HOLD |
| Index up, CE not up | HOLD |
| Dual-tape missing ATM / stale / wrong strike | HOLD |
| ML-001 overlay HOLD / PREMIUM_DIVERGENCE | HOLD new paper CE/PE |
| ML-002 residual \|z\|≥2 or FOLLOW-GAP | HOLD |
| INDEX 1m `SIDEWAYS` (low ER / flips / tight band) | HOLD **new** paper CE/PE. Flatten/cancel still run. HYPOTHESIS. |
| Score CLI `DATA_INSUFFICIENT` | HOLD |

Do not treat `TREND_UP` / cluster id as BUY_CE.

---

## Must not

- `ExecutionClient` / Super Order / `/alerts/orders`
- Blocking LLM on this path
- `production_params_written: true`
- Promote from book-tune JSON
- Claim CPCV / OOS from the 5-bar embargo

```text
HANDOFF
From:     teams/06_backtesting
To:       founder / 00 / 05 / 07
Date:     2026-09-15
Status:   PAPER PREP / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Dual-tape + desk_ml score at 09:15 IST. FOLLOW-GAP HOLD.
  production_params_written false. ExecutionClient unused.
Rejected: Live Super Order; treat embargo as OOS; STRAT-015+.
UNKNOWN: Same-session ATM depth after open; SENSEX OU mean-reversion.
```
