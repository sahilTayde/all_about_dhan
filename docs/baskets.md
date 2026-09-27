# Strategy baskets (boss basket selector)

**Shadow only.** The selector ranks and weights strategy cards for the day's regime and writes
that to a log. It places no orders, and nothing in the order path reads its output. It is **off
by default**. Code: `packages/boss/src/boss/basket.py`. Tests: `packages/boss/tests/test_basket.py`.

## Switching it on and off

| Control | Where | Effect |
|---|---|---|
| Feature flag | `basket_selector.enabled` in `config/event_path.yaml` (default `false`) | On = the boss runs the selector. Needs `USE_EVENT_BUS=1` (the boss only exists on the event path). |
| Env override | `USE_BASKET_SELECTOR=1` / `0` | Overrides `enabled` for one process. |
| Founder switch | the file `data/founder/basket_selector_off` | While it exists the selector never runs, even if enabled. It is checked at session start and on every tick. `python -m boss.basket off` creates it, `on` removes it, `status` shows both. |

With the flag off, the boss gets no basket object and runs exactly the code it ran before. The
test `test_off_by_default_replay_is_byte_identical_and_on_changes_no_trade` replays the committed
fixture day three ways: the monolith, the event path with the flag off, and the event path with
the selector on. The closed trades, open tickets, skip counts and event counts must match byte for
byte.

## When the boss calls it

For each underlying in an activatable basket:

1. **Pre-open.** Before the boss's first decision of the day, labels come only from prior-session
   daily closes (`preopen_days`). Rows dated today or later are dropped.
2. **Regime change.** Each time a 1-minute bar closes, labels are recomputed from today's
   **closed** bars (the minute still forming is never used). A row is written only when the
   labels change. Until `intraday_bars` closed bars exist, the pre-open trend and vol labels
   are kept.

Labels: `trend|chop` (Kaufman efficiency ratio against `*_trend_er_min`), `high_vol|low_vol`
(annualised realised vol against `*_high_vol_pct`), and `expiry|non_expiry` (session weekday
against the instrument's `expiry_weekday`). A label that cannot be computed is `unknown`, and then
every strategy gets weight 0 with the reason `regime_unknown`. The regime key is
`<trend>.<vol>.<expiry>`, for example `trend.low_vol.non_expiry`.

## Output: `data/shadow/basket/<day>.jsonl` (gitignored)

One JSON object per line: `day`, `ts`, `time_ist`, `underlying`, `market`, `trigger`
(`pre_open` | `regime_change`), `regime` (labels, key, source and the inputs used), `basket`, `lab`
(which lab file was loaded, rejected entries, error), `shadow: true`, `places_orders: false`.

`basket.strategies` is ranked: selected strategies first (by the lab's `rank`, then weight, then
id), then weight-0 strategies by id. Each entry has `id`, `weight`, `raw_weight`, `rank` (null
when the weight is 0), `reason`, and `score`.

| reason | weight 0 because |
|---|---|
| `selected` | (not 0) passed every gate |
| `basket_parked` | the basket has `activatable: false` (forex) |
| `regime_unknown` | a regime label could not be computed |
| `unscored_regime` | the card has no score for this regime key |
| `status_watch` / `status_parked` / `status_parked_for_forex_test` | the status for this regime is not `active_candidate` |
| `failed_min_trades` / `failed_pf` / `failed_net_pnl` / `failed_dsr` | below the `selection` gates |
| `zero_weight` | the lab gave weight 0 |

If the selected weights add up to more than `selection.max_total_weight`, they are scaled down
proportionally and rounded down to 1e-6, so the total never exceeds the cap. Rows contain no
wall-clock values, so the same inputs always produce the same bytes. The live paper loop re-replays
the session, so a row that is already in the file is never appended a second time.

## Basket files: `config/baskets/<market>.yaml`

`india.yaml` (NIFTY, SENSEX) is `activatable: true`. `forex.yaml` is `activatable: false`: it loads
and validates, but the boss never attaches it to an underlying and the selector gives it weight 0.

- `instruments.<SYMBOL>`: `exchange`, `lot_size`, `expiry_weekday` (`MON`..`SUN` or null),
  `session {open, close, tz}`, `tick_size`. Every value carries a `Source:` comment. A value that
  still needs checking is marked `TODO(verify)`, and an unknown value is null, not a guess. The
  paper engine does not read these values; it still gets its lot size from the Dhan instrument master.
- `selection`: `max_total_weight`, `min_trades`, `min_pf`, `min_dsr` (0..1), `require_positive_net`.
- `regime`: `preopen_days`, `preopen_trend_er_min`, `preopen_high_vol_pct`, `intraday_bars`,
  `intraday_trend_er_min`, `intraday_high_vol_pct`.
- `lab_scores`: path of the lab refresh file (relative to the repo root).
- `strategies`: strategy cards. In yaml, `scores` may be empty (the card is then weight 0 until the lab scores it).

## Strategy card

```yaml
id: MIX-EXAMPLE            # ^[A-Z][A-Z0-9_.-]{1,63}$ ; never STRAT-015+ (docs/FILE_CREATION.md)
source: {kind: trader | paper, ref: "video id / paper / lab run"}
markets: [NIFTY, SENSEX]   # must be instruments of the basket
adaptations:               # per-market parameter changes (keys must be in markets)
  SENSEX: {stop_frac: 0.35}
rules:                     # all five, each a non-empty mapping of exact parameters
  entry: {...}
  exit: {...}
  strike: {...}
  sizing: {...}
  skip: {...}
param_ranges:              # the values that were actually tested
  stop_frac: [0.30, 0.35, 0.40]
scores:                    # keyed by regime key; every field required
  trend.low_vol.non_expiry:
    {net_pnl: 41250.5, pf: 1.42, trades: 64, win_rate: 0.53, dsr: 0.96, weight: 0.4, rank: 1, status: active_candidate}
notes: ""                  # optional
```

`status` is one of `active_candidate`, `watch`, `parked`, `parked_for_forex_test`. Only
`active_candidate` can get a non-zero weight. Field ranges: `pf >= 0`, `trades` is an integer
`>= 0`, `win_rate` and `dsr` are in 0..1, `weight >= 0`, `rank` is an integer `>= 1`. Every number
must be finite. Unknown keys are rejected, so a typo cannot silently drop a rule.

## Lab refresh: `data/lab/basket_india.json` / `data/lab/basket_forex.json` (gitignored)

The lab writes this file, and the next session picks it up with no code change:

```json
{
  "schema_version": 1,
  "market": "india",
  "generated_at": "2026-09-26T18:00:00+05:30",
  "source": "scripts/lab/<script> run id",
  "strategies": [ { "...": "full strategy card, scores required" } ]
}
```

- A lab card **replaces** the yaml card with the same `id`. A new `id` is added.
- **Whole-file rejects:** the file is unreadable or not JSON, uses `NaN`/`Infinity` (cap `pf`
  before writing), has the wrong `schema_version` or `market`, is missing `generated_at` or
  `source`, or `strategies` is not a list. The selector then uses the yaml cards only, and the
  error is recorded in each row's `lab.error`.
- **Per-entry rejects:** a malformed card, an unscored card (no `scores`, or a score missing a
  field), a market outside the basket, or a duplicate id. The rest of the file is still used, and
  the rejects are listed in `lab.rejected`.

Check a file before shipping it: `python -m boss.basket validate data/lab/basket_india.json`
(exit 1 on any reject).

## Parity on the recorded Sep 17–25 tapes (local only)

The dual-tape files are not in git, so CI proves parity on the committed fixture day. On a machine
that has them, run the event-path parity with the selector on (it must still print `PARITY`, with
the same totals as the flag-off run):

```bash
USE_BASKET_SELECTOR=1 python -m desk_ml.event_parity --since 2026-09-17 --until 2026-09-25 --underlyings NIFTY
```
