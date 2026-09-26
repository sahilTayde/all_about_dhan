"""Futures ticks recorder (with volume)."""

from datetime import datetime
from typing import Dict, Any
import time

from .writer import DailyJSONLWriter
from .config import RecorderConfig


class FuturesRecorder:
    """
    Records futures 1-minute ticks (OHLCV + volume + OI).
    
    Critical: Volume is currently missing (lab journal line 80).
    """
    
    def __init__(self, config: RecorderConfig):
        self.config = config
        self.writer = DailyJSONLWriter(config.base_path, "futures_ticks")
        self.symbols = config.futures_symbols
    
    def start(self) -> None:
        if self.config.dry_run:
            self._dry_run_mode()
        else:
            self._production_mode()
    
    def _production_mode(self) -> None:
        """Production mode stub (same pattern as IndexRecorder)."""
        raise NotImplementedError(
            "Production mode requires Dhan API integration. "
            "To implement: Subscribe to futures symbols: " + ", ".join(self.symbols) + ". "
            "Ensure 'volume' and 'open_interest' fields are captured (critical for analysis)."
        )
    
    def _dry_run_mode(self) -> None:
        if self.config.verbose:
            print(f"[FuturesRecorder] Dry-run mode: generating {len(self.symbols) * 2} synthetic ticks...")
        
        base_time = datetime.now()
        for minute_offset in range(2):
            timestamp = base_time.replace(second=0, microsecond=0)
            timestamp = timestamp.replace(minute=timestamp.minute + minute_offset)
            
            for i, symbol in enumerate(self.symbols):
                base_price = 19850.0 if "NIFTY" in symbol else (44100.0 if "BANK" in symbol else 66200.0)
                tick = {
                    "symbol": symbol,
                    "expiry": "2026-09-30",  # Example: monthly expiry
                    "timestamp": timestamp.isoformat(),
                    "open": round(base_price + i * 10 + minute_offset * 5, 2),
                    "high": round(base_price + i * 10 + minute_offset * 5 + 25, 2),
                    "low": round(base_price + i * 10 + minute_offset * 5 - 18, 2),
                    "close": round(base_price + i * 10 + minute_offset * 5 + 12, 2),
                    "volume": 1234567 + minute_offset * 10000 + i * 5000,  # Synthetic volume (CRITICAL: must be real in production)
                    "open_interest": 5000000 + i * 100000
                }
                self.writer.write(tick)
            
            time.sleep(0.1)
        
        if self.config.verbose:
            print(f"[FuturesRecorder] Dry-run complete. {self.writer.records_written} ticks written.")
    
    def stop(self) -> None:
        self.writer.close()
        if self.config.verbose:
            print(f"[FuturesRecorder] Stopped. Total ticks: {self.writer.records_written}")
