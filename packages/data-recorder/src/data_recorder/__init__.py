"""
Data recorder package for all_about_dhan.

Records market data daily (cannot be backfilled):
- Index ticks (NIFTY, BANKNIFTY, SENSEX)
- Futures ticks with volume
- Option chain (full chain, OI/IV/greeks)
- Heavyweights (top 15 NIFTY stocks)
- News (RSS feeds)
- Global markets (Yahoo Finance)

Outputs: JSON Lines files under data/recon/ (gitignored).
"""

__version__ = "0.1.0"
