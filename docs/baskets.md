# Strategy baskets (basket selector)

**Shadow only, off by default, self-contained.** The selector ranks and weights strategy cards for
the current market regime and writes the result to a log. It places no orders, and nothing in the
engine, boss, desk or order path reads its output.

It is a separate module that does not edit any existing file:

| Path | What |
|---|---|
| `packages/strategy-basket/src/strategy_basket/basket.py` | card schema, loaders, selector, shadow log, bus wiring, CLI |
| `packages/strategy-basket/src/strategy_basket/entry.py` | entry-location policy: zones (FVG, candle 50%, POC), entry distance in ATR, verdicts |
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
desk's mark-to-market at 10, before the boss at 20), `REGIME_LABEL`, and `ENTRY_APPROVED` (to
measure each boss ticket). It never publishes,
and it catches its own errors, so it cannot add to `bus.errors` or change an entry. Merging it
also needs `packages/strategy-basket` added to `.cursor/install.sh` and the uv workspace; after
that, the tests' `conftest.py` can be deleted.

Until the hook lands, `strategy_basket.BasketEventSession(...)` is an `EventSession` with that
line applied. Replays and tests use it:
`replay_paper_scalp(..., event_session=BasketEventSession())`.

## Entry-location policy

Legacy entries chase the top of big impulse candles, then give 4–5 points back as price retraces
into the imbalance the move came from. So every strategy card must declare where it enters, and
every boss ticket gets its entry location measured.

**On each card** (required):

```yaml
entry_policy: {kind: chase}                                           # enter at the signal (legacy)
entry_policy: {kind: pullback_limit, zone: fvg, timeout_bars: 3}      # zone: fvg | candle_50 | poc
entry_policy: {kind: wait_consolidation, timeout_bars: 5}             # timeout optional
# any kind may add  max_stretch_atr: 1.2   (else the basket's entry_location.max_stretch_atr)
```

`pullback_limit` needs a `zone` and `timeout_bars` (closed 1-minute bars). `chase` has no timeout.
Only `pullback_limit` names a zone. The seed card `MIX-DEFAULT-BUY` is `chase`, because that is
what legacy does.

**On each signal.** For every boss `ENTRY_APPROVED` ticket, a `signal` row is written. It uses
only today's index 1-minute bars that closed before the ticket's tick; the forming minute is never
read. The row records:
- the index price;
- Wilder ATR (`atr_period`) on those bars;
- each zone:
  - `fvg`: the last 3-candle fair-value gap in the trade's direction within `lookback_bars`;
  - `candle_50`: 50% of the last candle in the trade's direction with range ≥ `impulse_atr_mult` × ATR;
  - `poc`: the session's highest-volume price bucket, `poc_bucket_atr` × ATR wide, using time at
    price when the tape has no volume.
- each zone's `distance_atr`: signed distance from the zone's near edge, positive when price has
  run beyond it in the trade's direction (above for CE, below for PE), 0 inside it, negative when
  the zone is still ahead;
- `entry_distance_atr` and `zone_type`: the nearest zone **behind** the price (distance ≥ 0).
  Zones ahead are logged but never picked, so a far-away POC cannot hide a stretched entry.

Each applicable card then gets a verdict. Nothing is enforced (`enforced: false`); the basket is
shadow only.

| action | when | `veto_reason` |
|---|---|---|
| `ENTER` | distance ≤ cap, or no cap configured | — |
| `VETO_STRETCHED` | `chase` card, distance > cap | `STRETCHED_ENTRY: <d> ATR beyond <zone> > max <cap>` |
| `WAIT_PULLBACK` | `pullback_limit`, distance to its zone > cap; logs `limit_index_level` (the zone edge) | — |
| `WAIT_CONSOLIDATION` | `wait_consolidation`, distance > cap | — |
| `CHASE_NOT_ALLOWED` | `chase` card while `mode: require` | `CHASE_POLICY_NOT_ALLOWED` |
| `NO_ZONE_BEHIND` | no zone behind the price (or the card's own zone is ahead of it) | — |
| `DATA_INSUFFICIENT` | not enough closed bars for ATR | — |

**In the selector** (`entry_location.mode` in the basket yaml):
- `log_only` (default): weights are unchanged, and chase cards carry an `entry_note` saying what
  the other modes would do.
- `prefer`: a chase card's weight is multiplied by `chase_weight_mult`, and it ranks after
  non-chasing cards of the same rank.
- `require`: chase cards get weight 0 with reason `entry_policy_chase`.

**All thresholds are placeholders.** `max_stretch_atr`, `chase_weight_mult`, `lookback_bars`,
`impulse_atr_mult` and `poc_bucket_atr` are marked `PLACEHOLDER` in `config/baskets/india.yaml`
until research round 10 sets them. On the synthetic fixture day, with the placeholder 1.0 ATR cap,
7 of 12 legacy tickets log `VETO_STRETCHED`. That is a smoke check on synthetic data, not evidence.

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
- `trigger` (`pre_open` | `regime_change` | `signal`);
- `regime`: `primary`, `vol`, `expiry`, `key`, `source` (`pre_open` | `regime_service`),
  `label_ts` (the labelled minute), `labels`, `version`, `features`;
- `basket`;
- `lab`: which lab file, whether it was used or ignored and why, rejected entries, error;
- `shadow: true`, `places_orders: false`.

`signal` rows carry `signal` (trade id, side, strike, entry premium, price, `atr`, `zones`,
`entry_distance_atr`, `zone_type`), `verdicts` (one per card for that index, with its current
weight), `vetoes` (card id → `veto_reason`), `regime_key` and `entry_mode`, instead of `regime`
and `basket`.

`basket.strategies` is ranked. Selected strategies come first (by the lab's `rank`, then weight,
then id), then weight-0 strategies by id. Each entry has `id`, `weight`, `raw_weight`, `rank`
(null when the weight is 0), `reason`, `score`, `entry_policy` and `entry_note`.

| reason | weight 0 because |
|---|---|
| `selected` | (not 0) passed every gate |
| `basket_parked` | the basket has `activatable: false` (forex) |
| `regime_unknown` | no regime key at all (defensive; the regime service always gives one) |
| `unscored_regime` | the card has no score for this regime key |
| `status_watch` / `status_parked` / `status_parked_for_forex_test` | the status for this regime is not `active_candidate` |
| `failed_min_trades` / `failed_pf` / `failed_net_pnl` / `failed_dsr` | below the `selection` gates |
| `zero_weight` | the lab gave weight 0 |
| `entry_policy_chase` | `entry_location.mode: require` and the card's `entry_policy` is `chase` |

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
- `entry_location` (required): `mode` (`log_only` | `prefer` | `require`), `max_stretch_atr`
  (null = no cap), `chase_weight_mult`, `atr_period`, `lookback_bars`, `impulse_atr_mult`,
  `poc_bucket_atr`. See the entry-location section.
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
entry_policy:              # required; see the entry-location section
  {kind: pullback_limit, zone: fvg, timeout_bars: 3, max_stretch_atr: 1.2}
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

## Parity against main `ec91e9e` (SHADOW_LOG=0, basket off)

Quoted Sep 17–25 dual-tape live-session totals on main after the closed-bar logit fix (#25).
These are the numbers a basket-off legacy replay must match:

| Run | Trades | Net INR |
|---|---:|---:|
| NIFTY | 63 | −96,190.79 |
| NIFTY + BANKNIFTY + SENSEX | 140 | −27,022.54 |
| Lab P2C | 36 | +110,000.29 |

Lab P2C is a separate stack (loss cooldown, session window 10:00–14:30). `replay_paper_scalp` does
not have those rules, so the checker records the quote and does not recompute it.

```bash
PYTHONPATH=packages/strategy-basket/src python -m strategy_basket baselines
```

The command forces `SHADOW_LOG=0`, clears `USE_BASKET_SELECTOR` and `USE_EVENT_BUS`, and walks each
day on the legacy path (`use_event_bus=False`). Exit 0 when both replay totals match. Exit 2 when
this machine has no dual-tape days (not a pass, not a mismatch). Exit 1 when a total differs.
It restores the three env vars before it returns.

The dual-tape files are not in git, so CI proves the basket-off path on the committed fixture day.
With `SHADOW_LOG=0`, the monolith replay and `BasketEventSession` with the flag off produce the same
closed trades, open tickets, and skip counts.

On a machine that has the tapes, the selector-on comparison is:

```bash
PYTHONPATH=packages/strategy-basket/src python -m strategy_basket parity --since 2026-09-17 --until 2026-09-25
```

For each day it replays the legacy path, then the event path with the selector forced on (rows go
to a temporary directory), and compares closed trades and skip counts. It prints `PARITY` or
`MISMATCH` per day and the totals. The legacy NIFTY total on that run must still read 63 trades /
−96,190.79. Pass extra replay kwargs with `--kw key=json`, as `desk_ml.event_parity` accepts them.
With the flag off, the selector never runs, so the legacy replay is the main path.
