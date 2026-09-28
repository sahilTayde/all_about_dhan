"""Test harness: fake Dhan live feed on 127.0.0.1, binary packet encoders, fake clock, market sim.

Packets follow the documented layout the V2-D1 decoder is verified against (8-byte header
``<BHBI`` + 154-byte FULL payload, 5 interleaved depth levels). No network beyond loopback.
"""

from __future__ import annotations

import asyncio
import heapq
import json
import math
import struct
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from dhan_client.config import Credentials, Settings
from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.http11 import Request, Response

from marketdata.clock import IST
from marketdata.config import RecorderConfig
from marketdata.instruments import Universe, build_universe, parse_scrip_master
from marketdata.recorder import MarketDataRecorder
from marketdata.schemas import load_schema

SEG_BYTE = {"IDX_I": 0, "NSE_FNO": 2, "BSE_FNO": 8}
IST_SHIFT = 19800
TEST_CLIENT_ID = "CLIENTID-SENTINEL-4242"
TEST_TOKEN = "TOKEN-SENTINEL-eyJhbGciOiJIUzUxMiJ9.xyz"
DAY = date(2026, 9, 28)
EXPIRY = "2026-09-29"


def ist(hh: int, mm: int, ss: float = 0.0, day: date = DAY) -> datetime:
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=IST) + timedelta(seconds=ss)


# ---- packet encoders ----------------------------------------------------------------------


def _header(code: int, length: int, seg: int, sid: int) -> bytes:
    return struct.pack("<BHBI", code, length, seg, sid)


def full_packet(
    sid: int,
    seg: int,
    ltp: float,
    bid: float,
    ask: float,
    *,
    oi: int = 1_000_000,
    ltt_epoch: int = 0,
    volume: int = 50_000,
    qty: int = 650,
    tick: float = 0.05,
) -> bytes:
    body = struct.pack(
        "<fHIfIIIIIIffff",
        ltp,
        75,
        ltt_epoch,
        ltp,
        volume,
        400_000,
        420_000,
        oi,
        oi + 5000,
        max(oi - 5000, 0),
        ltp,
        ltp,
        ltp,
        ltp,
    )
    depth = b"".join(
        struct.pack("<IIHHff", qty + 75 * i, qty + 150 * i, 3 + i, 4 + i, bid - tick * i, ask + tick * i)
        for i in range(5)
    )
    payload = body + depth
    assert len(payload) == 154
    return _header(8, 8 + len(payload), seg, sid) + payload


def index_packet(sid: int, ltp: float, ltt_epoch: int = 0) -> bytes:
    payload = struct.pack("<fI", ltp, ltt_epoch)
    return _header(1, 8 + len(payload), SEG_BYTE["IDX_I"], sid) + payload


def ticker_packet(sid: int, seg: int, ltp: float, ltt_epoch: int = 0) -> bytes:
    payload = struct.pack("<fI", ltp, ltt_epoch)
    return _header(2, 8 + len(payload), seg, sid) + payload


def quote_packet(sid: int, seg: int, ltp: float, ltt_epoch: int = 0) -> bytes:
    payload = (
        struct.pack("<f", ltp)
        + struct.pack("<h", 10)
        + struct.pack("<i", ltt_epoch)
        + struct.pack("<f", ltp)
        + struct.pack("<i", 0)
        + struct.pack("<i", 0)
        + struct.pack("<i", 0)
        + struct.pack("<f", ltp)
        + struct.pack("<f", ltp)
        + struct.pack("<f", ltp)
        + struct.pack("<f", ltp)
    )
    return _header(4, 8 + len(payload), seg, sid) + payload


def oi_packet(sid: int, seg: int, oi: int) -> bytes:
    payload = struct.pack("<i", oi)
    return _header(5, 8 + len(payload), seg, sid) + payload


def disconnect_packet(code: int) -> bytes:
    payload = struct.pack("<h", code)
    return _header(50, 8 + len(payload), 0, 0) + payload


def dhan_ltt(t: datetime) -> int:
    """Encode like the feed: seconds since epoch shifted to IST wall time."""
    return int(t.timestamp()) + IST_SHIFT


# ---- instruments --------------------------------------------------------------------------

CSV_HEADER = (
    "SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_INSTRUMENT_NAME,SEM_EXPIRY_CODE,"
    "SEM_TRADING_SYMBOL,SEM_LOT_UNITS,SEM_CUSTOM_SYMBOL,SEM_EXPIRY_DATE,SEM_STRIKE_PRICE,"
    "SEM_OPTION_TYPE,SEM_TICK_SIZE,SEM_EXPIRY_FLAG,SEM_EXCH_INSTRUMENT_TYPE,SEM_SERIES,SM_SYMBOL_NAME"
)


def option_sid(strike: int, side: str, expiry: str = EXPIRY) -> int:
    base = 40_000 if expiry == EXPIRY else 60_000
    return base + (strike - 22_000) // 50 * 2 + (0 if side == "CE" else 1)


def scrip_master_csv() -> str:
    rows = [
        CSV_HEADER,
        "NSE,I,13,INDEX,0,NIFTY,1,NIFTY,,0.00000,XX,0.0500,NA,INDEX,NA,Nifty 50",
        "NSE,I,25,INDEX,0,BANKNIFTY,1,BANKNIFTY,,0.00000,XX,0.0500,NA,INDEX,NA,Nifty Bank",
        "NSE,I,27,INDEX,0,FINNIFTY,1,FINNIFTY,,0.00000,XX,0.0500,NA,INDEX,NA,Nifty Fin Service",
        "BSE,I,51,INDEX,0,SENSEX,1,SENSEX,,0.00000,XX,0.0500,NA,INDEX,NA,SENSEX",
        "NSE,D,35000,FUTIDX,0,NIFTY-Sep2026-FUT,65,NIFTY SEP FUT,2026-09-29 14:30:00,-0.01000,XX,0.1000,M,FUT,NA,NIFTY",
        "NSE,D,35001,FUTIDX,0,NIFTY-Oct2026-FUT,65,NIFTY OCT FUT,2026-10-27 14:30:00,-0.01000,XX,0.1000,M,FUT,NA,NIFTY",
        "NSE,D,35099,FUTIDX,0,NIFTY-Nov2026-FUT,65,NIFTY NOV FUT,2026-11-24 14:30:00,-0.01000,XX,0.1000,M,FUT,NA,NIFTY",
        "NSE,D,35002,FUTIDX,0,FINNIFTY-Oct2026-FUT,65,FINNIFTY OCT FUT,2026-10-27 14:30:00,-0.01000,XX,0.1000,"
        "M,FUT,NA,FINNIFTY",
    ]
    for expiry in (EXPIRY, "2026-10-06"):
        for strike in range(22_000, 27_001, 50):
            for side in ("CE", "PE"):
                sid = option_sid(strike, side, expiry)
                rows.append(
                    f"NSE,D,{sid},OPTIDX,0,NIFTY-{expiry}-{strike}-{side},65,NIFTY {strike} {side},"
                    f"{expiry} 14:30:00,{strike}.00000,{side},0.0500,W,OP,NA,NIFTY"
                )
    for strike in range(22_000, 27_001, 50):  # decoy underlying with the same strikes
        rows.append(
            f"NSE,D,{90_000 + strike // 50},OPTIDX,0,FINNIFTY-{EXPIRY}-{strike}-CE,65,FINNIFTY {strike} CE,"
            f"{EXPIRY} 14:30:00,{strike}.00000,CE,0.0500,W,OP,NA,FINNIFTY"
        )
    return "\n".join(rows) + "\n"


def option_chain(spot: float = 24512.35) -> dict[str, Any]:
    oc = {
        f"{strike}.000000": {
            "ce": {"security_id": option_sid(strike, "CE"), "last_price": 1.0, "oi": 1},
            "pe": {"security_id": option_sid(strike, "PE"), "last_price": 1.0, "oi": 1},
        }
        for strike in range(22_000, 27_001, 50)
    }
    return {"last_price": spot, "oc": oc}


class StubSource:
    """InstrumentSource stub; ``fail`` maps method name -> list of exceptions to raise first."""

    def __init__(self, spot: float = 24512.35, fail: dict[str, list[Exception]] | None = None) -> None:
        self.spot = spot
        self.fail = fail or {}
        self.calls: list[str] = []

    def _maybe_fail(self, name: str) -> None:
        self.calls.append(name)
        pending = self.fail.get(name)
        if pending:
            raise pending.pop(0)

    def scrip_master_csv(self) -> str:
        self._maybe_fail("scrip_master_csv")
        return scrip_master_csv()

    def expiry_list(self, underlying_scrip: int, underlying_seg: str) -> list[str]:
        self._maybe_fail("expiry_list")
        assert (underlying_scrip, underlying_seg) == (13, "IDX_I")
        return ["2026-09-22", EXPIRY, "2026-10-06", "2026-10-27"]

    def option_chain(self, underlying_scrip: int, underlying_seg: str, expiry: str) -> dict[str, Any]:
        self._maybe_fail("option_chain")
        assert (underlying_scrip, underlying_seg, expiry) == (13, "IDX_I", EXPIRY)
        return option_chain(self.spot)


def make_universe(spot: float = 24512.35) -> Universe:
    text = scrip_master_csv()
    return build_universe(text, parse_scrip_master(text, "NIFTY"), option_chain(spot), "NIFTY", DAY, EXPIRY)


def settings_for(url: str, repo: Path) -> Settings:
    return Settings(
        credentials=Credentials(client_id=TEST_CLIENT_ID, access_token=TEST_TOKEN),
        dry_run=False,
        feed_ws_base=url,
        repo_root=repo,
    )


# ---- fake feed server ---------------------------------------------------------------------


class FakeDhanServer:
    """Speaks the feed's shape: JSON subscribe (15/17/21) / unsubscribe (16/18/22) / disconnect (12) in,
    binary packets out. ``reject_status`` makes the handshake fail with that HTTP status."""

    def __init__(self) -> None:
        self.subscribed: dict[tuple[int, int], str] = {}
        self.requests: list[tuple[float, dict[str, Any]]] = []
        self.query: list[dict[str, list[str]]] = []
        self.connections = 0
        self.attempts: list[float] = []
        self.sent = 0
        self.reject_status: int | None = None
        self.reject_count: int | None = None  # reject only the first N handshakes
        self._clients: set[ServerConnection] = set()
        self._server: Server | None = None
        self.url = ""

    async def __aenter__(self) -> FakeDhanServer:
        self._server = await serve(self._handler, "127.0.0.1", 0, process_request=self._process_request)
        port = next(iter(self._server.sockets)).getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}"
        return self

    async def __aexit__(self, *exc: object) -> None:
        assert self._server is not None
        self._server.close()
        await self._server.wait_closed()

    def _process_request(self, connection: ServerConnection, request: Request) -> Response | None:
        self.attempts.append(asyncio.get_running_loop().time())
        self.query.append(parse_qs(urlsplit(request.path).query))
        if self.reject_status is not None and (self.reject_count is None or len(self.attempts) <= self.reject_count):
            return connection.respond(HTTPStatus(self.reject_status), "rejected\n")
        return None

    async def _handler(self, ws: ServerConnection) -> None:
        self.connections += 1
        self.subscribed.clear()
        self._clients.add(ws)
        try:
            async for message in ws:
                data = json.loads(message)
                self.requests.append((asyncio.get_running_loop().time(), data))
                code = data.get("RequestCode")
                for item in data.get("InstrumentList", []):
                    key = (SEG_BYTE[item["ExchangeSegment"]], int(item["SecurityId"]))
                    if code in (15, 17, 21):
                        self.subscribed[key] = item["ExchangeSegment"]
                    elif code in (16, 18, 22):
                        self.subscribed.pop(key, None)
                if code == 12:
                    await ws.close()
        except Exception:
            pass
        finally:
            self._clients.discard(ws)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def send(self, frame: bytes | str) -> int:
        n = 0
        for ws in list(self._clients):
            try:
                await ws.send(frame)
                n += 1
            except Exception:
                continue
        self.sent += n
        return n

    async def drop_clients(self) -> None:
        for ws in list(self._clients):
            await ws.close(code=1011, reason="test outage")

    def sids(self, code: int) -> list[int]:
        return [
            int(i["SecurityId"]) for _, r in self.requests if r.get("RequestCode") == code for i in r["InstrumentList"]
        ]


# ---- fake clock ---------------------------------------------------------------------------


class FakeClock:
    """Manual clock. ``advance_to`` wakes sleepers in deadline order and waits until each
    woken task has gone back to sleep (or ``done()`` is true), so ticks are deterministic."""

    def __init__(self, start: datetime) -> None:
        self._now = start
        self._sleepers: list[tuple[datetime, int, asyncio.Future[None]]] = []
        self._seq = 0
        self.done: Callable[[], bool] = lambda: False

    def now(self) -> datetime:
        return self._now

    async def sleep(self, seconds: float) -> None:
        fut: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self._seq += 1
        heapq.heappush(self._sleepers, (self._now + timedelta(seconds=max(seconds, 0.0)), self._seq, fut))
        await fut

    def sleeping(self) -> bool:
        return self._waiting() > 0

    def _waiting(self) -> int:
        return sum(1 for *_, f in self._sleepers if not f.done())

    async def advance_to(self, when: datetime) -> None:
        while not self.done():
            self._sleepers = [s for s in self._sleepers if not s[2].done()]
            heapq.heapify(self._sleepers)
            if not self._sleepers or self._sleepers[0][0] > when:
                break
            deadline, _, fut = heapq.heappop(self._sleepers)
            self._now = max(self._now, deadline)
            before = self._waiting()
            fut.set_result(None)

            def resettled(b: int = before) -> bool:
                return self._waiting() > b or self.done()

            await until(resettled, timeout=5.0)
        self._now = max(self._now, when)


class OffsetClock:
    """Real-time clock that starts at a chosen wall time (soak and subprocess tests)."""

    def __init__(self, start: datetime, speed: float = 1.0) -> None:
        self.start, self.speed = start, speed
        self._m0 = time.monotonic()

    def now(self) -> datetime:
        return self.start + timedelta(seconds=(time.monotonic() - self._m0) * self.speed)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(max(seconds, 0.0) / self.speed)


async def until(pred: Callable[[], bool], timeout: float = 10.0) -> None:
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    spins = 0
    while not pred():
        if loop.time() > end:
            raise TimeoutError("condition not met in time")
        spins += 1
        await asyncio.sleep(0 if spins < 50 else 0.001)


# ---- market simulator ---------------------------------------------------------------------


class Market:
    """Deterministic packets for whatever the server has subscribed.

    ``rates`` maps security id -> packets per second (default ``default_hz``); ``silent`` maps
    security id -> [(start, end)] windows with no packets; ``spot`` is a function of time.
    """

    def __init__(
        self,
        universe: Universe,
        spot: Callable[[datetime], float],
        *,
        default_hz: float = 2.0,
        rates: dict[int, float] | None = None,
        silent: dict[int, list[tuple[datetime, datetime]]] | None = None,
        oi: Callable[[int, datetime], int] | None = None,
        max_per_frame: int = 6,
    ) -> None:
        self.universe = universe
        self.spot = spot
        self.default_hz = default_hz
        self.rates = rates or {}
        self.silent = silent or {}
        self.oi = oi or (lambda _sid, t: 1_000_000 + 1000 * (int(t.timestamp()) // 20 % 1000))
        self.max_per_frame = max_per_frame
        self._by_sid = {int(i.security_id): i for i in universe.all_instruments()}
        self._last: datetime | None = None
        self.packets = 0

    def price(self, sid: int, t: datetime) -> tuple[float, float, float]:
        inst = self._by_sid[sid]
        s = self.spot(t)
        if inst.kind == "FUTURE":
            mid = s + 80.0
        else:
            assert inst.strike is not None
            intrinsic = max(0.0, s - inst.strike) if inst.option_type == "CE" else max(0.0, inst.strike - s)
            mid = intrinsic + 60.0 * math.exp(-abs(s - inst.strike) / 250.0) + 5.0
        bid = math.floor(mid / 0.05) * 0.05
        return round(bid + 0.05, 2), round(bid, 2), round(bid + 0.10, 2)

    def packet(self, key: tuple[int, int], t: datetime) -> bytes:
        seg, sid = key
        inst = self._by_sid[sid]
        if inst.kind == "INDEX":
            return index_packet(sid, self.spot(t), dhan_ltt(t))
        ltp, bid, ask = self.price(sid, t)
        return full_packet(sid, seg, ltp, bid, ask, oi=self.oi(sid, t), ltt_epoch=dhan_ltt(t))

    def frames(self, t: datetime, subscribed: dict[tuple[int, int], str]) -> list[bytes]:
        prev, self._last = self._last, t
        if prev is None:
            return []
        due: list[bytes] = []
        for key in sorted(subscribed):
            sid = key[1]
            if sid not in self._by_sid:
                continue
            if any(a <= t < b for a, b in self.silent.get(sid, [])):
                continue
            hz = self.rates.get(sid, self.default_hz)
            phase = (sid % 97) / 97.0
            if hz > 0 and math.floor(t.timestamp() * hz + phase) > math.floor(prev.timestamp() * hz + phase):
                due.append(self.packet(key, t))
        self.packets += len(due)
        return [b"".join(due[i : i + self.max_per_frame]) for i in range(0, len(due), self.max_per_frame)]


SCHEMAS = {"depth_quotes": "depth_quote", "quote_snapshots": "quote_snapshot", "oi_cadence": "oi_cadence"}


def format_checker() -> Any:
    from jsonschema import FormatChecker  # dev dependency; only the schema checks need it

    checker = FormatChecker()
    # jsonschema skips date-time silently unless rfc3339-validator is installed; prove it is on.
    assert not checker.conforms("2026-09-28T07:30:00", "date-time"), "date-time format checker is not active"
    assert checker.conforms("2026-09-28T10:00:00.100+05:30", "date-time")
    return checker


def schema_errors(day_dir: Path) -> tuple[dict[str, int], list[str]]:
    """Validate every tape row: payload against its V2-01 schema, envelope times as date-time."""
    from jsonschema import Draft7Validator

    checker = format_checker()
    counts: dict[str, int] = {}
    errors: list[str] = []
    for stem, name in SCHEMAS.items():
        validator = Draft7Validator(load_schema(name), format_checker=checker)
        rows = read_rows(day_dir / f"{stem}.jsonl")
        counts[stem] = len(rows)
        for n, row in enumerate(rows):
            errors += [f"{stem}:{n}: {e.message}" for e in validator.iter_errors(row["payload"])]
            for key in ("timestamp", "event_ts", "available_ts"):
                if not checker.conforms(row[key], "date-time"):
                    errors.append(f"{stem}:{n}: envelope {key} {row[key]!r} is not date-time")
    return counts, errors


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


Hook = Callable[[datetime, FakeDhanServer, MarketDataRecorder], Awaitable[None]]


@dataclass
class Session:
    recorder: MarketDataRecorder
    server: FakeDhanServer
    day_dir: Path
    exit_code: int

    def rows(self, stem: str) -> list[dict[str, Any]]:
        return read_rows(self.day_dir / f"{stem}.jsonl")

    def payloads(self, stem: str) -> list[dict[str, Any]]:
        return [r["payload"] for r in self.rows(stem)]


async def run_session(
    tmp: Path,
    start: datetime,
    end: datetime,
    *,
    spot: Callable[[datetime], float] = lambda _t: 24512.35,
    market_kw: dict[str, Any] | None = None,
    config_kw: dict[str, Any] | None = None,
    source: StubSource | None = None,
    universe: Universe | None = None,
    hook: Hook | None = None,
    step: float = 0.05,
    wait_connect: bool = True,
) -> Session:
    """Run the real recorder (real collector socket, decoder and writers) against the fake
    server on a fake clock from ``start`` until ``end`` or until it stops by itself."""
    async with FakeDhanServer() as server:
        clock = FakeClock(start)
        built = universe if universe is not None else make_universe()
        config = RecorderConfig(tape_root=tmp / "tape", **(config_kw or {}))
        recorder = MarketDataRecorder(
            config,
            settings_for(server.url, tmp),
            source=source,
            universe=built if source is None or universe is not None else None,
            clock=clock,
        )
        task = asyncio.create_task(recorder.run())
        clock.done = task.done
        if wait_connect:
            await until(lambda: bool(server.subscribed) or task.done(), timeout=15)
        # never advance the clock while the recorder is busy outside it (e.g. loading instruments)
        await until(lambda: clock.sleeping() or task.done(), timeout=15)
        market = Market(built, spot, **(market_kw or {}))
        t = start
        while not task.done() and t < end:
            t += timedelta(seconds=step)
            await clock.advance_to(t)
            if hook is not None:
                await hook(t, server, recorder)
            for frame in market.frames(t, server.subscribed if server.client_count else {}):
                await server.send(frame)
            await until(lambda: recorder.stats.frames >= server.sent or task.done(), timeout=10)
        if not task.done():
            recorder.request_stop("test end")
            await clock.advance_to(t + timedelta(seconds=1))
        exit_code = await asyncio.wait_for(task, timeout=20)
        return Session(recorder, server, tmp / "tape" / start.date().isoformat(), exit_code)
