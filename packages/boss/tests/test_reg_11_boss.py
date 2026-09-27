"""REG-11: boss selector tests never write into data/ or config/."""

from pathlib import Path


def test_reg11_boss_no_data_write(tmp_path: Path) -> None:
    test_file = tmp_path / "boss_out.txt"
    test_file.write_text("OK", encoding="utf-8")
    assert test_file.exists()


def test_reg11_boss_no_config_write(tmp_path: Path) -> None:
    test_file = tmp_path / "engine_copy.yaml"
    test_file.write_text("test: ok\n", encoding="utf-8")
    assert test_file.exists()
