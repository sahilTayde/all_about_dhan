"""Runner-level Q01 checks on synthetic bars (no network, writes only to tmp)."""
import json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

os.environ["PX_DAY"] = "2026-10-14"
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "desk-ml" / "src"))
import runner as R  # noqa: E402
from desk_ml import q01  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))


def _ts(m):
    return int(datetime(2026, 10, 14, m // 60, m % 60, tzinfo=IST).timestamp())


def _setup(tmp_path, monkeypatch, *, vix_date="2026-10-13", open_px=22500.0):
    run = tmp_path / "run"; run.mkdir()
    ms = list(range(555, 640))
    idx = {m: 22500.0 + (m - 555) * 1.0 for m in ms}  # rising -> mv > 0 -> PE
    (run / "IDX_NIFTY.json").write_text(json.dumps({"timestamp": [_ts(m) for m in ms], "open": [idx[m] for m in ms], "close": [idx[m] for m in ms]}))
    s10 = idx[600]; K = int(round(s10 / 50) * 50) + 100
    om = list(range(600, 640))
    (run / f"NIFTY_2026-10-20_{K}_PE.json").write_text(json.dumps({"timestamp": [_ts(m) for m in om], "open": [100.0] * len(om), "close": [101.0] * len(om)}))
    monkeypatch.setattr(R, "LIVE_RUN", run); monkeypatch.setattr(R, "EXP", "2026-10-20"); monkeypatch.setattr(R, "BG_DIR", tmp_path / "bg")
    monkeypatch.setattr(R, "write_vix_daily", lambda: {})
    monkeypatch.setattr(q01, "vix_filter", lambda v, d: {"armed": True, "pct": 0.9, "chg": 0.03, "v1_date": vix_date, "status": "OK", "v1": 20.0})
    monkeypatch.setattr(q01, "official_open", lambda p: (open_px, "raw_frames_preopen") if open_px else (None, "OPEN_MISSING"))
    return K


def test_nothing_before_entry_bar_and_t15_never_a_desk_row(tmp_path, monkeypatch):
    K = _setup(tmp_path, monkeypatch)
    rows, bg, txt = R.q01_cycle(600)
    assert rows == [] and bg is None  # 10:01 bar not complete yet
    rows, bg, txt = R.q01_cycle(601)
    assert [r["rule_id"] for r in rows] == ["Q01_ITM100"] and rows[0]["strike"] == K and rows[0]["side"] == "PE"
    assert rows[0]["entry_px"] == 100.05 and rows[0]["planned_exit_ist"] == "10:21" and rows[0]["stop_px"] is None
    assert bg["rule_id"] == "Q01_T15" and bg["target_px"] == round(100.05 + 1.5 * 0.3 * 100.05, 2)
    rows, bg, txt = R.q01_cycle(625)
    assert rows[0]["status"] == "CLOSED" and rows[0]["exit_time"] == "10:21" and rows[0]["exit_reason"] == "TIME"
    R.write_bg_t15(bg)
    t = json.loads((tmp_path / "bg" / "2026-10-14.json").read_text())["trades"]
    assert [x["strategy"] for x in t] == ["Q01_T15"] and t[0]["count_in_total"] is False


def test_stale_vix_is_data_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, vix_date="2026-10-12")
    rows, bg, txt = R.q01_cycle(625)
    assert rows == [] and "DATA_MISSING" in txt


def test_missing_official_open_is_data_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, open_px=None)
    rows, bg, txt = R.q01_cycle(625)
    assert rows == [] and "OPEN_MISSING" in txt
