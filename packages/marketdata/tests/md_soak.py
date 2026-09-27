"""Real-time soak (not collected by pytest). No shim: real recorder, collector, decoder, writers.

    PYTHONPATH=packages/marketdata/tests python packages/marketdata/tests/md_soak.py OUT_DIR [START_HHMM]

The clock runs at real speed from START (default 15:19 IST), so the recorder's own 15:30 stop
ends the run. Scenario: spot trends +0.3 pt/s (re-centres), a 30 s outage at START+3 min with
reconnects rejected, the ATM CE silent 20 s at START+5 min, bad frames every minute.
"""

from __future__ import annotations

import asyncio
import base64
import json
import resource
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from md_fake_dhan import (
    FakeDhanServer,
    Market,
    OffsetClock,
    StubSource,
    ist,
    make_universe,
    option_sid,
    read_rows,
    schema_errors,
    settings_for,
)

from marketdata.__main__ import setup_logging
from marketdata.config import RecorderConfig
from marketdata.recorder import MarketDataRecorder


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))] if ordered else float("nan")


async def soak(out: Path, start: datetime) -> dict[str, Any]:
    universe = make_universe()
    clock = OffsetClock(start)
    sent_at: dict[str, datetime] = {}
    events: list[str] = []
    async with FakeDhanServer() as server:
        rec = MarketDataRecorder(
            RecorderConfig(tape_root=out / "tape", cache_dir=out / "cache"),
            settings_for(server.url, out),
            source=StubSource(),
            clock=clock,
        )
        task = asyncio.create_task(rec.run())
        atm_ce = option_sid(24500, "CE")
        t_out = start + timedelta(minutes=3)
        t_silent = start + timedelta(minutes=5)
        rates = {int(universe.index.security_id): 1.0}
        market = Market(
            universe,
            lambda t: 24512.35 + 0.3 * (t - start).total_seconds(),
            default_hz=5.0,
            rates=rates,
            silent={atm_ce: [(t_silent, t_silent + timedelta(seconds=20))]},
        )
        outage_done = False
        next_bad = start + timedelta(seconds=60)
        while not task.done():
            now = clock.now()
            if not outage_done and now >= t_out:
                server.reject_status = 503
                await server.drop_clients()
                events.append(f"{now:%H:%M:%S} outage start")
                outage_done = True
            if server.reject_status and now >= t_out + timedelta(seconds=30):
                server.reject_status = None
                events.append(f"{now:%H:%M:%S} outage end")
            if now >= next_bad and server.client_count:
                await server.send(b"\x01\x02")
                await server.send('{"note":"text frame"}')
                next_bad += timedelta(seconds=60)
            for frame in market.frames(now, server.subscribed if server.client_count else {}):
                if await server.send(frame):
                    sent_at[base64.b64encode(frame).decode()] = now
            await asyncio.sleep(0.02)
        code = task.result()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "exit_code": code,
        "stop_reason": rec.stop_reason,
        "stopped_at": clock.now().isoformat(),
        "events": events,
        "packets_sent": market.packets,
        "connections": server.connections,
        "cpu_s": round(usage.ru_utime + usage.ru_stime, 1),
        "max_rss_mb": round(usage.ru_maxrss / 1024, 1),
        "sent_at": sent_at,
    }


def analyse(out: Path, run: dict[str, Any], start: datetime, wall_s: float) -> dict[str, Any]:
    day = out / "tape" / start.date().isoformat()
    streams = {p.stem: p.read_bytes().count(b"\n") for p in sorted(day.glob("*.jsonl"))}
    depth = read_rows(day / "depth_quotes.jsonl")
    by_iid: dict[str, list[datetime]] = defaultdict(list)
    for r in depth:
        by_iid[r["payload"]["instrument_id"]].append(datetime.fromisoformat(r["timestamp"]))
    down = [
        (datetime.fromisoformat(r["timestamp"]), r["payload"]["status"])
        for r in read_rows(day / "feed_status.jsonl")
        if r["payload"]["status"] in ("UP", "DOWN")
    ]
    outage = [(a, b) for (a, sa), (b, sb) in zip(down, down[1:], strict=False) if sa == "DOWN" and sb == "UP"]
    gaps: dict[str, dict[str, float]] = {}
    for iid, times in by_iid.items():
        g = [(b - a).total_seconds() for a, b in zip(times, times[1:], strict=False)]
        g_live = [
            (b - a).total_seconds()
            for a, b in zip(times, times[1:], strict=False)
            if not any(o0 <= b and a <= o1 for o0, o1 in outage)
        ]
        gaps[iid] = {
            "rows": len(times),
            "max_gap_s": round(max(g), 3) if g else 0.0,
            "max_gap_excl_outage_s": round(max(g_live), 3) if g_live else 0.0,
            "p99_gap_s": round(pct(g_live, 0.99), 3) if g_live else 0.0,
            "gaps_over_1_05s_excl_outage": sum(x > 1.05 for x in g_live),
        }
    quotes = read_rows(day / "quote_snapshots.jsonl")
    q_by: dict[str, list[datetime]] = defaultdict(list)
    for r in quotes:
        q_by[r["payload"]["instrument_id"]].append(datetime.fromisoformat(r["timestamp"]))
    q_int = [(b - a).total_seconds() for ts in q_by.values() for a, b in zip(ts, ts[1:], strict=False)]
    q_off = [min(t.timestamp() % 5, 5 - t.timestamp() % 5) for ts in q_by.values() for t in ts]
    latency = []
    for r in read_rows(day / "raw_frames.jsonl"):
        sent = run["sent_at"].get(r["raw_b64"])
        if sent is not None:
            latency.append((datetime.fromisoformat(r["recv_ts"]) - sent).total_seconds() * 1000)
    proc_lat = [
        (datetime.fromisoformat(r["available_ts"]) - datetime.fromisoformat(r["event_ts"])).total_seconds() * 1000
        for r in depth
        if not r["payload"]["repeat"]
    ]
    counts, errors = schema_errors(day)
    ingest = Counter(r["reason"] for r in read_rows(day / "ingest_errors.jsonl"))
    subs = read_rows(day / "subscriptions.jsonl")
    summary = json.loads((day / "coverage_summary.json").read_text())
    rows_total = sum(v for k, v in streams.items() if k in ("depth_quotes", "quote_snapshots", "oi_cadence"))
    market_s = (min(datetime.fromisoformat(run["stopped_at"]), ist(15, 30)) - start).total_seconds()
    return {
        "wall_s": round(wall_s, 1),
        "exit_code": run["exit_code"],
        "stop_reason": run["stop_reason"],
        "process_finished_at": run["stopped_at"],
        "last_depth_row_at": max(r["timestamp"] for r in depth),
        "stop_logged": [r["payload"] for r in read_rows(day / "feed_status.jsonl")][-1],
        "events": run["events"],
        "connections": run["connections"],
        "packets_sent": run["packets_sent"],
        "rows_per_stream": streams,
        "payload_rows_per_s": round(rows_total / market_s, 2),
        "outage_windows": [[a.isoformat(), b.isoformat()] for a, b in outage],
        "depth_gaps": gaps,
        "quote_interval_s": {"min": min(q_int), "max": max(q_int), "median": statistics.median(q_int)},
        "quote_offset_from_5s_boundary_max_s": round(max(q_off), 3),
        "feed_latency_ms": {
            "n": len(latency),
            "p50": round(pct(latency, 0.5), 2),
            "p99": round(pct(latency, 0.99), 2),
            "max": round(max(latency), 2),
        },
        "recv_to_row_ms": {"p50": round(pct(proc_lat, 0.5), 2), "max": round(max(proc_lat), 2)},
        "schema_rows_checked": counts,
        "schema_errors": errors[:20],
        "schema_error_count": len(errors),
        "ingest_errors": dict(ingest),
        "recentres": sorted({r["atm"] for r in subs if r["reason"] == "recentre"}),
        "unsubscribes": sum(r["action"] == "unsubscribe" for r in subs),
        "coverage_failing": summary["failing"],
        "cpu_s": run["cpu_s"],
        "max_rss_mb": run["max_rss_mb"],
    }


def main() -> int:
    out = Path(sys.argv[1])
    hhmm = sys.argv[2] if len(sys.argv) > 2 else "1519"
    start = ist(int(hhmm[:2]), int(hhmm[2:]))
    out.mkdir(parents=True, exist_ok=True)
    listener = setup_logging(out / "soak.log")  # the product's logging setup
    t0 = time.monotonic()
    run = asyncio.run(soak(out, start))
    listener.stop()
    report = analyse(out, run, start, time.monotonic() - t0)
    (out / "soak_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    return 0 if report["schema_error_count"] == 0 and report["exit_code"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
