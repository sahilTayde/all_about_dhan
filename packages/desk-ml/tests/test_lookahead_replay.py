"""Same-day look-ahead must not enter replay S/R or follow-gap flags."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from desk_ml.features import Triple
from desk_ml.observer import follow_gap_itm_1m, follow_gap_series_itm_1m
from desk_ml.paper_scalp import build_sr_levels, replay_paper_scalp
from desk_ml.tape import ist_calendar_date

IST = timezone(timedelta(hours=5, minutes=30))
DAY_D = "2026-09-10"


def _ts(day: str, hour: int, minute: int, second: int = 0) -> int:
    y, m, d = (int(p) for p in day.split("-"))
    return int(datetime(y, m, d, hour, minute, second, tzinfo=IST).timestamp())


def _itm(ts: int, idx: float, ce: float, pe: float) -> Triple:
    return Triple(
        ts=ts,
        idx_close=idx,
        ce_close=ce,
        pe_close=pe,
        atm_strike=25000.0,
        itm_ce_close=ce,
        itm_pe_close=pe,
        itm_ce_strike=24800.0,
        itm_pe_strike=25200.0,
        premium_kind="ITM",
    )


def test_sr_preload_excludes_session_day(monkeypatch, tmp_path) -> None:
    """Day D's spike is in the close cache. Levels for day D must not contain it."""
    spike = 99999.0
    closes = {
        _ts("2026-09-07", 10, 0): 24000.0,
        _ts("2026-09-07", 15, 0): 24100.0,
        _ts("2026-09-08", 10, 0): 24050.0,
        _ts("2026-09-08", 15, 0): 23900.0,
        _ts("2026-09-09", 10, 0): 24020.0,
        _ts("2026-09-09", 15, 0): 24080.0,
        _ts(DAY_D, 9, 20): spike,
    }
    leaked = build_sr_levels(closes, session_ist_date=DAY_D)
    assert leaked["session_high"] == spike

    seen: dict = {}
    real = build_sr_levels

    def _spy(closes_by_ts, *, session_ist_date):
        seen["closes"] = dict(closes_by_ts)
        seen["day"] = session_ist_date
        out = real(closes_by_ts, session_ist_date=session_ist_date)
        seen["preload_high"] = out.get("session_high")
        seen["sr"] = out
        return out

    monkeypatch.setattr("desk_ml.paper_scalp.load_index_closes", lambda u, root=None: dict(closes))
    monkeypatch.setattr("desk_ml.paper_scalp.resolve_lot_size", lambda und, root=None: (65, "test"))
    monkeypatch.setattr("desk_ml.paper_scalp.build_sr_levels", _spy)

    triples = [_itm(_ts(DAY_D, 10, i), 24010.0 + i, 100.0, 90.0) for i in range(8)]
    replay_paper_scalp(
        root=tmp_path,
        underlyings=("NIFTY",),
        triples_by_und={"NIFTY": triples},
        write=False,
        session_ist_date=DAY_D,
    )

    assert seen["day"] == DAY_D
    assert seen["closes"], "prior sessions should still feed S/R"
    for ts, px in seen["closes"].items():
        assert ist_calendar_date(int(ts)) < DAY_D
        assert px != spike
    sr = seen["sr"]
    prices = [
        sr.get("pdh"),
        sr.get("pdl"),
        sr.get("pdc"),
        seen["preload_high"],
        sr.get("session_low"),
    ]
    prices.extend(sw.get("px") for sw in sr.get("swings") or [])
    assert spike not in prices
    assert seen["preload_high"] is None
    # step_underlying then fills session high from ticks already seen, not the cache spike.
    assert sr["session_high"] == 24017.0


def test_follow_gap_series_ignores_later_ticks() -> None:
    """A tick's flag must not change when any later timestamp is rewritten."""
    base = _ts(DAY_D, 10, 0)
    prev_early = _itm(base, 25000.0, 180.0, 180.0)
    prev_last = _itm(base + 30, 25000.0, 200.0, 180.0)
    early = _itm(base + 60, 25040.0, 210.0, 170.0)
    late = _itm(base + 90, 25100.0, 190.0, 160.0)
    nxt = _itm(base + 120, 25200.0, 220.0, 150.0)
    series = [prev_early, prev_last, early, late, nxt]

    out = follow_gap_series_itm_1m(series)
    assert out[0] is False and out[1] is False
    assert out[2] is False
    assert out[2] == bool(follow_gap_itm_1m(prev_last, early).get("follow_gap"))
    assert out[2] != bool(follow_gap_itm_1m(prev_last, late).get("follow_gap"))
    assert out[3] is True
    assert out[3] == bool(follow_gap_itm_1m(prev_last, late).get("follow_gap"))

    def _flags_before(index: int, replacement: Triple) -> list[bool]:
        changed = list(series)
        changed[index] = replacement
        return follow_gap_series_itm_1m(changed)[:index]

    assert _flags_before(4, _itm(base + 120, 10000.0, 500.0, 1.0)) == out[:4]
    assert _flags_before(3, _itm(base + 90, 20000.0, 50.0, 400.0)) == out[:3]
    assert _flags_before(2, _itm(base + 60, 10000.0, 1.0, 400.0)) == out[:2]
