# BACKTEST_SOD_EXAM — honesty slice + fill contract

**Team:** 06 · **Status:** `UNVALIDATED` / **NO_PROMOTE**  
**Founder close:** `./scripts/desk.sh close` (includes this exam).  
**CLI only:** `python -m desk_ml sod-exam` (last 5 weekdays from `desk.sh`; or pass `--days`).

**Where to read it (morning)**

1. Website: http://127.0.0.1:5173/pm → **Honesty exam (06)**
2. API: http://127.0.0.1:8000/paper/sod-exam
3. File: `data/recon/sod_exam_report.json` (gitignored). Mock fallback: `apps/web/public/mock/sod_exam_report.json`
4. This ticket: `teams/06_backtesting/docs/BACKTEST_SOD_EXAM.md`

write=false. Overlay unchanged. Spill rooms: `booking` (stall/against/unwind) vs `overlay` (ML HOLD/cut) vs `desk-clock` (15:16). One day is not a retune. Gate **not** `RESEARCH_READY_FOR_PROGRAMMING`.

**Replay gate:** `python -m desk_ml sod-exam --no-persist` must keep `overall_honesty` and `n_fill_contract_fail`. Room names may change. Do **not** recode overlay/booking from the exam. Booking ideas stay on `python -m desk_ml fix-first` / `paper-scalp --replay --no-write` until more NORMAL days agree.

See the live JSON for CLEAN / PEEKED / spill room. This file is the ticket home, not invented P/L.

**Run 2026-09-24 IST close (NIFTY dual-tape, write=false):** overall **CLEAN**. Fill-contract fails **0**. Peeked slices **0**. SOD closes: 18=17, 21=32, 22=27, 23=28, 24=33. Story every day: losses after fill (**booking:** stall/against/unwind) — watch booking on more **NORMAL** days; do not recode overlay tonight. 24 session_kind **EXPIRY** (not a retune sample). **NO_PROMOTE.** Win rate not claimed.

**Run 2026-09-20 IST (NIFTY dual-tape, write=false):** overall **CLEAN**. Fill-contract fails **0**. Peeked slices **0**. SOD closes: 16=1, 17=4, 18=5. Story on all three: losses after fill (stop/stall/cancel) — **watch overlay only if more NORMAL days agree**. 18 session_kind UNKNOWN (no nightly tag). **NO_PROMOTE.** Win rate not claimed.
