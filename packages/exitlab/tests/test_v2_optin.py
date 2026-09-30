"""V2 default evaluate() is unchanged; playbook is OFF unless both flags are on."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from contracts.payloads import CatastrophicStop, ExitPlan, Level
from oms.exits import evaluate, load_exit_defaults, load_exitlab_playbook, plan_from_mapping
from risk_engine import IST

NOW = datetime(2026, 9, 17, 10, 30, tzinfo=IST)
REPO = Path(__file__).resolve().parents[3]


def _pos(mark_stop: float = 50.0) -> dict:
    return {
        "instrument_id": "NSE_FNO:NIFTY:2026-09-22:23200:CE",
        "net_qty": 65,
        "orig_qty": 65,
        "avg_price": 180.0,
        "stop_price": mark_stop,
        "fill_ts": NOW,
        "exit_plan": ExitPlan(
            catastrophic=CatastrophicStop(level=Level("premium", mark_stop)),
            flat_by_ist="15:15",
        ),
    }


def test_load_exitlab_playbook_off_by_default() -> None:
    assert load_exitlab_playbook() is None
    assert load_exitlab_playbook(enabled=False) is None
    # YAML enabled:false even if the function is asked to load
    path = REPO / "config" / "v2" / "exits" / "exitlab_playbook.yaml"
    assert path.is_file()
    assert load_exitlab_playbook(path, enabled=True) is None


def test_defaults_yaml_still_house_stop_only() -> None:
    raw, sha = load_exit_defaults(REPO / "config" / "v2" / "exits" / "defaults.yaml")
    assert raw["atr"] is None
    assert raw["trail"] is None
    assert raw["target"] is None
    assert raw["time_stops"] is None
    assert sha


def test_evaluate_default_still_house_stop_then_eod() -> None:
    pos = _pos(50.0)
    req = evaluate(pos, NOW, mark=49.0, quote_ts=NOW)
    assert req is not None
    assert req.reason == "CATASTROPHIC_STOP"
    pos2 = _pos(10.0)
    later = NOW.replace(hour=15, minute=15)
    req2 = evaluate(pos2, later, mark=180.0, quote_ts=later)
    assert req2 is not None
    assert req2.reason == "FLATTEN_EOD"


def test_playbook_mapping_compiles_when_yaml_enabled(tmp_path: Path) -> None:
    src = (REPO / "config" / "v2" / "exits" / "exitlab_playbook.yaml").read_text()
    src = src.replace("enabled: false", "enabled: true", 1)
    path = tmp_path / "playbook.yaml"
    path.write_text(src)
    mapping = load_exitlab_playbook(path, enabled=True)
    assert mapping is not None
    plan = plan_from_mapping(mapping)
    assert plan.flat_by_ist == "15:15"
    assert plan.catastrophic.level.kind == "max_loss_inr"
