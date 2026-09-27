# Founder comments log (single source of truth for Sahil's mid-build comments)

Rule: every comment Sahil gives during the build gets a numbered entry here the same turn,
with where it is implemented, which test proves it, and its status. Nothing is considered
"done" until its test passes. Addenda to running build agents are queued, never interrupting.
Times are CT, 2026-09-26.

| # | Time | Comment (paraphrased) | Where it goes | Proof / test | Status |
|---|------|-----------------------|---------------|--------------|--------|
| C1 | 21:01 | Option buyer; no long ATM holds, no 1-2 trades/day cap; active management, market-driven trade count | v2 strategy runtime + exits | Lab replays, total net | Design input |
| C2 | 21:31 | Judge strategies on final total net P&L after costs; small losers and low win rate are fine | All labs, basket scoring | Every report headline = total net | Active |
| C3 | 21:32 | Strike per trade with a reason (ATM <=5 min holds, ITM100/200 for 15-30+ min, care on expiry and 09:20-10:00) | v2 strike router (strategy runtime) | Round 9 router test; shadow logging | Shadow; router lost less than fixed strikes but still lost |
| C4 | 21:35 | Use SSRN papers and good traders' setups actively; test, don't trust posted win rates | Harvest lab | PR #24 (51 papers), harvest lab basket | Running |
| C5 | 21:41 | Strategy library with India basket (NIFTY+SENSEX) and forex basket (parked); per-regime weight/rank so boss picks a daily basket | Strategy registry (bc-80505954) + harvest lab | basket_india.json / basket_forex.json | Running, first basket 08:00 CT Sun |
| C6 | 21:43 | Basket module is a separate parallel track; never blocks the 32-step build; draft PR, merges later | Self-contained files | Draft-only PR | Enforced |
| C7 | 21:48 | Do not follow the old engine; build our own production system (Redis, DuckDB, websockets, VPS, customer-ready); old tape engine is reference only | v2 architecture (bc-cd0a46e2) | New merge gate: tests, no-look-ahead, fault, perf, live-like dry run | Design running |
| C8 | 21:50 | Bring every fix done on the old engine into the new one | v2 build plan "Legacy bug carry-over" (13 items) | One must-pass test per item | Sent to design |
| C9 | 21:53 | System enters at top of big candles; loses 4-5 pts to retrace into imbalance/POC then stops out | Round 10 lab + v2 entry-location rule | Round 10 report (diagnosis + pullback/stretch/wait tests) | Lab running, 08:00 CT Sun |
| C10 | 21:54 | Boss and desk must be aligned to the entry-location rule | v2 desk order planner + boss veto; basket strategy cards | Log-only until round 10 thresholds; tests in v2 ticket | Sent to design + basket |
| C11 | 21:55 | Don't mess up with mid-build comments; lots of money and time spent | This log + morning status checklist | Each C# shows status in 08:00 CT report | Active |

Standing rules that also apply: paper only; every number from a source file or real run; verified cost stack
(Dhan Rs20/order, STT 0.15% sell premium, NSE 0.0355299%, stamp 0.003% buy, GST 18%, lot 65); going live for
customers only on Sahil's explicit call.

## Desk-lead design inputs (A#; not founder comments)

These are the desk lead's design inputs to the v2 architecture, kept separate from Sahil's C# entries. Numbering
follows the design addenda (A1 and A3 are covered by C8 and C9/C10). Times are CT, 2026-09-26, when the design agent
received them.

| # | Time | Input (paraphrased) | Where it goes | Proof / test | Status |
|---|------|---------------------|---------------|--------------|--------|
| A2 | 22:09 | Round 9 data needs: order-book depth <= 1 s and bid/ask quote snapshots <= 5 s for ATM/ITM100/ITM200 both sides; log OI update frequency; strike router with reason and shadow-priced alternatives; time stops as a first-class exit; preregistered forward-test harness, off by default | v2 marketdata (V2-D1, V2-D2), strike router (V2-06b), exits (V2-09), forward harness (V2-20a) | V2-D2 cadence tests; V2-06b router tests; V2-09 time-stop tests; V2-20a harness tests | Designed (PR #27) |
| A4 | 22:24 | Commit this log as the single source of truth and keep a traceability table from every C# (and every legacy carry-over item) to service, ticket and test; flag conflicts instead of resolving them silently | This file; `docs/architecture/V2_BUILD_PLAN.md` §4 | TRACE-01 meta-test in V2-16 | Designed (PR #27) |
| A5 | 22:28 | PR #20 cost-realism lessons (merged as c004ace): limits fill only at the limit on a trade-through, stops at or worse than the trigger; EOD flatten never held back by the stale-quote guard; malformed cost config fails closed with an alert; every trade tagged NSE/BSE; verified cost stack with BSE Rs 3,250/crore, recorded half-spread slippage, 0.20 pt/side fallback; realistic fills only | v2 fills and charges (V2-08), exits (V2-09), ledger (V2-10) | REG-12, REG-14, REG-15, REG-16, REG-17 | Designed (PR #27) |
| A6 | 22:33 | Round 10 entry result: no entry-location rule; marketable next-bar entries; entry_policy kept on strategy cards (chase default; pullback_limit and wait_consolidation supported but off); boss records stretch with no veto; the -4/-5 pt cluster comes from legacy tight cancel exits, so exits become per-strategy primitives with round 11 defaults | v2 order planner and boss (V2-08b), exit primitives (V2-09, V2-09b) | V2-08b acceptance; REG-18 | Designed (PR #27); exit defaults wait for round 11 |
