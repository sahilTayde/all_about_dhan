"""Market data recorder main loop (V2-D2) - all verification fixes applied."""

from __future__ import annotations

import asyncio
import base64
import json
import signal
from datetime import datetime, time, timezone
from typing import Any

from dhan_client.config import Settings
from dhan_client.decode import DECODER_VERIFIED, DecodeError, decode_frame
from dhan_client.feed import MarketFeedCollector
from dhan_client.types import FeedMode

from marketdata.config import RecorderConfig
from marketdata.instruments import resolve_instruments
from marketdata.tape import TapeWriter
from marketdata.types import DepthQuote, IngestError, OiCadence, QuoteSnapshot
from marketdata.utils import compute_sha256, ist_date_str, to_ist_timestamp


class MarketDataRecorder:
    """Main recorder with all verification fixes."""

    def __init__(self, config: RecorderConfig, settings: Settings) -> None:
        self.config = config
        self.settings = settings
        self.instruments: dict[str, tuple[Any, str, str]] = {}
        self.instrument_list: list[Any] = []
        
        # State tracking
        self.last_packet_ts: dict[str, float] = {}
        self.last_depth_emit: dict[str, float] = {}
        self.last_depth_data: dict[str, dict[str, Any]] = {}
        self.last_quote_emit: dict[str, float] = {}
        self.oi_state: dict[str, list[tuple[float, int]]] = {}  # [(ts, oi), ...]
        self.oi_window_start: dict[str, float] = {}
        
        self.depth_writer = TapeWriter(config.tape_root, "depth_quotes")
        self.quote_writer = TapeWriter(config.tape_root, "quote_snapshots")
        self.oi_writer = TapeWriter(config.tape_root, "oi_cadence")
        self.raw_writer = TapeWriter(config.tape_root, "raw_frames")
        self.error_writer = TapeWriter(config.tape_root, "ingest_errors")
        
        self._collector: MarketFeedCollector | None = None
        self._stop_event = asyncio.Event()
        self._clock_task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        """Run the recorder until 15:30 IST."""
        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: self._stop_event.set())
        
        # Resolve instruments (placeholder spot for now)
        initial_spot = 24500.0 if self.config.underlying == "NIFTY" else 80000.0
        self.instruments = resolve_instruments(self.config.underlying, initial_spot)
        self.instrument_list = [inst for inst, _, _ in self.instruments.values()]
        
        print(f"Resolved {len(self.instrument_list)} instruments")
        
        # Start collector
        self._collector = MarketFeedCollector(
            settings=self.settings,
            instruments=self.instrument_list,
            mode=FeedMode.FULL,
            reconnect=True,
        )
        
        # Start clock task
        self._clock_task = asyncio.create_task(self._clock_loop())
        
        # Start flush timers
        asyncio.create_task(self.depth_writer.start_flush_timer())
        asyncio.create_task(self.quote_writer.start_flush_timer())
        asyncio.create_task(self.oi_writer.start_flush_timer())
        asyncio.create_task(self.raw_writer.start_flush_timer())
        asyncio.create_task(self.error_writer.start_flush_timer())
        
        try:
            # Run collector with raw frame hook
            await self._collector.run(on_packet=self._on_packet_wrapper)
        finally:
            self._cleanup()

    def _on_packet_wrapper(self, payload: dict[str, Any]) -> None:
        """Wrapper to catch raw frames before processing."""
        # Write raw frame if decoder not verified
        if not DECODER_VERIFIED and "raw_payload" in payload:
            try:
                now = datetime.utcnow()
                raw_b64 = base64.b64encode(payload["raw_payload"]).decode("ascii")
                self.raw_writer.write(
                    {
                        "ts": to_ist_timestamp(now),
                        "raw_b64": raw_b64,
                        "kind": payload.get("kind"),
                    },
                    now,
                )
            except Exception:
                pass
        
        # Process packet
        asyncio.create_task(self._on_packet(payload))

    async def _on_packet(self, payload: dict[str, Any]) -> None:
        """Handle decoded packet - FIXED to read security_id from top level."""
        now = datetime.utcnow()
        
        try:
            # FIX 1: Read security_id from TOP LEVEL (not payload["header"])
            security_id = str(payload.get("security_id", ""))
            if not security_id or security_id not in self.instruments:
                return
            
            _, instrument_id, rule_side = self.instruments[security_id]
            rule, side = rule_side.split("|")
            
            # Track packet arrival time
            self.last_packet_ts[security_id] = now.timestamp()
            
            kind = payload.get("kind")
            if kind not in ("full", "index"):
                return
            
            fields = payload.get("fields", {})
            ltp = fields.get("ltp")
            oi = fields.get("oi")
            ltt = fields.get("last_trade_time_epoch")
            
            # Extract depth
            bid_depth = fields.get("bid_depth", [])
            ask_depth = fields.get("ask_depth", [])
            
            # Update OI tracking
            if oi is not None:
                self._update_oi(security_id, now.timestamp(), oi)
            
            # Emit depth (throttled)
            await self._emit_depth_if_needed(
                security_id, instrument_id, now, ltp, oi, ltt, bid_depth, ask_depth
            )
            
        except Exception as e:
            # Log error
            await self._log_ingest_error(
                now, "on_packet", str(e), None, payload
            )

    async def _emit_depth_if_needed(
        self,
        security_id: str,
        instrument_id: str,
        now: datetime,
        ltp: float | None,
        oi: int | None,
        ltt: int | None,
        bid_depth: list[dict[str, Any]],
        ask_depth: list[dict[str, Any]],
    ) -> None:
        """Emit depth with throttling."""
        now_ts = now.timestamp()
        last_emit = self.last_depth_emit.get(security_id, 0)
        
        # Throttle: 250ms minimum
        if now_ts - last_emit < 0.25:
            # Update last data but don't emit yet
            self.last_depth_data[security_id] = {
                "ltp": ltp,
                "oi": oi,
                "ltt": ltt,
                "bid_depth": bid_depth,
                "ask_depth": ask_depth,
            }
            return
        
        # Emit
        self.last_depth_emit[security_id] = now_ts
        self.last_depth_data[security_id] = {
            "ltp": ltp,
            "oi": oi,
            "ltt": ltt,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
        }
        
        # Build depth quote
        bid = bid_depth[0]["price"] if bid_depth else None
        bid_qty = bid_depth[0]["quantity"] if bid_depth else None
        ask = ask_depth[0]["price"] if ask_depth else None
        ask_qty = ask_depth[0]["quantity"] if ask_depth else None
        
        levels = {
            "bid": [[d["price"], d["quantity"]] for d in bid_depth],
            "ask": [[d["price"], d["quantity"]] for d in ask_depth],
        }
        
        # Check staleness
        stale = False  # Will be set by clock task
        
        depth_quote = DepthQuote(
            instrument_id=instrument_id,
            bid=bid,
            bid_qty=bid_qty,
            ask=ask,
            ask_qty=ask_qty,
            ltp=ltp,
            oi=oi,
            levels=levels,
            exchange_ts=to_ist_timestamp(now),
            repeat=False,
            stale=stale,
            raw_b64=None,
        )
        
        try:
            self.depth_writer.write(depth_quote.__dict__, now)
        except ValueError as e:
            # NaN/Inf error
            await self._log_ingest_error(now, "depth_write", str(e), None, depth_quote.__dict__)

    def _update_oi(self, security_id: str, ts: float, oi: int) -> None:
        """Track OI changes."""
        if security_id not in self.oi_state:
            self.oi_state[security_id] = []
            self.oi_window_start[security_id] = ts
        
        # Check if OI changed
        if not self.oi_state[security_id] or self.oi_state[security_id][-1][1] != oi:
            self.oi_state[security_id].append((ts, oi))

    async def _clock_loop(self) -> None:
        """1-second clock for heartbeats, snapshots, OI cadence."""
        while not self._stop_event.is_set():
            await asyncio.sleep(1.0)
            
            now = datetime.utcnow()
            now_ts = now.timestamp()
            
            # Check if we should stop at 15:30 IST
            if self._should_stop_recording(now):
                print("Reached 15:30 IST, stopping recorder...")
                await self._write_coverage_summary(now)
                self._stop_event.set()
                return
            
            # Heartbeat: emit repeat depth for instruments with no recent packet
            for security_id in list(self.last_packet_ts.keys()):
                last_pkt = self.last_packet_ts.get(security_id, 0)
                last_emit = self.last_depth_emit.get(security_id, 0)
                
                # Heartbeat every 1s if no new data
                if now_ts - last_emit >= 1.0:
                    await self._emit_heartbeat(security_id, now, now_ts - last_pkt > 5.0)
            
            # Quote snapshots every 5s (on 5s boundaries)
            if int(now_ts) % 5 == 0:
                await self._emit_quote_snapshots(now)
            
            # OI cadence every minute (on minute boundaries)
            if int(now_ts) % 60 == 0:
                await self._emit_oi_cadence(now)

    async def _emit_heartbeat(self, security_id: str, now: datetime, stale: bool) -> None:
        """Emit heartbeat depth quote."""
        if security_id not in self.last_depth_data:
            return
        
        _, instrument_id, _ = self.instruments[security_id]
        data = self.last_depth_data[security_id]
        
        bid_depth = data.get("bid_depth", [])
        ask_depth = data.get("ask_depth", [])
        
        depth_quote = DepthQuote(
            instrument_id=instrument_id,
            bid=bid_depth[0]["price"] if bid_depth else None,
            bid_qty=bid_depth[0]["quantity"] if bid_depth else None,
            ask=ask_depth[0]["price"] if ask_depth else None,
            ask_qty=ask_depth[0]["quantity"] if ask_depth else None,
            ltp=data.get("ltp"),
            oi=data.get("oi"),
            levels={
                "bid": [[d["price"], d["quantity"]] for d in bid_depth],
                "ask": [[d["price"], d["quantity"]] for d in ask_depth],
            },
            exchange_ts=to_ist_timestamp(now),
            repeat=True,
            stale=stale,
            raw_b64=None,
        )
        
        try:
            self.depth_writer.write(depth_quote.__dict__, now)
            self.last_depth_emit[security_id] = now.timestamp()
        except ValueError:
            pass

    async def _emit_quote_snapshots(self, now: datetime) -> None:
        """Emit quote snapshots every 5s (options only)."""
        for security_id, (_, instrument_id, rule_side) in self.instruments.items():
            rule, side = rule_side.split("|")
            
            # Skip INDEX/FUTURE
            if side in ("INDEX", "FUTURE"):
                continue
            
            if security_id not in self.last_depth_data:
                continue
            
            data = self.last_depth_data[security_id]
            last_pkt_ts = self.last_packet_ts.get(security_id, 0)
            depth_age_ms = int((now.timestamp() - last_pkt_ts) * 1000)
            
            bid_depth = data.get("bid_depth", [])
            ask_depth = data.get("ask_depth", [])
            bid = bid_depth[0]["price"] if bid_depth else None
            ask = ask_depth[0]["price"] if ask_depth else None
            mid = (bid + ask) / 2 if bid and ask else None
            spread = ask - bid if bid and ask else None
            
            # Convert LTT epoch to ISO timestamp
            ltt_epoch = data.get("ltt")
            ltt_str = None
            if ltt_epoch:
                ltt_dt = datetime.fromtimestamp(ltt_epoch, tz=timezone.utc)
                ltt_str = to_ist_timestamp(ltt_dt)
            
            quote = QuoteSnapshot(
                instrument_id=instrument_id,
                rule=rule,
                side=side,
                bid=bid,
                ask=ask,
                mid=mid,
                spread=spread,
                ltp=data.get("ltp"),
                ltt=ltt_str,
                oi=data.get("oi"),
                depth_age_ms=depth_age_ms,
                stale=depth_age_ms > 5000,
            )
            
            try:
                self.quote_writer.write(quote.__dict__, now)
            except ValueError:
                pass

    async def _emit_oi_cadence(self, now: datetime) -> None:
        """Emit OI cadence stats every minute."""
        for security_id, changes in list(self.oi_state.items()):
            if len(changes) < 2:
                # Not enough data
                continue
            
            _, instrument_id, _ = self.instruments[security_id]
            
            # Compute gaps (excluding first observation which isn't a "change")
            if len(changes) > 1:
                gaps = [changes[i][0] - changes[i-1][0] for i in range(1, len(changes))]
                gaps.sort()
                
                median = gaps[len(gaps) // 2] if gaps else None
                p90_idx = int(len(gaps) * 0.9)
                p90 = gaps[min(p90_idx, len(gaps) - 1)] if gaps else None
                
                oi_cadence = OiCadence(
                    instrument_id=instrument_id,
                    window_s=60,
                    oi_updates=len(changes) - 1,  # Exclude first
                    median_gap_s=round(median, 2) if median else None,
                    p90_gap_s=round(p90, 2) if p90 else None,
                    last_oi_change=to_ist_timestamp(datetime.fromtimestamp(changes[-1][0], tz=timezone.utc)),
                    sources=["FULL"],
                )
                
                try:
                    self.oi_writer.write(oi_cadence.__dict__, now)
                except ValueError:
                    pass
            
            # Reset for next window
            self.oi_state[security_id] = []
            self.oi_window_start[security_id] = now.timestamp()

    def _should_stop_recording(self, now: datetime) -> bool:
        """Check if we should stop at 15:30 IST."""
        # IST is UTC+5:30
        from datetime import timedelta
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        ist_now = now.replace(tzinfo=timezone.utc).astimezone(ist_offset)
        stop_time = time(15, 30)
        return ist_now.time() >= stop_time

    async def _write_coverage_summary(self, now: datetime) -> None:
        """Write daily coverage summary."""
        summary = {
            "date": ist_date_str(now),
            "underlying": self.config.underlying,
            "instruments": {},
        }
        
        # TODO: Calculate per-instrument coverage
        # For now, just write placeholder
        for security_id, (_, instrument_id, _) in self.instruments.items():
            summary["instruments"][instrument_id] = {
                "coverage_pct": 0.0,
                "gaps": [],
            }
        
        summary_path = self.config.tape_root / ist_date_str(now) / "coverage_summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

    async def _log_ingest_error(
        self,
        now: datetime,
        source: str,
        reason: str,
        offset: int | None,
        data: Any,
    ) -> None:
        """Log ingest error."""
        try:
            data_bytes = str(data).encode()
            error = IngestError(
                ts=to_ist_timestamp(now),
                source=source,
                reason=reason,
                offset=offset,
                sha256=compute_sha256(data_bytes),
                raw_b64=base64.b64encode(data_bytes[:1024]).decode() if data_bytes else None,
            )
            self.error_writer.write(error.__dict__, now)
        except Exception:
            pass

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._clock_task:
            self._clock_task.cancel()
        self.depth_writer.close()
        self.quote_writer.close()
        self.oi_writer.close()
        self.raw_writer.close()
        self.error_writer.close()
