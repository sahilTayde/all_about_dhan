# harness (V2-25)

Off-market Dhan **order-path** test: submit one far-off LIMIT buy, cancel at once.

**Default = OFF.** CI and the default CLI never construct a live Dhan client and never
place a marketable order. This is not live trading and does not open `DhanBroker`.

```bash
# Always refused (exit 2) unless the founder sets the approval phrase + credentials
# and passes --mode shadow|harness --transport dhan on their machine.
python -m harness

# Mock / recorded path (still needs the approval flag + dummy credentials in-process)
python -m harness --mode shadow --transport mock
```

Live transport is extra-explicit:

```text
ALL_ABOUT_DHAN_SHADOW_HARNESS=I_APPROVE_OFF_MARKET_SHADOW_TEST
DHAN_CLIENT_ID=...
DHAN_ACCESS_TOKEN=...
python -m harness --mode shadow --transport dhan --security-id <dhan-security-id>
```

`ALL_ABOUT_DHAN_LIVE_CONFIRM` does **not** enable this harness. Mode `live` /
`limited_live` is refused. BUY LIMIT at ₹1 only (cap ₹1.05). MARKET is refused.
