"""V2-12 live market-data service: ticks, closed bars, chain, FEED_STATUS.

Wraps ``dhan_client.feed.MarketFeedCollector``. Paper / market-data only; no orders.
New entry point (recorder CLI is unchanged):

    python -m marketdata.dhan_ws --mode live-data
    python -m marketdata.dhan_ws --mode replay --tape PATH
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from dhan_client.config import Settings, load_settings, repo_root
from dhan_client.errors import CredentialsError
from dhan_client.feed import MarketFeedCollector
from dhan_client.types import FeedMode

from marketdata import logsafe
from marketdata.bars import BarBuilder
from marketdata.chain import ChainPoller, FetchChain
from marketdata.clock import Clock, LiveClock, iso, market_close, market_open, session_day
from marketdata.config import RecorderConfig
from marketdata.frames import decode_frame_checked
from marketdata.instruments import UNDERLYINGS, DhanInstrumentSource, Universe, load_universe
from marketdata.normalize import SecurityMap, bar_payload, resolve_exchange_ts, tick_from_packet, tick_payload
from marketdata.sources import TapeSource
from marketdata.strikes import Change, StrikeSet
from marketdata.tape import TapeWriter, tape_drop_count
from marketdata.types import BarClosed, SimClock, Tick, parse_ts

log = logging.getLogger("marketdata.live")

STREAMS: dict[str, tuple[str, str]] = {
    "TICK": ("ticks", "md:ticks"),
    "BAR_CLOSED": ("bars_1m", "md:bars:1m"),
    "CHAIN_SNAPSHOT": ("chain", "md:chain"),
    "FEED_STATUS": ("feed_status", "md:status"),
    "CLOCK": ("clock", "md:clock"),
}
OnFeedStatus = Callable[[dict[str, Any]], None]
MEMORY_PUBLISHER_MAXLEN = 10_000
_BAD_QUALITY = frozenset({"STALE", "DOWN"})


class Publisher(Protocol):
    def publish(self, envelope: dict[str, Any]) -> None: ...


class MemoryPublisher:
    """Bounded in-process sink. Live path must never use an unbounded list."""

    def __init__(self, *, maxlen: int = MEMORY_PUBLISHER_MAXLEN) -> None:
        self.maxlen = maxlen
        self.events: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def publish(self, envelope: dict[str, Any]) -> None:
        self.events.append(envelope)

    def of(self, event_type: str) -> list[dict[str, Any]]:
        return [row for row in self.events if row["event_type"] == event_type]

    def payloads(self, event_type: str) -> list[dict[str, Any]]:
        return [row["payload"] for row in self.of(event_type)]


class RedisPublisher:
    """XADD each envelope to its ``stream`` (md:ticks, md:bars:1m, …)."""

    def __init__(self, client: Any, *, maxlen: int = 100_000) -> None:
        self.client = client
        self.maxlen = maxlen

    def publish(self, envelope: dict[str, Any]) -> None:
        self.client.xadd(
            str(envelope["stream"]),
            {"event": json.dumps(envelope, separators=(",", ":"), allow_nan=False)},
            maxlen=self.maxlen,
            approximate=True,
        )


def make_envelope(event_type: str, payload: dict[str, Any], now: datetime, event_ts: str) -> dict[str, Any]:
    ts = iso(now)
    return {
        "event_type": event_type,
        "payload": payload,
        "source": "marketdata",
        "event_id": uuid.uuid4().hex,
        "timestamp": ts,
        "v": 2,
        "stream": STREAMS[event_type][1],
        "event_ts": event_ts,
        "available_ts": ts,
        "account_id": None,
        "correlation_id": None,
        "causation_id": None,
    }


class LiveMarketData:
    """Live path: feed -> normalize -> ticks / closed bars / chain / FEED_STATUS."""

    def __init__(
        self,
        settings: Settings,
        universe: Universe,
        *,
        publisher: Publisher | None = None,
        clock: Clock | None = None,
        config: RecorderConfig | None = None,
        tape_root: Path | None = None,
        on_feed_status: OnFeedStatus | None = None,
        chain_fetch: FetchChain | None = None,
    ) -> None:
        self.settings = settings
        self.universe = universe
        self.publisher: Publisher = publisher or MemoryPublisher()
        self.clock: Clock = clock or LiveClock()
        self.config = config or RecorderConfig(tape_root=tape_root or Path("."))
        self.on_feed_status = on_feed_status
        self.bars = BarBuilder()
        self.strikes = StrikeSet(
            universe, retention_s=self.config.retention_s, max_instruments=self.config.max_instruments
        )
        self.securities = SecurityMap(universe.all_instruments())
        self.chain = ChainPoller(chain_fetch) if chain_fetch is not None else None
        self.tape = (
            {
                stem: TapeWriter(
                    tape_root,
                    stem,
                    background=True,
                    queue_max=self.config.tape_queue_max,
                    put_timeout_s=self.config.tape_queue_put_timeout_s,
                )
                for stem, _ in STREAMS.values()
            }
            if tape_root is not None
            else {}
        )
        self.collector: MarketFeedCollector | None = None
        self.stop_reason: str | None = None
        self.spot = universe.spot
        self.frames = 0
        self._connected = False
        self._down_since: datetime | None = None
        self._connects_seen = 0
        self._up_since_s = float("-inf")
        self._last_tick_s: dict[str, float] = {}
        self._subscribed_s: dict[str, float] = {}
        self._stale: set[str] = set()
        self._open_dt: datetime | None = None
        self.unstamped_tick_count: int = 0
        self._unstamped_open: dict[str, int] = {}
        self.suppressed_bars: int = 0
        self._quality = "DOWN"
        self._quality_since: datetime | None = None
        self._bad_ranges: list[tuple[datetime, datetime, str]] = []

    def request_stop(self, reason: str = "stop requested") -> None:
        if self.stop_reason is None:
            self.stop_reason = reason
            log.warning("stopping: %s", reason)
        if self.collector is not None:
            self.collector.stop()

    async def run(self) -> int:
        if self.settings.dry_run or not self.settings.credentials.has_access:
            raise CredentialsError("live-data mode needs DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN")
        creds = self.settings.credentials
        logsafe.install([creds.client_id, creds.access_token])
        now = self.clock.now()
        day = session_day(now)
        open_dt, close_dt = market_open(day), market_close(day)
        self._open_dt = open_dt
        connect_at = open_dt - timedelta(seconds=self.config.connect_early_s)
        while self.stop_reason is None and self.clock.now() < connect_at:
            await self.clock.sleep(min(1.0, (connect_at - self.clock.now()).total_seconds()))
        if self.stop_reason is not None:
            return 0
        start = self.clock.now()
        for writer in self.tape.values():
            writer.open(start)
        first = self.strikes.update(self.spot, start.timestamp())
        self._mark_subscribed(first, start)
        self.collector = MarketFeedCollector(
            self.settings,
            [inst.feed for inst in first.subscribe],
            mode=FeedMode.FULL,
            index_mode=FeedMode(self.config.index_feed_mode),
            reconnect=True,
            max_backoff_seconds=self.config.max_backoff_s,
        )
        feed = asyncio.create_task(self.collector.run(on_frame=self._on_frame))
        try:
            await self._loop(feed, close_dt)
        finally:
            self.collector.stop()
            feed.cancel()
            await asyncio.gather(feed, return_exceptions=True)
            self._status(self.clock.now(), "DOWN", detail=self.stop_reason or "stopped")
            for writer in self.tape.values():
                writer.close()
        return 0

    async def _loop(self, feed: asyncio.Task[None], close_dt: datetime) -> None:
        last_s = self.clock.now().timestamp()
        while self.stop_reason is None:
            now = self.clock.now()
            now_s = now.timestamp()
            if now >= close_dt:
                self.request_stop(f"market close {close_dt.strftime('%H:%M')} IST")
                return
            if feed.done() and self.stop_reason is None:
                exc = feed.exception()
                self.request_stop(f"feed task ended: {exc!r}")
                if exc is not None:
                    raise exc
                return
            self._watch_connection(now)
            if int(now_s) > int(last_s):
                clock_payload = {
                    "session": now.date().isoformat(),
                    "phase": "MARKET",
                    "minute": now.strftime("%H:%M"),
                }
                self._emit("CLOCK", clock_payload, now, iso(now))
                for bar in self.bars.on_clock(now):
                    self._emit_bar(bar)
                self._watch_staleness(now, now_s)
                await self._apply(self.strikes.update(self.spot, now_s), now)
                self._maybe_chain(now, now_s)
                for writer in self.tape.values():
                    writer.flush()
            last_s = now_s
            await self.clock.sleep(self.config.tick_s)

    def _maybe_chain(self, now: datetime, now_s: float) -> None:
        if self.chain is None:
            return
        snap = self.chain.poll(
            int(self.universe.index.security_id),
            "IDX_I",
            self.universe.expiry,
            self.universe.underlying,
            now_s,
        )
        if snap is not None:
            self._emit("CHAIN_SNAPSHOT", snap, now, iso(now))

    async def _on_frame(self, raw: bytes | str) -> None:
        now = self.clock.now()
        self.frames += 1
        if isinstance(raw, str):
            return
        packets, _errors = decode_frame_checked(raw)
        for packet in packets:
            kind = packet.decoded.kind
            if kind in ("disconnect", "market_status", "prev_close"):
                continue
            # Index spot is ticker/quote/index (request 15/17), not FULL depth.
            header = packet.decoded.header
            inst = self.securities.resolve(header.exchange_segment, header.security_id)
            if inst is None or inst.instrument_id not in self.strikes.subscribed:
                continue
            exchange_ts, ts_source = resolve_exchange_ts(packet.decoded.fields, now)
            tick = tick_from_packet(packet, inst.instrument_id, exchange_ts)
            if tick is None:
                continue
            self._last_tick_s[inst.instrument_id] = now.timestamp()
            self._emit("TICK", tick_payload(tick, ts_source=ts_source), now, tick.exchange_ts)
            if ts_source != "ltt":
                self.unstamped_tick_count += 1
                iid = inst.instrument_id
                self._unstamped_open[iid] = self._unstamped_open.get(iid, 0) + 1
            else:
                for bar in self.bars.on_tick(tick, now):
                    self._emit_bar(bar)
            if inst.kind == "INDEX" and tick.ltp:
                self.spot = tick.ltp
                await self._apply(self.strikes.update(self.spot, now.timestamp()), now)

    def _watch_connection(self, now: datetime) -> None:
        assert self.collector is not None
        connected = self.collector.connected
        if connected and self._connected and self.collector.connect_count != self._connects_seen:
            self._status(now, "DOWN", detail="websocket closed and reopened between ticks")
            self._down_since, self._connected = now, False
        if connected and not self._connected:
            self._connects_seen = self.collector.connect_count
            self._up_since_s = now.timestamp()
            gap = (now - self._down_since).total_seconds() if self._down_since else None
            self._status(now, "UP", gap_s=gap, detail=f"connect #{self.collector.connect_count}")
        elif self._connected and not connected:
            self._down_since = now
            self._status(now, "DOWN", detail="websocket closed; reconnecting with backoff")
        self._connected = connected

    def _watch_staleness(self, now: datetime, now_s: float) -> None:
        if not self._connected or self._open_dt is None or now < self._open_dt:
            return
        for iid, inst in self.strikes.subscribed.items():
            if inst.kind != "INDEX":
                continue
            last = self._last_tick_s.get(iid)
            age = None if last is None else now_s - last
            waited = now_s - max(self._subscribed_s.get(iid, now_s), self._up_since_s)
            stale = waited > self.config.stale_after_s if age is None else age > self.config.stale_after_s
            if stale and iid not in self._stale:
                self._stale.add(iid)
                self._status(now, "STALE", instrument_id=iid, gap_s=None if age is None else round(age, 3))
            elif not stale and iid in self._stale:
                self._stale.discard(iid)
                self._status(now, "FRESH", instrument_id=iid)

    async def _apply(self, change: Change, now: datetime) -> None:
        if not change.subscribe and not change.unsubscribe:
            return
        self._mark_subscribed(change, now)
        assert self.collector is not None
        if change.subscribe:
            await self.collector.subscribe([inst.feed for inst in change.subscribe])
        if change.unsubscribe:
            await self.collector.unsubscribe([inst.feed for inst in change.unsubscribe])

    def _mark_subscribed(self, change: Change, now: datetime) -> None:
        for inst in change.subscribe:
            self._subscribed_s[inst.instrument_id] = now.timestamp()

    def _bar_feed_quality(self, start: datetime, end: datetime) -> str:
        """Worst STALE/DOWN overlapping ``[start, end)``, else OK."""
        worst: str | None = None
        if self._quality in _BAD_QUALITY and (self._quality_since is None or self._quality_since < end):
            worst = self._quality
        for bad_start, bad_end, reason in self._bad_ranges:
            if bad_start < end and bad_end > start and (reason == "DOWN" or worst != "DOWN"):
                worst = reason
        return worst or "OK"

    def _note_quality(self, now: datetime, status: str) -> None:
        if status == "DOWN":
            new_q = "DOWN"
        elif status == "STALE":
            new_q = "DOWN" if not self._connected else "STALE"
        elif status == "UP":
            new_q = "STALE" if self._stale else "OK"
        elif status == "FRESH":
            new_q = "OK" if self._connected else "DOWN"
        else:
            return
        if new_q == self._quality:
            return
        if self._quality in _BAD_QUALITY and self._quality_since is not None:
            self._bad_ranges.append((self._quality_since, now, self._quality))
        self._quality = new_q
        self._quality_since = now

    def _emit_bar(self, bar: BarClosed) -> None:
        start, end = parse_ts(bar.start), parse_ts(bar.end)
        quality = self._bar_feed_quality(start, end)
        unstamped = self._unstamped_open.pop(bar.instrument_id, 0)
        if quality != "OK":
            # Gap bars are not published as clean OHLC. FEED_STATUS covers the hole.
            self.suppressed_bars += 1
            return
        avail = parse_ts(bar.available_ts)
        payload = bar_payload(bar, unstamped_ticks=unstamped, feed_quality=quality)
        env = make_envelope("BAR_CLOSED", payload, avail, bar.end)
        env["available_ts"] = bar.available_ts
        self._publish(env, avail)

    def _emit(self, event_type: str, payload: dict[str, Any], now: datetime, event_ts: str) -> None:
        self._publish(make_envelope(event_type, payload, now, event_ts), now)

    def _publish(self, env: dict[str, Any], now: datetime) -> None:
        self.publisher.publish(env)
        stem = STREAMS[str(env["event_type"])][0]
        if stem in self.tape:
            self.tape[stem].write(env, now)
        if env["event_type"] == "FEED_STATUS" and self.on_feed_status is not None:
            self.on_feed_status(env["payload"])

    def _status(self, now: datetime, status: str, **extra: Any) -> None:
        self._emit(
            "FEED_STATUS",
            {"status": status, "since": iso(now), **extra, "tape_drops": tape_drop_count()},
            now,
            iso(now),
        )
        self._note_quality(now, status)


def replay_tape(path: Path, publisher: Publisher, *, clock: SimClock | None = None) -> int:
    """Play a JSONL tape through TapeSource into ``publisher`` (ticks + closed bars)."""
    builder = BarBuilder()
    source = TapeSource(path, clock=clock)
    published = 0
    for event in source.events():
        if event.event_type == "TICK":
            tick = event.payload
            assert isinstance(tick, Tick)
            env = make_envelope("TICK", tick_payload(tick), event.available_ts, tick.exchange_ts)
            publisher.publish(env)
            published += 1
            for bar in builder.on_tick(tick, event.available_ts):
                bar_env = make_envelope("BAR_CLOSED", bar_payload(bar), parse_ts(bar.available_ts), bar.end)
                bar_env["available_ts"] = bar.available_ts
                publisher.publish(bar_env)
                published += 1
        elif event.event_type == "CLOCK":
            payload = event.payload if isinstance(event.payload, dict) else {"ts": event.available_ts.isoformat()}
            publisher.publish(make_envelope("CLOCK", payload, event.available_ts, event.available_ts.isoformat()))
            published += 1
            for bar in builder.on_clock(event.available_ts):
                bar_env = make_envelope("BAR_CLOSED", bar_payload(bar), parse_ts(bar.available_ts), bar.end)
                bar_env["available_ts"] = bar.available_ts
                publisher.publish(bar_env)
                published += 1
    return published


def _tape_file(path: Path) -> Path:
    if path.is_file():
        return path
    for name in ("ticks.jsonl", "depth_quotes.jsonl"):
        candidate = path / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no tape jsonl at {path}")


def _publisher_for(redis_url: str | None) -> Publisher:
    if not redis_url:
        return MemoryPublisher()
    try:
        import redis  # optional; replay-into-Redis only
    except ImportError as exc:
        raise SystemExit("replay --redis-url needs the redis package") from exc
    return RedisPublisher(redis.Redis.from_url(redis_url))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m marketdata.dhan_ws",
        description="V2-12 live market data (ticks, closed bars, chain, feed status). Paper only.",
    )
    parser.add_argument("--mode", choices=("live-data", "replay"), required=True)
    parser.add_argument("--tape", type=Path, default=None, help="replay jsonl, or live-data tape root")
    parser.add_argument("--underlying", default="NIFTY", choices=sorted(UNDERLYINGS))
    parser.add_argument("--redis-url", default=None, help="replay/live: XADD envelopes to Redis streams")
    args = parser.parse_args(argv)

    if args.mode == "replay":
        if args.tape is None:
            parser.error("--mode replay needs --tape")
        n = replay_tape(_tape_file(args.tape), _publisher_for(args.redis_url))
        print(f"replayed {n} events from {args.tape}")
        return 0

    root = repo_root()
    try:
        settings = load_settings(dry_run=False)
    except CredentialsError:
        log.error("live-data mode needs DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN")
        return 2
    day = session_day(LiveClock().now())
    cache_dir = root / "data" / "cache" / "marketdata"
    source = DhanInstrumentSource(settings, cache_dir, day=day)
    try:
        universe = load_universe(source, args.underlying, day, sleep=lambda _s: None)
        publisher = _publisher_for(args.redis_url)
        live = LiveMarketData(
            settings,
            universe,
            publisher=publisher,
            config=RecorderConfig(tape_root=args.tape or root / "data" / "tape" / "v2"),
            tape_root=args.tape,
            chain_fetch=lambda scrip, seg, expiry: source.option_chain(scrip, seg, expiry),
        )
        return asyncio.run(live.run())
    except CredentialsError as exc:
        log.error("startup failed: %s", exc)
        return 2
    finally:
        source.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    sys.exit(main())
