"""Optional / simple WebSocket: dry-run ticks, or a one-instrument live proxy.

Live proxy uses dhan-client MarketFeedCollector. Query:

  /ws/feed?segment=NSE_EQ&security_id=1333&mode=ticker

Default is dry-run placeholder JSON (no Dhan socket). Pass `live=1` only when
tokens are set and you intend to open Dhan's feed.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from dataclasses import replace

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from dhan_client.client import DhanClient
from dhan_client.types import FeedInstrument, FeedMode

from api.config import ApiSettings

router = APIRouter()

_MODE = {
    "ticker": FeedMode.TICKER,
    "quote": FeedMode.QUOTE,
    "full": FeedMode.FULL,
}


@router.websocket("/ws/feed")
async def feed_proxy(
    websocket: WebSocket,
    segment: str = "NSE_EQ",
    security_id: str = "1333",
    mode: str = "ticker",
    live: str = "0",
) -> None:
    await websocket.accept()
    settings: ApiSettings = websocket.app.state.settings
    feed_mode = _MODE.get(mode, FeedMode.TICKER)
    instrument = FeedInstrument(exchange_segment=segment, security_id=str(security_id))
    # Default dry-run even if env tokens exist. Pass live=1 to open Dhan WS.
    dhan_settings = settings.dhan
    if live != "1":
        dhan_settings = replace(dhan_settings, dry_run=True)
    client = DhanClient(dhan_settings)
    collector = client.feed_collector(
        [instrument], mode=feed_mode, reconnect=not dhan_settings.dry_run
    )

    queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

    def on_packet(pkt: dict) -> None:
        queue.put_nowait(pkt)

    async def producer() -> None:
        try:
            await collector.run(on_packet)
        finally:
            queue.put_nowait(None)

    task = asyncio.create_task(producer())
    try:
        if dhan_settings.dry_run:
            pkt = await queue.get()
            if pkt is not None:
                await websocket.send_json(pkt)
            await websocket.send_json(
                {
                    "kind": "dry_run_idle",
                    "note": "Skeleton proxy: one placeholder then idle. Ctrl+C to stop.",
                }
            )
            while True:
                await asyncio.sleep(30)
                await websocket.send_json({"kind": "ping", "dry_run": True})
        else:
            while True:
                pkt = await queue.get()
                if pkt is None:
                    break
                await websocket.send_json(pkt)
    except WebSocketDisconnect:
        collector.stop()
    finally:
        collector.stop()
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
@router.websocket("/ws/signals")
async def paper_signals(websocket: WebSocket, live: str = "0") -> None:
    """Customer paper BUY CE/PE/HOLD from Dhan index ticks. Orders stay refused."""
    await websocket.accept()
    from backtest_engine.live_signals import PaperSignalEngine, YAML_INDEX

    settings: ApiSettings = websocket.app.state.settings
    dhan_settings = settings.dhan
    if live != "1":
        dhan_settings = replace(dhan_settings, dry_run=True)
    instruments = [
        FeedInstrument(exchange_segment="IDX_I", security_id=str(sid))
        for sid in YAML_INDEX
    ]
    client = DhanClient(dhan_settings)
    collector = client.feed_collector(
        instruments, mode=FeedMode.TICKER, reconnect=not dhan_settings.dry_run
    )
    engine = PaperSignalEngine()
    queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

    def on_packet(pkt: dict) -> None:
        if pkt.get("kind") == "dry_run_placeholder":
            queue.put_nowait(
                {"kind": "paper_signal", "dry_run": True, "orders": "refused", "underlyings": {}}
            )
            return
        snap = engine.ingest(pkt)
        if snap:
            queue.put_nowait(snap)

    async def producer() -> None:
        try:
            await collector.run(on_packet)
        finally:
            queue.put_nowait(None)

    task = asyncio.create_task(producer())
    try:
        while True:
            pkt = await queue.get()
            if pkt is None:
                break
            websocket.app.state.live_paper = pkt
            await websocket.send_json(pkt)
            if dhan_settings.dry_run:
                await websocket.send_json(
                    {
                        "kind": "dry_run_idle",
                        "note": "Pass live=1 with tokens to stream Dhan ticks into paper signals.",
                        "orders": "refused",
                    }
                )
                while True:
                    await asyncio.sleep(30)
                    await websocket.send_json({"kind": "ping", "dry_run": True, "orders": "refused"})
    except WebSocketDisconnect:
        collector.stop()
    finally:
        collector.stop()
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        client.close()
