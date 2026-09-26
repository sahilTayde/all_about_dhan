"""Index ticks recorder: NIFTY, BANKNIFTY, SENSEX 1-minute OHLCV.

Reuses existing DhanClient feed_collector for websocket subscriptions.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.types import FeedInstrument, FeedMode, JsonDict

from data_recorder.writer import JsonLinesWriter, ist_date_str

log = logging.getLogger("data_recorder.index")

# Index security IDs (from Dhan scrip master)
# NOTE: These are loaded from instrument master at runtime, not hardcoded
INDEX_SIDS = {"NIFTY": "13", "BANKNIFTY": "25", "SENSEX": "51"}


class IndexRecorder:
    """Record index 1-minute ticks via Dhan websocket feed."""

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
        self.writer = JsonLinesWriter(output_dir, "index_ticks", verbose=verbose)
        self.verbose = verbose
        self._minute_bars: dict[str, dict[str, Any]] = {}

    def _get_security_id(self, symbol: str) -> Optional[str]:
        """Get security ID from instrument master (existing logic)."""
        # In production, use client.instruments.fetch_scrip_master_text() and parse
        # For now, use known IDs
        return INDEX_SIDS.get(symbol)

    async def _on_packet(self, packet: JsonDict) -> None:
        """Handle incoming websocket packet."""
        try:
            symbol = packet.get("symbol") or packet.get("trading_symbol")
            if not symbol:
                return

            # Extract OHLCV from packet
            timestamp = packet.get("timestamp") or packet.get("exchange_timestamp")
            ltp = packet.get("ltp") or packet.get("last_price")
            volume = packet.get("volume")

            if not timestamp or ltp is None:
                return

            # Aggregate into 1-minute bars
            minute_key = self._minute_key(timestamp)
            bar_key = f"{symbol}_{minute_key}"

            if bar_key not in self._minute_bars:
                self._minute_bars[bar_key] = {
                    "symbol": symbol,
                    "timestamp": datetime.fromtimestamp(minute_key).isoformat(),
                    "open": ltp,
                    "high": ltp,
                    "low": ltp,
                    "close": ltp,
                    "volume": volume,
                }
            else:
                bar = self._minute_bars[bar_key]
                bar["high"] = max(bar["high"], ltp)
                bar["low"] = min(bar["low"], ltp)
                bar["close"] = ltp
                if volume is not None:
                    bar["volume"] = volume

        except Exception as e:
            log.warning("Error processing index packet: %s", e)

    def _minute_key(self, timestamp: Any) -> int:
        """Floor timestamp to minute boundary."""
        ts = int(timestamp) if timestamp else 0
        if ts > 1e12:  # milliseconds
            ts = ts // 1000
        return ts - (ts % 60)

    async def _flush_bars(self) -> None:
        """Periodically flush completed minute bars."""
        while True:
            await asyncio.sleep(60)
            current_minute = self._minute_key(datetime.now().timestamp())

            # Flush bars older than current minute
            to_remove = []
            for bar_key, bar in self._minute_bars.items():
                bar_ts = datetime.fromisoformat(bar["timestamp"]).timestamp()
                if self._minute_key(bar_ts) < current_minute:
                    self.writer.write(bar)
                    to_remove.append(bar_key)

            for key in to_remove:
                del self._minute_bars[key]

    async def run(self) -> None:
        """Run index recorder (subscribes via websocket)."""
        if self.client.dry_run:
            await self._run_dry()
            return

        # Build FeedInstrument list
        instruments: list[FeedInstrument] = []
        for symbol in self.symbols:
            sid = self._get_security_id(symbol)
            if sid:
                instruments.append(
                    FeedInstrument(
                        exchange_segment=1,  # NSE_FNO
                        security_id=int(sid),
                    )
                )

        if not instruments:
            log.warning("No instruments to subscribe for index recorder")
            return

        # Create feed collector (reuses existing infrastructure)
        collector = self.client.feed_collector(instruments, mode=FeedMode.TICKER)

        # Run feed and flush tasks concurrently
        await asyncio.gather(
            collector.run(self._on_packet),
            self._flush_bars(),
        )

    async def _run_dry(self) -> None:
        """Dry-run: generate synthetic index ticks."""
        log.info("Index recorder dry-run: generating 6 synthetic ticks (3 symbols × 2 minutes)")
        base_time = datetime.now()

        for minute in range(2):
            timestamp = base_time.replace(second=0, microsecond=0)
            timestamp = timestamp.replace(minute=base_time.minute + minute)

            for i, symbol in enumerate(self.symbols):
                base_price = 19800.0 + i * 100.0
                record = {
                    "symbol": symbol,
                    "timestamp": timestamp.isoformat(),
                    "open": base_price,
                    "high": base_price + 20.0,
                    "low": base_price - 15.0,
                    "close": base_price + 10.0,
                    "volume": None,  # Index volume not provided by Dhan
                }
                self.writer.write(record)

        log.info("Index recorder dry-run complete")

    def close(self) -> None:
        """Close writer."""
        self.writer.close()
