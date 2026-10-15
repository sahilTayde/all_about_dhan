# LIVE SESSION

**As of (IST):** `2026-10-14T15:28:01+05:30`  
**Session (IST date):** `2026-10-14` · live_session=True  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE.** Orders refused. paper wr net=None% gross=None% (0/0 filled net). desk ₹570000.0 split across 1 tradable fill books (typical ₹570000.0/tradable; observe books ₹0).  
**Gross P/L:** ₹0.0 · **charges:** ₹0.0 (Groww+statutory VERIFY) · **Net P/L:** ₹0.0 · won ₹0 · lost ₹0 · desk equity ₹570000.0  (start ₹570000.0). Open 0.

SOD-on: one desk ticket (`MIX-DEFAULT-BUY`) + analyst room observe. Lab books never OPEN. Analyst CE/PE is logged MATCH/DISSENT/SPOKEN_PICKER_HOLD even when picker HOLD / observer VETO / desk ignores. A HOLD on ML-001 does **not** invent a wing.

## Today at a glance (gross vs net after Groww + statutory)

Filled 0 · cancelled 0 · W net 0 / L 0 · W gross 0 / L gross 0. TARGET hits 0 · TIME exits 0 (SUCCESS = TARGET only; TIME green is not SUCCESS).
wr **gross** None% · wr **net** None% (Groww+statutory VERIFY).
Capital split (₹570000.0 desk, SKIP/DI = ₹0 redistributed, min 10 lots/fill): `MIX-DEFAULT-BUY` ₹570000.0 · `ML-001` ₹0.0 · `ML-002` ₹0.0 · `ML-1` ₹0.0 · `MIX-ML-LOGIT` ₹0.0 · `MIX-ML-LOGIT-XR` ₹0.0 · `MIX-TV-EP-024` ₹0.0 · `MIX-ML-GREEKS` ₹0.0.
Gross ₹0.0 − brokerage ₹0.0 − GST ₹0.0 − STT ₹0.0 − exch ₹0.0 − SEBI ₹0.0 − stamp ₹0.0 = **net ₹0.0**.
SIDEWAYS skip (NEW opens only, HYPOTHESIS): n_skip_sideways=0 · REGIME_UNKNOWN_WAIT=0 · n_sideways_bars=0 · filled SL-hits=0.
Best ML book: `ML-001` rank 2 net ₹0.0 (filled 0).

## Ranked books (net ₹, all indices)

| rank | book | kind | filled | cancel | W | L | wr% net | wr% gross | gross ₹ | charges ₹ | **net ₹** | capital ₹ |
|------|------|------|--------|--------|---|---|--------|----------|---------|-----------|-----------|-----------|
| 1 | `MIX-DEFAULT-BUY` | DESK | 0 | 0 | 0 | 0 | None | None | None | None | 0.0 | 570000.0 |
| 2 | `ML-001` | ML | 0 | 0 | 0 | 0 | None | None | None | None | 0.0 | 0.0 |
| 3 | `ML-002` | ML | 0 | 0 | 0 | 0 | None | None | None | None | 0.0 | 0.0 |
| 4 | `ML-1` | ML | 0 | 0 | 0 | 0 | None | None | None | None | 0.0 | 0.0 |
| 5 | `MIX-ML-LOGIT` | ML | 0 | 0 | 0 | 0 | None | None | None | None | 0.0 | 0.0 |
| 6 | `MIX-ML-LOGIT-XR` | ML | 0 | 0 | 0 | 0 | None | None | None | None | 0.0 | 0.0 |
| 7 | `MIX-TV-EP-024` | LAB | 0 | 0 | 0 | 0 | None | None | None | None | 0.0 | 0.0 |
| 8 | `MIX-ML-GREEKS` | ML | 0 | 0 | 0 | 0 | None | None | None | None | 0.0 | 0.0 |

## Open tickets (last updated desc — strike / limit / target / SL / CE|PE / status)

| model | und | CE/PE | strike | limit | **target** | stop | last_ltp | filled | status | regime | updated |
|-------|-----|-------|--------|-------|-----------|------|----------|--------|--------|--------|---------|
| — | — | — | — | — | — | — | — | — | none | — | — |

## Closed tickets (last — last updated desc — strike / entry / **exit** / target / SL / reason)

| model | und | side | strike | entry | **exit** | target | stop | reason | target_hit | pnl ₹ | result | regime | updated |
|-------|-----|------|--------|-------|----------|--------|------|--------|------------|-------|--------|--------|---------|
| `PX_B2` | NIFTY | PE | 22650.0 | 139.15 | 114.7 | None | None | `EXIT` | False | -16239.18 | LOSS | — | 2026-10-14T09:44:00+05:30 |
| `PX_EP010` | NIFTY | CE | 22750.0 | 142.9 | 146.1 | None | None | `TARGET` | False | 1672.87 | SUCCESS | — | 2026-10-14T09:46:00+05:30 |
| `PX_ORB_A` | NIFTY | CE | 22750.0 | 153.0 | 130.95 | None | None | `STOP` | False | -14715.69 | LOSS | — | 2026-10-14T09:54:00+05:30 |
| `PX_R07` | NIFTY | PE | 22650.0 | 139.55 | 199.2 | None | None | `EXIT` | False | 38267.44 | SUCCESS | — | 2026-10-14T13:19:00+05:30 |
| `PX_R07` | NIFTY | CE | 22650.0 | 148.0 | 130.45 | None | None | `EXIT` | False | -11787.57 | LOSS | — | 2026-10-14T14:08:00+05:30 |

### Closed justification (SUCCESS=TARGET / TIME / LOSS / CANCEL)

- `PX_B2` NIFTY PE LOSS `EXIT`: paper_extra B2: lab rule signal, ATM, entry next-minute open. Lab B2: NIFTY index stop / rule exit (stress.py path) NO_PROMOTE.
- `PX_EP010` NIFTY CE SUCCESS `TARGET`: paper_extra EP-010: lab rule signal, ATM, entry next-minute open. TV EP-010 port: own exit signal or stop NO_PROMOTE.
- `PX_ORB_A` NIFTY CE LOSS `STOP`: paper_extra I1_ORB:ORB_A:T2: lab rule signal, ATM, entry next-minute open. Lab I1_ORB:ORB_A:T2: index stop / target / time per lab rule (T2 variant) NO_PROMOTE.
- `PX_R07` NIFTY PE SUCCESS `EXIT`: paper_extra R07: lab rule signal, ATM, entry next-minute open. Lab R07 (combos): index path exit NO_PROMOTE.
- `PX_R07` NIFTY CE LOSS `EXIT`: paper_extra R07: lab rule signal, ATM, entry next-minute open. Lab R07 (combos): index path exit NO_PROMOTE.

## Seen but not taken / cancelled (why)

Saw a CE/PE but did not OPEN, or OPENED then CANCELLED. Not live orders. Last-3 PUT/CE impulse can TREND; 15m chop skip stays when last-3 is also chop.

- BANKNIFTY: 15m TREND (er_vwap_ema_vol_rsi, ER=0.5698). Last-3 1m closes [55378.1, 55378.1, 55378.1] net=0.0 impulse=none. Dealer HOLD; logit side=SKIP. ITM bin CE 55100.0 votes=['CE_PREMIUM_UP', 'CE_SHORT_COVER'] vs PE 55700.0 votes=['PE_PREMIUM_UP', 'PE_SHORT_COVER'] reason=itm_bin_pe_confirm. Two ITM-leg votes can TREND without three INDEX 1m bars.
- NIFTY: 15m TREND (itm_bin_ce_confirm, ER=0.4355). Last-3 1m closes [22625.15, 22625.15, 22625.15] net=0.0 impulse=none. Dealer HOLD; logit side=SKIP. ITM bin CE 22450.0 votes=['CE_PREMIUM_UP', 'PE_PREMIUM_DOWN', 'CE_SHORT_COVER'] vs PE 22850.0 votes=['PE_DELTA_MORE_ITM', 'PE_LONG_UNWIND'] reason=itm_bin_ce_confirm. Two ITM-leg votes can TREND without three INDEX 1m bars.
- SENSEX: 15m TREND (er_vwap_ema_vol_rsi, ER=0.459). Last-3 1m closes [72807.04, 72807.04, 72807.04] net=0.0 impulse=none. Dealer HOLD; logit side=PE. ITM bin CE 72500.0 votes=['CE_PREMIUM_UP', 'PE_PREMIUM_DOWN'] vs PE 73100.0 votes=['PE_DELTA_MORE_ITM'] reason=itm_bin_wait. Two ITM-leg votes can TREND without three INDEX 1m bars.

| kind | model | und | seen CE/PE | reason | why | regime | last-3 impulse | updated |
|------|-------|-----|------------|--------|-----|--------|----------------|---------|
| — | — | — | — | none | — | — | — | — |

## ITM CE / PE bin (three charts)

Three charts: INDEX + ITM CE + ITM PE. Keep this bin during paper trades. ITM PE volume/delta/OI-up-with-premium + CE selling/premium down can TREND without three INDEX 1m bars. Missing OI/vol/delta is DATA_INSUFFICIENT, never invented. Roll the bin when booked ITM becomes ATM/OTM. NO_PROMOTE.

| und | index | CE strike | CE $ | CE vol | CE OI | PE strike | PE $ | PE vol | PE OI | PE votes | CE votes | side | reason | missing |
|-----|-------|-----------|------|--------|-------|-----------|------|--------|-------|----------|----------|------|--------|---------|
| NIFTY | 22625.15 | 22450.0 | 242.8 | 4636905.0 | 431275.0 | 22850.0 | 280.3 | 16634475.0 | 402935.0 | PE_DELTA_MORE_ITM,PE_LONG_UNWIND | CE_PREMIUM_UP,PE_PREMIUM_DOWN,CE_SHORT_COVER | CE | `itm_bin_ce_confirm` | — |
| BANKNIFTY | 55378.1 | 55100.0 | 830.95 | 289080.0 | 101190.0 | 55700.0 | 724.25 | 932970.0 | 84330.0 | PE_PREMIUM_UP,PE_SHORT_COVER | CE_PREMIUM_UP,CE_SHORT_COVER | PE | `itm_bin_pe_confirm` | — |
| SENSEX | 72807.04 | 72500.0 | 401.15 | 19845360.0 | 476620.0 | 73100.0 | 482.5 | 51229300.0 | 279460.0 | PE_DELTA_MORE_ITM | CE_PREMIUM_UP,PE_PREMIUM_DOWN | — | `itm_bin_wait` | — |

Comments (HYPOTHESIS, not a promote):

## Leaderboard (book × index, ranked by net ₹)

| rank | book | underlying | n | wins | losses | wr% net | wr% gross | pts | gross ₹ | charges ₹ | **net ₹** |
|------|------|------------|---|------|--------|--------|----------|-----|---------|-----------|-----------|
| — | — | — | 0 | 0 | 0 | — | — | — | — | — | — |

LIVE SESSION: dual-tape ticks for this IST date only. Not fills. Rank ≠ promote. `MIX-ML-LOGIT*` trains on INDEX 3m before the ATM session. `win_rate` net = filled hit rate after Groww+STT; `win_rate_gross` is before charges. Not a promote. `MIX-TV-EP-024` SMA lab is KEEP_ALL, not customer default.

## Index / ML notes (HYPOTHESIS paper only)

- MIX-ML-GREEKS: 0 filled tickets — Dhan greeks/IV missing most of the session. Adjustment: keep the book; require live chain from 09:15 IST. Do not retune ml001-v1.
- NIFTY: no filled paper tickets today.
- BANKNIFTY: no filled paper tickets today.
- SENSEX: no filled paper tickets today.
- Rank is after Groww ₹20/order × 2 + GST 18% on brokerage + STT 0.15% sell premium (VERIFY). Cannot CANDIDATE. NO_PROMOTE. INDEX 1m SIDEWAYS_HOLD is HYPOTHESIS paper skip of NEW opens only.

## Analyst model signals (room vs picker — ignored votes still logged)

Analyst room: FOLLOWS / logit / XR / greeks / STRAT (spoken) / TV lab. SOD fills MIX-DEFAULT-BUY only. MATCH / DISSENT / SPOKEN_PICKER_HOLD / SILENT even when picker HOLD, observer VETO, or desk ignores — shadow tape for later tune, not extra Monday capital. NO_PROMOTE.
Logged rows: 2000.

| source | vs picker | n |
|--------|-----------|---|
| `MIX-TV-EP-024` | DISSENT | 4 |
| `MIX-TV-EP-024` | MATCH | 82 |
| `MIX-TV-EP-024` | SILENT | 17 |
| `MIX-TV-EP-024` | SPOKEN_PICKER_HOLD | 231 |
| `STRAT-003` | DISSENT | 1 |
| `STRAT-003` | MATCH | 45 |
| `STRAT-003` | SILENT | 188 |
| `STRAT-003` | SPOKEN_PICKER_HOLD | 100 |
| `follows` | DISSENT | 6 |
| `follows` | MATCH | 70 |
| `follows` | SILENT | 136 |
| `follows` | SPOKEN_PICKER_HOLD | 121 |
| `greeks` | MATCH | 2 |
| `greeks` | SILENT | 323 |
| `greeks` | SPOKEN_PICKER_HOLD | 8 |
| `logit` | DISSENT | 41 |
| `logit` | MATCH | 43 |
| `logit` | SILENT | 25 |
| `logit` | SPOKEN_PICKER_HOLD | 224 |
| `xr` | MATCH | 7 |
| `xr` | SILENT | 324 |
| `xr` | SPOKEN_PICKER_HOLD | 2 |

Latest spoken (still analysts when observer VETO / picker HOLD):

| source | side | vs picker | picker | observer | ignored |
|--------|------|-----------|--------|----------|---------|
| `follows` | SILENT | SILENT | HOLD/— | PASS | False |
| `logit` | PE | SPOKEN_PICKER_HOLD | HOLD/— | PASS | True |
| `xr` | SILENT | SILENT | HOLD/— | PASS | False |
| `greeks` | SILENT | SILENT | HOLD/— | PASS | False |
| `STRAT-003` | CE | SPOKEN_PICKER_HOLD | HOLD/— | PASS | True |
| `MIX-TV-EP-024` | CE | SPOKEN_PICKER_HOLD | HOLD/— | PASS | True |

## Models / steps

| id | closed | W | L | wr% net | wr% gross | equity ₹ | capital ₹ | last run |
|----|--------|---|---|--------|----------|----------|-----------|----------|
| `MIX-DEFAULT-BUY` | 0 | 0 | 0 | None | None | 570000.0 | 570000.0 | `2026-10-14T15:28:01+05:30` |
| `ML-001` | 0 | 0 | 0 | None | None | 0.0 | 0.0 | `2026-10-14T15:28:01+05:30` |
| `ML-002` | 0 | 0 | 0 | None | None | 0.0 | 0.0 | `2026-10-14T15:28:01+05:30` |
| `ML-1` | 0 | 0 | 0 | None | None | 0.0 | 0.0 | `2026-10-14T15:28:01+05:30` |
| `MIX-ML-LOGIT` | 0 | 0 | 0 | None | None | 0.0 | 0.0 | `2026-10-14T15:28:01+05:30` |
| `MIX-ML-LOGIT-XR` | 0 | 0 | 0 | None | None | 0.0 | 0.0 | `2026-10-14T15:28:01+05:30` |
| `MIX-TV-EP-024` | 0 | 0 | 0 | None | None | 0.0 | 0.0 | `2026-10-14T15:28:01+05:30` |
| `MIX-ML-GREEKS` | 0 | 0 | 0 | None | None | 0.0 | 0.0 | `2026-10-14T15:28:01+05:30` |

## Mistakes (paper-param nudge only; no MIX write)

Paper params: stop_frac=0.38 target_frac=0.55 hold_bars=9 skip_sideways=True regime_er_max=0.3. production_params_written=false.
- session params frozen; nudge runs post-market: python -m desk_ml nudge-params

## DATA_INSUFFICIENT

- DATA_INSUFFICIENT: NIFTY last-21d INDEX+ATM tape join empty
- DATA_INSUFFICIENT: NIFTY ATM days ['2026-09-17', '2026-09-18', '2026-09-21', '2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01', '2026-10-05', '2026-10-08', '2026-10-09', '2026-10-12', '2026-10-13', '2026-10-14'] have no INDEX 1m (merged INDEX span 2021-09-06→2026-09-16)
- DATA_INSUFFICIENT: BANKNIFTY last-21d INDEX+ATM tape join empty
- DATA_INSUFFICIENT: BANKNIFTY ATM days ['2026-09-17', '2026-09-18', '2026-09-21', '2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01', '2026-10-05', '2026-10-08', '2026-10-09', '2026-10-12', '2026-10-13', '2026-10-14'] have no INDEX 1m (merged INDEX span 2021-09-06→2026-09-16)
- DATA_INSUFFICIENT: SENSEX last-21d INDEX+ATM tape join empty
- DATA_INSUFFICIENT: SENSEX ATM days ['2026-09-17', '2026-09-18', '2026-09-21', '2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01', '2026-10-05', '2026-10-08', '2026-10-09', '2026-10-12', '2026-10-13', '2026-10-14'] have no INDEX 1m (merged INDEX span 2021-09-06→2026-09-16)
- DATA_INSUFFICIENT: no OPTIDX 1m bars in last 21 calendar days

## How to watch

```bash
python -m desk_ml paper-scalp --replay --source dual-tape --live-session
python -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 2 --max-ticks 0
touch data/recon/ml_paper_scalp_STOPPED.flag
```

Dashboard JSON/MD rewrite **every 2s** from the last tick. Dual-tape Dhan poll stays **45s** (optionchain rate-limit). Tick ≠ 2s on purpose.

JSON: `data/recon/ml_paper_dashboard.json` (gitignored) · mock: `apps/web/public/mock/ml_paper_dashboard.json`  
UI: `/pm` and `/desk` (existing Vite; do not restart npm). API: `GET /paper/ml-books`.

KEEP_ALL STRAT-001–014. No STRAT-015+.

