"""Futures recorder: NIFTY, BANKNIFTY, SENSEX futures with volume.

CRITICAL: Volume field must be captured (currently missing per lab journal).
Reuses existing DhanClient feed infrastructure.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.types import FeedInstrument, FeedMode, JsonDict

from data_recorder.writer import JsonLinesWriter

log = logging.getLogger("data_recorder.futures")


class FuturesRecorder:
    """Record futures 1-minute ticks with volume via Dhan websocket feed."""

    def __init__(
        self,
        client: DhanClient,
        symbols: list[str],
        output_dir: Path,
        *,
        verbose: bool = False,
    ) -> None:
        self.client = client
        self.symbols = symbols
        self.writer = JsonLinesWriter(output_dir, "futures_ticks", verbose=verbose)
        self.verbose = verbose
        self._minute_bars: dict[str, dict[str, Any]] = {}

    def _get_current_month_expiry(self) -> str:
        """Get current month futures expiry (last Thursday)."""
        # Simplified: return end of current month
        # In production, use actual NSE futures expiry logic
        today = datetime.now()
        next_month = today.replace(day=28) + timedelta(days=4)
        return next_month.replace(day=1).strftime("%Y-%m-%d")

    def _get_instrument_for_future(self, symbol: str) -> Optional[FeedInstrument]:
        """Look up futures instrument via existing instrument master."""
        # In production: use client.instruments.fetch_scrip_master_text()
        # and filter for current month futures contracts
        # For now, return placeholder (dry-run will handle)
        if self.client.dry_run:
            return FeedInstrument(exchange_segment=1, security_id=99999)
        
        # TODO: Implement instrument lookup using existing instruments client
        # Example logic (to be implemented):
        # master_text = self.client.instruments.fetch_scrip_master_text()
        # Parse CSV, filter by symbol + instrument_type="FUTIDX" + current expiry
        log.warning(
            "Futures instrument lookup not fully implemented. "
            "Use client.instruments.fetch_scrip_master_text() to find security IDs."
        )
        return None

    async def _on_packet(self, packet: JsonDict) -> None:
        """Handle incoming websocket packet."""
        try:
            symbol = packet.get("symbol") or packet.get("trading_symbol")
            if not symbol:
                return

            timestamp = packet.get("timestamp") or packet.get("exchange_timestamp")
            ltp = packet.get("ltp") or packet.get("last_price")
            volume = packet.get("volume") or packet.get("traded_volume")
            oi = packet.get("oi") or packet.get("open_interest")

            if not timestamp or ltp is None:
                return

            # Aggregate into 1-minute bars
            minute_key = self._minute_key(timestamp)
            bar_key = f"{symbol}_{minute_key}"

            if bar_key not in self._minute_bars:
                self._minute_bars[bar_key] = {
                    "symbol": symbol,
                    "expiry": self._get_current_month_expiry(),
                    "timestamp": datetime.fromtimestamp(minute_key).isoformat(),
                    "open": ltp,
                    "high": ltp,
                    "low": ltp,
                    "close": ltp,
                    "volume": volume,  # CRITICAL: Must capture volume
                    "open_interest": oi,
                }
            else:
                bar = self._minute_bars[bar_key]
                bar["high"] = max(bar["high"], ltp)
                bar["low"] = min(bar["low"], ltp)
                bar["close"] = ltp
                if volume is not None:
                    bar["volume"] = volume
                if oi is not None:
                    bar["open_interest"] = oi

        except Exception as e:
            log.warning("Error processing futures packet: %s", e)

    def _minute_key(self, timestamp: Any) -> int:
        """Floor timestamp to minute boundary."""
        ts = int(timestamp) if timestamp else 0
        if ts > 1e12:
            ts = ts // 1000
        return ts - (ts % 60)

    async def _flush_bars(self) -> None:
        """Periodically flush completed minute bars."""
        while True:
            await asyncio.sleep(60)
            current_minute = self._minute_key(datetime.now().timestamp())

            to_remove = []
            for bar_key, bar in self._minute_bars.items():
                bar_ts = datetime.fromisoformat(bar["timestamp"]).timestamp()
                if self._minute_key(bar_ts) < current_minute:
                    self.writer.write(bar)
                    to_remove.append(bar_key)

            for key in to_remove:
                del self._minute_bars[key]

    async def run(self) -> None:
        """Run futures recorder (subscribes via websocket)."""
        if self.client.dry_run:
            await self._run_dry()
            return

        # Build FeedInstrument list
        instruments: list[FeedInstrument] = []
        for symbol in self.symbols:
            inst = self._get_instrument_for_future(symbol)
            if inst:
                instruments.append(inst)

        if not instruments:
            log.warning("No instruments to subscribe for futures recorder")
            return

        collector = self.client.feed_collector(instruments, mode=FeedMode.FULL)

        await asyncio.gather(
            collector.run(self._on_packet),
            self._flush_bars(),
        )

    async def _run_dry(self) -> None:
        """Dry-run: generate synthetic futures ticks WITH VOLUME."""
        log.info("Futures recorder dry-run: generating 6 synthetic ticks (3 symbols × 2 minutes)")
        base_time = datetime.now()
        expiry = self._get_current_month_expiry()

        for minute in range(2):
            timestamp = base_time.replace(second=0, microsecond=0)
            timestamp = timestamp.replace(minute=base_time.minute + minute)

            for i, symbol in enumerate(self.symbols):
                base_price = 19850.0 + i * 100.0
                record = {
                    "symbol": symbol,
                    "expiry": expiry,
                    "timestamp": timestamp.isoformat(),
                    "open": base_price,
                    "high": base_price + 25.0,
                    "low": base_price - 18.0,
                    "close": base_price + 12.0,
                    "volume": 1234567 + i * 100000,  # CRITICAL: Volume present
                    "open_interest": 5000000 + i * 500000,
                }
                self.writer.write(record)

        log.info("Futures recorder dry-run complete")

    def close(self) -> None:
        """Close writer."""
        self.writer.close()
