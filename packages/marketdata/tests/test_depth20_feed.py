"""2026-10-22: 20-level depth recording behind RecorderConfig.depth20 (default off). Box only: a local fake
depth socket, synthetic frames, no Dhan call, no token."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import websockets
from md_fake_dhan import EXPIRY, ist, make_universe, run_session

from marketdata import depth20
from marketdata.config import RecorderConfig
from marketdata.depth20_feed import (
    SUBSCRIBE_CODE,
    UNSUBSCRIBE_CODE,
    Depth20Feed,
    depth20_url,
    pick_targets,
)

NOW = datetime(2026, 10, 22, 4, 0, tzinfo=timezone.utc)


def test_default_off_and_url() -> None:
    assert RecorderConfig(tape_root=Path("/tmp/x")).depth20 is False
    url = depth20_url("wss://depth-api-feed.dhan.co/twentydepth", "100", "tok")
    assert url.startswith("wss://depth-api-feed.dhan.co/twentydepth?") and "authType=2" in url


def test_pick_targets_nse_only_dedup_cap() -> None:
    c = [("BSE_FNO:SENSEX:x:74500:PE", "BSE_FNO", "9")] + [(f"N{i}", "NSE_FNO", str(i)) for i in range(60)]
    c.insert(2, ("dup", "NSE_FNO", "0"))
    got = pick_targets(c)
    assert len(got) == 50 and got[0] == ("N0", "NSE_FNO", "0")
    assert all(seg == "NSE_FNO" for _, seg, _ in got) and "dup" not in {i for i, _, _ in got}


class _WS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, text: str) -> None:
        self.sent.append(json.loads(text))


def test_sync_subscribes_and_unsubscribes_and_throttles() -> None:
    targets = [("A", "NSE_FNO", "1"), ("B", "NSE_FNO", "2")]
    rows: list[dict] = []
    clock = {"t": NOW}
    feed = Depth20Feed("ws://x", lambda: list(targets), lambda r, _n: rows.append(r), lambda: clock["t"], throttle_s=1.0)
    ws = _WS()
    asyncio.run(feed._sync(ws))
    assert ws.sent[0]["RequestCode"] == SUBSCRIBE_CODE and ws.sent[0]["InstrumentCount"] == 2
    frame = depth20.pack_message(41, 2, 1, [(100.0, 75, 3), (99.95, 150, 4)]) + depth20.pack_message(51, 2, 1, [(100.1, 65, 1)])
    assert feed.on_frame(frame) == 2
    assert feed.on_frame(frame) == 0  # throttled within 1 s
    clock["t"] = NOW.replace(second=2)
    assert feed.on_frame(frame) == 2
    assert rows[0]["instrument_id"] == "A" and rows[0]["side"] == "bid" and rows[0]["levels"][0] == [100.0, 75, 3]
    assert feed.on_frame(depth20.pack_message(41, 2, 777, [(1.0, 1, 1)])) == 0  # not subscribed
    targets.pop(0)
    asyncio.run(feed._sync(ws))
    assert ws.sent[-1]["RequestCode"] == UNSUBSCRIBE_CODE and ws.sent[-1]["InstrumentList"][0]["SecurityId"] == "1"


async def _serve_depth(seen: list[dict], frames: list[bytes]):
    async def handler(ws):
        async for msg in ws:
            seen.append(json.loads(msg))
            if seen[-1].get("RequestCode") == SUBSCRIBE_CODE:
                for f in frames:
                    await ws.send(f)

    return await websockets.serve(handler, "127.0.0.1", 0)


def test_real_socket_round_trip() -> None:
    async def go() -> tuple[list[dict], list[dict]]:
        seen: list[dict] = []
        frame = depth20.pack_message(41, 2, 5, [(50.0, 75, 2)]) + depth20.pack_message(51, 2, 5, [(50.2, 75, 1)])
        server = await _serve_depth(seen, [frame])
        port = server.sockets[0].getsockname()[1]
        rows: list[dict] = []
        feed = Depth20Feed(f"ws://127.0.0.1:{port}/twentydepth", lambda: [("X", "NSE_FNO", "5")],
                           lambda r, _n: rows.append(r), lambda: datetime.now(timezone.utc), resync_s=0.2)
        task = asyncio.create_task(feed.run())
        for _ in range(100):
            if len(rows) >= 2:
                break
            await asyncio.sleep(0.02)
        feed.stop()
        await asyncio.wait_for(task, 5)
        server.close()
        await server.wait_closed()
        return seen, rows

    seen, rows = asyncio.run(go())
    assert seen[0] == {"RequestCode": 23, "InstrumentCount": 1, "InstrumentList": [{"ExchangeSegment": "NSE_FNO", "SecurityId": "5"}]}
    assert {r["side"] for r in rows} == {"bid", "ask"}
    assert seen[-1] == {"RequestCode": 12}


def test_recorder_writes_depth20_tape_when_on_and_nothing_when_off(tmp_path: Path) -> None:
    universe = make_universe()
    held = f"NSE_FNO:NIFTY:{EXPIRY}:24000:CE"
    sid = int(universe.options[(24000, "CE")].security_id) if (24000, "CE") in universe.options else None
    assert sid is not None

    async def go(depth_on: bool, root: Path):
        seen: list[dict] = []
        frame = depth20.pack_message(41, 2, sid, [(120.0, 75, 2)]) + depth20.pack_message(51, 2, sid, [(120.5, 75, 2)])
        server = await _serve_depth(seen, [frame])
        port = server.sockets[0].getsockname()[1]
        try:
            pins = root / "data" / "recon" / "paper_booked"
            pins.mkdir(parents=True, exist_ok=True)
            (pins / f"{ist(10, 0).date().isoformat()}.jsonl").write_text(json.dumps(
                {"trade_id": "h", "underlying": "NIFTY", "side": "CE", "atm_strike": 24000, "opened_ts": 1}) + "\n")
            s = await run_session(root, ist(10, 0), ist(10, 0, 3), universe=universe,
                                  config_kw={"pin_root": root, "depth20": depth_on,
                                             "depth20_ws_base": f"ws://127.0.0.1:{port}/twentydepth"})
        finally:
            server.close()
            await server.wait_closed()
        return s, seen

    s_on, seen_on = asyncio.run(go(True, tmp_path / "on"))
    rows = s_on.rows("depth20")
    assert rows and rows[0]["instrument_id"] == held
    subs = [m for m in seen_on if m.get("RequestCode") == 23]
    assert subs and subs[0]["InstrumentList"][0]["SecurityId"] == str(sid)  # held contract first
    assert all(i["ExchangeSegment"] == "NSE_FNO" for m in subs for i in m["InstrumentList"])
    s_off, seen_off = asyncio.run(go(False, tmp_path / "off"))
    assert not seen_off and not (s_off.day_dir / "depth20.jsonl").exists()
