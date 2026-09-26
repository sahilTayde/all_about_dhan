"""Global markets fetcher (Yahoo Finance daily close)."""

from datetime import datetime, date
from typing import Dict, Any
import time

from .writer import DailyJSONLWriter
from .config import RecorderConfig


class GlobalFetcher:
    """
    Fetches global market data (daily close: SPX, DXY, US10Y, crude, gold, USDINR).
    
    In production: Uses yfinance library (lightweight Yahoo Finance API wrapper).
    In dry-run: Generates synthetic data.
    """
    
    def __init__(self, config: RecorderConfig):
        self.config = config
        self.writer = DailyJSONLWriter(config.base_path, "global_markets")
        self.symbols = config.global_symbols
    
    def start(self) -> None:
        """Run once (fetch all symbols, write daily close)."""
        if self.config.dry_run:
            self._dry_run_mode()
        else:
            self._production_mode()
    
    def _production_mode(self) -> None:
        """Production mode stub."""
        raise NotImplementedError(
            "Production mode requires yfinance library. "
            "To implement: "
            "1. pip install yfinance "
            "2. import yfinance as yf "
            "3. For each symbol in self.symbols: "
            "   ticker = yf.Ticker(symbol) "
            "   hist = ticker.history(period='1d')  # Last 1 day "
            "   close = hist['Close'].iloc[-1] "
            "   prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else None "
            "   change_pct = ((close - prev_close) / prev_close) if prev_close else None "
            "   global_data = { "
            "       'symbol': symbol, "
            "       'date': date.today().isoformat(), "
            "       'close': close, "
            "       'change_pct': change_pct "
            "   } "
            "   self.writer.write(global_data) "
        )
    
    def _dry_run_mode(self) -> None:
        if self.config.verbose:
            print(f"[GlobalFetcher] Dry-run mode: generating {len(self.symbols)} synthetic global market data...")
        
        today = date.today()
        
        for i, symbol in enumerate(self.symbols):
            # Synthetic close (realistic-ish: SPX ~4500, DXY ~103, US10Y ~4.5%, crude ~85, gold ~1950, USDINR ~83)
            base_value = {
                "^GSPC": 4500.0,
                "^IXIC": 14000.0,
                "DX-Y.NYB": 103.0,
                "^TNX": 4.5,
                "CL=F": 85.0,
                "GC=F": 1950.0,
                "USDINR=X": 83.0
            }.get(symbol, 100.0)
            
            close = round(base_value + i * 0.5, 2)
            prev_close = round(base_value - 0.2, 2)
            change_pct = round((close - prev_close) / prev_close, 4)
            
            global_data = {
                "symbol": symbol,
                "date": today.isoformat(),
                "close": close,
                "change_pct": change_pct
            }
            self.writer.write(global_data)
            time.sleep(0.05)
        
        if self.config.verbose:
            print(f"[GlobalFetcher] Dry-run complete. {self.writer.records_written} global data points written.")
    
    def stop(self) -> None:
        self.writer.close()
        if self.config.verbose:
            print(f"[GlobalFetcher] Stopped. Total global data: {self.writer.records_written}")
