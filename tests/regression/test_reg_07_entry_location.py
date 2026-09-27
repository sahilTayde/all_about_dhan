"""REG-07: bad entry-location YAML keeps last-good and raises CONFIG_INVALID."""

from __future__ import annotations

from pathlib import Path

import pytest
from helpers import write_entry_cfg
from risk_engine.last_good import ConfigInvalid

from oms.planner import REPO_CHASE_YAML, EntryConfigStore


def test_reg_07_entry_location_keeps_last_good(tmp_path: Path) -> None:
    path = write_entry_cfg(tmp_path)
    store = EntryConfigStore(path, chase_path=REPO_CHASE_YAML)
    good = store.get()
    path.write_text(path.read_text(encoding="utf-8").replace("record_only", "veto"), encoding="utf-8")
    with pytest.raises(ConfigInvalid, match="CONFIG_INVALID"):
        store.get()
    assert store.last is not None
    assert store.last.config_hash == good.config_hash
