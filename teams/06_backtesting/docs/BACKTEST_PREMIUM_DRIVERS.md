# What moves option premiums: observe first, then test (E55, E56, E57)

Paper research only. No live orders. Registry rows E55 (observations), E56 (loop 1 rules), E57 (loop 2) in
`BACKTEST_RESEARCH_REGISTRY.md`. Code: `scripts/lab5y/observe_lab.py` (selftest included). Run date: 2026-11-17.

## Now

- We watched first and traded second. 19 things were measured on four years of 1-minute data (LEARN, 2021-10-27 to
  2025-10-24) and on 8 tick-tape days, before any rule was written.
- From what we saw, 8 trading rules and 1 tick rule were frozen in the registry and then scored once on the unseen
  year (TEST, 2025-10-27 to 2026-10-26) or on 3 held-back tape days.
- **Result: 0 of 13 scored cells pass the bar that was fixed in advance.** Nothing new goes to the desk.
- The closest result: **when the index closes through yesterday's high or low, it tends to keep going for 15 minutes**
  (about +3 to +4 index points). Buying a 2-strikes-in-the-money NIFTY option on that signal made money after all costs
  in the four learning years (+Rs 9.05 lakh, 573 trades) and in the unseen year (+Rs 3.21 lakh, 161 trades). It still
  fails the bar: the unseen-year result could be luck about 1 time in 12 (p 0.084; the bar was 0.005), it wins only 48%
  of trades, and without its 5 best trades the unseen-year profit is Rs 0.66 lakh. The SENSEX wall rule (R5) is equally
  close (p 0.058) but loses on NIFTY. These are small, consistent tendencies, not an edge.
- The only strategy that passes all tests is still the expiry-day strangle sale (rows E39 / E43). This study does not
  change that.

## Why

Plain reasons, each with its number.

1. **The index move is almost the whole story.** About 80% of a NIFTY option's 1-minute price change is the printed
   index move; 91-97% when the move is read from the options' own implied future (delta and gamma). The general volatility level adds 1-14%. Everything else is 2% or less. There is no hidden second
   driver to trade.
2. **Nothing we record moves before the options.** On the tick tape the option prices move first, about 0.2 second
   ahead of the NIFTY future's quote on our feed. The SENSEX index print is 0.5 second behind. Volatility changes and
   index moves happen in the same minute. The cross-market tape (VIX, BANKNIFTY, 11 heavyweights, crude, gold) shows no
   1-minute lead either, on 3 days.
3. **A minute candle forms like a coin-toss walk.** After 5 / 15 / 30 seconds the bar has made 27% / 51% / 73% of its
   range. A random walk gives 29% / 50% / 71%. No second of the minute is special.
4. **Time decay is real but it is already known and mostly not capturable.** Premiums fall fastest in the first 15
   minutes and in the last 90 minutes of expiry day. The opening fall is mostly the first minute's print: a straddle
   sold at the real 09:16 open keeps 2.9 points on NIFTY, and nothing is left by 09:20. Selling it made money in the
   learning years and lost in the unseen year.
5. **The popular chart ideas show nothing above cost.** Liquidity sweep, fair value gap, order block, opening range
   and VWAP crosses were defined mechanically before looking. The largest is the fair value gap: +0.6 index point in 15
   minutes (11,830 cases). A trade costs about 2 index points.
6. **Levels that did show something:** yesterday's high and low (NIFTY), multiples of 500 (NIFTY), and the
   highest-open-interest strikes. All six rules built on them were positive in the learning years. In the unseen year
   the gains shrank and none is statistically safe.
7. **Price gaps between strikes are not free money.** At a glance a risk-free "box" appears in 80% of seconds. Half a
   second later it is worth 0.2 point, and one second later it is negative. The four quotes were simply not updated at
   the same instant.

## Observations table (phase 1, no rules)

Sample: LEARN panel unless "tape" is written. Points are premium points per unit unless "index points" is written.
One round trip costs about 0.75 (NIFTY ATM), 0.9 (NIFTY ITM2) and 1.9-4.5 (SENSEX) premium points.

| # | What was seen | Size | Sample | New or known |
|---|---|---|---|---|
| 1 | Share of a 1-minute premium change explained by the index move (delta + gamma) | NIFTY 91-97% and SENSEX 86-90% measured on the option-implied future (which is built from the same option prices); about 80% on the printed NIFTY index (critic's check) | NIFTY about 700,000 option-minutes per depth (calls and puts), 983 days; SENSEX about 400,000, 602 days | New |
| 2 | Share explained by the general volatility level / by the strike's own volatility / left over | NIFTY 1-14% (largest far out of the money) / -6 to +2% / 2% or less | same | New |
| 3 | Real decay against the textbook (calendar) decay, NIFTY ATM, points per hour, index move removed | 09:15-09:30: -6.6 against -0.8; midday: -1.7 against -0.8; expiry 14:00-15:00: -14.5 against -9.7; expiry last half hour: -20.8 against -8.1 | 5-minute changes, 3,760 to 207,709 per cell | New as numbers (D4 is the known base) |
| 4 | What one bought NIFTY ATM option loses per hour in total (decay minus gamma gains) | midday -0.4; first 15 minutes -2.4; expiry 14:00-15:00 -4.4; expiry last half hour -10.7 | same | Known in kind (D4, E45), new by clock |
| 5 | Does a premium that has bled keep bleeding? After the worst tenth of 5-minute non-index falls, the next 15 minutes | NIFTY ATM -0.91 against -0.53 on average (0.4 extra); expiry day -3.10 against -1.68 | 407,664 and 111,411 option-minutes | Below cost off expiry; on expiry it is the E52 sell model again (closed) |
| 6 | ATM implied volatility through the day | falls 7% from 09:20 to 15:15 on normal days, 12% the day before expiry; expiry: -5% by 10:00, flat, then collapses after 14:45 | 577 / 197 / 209 NIFTY days | New |
| 7 | Put-minus-call skew two strikes out | +0.7 vol points (normal), +1.1 (day before), +1.6 (expiry); steady through the day | same | New; E17 found no edge in skew |
| 8 | Which moves first, volatility or the index? | same minute: correlation -0.31 (NIFTY), -0.19 (SENSEX); every lag of 1-5 minutes: 0.02 or less | 774 and 468 days | New |
| 9 | After a sharp 3-minute fall in implied volatility, the ATM straddle over the next 15 minutes | -0.71 against -0.31 on average (0.4 extra on two options) | 224,967 minutes | Below cost; E44 h is the known relative |
| 10 | NIFTY against SENSEX, option-implied futures | same minute 0.886; one minute apart 0.03 or less | 601 days | Known (D6, E20): the lag is only in the index print |
| 11 | Tape: quotes and depth | NIFTY ATM spread 0.25, ITM2 0.40, ITM4 0.60; best size 800 / 400 / 300 units against 650 for 10 lots. SENSEX ATM spread 0.75-0.80, best size 80 against 200. NIFTY future spread 5 points | 8 tape days, 180,000-300,000 ticks per class | Partly known (E46); new by depth |
| 12 | Tape: how a 1-minute candle forms | range made after 5 / 15 / 30 s: 27% / 51% / 73% (random walk 29 / 50 / 71) | 2,713 NIFTY ATM bars, 8 days | New |
| 13 | Tape: who moves first, in milliseconds | options lead the NIFTY future quote by about 0.2 s; NIFTY and SENSEX options move together (0.0 s); the SENSEX index print is 0.5 s late | 8 days | New (sharpens D6 and E46) |
| 14 | Tape: an option that looks cheap against the future | the "cheapness" reverses 35-43% in the next 30-60 s, but the option itself moves 0.0 to +0.25, inside its own spread: the future's quote was the noisy one | 4,200-127,000 windows, 6 non-expiry days | New (explains E46's weak future signal) |
| 15 | Cross-market tape, 1-minute returns against NIFTY | same minute: BANKNIFTY 0.87, FINNIFTY 0.91, heavyweights 0.42-0.68, VIX -0.47, crude -0.22, gold +0.11; one to three minutes apart: 0.11 or less | 3 days only | New; weak sample |
| 16 | Open-interest build-up labels (long build-up, short covering, ...) against the next hour | 1.5 index points or less; the sign flips with the way days are weighted | 4,467-24,497 cases per label | Known family (E31, R2): still nothing |
| 17 | Open-interest walls (NIFTY) | index breaks the call wall within 30 minutes 37% of the time against 49% for an ordinary strike; put wall 53% against 48% | 282 / 359 first approaches | New; became rules R5 / R6 |
| 18 | Yesterday's high / low (NIFTY), after the first 1-minute close through it in either direction (a fall back inside counts too) | index goes on +6.1 points in 15 minutes after a low break (t 3.0), +1.9 after a high break; ITM2 option gains 3.4 gross | 573 events on 527 days | Level breaks were tested on one year before (E21, E31) and lost; new on these four years with ITM2 |
| 19 | Round numbers | NIFTY multiples of 500: the index continues +5.3 points in 15 minutes (t 2.2); multiples of 100: nothing; SENSEX 1,000s: nothing | 310 events | New; became R3 / R4 |
| 20 | Opening range break, VWAP cross | -1.5 and -1.3 index points in 15 minutes (nothing) | 983 and 2,123 events | Known (E5, E44) |
| 21 | ICT liquidity sweep (reversal expected) | -0.4 index point in 15 minutes: no reversal | 475 events | New: no edge |
| 22 | ICT fair value gap (bounce expected) | +0.6 index point in 15 minutes (t 2.0): real but a quarter of the cost | 11,830 events | New: below cost |
| 23 | ICT order block (bounce expected) | NIFTY -0.3 (nothing); SENSEX +5.4 index points (t 2.5) = 2.6 premium points, below the 3.5-4.5 cost | 1,355 / 825 events | New: below cost |
| 24 | Put-call parity gap between neighbouring strikes, 1-minute closes | NIFTY median 0.15, worst tenth 0.9; 75-84% of a big gap is gone by the next bar | 348,705 bars per strike | New: print noise |
| 25 | Option closes that move against the index move | 0.1-0.2% of NIFTY ITM bars; the next bar catches up 0.8 (ITM2) to 1.9 (ITM4) points | 384,000 bars per depth | New: stale last-trade prints, at most 1.4 times cost |
| 26 | Deeper look: is yesterday's exact level special? Same test on levels shifted by 0.15-0.50% | NIFTY: real level +3.41, shifted levels -0.67 to +1.39. SENSEX: shifted levels do as well as the real one | 309-702 events per variant | New: on NIFTY the level itself matters |
| 27 | Deeper look: opening straddle sale by entry minute, 15-minute hold (NIFTY expiry day) | 09:16 +2.90; 09:17 +1.18; 09:20 +0.64; 09:30 +0.43 | 209 days | New: the crush is the first minute |
| 28 | Deeper look: parity box on the tape after a 10-lot fill and a delay | +1.65 at the decision, +0.20 after 0.5 s, -0.24 after 1 s | 4,532 cases on 8 days | New: not real |

## Strategies table (phases 2 and 3)

Rs at 10 lots, costs of the trade date x1.5, entry at the next minute's open with the 75th-percentile half-spread, pure
time exit, no stop. p = day-block bootstrap on the unseen year (TEST). The bar to pass, fixed before scoring: TEST profit
above zero, LEARN above zero, p below 0.005 (E56) or 0.025 (E57), better than a random-entry placebo, still positive at
double costs, 3 of 4 quarters positive.

| Rule | Index | Period | Trades | Win rate | Rs per trade | Rs total | p | Verdict |
|---|---|---|---|---|---|---|---|---|
| R1 buy ITM2 on a close through yesterday's high / low, hold 15 min | NIFTY | LEARN | 573 | 49.0% | +1,580 | +9,05,289 | 0.007 | |
| | NIFTY | TEST | 161 | 48.4% | +1,997 | +3,21,490 | 0.084 | FAIL (p; 5 trades = 80% of profit) |
| | SENSEX | LEARN | 353 | 48.7% | +974 | +3,43,874 | 0.083 | |
| | SENSEX | TEST | 161 | 48.4% | +535 | +86,099 | 0.333 | FAIL |
| R1 control: the same with the ATM option | NIFTY | TEST | 161 | 47.2% | +2,163 | +3,48,167 | 0.048 | control, not counted |
| R2 same events, sell the opposite ATM option, 15 min | NIFTY | LEARN | 573 | 52.9% | +535 | +3,06,726 | 0.085 | |
| | NIFTY | TEST | 161 | 51.6% | +612 | +98,487 | 0.218 | FAIL |
| | SENSEX | LEARN | 354 | 53.7% | +1,313 | +4,64,842 | 0.003 | |
| | SENSEX | TEST | 161 | 54.0% | +703 | +1,13,147 | 0.144 | FAIL |
| R3 buy ITM2 with a cross of a multiple of 500, 15 min | NIFTY | LEARN | 310 | 53.9% | +1,071 | +3,32,120 | 0.093 | |
| | NIFTY | TEST | 89 | 44.9% | +968 | +86,152 | 0.334 | FAIL |
| R4 same events, sell the opposite ATM option | NIFTY | LEARN | 310 | 58.4% | +939 | +2,91,190 | 0.118 | |
| | NIFTY | TEST | 89 | 50.6% | +306 | +27,192 | 0.421 | FAIL |
| R5 buy an ITM2 put when the index first nears an open-interest wall, 30 min | NIFTY | LEARN | 641 | 48.8% | +909 | +5,82,571 | 0.077 | |
| | NIFTY | TEST | 242 | 49.2% | -91 | -22,022 | 0.533 | FAIL |
| | SENSEX | LEARN | 301 | 50.2% | +1,377 | +4,14,562 | 0.089 | |
| | SENSEX | TEST | 204 | 52.0% | +2,197 | +4,48,133 | 0.058 | FAIL (p) |
| R6 same events, sell the ATM call, 30 min | NIFTY | LEARN | 640 | 56.1% | +666 | +4,26,242 | 0.065 | |
| | NIFTY | TEST | 242 | 55.8% | -245 | -59,222 | 0.588 | FAIL |
| | SENSEX | LEARN | 159 | 58.5% | +1,589 | +2,52,612 | 0.037 | |
| | SENSEX | TEST | 108 | 56.5% | +990 | +1,06,879 | 0.223 | FAIL |
| S1 sell the ATM straddle at the 09:16 open, buy back 09:31 (expiry day and the day before) | NIFTY | LEARN | 406 | 59.1% | +1,315 | +5,34,046 | 0.005 | |
| | NIFTY | TEST | 102 | 53.9% | -117 | -11,948 | 0.530 | FAIL |
| S2 the same on days two or more before expiry | SENSEX | LEARN | 311 | 60.1% | +1,560 | +4,85,181 | 0.005 | |
| | SENSEX | TEST | 144 | 45.1% | -316 | -45,482 | 0.616 | FAIL |
| T1 tick rule: parity box of 1.5+ points with all four quotes fresh, filled 0.5 s later | NIFTY | 8 observe days | 174 | 79% above charges | +Rs 525 (0.81 point x 650) | untestable as money: no trade prints | - | |
| | NIFTY | 3 holdout days | 22 | 73% above charges | +Rs 300 (0.46 point x 650) | untestable as money | - | no LEAD (one holdout day negative, 2 cases) |

Notes on the table.

- R1 NIFTY by year (Rs per trade): 2021 -686, 2022 -197, 2023 +1,872, 2024 +2,349, 2025 +3,202, 2026 +1,515. Expiry-day
  trades earn far more than the others (+3,896 LEARN / +3,352 TEST per trade against +960 / +1,518).
- T1: the charges for four legs were taken as 0.90 point. The tape cannot prove that a displayed quote would have
  filled, so even a pass here would only have earned a zero-size forward log.

## Independent review (Opus critic)

An independent Opus reviewer read the engine line by line and rebuilt rule R1 with its own code.

- **R1 reproduced to the rupee** from a separately written event detector (1,258 events, identical to the lab's): NIFTY
  LEARN 573 trades +9.05 lakh, TEST 161 trades +3.215 lakh; SENSEX +3.44 lakh / +0.86 lakh.
- **No look-ahead found.** Yesterday's levels come from the right day, the fill is the next minute's open, the hold is
  15 minutes, index and option bars are aligned, and the 1-minute open interest is truly intraday.
- **The R1 effect is real direction, but small.** Buying the opposite way on the same events loses Rs 2,304 (LEARN) /
  2,860 (TEST) per trade. The five biggest winners are real days (two Budget sessions among them), not data errors.
  Without them the NIFTY TEST profit is Rs 0.66 lakh. Expiry days are 21% of trades and about half the profit. Against
  a same-side buy at a random minute of the same day the edge is Rs 755 (LEARN) / 1,413 (TEST) per trade.
- **Wording corrected.** Calling R1 NIFTY "the" lead was selective: R5 on SENSEX is as close (p 0.058), and about 72
  looks were taken on the learning years before the six rules were chosen. The fair statement is "a consistent small
  continuation after a cross of yesterday's high or low, not significant".
- **Observation 1 corrected:** the 91-97% share uses a future built from the same option prices; on the printed index it
  is about 80%.
- **The tick box (T1) is weaker than shown.** In about 42% of cases the quotes simply had not changed half a second
  later, which is not proof of a fill. Realistic charges with interest and exercise tax are 1.0-1.3 points, against 1.36
  measured. "No LEAD" stands.
- The placebo does not match the volatility of the day, so "beats the placebo" is weak evidence on its own.
- Verdicts: E56 0 of 10 PASS stands; E57 S1 / S2 FAIL stands; T1 no LEAD stands. Observations 3 to 28 were not
  re-checked by the reviewer.

## Next

One recommended action: **keep the desk as it is** (expiry-day strangle, log only). If the founder wants one thing
watched, log the yesterday's-high / low cross (R1, NIFTY) forward at zero size in `fin1_shadow`: the frozen bar says
FAIL, so it does not enter by rule, and it needs about 150 more events (roughly one year) to settle.

What this study closes:

- Second-level and tick-level speed: closed again. The options are already the fastest thing we record.
- ICT sweep, fair value gap, order block: measured, no edge above cost.
- Parity and box arbitrage at retail latency: not real.

What stays open and needs data we do not have: the next-week option series (a same-day term structure is untestable on
this panel and tape), trade prints on the tape (fills at a displayed quote are untestable), and more than 3 days of
the cross-market tape.
