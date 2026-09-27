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
