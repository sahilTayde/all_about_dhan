# SESSION_PREP_ML — data 09:00 IST; first NEW 09:30; flatten 15:16; ticks to 15:30

## Founder — one command (do this, nothing else)

From the repo root. PAPER. No live orders.

| When | Command | What it does |
|------|---------|----------------|
| **Morning** (before / at 09:00 IST) | `./scripts/desk.sh morning` | Pre-market drill + API `:8000` + website `:5173` + dual-tape capture. Then open `/pm`, pick index, **START TRADE**. |
| **During session** | `./scripts/desk.sh status` | Pids and URLs. Do not restart unless something is DOWN. |
| **After close** (15:40 IST) | `./scripts/desk.sh close` | Stops data capture. **Keeps the website on.** Runs honesty exam + nightly recon + docs auditor. |
| Website only (review, no tape) | `./scripts/desk.sh website` | API + Vite. Capture off. |

**Morning review URLs**

- Desk: http://127.0.0.1:5173/desk
- Founder + honesty exam: http://127.0.0.1:5173/pm → section **Honesty exam (06)**
- Honesty JSON: `data/recon/sod_exam_report.json` (also `GET http://127.0.0.1:8000/paper/sod-exam`)
- Nightly JSON: `data/recon/YYYY-MM-DD.json` (IST date)
- Nightly PhD note: `teams/02_phd_math/docs/handoffs/NIGHTLY_YYYY-MM-DD.md`
- Auditor: `teams/00_orchestrator/docs/AUDIT_LATEST.md`
- Close receipt: `data/recon/close_status.txt`

Do **not** mix extra `npm run dev` / `uvicorn` / `dual-tape` lines on a normal day. One command.

---


**Team:** 06_backtesting (runbook) · 07 `packages/desk-ml` · 05 dual-tape  
**Date:** 2026-09-15 (IST)  
**Status:** `HYPOTHESIS` / **NO_PROMOTE** / `production_params_written: false`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** refused. Do **not** enable `ExecutionClient`. No Super Order.

Education ≠ advice. Cluster / OU numbers are cache counts, not a win rate.

This is how to start **paper gather + overlay score**. **FOUNDER LOCK:** dual-tape **data** **Mon–Fri 09:00–15:30 IST**. No Sat/Sun. Persist **INDEX + ITM option premium only** (never ATM/OTM). NIFTY example: spot 23500 → **23300 CE / 23700 PE**. NEW paper **09:30–15:16**; flatten all books **15:16**; ticks (no trade) **15:16–15:30**. It is **not** a promote. Customer default stays `MIX-DEFAULT-BUY`. KEEP_ALL STRAT-001–014.

---

## Now (what is true)

| Piece | State |
|-------|--------|
| Dual-tape | `python -m trading_agents_india dual-tape` — INDEX 1m + **ITM** option 1m chart (NIFTY ATM-4/ATM+4) + ITM chain LTP. No ATM option candles. No LLM. No orders. |
| ML-001 | KMeans k=4 + IsolationForest. Fit on warehouse `ohlc_bars`/`bars_1m` ∪ `premium_tape`. Seed **14**. Embargo last **5** 1m rows from fit (AFML analog, **not** CPCV / **not** OOS). |
| ML-002 | OU on residual + VWMA windows **40 / 60 / 90** only (max 3 tweaks). FOLLOW-GAP HOLD. SENSEX OU may be `DATA_INSUFFICIENT` / not mean-reverting on the thin ATM book. |
| Score CLI | `python -m desk_ml score --underlying NIFTY --source dual-tape` after two ticks with all three LTPs. |
| Live Super Order | **off** |

**Observer (ITM 1m) after picker:** SOD is **on by default**. Product path: FOLLOWS analyst → majority HOLD-or-one-wing → one observer review → one working ticket (`MIX-DEFAULT-BUY` ITM LTP). VETO kills NEW. ATM / missing ITM / strike roll / flat index → **PASS** (and desk does not fill ATM as ITM). LAB books observe-or-skip. `--sod-off` is pytest A/B of the old parallel FILL engine only — not the Monday path. Booking overlay unchanged. LLM exit/risk/partial-book is mock/fail-soft and **not** on ALLOW. **NO_PROMOTE.**

---

## 09:00 data / 09:30 first NEW / 15:16 flatten / 15:30 last tick (laptop, Mon–Fri only)

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
# A/B write=false (does not write MIX params):
# python -m desk_ml paper-scalp --replay --source dual-tape --underlyings NIFTY --session-date 2026-09-17 --no-write
# python -m desk_ml paper-scalp --replay --source dual-tape --underlyings NIFTY --session-date 2026-09-17 --no-write --sod-off
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

## HOLD rules (FOLLOW-GAP = closed 1m INDEX vs ITM wing)

| Case | Action |
|------|--------|
| Closed 1m INDEX down, same-strike ITM PE not up | VETO PE (`FOLLOW_GAP`) |
| Closed 1m INDEX up, same-strike ITM CE not up | VETO CE (`FOLLOW_GAP`) |
| ATM day / missing ITM / strike roll / no 1m / index flat | PASS (do not assume) |
| ML-001 overlay HOLD / PREMIUM_DIVERGENCE | HOLD new paper CE/PE |
| ML-002 residual \|z\|≥2 or FOLLOW-GAP | HOLD |
| INDEX 1m `SIDEWAYS` (low ER / flips / tight band) | HOLD **new** paper CE/PE. Flatten/cancel still run. HYPOTHESIS. |
| Score CLI `DATA_INSUFFICIENT` | HOLD |

Do not treat `TREND_UP` / cluster id as BUY_CE.

**INDEX S/R (pre-market / first dual-tape walk):** `build_sr_levels` on INDEX 1m closes — previous IST day high/low/close (PDH/PDL/PDC), then today session high/low as prints arrive, plus swing proxies on 15m / 30m / 60m / 1d / 1w. A last-3 1m dump/rally does **not** override the ITM CE/PE bin until volume + candle + option premiums confirm, and not as a false break at those levels. Proxy POC is typical (H+L+C)/3, not order flow. **NO_PROMOTE.**

**Replay tape (18 Sep):** dual-tape persist writes `replay_index` / `replay_premium` / `replay_strike` / `replay_features` / `replay_decision` into local sqlite. INDEX 1m REST miss **carries** last LTP. Paper OPEN **and CLOSE** rows include `justification` (SUCCESS/LOSS/CANCEL). Ship overlay: NIFTY **CE or PE** + strength + max4, skip BN+SENSEX, no T2. See `BACKTEST_REPLAY_TAPE.md`.

**Two work types (do not mix):**

| Desk | Job | Tune when |
|------|-----|-----------|
| Signal | Dealer / logit / XR / greeks say CE or PE (strike/limit). ML-001/002 observe (no own side). | Later: inspect *what* they fired and *why*. |
| Booking | After fill: path SL, trail, STALL only in INDEX ER<0.35 chop; TREND ER≥0.35 same-wing is retracement hold. AGAINST / bin / unwind / IV. | Every session. Do not recode without founder confirm. |

Same ticket, different skill. Switching bins / watching the other wing is **booking**, not a new MIX. `python -m desk_ml fix-first` scores booking. ML retune is parked.

**FIX-FIRST drill (pre-open and post-market, every session):** write=false from **2026-09-17**. Labels each IST **hour** TRENDING / SIDEWAYS / CHOPPY / VOLATILE from INDEX 1m ER/flips/range (**not** itm_bin TREND; lunch ER ~0.05 is chop). Fill `market_kind` = open ER (missing → UNKNOWN); close kind stamped at exit. Hour kind scores **booking**. Same job also writes `signal_desk` (dealer vs logit vs XR vs observe) — **do not mix** with STALL/TARGET recodes. Overlay exits unchanged until founder confirms. `data/recon/fix_first_progress.json`. CLI: `python -m desk_ml fix-first` / `python -m jobs pre-market` / `python -m jobs post-market`.

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
  FIX-FIRST pre-open + post-market drill from 17 Sep write=false. production_params_written false.
  ExecutionClient unused.
Rejected: Live Super Order; treat embargo as OOS; STRAT-015+.
UNKNOWN: Same-session ATM depth after open; SENSEX OU mean-reversion.
```
