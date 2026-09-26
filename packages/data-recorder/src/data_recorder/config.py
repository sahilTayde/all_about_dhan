"""Configuration for data recorder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RecorderConfig:
    """Configuration for market data recorder."""

    # Output directory (gitignored)
    output_dir: Path = Path("data/recon")

    # Index symbols to record (1-minute ticks)
    index_symbols: list[str] = None

    # Futures symbols (with volume)
    futures_symbols: list[str] = None

    # Option chain underlyings
    option_chain_underlyings: list[str] = None

    # Heavyweight stocks (top 15 NIFTY components)
    heavyweight_symbols: list[str] = None

    # News RSS feed URLs
    news_feeds: list[str] = None

    # Global market symbols
    global_symbols: list[str] = None

    # Dry-run mode (generates synthetic data, no Dhan API calls)
    dry_run: bool = False

    # Verbose logging
    verbose: bool = False

    # Health heartbeat interval (seconds)
    heartbeat_interval: int = 60

    def __post_init__(self) -> None:
        if self.index_symbols is None:
            self.index_symbols = ["NIFTY", "BANKNIFTY", "SENSEX"]
        if self.futures_symbols is None:
            # Current month futures for indices
            self.futures_symbols = ["NIFTYFUT", "BANKNIFTYFUT", "SENSEXFUT"]
        if self.option_chain_underlyings is None:
            self.option_chain_underlyings = ["NIFTY", "BANKNIFTY", "SENSEX"]
        if self.heavyweight_symbols is None:
            # Top 15 NIFTY components (by weight/liquidity)
            self.heavyweight_symbols = [
                "RELIANCE",
                "TCS",
                "HDFCBANK",
                "INFY",
                "ICICIBANK",
                "HINDUNILVR",
                "ITC",
                "SBIN",
                "BHARTIARTL",
                "KOTAKBANK",
                "LT",
                "AXISBANK",
                "ASIANPAINT",
                "MARUTI",
                "HCLTECH",
            ]
        if self.news_feeds is None:
            self.news_feeds = [
                "https://www.moneycontrol.com/rss/latestnews.xml",
                "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            ]
        if self.global_symbols is None:
            self.global_symbols = ["SPY", "DXY", "^TNX", "CL=F", "GC=F", "USDINR=X", "^VIX"]


def load_config(*, dry_run: Optional[bool] = None, verbose: bool = False) -> RecorderConfig:
    """Load recorder configuration."""
    config = RecorderConfig(verbose=verbose)
    if dry_run is not None:
        config.dry_run = dry_run
    return config
