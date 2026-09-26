"""Configuration for data recorder."""

from dataclasses import dataclass, field
from typing import List
from pathlib import Path


@dataclass
class RecorderConfig:
    """Configuration for all data recorders."""
    
    # Storage
    base_path: Path = Path("data/recon")
    
    # Symbols to record
    index_symbols: List[str] = field(default_factory=lambda: ["NIFTY", "BANKNIFTY", "SENSEX"])
    futures_symbols: List[str] = field(default_factory=lambda: ["NIFTYFUT", "BANKNIFTYFUT", "SENSEXFUT"])
    
    # Top 15 NIFTY heavyweights by weight (as of Sep 2026; verify with NSE factsheet)
    heavyweight_symbols: List[str] = field(default_factory=lambda: [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "BHARTIARTL", "ITC", "HINDUNILVR", "SBIN", "KOTAKBANK",
        "AXISBANK", "LT", "ASIANPAINT", "MARUTI", "TITAN"
    ])
    
    # Global markets (Yahoo Finance symbols)
    global_symbols: List[str] = field(default_factory=lambda: [
        "^GSPC",      # S&P 500 (SPX)
        "^IXIC",      # Nasdaq 100 (NDX)
        "DX-Y.NYB",   # US Dollar Index (DXY)
        "^TNX",       # US 10-Year Treasury Yield
        "CL=F",       # Crude Oil WTI
        "GC=F",       # Gold
        "USDINR=X"    # USD/INR
    ])
    
    # News RSS feeds
    news_feeds: List[dict] = field(default_factory=lambda: [
        {"name": "MoneyControl", "url": "https://www.moneycontrol.com/rss/latestnews.xml"},
        {"name": "EconomicTimes", "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms"}
    ])
    
    # Dry-run mode (no network calls; generates synthetic data for testing)
    dry_run: bool = False
    
    # Verbosity
    verbose: bool = True


def get_config() -> RecorderConfig:
    """Get recorder configuration (factory)."""
    return RecorderConfig()
