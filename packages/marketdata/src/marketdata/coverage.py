"""Per-instrument depth coverage for one recorded day, computed from the tape files.

A market minute counts as covered for an instrument when at least one packet for it was
received in that minute (a non-repeat DEPTH_QUOTE row; heartbeats do not count). Coverage is
measured against the minutes the instrument was subscribed (``subscriptions.jsonl``), inside
09:15-15:30 IST. The M1 gate asks for >= 95% on every traded instrument.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from marketdata.clock import IST, iso, market_close, market_open

GATE_PCT = 95.0
MIN_SUBSCRIBED_MINUTES = 30


def _rows(path: Path, bad: dict[str, int]) -> Iterator[dict[str, Any]]:
    bad[path.stem] = 0
    if not path.is_file():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                bad[path.stem] += 1


def _minute(ts: str, open_dt: datetime) -> int:
    return int((datetime.fromisoformat(ts) - open_dt).total_seconds() // 60)


def _ranges(minutes: list[int], open_dt: datetime) -> list[list[str]]:
    out: list[list[str]] = []
    for m in minutes:
        start = (open_dt + timedelta(minutes=m)).strftime("%H:%M")
        end = (open_dt + timedelta(minutes=m + 1)).strftime("%H:%M")
        if out and out[-1][1] == start:
            out[-1][1] = end
        else:
            out.append([start, end])
    return out


def summarize(day_dir: Path, day: date) -> dict[str, Any]:
    open_dt, close_dt = market_open(day), market_close(day)
    total = int((close_dt - open_dt).total_seconds() // 60)
    bad: dict[str, int] = {}

    subscribed: dict[str, set[int]] = defaultdict(set)
    since: dict[str, int] = {}
    for row in _rows(day_dir / "subscriptions.jsonl", bad):
        iid, m = row["instrument_id"], max(0, _minute(row["ts"], open_dt))
        if row["action"] == "subscribe":
            since.setdefault(iid, m)
        elif iid in since:
            subscribed[iid].update(range(since.pop(iid), min(m, total)))
    for iid, m in since.items():
        subscribed[iid].update(range(m, total))

    covered: dict[str, set[int]] = defaultdict(set)
    rows: dict[str, int] = defaultdict(int)
    repeats: dict[str, int] = defaultdict(int)
    last_emit: dict[str, datetime] = {}
    max_gap: dict[str, float] = defaultdict(float)
    for env in _rows(day_dir / "depth_quotes.jsonl", bad):
        p = env["payload"]
        iid = p["instrument_id"]
        emitted = datetime.fromisoformat(env["timestamp"])
        if not open_dt <= emitted < close_dt:
            continue
        rows[iid] += 1
        if p["repeat"]:
            repeats[iid] += 1
        else:
            covered[iid].add(_minute(p["exchange_ts"], open_dt))
        if iid in last_emit:
            max_gap[iid] = max(max_gap[iid], (emitted - last_emit[iid]).total_seconds())
        last_emit[iid] = emitted

    instruments: dict[str, Any] = {}
    failing: list[str] = []
    for iid in sorted(set(subscribed) | set(rows)):
        expected = subscribed.get(iid, set())
        got = covered[iid] & expected
        pct = round(100.0 * len(got) / len(expected), 2) if expected else None
        instruments[iid] = {
            "subscribed_minutes": len(expected),
            "minutes_with_depth": len(got),
            "pct_of_subscribed": pct,
            "pct_of_session": round(100.0 * len(covered[iid] & set(range(total))) / total, 2),
            "gaps": _ranges(sorted(expected - got), open_dt),
            "depth_rows": rows[iid],
            "repeat_rows": repeats[iid],
            "max_row_gap_s": round(max_gap[iid], 3),
        }
        if len(expected) >= MIN_SUBSCRIBED_MINUTES and (pct or 0.0) < GATE_PCT:
            failing.append(iid)
    return {
        "day": day.isoformat(),
        "generated_at": iso(datetime.now(IST)),
        "market_minutes": total,
        "gate_pct": GATE_PCT,
        "gate_min_subscribed_minutes": MIN_SUBSCRIBED_MINUTES,
        "failing": failing,
        "bad_lines": bad,
        "instruments": instruments,
    }


def write_summary(day_dir: Path, day: date) -> Path:
    out = day_dir / "coverage_summary.json"
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(summarize(day_dir, day), indent=1), encoding="utf-8")
    tmp.replace(out)
    return out
