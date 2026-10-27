"""Cross-market recorder (2026-10-12). Record only; places no orders; separate process.

    python -m marketdata.cross_market --record-only [--tape-root PATH] [--until HH:MM]

Records one 1-minute OHLC row per instrument from ONE Dhan market-feed socket (QUOTE mode):
India VIX, BANKNIFTY, FINNIFTY index; 11 NIFTY heavyweights (NSE_EQ); MCX CRUDEOIL and GOLD
front-month futures; NSE USDINR front-month future. Security ids are resolved at startup from
Dhan's public scrip master CSV, never hardcoded. An instrument the CSV does not list is written to
``missing.json`` and skipped (no guess).

Credentials come from the same ``dhan_client.config.load_settings`` path the V2 recorder uses;
this module never reads or logs the token. A crash here cannot stall the desk loop: it is its own
process (screen ``cross-recorder``) and writes only under ``<tape_root>/<name>/``.

Tape layout: ``<tape_root>/<name>/<YYYY-MM-DD>.jsonl`` (IST date), schema in ``<tape_root>/SCHEMA.json``.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import logging
import signal
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

IST = timezone(timedelta(hours=5, minutes=30))
log = logging.getLogger("marketdata.cross_market")

INDEXES = {"INDIAVIX": "INDIA VIX", "BANKNIFTY": "BANKNIFTY", "FINNIFTY": "FINNIFTY"}
HEAVYWEIGHTS = ("HDFCBANK", "RELIANCE", "ICICIBANK", "INFY", "TCS", "BHARTIARTL", "LT", "ITC",
                "SBIN", "AXISBANK", "KOTAKBANK")
# name -> (exchange, instrument, trading-symbol prefix)
FUTURES = {"CRUDEOIL": ("MCX", "FUTCOM", "CRUDEOIL-"), "GOLD": ("MCX", "FUTCOM", "GOLD-"),
           "USDINR": ("NSE", "FUTCUR", "USDINR-")}
SEGMENTS = {("NSE", "I"): "IDX_I", ("BSE", "I"): "IDX_I", ("NSE", "E"): "NSE_EQ",
            ("MCX", "M"): "MCX_COMM", ("NSE", "C"): "NSE_CURRENCY"}
SCHEMA = {
    "version": 1,
    "row": {
        "ts": "str ISO IST, minute start (bar covers ts .. ts+59s)",
        "name": "str e.g. INDIAVIX, BANKNIFTY, SBIN, CRUDEOIL",
        "security_id": "str from Dhan scrip master", "segment": "str Dhan exchange segment",
        "symbol": "str scrip-master trading symbol (futures carry expiry)",
        "o": "float", "h": "float", "l": "float", "c": "float last LTP in the minute",
        "ticks": "int packets in the minute", "volume": "int|null cumulative day volume (QUOTE packets)",
        "prev_close": "float|null from Dhan prev-close packet", "src": "dhan_feed",
    },
    "notes": "Minutes with no packet are not written (a gap, never a carried price).",
}


@dataclass(frozen=True)
class CrossInstrument:
    name: str
    security_id: str
    segment: str
    symbol: str


def _expiry(row: dict[str, str]) -> str:
    return (row.get("SEM_EXPIRY_DATE") or "")[:10]


def resolve(csv_text: str, day: date) -> tuple[list[CrossInstrument], list[str]]:
    """Pure: scrip-master CSV text -> (instruments, missing names). Futures = nearest unexpired."""
    want_idx = {v.upper(): k for k, v in INDEXES.items()}
    found: dict[str, CrossInstrument] = {}
    fut_best: dict[str, tuple[str, CrossInstrument]] = {}
    d = day.isoformat()
    for r in csv.DictReader(io.StringIO(csv_text)):
        exch, seg, inst = r.get("SEM_EXM_EXCH_ID", ""), r.get("SEM_SEGMENT", ""), r.get("SEM_INSTRUMENT_NAME", "")
        sym = (r.get("SEM_TRADING_SYMBOL") or "").strip()
        sid = (r.get("SEM_SMST_SECURITY_ID") or "").strip()
        segment = SEGMENTS.get((exch, seg))
        if not sid or not segment:
            continue
        if inst == "INDEX" and exch == "NSE" and sym.upper() in want_idx:
            n = want_idx[sym.upper()]
            found.setdefault(n, CrossInstrument(n, sid, segment, sym))
        elif inst == "EQUITY" and exch == "NSE" and sym in HEAVYWEIGHTS and (r.get("SEM_SERIES") or "EQ") == "EQ":
            found.setdefault(sym, CrossInstrument(sym, sid, segment, sym))
        else:
            for n, (fx, fi, pre) in FUTURES.items():
                if exch == fx and inst == fi and sym.startswith(pre) and _expiry(r) >= d:
                    e = _expiry(r)
                    if n not in fut_best or e < fut_best[n][0]:
                        fut_best[n] = (e, CrossInstrument(n, sid, segment, sym))
    for n, (_, ci) in fut_best.items():
        found[n] = ci
    order = list(INDEXES) + list(HEAVYWEIGHTS) + list(FUTURES)
    return [found[n] for n in order if n in found], [n for n in order if n not in found]


class MinuteBars:
    """Packet dicts (dhan_client.decode.packet_as_dict) -> closed 1-minute rows. Pure, no I/O."""

    def __init__(self, instruments: list[CrossInstrument]) -> None:
        self.by_id = {i.security_id: i for i in instruments}
        self.cur: dict[str, dict[str, Any]] = {}
        self.prev_close: dict[str, float] = {}

    def on_packet(self, pkt: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
        sid = str(pkt.get("security_id"))
        inst = self.by_id.get(sid)
        out = self.roll(now)
        if inst is None:
            return out
        f = pkt.get("fields") or {}
        if pkt.get("kind") == "prev_close" and f.get("prev_close"):
            self.prev_close[sid] = float(f["prev_close"])
            return out
        ltp = f.get("ltp")
        if not ltp or ltp <= 0:
            return out
        m = now.astimezone(IST).replace(second=0, microsecond=0)
        b = self.cur.get(sid)
        if b is None:
            b = self.cur[sid] = {"ts": m.isoformat(), "name": inst.name, "security_id": sid,
                                 "segment": inst.segment, "symbol": inst.symbol,
                                 "o": ltp, "h": ltp, "l": ltp, "c": ltp, "ticks": 0, "volume": None}
        b["h"], b["l"], b["c"] = max(b["h"], ltp), min(b["l"], ltp), ltp
        b["ticks"] += 1
        if f.get("volume") is not None:
            b["volume"] = int(f["volume"])
        return out

    def roll(self, now: datetime) -> list[dict[str, Any]]:
        """Emit bars whose minute has ended."""
        m = now.astimezone(IST).replace(second=0, microsecond=0).isoformat()
        done = [sid for sid, b in self.cur.items() if b["ts"] < m]
        rows = []
        for sid in done:
            b = self.cur.pop(sid)
            rows.append({**b, "o": round(b["o"], 4), "h": round(b["h"], 4), "l": round(b["l"], 4),
                         "c": round(b["c"], 4), "prev_close": self.prev_close.get(sid), "src": "dhan_feed"})
        return rows


class CrossTape:
    """Append rows to <root>/<name>/<day>.jsonl, flushed per write (one row per name per minute)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        (root / "SCHEMA.json").write_text(json.dumps(SCHEMA, indent=1), encoding="utf-8")

    def write(self, rows: list[dict[str, Any]]) -> None:
        for r in rows:
            p = self.root / r["name"] / f"{r['ts'][:10]}.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(r, separators=(",", ":")) + "\n")


def latest(root: Path, name: str, day: str) -> dict[str, Any] | None:
    """Last row of a tape (tail read, O(1)). Used by market_read."""
    p = root / name / f"{day}.jsonl"
    if not p.exists():
        return None
    with open(p, "rb") as fh:
        fh.seek(0, 2)
        fh.seek(max(0, fh.tell() - 4096))
        lines = fh.read().splitlines()
    for ln in reversed(lines):
        try:
            return json.loads(ln)
        except ValueError:
            continue
    return None


async def _run(tape_root: Path, until: str) -> int:
    from dhan_client.config import load_settings
    from dhan_client.errors import CredentialsError
    from dhan_client.feed import MarketFeedCollector
    from dhan_client.instruments import InstrumentClient
    from dhan_client.rest import RestClient
    from dhan_client.types import FeedInstrument, FeedMode

    try:
        settings = load_settings(dry_run=False)
    except CredentialsError:
        log.error("needs DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN (same .env as the V2 recorder)")
        return 2
    day = datetime.now(IST).date()
    text = InstrumentClient(RestClient(settings)).fetch_scrip_master_text()
    insts, missing = resolve(text, day)
    tape = CrossTape(tape_root)
    (tape_root / "missing.json").write_text(json.dumps({"day": day.isoformat(), "missing": missing,
                                                         "resolved": [i.__dict__ for i in insts]}, indent=1))
    log.info("cross recorder: %d instruments, missing=%s", len(insts), missing)
    bars = MinuteBars(insts)
    feed = MarketFeedCollector(settings, [FeedInstrument(i.segment, i.security_id) for i in insts],
                               mode=FeedMode.QUOTE, index_mode=FeedMode.QUOTE)

    def on_packet(pkt: dict[str, Any]) -> None:
        tape.write(bars.on_packet(pkt, datetime.now(IST)))

    async def clock() -> None:
        while True:
            await asyncio.sleep(1)
            now = datetime.now(IST)
            tape.write(bars.roll(now))
            if now.strftime("%H:%M") >= until:
                feed.stop()
                return

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, feed.stop)
    tick = asyncio.create_task(clock())
    try:
        await feed.run(on_packet)
    finally:
        tick.cancel()
        tape.write(bars.roll(datetime.now(IST) + timedelta(minutes=1)))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m marketdata.cross_market")
    ap.add_argument("--record-only", action="store_true")
    ap.add_argument("--tape-root", type=Path, default=None, help="default <repo>/data/tape/cross")
    ap.add_argument("--until", default="15:35", help="IST HH:MM to stop (default 15:35)")
    ap.add_argument("--resolve", type=Path, help="print ids resolved from a local scrip-master CSV and exit")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("websockets").setLevel(logging.WARNING)
    if a.resolve:
        insts, missing = resolve(a.resolve.read_text(encoding="utf-8"), datetime.now(IST).date())
        print(json.dumps({"resolved": [i.__dict__ for i in insts], "missing": missing}, indent=1))
        return 0
    if not a.record_only:
        ap.error("pass --record-only")
    from dhan_client.config import repo_root
    root = a.tape_root or repo_root() / "data" / "tape" / "cross"
    try:
        return asyncio.run(_run(root, a.until))
    except KeyboardInterrupt:
        return 0
    except Exception:
        log.exception("cross recorder crashed (desk loop unaffected)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
