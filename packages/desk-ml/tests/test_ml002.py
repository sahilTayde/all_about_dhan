"""ML-002 MRR/OU + book-tune inventory. Cache fixtures only."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from desk_ml.book_tune import run_book_tune
from desk_ml.features import Triple, build_feature_rows
from desk_ml.inventory import inventory_recon
from desk_ml.mrr import mrr_fit_underlying, ou_ar1, pick_preferred, rolling_z, score_mrr_last, vwma
from desk_ml.tape import load_triples

IST = timezone(timedelta(hours=5, minutes=30))


def _ts(i: int) -> int:
    return int(datetime(2026, 9, 11, 9, 15, tzinfo=IST).timestamp()) + i * 60


def _triples() -> list[Triple]:
    out: list[Triple] = []
    idx, ce, pe = 25000.0, 120.0, 110.0
    n = 0

    def push(di: float, dce: float, dpe: float, count: int) -> None:
        nonlocal idx, ce, pe, n
        for _ in range(count):
            idx += di
            ce = max(5.0, ce + dce)
            pe = max(5.0, pe + dpe)
            out.append(Triple(ts=_ts(n), idx_close=idx, ce_close=ce, pe_close=pe))
            n += 1

    push(8.0, 1.6, -1.2, 50)
    push(-8.0, -1.5, 1.7, 50)
    push(0.2, 0.05, -0.04, 40)
    push(-10.0, -0.2, -1.8, 20)
    return out


def test_ou_mean_reverting_ar1() -> None:
    x = [1.0]
    for _ in range(120):
        x.append(0.75 * x[-1])
    out = ou_ar1(x)
    assert out["mean_reverting"] is True
    assert out["half_life_bars"] is not None
    assert out["half_life_bars"] > 0


def test_replay_hold_no_win_rate() -> None:
    from desk_ml.replay import replay_hold

    report = replay_hold("NIFTY", triples=_triples())
    assert report["ok"] is True
    assert report["win_rate"] is None
    assert report["promote"] is False
    assert report["production_params_written"] is False
    names = {r["rule"] for r in report["rules"]}
    assert names == {
        "FOLLOW_GAP",
        "ML-001_HOLD",
        "ML-002_Z>=2",
        "UNION_HOLD",
        "DIVERGE_ONLY",
        "UNION_NO_FOLLOW_GAP",
    }
    assert report["n_scored"] > 0


def test_mrr_fit_three_windows_no_promote() -> None:
    report = mrr_fit_underlying("NIFTY", persist=False, triples=_triples())
    assert report["ok"] is True
    assert report["promote"] is False
    assert report["production_params_written"] is False
    assert report["win_rate"] is None
    assert report["gate"] == "BACKTEST_REQUIRED"
    assert report["windows_tried"] == [40, 60, 90]
    assert len(report["tweaks"]) == 3
    assert set(t["window"] for t in report["tweaks"]) == {40, 60, 90}


def test_rolling_z_excludes_current() -> None:
    vals = [0.0, 1.0, -1.0, 0.5, 8.0]
    zs = rolling_z(vals, 4)
    assert zs[0] is None
    assert zs[3] is None
    assert zs[4] is not None
    assert zs[4] > 2.0


def test_vwma_equal_weight_when_vol_zero() -> None:
    closes = [10.0, 20.0, 30.0, 40.0]
    vols = [0.0, 0.0, 0.0, 0.0]
    out = vwma(closes, vols, 3)
    assert out[0] is None
    assert out[1] is None
    assert abs(out[2] - 20.0) < 1e-9
    assert abs(out[3] - 30.0) < 1e-9


def test_pick_preferred_empty() -> None:
    out = pick_preferred(
        [{"window": 40, "n_scored": 2, "ou": {"mean_reverting": False}, "mean_abs_z": 1.0}]
    )
    assert out["status"] == "DATA_INSUFFICIENT"
    assert out["window"] is None


def test_inventory_empty_tmp(tmp_path: Path) -> None:
    as_of = datetime(2026, 9, 14, 12, 0, tzinfo=IST)
    inv = inventory_recon(root=tmp_path, calendar_days=21, as_of=as_of)
    assert inv["promote"] is False
    assert inv["joins"]["NIFTY"]["week_tape_missing"] is True
    assert any("DATA_INSUFFICIENT" in g for g in inv["data_gaps"])


def test_book_tune_fixture_writes_json(tmp_path: Path) -> None:
    ohlc = tmp_path / "data" / "recon" / "ohlc"
    tape = tmp_path / "data" / "recon" / "premium_tape"
    ohlc.mkdir(parents=True)
    tape.mkdir(parents=True)
    triples = _triples()
    ts = [t.ts for t in triples]
    chart = {
        "timestamp": ts,
        "open": [t.idx_close for t in triples],
        "high": [t.idx_close + 1 for t in triples],
        "low": [t.idx_close - 1 for t in triples],
        "close": [t.idx_close for t in triples],
        "volume": [1] * len(triples),
    }
    (ohlc / "INDEX_IDX_I_13_1_2026-09-11_2026-09-11.json").write_text(json.dumps(chart))
    payload = {
        "ce": [
            {"ts": t.ts, "open": t.ce_close, "high": t.ce_close, "low": t.ce_close, "close": t.ce_close, "volume": 10}
            for t in triples
        ],
        "pe": [
            {"ts": t.ts, "open": t.pe_close, "high": t.pe_close, "low": t.pe_close, "close": t.pe_close, "volume": 10}
            for t in triples
        ],
    }
    (tape / "NIFTY_ATM_1m_2026-09-11.json").write_text(json.dumps(payload))
    as_of = datetime(2026, 9, 14, 18, 0, tzinfo=IST)
    report = run_book_tune(
        root=tmp_path,
        calendar_days=21,
        underlyings=("NIFTY",),
        persist=True,
        as_of=as_of,
    )
    assert report["production_params_written"] is False
    assert report["promote"] is False
    assert report["gate"] == "BACKTEST_REQUIRED"
    assert report["ml001_seed"] == 14
    nifty = report["models"]["NIFTY"]
    assert nifty["ml001_fit"]["ok"] is True
    assert set(nifty["ml001_fit"]["cluster_sizes"]) <= {"TREND_UP", "TREND_DN", "RANGE", "DIVERGE"}
    assert nifty["ml002_mrr_fit"]["ok"] is True
    path = Path(report["path"])
    assert path.name == "BOOK_MODEL_TUNE_2026-09-14.json"
    assert path.is_file()
    joined, meta = load_triples("NIFTY", root=tmp_path)
    assert meta["aligned_triples"] == len(triples)
    assert len(build_feature_rows(joined)) == len(triples) - 1


def test_load_triples_window_filter(tmp_path: Path) -> None:
    ohlc = tmp_path / "data" / "recon" / "ohlc"
    tape = tmp_path / "data" / "recon" / "premium_tape"
    ohlc.mkdir(parents=True)
    tape.mkdir(parents=True)
    ts = [_ts(i) for i in range(5)]
    chart = {
        "timestamp": ts,
        "open": [25000] * 5,
        "high": [25001] * 5,
        "low": [24999] * 5,
        "close": [25000] * 5,
        "volume": [1] * 5,
    }
    (ohlc / "INDEX_IDX_I_13_1_2026-09-11_2026-09-11.json").write_text(json.dumps(chart))
    payload = {
        "ce": [{"ts": t, "close": 100.0} for t in ts],
        "pe": [{"ts": t, "close": 90.0} for t in ts],
    }
    (tape / "NIFTY_ATM_1m_2026-09-11.json").write_text(json.dumps(payload))
    all_t, _ = load_triples("NIFTY", root=tmp_path)
    none, meta = load_triples("NIFTY", root=tmp_path, min_ts=ts[-1] + 60, max_ts=ts[-1] + 120)
    assert len(all_t) == 5
    assert none == []
    assert "DATA_INSUFFICIENT" in meta["data_gaps"][0]



def test_mrr_score_last_no_promote(tmp_path: Path) -> None:
    report = mrr_fit_underlying("NIFTY", root=tmp_path, persist=True, triples=_triples())
    assert report["production_params_written"] is False
    scored = score_mrr_last("NIFTY", root=tmp_path, triples=_triples())
    assert scored["ok"] is True
    assert scored["promote"] is False
    assert scored["production_params_written"] is False
    assert scored["session_action"] in {"HOLD", "WATCH_ONLY"}
    assert scored.get("oos_claim") is not True


def test_causal_z_excludes_current_bar() -> None:
    values = [0.0, 1.0, 0.0, 1.0, 10.0]
    z = rolling_z(values, 4, causal=True)
    assert z[-1] is not None
    # Past window is 0,1,0,1; current 10 is not in the mean.
    assert abs(float(z[-1])) > 1.0
    leaky = rolling_z(values, 4, causal=False)
    assert leaky[-1] is not None
    assert abs(float(z[-1])) > abs(float(leaky[-1]))
