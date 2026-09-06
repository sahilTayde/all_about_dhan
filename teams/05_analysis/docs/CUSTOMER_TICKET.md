# CUSTOMER_TICKET — suggested CE/PE with stop, target, confidence box

**Team:** 05 (talk) · 04 (ticket shape) · 07 (UI)  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / paper UI  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.**  
**Surface:** customer `/` — you decide Yes/No. Mix IDs stay light; confidence is **agreement**, not a win rate.

## What the customer sees

| Left | Right |
|------|--------|
| BUY CE or BUY PE + underlying | **Desk confidence** % (capped) |
| Strike · Entry · Stop · Target | Which playbooks are eligible + why |
| Honesty state (WATCH / EARLY / CONFIRMED / …) | Fairness line: not a win rate, not a fill |

Then: **Did you take this trade?** Yes / No. Orders stay refused.

## Confidence (fair labels)

Score = stage base + bonus if a second paper playbook agrees on the **same** side. Cap **72**. Never “90% sure this will work.”

| Band | Meaning |
|------|---------|
| none | No active lean |
| low | Early / thin agreement |
| moderate | One confirmed lean |
| higher_agreement | Confirmed + second playbook agrees |

Plain playbook names on `/` (not STRAT soup):

- **Session trend stack** ← `MIX-DEFAULT-BUY`
- **Gap + expansion** ← `MIX-CLUB-GR` (PAPER_WATCH)

## Levels (honest — named method)

Paper levels use a **named MIX / method id**, not silent hardcoded index points.

| Default method | Rule |
|----------------|------|
| `MIX-DESK-IQ-ATR-RR2` / `MIX-SLTP-ATR-R2` | Wilder ATR(14)×1.5 stop from entry; target R×2. Needs ATR seed from recent bars. |
| Fallback | If ATR missing → `levels_ready=false` + `DATA_INSUFFICIENT` (no fake points). |
| Deprecated | `DESK_PLACEHOLDER` fixed pts (NIFTY 30 / BN 60 / SENSEX 100) only if explicitly selected — labeled deprecated. |

Unit: `INDEX_POINTS_PROXY`. Option premium LTP still UNKNOWN until chain binds.  
Backtest of ATR overlay on NIFTY INDEX 3m: **FAIL** — see [`BACKTEST_SLTP_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_SLTP_2026-09-06.md). Do **not** paste that wr into confidence.

## Must not

- Auto-place orders.  
- Show backtest wr as “confidence this trade wins.”  
- Dump MACD/RSI/STRAT IDs on customer `/`.  
- Claim `RESEARCH_READY_FOR_PROGRAMMING`.  
- Silent hardcoded stops presented as a strategy.

Code: `levels.py` · `ticket_confidence.py` · `live_signals.py` · `ConfidenceBox.jsx` · `SignalCard.jsx`.
