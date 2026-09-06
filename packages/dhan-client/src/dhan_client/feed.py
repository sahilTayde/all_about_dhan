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
from typing import Awaitable, Callable, Optional, Sequence
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

_SUBSCRIBE_CODE = {
    FeedMode.TICKER: FeedRequestCode.SUBSCRIBE_TICKER,
    FeedMode.QUOTE: FeedRequestCode.SUBSCRIBE_QUOTE,
    FeedMode.FULL: FeedRequestCode.SUBSCRIBE_FULL,
}


def chunked(items: Sequence[FeedInstrument], size: int) -> list[list[FeedInstrument]]:
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


def subscribe_messages(
    instruments: Sequence[FeedInstrument],
    mode: FeedMode = FeedMode.TICKER,
) -> list[dict[str, object]]:
    if len(instruments) > FEED_MAX_INSTRUMENTS_PER_CONNECTION:
        raise ValueError(
            f"max {FEED_MAX_INSTRUMENTS_PER_CONNECTION} instruments per connection"
        )
    request_code = int(_SUBSCRIBE_CODE[mode])
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
        reconnect: bool = True,
        max_backoff_seconds: float = 30.0,
    ) -> None:
        self.settings = settings
        self.instruments = list(instruments)
        self.mode = mode
        self.reconnect = reconnect
        self.max_backoff_seconds = max_backoff_seconds
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self, on_packet: Optional[OnPacket] = None) -> None:
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
                await self._run_socket(on_packet)
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception:
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

    async def _run_dry(self, on_packet: Optional[OnPacket]) -> None:
        messages = subscribe_messages(self.instruments, self.mode)
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
            log.info("dry-run subscribe payload keys=%s count=%s", list(msg), msg.get("InstrumentCount"))
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

    async def _run_socket(self, on_packet: Optional[OnPacket]) -> None:
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
            for msg in subscribe_messages(self.instruments, self.mode):
                await ws.send(json.dumps(msg))
                log.info(
                    "subscribed batch count=%s request_code=%s",
                    msg.get("InstrumentCount"),
                    msg.get("RequestCode"),
                )
            while not self._stop.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=FEED_STALE_DISCONNECT_SECONDS)
                except asyncio.TimeoutError:
                    log.info("feed recv timeout; reconnecting")
                    break
                if isinstance(raw, str):
                    log.info("feed text frame len=%s (unexpected; responses are binary)", len(raw))
                    continue
                for packet in decode_frame(raw):
                    payload = packet_as_dict(packet)
                    if on_packet is not None:
                        result = on_packet(payload)
                        if asyncio.iscoroutine(result):
                            await result

            try:
                await ws.send(json.dumps({"RequestCode": int(FeedRequestCode.DISCONNECT)}))
            except Exception:
                log.debug("feed disconnect send failed", exc_info=True)
