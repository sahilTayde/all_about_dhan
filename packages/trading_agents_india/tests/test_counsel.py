"""Counsel settings — no live keys required."""

from trading_agents_india.counsel import ROLES, _together, counsel_settings


def test_roles_are_desk_jobs() -> None:
    assert "review" in ROLES
    assert "validate" in ROLES


def test_counsel_settings_never_includes_key_material() -> None:
    cfg = counsel_settings()
    blob = str(cfg)
    assert "sk-" not in blob
    assert "AQ." not in blob
    assert cfg["gemini_model"]
    assert cfg["openai_model"]


def test_together_aligned_and_split() -> None:
    assert _together(True, True, "AGREE\nwhy", "AGREE with tape") == "ALIGNED"
    assert _together(True, True, "AGREE\n", "DISAGREE\n") == "SPLIT"
    assert _together(True, False, "AGREE", "") == "ONE_ONLY"
