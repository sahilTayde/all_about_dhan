"""REG-07: bad entry_location.yaml keeps last-good and raises CONFIG_INVALID."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from helpers import REPO
from risk_engine.last_good import ConfigInvalid

from oms.planner import load_entry_config


def test_reg_07_entry_config_invalid_keeps_last_good(tmp_path: Path) -> None:
    entry = yaml.safe_load((REPO / "config/v2/entry_location.yaml").read_text())
    chase = yaml.safe_load((REPO / "config/v2/entry/chase_defaults.yaml").read_text())
    epath = tmp_path / "entry_location.yaml"
    cpath = tmp_path / "chase_defaults.yaml"
    epath.write_text(yaml.safe_dump(entry))
    cpath.write_text(yaml.safe_dump(chase))
    cfg = load_entry_config(epath, cpath)
    good = dict(cfg.get())
    entry["boss_stretch"] = "veto"
    epath.write_text(yaml.safe_dump(entry))
    with pytest.raises(ConfigInvalid, match="CONFIG_INVALID"):
        cfg.reload()
    assert cfg.get() == good
    entry["boss_stretch"] = "record_only"
    entry["wait_consolidation"] = {
        "enabled": True,
        "consol_max_atr": None,
        "wait_max_bars": 3,
    }
    epath.write_text(yaml.safe_dump(entry))
    with pytest.raises(ConfigInvalid, match="null parameter"):
        cfg.reload()
    assert cfg.get() == good
