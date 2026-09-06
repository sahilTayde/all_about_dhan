# PLAN — Market-hours paper agents (TradingAgents India)

**Date:** 2026-09-06  
**Status:** `IMPLEMENTED_SKELETON` / **UNVALIDATED** / paper only  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Package:** `packages/trading_agents_india`  
**EXTERNAL:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0)

No live orders. No win rates. KEEP_ALL STRAT-001–014. Does **not** touch `transcripts.sqlite`.

---

## Goal

During the NSE session, poll a multi-agent graph and append **paper** CE/PE/HOLD leans to:

1. `data/knowledge/trading_agents_india.sqlite`
2. `data/recon/paper_watch/{MIX-DEFAULT-BUY,MIX-TA-*}/YYYY-MM-DD.jsonl`

---

## Session clock (IST)

| Window | Behavior |
|--------|----------|
| 09:00–09:30 | `MIX-CLOCK-CAS` dead-band → graph may run; **HOLD only** |
| 09:30–15:00 | Active paper window — CE/PE allowed (still paper / refused) |
| 15:00–15:30 | Dead-band (CAS) → **HOLD only** |
| else / weekend | Outside shell → no directional paper |

---

## Tick cadence

| Setting | Value |
|---------|-------|
| Default | **45s** |
| Allowed band now | **30–60s** (CLI clamp 30–300) |
| Path toward faster | **15s** documented once option-chain **1 unique / 3s** budget + graph cost allow — **not default** |

---

## Agent graph + handoffs

```text
news → sentiment → technical → chain_watcher → bull → bear → boss → trader → risk
```

Structured `AgentHandoff` messages between roles. **Trader** emits paper `BUY_CE|BUY_PE|HOLD` only; **execution refused**.

New persona: **Option Chain Watcher** — Dhan chain if tokens work else fixtures; fake-breakout / thin-wall = `HYPOTHESIS`; DI if no data.

Premium: try OPTIDX rollingoption; else **INDEX proxy** labeled `HYPOTHESIS`.

Reasons cite `MIX-DEFAULT-BUY` + `MIX-TA-*` + optional PhD note snippets (inputs, not deletes).

---

## CLI

```bash
python -m trading_agents_india session --dry-run
python -m trading_agents_india market-hours --simulate --max-ticks 2
python -m trading_agents_india market-hours --tick-seconds 45 --max-ticks 8
python -m trading_agents_india clock
python -m trading_agents_india session --mode LIVE   # refuses
```

---

## MIX

- Existing: `MIX-TA-FLOW-RISK`, `MIX-TA-EVENT-HOLD`, `MIX-TA-EXEC-SANITY`
- New ledger id: **`MIX-TA-MARKET-HOURS`** (`PAPER_WATCH`, not default, not promote)

---

## HANDOFF

**Accepted:** Poll loop + dead-bands + handoffs + chain watcher + premium lean path + dual ledger + PAPER vs LIVE refuse tests + dry simulation.  
**Rejected:** Live orders; win rates; STRAT deletes; overwriting transcripts KB.  
**UNKNOWN / DI:** Live OI wall parser; OPTIDX dual CE/PE fetch; India sentiment; EVENT_MEMORY analogs; 15s tick readiness.
