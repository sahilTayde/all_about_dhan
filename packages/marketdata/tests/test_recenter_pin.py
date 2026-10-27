"""2026-10-21 recentre-pin fix: contracts with an open (or just-closed) desk / paper_extra / shadow trade
are never unsubscribed or dropped from QUOTE_SNAPSHOT by a re-centre. Paper / shadow only.

The Oct 21 replay uses the real session's index spots (from tape_copies/2026-10-21/v2/depth_quotes.jsonl,
last LTP per second) and the real subscriptions.jsonl (sha 8d5081d9...) to check fidelity."""

from __future__ import annotations

import gzip
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from marketdata.instruments import Instrument, Universe
from marketdata.pins import HeldPinReader
from marketdata.strikes import StrikeSet

FIX = Path(__file__).parent / "fixtures"
DAY = date(2026, 10, 21)
EXP = {"NIFTY": "2026-10-27", "SENSEX": "2026-10-22"}
NIFTY_23000PE = "NSE_FNO:NIFTY:2026-10-27:23000:PE"
SENSEX_74100PE = "BSE_FNO:SENSEX:2026-10-22:74100:PE"
SENSEX_74500PE = "BSE_FNO:SENSEX:2026-10-22:74500:PE"
# When each contract had an open shadow / re-entry trade on Oct 21 (IST), from the lab's
# forward_exits and reentry_watch files. The 12:12-15:29 and 11:20 gaps fall inside these.
WINDOWS = {
    SENSEX_74500PE: ("10:42", "11:28"),
    NIFTY_23000PE: ("09:58", "15:15"),
    SENSEX_74100PE: ("10:13", "15:15"),
}


def _ts(hhmm: str) -> float:
    hh, mm = map(int, hhmm.split(":"))
    return datetime.fromisoformat(f"2026-10-21T{hh:02d}:{mm:02d}:00+05:30").timestamp()


def _universe(name: str, spot: float) -> Universe:
    step = 50 if name == "NIFTY" else 100
    lo, hi = (21500, 24500) if name == "NIFTY" else (70000, 78000)
    exch = "NSE" if name == "NIFTY" else "BSE"
    exp = EXP[name]
    options = {}
    sid = 100000 if name == "NIFTY" else 200000
    for k in range(lo, hi + step, step):
        for side in ("CE", "PE"):
            sid += 1
            options[(k, side)] = Instrument(f"{exch}_FNO:{name}:{exp}:{k}:{side}", str(sid), f"{exch}_FNO", "OPTION", exp, k, side)
    index = Instrument(f"{exch}_IDX:{name}", "13" if name == "NIFTY" else "51", "IDX_I", "INDEX")
    fut = Instrument(f"NSE_FNO:NIFTY:{exp}", "48704", "NSE_FNO", "FUTURE", exp) if name == "NIFTY" else None
    return Universe(underlying=name, expiry=exp, spot=spot, strike_step=step, index=index, future=fut, options=options)


def _spots() -> list[tuple[str, float, float]]:
    out = []
    with gzip.open(FIX / "oct21_index_spots.jsonl.gz", "rt") as fh:
        for line in fh:
            r = json.loads(line)
            out.append((r["u"], datetime.fromisoformat(r["ts"]).timestamp(), float(r["spot"])))
    return out


def _held_pins(root: Path, rows: list[dict]) -> None:
    p = root / "data" / "recon" / "held_pins" / f"{DAY.isoformat()}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


class _Clock:
    t = 0.0

    def __call__(self) -> float:
        return self.t


def _replay(root: Path | None, *, extra: bool = True, max_pinned: int | None = 40):
    """Drive one StrikeSet per underlying through the Oct 21 spot path, as the recorder does
    (update on every spot and every second). Returns events and per-minute snapshot membership."""
    clock = _Clock()
    spots = _spots()
    # The recorder's first update uses the universe spot (prev close from the chain), as logged in the
    # real subscriptions.jsonl "start" rows: NIFTY 22888.95, SENSEX 73852.9 at 09:13:00 IST.
    first = {"NIFTY": 22888.95, "SENSEX": 73852.9}
    unis = {u: _universe(u, first[u]) for u in ("NIFTY", "SENSEX")}
    pins = HeldPinReader(root, DAY, unis.values(), extra=extra, now=clock) if root is not None else None
    sets = {
        u: StrikeSet(
            uni,
            retention_s=600.0,
            max_instruments=100,
            open_positions=pins if pins is not None else (lambda: set()),
            open_ladder_n=5,
            near_atm_n=4,
            max_pinned=max_pinned if extra else None,
        )
        for u, uni in unis.items()
    }
    unsub: list[tuple[float, str]] = []
    snap: dict[str, list[float]] = {k: [] for k in WINDOWS}
    peak = 0
    last_min = -1
    for u in sets:
        clock.t = _ts("09:13")
        sets[u].update(first[u], clock.t)
    for u, t, s in spots:
        clock.t = t
        ch = sets[u].update(s, t)
        unsub += [(t, i.instrument_id) for i in ch.unsubscribe]
        peak = max(peak, sum(len(x.subscribed) for x in sets.values()))
        assert all(len(x.subscribed) <= 100 for x in sets.values())
        m = int(t // 60)
        if m != last_min:
            last_min = m
            targets = {**sets["NIFTY"].snapshot_targets(), **sets["SENSEX"].snapshot_targets()}
            for k in WINDOWS:
                if k in targets:
                    snap[k].append(t)
    return unsub, snap, peak, sets


def _in(t: float, a: str, b: str) -> bool:
    return _ts(a) <= t <= _ts(b)


def _covered(snap_times: list[float], a: str, b: str) -> float:
    want = int((_ts(b) - _ts(a)) // 60)
    got = sum(1 for t in snap_times if _in(t, a, b))
    return got / max(want, 1)


def _pin_rows() -> list[dict]:
    rows = []
    for iid, (a, b) in WINDOWS.items():
        rows.append({"event": "open", "instrument_id": iid, "ts": f"2026-10-21T{a}:00+05:30", "source": "lab_shadow", "trade_id": iid})
    return rows


def test_fixture_matches_tape_copy_sha() -> None:
    import hashlib

    h = hashlib.sha256((FIX / "oct21_subscriptions.jsonl").read_bytes()).hexdigest()
    assert h == "8d5081d9a0f6776c66494dd721d5045f58eee888cb9c842a62fc55077afe32c4"


def test_replay_without_fix_reproduces_oct21_cuts() -> None:
    """Fidelity: with no pins, the replay drops SENSEX 74500 PE around 11:30 (logged 11:30:15) and
    leaves 23000PE / 74100PE out of QUOTE_SNAPSHOT after ~12:12, as the real session did."""
    unsub, snap, _, _ = _replay(None)
    real = [json.loads(l) for l in (FIX / "oct21_subscriptions.jsonl").read_text().splitlines()]
    real_74500 = [r["ts"] for r in real if r["action"] == "unsubscribe" and r["instrument_id"] == SENSEX_74500PE]
    assert real_74500 and real_74500[0].startswith("2026-10-21T11:30")
    drops = [t for t, i in unsub if i == SENSEX_74500PE]
    assert drops and _in(drops[0], "11:25", "11:35")
    assert _covered(snap[NIFTY_23000PE], "12:20", "15:15") < 0.05
    assert _covered(snap[SENSEX_74100PE], "12:20", "15:15") < 0.05
    assert _covered(snap[SENSEX_74500PE], "11:21", "11:28") < 0.2


def test_replay_with_pins_keeps_all_three_contracts(tmp_path: Path) -> None:
    rows = _pin_rows()
    rows.append({"event": "close", "instrument_id": SENSEX_74500PE, "ts": "2026-10-21T11:28:00+05:30", "source": "lab_shadow", "trade_id": SENSEX_74500PE})
    _held_pins(tmp_path, rows)
    unsub, snap, peak, _ = _replay(tmp_path)
    for iid, (a, b) in WINDOWS.items():
        assert not [t for t, i in unsub if i == iid and _in(t, a, b)], iid
        assert _covered(snap[iid], a, b) >= 0.99, (iid, _covered(snap[iid], a, b))
    # 15-minute cooldown after the 11:28 close: still subscribed until 11:43.
    assert not [t for t, i in unsub if i == SENSEX_74500PE and t < _ts("11:43")]
    assert peak <= 200


def test_replay_off_switch_is_old_behaviour(tmp_path: Path) -> None:
    _held_pins(tmp_path, _pin_rows())
    unsub_off, snap_off, _, _ = _replay(tmp_path, extra=False)
    unsub_none, snap_none, _, _ = _replay(None)
    assert unsub_off == unsub_none
    assert snap_off == snap_none


def test_paper_extra_open_and_cooldown(tmp_path: Path) -> None:
    clock = _Clock()
    uni = _universe("NIFTY", 22900)
    book = {
        "rows": [
            {"strategy": "R07", "underlying": "NIFTY", "strike": 23000.0, "side": "PE", "entry_time": "10:05", "exit_time": None, "status": "OPEN"},
            {"strategy": "EP010", "underlying": "NIFTY", "strike": 22950.0, "side": "CE", "entry_time": "10:40", "exit_time": "11:41", "status": "CLOSED"},
            {"strategy": "IB_5", "underlying": "NIFTY", "strike": 22850.0, "side": "PE", "entry_time": None, "status": "SKIPPED_CHASE"},
        ]
    }
    p = tmp_path / "data" / "recon" / "paper_extra" / f"{DAY.isoformat()}.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(book))
    r = HeldPinReader(tmp_path, DAY, [uni], now=clock)
    clock.t = _ts("11:50")
    assert r.ranked() == ["NSE_FNO:NIFTY:2026-10-27:23000:PE", "NSE_FNO:NIFTY:2026-10-27:22950:CE"]
    clock.t = _ts("11:57")
    assert r.ranked() == ["NSE_FNO:NIFTY:2026-10-27:23000:PE"]
    off = HeldPinReader(tmp_path, DAY, [uni], extra=False, now=clock)
    assert off() == set()


def test_held_pins_two_watchers_on_one_contract(tmp_path: Path) -> None:
    clock = _Clock()
    uni = _universe("SENSEX", 74000)
    _held_pins(
        tmp_path,
        [
            {"event": "open", "underlying": "SENSEX", "strike": 74500, "side": "PE", "ts": "10:42", "source": "reentry", "trade_id": "K1_R01"},
            {"event": "open", "underlying": "SENSEX", "strike": 74500, "side": "PE", "ts": "10:42", "source": "reentry", "trade_id": "K1_B3a"},
            {"event": "close", "underlying": "SENSEX", "strike": 74500, "side": "PE", "ts": "11:20", "source": "reentry", "trade_id": "K1_R01"},
        ],
    )
    clock.t = _ts("13:00")
    assert HeldPinReader(tmp_path, DAY, [uni], now=clock)() == {SENSEX_74500PE}


def test_pin_cap_keeps_oldest_open_and_respects_subscription_limit(tmp_path: Path) -> None:
    clock = _Clock()
    clock.t = _ts("12:00")
    uni = _universe("NIFTY", 22900)
    rows = [
        {"event": "open", "underlying": "NIFTY", "strike": 21600 + 50 * i, "side": "CE", "ts": f"10:{i:02d}", "source": "s", "trade_id": str(i)}
        for i in range(55)
    ]
    _held_pins(tmp_path, rows)
    pins = HeldPinReader(tmp_path, DAY, [uni], now=clock)
    ss = StrikeSet(uni, retention_s=600, max_instruments=100, open_positions=pins, open_ladder_n=5, near_atm_n=4, max_pinned=40)
    ss.update(22900, clock.t)
    held = ss._held()
    assert len(held) == 40 and len(ss.pins_dropped) == 15
    assert held[0].endswith(":21600:CE")  # oldest open first
    assert len(ss.subscribed) <= 100
    assert all(i in ss.subscribed for i in held)


@pytest.mark.parametrize("value", ["11:20", "2026-10-21T11:20:00+05:30", 1792561800])
def test_timestamp_forms(tmp_path: Path, value) -> None:
    r = HeldPinReader(tmp_path, DAY)
    assert r._ts(value) == pytest.approx(_ts("11:20"))
