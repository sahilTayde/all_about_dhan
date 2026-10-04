# Shadow logging

Paper replay writes one JSON object per line to `data/shadow/<YYYY-MM-DD>.jsonl`. The directory is created at runtime and gitignored. Nothing in this file is an order.

V2 shadow launcher (optional, paper only) writes a **separate** book under `data/shadow/v2/YYYY-MM-DD/` (`decisions.jsonl`, `pnl.jsonl`, `compare.json`). It loads the founder-approved paper/shadow basket (`config/v2/baskets/approved_paper_shadow.yaml` or a dated file) plus `config/v2/exits/defaults.yaml`. Rows are `ENTER` or an explicit V2 abstain (`PENDING_LAB`, `NO_BASKET`, `NO_CLOSED_BAR`, …) — not HOLD-only. It does not replace this legacy file and does not own the live paper book. See `packages/shadow/README.md`.

Default is on. Set `SHADOW_LOG=0` or `engine.shadow_log = False` to skip the write. A crash inside the shadow code is logged and the paper engine continues with the same ticket.

One row per index per IST minute (the first decision of that minute). Later ticks in the minute still update the order-flow snapshot window; they do not add another row.

## Row (`schema`: `shadow-v1`)

| Field | Meaning |
| --- | --- |
| `ts` | Unix seconds of the decision tick |
| `minute_ist` | `YYYY-MM-DDTHH:MM` in IST |
| `index` | `NIFTY`, `BANKNIFTY`, or `SENSEX` |
| `live` | Picker decision that sized the paper ticket: `action`, `side`, `detail`, `skip` |
| `shadow` | Same fields from the picker with MIX-ML-LOGIT (`logit`) and XR (`xr`) removed |
| `agree` | True when `live` and `shadow` have the same `action` and `side` |
| `logit_p` | MIX-ML-LOGIT sigmoid probability. The live vote still uses the CE/PE/SKIP lean, not this number |
| `hari` | S1. `em30` is the next-30-minute expected move in index points. `rv_5`, `rv_30`, `rv_120` are sums of squared 1-minute log returns. `rv_prev_day` is the same for the previous session when those closes were passed in. `fitted: false` means `config/shadow/hari.yaml` still has placeholder coefficients |
| `order_flow` | S2. `score` in [-1, 1]: near-the-money CE minus PE, open-interest change plus volume change, over the last 1–5 chain snapshots, divided by the sum of absolute changes. Null when the tape has no OI or volume |
| `volsize_7b` | `shadow_lots = clip(round(25 * 27.4 / em30), 5, 25)` next to `live_lots`. Null shadow lots when `em30` is missing or not positive |

`hari.em30 = spot * sqrt(max(forecast variance, 0))`. Forecast variance is `intercept + rv_5 * b5 + rv_30 * b30 + rv_120 * b120 + rv_prev_day * bd` from `config/shadow/hari.yaml`. A missing window is skipped, not filled in.
