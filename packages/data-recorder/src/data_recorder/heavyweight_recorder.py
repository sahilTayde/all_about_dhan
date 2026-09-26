"""Heavyweight stocks recorder (top 15 NIFTY constituents)."""

from datetime import datetime
from typing import Dict, Any
import time

from .writer import DailyJSONLWriter
from .config import RecorderConfig


class HeavyweightRecorder:
    """
    Records top NIFTY heavyweight stocks (1-minute LTP).
    
    Critical: Missing data (lab journal line 80). H06 breadth filter showed +35.2k on tape
    but only ~42 days history overlap. Recording daily accumulates data for breadth analysis.
    """
    
    def __init__(self, config: RecorderConfig):
        self.config = config
        self.writer = DailyJSONLWriter(config.base_path, "heavyweight_ticks")
        self.symbols = config.heavyweight_symbols
    
    def start(self) -> None:
        if self.config.dry_run:
            self._dry_run_mode()
        else:
            self._production_mode()
    
    def _production_mode(self) -> None:
        """Production mode stub."""
        raise NotImplementedError(
            "Production mode requires Dhan API integration. "
            "To implement: Subscribe to NSE equity symbols: " + ", ".join(self.symbols) + ". "
            "Capture: ltp (last traded price), volume (cumulative day so far). "
            "1-minute snapshots sufficient (no need for tick-by-tick)."
        )
    
    def _dry_run_mode(self) -> None:
        if self.config.verbose:
            print(f"[HeavyweightRecorder] Dry-run mode: generating {len(self.symbols) * 2} synthetic ticks...")
        
        base_time = datetime.now()
        for minute_offset in range(2):
            timestamp = base_time.replace(second=0, microsecond=0)
            timestamp = timestamp.replace(minute=timestamp.minute + minute_offset)
            
            for i, symbol in enumerate(self.symbols):
                # Synthetic LTP (realistic-ish: Reliance ~2500, TCS ~3800, HDFC Bank ~1600)
                base_price = 2500.0 if symbol == "RELIANCE" else (3800.0 if symbol == "TCS" else 1600.0)
                tick = {
                    "symbol": symbol,
                    "timestamp": timestamp.isoformat(),
                    "ltp": round(base_price + i * 5 + minute_offset * 2, 2),
                    "volume": 123456 + minute_offset * 1000 + i * 500
                }
                self.writer.write(tick)
            
            time.sleep(0.1)
        
        if self.config.verbose:
            print(f"[HeavyweightRecorder] Dry-run complete. {self.writer.records_written} ticks written.")
    
    def stop(self) -> None:
        self.writer.close()
        if self.config.verbose:
            print(f"[HeavyweightRecorder] Stopped. Total ticks: {self.writer.records_written}")
