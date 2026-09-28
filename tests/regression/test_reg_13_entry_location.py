"""REG-13: changing any entry-location or chase-default value changes config_hash."""

from __future__ import annotations

import yaml
from helpers import REPO
from strategies.params_hash import config_hash

from oms.planner import entry_config_hash


def test_reg_13_changing_entry_location_or_chase_defaults_changes_hash() -> None:
    entry = yaml.safe_load((REPO / "config/v2/entry_location.yaml").read_text())
    chase = yaml.safe_load((REPO / "config/v2/entry/chase_defaults.yaml").read_text())
    base = entry_config_hash(entry, chase)
    for key, value in (
        ("boss_stretch", "record_only"),
        ("default_entry_policy", "chase"),
    ):
        assert entry[key] == value
    tweaked = dict(entry)
    tweaked["fvg"] = {"fill_rule": "full", "max_age_bars": 30}
    assert entry_config_hash(tweaked, chase) != base
    chase_tweaked = dict(chase)
    chase_tweaked["chase_timeout_s"] = 3.0
    assert entry_config_hash(entry, chase_tweaked) != base
    assert config_hash(entry_location=entry, chase_defaults=chase) != config_hash(
        entry_location=tweaked, chase_defaults=chase
    )
