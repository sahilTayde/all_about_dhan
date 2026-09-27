# runtime (V2-15)

`python -m runtime <engine|health|reset-breaker|deploy|backup|restore|job>`.
Paper only. Restart breaker + job timeouts. Stub engine writes `ENGINE_STATUS READY`.
V2-14 reads `breaker_open` from `RestartBreaker.is_open` (not imported here).
