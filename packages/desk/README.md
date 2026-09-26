# desk (PR-008)

`Desk` executes and never decides. In order of precedence:

1. `FOUNDER_COMMAND` (priority 0): `PAUSE_ENTRIES`, `RESUME_ENTRIES`, `FLATTEN_ALL [underlying]`.
2. `MARKET_TICK`: mark-to-market with fills, STOP/TARGET/overlay exits. There is no boss round trip.
3. `ENTRY_APPROVED`: check founder pause, then `RiskEngine.check_entry`, then
   `broker.place_order`, then book the ticket. A veto, a broker refusal, or any error while
   building the order means no trade (`ENTRY_VETOED`).
4. `EXIT_APPROVED`: close one ticket now.

Every entry, exit and cancel goes through the risk engine (`check_entry` / `check_exit`) and then
the broker. `attach_ledger` records it in the ledger.

`ClockedPaperBroker` is a `PaperBroker` whose approval-age check runs on the session clock (tape
time in replay). Its `fill_at` books the paper engine's simulated fill for a single order. The
Dhan broker and its live gate are not used or changed here.
