"""Index ticks recorder (NIFTY, BANKNIFTY, SENSEX)."""

from datetime import datetime
from typing import List, Dict, Any
import time

from .writer import DailyJSONLWriter
from .config import RecorderConfig


class IndexRecorder:
    """
    Records index 1-minute ticks (OHLCV per minute).
    
    In production: subscribes to Dhan websocket for real-time ticks.
    In dry-run: generates synthetic ticks for testing.
    """
    
    def __init__(self, config: RecorderConfig):
        self.config = config
        self.writer = DailyJSONLWriter(config.base_path, "index_ticks")
        self.symbols = config.index_symbols
    
    def start(self) -> None:
        """Start recording (runs until stopped)."""
        if self.config.dry_run:
            self._dry_run_mode()
        else:
            self._production_mode()
    
    def _production_mode(self) -> None:
        """
        Production mode: subscribe to Dhan websocket.
        
        NOTE: This is a stub. In production, Sahil runs this with:
        1. Dhan API credentials in environment (DHAN_TOKEN, DHAN_CLIENT_ID)
        2. Dhan websocket client (to be implemented with real Dhan API)
        
        For now, this raises NotImplementedError with instructions.
        """
        raise NotImplementedError(
            "Production mode requires Dhan API integration. "
            "To implement: "
            "1. Install Dhan Python SDK or use websocket library. "
            "2. Subscribe to symbols: " + ", ".join(self.symbols) + ". "
            "3. On each tick, call self._write_tick(symbol, tick_data). "
            "Example: "
            "  from dhanhq import marketfeed  # hypothetical "
            "  client = marketfeed.DhanFeed(token=DHAN_TOKEN) "
            "  client.subscribe(symbols=self.symbols, mode='full') "
            "  client.on_tick(self._on_tick) "
            "  client.connect() "
        )
    
    def _dry_run_mode(self) -> None:
        """
        Dry-run mode: generate synthetic ticks for testing.
        Generates 5 ticks (one per symbol per minute for ~2 minutes).
        """
        if self.config.verbose:
            print(f"[IndexRecorder] Dry-run mode: generating {len(self.symbols) * 2} synthetic ticks...")
        
        base_time = datetime.now()
        for minute_offset in range(2):  # 2 minutes
            timestamp = base_time.replace(second=0, microsecond=0)
            timestamp = timestamp.replace(minute=timestamp.minute + minute_offset)
            
            for i, symbol in enumerate(self.symbols):
                # Synthetic OHLCV (realistic-ish values for NIFTY ~19800, BANKNIFTY ~44000, SENSEX ~66000)
                base_price = 19800.0 if "NIFTY" in symbol else (44000.0 if "BANK" in symbol else 66000.0)
                tick = {
                    "symbol": symbol,
                    "timestamp": timestamp.isoformat(),
                    "open": round(base_price + i * 10 + minute_offset * 5, 2),
                    "high": round(base_price + i * 10 + minute_offset * 5 + 20, 2),
                    "low": round(base_price + i * 10 + minute_offset * 5 - 15, 2),
                    "close": round(base_price + i * 10 + minute_offset * 5 + 10, 2),
                    "volume": None  # Spot index has no volume
                }
                self._write_tick(tick)
            
            time.sleep(0.1)  # Small delay to simulate real-time
        
        if self.config.verbose:
            print(f"[IndexRecorder] Dry-run complete. {self.writer.records_written} ticks written.")
    
    def _write_tick(self, tick: Dict[str, Any]) -> None:
        """Write a tick to file."""
        self.writer.write(tick)
    
    def stop(self) -> None:
        """Stop recording and close files."""
        self.writer.close()
        if self.config.verbose:
            print(f"[IndexRecorder] Stopped. Total ticks: {self.writer.records_written}")
