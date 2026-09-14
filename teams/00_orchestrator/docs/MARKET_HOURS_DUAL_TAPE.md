# Market-hours dual tape (INDEX + ATM CE/PE)

**Status:** PAPER gather + deterministic desk notes · **NO_PROMOTE** · not `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** refused (`ExecutionClient` SafeMode). **LLM:** none on this path ([`TOKEN_ML_STRATEGY.md`](../../../docs/TOKEN_ML_STRATEGY.md)).  
**Retune:** no production param writes ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)).  
**Customer default:** `MIX-DEFAULT-BUY` unchanged. KEEP_ALL. STRAT catalog untouched.

This is **not** the old LLM `market-hours` paper_ops loop.

---

## Why two tapes

Each tick stores **index** (LTP + last 1m bar) beside **ATM CE LTP** and **ATM PE LTP**. A dealer then checks whether premium moved the way spot did. When it did not, we **HOLD** and do not open a new paper CE/PE.

---

## How to run

```bash
cd /path/to/all_about_dhan
# Closed market / dry (cache + fixtures; finite ticks do not sleep)
python -m trading_agents_india dual-tape --simulate --max-ticks 2

# After-hours or live session: try Dhan (stale LTP is ok). 0 = until stop flag.
python -m trading_agents_india dual-tape --live-chain --tick-seconds 45 --max-ticks 0
```

Default tick is **45s** (clamp 30–300). Prefer 30–45s; full option-chain still respects Dhan’s unique-request budget (desk-intel full chain is **3m**; this loop reuses `watch_chain` / rolling ATM, not a 30s full-chain spray).

**Stop:** `touch data/recon/paper_dual_tape_STOPPED.flag` — the loop exits on the next tick.  
**Running:** `data/recon/paper_dual_tape_RUNNING.flag` (PID + how-to-stop).  
**Do not restart npm** for this path.

### Legacy `paper_ops_STOPPED.flag`

That flag (2026-09-10) halted the **LLM market-hours / paper_ops** stack. Founder asked 2026-09-14 to **start paper data**. Dual-tape is a **new** loop: no LLM, no Dhan orders. The old flag is **documented, not deleted**. Dual-tape only honours `paper_dual_tape_STOPPED.flag`.

---

## Fields stored

JSONL + `latest.json`: `data/recon/paper_watch/DUAL-TAPE/`  
Human notes: `data/recon/paper_watch/DUAL-TAPE/YYYY-MM-DD.notes.md`  
SQLite: `dual_tape_ticks` in `data/knowledge/trading_agents_india.sqlite` (do not git-add).  
Ledger event: `DESK_DIVERGENCE` on the paper ledger JSONL.

Per underlying (NIFTY, BANKNIFTY, SENSEX):

| Field | Meaning |
|-------|---------|
| `index_ltp` | Last INDEX close / chain `last_price` if that is what we have |
| `index_1m` | Last 1m `{ts,open,high,low,close,volume}` or null |
| `atm_ce_ltp` / `atm_pe_ltp` | ATM weeklies from rollingoption and/or chain |
| `atm_strike`, `expiry` | From chain parse when present |
| `pcr_oi`, `strike_count`, `chain_lean`, `chain_spot` | Compact chain — already in gather |
| `atm_*_iv` / `delta` / `gamma` | **null unless Dhan/parser sent them** — never invented |
| `index_delta`, `ce_delta`, `pe_delta` | vs previous persisted tick |
| `stale`, `wrong_strike`, `data_gaps`, `*_source` | Honesty flags |

---

## CE/PE vs index (desk persona)

Deterministic, first. **No LLM.**

| Case | Action |
|------|--------|
| Index **down**, PE **not up** and/or CE **not down** | `PREMIUM_DIVERGENCE` → **HOLD**, no new paper CE/PE. Reason like a dealer: IV crush, event, stale quote, wrong strike. |
| Index **up**, ATM CE **follows up** | `BUY_CE_CONFIRM` — paper **note** only; not a fill; not a customer MIX change. |
| Index **down**, PE up and CE down | `BUY_PE_CONFIRM` — same: note only. |
| After hours / frozen LTP | `STALE` → HOLD. Next real load **09:15 IST**. |
| Missing ATM / jumped sheet + missing LTP | `WRONG_STRIKE` → HOLD. |
| Missing prints | `DATA_INSUFFICIENT` → HOLD. |

---

## Coalition

- **03** INDEX 1m + rolling ATM + optionchain (existing hooks).  
- **05** dealer note (`desk_divergence.py`).  
- **04** MIX-DEFAULT-BUY not rewritten.  
- **06** no auto-retune from these ticks.  
- **07** no npm. **08** unit tests on the judge + loop.

```text
Accepted: founder start of paper dual-tape; 45s poll; persist compact JSON/sqlite.
Rejected: live Dhan orders; blocking LLM; auto-write production params; new STRAT-015; promote.
UNKNOWN: whether after-hours Dhan still returns last LTP on this token day.
```
