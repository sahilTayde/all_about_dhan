"""Generic Live Market Feed collector: connect, subscribe, decode, reconnect.

https://dhanhq.co/docs/v2/live-market-feed/

- URL: ``wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2``
- Subscribe JSON: RequestCode, InstrumentCount, InstrumentList
- Max 100 instruments per JSON message, 5000 per connection, 5 connections/user
- Server ping every 10s; stale after ~40s without pong (library auto-pong)
- Disconnect JSON: ``{"RequestCode": 12}``
- No strategy. No orders.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Optional, Union
from urllib.parse import urlencode

from dhan_client.annexure import FeedRequestCode
from dhan_client.config import Settings
from dhan_client.decode import decode_frame, packet_as_dict
from dhan_client.endpoints import (
    FEED_AUTH_TYPE,
    FEED_MAX_INSTRUMENTS_PER_CONNECTION,
    FEED_MAX_INSTRUMENTS_PER_MESSAGE,
    FEED_STALE_DISCONNECT_SECONDS,
    FEED_VERSION,
)
from dhan_client.errors import CredentialsError
from dhan_client.logging_util import get_logger, redact_url
from dhan_client.types import FeedInstrument, FeedMode, JsonDict

log = get_logger(__name__)

OnPacket = Callable[[JsonDict], Optional[Awaitable[None]]]
# Receives every websocket message (bytes or text) untouched; the caller owns decoding.
OnFrame = Callable[[Union[bytes, str]], Optional[Awaitable[None]]]

_SUBSCRIBE_CODE = {
    FeedMode.TICKER: FeedRequestCode.SUBSCRIBE_TICKER,
    FeedMode.QUOTE: FeedRequestCode.SUBSCRIBE_QUOTE,
    FeedMode.FULL: FeedRequestCode.SUBSCRIBE_FULL,
}

_UNSUBSCRIBE_CODE = {
    FeedMode.TICKER: FeedRequestCode.UNSUBSCRIBE_TICKER,
    FeedMode.QUOTE: FeedRequestCode.UNSUBSCRIBE_QUOTE,
    FeedMode.FULL: FeedRequestCode.UNSUBSCRIBE_FULL,
}


def chunked(items: Sequence[FeedInstrument], size: int) -> list[list[FeedInstrument]]:
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


def _inst_key(inst: FeedInstrument) -> tuple[str, str]:
    return (inst.exchange_segment, str(inst.security_id))


def feed_mode_for(
    inst: FeedInstrument,
    *,
    default: FeedMode,
    index_mode: FeedMode = FeedMode.TICKER,
) -> FeedMode:
    """IDX_I has no FULL/depth ticks; ticker (15) or quote (17) only."""
    if inst.exchange_segment == "IDX_I":
        return index_mode
    return default


def subscribe_messages_for_modes(
    instruments: Sequence[FeedInstrument],
    modes: Mapping[tuple[str, str], FeedMode],
    *,
    default: FeedMode,
    unsubscribe: bool = False,
) -> list[dict[str, object]]:
    grouped: dict[FeedMode, list[FeedInstrument]] = {}
    for inst in instruments:
        grouped.setdefault(modes.get(_inst_key(inst), default), []).append(inst)
    messages: list[dict[str, object]] = []
    for mode, group in grouped.items():
        messages.extend(subscribe_messages(group, mode, unsubscribe=unsubscribe))
    return messages


def subscribe_messages(
    instruments: Sequence[FeedInstrument],
    mode: FeedMode = FeedMode.TICKER,
    *,
    unsubscribe: bool = False,
) -> list[dict[str, object]]:
    if len(instruments) > FEED_MAX_INSTRUMENTS_PER_CONNECTION:
        raise ValueError(
            f"max {FEED_MAX_INSTRUMENTS_PER_CONNECTION} instruments per connection"
        )
    request_code = int((_UNSUBSCRIBE_CODE if unsubscribe else _SUBSCRIBE_CODE)[mode])
    messages: list[dict[str, object]] = []
    for group in chunked(list(instruments), FEED_MAX_INSTRUMENTS_PER_MESSAGE):
        messages.append(
            {
                "RequestCode": request_code,
                "InstrumentCount": len(group),
                "InstrumentList": [
                    {
                        "ExchangeSegment": inst.exchange_segment,
                        "SecurityId": str(inst.security_id),
                    }
                    for inst in group
                ],
            }
        )
    return messages


def feed_url(settings: Settings) -> str:
    creds = settings.credentials
    query = urlencode(
        {
            "version": FEED_VERSION,
            "token": creds.access_token,
            "clientId": creds.client_id,
            "authType": FEED_AUTH_TYPE,
        }
    )
    return f"{settings.feed_ws_base}?{query}"


class MarketFeedCollector:
    """Connect / subscribe / decode / reconnect. Dry-run never opens a socket."""

    def __init__(
        self,
        settings: Settings,
        instruments: Sequence[FeedInstrument],
        *,
        mode: FeedMode = FeedMode.TICKER,
        index_mode: FeedMode = FeedMode.TICKER,
        reconnect: bool = True,
        max_backoff_seconds: float = 30.0,
    ) -> None:
        self.settings = settings
        self.instruments = list(instruments)
        self.mode = mode
        self.index_mode = index_mode
        self._modes: dict[tuple[str, str], FeedMode] = {
            _inst_key(i): feed_mode_for(i, default=mode, index_mode=index_mode)
            for i in self.instruments
        }
        self.reconnect = reconnect
        self.max_backoff_seconds = max_backoff_seconds
        self._stop = asyncio.Event()
        self._ws: Any = None
        # Read-only connection state for supervisors (never holds secrets).
        self.connected = False
        self.connect_count = 0
        self.error_count = 0
        self.last_error: BaseException | None = None

    def stop(self) -> None:
        self._stop.set()

    def _messages(
        self, instruments: Sequence[FeedInstrument], *, unsubscribe: bool = False
    ) -> list[dict[str, object]]:
        return subscribe_messages_for_modes(
            instruments, self._modes, default=self.mode, unsubscribe=unsubscribe
        )

    async def subscribe(
        self, instruments: Sequence[FeedInstrument], mode: FeedMode | None = None
    ) -> None:
        """Add instruments; sent now if a socket is open, and on every reconnect."""
        new = [i for i in instruments if i not in self.instruments]
        if not new:
            return
        for inst in new:
            self._modes[_inst_key(inst)] = (
                mode
                if mode is not None
                else feed_mode_for(inst, default=self.mode, index_mode=self.index_mode)
            )
        self.instruments.extend(new)
        await self._send_batches(self._messages(new))

    async def unsubscribe(self, instruments: Sequence[FeedInstrument]) -> None:
        gone = [i for i in instruments if i in self.instruments]
        if not gone:
            return
        batches = self._messages(gone, unsubscribe=True)
        self.instruments = [i for i in self.instruments if i not in gone]
        for inst in gone:
            self._modes.pop(_inst_key(inst), None)
        await self._send_batches(batches)

    async def _send_batches(self, messages: list[dict[str, object]]) -> None:
        ws = self._ws
        if ws is None:
            return
        for msg in messages:
            await ws.send(json.dumps(msg))
            log.info(
                "sent batch count=%s request_code=%s",
                msg.get("InstrumentCount"),
                msg.get("RequestCode"),
            )

    async def run(
        self,
        on_packet: OnPacket | None = None,
        *,
        on_frame: OnFrame | None = None,
    ) -> None:
        if self.settings.dry_run:
            await self._run_dry(on_packet)
            return
        if not self.settings.credentials.has_access:
            raise CredentialsError(
                "Live feed needs DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN."
            )
        backoff = 1.0
        while not self._stop.is_set():
            try:
                await self._run_socket(on_packet, on_frame)
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = exc
                self.error_count += 1
                log.exception("feed connection dropped")
            if not self.reconnect or self._stop.is_set():
                break
            log.info("reconnecting feed in %.1fs", backoff)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                break
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2.0, self.max_backoff_seconds)

    async def _run_dry(self, on_packet: OnPacket | None) -> None:
        messages = self._messages(self.instruments)
        log.info(
            "dry-run feed: would connect to %s (token redacted) subscribe_batches=%s instruments=%s mode=%s",
            redact_url(feed_url(self.settings))
            if self.settings.credentials.has_access
            else f"{self.settings.feed_ws_base}?version={FEED_VERSION}&token=***&clientId=***&authType={FEED_AUTH_TYPE}",
            len(messages),
            len(self.instruments),
            self.mode.value,
        )
        for msg in messages:
            log.info(
                "dry-run subscribe payload keys=%s count=%s",
                list(msg),
                msg.get("InstrumentCount"),
            )
        placeholder: JsonDict = {
            "kind": "dry_run_placeholder",
            "mode": self.mode.value,
            "instruments": [
                {
                    "exchange_segment": i.exchange_segment,
                    "security_id": i.security_id,
                }
                for i in self.instruments
            ],
            "subscribe_messages": messages,
            "notes": [
                "No socket opened.",
                "Binary decode runs only on live frames (see dhan_client.decode).",
            ],
        }
        if on_packet is not None:
            result = on_packet(placeholder)
            if asyncio.iscoroutine(result):
                await result

    async def _run_socket(
        self, on_packet: OnPacket | None, on_frame: OnFrame | None = None
    ) -> None:
        try:
            import websockets
        except ImportError as exc:
            raise RuntimeError("install websockets to use the live feed") from exc

        url = feed_url(self.settings)
        log.info("opening feed %s", redact_url(url))
        async with websockets.connect(
            url,
            ping_interval=20,
            ping_timeout=FEED_STALE_DISCONNECT_SECONDS,
            max_size=2**20,
        ) as ws:
            self.connect_count += 1
            # Set before the initial batches so a concurrent subscribe() is never dropped
            # (a duplicate subscribe is harmless).
            self._ws = ws
            try:
                for msg in self._messages(self.instruments):
                    await ws.send(json.dumps(msg))
                    log.info(
                        "subscribed batch count=%s request_code=%s",
                        msg.get("InstrumentCount"),
                        msg.get("RequestCode"),
                    )
                self.connected = True
                self.last_error = None
                while not self._stop.is_set():
                    try:
                        raw = await asyncio.wait_for(
                            ws.recv(), timeout=FEED_STALE_DISCONNECT_SECONDS
                        )
                    except asyncio.TimeoutError:
                        log.info("feed recv timeout; reconnecting")
                        break
                    if on_frame is not None:
                        handled = on_frame(raw)
                        if asyncio.iscoroutine(handled):
                            await handled
                        continue
                    if isinstance(raw, str):
                        log.info(
                            "feed text frame len=%s (unexpected; responses are binary)",
                            len(raw),
                        )
                        continue
                    for packet in decode_frame(raw):
                        payload = packet_as_dict(packet)
                        if on_packet is not None:
                            result = on_packet(payload)
                            if asyncio.iscoroutine(result):
                                await result

                try:
                    await ws.send(
                        json.dumps({"RequestCode": int(FeedRequestCode.DISCONNECT)})
                    )
                except Exception:
                    log.debug("feed disconnect send failed", exc_info=True)
            finally:
                self._ws = None
                self.connected = False
