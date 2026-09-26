# analysts (PR-009)

Common interface: `Analyst.vote(MarketContext) -> Vote(analyst_id, signal, confidence, reasoning, metadata)`,
where `signal` is `BUY_CE | BUY_PE | HOLD | ABSTAIN`.

- `register("KEY")` adds an analyst to the registry, and `config/analysts.yaml` lists the enabled
  keys in order. The default 22 keys are the paper engine's existing analyst room
  (`desk_ml.picker.collect_analyst_votes`), wrapped rather than rewritten. Conversion to and from
  picker votes is lossless.
- `AnalystRoom` runs every analyst in parallel with a per-request timeout (500 ms). A timeout, a
  crash, or a wrong return value becomes `ABSTAIN` for that analyst only. `room.attach(bus, contexts)`
  answers `REQUEST_VOTES` with one `ANALYST_VOTE` per analyst.
- New research features: put values in `MarketContext.features`, write an analyst that reads
  them, register its key, and add the key to the config.

Tests: see docs/PHASE2_NOTES.md.
