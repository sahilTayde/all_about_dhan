"""Config loader last-good fallback (REG-07) and EngineConfig validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from runtime.config import ConfigLoadError, load_with_last_good
from runtime.wiring import EngineConfig


def test_load_valid_config(tmp_path: Path) -> None:
    """Load valid config and cache last-good."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("key: value\nnumber: 42\n", encoding="utf-8")

    config = load_with_last_good(config_file, cache_dir=tmp_path)
    assert config == {"key": "value", "number": 42}
    assert (tmp_path / ".last_good_test.yaml").exists()


def test_reg_07a_bad_yaml_uses_last_good(tmp_path: Path) -> None:
    """REG-07a: bad YAML mid-session keeps last-good values."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("key: good\n", encoding="utf-8")
    assert load_with_last_good(config_file, cache_dir=tmp_path) == {"key": "good"}

    config_file.write_text("key: [bad\nunclosed: bracket\n", encoding="utf-8")
    assert load_with_last_good(config_file, cache_dir=tmp_path) == {"key": "good"}


def test_reg_07b_valid_file_after_bad(tmp_path: Path) -> None:
    """REG-07b: a valid file replaces last-good."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("key: first\n", encoding="utf-8")
    assert load_with_last_good(config_file, cache_dir=tmp_path) == {"key": "first"}

    config_file.write_text("invalid: yaml: bad\n", encoding="utf-8")
    assert load_with_last_good(config_file, cache_dir=tmp_path) == {"key": "first"}

    config_file.write_text("key: fixed\n", encoding="utf-8")
    assert load_with_last_good(config_file, cache_dir=tmp_path) == {"key": "fixed"}

    last_good = tmp_path / ".last_good_test.yaml"
    with last_good.open(encoding="utf-8") as handle:
        assert yaml.safe_load(handle) == {"key": "fixed"}


def test_reg_07c_no_valid_config_at_start_exits_only(tmp_path: Path) -> None:
    """REG-07c: no valid config at start means exits-only."""
    config_file = tmp_path / "nonexistent.yaml"
    config = load_with_last_good(config_file, cache_dir=tmp_path, exits_only_on_missing=True)
    assert config == {"exits_only": True}


def test_no_valid_config_raises_without_exits_only(tmp_path: Path) -> None:
    """Without exits_only_on_missing, missing file is rejected with a clear error."""
    config_file = tmp_path / "nonexistent.yaml"
    with pytest.raises(ConfigLoadError, match="rejected: config invalid and no last-good"):
        load_with_last_good(config_file, cache_dir=tmp_path, exits_only_on_missing=False)


def test_config_must_be_mapping(tmp_path: Path) -> None:
    """A YAML list is rejected with a clear error."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(ConfigLoadError, match="must be a mapping"):
        load_with_last_good(config_file, cache_dir=tmp_path, exits_only_on_missing=False)


def test_last_good_used_when_current_invalid(tmp_path: Path) -> None:
    """Last-good is used when current config becomes a scalar."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("max_trades: 10\nrisk_pct: 0.02\n", encoding="utf-8")
    config1 = load_with_last_good(config_file, cache_dir=tmp_path)
    assert config1["max_trades"] == 10

    config_file.write_text("just a string", encoding="utf-8")
    config2 = load_with_last_good(config_file, cache_dir=tmp_path)
    assert config2["max_trades"] == 10
    assert config2["risk_pct"] == 0.02


def test_engine_config_load_valid(tmp_path: Path) -> None:
    """EngineConfig.load reads YAML and exposes exits_only."""
    path = tmp_path / "engine.yaml"
    path.write_text("exits_only: false\nmax_trades: 3\n", encoding="utf-8")
    cfg = EngineConfig.load(path, cache_dir=tmp_path)
    assert cfg.exits_only is False
    assert cfg.data["max_trades"] == 3


def test_engine_config_rejects_bad_exits_only() -> None:
    """Bad exits_only type is rejected with a clear error."""
    with pytest.raises(ConfigLoadError, match="exits_only must be a bool"):
        EngineConfig({"exits_only": "yes"})


def test_engine_config_missing_file_exits_only(tmp_path: Path) -> None:
    """EngineConfig.load with no file starts exits-only."""
    cfg = EngineConfig.load(tmp_path / "missing.yaml", cache_dir=tmp_path)
    assert cfg.exits_only is True
