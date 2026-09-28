# control (V2-11)

Founder command log and paper-only control semantics. Gateway routes live in `apps/api`. Flatten and kill go through the order router and exit primitives after `risk.check_flatten` / `risk.check_exit`. `DhanBroker` is never constructed.
