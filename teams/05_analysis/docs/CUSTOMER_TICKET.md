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

Paper **index** ATR levels may exist for chart / research (`index_*`).  
Customer ticket **Entry / Stop / Target** for BUY_CE / BUY_PE are **option premium** only.

| Default method | Rule |
|----------------|------|
| `MIX-DESK-IQ-ATR-RR2` / `MIX-SLTP-ATR-R2` | Wilder ATR(14)×1.5 stop from index entry; target R×2 — kept as `index_*` for chart. |
| Customer premium slots | Bound when ATM option LTP exists (`POST /optionchain`). Entry = LTP. Target = entry×1.25 (`MIX-SLTP-PREM-PCT`). **Okala PAPER starter Stop** = entry×0.75 (`paper_starter_premium_stop` / `NEWS_VETO_ENABLED=false` path) — HYPOTHESIS until swing/greek map. Teacher swing stop still fills `index_stop` when bars exist. |
| Fallback | If ATR missing → index builder `levels_ready=false`. Premium still DI until chain binds. |
| Gap reason | When LTP missing: `levels_note` / UI shows e.g. `OPTIDX premium not fetched` / dry_run / expiry empty — never paste index prints into Entry/SL/Target. |
| Deprecated | `DESK_PLACEHOLDER` fixed pts (NIFTY 30 / BN 60 / SENSEX 100) only if explicitly selected — labeled deprecated; still quarantined off customer premium slots. |

Unit on customer ticket: `OPTION_PREMIUM` (DI until LTP). Chart overlays may show index entrySpot/stopSpot/targetSpot separately.  
Backtest of ATR overlay on NIFTY INDEX 3m: **FAIL** — see [`BACKTEST_SLTP_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_SLTP_2026-09-06.md). Do **not** paste that wr into confidence.

## Must not

- Auto-place orders.  
- Show backtest wr as “confidence this trade wins.”  
- Dump MACD/RSI/STRAT IDs on customer `/`.  
- Claim `RESEARCH_READY_FOR_PROGRAMMING`.  
- Silent hardcoded stops presented as a strategy.

Code: `levels.py` · `option_premium_ltp.py` · `ticket_confidence.py` · `live_signals.py` · [`PREMIUM_SWING_STOP.md`](PREMIUM_SWING_STOP.md) · `ConfidenceBox.jsx` · `SignalCard.jsx`.
