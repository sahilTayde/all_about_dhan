# Shadow analysts (log only)

Paper only. These analysts are registered with `@register` and listed in `config/analysts.yaml`
with `shadow: true`. Each tick they append an `ANALYST_VOTE` (`value`, `flag`, `confidence`,
`reasoning`) to the event audit log. The boss does not use them for entries. Trades with the
flag on match trades with these rows removed.

They read only data at this tick: 1-minute bars built from prints up to now, daily bars from
prior sessions, the book, and the option-chain snapshot on this tick. A missing input is a
skip (`value` empty), not a guessed number.

Replay and parity do not apply the wall-clock analyst timeout, so a slow machine cannot turn
one of these into an abstain that would not have happened on a quiet machine. The live paper
loop still uses `timeout_ms`.

## Features

| Analyst | What it logs | Config |
|---|---|---|
| `rng60_atr` | (high − low of the last 60 one-minute spot bars) / daily ATR14 from **prior** sessions. Also `expected_abs_move_pts` ≈ that ratio × ATR14 (the 60-minute range in points). | `features.vol.rng60.window_min` = 60 |
| `rng5_3m` | Range of the last 5 **completed** 3-minute bars / the same ATR14. The 3-minute bar still forming is left out. | `features.vol.rng5_3m.n_bars` = 5 |
| `rv30` | Annualised % realised volatility: sample stdev of 30 one-minute log returns × √(252 × 375) × 100. 375 minutes is 09:15–15:30. | `features.vol.rv30.window` = 30 |
| `er30` | Efficiency ratio over 30 one-minute moves: \|net move\| / sum of \|moves\|. Log only, confidence 0.2. | `features.vol.er30.window` = 30 |
| `br3_3m` | Average body/range of the last 3 completed 3-minute bars. Log only, confidence 0.2. | `features.vol.br3_3m.n_bars` = 3 |
| `chasing` | Flag when `rng60_atr` > threshold. | `shadow.chasing.threshold` = 0.376 |
| `high_vol` | Flag when `rv30` > threshold (percent). | `shadow.high_vol.rv30_min` = 10.06 |
| `minutes_since_prior_trade` | Minutes since the last open or close on this index in the book. Future timestamps are ignored. | (book state) |
| `day_direction` | Alignment: flag `CE` when spot > the day's open, `PE` when spot < the day's open, `FLAT` when equal. The open is the quote `day_open` when the tape has it, else the 09:15 open in the saved index OHLC, else the 09:15 bar. Tapes that arm at 09:30 have none of those, so the first bar is used and the log says `open_source: fallback_first_bar`. | `shadow.c5_trend_align.enabled` |
| `late_day_momentum` | Sign of the **completed** 14:44 close versus the prior session's close (+1 / −1 / 0). Before 14:45 the value is empty (`NOT_YET`). A later bar does not replace the 14:44 close. A missing prior close is `MISSING_PRIOR_CLOSE`. A prior close older than the previous weekday is `STALE_PRIOR_CLOSE`. Neither case invents a sign. | `shadow.c4_late_mom.enabled` |
| `expiry_day` | `dte` until **this index's** chain expiry (the tape `expiry`, the chain snapshot under `data/desk_intel/snapshots/{UND}/`, or a recorder row in `data/recon/option_chain/{YYYYMMDD}.jsonl` whose `underlying` matches). Calendars are not mixed: a NIFTY Tuesday is not applied to SENSEX or BANKNIFTY. If this index has a chain expiry, that date is used alone. NIFTY with no chain expiry falls back to `default_expiry_tuesdays()` (ends 2026-09-15) and then weekly Tuesdays, with one `EXPIRY CALENDAR EXHAUSTED` warning. Other indices with no chain expiry are skipped (`NO_INDEX_EXPIRY`). Flag is true when `dte` is 0. | this index's chain |
| `gex` | Dealer gamma exposure and the zero-gamma level. See below. | `shadow.gex.dealer_convention` |

Daily ATR14 is Wilder's ATR on daily bars that end before today's session. When the history is
only index closes, the day's high and low are the high and low of those closes. Today's session
is not in the ATR.

## Dealer GEX

Convention `long_calls_short_puts` (the default): dealers are assumed long calls and short puts,
so call GEX is positive and put GEX is negative.

For each strike inside the window (`shadow.gex.window_points`, default **±300** points of spot):

```
call = + gamma_ce × oi_contracts × lot_size × spot² × 0.01
put  = − gamma_pe × oi_contracts × lot_size × spot² × 0.01
```

Open interest on the tape is often in **shares** (about one lot times the contract count). If at
least 80% of the positive OI prints in the window divide evenly by the lot, those prints are
treated as shares and divided by the lot before the formula multiplies by the lot again. Otherwise
they are treated as contracts. A row may set `oi_unit` to `shares` or `contracts` and that wins.
The vote reasoning logs `oi_unit`, `strike_min`, `strike_max`, `window_points`, and `n_strikes`.

`gex` is the sum. `flag` / `regime` is `pos` when the sum is positive, `neg` when it is negative,
`flat` when it is zero. The zero-gamma level is the interpolated strike where the cumulative sum
(strikes from low to high) changes sign. If it never changes sign, zero-gamma is empty.

The chain is the tick's `wing_quotes` (or `engine.live_chain_rows` / a chain snapshot, dropping
any row timestamped after this tick). If gamma, OI, spot, or lot size is missing, the analyst
skips. It does not invent greeks.

`short_calls_long_puts` flips both signs. Any other convention string skips.

## Not implemented

Consolidation-box and sweep-and-reclaim event logging. There is no clean detector for those
events in this repo. `backtest_engine.fabio_proxy` is a strategy lean, not an event detector.
Do not add a new trading rule for them here.

## CSV after 20+ sessions

Point the audit log at a file (`EventSession(audit=EventAuditLog(path))`), then:

```bash
python scripts/export_shadow_audit.py --audit data/ledger/events.sqlite --out shadow_minutes.csv
```

One row per session date, minute (IST) and underlying. The last vote in that minute is kept.
Columns are each shadow value, its flag, `rng60_atr_expected_abs_move_pts`, and `gex_zero_gamma`.

## Deflated Sharpe

`analysts.eval.dsr(trade_pnls, n_trials)` is the Deflated Sharpe Ratio (Bailey & López de Prado,
2014) for one stream of trade P&Ls and a trial count. It does not place orders.
