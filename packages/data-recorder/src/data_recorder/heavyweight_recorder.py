"""Heavyweight stocks recorder: top 15 NIFTY components for breadth analysis.

Reuses existing DhanClient feed infrastructure.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.types import FeedInstrument, FeedMode, JsonDict

from data_recorder.writer import JsonLinesWriter

log = logging.getLogger("data_recorder.heavyweight")


class HeavyweightRecorder:
    """Record heavyweight stock ticks via Dhan websocket feed."""

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
        self.writer = JsonLinesWriter(output_dir, "heavyweight_ticks", verbose=verbose)
        self.verbose = verbose
        self._minute_bars: dict[str, dict[str, Any]] = {}

    def _get_instrument_for_stock(
        self, symbol: str, instruments_data: dict[str, Any]
    ) -> Optional[FeedInstrument]:
        """Look up equity instrument from parsed instrument master."""
        heavyweights = instruments_data.get("heavyweights", {})
        
        if symbol in heavyweights:
            return FeedInstrument(
                exchange_segment=0,  # NSE_EQ
                security_id=heavyweights[symbol],
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
            log.warning("Error processing heavyweight packet: %s", e)

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

    async def run(self, instruments_data: dict[str, Any]) -> None:
        """Run heavyweight recorder (subscribes via websocket)."""
        if self.client.dry_run:
            await self._run_dry()
            return

        # Build FeedInstrument list
        instruments: list[FeedInstrument] = []
        for symbol in self.symbols:
            inst = self._get_instrument_for_stock(symbol, instruments_data)
            if inst:
                instruments.append(inst)
            else:
                log.warning("No security ID found for heavyweight: %s", symbol)

        if not instruments:
            log.warning("No instruments to subscribe for heavyweight recorder")
            return

        collector = self.client.feed_collector(instruments, mode=FeedMode.TICKER, reconnect=True)

        await asyncio.gather(
            collector.run(self._on_packet),
            self._flush_bars(),
        )

    async def _run_dry(self) -> None:
        """Dry-run: generate synthetic heavyweight ticks."""
        log.info(
            "Heavyweight recorder dry-run: generating %d synthetic ticks (%d stocks × 2 minutes)",
            len(self.symbols) * 2,
            len(self.symbols),
        )
        base_time = datetime.now()

        for minute in range(2):
            timestamp = base_time.replace(second=0, microsecond=0)
            timestamp = timestamp.replace(minute=base_time.minute + minute)

            for i, symbol in enumerate(self.symbols):
                base_price = 2500.0 + i * 100.0
                record = {
                    "symbol": symbol,
                    "timestamp": timestamp.isoformat(),
                    "open": base_price,
                    "high": base_price + 12.0,
                    "low": base_price - 8.0,
                    "close": base_price + 5.0,
                    "volume": 50000 + i * 5000,
                }
                self.writer.write(record)

        log.info("Heavyweight recorder dry-run complete")

    def close(self) -> None:
        """Close writer."""
        self.writer.close()
