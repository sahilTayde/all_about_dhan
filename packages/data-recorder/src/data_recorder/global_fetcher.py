"""Global markets fetcher: SPX, DXY, US10Y, crude, gold, USDINR, VIX."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from data_recorder.writer import JsonLinesWriter

log = logging.getLogger("data_recorder.global")


class GlobalFetcher:
    """Fetch global market data (daily close prices)."""

    def __init__(
        self,
        symbols: list[str],
        output_dir: Path,
        *,
        verbose: bool = False,
    ) -> None:
        self.symbols = symbols
        self.writer = JsonLinesWriter(output_dir, "global_markets", verbose=verbose)
        self.verbose = verbose
        self._poll_interval = 3600  # 1 hour

    async def run(self) -> None:
        """Run global markets fetcher (polls every hour)."""
        try:
            import yfinance as yf
        except ImportError:
            log.error(
                "yfinance not installed. Install with: pip install yfinance\n"
                "Global markets fetcher will not run until yfinance is available."
            )
            return

        if self.verbose:
            log.info("Global markets fetcher starting")

        while True:
            for symbol in self.symbols:
                try:
                    await self._fetch_symbol(symbol, yf)
                except Exception as e:
                    log.error("Error fetching %s: %s", symbol, e)

            await asyncio.sleep(self._poll_interval)

    async def _fetch_symbol(self, symbol: str, yf: Any) -> None:
        """Fetch latest data for one symbol."""
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")

        if hist.empty:
            return

        latest = hist.iloc[-1]

        record = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "open": float(latest["Open"]) if "Open" in latest else None,
            "high": float(latest["High"]) if "High" in latest else None,
            "low": float(latest["Low"]) if "Low" in latest else None,
            "close": float(latest["Close"]) if "Close" in latest else None,
            "volume": int(latest["Volume"]) if "Volume" in latest else None,
            "change_pct": (
                ((latest["Close"] - latest["Open"]) / latest["Open"] * 100)
                if "Close" in latest and "Open" in latest
                else None
            ),
        }
        self.writer.write(record)

    async def run_dry(self) -> None:
        """Dry-run: generate synthetic global market data."""
        log.info("Global markets fetcher dry-run: generating %d synthetic records", len(self.symbols))

        timestamp = datetime.now().isoformat()

        for symbol in self.symbols:
            record = {
                "symbol": symbol,
                "timestamp": timestamp,
                "open": 4200.0,
                "high": 4215.0,
                "low": 4195.0,
                "close": 4210.0,
                "volume": 1000000,
                "change_pct": 0.24,
            }
            self.writer.write(record)

        log.info("Global markets fetcher dry-run complete")

    def close(self) -> None:
        """Close writer."""
        self.writer.close()
