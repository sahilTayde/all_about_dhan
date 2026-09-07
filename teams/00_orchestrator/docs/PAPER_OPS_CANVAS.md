# Paper ops canvas — layout + unplug policy

**Surface:** Cursor canvas `paper-operations-monitor.canvas.tsx` under the workspace canvases dir (`~/.cursor/projects/.../canvases/`)  
**Generator:** `scripts/paper_ops_monitor.py` (rewrites the canvas while ops monitor runs)  
**Gate:** PAPER only · NO_PROMOTE · orders REFUSED · not `RESEARCH_READY_FOR_PROGRAMMING`  
**Decision log:** [`data/recon/CANVAS_UNPLUG_2026-09-07.md`](../../../data/recon/CANVAS_UNPLUG_2026-09-07.md)

---

## Purpose

Operator-internal day board for paper market-hours. Not the customer `/` desk. Founder should see **FINAL/STOPPED, promote=false, signal/shadow, top veto reasons, LLM health, digest links** without drowning in DATA_INSUFFICIENT (DI) mass.

---

## Kept (primary)

| Block | Why |
|-------|-----|
| FINAL / STOPPED · promote=false · orders REFUSED pills | Day / gate state |
| Signals / shadow · HOLD/CE/PE · fills · non-HOLD | Paper outcome |
| LLM status / openai_used / last error · API/Vite | Rate-limit + desk health |
| **Top veto reasons** table | Explains zero CE/PE without DI flood |
| Attention table (actionable only) | Restart / LLM fail / Vite / shell |
| Digest + attention queue paths | `FOUNDER_DIGEST_*` · `ATTENTION_QUEUE_*` |

---

## Unplugged (collapsed or removed from primary)

| Item | Where now | Re-enable |
|------|-----------|-----------|
| Full DI why table (18 rows, buckets, ports, HOLD-on-DI) | Collapsed **DI honesty** card (≤6 top rows; unbound STRAT labeled) | Set `defaultOpen={true}` on DI card in `_render_canvas` / sealed canvas |
| Per-persona agent rows (news/sentiment/tech/chain/bull/bear/boss) | Collapsed **Agent roster** (slim: runner/trader/risk/ops/analysis/clock) | Expand roster card; or restore full `_agent_rows` into primary in `_render_canvas` |
| Full data-flow table | Removed from primary (still computed in payload for status JSON) | Re-add `<H2>Data flow` + `flowRows` table from git history / prior template |
| Fixture `LEVELS_NON_NUMERIC` strip | Collapsed **Parked fixture / DI noise** | Expand parked card; or put `level_bugs` back into `_tuning_rows` |
| DI ratio as founder “Tune data path” attention | Parked; DI card only | Remove `_is_parked_attention_why` filter for DI strings |
| Repeated “Why DI is high” callout + 4–5 DI Stat grids | Single collapsed DI card | Re-add callout/stats in `_render_canvas` |

---

## Why DI looked huge (2026-09-07)

- **11502 / 12141** candidates → `DATA_INSUFFICIENT`
- Almost all DI = **unbound STRAT-001–014** (`candidate_evaluator_available=false`)
- Only bound PAPER evaluator (typically `MIX-DEFAULT-BUY`) → **VETOED**, not DI
- KEEP_ALL: DI is honesty, **not** a catalog delete
- Binding / summarize-per-tick = workstream C (P1-3), not canvas

---

## Do not

- Promote from canvas stats
- Treat DI as “agents failed” or as license to delete STRATs
- Restart npm / paper ops from this doc unless founder asks
- Print secrets

---

## HANDOFF

**Accepted:** founder-ops primary layout; DI grouped + collapsed; fixture LEVELS parked.  
**Rejected:** deleting STRATs; inventing CE/PE; live orders.  
**UNKNOWN:** next NSE quiet session CE/PE after process P0 (owned elsewhere).
