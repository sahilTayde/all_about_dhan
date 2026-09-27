"""REG-13: changing entry-location config changes config_hash (V2-08b)."""

from __future__ import annotations

from pathlib import Path

import yaml
from helpers import write_entry_cfg

from oms.planner import REPO_CHASE_YAML, REPO_ENTRY_YAML, load_chase_defaults, load_entry_location


def test_reg_13_entry_location_hash_changes(tmp_path: Path) -> None:
    base = load_entry_location()
    other = load_entry_location(write_entry_cfg(tmp_path, zones=["fvg"]))
    assert other.config_hash != base.config_hash
    chase = tmp_path / "chase_defaults.yaml"
    raw = yaml.safe_load(REPO_CHASE_YAML.read_text(encoding="utf-8"))
    raw["chase_timeout_s"] = 3.5
    chase.write_text(yaml.safe_dump(raw), encoding="utf-8")
    tweaked = load_entry_location(REPO_ENTRY_YAML, chase_path=chase)
    assert tweaked.config_hash != base.config_hash
    assert load_chase_defaults().chase_timeout_s == 2.0
