# DESK_SIGNAL_JSON v1 — the web app's signal contract

**Owner:** 05 (customer talk) + 04 (signal staging). **Layer:** `HYPOTHESIS` product format.
**Gate:** PAPER only. `NO_PROMOTE`. Execution refused. Not `RESEARCH_READY_FOR_PROGRAMMING`.

Origin: the founder's Gemini session format ([`gemini_signal/GEMINI_SIGNAL_LEARNING.md`](gemini_signal/GEMINI_SIGNAL_LEARNING.md))
hardened by 4 counsel rounds ([`COUNSEL_SIGNAL_FORMAT_2026-09-10.md`](../../00_orchestrator/docs/COUNSEL_SIGNAL_FORMAT_2026-09-10.md)).
Code: `packages/trading_agents_india/src/trading_agents_india/signal_schema.py`.

## Contract in one look

One JSON card per underlying per tick. The frontend renders **from JSON only** — the model
never writes customer prose directly (skill §87 principle).

| Field group | Content | Honesty rule |
|---|---|---|
| identity | `signal_id`, `supersedes_signal_id`, `analysis_timestamp_ist` | new card supersedes old; no ghost signals |
| decision | `BUY_CE`/`BUY_PE`/`WAIT`/`NO_TRADE` + `stage` + `status` | precedence enforced in code (below) |
| confidence | `confidence_score` 0–100 or **null** | evidence alignment, never win probability; null when `data_quality.score < 40` |
| underlying / option | spot, trend enum; option ltp, `premium_ohlc_present`, entry/stop/targets | anything unsourced is `null` — never 0, never guessed |
| technical_confirmation | vwap/ema/supertrend/price_action/volume as enums `ABOVE\|BELOW\|RECLAIM\|REJECT\|FLAT\|UNKNOWN` | no free-text indicator talk |
| order_flow | `{"status": "UNAVAILABLE"}` | Dhan has no aggressor-delta surface; constant until it does |
| cases | `bull_case`, `bear_case`, `primary_reason` | two-pass discipline (skill §49) |
| lifecycle | `invalidation`, `valid_until_ist`, `status` incl. `EXPIRED` | BUY_* without both ⇒ auto-downgrade to WAIT |
| compliance | paper_only, execution refused, NO_PROMOTE, layer, `win_rate_claim: null` | every card carries it |

## Decision precedence (enforced in `build_signal_json`)

1. `risk_veto` / stage `VETOED` / any veto ⇒ `NO_TRADE` + status `VETOED`. Hard override.
2. `BUY_CE`/`BUY_PE` requires **all** of: non-empty `invalidation`, future `valid_until_ist`,
   `premium_ohlc_present: true`. Missing any ⇒ downgrade to `WAIT` + named risk flag
   (`DOWNGRADED_MISSING_INVALIDATION` / `DOWNGRADED_EXPIRED_VALIDITY` / `DOWNGRADED_MISSING_PREMIUM_OHLC`).
3. `WAIT` ⇒ status `WATCHING`. `NO_TRADE` ⇒ `INACTIVE`.
4. `apply_expiry()` flips ACTIVE/WATCHING to `EXPIRED` past `valid_until_ist`.

**Premium tape (2026-09-10):** `trading_agents_india/premium_tape.py` now persists rolling
ATM 1m CE+PE bars per day under `data/recon/premium_tape/` from documented
`POST /charts/rollingoption` (one call per side), and the market-hours gather wires it into
tickets (`premium_bars`, `premium_ohlc_present`). When the gather runs `--live-chain`, BUY_*
cards can render and `MIX-DUAL-INDEX-MASTER` evaluates its full premium gate (same math as
the shadow harness). Without a live tape the old downgrade path still applies.

## v2 (needs founder ask + data)

- Position-aware execution plan (join paper ledger avg price → exit-zone coaching like the
  founder's Gemini session did for the 130.00 average).
- Real entry/stop/targets from premium structure once premium OHLC persists.
- `trigger_level` / `invalidation_level` numeric fills from level engine.
