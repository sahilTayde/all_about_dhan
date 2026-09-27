"""
Test config loader with last-good fallback.

REG-07 tests from V2_BUILD_PLAN.md:
- REG-07a: Bad YAML mid-session keeps bus running with last-good values and one alert
- REG-07b: A valid file clears it
- REG-07c: No valid config at start means exits-only
"""

import tempfile
from pathlib import Path

import pytest
from contracts.config import ConfigLoadError, load_with_last_good


def test_load_valid_config(tmp_path: Path):
    """Load valid config."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("key: value\nnumber: 42\n")

    config = load_with_last_good(config_file, cache_dir=tmp_path)
    assert config == {"key": "value", "number": 42}

    # Check last-good was cached
    last_good = tmp_path / ".last_good_test.yaml"
    assert last_good.exists()


def test_reg_07a_bad_yaml_uses_last_good(tmp_path: Path):
    """REG-07a: Bad YAML mid-session keeps last-good values."""
    config_file = tmp_path / "test.yaml"

    # First: valid config
    config_file.write_text("key: good\n")
    config1 = load_with_last_good(config_file, cache_dir=tmp_path)
    assert config1 == {"key": "good"}

    # Second: bad YAML (truly invalid - unmatched bracket)
    config_file.write_text("key: [bad\nunclosed: bracket\n")
    config2 = load_with_last_good(config_file, cache_dir=tmp_path)
    # Should return last-good
    assert config2 == {"key": "good"}
    # Caller must raise CONFIG_INVALID alert


def test_reg_07b_valid_file_after_bad(tmp_path: Path):
    """REG-07b: A valid file clears the error state."""
    config_file = tmp_path / "test.yaml"

    # First: valid config
    config_file.write_text("key: first\n")
    config1 = load_with_last_good(config_file, cache_dir=tmp_path)
    assert config1 == {"key": "first"}

    # Second: bad YAML (uses last-good)
    config_file.write_text("invalid: yaml: bad\n")
    config2 = load_with_last_good(config_file, cache_dir=tmp_path)
    assert config2 == {"key": "first"}

    # Third: valid again
    config_file.write_text("key: fixed\n")
    config3 = load_with_last_good(config_file, cache_dir=tmp_path)
    assert config3 == {"key": "fixed"}

    # Check new last-good was cached
    last_good = tmp_path / ".last_good_test.yaml"
    import yaml

    with open(last_good) as f:
        assert yaml.safe_load(f) == {"key": "fixed"}


def test_reg_07c_no_valid_config_at_start_exits_only(tmp_path: Path):
    """REG-07c: No valid config at start means exits-only."""
    config_file = tmp_path / "nonexistent.yaml"

    # With exits_only_on_missing=True
    config = load_with_last_good(config_file, cache_dir=tmp_path, exits_only_on_missing=True)
    assert config == {"exits_only": True}


def test_no_valid_config_raises_without_exits_only(tmp_path: Path):
    """Without exits_only_on_missing, raises if no valid config."""
    config_file = tmp_path / "nonexistent.yaml"

    with pytest.raises(ConfigLoadError, match="Config invalid and no last-good"):
        load_with_last_good(config_file, cache_dir=tmp_path, exits_only_on_missing=False)


def test_config_must_be_dict(tmp_path: Path):
    """Config must be a dict, not a list or scalar."""
    config_file = tmp_path / "test.yaml"

    # List instead of dict
    config_file.write_text("- item1\n- item2\n")
    with pytest.raises(ConfigLoadError, match="must be a dict"):
        load_with_last_good(config_file, cache_dir=tmp_path, exits_only_on_missing=False)


def test_last_good_used_when_current_invalid(tmp_path: Path):
    """Last-good is used when current config becomes invalid."""
    config_file = tmp_path / "test.yaml"

    # Valid config
    config_file.write_text("max_trades: 10\nrisk_pct: 0.02\n")
    config1 = load_with_last_good(config_file, cache_dir=tmp_path)
    assert config1["max_trades"] == 10

    # Make it invalid (not a dict)
    config_file.write_text("just a string")
    config2 = load_with_last_good(config_file, cache_dir=tmp_path)
    # Should get last-good
    assert config2["max_trades"] == 10
    assert config2["risk_pct"] == 0.02
