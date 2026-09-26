# boss (PR-007)

`Boss` handles `MARKET_TICK` after the desk. It builds the analyst-room context, publishes
`REQUEST_VOTES`, collects the `ANALYST_VOTE`s, and then runs the paper engine's decision rules
unchanged (`paper_scalp.step_decide`: picker majority → observer → entry gates).

Each ticket becomes `ENTRY_APPROVED` (with the sized ticket: strike, lots, limit, stop, target and
the analysts behind it) or `NO_ENTRY` (with the gate that skipped it). The boss never calls the
risk engine or a broker; the desk does. Flow and parity: docs/PHASE2_NOTES.md.
