# Strategy baskets (basket selector)

**Shadow only, off by default, self-contained.** The selector ranks and weights strategy cards for
the current market regime and writes the result to a log. It places no orders, and nothing in the
engine, boss, desk or order path reads its output.

It is a separate module that does not edit any existing file:

| Path | What |
|---|---|
| `packages/strategy-basket/src/strategy_basket/basket.py` | card schema, loaders, selector, shadow log, bus wiring, CLI |
| `packages/strategy-basket/tests/` | tests (`conftest.py` puts `src` on the path until the package is installed) |
| `config/baskets/selector.yaml` | flags: `enabled` (default `false`), founder off file, paths |
| `config/baskets/india.yaml`, `config/baskets/forex.yaml` | instruments, selection gates, strategy cards |
| `data/shadow/basket/` | runtime output, lab refresh files and the founder off file (gitignored with `data/shadow/`) |

## Regime labels come from the regime service

The selector does not compute regimes. It uses the regime service's minute labels
(`desk_ml.regime`, PR #21; thresholds in `config/regime.yaml`). Those labels are built from
completed 1-minute bars only, one bar at a time. The regime service publishes a `REGIME_LABEL`
event (`scope: minute`) whenever an index's label changes. It does this while the boss handles
that tick, so the label is on the bus before the boss decides.

The basket key is `<primary>.<vol>.<expiry>`, taken straight from that label:

| Part | Values | From the label |
|---|---|---|
| primary | `trend_up`, `trend_down`, `range`, `unknown` | `primary` (`unknown` = labeller warm-up) |
| vol | `vol_expansion`, `vol_compression`, `vol_normal` | `vol`; `vol_normal` when the label has neither (this includes warm-up) |
| expiry | `expiry_day`, `non_expiry_day` | `expiry_day` |

In the terms of the original spec: `trend_up` and `trend_down` are trend, `range` is chop,
`vol_expansion` is high vol, and `vol_compression` is low vol.

The selector runs at two moments:

1. **Pre-open.** On an index's first tick of the day, before the boss's first decision, the
   selector writes one row. At that point only the expiry flag is known. It comes from the same
   expiry calendar the regime labeller is given (`desk_ml.regime.shadow._expiry_dates`). The key
   is `unknown.vol_normal.<expiry>`, which is what the labeller itself reports while it warms up.
   A strategy meant for the open can be scored under that key.
2. **Regime change.** On each minute `REGIME_LABEL` whose basket key differs from the last row's
   key. If only the label list changes (for example `gap_day`) and the key does not, no row is written.

**No look-ahead:**
- Labels are causal, per the regime service.
- The selector also refuses any label for a minute that had not closed at the tick it arrived on
  (`label_ts + 60 > tick ts`). Such a label is logged as an error and produces no row.
- A lab file whose scores used the session day or later is ignored for that session (see
  `data_until` in the lab file section). This is the same rule the regime service applies to its
  saved weight state.
- Tests check that every row's minute closed before its tick, and that changing the fixture after
  tick 500 leaves every earlier row unchanged.

If `config/regime.yaml` has `mode: off`, no minute labels are published. The selector then writes
only the pre-open rows (`labels_seen` in the summary stays 0).

## Hooking it in: one line (not applied yet)

This PR does not edit the boss or `EventSession`. When the main build is ready, the integration
is one call at the end of `EventSession.attach` in `packages/desk-ml/src/desk_ml/event_path.py`,
after `self.boss = Boss(...)` (plus its import):

```python
        from strategy_basket import attach_from_settings
        self.basket_bus = attach_from_settings(self.bus, engine, self.steps)
```

`attach_from_settings` returns `None` when the feature is off or the founder switch is set, and
then it subscribes nothing. When it is on, it subscribes to `MARKET_TICK` (priority 15: after the
desk's mark-to-market at 10, before the boss at 20) and to `REGIME_LABEL`. It never publishes,
and it catches its own errors, so it cannot add to `bus.errors` or change an entry. Merging it
also needs `packages/strategy-basket` added to `.cursor/install.sh` and the uv workspace; after
that, the tests' `conftest.py` can be deleted.

Until the hook lands, `strategy_basket.BasketEventSession(...)` is an `EventSession` with that
line applied. Replays and tests use it:
`replay_paper_scalp(..., event_session=BasketEventSession())`.

## Switching it on and off

| Control | Where | Effect |
|---|---|---|
| Feature flag | `enabled` in `config/baskets/selector.yaml` (default `false`) | On = the selector runs on the event path (`USE_EVENT_BUS=1`). |
| Env override | `USE_BASKET_SELECTOR=1` / `0` | Overrides `enabled` for one process. |
| Founder switch | the file `data/shadow/basket/FOUNDER_OFF` | While it exists the selector never runs, even if enabled. It is checked at session start and on every call. `python -m strategy_basket off` creates it, `on` removes it, `status` shows both. |

With the flag off, nothing from this module runs at all. The test
`test_off_by_default_replay_is_byte_identical_and_on_changes_no_trade` replays the committed
fixture day five ways:
- the monolith;
- the event path from main;
- `BasketEventSession` with default settings (off);
- `BasketEventSession` with the selector on, twice.

The closed trades, open tickets and skip counts must match byte for byte, and the event counts
must be identical.

## Output: `data/shadow/basket/<day>.jsonl`

One JSON object per line with these fields:
- `day`, `ts` (the tick it was decided on), `time_ist`, `underlying`, `market`;
- `trigger` (`pre_open` | `regime_change`);
- `regime`: `primary`, `vol`, `expiry`, `key`, `source` (`pre_open` | `regime_service`),
  `label_ts` (the labelled minute), `labels`, `version`, `features`;
- `basket`;
- `lab`: which lab file, whether it was used or ignored and why, rejected entries, error;
- `shadow: true`, `places_orders: false`.

`basket.strategies` is ranked. Selected strategies come first (by the lab's `rank`, then weight,
then id), then weight-0 strategies by id. Each entry has `id`, `weight`, `raw_weight`, `rank`
(null when the weight is 0), `reason` and `score`.

| reason | weight 0 because |
|---|---|
| `selected` | (not 0) passed every gate |
| `basket_parked` | the basket has `activatable: false` (forex) |
| `regime_unknown` | no regime key at all (defensive; the regime service always gives one) |
| `unscored_regime` | the card has no score for this regime key |
| `status_watch` / `status_parked` / `status_parked_for_forex_test` | the status for this regime is not `active_candidate` |
| `failed_min_trades` / `failed_pf` / `failed_net_pnl` / `failed_dsr` | below the `selection` gates |
| `zero_weight` | the lab gave weight 0 |

If the selected weights add up to more than `selection.max_total_weight`, they are scaled down
proportionally and rounded down to 1e-6, so the total never exceeds the cap. Rows contain no
wall-clock values, so the same inputs always produce the same bytes. The live paper loop
re-replays the session, so a row that is already in the file is never appended a second time.

## Basket files: `config/baskets/<market>.yaml`

`india.yaml` (NIFTY, SENSEX) is `activatable: true`. `forex.yaml` is `activatable: false`: it loads
and validates, but it is never attached to an underlying and the selector gives it weight 0.

- `instruments.<SYMBOL>`: `exchange`, `lot_size`, `expiry_weekday` (`MON`..`SUN` or null),
  `session {open, close, tz}`, `tick_size`. Every value carries a `Source:` comment. A value that
  still needs checking is marked `TODO(verify)`, and an unknown value is null, not a guess. These
  are metadata for the basket only. The engine gets its lot size from the Dhan instrument master,
  and the `expiry_day` flag comes from the regime service's calendar.
- `selection`: `max_total_weight`, `min_trades`, `min_pf`, `min_dsr` (0..1), `require_positive_net`.
- `lab_scores`: path of the lab refresh file (relative to the repo root).
- `strategies`: strategy cards. In yaml, `scores` may be empty (the card is then weight 0 until the lab scores it).
- A `regime:` block is rejected. Regime thresholds belong to `config/regime.yaml`.

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
  trend_up.vol_normal.non_expiry_day:
    {net_pnl: 41250.5, pf: 1.42, trades: 64, win_rate: 0.53, dsr: 0.96, weight: 0.4, rank: 1, status: active_candidate}
notes: ""                  # optional
```

`status` is one of `active_candidate`, `watch`, `parked`, `parked_for_forex_test`. Only
`active_candidate` can get a non-zero weight. Field ranges: `pf >= 0`, `trades` is an integer
`>= 0`, `win_rate` and `dsr` are in 0..1, `weight >= 0`, `rank` is an integer `>= 1`. Every number
must be finite. Unknown keys are rejected, so a typo cannot silently drop a rule.

## Lab refresh: `data/shadow/basket/lab/basket_<market>.json`

The lab writes this file, and the next session picks it up with no code change:

```json
{
  "schema_version": 1,
  "market": "india",
  "generated_at": "2026-09-26T18:00:00+05:30",
  "source": "scripts/lab/<script> run id",
  "data_until": "2026-09-25",
  "strategies": [ { "...": "full strategy card, scores required" } ]
}
```

- `data_until` is the last session date the scores used. The file is used only for sessions
  **after** that date; for a session on or before it, the file is ignored and the row's
  `lab.ignored` says why.
- A lab card **replaces** the yaml card with the same `id`. A new `id` is added.
- **Whole-file rejects:** the file is unreadable or not JSON, uses `NaN`/`Infinity` (cap `pf`
  before writing), has the wrong `schema_version` or `market`, is missing `generated_at`,
  `source` or a valid `data_until`, or `strategies` is not a list. The selector then uses the
  yaml cards only, and the error is recorded in each row's `lab.error`.
- **Per-entry rejects:** a malformed card, an unscored card (no `scores`, or a score missing a
  field), a market outside the basket, or a duplicate id. The rest of the file is still used, and
  the rejects are listed in `lab.rejected`.

Check a file before shipping it:
`PYTHONPATH=packages/strategy-basket/src python -m strategy_basket validate data/shadow/basket/lab/basket_india.json`
(exit 1 on any reject).

## Parity on the recorded Sep 17–25 tapes (local only)

The dual-tape files are not in git, so CI proves parity on the committed fixture day. On a machine
that has the tapes, run:

```bash
PYTHONPATH=packages/strategy-basket/src python -m strategy_basket parity --since 2026-09-17 --until 2026-09-25
```

For each day it replays the legacy path, then the event path with the selector forced on (rows go
to a temporary directory), and compares closed trades and skip counts. It prints `PARITY` or
`MISMATCH` per day and the totals. The legacy NIFTY total must still read 66 trades / −128,730.49.
Pass extra replay kwargs with `--kw key=json`, as `desk_ml.event_parity` accepts them. With the flag
off, the selector never runs, so the legacy replay is unchanged by construction.
