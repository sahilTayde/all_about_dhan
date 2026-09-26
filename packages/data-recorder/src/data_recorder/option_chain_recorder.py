"""Option chain recorder (full chain, OI/IV/greeks)."""

from datetime import datetime
from typing import Dict, Any
import time

from .writer import DailyJSONLWriter
from .config import RecorderConfig


class OptionChainRecorder:
    """
    Records full option chain (all strikes CE/PE, with OI/IV/greeks).
    
    Critical: Multi-strike OI history is missing (lab journal line 80).
    Current system may only store ATM ±5 strikes or may not store OI/IV consistently.
    This recorder captures ALL strikes (ATM-500 to ATM+500 minimum, wider if available).
    """
    
    def __init__(self, config: RecorderConfig):
        self.config = config
        self.writer = DailyJSONLWriter(config.base_path, "option_chain")
        self.underlyings = config.index_symbols  # NIFTY, BANKNIFTY, SENSEX
    
    def start(self) -> None:
        if self.config.dry_run:
            self._dry_run_mode()
        else:
            self._production_mode()
    
    def _production_mode(self) -> None:
        """Production mode stub."""
        raise NotImplementedError(
            "Production mode requires Dhan API integration. "
            "To implement: "
            "1. Poll Dhan REST API: GET /api/v1/market-data/option-chain?symbol=NIFTY&expiry=YYYY-MM-DD "
            "   OR subscribe to websocket for chain updates (if Dhan supports). "
            "2. Capture ALL strikes (not just ATM ±5; request full range ATM-500 to ATM+500 minimum). "
            "3. Ensure fields: ltp, bid, ask, volume, open_interest (CRITICAL), iv, delta, gamma, theta, vega. "
            "4. Poll every 60 seconds (1-minute snapshots). "
            "5. If rate-limited, poll every 2-3 min (acceptable; interpolate if needed in backtest). "
            "Underlyings: " + ", ".join(self.underlyings)
        )
    
    def _dry_run_mode(self) -> None:
        """
        Dry-run: generate synthetic chain for 3 strikes × 2 types (CE/PE) × 1 underlying (NIFTY).
        Real system would have ~150 strikes × 2 types = 300 rows per snapshot.
        """
        if self.config.verbose:
            print(f"[OptionChainRecorder] Dry-run mode: generating synthetic option chain...")
        
        base_time = datetime.now()
        timestamp = base_time.replace(second=0, microsecond=0)
        
        # Synthetic: NIFTY at 19800, 3 strikes (19700, 19800, 19900), CE and PE
        underlying = "NIFTY"
        atm = 19800.0
        strikes = [atm - 100, atm, atm + 100]
        
        for strike in strikes:
            for option_type in ["CE", "PE"]:
                option = {
                    "underlying": underlying,
                    "expiry": "2026-09-26",  # Weekly expiry
                    "strike": strike,
                    "option_type": option_type,
                    "timestamp": timestamp.isoformat(),
                    "ltp": round(50.0 + (atm - strike) * 0.3 if option_type == "CE" else 50.0 + (strike - atm) * 0.3, 2),
                    "bid": round(49.5, 2),
                    "ask": round(50.5, 2),
                    "volume": 12345,
                    "open_interest": 500000,  # CRITICAL field
                    "iv": round(0.15 + abs(strike - atm) * 0.0001, 4),  # Implied volatility
                    "delta": round(0.5 if option_type == "CE" else -0.5, 4),
                    "gamma": round(0.001, 6),
                    "theta": round(-5.0, 4),
                    "vega": round(10.0, 4)
                }
                self.writer.write(option)
        
        if self.config.verbose:
            print(f"[OptionChainRecorder] Dry-run complete. {self.writer.records_written} options written.")
    
    def stop(self) -> None:
        self.writer.close()
        if self.config.verbose:
            print(f"[OptionChainRecorder] Stopped. Total options: {self.writer.records_written}")
