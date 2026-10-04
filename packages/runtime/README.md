# runtime (V2-15)

`python -m runtime <engine|health|reset-breaker|deploy|backup|restore|job|bench-legacy|forward-eval>`.
Paper only. Restart breaker + job timeouts. Stub engine writes `ENGINE_STATUS READY`.
`bench-legacy` is the V2-17 frozen `replay_paper_scalp` entry (same package, one pyproject).
`forward-eval` is the V2-20a harness (`forward_eval.enabled: false` by default; exits 0 doing nothing).
V2-14 reads `breaker_open` from `RestartBreaker.is_open` (not imported here).
