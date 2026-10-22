"""20-level depth recorder task (paper / recording only). Behind RecorderConfig.depth20 (default False).

Opens ONE extra websocket to Dhan's 20-depth endpoint (``wss://depth-api-feed.dhan.co/twentydepth``),
subscribes up to 50 NSE_FNO contracts (held pins first, then the moving ATM set; Dhan allows 50 per
connection and only NSE segments, so SENSEX/BSE contracts are skipped), and writes one row per
instrument per side update, throttled per instrument, to the plain tape ``depth20.jsonl``.

Never places orders. Every failure is contained here: a crash or a refused socket is logged and retried
with backoff and never stops the main recorder. Note Dhan's 5-socket-per-user limit (a 6th socket
disconnects the oldest with 805): count sockets before turning this on.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from marketdata.depth20 import parse_frame

log = logging.getLogger(__name__)

DEPTH20_WS_BASE = "wss://depth-api-feed.dhan.co/twentydepth"
SUBSCRIBE_CODE = 23
UNSUBSCRIBE_CODE = 25
DISCONNECT_CODE = 12
MAX_PER_SOCKET = 50
NSE_SEGMENTS = frozenset({"NSE_FNO", "NSE_EQ"})


def depth20_url(base: str, client_id: str, token: str) -> str:
    return f"{base}?{urlencode({'token': token, 'clientId': client_id, 'authType': 2})}"


def request(code: int, items: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "RequestCode": code,
        "InstrumentCount": len(items),
        "InstrumentList": [{"ExchangeSegment": seg, "SecurityId": sid} for seg, sid in items],
    }


def pick_targets(candidates: list[tuple[str, str, str]], limit: int = MAX_PER_SOCKET) -> list[tuple[str, str, str]]:
    """candidates: (instrument_id, exchange_segment, security_id) in priority order. NSE only, dedup, capped."""
    out: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for iid, seg, sid in candidates:
        if seg not in NSE_SEGMENTS or (seg, sid) in seen:
            continue
        seen.add((seg, sid))
        out.append((iid, seg, sid))
        if len(out) >= limit:
            break
    return out


class Depth20Feed:
    def __init__(
        self,
        url: str,
        targets: Callable[[], list[tuple[str, str, str]]],
        write: Callable[[dict[str, Any], datetime], None],
        now: Callable[[], datetime],
        *,
        throttle_s: float = 1.0,
        resync_s: float = 5.0,
        max_backoff_s: float = 30.0,
        connect: Callable[..., Any] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.url = url
        self.targets = targets
        self.write = write
        self.now = now
        self.throttle_s = throttle_s
        self.resync_s = resync_s
        self.max_backoff_s = max_backoff_s
        self._connect = connect
        self._sleep = sleep
        self.subscribed: dict[tuple[str, str], str] = {}
        self._last_row_s: dict[tuple[str, str], float] = {}
        self._stop = False
        self.rows = 0
        self.frames = 0
        self.errors = 0

    def stop(self) -> None:
        self._stop = True

    def _ids(self) -> dict[tuple[str, str], str]:
        try:
            return {(seg, sid): iid for iid, seg, sid in pick_targets(self.targets())}
        except Exception:  # never let a pin read kill the feed
            log.exception("depth20 target read failed")
            return dict(self.subscribed)

    async def _sync(self, ws: Any) -> None:
        want = self._ids()
        drop = [k for k in self.subscribed if k not in want]
        add = [k for k in want if k not in self.subscribed]
        if drop:
            await ws.send(json.dumps(request(UNSUBSCRIBE_CODE, drop)))
            for k in drop:
                self.subscribed.pop(k, None)
        if add:
            await ws.send(json.dumps(request(SUBSCRIBE_CODE, add)))
        self.subscribed.update({k: want[k] for k in add})

    def on_frame(self, raw: bytes | str) -> int:
        if not isinstance(raw, (bytes, bytearray)):
            return 0
        self.frames += 1
        now = self.now()
        now_s = now.timestamp()
        n = 0
        seg_by_sid = {sid: seg for seg, sid in self.subscribed}
        for msg in parse_frame(bytes(raw)):
            sid = msg["security_id"]
            seg = seg_by_sid.get(sid, "NSE_FNO")
            key = (seg, sid)
            iid = self.subscribed.get(key)
            if iid is None:
                continue
            tkey = (sid, msg["side"])
            last = self._last_row_s.get(tkey)
            if last is not None and now_s - last < self.throttle_s:
                continue
            self._last_row_s[tkey] = now_s
            self.write(
                {"ts": now.isoformat(timespec="milliseconds"), "instrument_id": iid, "security_id": sid,
                 "segment": seg, "side": msg["side"], "levels": msg["levels"], "n_levels": len(msg["levels"])},
                now,
            )
            n += 1
        self.rows += n
        return n

    async def run(self) -> None:
        if self._connect is None:
            import websockets

            self._connect = websockets.connect
        backoff = 1.0
        while not self._stop:
            try:
                async with self._connect(self.url, ping_interval=None, max_size=2**22) as ws:
                    backoff = 1.0
                    self.subscribed.clear()
                    await self._sync(ws)
                    loop = asyncio.get_running_loop()
                    next_sync = loop.time() + self.resync_s
                    while not self._stop:
                        timeout = max(0.05, next_sync - loop.time())
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                            self.on_frame(raw)
                        except asyncio.TimeoutError:
                            pass
                        if loop.time() >= next_sync:
                            await self._sync(ws)
                            next_sync = loop.time() + self.resync_s
                    try:
                        await ws.send(json.dumps({"RequestCode": DISCONNECT_CODE}))
                    except Exception:
                        pass
                    return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.errors += 1
                log.warning("depth20 socket error (%s); retry in %.0fs", type(exc).__name__, backoff)
                await self._sleep(backoff)
                backoff = min(self.max_backoff_s, backoff * 2)
