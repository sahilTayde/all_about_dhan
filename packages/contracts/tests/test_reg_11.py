"""REG-11 test data guard: prevent test writes to data/ and config/."""

import subprocess

import pytest


@pytest.mark.reg11a_probe
def test_reg11a_write_to_data_is_blocked(tmp_path):
    """REG-11a probe: writes into data/ must be blocked by audit hook."""
    from pathlib import Path

    with pytest.raises(PermissionError, match="REG-11: test writes"):
        (Path("data") / "test.txt").write_text("forbidden")


@pytest.mark.reg11a_probe
def test_reg11a_write_to_config_is_blocked(tmp_path):
    """REG-11a probe: writes into config/ must be blocked by audit hook."""
    from pathlib import Path

    with pytest.raises(PermissionError, match="REG-11: test writes"):
        (Path("config") / "test.yaml").write_text("forbidden")


@pytest.mark.reg11a_probe
def test_reg11a_tmp_path_is_allowed(tmp_path):
    """REG-11a probe: tmp_path must still work."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("allowed")
    assert test_file.read_text() == "allowed"


def test_reg11b_git_status_clean_after_suite():
    """
    REG-11b: git status --porcelain --ignored data config is empty after full suite.
    
    Run at end of session to verify no test left data/ or config/ files behind.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", "--ignored", "data", "config"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout.strip()
    if output:
        pytest.fail(
            f"REG-11b: Tests left files in data/ or config/:\n{output}\n"
            "Run 'git status data config' to inspect."
        )

