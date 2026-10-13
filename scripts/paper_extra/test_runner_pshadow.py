"""Runner-level premium-shadow checks (no network, tmp only): shadows land in the background box marked not counted, never in desk rows."""
import json, os, sys
from pathlib import Path

os.environ["PX_DAY"] = "2026-10-14"
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "desk-ml" / "src"))
import runner as R  # noqa: E402

JS = {"day": "2026-10-14", "data_through": "10:30", "errors": {}, "need_strikes": [24900, 25300],
      "rows": [{"name": "B2_P", "research_strat": "B2", "side": "CE", "strike": 24900, "signal_ist": "09:16", "S": 0.3, "k": 2.0,
                "status": "CLOSED", "em": 556, "en": 300.05, "stop_px": 210.04, "target_px": 480.08, "capm": 600, "xm": 590, "kind": "STOP",
                "fill_m": 591, "ex": 205.0},
               {"name": "VWAPCONT_PE_P", "research_strat": "VWAP_CONT", "side": "PE", "strike": 25300, "signal_ist": "10:10", "S": 0.3, "k": 1.5,
                "status": "OPEN", "em": 611, "en": 150.05, "stop_px": 105.03, "target_px": 217.57, "capm": 641, "mark_m": 630, "mark_px": 160.0}]}


def test_bg_only_not_counted_and_strikes_pinned(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "BG_DIR", tmp_path / "bg"); monkeypatch.setattr(R, "OUT", tmp_path / "recon" / "2026-10-14.json")
    monkeypatch.setattr(R, "PS_DIR", tmp_path / "ps"); monkeypatch.setattr(R, "RT", tmp_path / "rt")
    (tmp_path / "ps").mkdir(); (tmp_path / "ps" / "pshadow_latest.json").write_text(json.dumps(JS))
    started = []
    monkeypatch.setattr(R.subprocess, "Popen", lambda *a, **k: started.append(a) or type("P", (), {"poll": lambda s: None})())
    R.EXTRA_STRIKES.clear()
    txt = R.pshadow_cycle()
    assert "B2_P:CLOSED" in txt and started and {24900, 25300} <= R.EXTRA_STRIKES
    bg = json.loads((tmp_path / "bg" / "2026-10-14.json").read_text())
    tr = {t["strategy"]: t for t in bg["trades"]}
    assert set(tr) == {"SHADOW_B2_P", "SHADOW_VWAPCONT_PE_P"}
    assert all(t["count_in_total"] is False and t["verified"] == "SHADOW" and t["traded"] is False for t in tr.values())
    b = tr["SHADOW_B2_P"]
    assert (b["stop_px"], b["target_px"], b["entry_ist"], b["exit_ist"], b["exit_signal_ist"], b["exit_reason_std"], b["planned_exit_ist"]) == \
        (210.04, 480.08, "09:16", "09:51", "09:50", "STOP", "10:00")
    assert b["net_inr_1_5x"] is not None and b["net_inr_1_5x"] < (205.0 - 300.05) * 650
    v = tr["SHADOW_VWAPCONT_PE_P"]
    assert v["status"] == "OPEN" and v["exit_px"] is None and v["net_inr_1_5x"] is None and v["mark_px"] == 160.0
    # desk file is untouched by the shadow path
    R.write([], "x")
    assert json.loads(R.OUT.read_text())["rows"] == []
    # job still running -> no relaunch, no overlap
    assert R.pshadow_cycle() == "pshadow running"


def test_off_before_from_day(monkeypatch):
    monkeypatch.setattr(R, "DAY", "2026-10-13")
    assert R.pshadow_cycle().startswith("pshadow off")
