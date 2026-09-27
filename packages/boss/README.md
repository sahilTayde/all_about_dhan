# boss (PR-007)

`Boss` handles `MARKET_TICK` after the desk. It builds the analyst-room context, publishes
`REQUEST_VOTES`, collects the `ANALYST_VOTE`s, and then runs the paper engine's decision rules
unchanged (`paper_scalp.step_decide`: picker majority → observer → entry gates).

Each ticket becomes `ENTRY_APPROVED` (with the sized ticket: strike, lots, limit, stop, target and
the analysts behind it) or `NO_ENTRY` (with the gate that skipped it). The boss never calls the
risk engine or a broker; the desk does. Votes with `shadow: true` are audited and ignored.
Flow and parity: docs/PHASE2_NOTES.md.

`boss.basket` is the strategy registry and basket selector. It is shadow only and off by default.
When it is on, the boss picks a ranked, weighted basket pre-open and on each regime change, and
logs it to `data/shadow/basket/<day>.jsonl`. Schema, flags and the lab refresh: docs/baskets.md.

Install: `pip install -e packages/boss`
