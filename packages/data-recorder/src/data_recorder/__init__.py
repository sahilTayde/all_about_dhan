"""Daily market data recorder: index, futures, option chain, heavyweights, news, global markets.

Reuses existing Dhan client infrastructure:
- dhan_client.DhanClient for REST + websocket feed
- dhan_client.instruments for security ID lookup
- desk_intel.option_chain_poller for existing rate-limited option chain polling
"""

__version__ = "0.1.0"
