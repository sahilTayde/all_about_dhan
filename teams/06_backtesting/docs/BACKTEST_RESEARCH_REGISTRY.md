# Strategy research registry and status (NIFTY / SENSEX index options, paper only)

One file, append-only: every experiment gets a row, failures included. Detail tables live in
`BACKTEST_ROUND2_OPTIONS_1Y.md` (rounds 2-4) and `BACKTEST_INDEX_5Y_PRICE_RULES.md` (round 0). Never re-test a row below
under a new name; read "Lessons" first.

## Research status (updated 2026-10-28)

**Objective.** Find a rule with a reproducible edge after realistic costs, or prove there is none in the data we have.
"Better" means the system can tell real opportunities from noise and stays out when it has no edge. Trading more is not the goal.

**Live strategies.** None. No live orders. Paper and shadow only.

**Forward shadow (running daily from the recorder tape).** These rows are not live results.
- FIN1: buy the straddle on active openings.
- S2: sell the straddle on calm openings.
- Adoption rule: 40+ logged days and p < 0.05 outside Oct-2026. Status: 3 days logged (16/21/22 Oct). FIN1 net -7.5k over 4 signals; S2 net -3.9k over 2.

**Most promising candidates.** None proven. Experiments done: R0-R3, R3b, E1-E9, E12-E18 (E15 blocked: no data); audit A1 (closed 2026-10-28). Ranked by remaining hope:
1. FIN1 and S2, waiting on forward data.
2. The fade credit spread (E5b), undecidable on the history and needs the wider tape.

**Important discoveries.**
- **D1.** Dhan expired-options history is ATM+-3 only. ATM+-4..10 was refused on 728/728 calls.
  - On trend days the held strike vanishes, so anything held to 15:15 and any wing structure is undecidable on history.
  - The round-2 buyer engine exited early there, which biased rounds 2-3 for 15:15 holds.
- **D2.** How much the rest of the day moves (RV vs IV) IS predictable at 09:45.
  - Opening RV/IV gives AUC 0.74 on dev and 0.86 on holdout.
  - A walk-forward logistic model gives 0.70 / 0.87.
  - But option P&L is not predictable: S1 win AUC was 0.445 on the holdout.
  - Prices already include the predictable part of volatility. This explains why every timing rule failed out of sample.
- **D3.** After 09:45, breakouts failed more than random in calm Dec-Jul (dev p_vs_rand 0.91-0.99). That did not hold in Aug-Oct.
  - Pattern behaviour is regime-dependent.
  - The regime-to-P&L link does not survive out of sample (D2).
- **D4.** A random intraday ATM buy loses Rs 1.0-1.3k per trade (10 lots) to spread, costs and theta. Any buyer signal must clear that.

**Blockers.**
- Strike width of the history (D1). The live recorder tape is wider (moving ATM+-4, open ATM+-5 ladder, 10-minute retention) but has only 13 days so far.
- The auto-mode classifier refuses to create scheduled tasks for the standalone self-heal and the weekly review.

**Next prioritized experiments.** Reasons are in the E-rows.
1. **E10: re-run E5b (fade credit spread) and the iron fly on forward tape days** once 20+ full days exist (about 2026-11-20). The live ladder gives the wings real quotes. It is the only open candidate the history cannot decide.
2. **Judge FIN1 and S2 at 40 forward days** (about late Dec 2026).
3. **E11 (cheap): use the E9 imbalance only to time FIN1/S2 entries inside a 2-minute window.** It could save part of the half-spread. Test it on forward days; do not make it a signal.
- E9 is done: order-book imbalance carries information, but it is smaller than the spread.
- E12-E14 are done (2026-10-28), all rejected. Relative NIFTY/SENSEX vol, selling after a shock, and exit choice on random entries give no edge after costs. Exit tuning cannot rescue entries that have no edge.
- E16-E17 are done (2026-10-28), all rejected. The full T-1 option chain (max pain, OI pin, smile skew) adds no tradeable edge. E15 (GIFT Nifty) is blocked: the official history needs a session token; the founder can download it by hand.
- E18 is done (2026-10-28), rejected: the E6 volatility forecast does not cut S1's left tail (holdout CVaR p 1.00, maxdd p 0.48 vs random skips).

**Research infrastructure changes (2026-10-28).**
- `scripts/lab5y/sell_lab.py`: multi-leg engine with bounds, spot exits, studies `grid e5 e5b e6 e7 e8 e12 e13 e14 selftest`. `struct` gains `lots` (fixed brokerage, the rest scales) and `trail`.
- `fin1_shadow.py` logs S2.
- `scripts/lab5y/ext_fetch.py` also caches the NSE/BSE F&O bhavcopy (NIFTY/SENSEX index-option rows) in `data/cache/ext/bhav/`; `sell_lab.py` gains `chain_table` and study `e16e17`.
- `claude_daily.sh` gains `heal` (10-minute self-heal) and `report` (daily report and ping).
- `fin1_shadow.py forward [day|all]` (read-only): the 09:46 ATM-IV cone to 15:15 (+-1/2 sigma, sigma scaled by the trading-minute share of the option's remaining variance), the FIN1/S2 decision, then the realized close. One row per sym-day in `data/recon/forward_view.jsonl`, an SVG per day in `data/recon/forward_view/`, and a calibration line in the daily report. 2026-10-28 backfill: 12 sym-days (6 days); on the other 11 tape days the index spot ticks (NSE_IDX/BSE_IDX) were missing from the opening half hour (first spot tick 12:14 on 10-27, 10:59 on 10-13) although the recorder was running.

## Experiment registry

Common setup unless noted:
- **Data:** Dhan rolling expired weekly options, 1m bars, 2025-10-27..2026-10-23, ATM+-3.
- **Split:** dev before 2026-07-27, walk-forward by month; holdout 2026-07-27..10-23 run once per frozen rule.
- **Fills and costs:** fill at the next 1m open plus a p75 half-spread from the tape; costs from config/charges.yaml x1.5; 10 lots (NIFTY 65, SENSEX 20).
- **Code:** `scripts/lab5y/opt1y_lab.py` (R2-R3) and `scripts/lab5y/sell_lab.py` (R4+).

| ID | Question / hypothesis | Entry | Exit | Result (dev / holdout) | Uncertainty and limits | Decision | Next |
|---|---|---|---|---|---|---|---|
| R0 | 5y index price rules (momentum, fade, ORB) on 1m spot | various | various | null vs random after costs | index only, no option prices | reject | options data (R2) |
| R1 | 13 tape days, option rules | various | various | null | 13 days only | reject | 1y history (R2) |
| R2-F | OI, vol, expiry, F4 structure, walk-forward ML (round 2) | various | old engine | null except FIN1 | old engine biased on 15:15 holds (D1) | reject; FIN1 to shadow | E1 |
| R3 | NSE FII OI, FRED S&P/VIX/INR, RBI/FOMC days (10 variants) | 09:46 | 15:15 | all null; FII contrarian +4.5L dev, -29k holdout | 15:15 holds undecidable (D1) | reject | E2 |
| E1 | Short straddle / iron fly / long straddle × 6 entries × 6 exits, held to 15:15 | 09:20-14:00 | time, stops, targets | short straddle -27.9L..+34.9L, long -42L..+18L (cons..opt) | bounds dominate | undecidable | spot-exit grid (E2) |
| E2 | Same structures with spot exits <= 2.5 steps (bounds-free) | 09:20-14:00 | spot 1-2.5, credit stop/target | long straddle loses in every cell; short straddle + only at 09:46-10:30 | 48 cells, multiple testing | freeze S1/S2 | E3 |
| E3 | S1 short straddle 09:47 with a 2-step spot exit; S2 = S1 when opening RV/IV <= 1.0042 | 09:47 | 2-step spot or 15:15 | after the A1 fix: S1 +3.33L p 0.14 / -2.23L; S2 +4.97L p 0.03 / -99k (before the fix: +5.07L / -53k) | dev = calm months | reject; S2 to shadow | E5, E6 |
| E4 | FIN1 re-scored with bounds | 09:46 | 15:15 | dev -2.55L..+4.93L, holdout -75k..+4.88L | bounds dominate | undecidable; keep shadow | forward data |
| E5 | E5a: buy ATM on the first close beyond the 09:15-09:45 range; E5b: fade a break that re-enters within 15 min (12 cells) | <= 12:00 | spot target 1/1.5/2, stop 0.5/1 | ORB worse than random (p_vs_rand 0.91-0.99) / about random; fade better than random by about 1k/trade but net about 0 / not significant | regime-specific | reject both as standalone | E5b variants, E6 |
| E5b | Fade with ITM1 buy, or with a credit spread (short ATM + wing 2 steps out) | same | same | ITM1 worse in every cell; credit spread after the A1 fix: cons -6.4L..-17.2L, opt +1.2L..+5.6L | the wing leaves the tape on target moves | ITM1 reject; credit spread undecidable | E10 |
| E6 | Can the rest-of-day RV/IV be predicted at 09:45? | - | - | or_iv AUC 0.74 / 0.86; logistic 0.70 / 0.87; outside data about 0.5 | the target is relative to the dev median | yes, volatility is predictable | E7 |
| E7 | Does S1 P&L follow the E6 score (quintiles, cuts from dev)? | 09:47 | 2-step spot | not monotone; calmest fifth +2.05L / +6k | 55/27 days per bucket | no | E8 |
| E8 | Predict S1 win/lose directly (walk-forward logistic) | 09:47 | 2-step spot | AUC 0.605 / 0.445; the top half still loses on holdout | 192/124 days | no edge in timing the seller; stop optimizing these features | E9 |
| E9 | Does 5-level order-book imbalance on ATM-near options (live tape, 1 s snapshots) predict the option mid 60 s / 300 s ahead beyond the spread? `scripts/lab5y/depth_lab.py` | imb5 > +0.6, buy at ask (frozen) | sell at bid after 60 / 300 s | IC small but real for NIFTY at 60 s (imb1 0.0074 t 4.5, micro 0.0076 t 4.4); SENSEX and 300 s about 0. Rule vs random: +0.15 NIFTY pts (p 0.01), +0.27 SENSEX pts (p 0.04) at 60 s, but net -Rs 100..119 per lot per trade in every cell (wins 33-39%) | 7 days, one regime (Oct-2026); overlapping 1 s samples (t uses days) | information yes, tradeable no; at most use it for entry timing (a fraction of the half-spread) | E10 |
| R3b | Brent crude (FRED DCOILBRENTEU, US date before the Indian day) as a 5th outside source; sign fixed a priori: Brent up -> PE (India imports oil). Same R3 engine; also closes the A1 leftovers | 09:46 | 15:15 | dir by sign: dev -6.3L (p 0.90) / holdout -4.8L (p 0.999, worse than random); straddle on big |Brent| move: dev -6.3L (p 0.09) / -1.7L. Other R3 rows unchanged | 15:15 holds use the old engine (D1, 33-58% lost to the strike window); EIA publishes about a week late, so the last days reuse 20-Oct | reject | none |
| E12 | NIFTY vs SENSEX relative vol: z = log(IV_S/IV_N) at 09:46, minus the mean of prior days with the same DTE pair, vs the prior 20 days. If abs(z) > 1.5, short the rich ATM straddle and buy the cheap one, vega-matched in whole lots (1-10 each) | 09:47 | either index moves 2 steps, or 15:15 | pair: dev -14k on 22 pairs (p_boot 0.67, p_vs_rand 0.11, 2/5 months) / holdout +9.7k on 12 (p_boot 0.37, p_vs_rand 0.055). Short legs +12k / +21k, long legs -27k / -11k in both samples | 22 + 12 signals only; 0% forced, so the bounds play no role | reject (sign flips, never significant) | none |
| E13 | Sell after a shock: the first 2-step spot move from 09:45 (by 14:00); short the ATM straddle on the next bar if ATM IV rose more than X since 09:45 (X = walk-forward dev median, -0.25 IV pts) | <= 14:01 | further 2-step move, 30%-of-credit stop, or 15:15 | rule: dev cons -1.78L on 114 (p_boot 0.91; opt +3.6L) / holdout -37.7k on 55 (p 0.64). Control, every shock: dev -2.9L / holdout +23.7k (p 0.40). Holdout: the 15 shocks the filter dropped made +61k | dev cons/opt gap = 3 SENSEX trades whose strike left the ATM+-3 window (bound path, not data holes); without them both modes are -1.02L. p_vs_rand 0.001 / 0.02 is NOT evidence: the random minutes include bars before the coming shock (critic) | reject | none |
| E14 | Exits only: random entries (4 per sym-day, 09:20-14:00, random side) for long ATM, short straddle and the E5b fade credit spread; 11 exits (spot 1/1.5/2/2.5 steps, time 15/30/60/120 min, premium trail 20/30/50% with a 2.5-step cap) vs holding to 15:15 on the same entries | random | as listed | strict test, exit(cons) - hold(opt): 0 of 33 cells pass (Bonferroni 0.0015), dev and holdout. Every cell loses in cons on dev; best on holdout is short straddle trail20 at +2k (breakeven). Short straddle vs hold (cons): early exits lost less on dev (+0.8..+1.3Cr) but MORE on holdout in all 11 cells (-28k..-9.9L, hold +30k) | the strict test was unpassable for short structures, since opt prices off-tape short legs at intrinsic (19.7% / 35.4% of holds forced on dev). The cons upper bound is about 20-25% over the real price one strike out (critic calibration). Long ATM vs cons hold is meaningless (loose bound) | reject: no exit makes random entries pay; the dev finding that early exits help straddle sellers did not survive the holdout | none |
| E15 | GIFT Nifty (NSE IX) overnight move known before 09:15, residual after the NIFTY open gap; (a) ATM in its sign, (b) straddle on a big residual | 09:46 | 2.5-step spot or 15:15 | not run: BLOCKED, data not obtained. nseix.com serves history only through a session-token API (/api/historical-derivative, /api/historical-reports need a token from /api/generate-token); a scripted token fetch was refused as access circumvention, and no static archive URL exists in the site bundle. SGX Nifty ended 2023. Nothing approximated | not proof that no data exists; also unverified whether the NSE IX daily close for date T is the 02:45 session-2 close (usable on T+1) or the 15:40 close (almost no overnight info) | blocked | founder downloads NSE IX daily history by hand (browser), or approves a browser download; then run the frozen rules |
| E16 | Full-chain option positioning from the T-1 NSE/BSE F&O bhavcopy (new source: every strike's EOD OI; Dhan history is ATM+-3, D1). g = (max-pain strike - spot 09:45) / step. (a) ATM toward max pain if abs(g) > WF q0.7; (b) pin: short ATM straddle if abs(g) <= 1 and dte <= 1 | 09:46 | (a) 2.5-step spot or 15:15; (b) 2-step spot or 15:15 | (a) dev cons -12.3L on 138 (p_boot 0.988, p_vs_rand 0.82, 3/8 months, maxdd -15.9L) / holdout +1.64L on 44 (p_boot 0.22, p_vs_rand 0.032, 3/4). (b) dev +20k on 36 (p_boot 0.44, p_vs_rand 0.81) / holdout -71k on 9 (p 0.89). Spearman g vs 09:45->close move 0.061 / 0.010 | 4 cells, Bonferroni 0.0125. Chain covers 489/492 panel sym-days (3 SENSEX days with a holiday-shifted expiry unmatched). Sign flips dev -> holdout: noise | reject | none |
| E17 | Smile skew from the same T-1 chain: rr = IV(put ~1 sd below) - IV(call ~1 sd above), Black-76 from close; z vs the prior 20 days. (a) ATM against the skew (z > 0 -> PE, informed put demand) if abs(z) > WF q0.7; (b) long straddle if z > WF q0.7 | 09:46 | 2.5-step spot or 15:15 | (a) dev cons -7.6L on 82 (p_boot 0.991, p_vs_rand 0.88, 0/8 months) / holdout -1.94L on 59 (p 0.78). (b) dev -5.5L on 92 (p_boot 0.994, p_vs_rand 0.20, 1/7) / holdout -1.44L on 62 (p_boot 0.74, p_vs_rand 0.007, 3/4) | the q0.7 cut picked about 50% of holdout days (the skew z distribution shifted). (b): on high-skew days long straddles lost less than random long straddles on holdout only, but still lost | reject; (b) is a lead only (skew may say when buying vol is least bad), not an edge | none unless a forward check is cheap |
| E18 | E6 forecast as a TAIL gate, not a profit signal: skip S1 (short ATM straddle 09:47, 2-step spot exit) when the E6 walk-forward score > dev q0.8 (0.968). Frozen before results: CVaR 5% per trade, worst day, maxdd, mean, total vs 1000 random skips of the same count; adopt only if p(CVaR) and p(maxdd) < 0.05 and mean not worse, dev AND holdout. `sell_lab.py e18` | 09:47 | 2-step spot or 15:15 | dev cons (skip 55/274): CVaR5 -24.6k vs -27.2k all (p 0.015), worst day -51k vs -66k (p 0.10), maxdd -2.08L vs -3.13L (p 0.12), mean 867 vs 1,044 (worse) / holdout (skip 24/124): CVaR5 -31.8k vs -30.8k (p 1.00: no worst trade was on a skipped day), worst day unchanged -58k, maxdd -3.23L vs -4.02L (p 0.48, = random), mean -1,070 vs -1,431 | holdout not fully fresh: E7 had already printed the holdout mean of this exact bucket (q5); its tails were not seen. Opt mode gives the same verdict. Holdout: all 7 worst S1 trades were on days scored below the cut (4 in the calmest fifth); dev: 6 of the 14 worst were skipped | reject: predicting high volatility does not predict S1's big losses; skipping costs mean on dev and cuts no tail on holdout | none (do not re-test with other cuts) |

A1 leftovers closed 2026-10-28: (1) `opt1y_lab.pool()` cache key now includes HSCOL, the cost multiplier and a hash of the code, so stale placebo pools cannot be reused; (2) DEXINUS timing checked: `ext_table()` uses only US dates before the Indian day, and the noon-NY rate is fixed at about 21:30 IST the evening before (FRED publishes later, but the rupee trades live), so there is no look-ahead.
