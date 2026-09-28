# premarket (V2-18)

Publishes `PRE_MARKET_SUMMARY` from **prior-session** bars only. Event-day holds and HAR inputs included. `available_ts` is the run time and must be before 09:15 IST. Idempotent. Paper only. No network.

```bash
python -m premarket --session 2026-09-28 --now 2026-09-28T08:30:00+05:30 --prior bars.json --out DIR
```
