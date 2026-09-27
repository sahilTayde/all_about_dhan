"""V2-D2 recorder: FULL-mode feed -> DEPTH_QUOTE, QUOTE_SNAPSHOT, OI_CADENCE tapes.

Record only. It subscribes to the market feed and reads REST data endpoints; it has no
order code path. Every row is an Envelope v2 (``timestamp``/``available_ts`` = when the row
was written, ``event_ts`` = when the data was received) whose ``payload`` matches the
vendored V2-01 JSON schema for its type (``marketdata/schemas``).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import math
import threading
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from dhan_client.config import Settings
from dhan_client.decode import DECODER_VERIFIED
from dhan_client.errors import CredentialsError
from dhan_client.feed import MarketFeedCollector
from dhan_client.types import FeedMode

from marketdata import logsafe
from marketdata.clock import IST, Clock, LiveClock, iso, market_close, market_open, session_day
from marketdata.config import RecorderConfig
from marketdata.coverage import write_summary
from marketdata.depth import DepthTracker, quote_from_full, quote_from_ltp
from marketdata.frames import Packet, decode_frame_checked
from marketdata.instruments import (
    Instrument,
    InstrumentSource,
    StartupError,
    Universe,
    load_cached_universe,
    load_universe,
    save_universe,
)
from marketdata.oi_cadence import OiCadenceTracker
from marketdata.quotes import snapshot
from marketdata.strikes import Change, StrikeSet
from marketdata.tape import TapeWriter

log = logging.getLogger(__name__)

# event type -> (file stem, stream)
ENVELOPE_STREAMS = {
    "DEPTH_QUOTE": ("depth_quotes", "md:depth"),
    "QUOTE_SNAPSHOT": ("quote_snapshots", "md:quotes"),
    "OI_CADENCE": ("oi_cadence", "md:oi_cadence"),
    "FEED_STATUS": ("feed_status", "md:status"),
}
PLAIN_STREAMS = ("raw_frames", "ingest_errors", "subscriptions")
# Live-feed disconnect codes for unusable credentials or no data plan (annexure 806-810).
AUTH_DISCONNECT_CODES = frozenset({806, 807, 808, 809, 810})
IST_EPOCH_SHIFT = 19800


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _http_status(exc: BaseException | None) -> int | None:
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None) or getattr(exc, "status_code", None)
    return status if isinstance(status, int) else None


class _StoppedError(Exception):
    """A stop was requested while startup was retrying."""


@dataclass
class Stats:
    frames: int = 0
    packets: int = 0
    ingest_errors: int = 0
    late_packets: int = 0


class MarketDataRecorder:
    def __init__(
        self,
        config: RecorderConfig,
        settings: Settings,
        *,
        source: InstrumentSource | None = None,
        universe: Universe | None = None,
        clock: Clock | None = None,
    ) -> None:
        if source is None and universe is None:
            raise ValueError("pass an InstrumentSource or a resolved Universe")
        self.config = config
        self.settings = settings
        self.source = source
        self.universe = universe
        self.clock: Clock = clock or LiveClock()
        self.tape = {
            name: TapeWriter(config.tape_root, name, background=True)
            for name in [s for s, _ in ENVELOPE_STREAMS.values()] + list(PLAIN_STREAMS)
        }
        self.depth = DepthTracker(config.depth_throttle_s, config.depth_heartbeat_s)
        self.oi = OiCadenceTracker(config.oi_window_s)
        self.stats = Stats()
        self.exit_code = 0
        self.stop_reason: str | None = None
        self._stop_event = threading.Event()
        self.collector: MarketFeedCollector | None = None
        self.strikes: StrikeSet | None = None
        self.spot: float = universe.spot if universe else 0.0
        self._by_security: dict[tuple[str, str], Instrument] = {}
        self._unknown_seen: set[tuple[str, str]] = set()
        self._stale: set[str] = set()
        self._connected = False
        self._down_since: datetime | None = None
        self._auth_failures = 0
        self._errors_seen = 0
        self._connects_seen = 0
        self._up_since_s = float("-inf")
        self._subscribed_s: dict[str, float] = {}
        self._last_spot_s = float("-inf")
        self._last_spot_poll_s = float("-inf")
        self._spot_poll: asyncio.Task[None] | None = None
        self._ltt_shift: int | None = None
        self._implausible_logged_s = float("-inf")
        self._open_dt: datetime | None = None

    # ---- lifecycle -------------------------------------------------------------------

    def request_stop(self, reason: str = "stop requested (signal)", exit_code: int = 0) -> None:
        if self.stop_reason is None:
            self.stop_reason = reason
            self.exit_code = exit_code
            log.warning("stopping: %s", reason)
        self._stop_event.set()
        if self.collector is not None:
            self.collector.stop()

    def _retry_sleep(self, seconds: float) -> None:
        """Sleep between startup retries (worker thread); ends at once when a stop is requested."""
        if self._stop_event.wait(seconds):
            raise _StoppedError

    async def _nap(self, seconds: float) -> None:
        await self.clock.sleep(seconds)

    async def _wait_until(self, when: datetime) -> None:
        while self.stop_reason is None and self.clock.now() < when:
            await self._nap(min(1.0, (when - self.clock.now()).total_seconds()))

    async def run(self) -> int:
        if self.settings.dry_run or not self.settings.credentials.has_access:
            raise CredentialsError("live recording needs DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN")
        creds = self.settings.credentials
        logsafe.install([creds.client_id, creds.access_token])
        now = self.clock.now()
        day = session_day(now)
        open_dt, close_dt = market_open(day), market_close(day)
        self._open_dt = open_dt
        if self.universe is None:
            self.universe = await self._load_universe(day, open_dt)
            if self.universe is None:
                return self.exit_code
            self.spot = self.universe.spot
        universe = self.universe
        self.strikes = StrikeSet(
            universe, retention_s=self.config.retention_s, max_instruments=self.config.max_instruments
        )
        self._by_security = {(i.exchange_segment, i.security_id): i for i in universe.all_instruments()}

        connect_at = open_dt - timedelta(seconds=self.config.connect_early_s)
        if self.clock.now() < connect_at:
            log.info(
                "session %s: waiting until %s to connect (market %s-%s IST)",
                day,
                iso(connect_at),
                open_dt.strftime("%H:%M"),
                close_dt.strftime("%H:%M"),
            )
            await self._wait_until(connect_at)
            if self.stop_reason is not None:
                return self.exit_code

        start = self.clock.now()
        self._last_spot_s = start.timestamp()  # the spot fallback counts from the connect
        for writer in self.tape.values():
            repaired = writer.open(start)
            if repaired:
                log.warning("repaired %s: removed %d bytes", writer.path, repaired["removed_bytes"])
                self._error(repaired["reason"], start, **{k: v for k, v in repaired.items() if k != "reason"})
        first = self.strikes.update(self.spot, start.timestamp())
        self._log_change(first, start, "start")
        self.collector = MarketFeedCollector(
            self.settings,
            [i.feed for i in first.subscribe],
            mode=FeedMode.FULL,
            reconnect=True,
            max_backoff_seconds=self.config.max_backoff_s,
        )
        log.info(
            "recording %s expiry=%s spot=%.2f atm=%s instruments=%d into %s",
            universe.underlying,
            universe.expiry,
            self.spot,
            self.strikes.atm,
            len(first.subscribe),
            self.config.tape_root / day.isoformat(),
        )
        feed = asyncio.create_task(self.collector.run(on_frame=self._on_frame))
        try:
            await self._clock_loop(feed, close_dt)
        finally:
            self.collector.stop()
            feed.cancel()
            await asyncio.gather(feed, return_exceptions=True)
            if self._spot_poll is not None:
                self._spot_poll.cancel()
            end = self.clock.now()
            self._status(end, "DOWN", detail=self.stop_reason or "stopped")
            for writer in self.tape.values():
                writer.close()
            self._write_coverage(day)
            log.info(
                "recorder stopped (%s): frames=%d packets=%d rows %s",
                self.stop_reason,
                self.stats.frames,
                self.stats.packets,
                {name: w.rows for name, w in self.tape.items()},
            )
        return self.exit_code

    async def _load_universe(self, day: date, open_dt: datetime) -> Universe | None:
        assert self.source is not None
        cache = self.config.cache_dir
        deadline = max(open_dt + timedelta(minutes=5), self.clock.now() + timedelta(minutes=2))
        while True:
            try:
                universe = await asyncio.to_thread(
                    load_universe,
                    self.source,
                    self.config.underlying,
                    day,
                    attempts=self.config.startup_attempts,
                    sleep=self._retry_sleep,
                )
            except _StoppedError:
                return None
            except StartupError as exc:
                if not exc.retryable:
                    raise
                if self.stop_reason is not None:
                    return None
                if self.clock.now() >= deadline:
                    cached = load_cached_universe(cache, self.config.underlying, day) if cache else None
                    if cached is None:
                        raise
                    log.error("instrument load failed (%s); using cached instruments %s", exc, cached[1])
                    return cached[0]
                log.warning("instrument load failed (%s); retrying until %s", exc, iso(deadline))
                await self._nap(self.config.startup_retry_s)
                continue
            if cache is not None:
                save_universe(universe, cache, day)
            return universe

    def _write_coverage(self, day: date) -> None:
        try:
            path = write_summary(self.config.tape_root / day.isoformat(), day)
            log.info("coverage summary: %s", path)
        except Exception:
            log.exception("coverage summary failed")

    async def _clock_loop(self, feed: asyncio.Task[None], close_dt: datetime) -> None:
        last_s = self.clock.now().timestamp()
        while True:
            now = self.clock.now()
            now_s = now.timestamp()
            if self.stop_reason is not None:
                return
            if now >= close_dt:
                self.request_stop(f"market close {close_dt.strftime('%H:%M')} IST")
                return
            if feed.done():
                exc = feed.exception()
                self.request_stop(f"feed task ended: {exc!r}", exit_code=1)
                return
            await self._tick(now, now_s, last_s)
            last_s = now_s
            await self._nap(self.config.tick_s)

    # ---- periodic work ---------------------------------------------------------------

    async def _tick(self, now: datetime, now_s: float, last_s: float) -> None:
        assert self.collector is not None
        assert self.strikes is not None
        self._watch_connection(now)
        for payload in self.depth.tick(now_s, heartbeat=self._connected):
            self._emit("DEPTH_QUOTE", payload, now, payload["exchange_ts"])

        interval = self.config.quote_interval_s
        if math.floor(now_s / interval) > math.floor(last_s / interval):
            for iid, (rule, side) in self.strikes.current.items():
                row = snapshot(iid, rule, side, self.depth.books.get(iid), now_s, self.config.stale_after_s)
                self._emit("QUOTE_SNAPSHOT", row, now, iso(now))

        window = self.config.oi_window_s
        if math.floor(now_s / window) > math.floor(last_s / window):
            end_s = math.floor(now_s / window) * window
            for row in self.oi.close_window(end_s):
                self._emit("OI_CADENCE", row, now, iso(datetime.fromtimestamp(end_s, IST)))
            self._log_status(now)

        if math.floor(now_s) > math.floor(last_s):
            self._watch_staleness(now, now_s)
            await self._apply(self.strikes.update(self.spot, now_s), now, "retention")
            self._maybe_poll_spot(now, now_s)
            for writer in self.tape.values():
                writer.flush()

    def _watch_connection(self, now: datetime) -> None:
        assert self.collector is not None
        connected = self.collector.connected
        if connected and self._connected and self.collector.connect_count != self._connects_seen:
            self._status(now, "DOWN", detail="websocket closed and reopened between ticks")
            log.warning("feed reconnected between ticks")
            self._down_since, self._connected = now, False
        if connected and not self._connected:
            self._connects_seen = self.collector.connect_count
            self._up_since_s = now.timestamp()
            gap = (now - self._down_since).total_seconds() if self._down_since else None
            self._status(now, "UP", gap_s=gap, detail=f"connect #{self.collector.connect_count}")
            log.info("feed connected (connect #%d)", self.collector.connect_count)
            self._auth_failures = 0
        elif self._connected and not connected:
            self._down_since = now
            self._status(now, "DOWN", detail="websocket closed; reconnecting with backoff")
            log.warning("feed disconnected; reconnecting with backoff")
        self._connected = connected
        new_errors = self.collector.error_count - self._errors_seen
        err = self.collector.last_error
        if new_errors > 0 and err is not None:
            self._errors_seen = self.collector.error_count
            status = _http_status(err)
            log.error("feed connection failed: %s", type(err).__name__ + (f" HTTP {status}" if status else ""))
            if status in (401, 403):
                self._auth_failures += new_errors
                if self._auth_failures >= self.config.max_auth_failures:
                    self._status(now, "AUTH_FAILED", detail=f"websocket handshake HTTP {status}")
                    self.request_stop(
                        f"Dhan rejected the feed login {self._auth_failures} times (HTTP {status}); "
                        "check DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN",
                        exit_code=2,
                    )

    def _watch_staleness(self, now: datetime, now_s: float) -> None:
        assert self.strikes is not None
        assert self._open_dt is not None
        if not self._connected or now < self._open_dt:
            return
        for iid in self.strikes.subscribed:
            age = self.depth.age_s(iid, now_s)
            if age is None:  # nothing received yet: count from subscription / reconnect
                waited = now_s - max(self._subscribed_s.get(iid, now_s), self._up_since_s)
                stale = waited > self.config.stale_after_s
            else:
                stale = age > self.config.stale_after_s
            if stale and iid not in self._stale:
                self._stale.add(iid)
                self._status(now, "STALE", instrument_id=iid, gap_s=None if age is None else round(age, 3))
            elif not stale and iid in self._stale:
                self._stale.discard(iid)
                self._status(now, "FRESH", instrument_id=iid)

    def _maybe_poll_spot(self, now: datetime, now_s: float) -> None:
        assert self._open_dt is not None
        assert self.universe is not None
        if (
            self.source is None
            or not self._connected
            or now < self._open_dt
            or now_s - self._last_spot_s < self.config.spot_fallback_after_s
            or now_s - self._last_spot_poll_s < self.config.spot_poll_s
            or (self._spot_poll is not None and not self._spot_poll.done())
        ):
            return
        self._last_spot_poll_s = now_s
        self._spot_poll = asyncio.create_task(self._poll_spot())

    async def _poll_spot(self) -> None:
        assert self.source is not None
        assert self.universe is not None
        u = self.universe
        try:
            chain = await asyncio.to_thread(self.source.option_chain, int(u.index.security_id), "IDX_I", u.expiry)
            spot = float(chain.get("last_price") or 0.0)
        except Exception as exc:
            log.warning("spot fallback via option chain failed: %s", type(exc).__name__)
            return
        if spot > 0:
            log.info(
                "no index tick for %.0fs; spot %.2f from the option chain", self.config.spot_fallback_after_s, spot
            )
            now = self.clock.now()
            await self._on_spot(spot, now, now.timestamp(), from_feed=False)

    def _log_status(self, now: datetime) -> None:
        assert self.strikes is not None
        log.info(
            "%s connected=%s frames=%d packets=%d rows depth=%d quotes=%d oi=%d errors=%d "
            "spot=%.2f atm=%s subscribed=%d stale=%d",
            now.strftime("%H:%M"),
            self._connected,
            self.stats.frames,
            self.stats.packets,
            self.tape["depth_quotes"].rows,
            self.tape["quote_snapshots"].rows,
            self.tape["oi_cadence"].rows,
            self.stats.ingest_errors,
            self.spot,
            self.strikes.atm,
            len(self.strikes.subscribed),
            len(self._stale),
        )

    # ---- feed input ------------------------------------------------------------------

    async def _on_frame(self, raw: bytes | str) -> None:
        now = self.clock.now()
        self.stats.frames += 1
        if isinstance(raw, str):
            self._error("text frame (feed responses are binary)", now, text=raw[:1000])
            return
        if not DECODER_VERIFIED:
            self._write("raw_frames", {"recv_ts": iso(now), "raw_b64": _b64(raw)}, now)
        packets, errors = decode_frame_checked(raw)
        for err in errors:
            self._error(
                err.reason,
                now,
                offset=err.offset,
                frame_len=len(raw),
                sha256=hashlib.sha256(err.raw).hexdigest(),
                raw_b64=_b64(err.raw),
            )
        for packet in packets:
            if not packet.finite:
                self._error(
                    f"non-finite value in {packet.decoded.kind} packet; written as null",
                    now,
                    security_id=str(packet.decoded.header.security_id),
                    sha256=hashlib.sha256(packet.raw).hexdigest(),
                    raw_b64=_b64(packet.raw),
                )
            await self._on_packet(packet, now)

    async def _on_packet(self, packet: Packet, now: datetime) -> None:
        assert self.strikes is not None
        assert self.universe is not None
        decoded, header = packet.decoded, packet.decoded.header
        kind, fields = decoded.kind, decoded.fields
        if kind == "disconnect":
            code = fields.get("disconnection_code")
            log.error("feed sent disconnect code %s", code)
            self._status(now, "DISCONNECT", detail=f"code {code}")
            if code in AUTH_DISCONNECT_CODES:
                self.request_stop(
                    f"Dhan closed the feed with code {code} (credentials or data plan); "
                    "check DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN",
                    exit_code=2,
                )
            return
        if kind in ("market_status", "prev_close"):
            return
        key = (str(header.exchange_segment), str(header.security_id))
        inst = self._by_security.get(key)
        if inst is None:
            if key not in self._unknown_seen:
                self._unknown_seen.add(key)
                self._error("packet for an unknown security id", now, segment=key[0], security_id=key[1])
            return
        iid = inst.instrument_id
        if iid not in self.strikes.subscribed:
            self.stats.late_packets += 1
            return
        self.stats.packets += 1
        now_s = now.timestamp()
        raw_b64 = None if DECODER_VERIFIED else _b64(packet.raw)
        ltp = fields.get("ltp")
        if kind == "full":
            ltt = self._ltt(fields.get("last_trade_time_epoch"), now_s)
            self._depth(iid, quote_from_full(fields), now, raw_b64, ltt)
            if inst.kind != "INDEX" and fields.get("oi") is not None:
                self.oi.observe(iid, int(fields["oi"]), now_s, "full")
        elif kind == "oi":
            if inst.kind != "INDEX":
                self.oi.observe(iid, int(fields["oi"]), now_s, "feed_oi")
        elif inst.kind == "INDEX" and ltp is not None:
            self._depth(iid, quote_from_ltp(ltp), now, raw_b64, None)
        if inst.kind == "INDEX" and ltp and math.isfinite(ltp):
            await self._on_spot(float(ltp), now, now_s, from_feed=True)

    def _depth(self, iid: str, quote: dict[str, Any], now: datetime, raw_b64: str | None, ltt: str | None) -> None:
        payload = self.depth.update(iid, quote, now.timestamp(), iso(now), raw_b64, ltt)
        if payload is not None:
            self._emit("DEPTH_QUOTE", payload, now, payload["exchange_ts"])

    def _ltt(self, epoch: Any, now_s: float) -> str | None:
        """Last trade time. Whether Dhan's epoch is UTC or IST-shifted is decided once from
        the first trade within an hour of the receive time under either reading."""
        if not epoch:
            return None
        if self._ltt_shift is None:
            for shift in (0, IST_EPOCH_SHIFT):
                if abs(epoch - shift - now_s) < 3600:
                    self._ltt_shift = shift
                    log.info("feed LTT epoch reads as %s", "UTC" if shift == 0 else "IST-shifted")
                    break
            else:
                return None
        return iso(datetime.fromtimestamp(epoch - self._ltt_shift, IST))

    async def _on_spot(self, spot: float, now: datetime, now_s: float, *, from_feed: bool) -> None:
        assert self.strikes is not None
        assert self.universe is not None
        if abs(spot / self.universe.spot - 1.0) > 0.15:
            if now_s - self._implausible_logged_s >= 60:
                self._implausible_logged_s = now_s
                self._error("implausible index price ignored", now, spot=spot, reference=self.universe.spot)
            return
        self.spot = spot
        if from_feed:
            self._last_spot_s = now_s
        await self._apply(self.strikes.update(spot, now_s), now, "recentre")

    async def _apply(self, change: Change, now: datetime, reason: str) -> None:
        if not change.subscribe and not change.unsubscribe:
            return
        assert self.collector is not None
        if change.recentred:
            log.info("re-centred on spot %.2f: ATM %s", self.spot, change.atm)
        self._log_change(change, now, reason)
        for inst in change.unsubscribe:
            self.depth.drop(inst.instrument_id)
            self.oi.drop(inst.instrument_id)
            self._stale.discard(inst.instrument_id)
        try:
            if change.subscribe:
                await self.collector.subscribe([i.feed for i in change.subscribe])
            if change.unsubscribe:
                await self.collector.unsubscribe([i.feed for i in change.unsubscribe])
        except Exception as exc:
            # The collector already holds the new set and resubscribes it on reconnect.
            log.warning("live subscription update failed (%s); applied on reconnect", type(exc).__name__)

    def _log_change(self, change: Change, now: datetime, reason: str) -> None:
        assert self.strikes is not None
        for inst in change.subscribe:
            self._subscribed_s[inst.instrument_id] = now.timestamp()
        for action, items in (("subscribe", change.subscribe), ("unsubscribe", change.unsubscribe)):
            for inst in items:
                rule = self.strikes.rule_for(inst.instrument_id)
                self._write(
                    "subscriptions",
                    {
                        "ts": iso(now),
                        "action": action,
                        "reason": reason,
                        "instrument_id": inst.instrument_id,
                        "security_id": inst.security_id,
                        "exchange_segment": inst.exchange_segment,
                        "rule": rule[0] if rule else inst.kind,
                        "spot": self.spot,
                        "atm": change.atm,
                    },
                    now,
                )

    # ---- output ----------------------------------------------------------------------

    def _emit(self, event_type: str, payload: dict[str, Any], now: datetime, event_ts: str) -> None:
        stem, stream = ENVELOPE_STREAMS[event_type]
        ts = iso(now)
        # Envelope v2 field set (architecture section 4.4), kept key-for-key compatible.
        env = {
            "event_type": event_type,
            "payload": payload,
            "source": "marketdata",
            "event_id": uuid.uuid4().hex,
            "timestamp": ts,
            "v": 2,
            "stream": stream,
            "event_ts": event_ts,
            "available_ts": ts,
            "account_id": None,
            "correlation_id": None,
            "causation_id": None,
        }
        self._write(stem, env, now)

    def _status(self, now: datetime, status: str, **extra: Any) -> None:
        self._emit("FEED_STATUS", {"status": status, "since": iso(now), **extra}, now, iso(now))

    def _error(self, reason: str, now: datetime, **extra: Any) -> None:
        self.stats.ingest_errors += 1
        self._write("ingest_errors", {"ts": iso(now), "reason": reason, **extra}, now)

    def _write(self, stem: str, record: dict[str, Any], now: datetime) -> None:
        try:
            repaired = self.tape[stem].write(record, now)
        except (TypeError, ValueError) as exc:
            if stem == "ingest_errors":
                log.error("dropping an ingest_errors row that cannot be serialised: %s", exc)
                return
            self._error(f"{stem} row cannot be serialised: {exc}", now, row=repr(record)[:2000])
            return
        if repaired:
            self._error(repaired["reason"], now, **{k: v for k, v in repaired.items() if k != "reason"})
