"""B2b, R02, R20 off from desk slots and promotion (config only); still shadow-scored."""

from __future__ import annotations

from pathlib import Path

import yaml

from desk_ml import research_rules as rr

REPO = Path(__file__).resolve().parents[3]


def test_config_lists_exactly_the_three() -> None:
    blob = yaml.safe_load((REPO / "config" / "desk_rules_off.yaml").read_text())
    assert [i["id"] for i in blob["rules_off"]] == ["B2b", "R02", "R20", "R01_B3A_VOL"]
    off = rr.desk_rules_off()
    assert {"B2b", "R20", rr.R02, rr.R01_B3A} <= off
    assert rr.R01 not in off  # 2026-10-13 Sahil: R01 back on paper
    assert not {"B6a", "R15", "R19", "R21"} & off


def test_no_off_rule_in_v2_account_slots() -> None:
    text = (REPO / "config" / "v2" / "accounts.yaml").read_text()
    accts = yaml.safe_load(text)["accounts"]
    ids = {str(a.get("strategy_id") or "") for a in accts if a.get("status") == "active"}
    assert not ids & rr.desk_rules_off()


def test_replay_never_trades_r02_on_a_new_day(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(rr, "SHADOW_RULE_IDS", ())  # even if un-parked, the off list keeps R02 off the desk
    monkeypatch.setattr(rr, "LIVE_RULE_IDS", (rr.R01, rr.R01_B3A, rr.R02))
    res = rr.replay(tmp_path, "2026-10-13")
    assert rr.R02 not in res["rule_ids"]
    assert rr.R02 in res["shadow_parked"]["rule_ids"]


def test_replay_r01_on_b3a_off_on_a_new_day(tmp_path) -> None:
    res = rr.replay(tmp_path, "2026-10-13")
    assert rr.R01 in res["rule_ids"]  # 2026-10-13 Sahil: R01 back on paper
    assert rr.R01_B3A not in res["rule_ids"]
    assert rr.R01_B3A in set(res["shadow_parked"]["rule_ids"])
