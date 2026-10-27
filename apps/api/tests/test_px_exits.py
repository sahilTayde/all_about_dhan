"""Read-only PX exit-labels + shadow-exits route. Fixtures in tests/fixtures/px_exits are TEST FIXTURES (see README there)."""

from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import px_exits

FIX = Path(__file__).parent / "fixtures" / "px_exits"
REPO = Path(__file__).resolve().parents[3]
DAY = "2026-10-21"


@pytest.fixture()
def roots(tmp_path, monkeypatch):
    recon, live = tmp_path / "recon", tmp_path / "live"
    shutil.copytree(FIX / "recon", recon)
    shutil.copytree(FIX / "live", live)
    monkeypatch.setattr(px_exits, "RECON_DIR", recon)
    monkeypatch.setattr(px_exits, "LIVE_DIR", live)
    return recon, live


def client():
    app = FastAPI()
    app.include_router(px_exits.router)
    return TestClient(app)


def by_rule(rows, rid):
    return next(r for r in rows if r["rule_id"] == rid)


def test_bad_day_422(roots):
    c = client()
    assert c.get("/research/px-exits", params={"day": "2026-13-40"}).status_code == 422
    assert c.get("/research/px-exits", params={"day": "../../etc"}).status_code == 422


def test_all_missing_is_ok_not_error(tmp_path, monkeypatch):
    monkeypatch.setattr(px_exits, "RECON_DIR", tmp_path / "nope")
    monkeypatch.setattr(px_exits, "LIVE_DIR", tmp_path / "nope2")
    j = client().get("/research/px-exits", params={"day": DAY}).json()
    assert j["ok"] is True and j["rows"] == [] and j["shadow_overlays"] == [] and j["shadow_narrow_open"] == []
    assert set(j["sources"].values()) == {"missing"}


def test_rows_only_px_and_sidecar_wins(roots):
    j = client().get("/research/px-exits", params={"day": DAY}).json()
    assert all(r["rule_id"].startswith("PX_") for r in j["rows"])  # R01 row (with a fake exit_status) is dropped
    orb = by_rule(j["rows"], "PX_ORB_A")
    assert orb["exit_status"]["label"] == "REVERSING"
    assert orb["exit_status"]["updated_ist"].endswith("13:40:17+05:30")  # sidecar (13:40:17) beats OUT json (13:39:50)
    assert orb["exit_status_src"] == "live_exits_status.json"
    fad = by_rule(j["rows"], "PX_IB_15")
    assert fad["exit_status"]["label"] == "FADING" and fad["exit_status_src"] == f"{DAY}.json"
    err = by_rule(j["rows"], "PX_VWAP_CONT")
    assert err["exit_status"]["error"]
    ep = by_rule(j["rows"], "PX_EP010")
    assert ep["status"] == "CLOSED" and "exit_status" not in ep and ep["live"] is None
    assert orb["regime"]["cell"] == "TREND|WITH|VOL_MID" and orb["shadow_narrow_open"]["would_skip"] is False
    assert j["in_desk_pnl"] is False and j["in_paper_extra_total"] is False and j["shadow_only"] is True


def test_jsonl_bad_lines_counted(roots):
    j = client().get("/research/px-exits", params={"day": DAY}).json()
    assert len(j["shadow_overlays"]) == 2 and j["bad_lines"]["shadow_overlays"] == 1
    assert j["shadow_overlays"][1]["ts"] is None
    assert len(j["shadow_narrow_open"]) == 1 and j["bad_lines"]["shadow_narrow_open"] == 0


def test_live_stop_orb_a_floor_and_gap(roots):
    j = client().get("/research/px-exits", params={"day": DAY}).json()
    lv = by_rule(j["rows"], "PX_ORB_A")["live"]
    # entry 634.65, S .3, hw 893.2: BE trail = 625.24; floor 729.85; gap .15 -> 893.2*0.85 = 759.22 binds
    assert lv["live_stop"] == 759.22 and lv["binding"] == "gap trail"
    assert lv["stop_floor"] == 729.85 and lv["trail_gap"] == 0.15 and lv["trail_armed"] is True
    eng = by_rule(j["rows"], "PX_ENG_5")["live"]
    assert eng["live_stop"] == 397.42 and eng["binding"] == "base stop" and eng["stop_floor"] is None


def test_live_stop_matches_pricer():
    """Same number as scripts/paper_extra/live_pricer.LiveTrade.stop for the same saved state."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("_lp", REPO / "scripts" / "paper_extra" / "live_pricer.py")
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)
    cases = [(634.65, 893.2, 729.85, 0.15), (634.65, 893.2, 729.85, None), (634.65, 700.0, None, None), (100.0, 131.0, None, None),
             (100.0, 150.0, None, 0.1), (100.0, 100.0, 95.0, None), (567.75, 577.4, None, None), (100.0, 129.9, 0.0, 0.0),
             (100.0, 90.0, None, 0.2)]
    for entry, hw, floor, gap in cases:
        t = lp.LiveTrade(["K", "NIFTY", "10:00"], "iid", entry, 0.3, 0.6, hw=hw)
        t.stop_floor, t.trail_gap = floor, gap
        got = px_exits.live_stop({"entry": entry, "S": 0.3, "hw": hw, "stop_floor": floor, "trail_gap": gap})["live_stop"]
        assert got == pytest.approx(t.stop, abs=0.006), (entry, hw, floor, gap)


def test_live_stop_missing_inputs_is_none():
    assert px_exits.live_stop({"entry": 100, "S": 0.3}) is None
    assert px_exits.live_stop({"entry": None, "S": 0.3, "hw": 120}) is None


def test_other_day_file_ignored(roots):
    recon, _ = roots
    blob = json.loads((recon / f"{DAY}.json").read_text())
    blob["day"] = "2026-10-20"
    (recon / f"{DAY}.json").write_text(json.dumps(blob))
    j = client().get("/research/px-exits", params={"day": DAY}).json()
    assert j["rows"] == [] and j["sources"]["rows"] == "other_day"


# ---- isolation: shadow / label data never reaches desk or paper-extra totals ----

def _desk_ml():
    p = str(REPO / "packages" / "desk-ml" / "src")
    if p not in sys.path:
        sys.path.insert(0, p)
    return pytest.importorskip("desk_ml.research_rules")


def test_paper_extra_rows_unchanged_by_shadow_fields(tmp_path):
    rr = _desk_ml()
    blob = json.loads((FIX / "recon" / f"{DAY}.json").read_text())
    with_root, without_root = tmp_path / "a", tmp_path / "b"
    for root, strip in ((with_root, False), (without_root, True)):
        d = root / "data" / "recon" / "paper_extra"
        d.mkdir(parents=True)
        b = copy.deepcopy(blob)
        if strip:
            for r in b["rows"]:
                for k in px_exits.SHADOW_FIELDS:
                    r.pop(k, None)
        else:  # shadow jsonl files present next to it as well
            shutil.copy(FIX / "recon" / f"shadow_overlays_{DAY}.jsonl", d)
            shutil.copy(FIX / "recon" / f"shadow_narrow_open_{DAY}.jsonl", d)
        (d / f"{DAY}.json").write_text(json.dumps(b))
    a, b = rr.paper_extra_rows(with_root, DAY), rr.paper_extra_rows(without_root, DAY)
    assert a == b
    dumped = json.dumps(a, default=str)
    for k in px_exits.SHADOW_FIELDS + ("base60_1m", "if_dr_applied", "net_inr_1_5x"):
        assert k not in dumped


def test_no_desk_module_reads_shadow_files():
    names = ("shadow_overlays_", "live_exits_status", "shadow_narrow_open", "px_exits")
    targets = [REPO / "packages" / "desk-ml" / "src" / "desk_ml" / "research_rules.py"]
    targets += [p for p in (REPO / "apps" / "api" / "src" / "api").glob("*.py") if p.name not in ("px_exits.py", "main.py")]
    for p in targets:
        text = p.read_text(encoding="utf-8")
        for n in names:
            assert n not in text, f"{p.name} references {n}"
    own = (REPO / "apps/api/src/api/px_exits.py").read_text(encoding="utf-8")
    imports = [ln for ln in own.splitlines() if ln.startswith(("import ", "from "))]
    assert not any(m in ln for ln in imports for m in ("ui_feed", "desk_merge", "research_rules", "runner", "desk_ml"))


def test_web_fixture_snapshot_in_sync():
    """apps/web/scripts/px_exits_fixture_response.json (web unit test input) == this route on the same fixture."""
    snap = json.loads((REPO / "apps" / "web" / "scripts" / "px_exits_fixture_response.json").read_text(encoding="utf-8"))
    snap.pop("_fixture")
    got = json.loads(json.dumps(px_exits.load_day(DAY, FIX / "recon", FIX / "live")))
    assert got == snap
