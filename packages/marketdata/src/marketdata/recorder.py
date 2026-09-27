"""Market data recorder main loop (V2-D2).

Subscribes to FULL feed, emits DEPTH_QUOTE, QUOTE_SNAPSHOT, OI_CADENCE.
Writes to tape. Standalone, no engine required.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from contracts.payloads import DepthQuote, OiCadence, QuoteSnapshot
from dhan_client.config import Settings
from dhan_client.decode import DECODER_VERIFIED
from dhan_client.feed import MarketFeedCollector
from dhan_client.types import FeedMode

from marketdata.config import RecorderConfig
from marketdata.depth import DepthTracker
from marketdata.oi_cadence import OiCadenceTracker
from marketdata.quotes import QuoteTracker
from marketdata.strikes import StrikeSetManager
from marketdata.tape import TapeWriter


class MarketDataRecorder:
    """Main recorder: subscribes, tracks, emits, writes."""
    
    def __init__(self, config: RecorderConfig, settings: Settings) -> None:
        self.config = config
        self.settings = settings
        
        self.strike_manager = StrikeSetManager(
            underlying=config.underlying,
            retention_seconds=config.old_strike_retention_s,
        )
        self.depth_tracker = DepthTracker(
            throttle_ms=config.depth_throttle_ms,
            heartbeat_s=config.depth_heartbeat_s,
            stale_threshold_s=config.stale_depth_threshold_s,
        )
        self.quote_tracker = QuoteTracker(interval_s=config.quote_snapshot_interval_s)
        self.oi_tracker = OiCadenceTracker(window_s=config.oi_cadence_window_s)
        
        # Tape writers
        self.depth_writer = TapeWriter(config.tape_root, "depth_quotes")
        self.quote_writer = TapeWriter(config.tape_root, "quote_snapshots")
        self.oi_writer = TapeWriter(config.tape_root, "oi_cadence")
        self.raw_writer = TapeWriter(config.tape_root, "raw_frames")
        self.error_writer = TapeWriter(config.tape_root, "ingest_errors")
        
        self._collector: MarketFeedCollector | None = None
        self._session_start: datetime | None = None

    async def run(self) -> None:
        """Run the recorder."""
        # Start with a placeholder spot price to get initial strikes
        # In production, fetch from index or REST API
        initial_spot = 24500.0 if self.config.underlying == "NIFTY" else 80000.0
        new_instruments = self.strike_manager.update_spot(initial_spot)
        
        if not new_instruments:
            print(f"No instruments to subscribe for {self.config.underlying}")
            return
        
        self._collector = MarketFeedCollector(
            settings=self.settings,
            instruments=new_instruments,
            mode=FeedMode.FULL,
            reconnect=True,
        )
        
        print(f"Starting recorder for {self.config.underlying}: {len(new_instruments)} instruments")
        self._session_start = datetime.utcnow()
        
        try:
            await self._collector.run(on_packet=self._on_packet)
        finally:
            self._close_writers()

    async def _on_packet(self, payload: dict[str, Any]) -> None:
        """Handle one decoded packet from the feed."""
        now = datetime.utcnow()
        
        try:
            # Store raw frame if decoder not verified
            if not DECODER_VERIFIED and "raw_payload" in payload:
                raw_b64 = base64.b64encode(payload["raw_payload"]).decode("ascii")
                self.raw_writer.write({"ts": now.isoformat(), "raw_b64": raw_b64}, now)
            
            kind = payload.get("kind")
            if kind != "full":
                return
            
            security_id = str(payload.get("header", {}).get("security_id", ""))
            if not security_id:
                return
            
            # Extract fields
            fields = payload.get("fields", {})
            ltp = fields.get("ltp")
            oi = fields.get("oi")
            bid_depth = fields.get("bid_depth", [])
            ask_depth = fields.get("ask_depth", [])
            
            # Get strike rule/side
            strike_info = self.strike_manager.get_strike_rule(security_id)
            if not strike_info:
                return
            
            rule, side = strike_info
            
            # Update OI tracker
            if oi is not None:
                self.oi_tracker.update(security_id, oi)
            
            # Depth quote (throttled, with heartbeat)
            depth_data = {
                "ltp": ltp,
                "oi": oi,
                "bid_depth": bid_depth,
                "ask_depth": ask_depth,
            }
            should_emit, is_repeat = self.depth_tracker.should_emit(security_id, depth_data)
            if should_emit:
                stale = self.depth_tracker.is_stale(security_id)
                bid = bid_depth[0]["price"] if bid_depth else None
                bid_qty = bid_depth[0]["quantity"] if bid_depth else None
                ask = ask_depth[0]["price"] if ask_depth else None
                ask_qty = ask_depth[0]["quantity"] if ask_depth else None
                
                # Build levels dict for DepthQuote
                levels = {
                    "bid": [[d["price"], d["quantity"]] for d in bid_depth],
                    "ask": [[d["price"], d["quantity"]] for d in ask_depth],
                }
                
                depth_quote = DepthQuote(
                    instrument_id=security_id,
                    bid=bid,
                    bid_qty=bid_qty,
                    ask=ask,
                    ask_qty=ask_qty,
                    ltp=ltp,
                    oi=oi,
                    levels=levels,
                    exchange_ts=now.isoformat(),
                    repeat=is_repeat,
                    raw_b64=None,
                )
                self.depth_writer.write(depth_quote.__dict__, now)
            
            # Quote snapshot (every 5s)
            quote_data = {
                "bid": bid_depth[0]["price"] if bid_depth else None,
                "ask": ask_depth[0]["price"] if ask_depth else None,
                "ltp": ltp,
                "oi": oi,
            }
            if self.quote_tracker.should_emit(security_id, quote_data):
                bid = quote_data["bid"]
                ask = quote_data["ask"]
                mid = (bid + ask) / 2 if bid is not None and ask is not None else None
                spread = ask - bid if bid is not None and ask is not None else None
                
                quote_snapshot = QuoteSnapshot(
                    instrument_id=security_id,
                    rule=rule,
                    side=side,
                    bid=bid,
                    ask=ask,
                    mid=mid,
                    spread=spread,
                    ltp=ltp,
                    ltt=None,  # Not available in this packet
                    oi=oi,
                    depth_age_ms=None,  # Not tracked yet
                    stale=self.depth_tracker.is_stale(security_id),
                )
                self.quote_writer.write(quote_snapshot.__dict__, now)
            
            # OI cadence (every minute)
            if self.oi_tracker.should_emit(security_id):
                stats = self.oi_tracker.compute_stats(security_id)
                oi_cadence = OiCadence(
                    instrument_id=security_id,
                    window_s=self.config.oi_cadence_window_s,
                    oi_updates=stats["oi_updates"],
                    median_gap_s=stats["median_gap_s"],
                    p90_gap_s=stats["p90_gap_s"],
                    last_oi_change=now.isoformat(),
                    sources=["FULL"],
                )
                self.oi_writer.write(oi_cadence.__dict__, now)
                self.oi_tracker.reset_window(security_id)
        
        except Exception as e:
            # Log error and continue (REG-06)
            error_record = {
                "ts": now.isoformat(),
                "source": "on_packet",
                "reason": str(e),
                "sha256": hashlib.sha256(str(payload).encode()).hexdigest(),
            }
            self.error_writer.write(error_record, now)

    def _close_writers(self) -> None:
        """Close all tape writers."""
        self.depth_writer.close()
        self.quote_writer.close()
        self.oi_writer.close()
        self.raw_writer.close()
        self.error_writer.close()
