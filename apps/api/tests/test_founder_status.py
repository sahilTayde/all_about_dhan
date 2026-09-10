from api.founder_status import _scrub, build_founder_status


def test_scrub_drops_token_keys() -> None:
    out = _scrub({"access_token": "SECRET", "ok": True, "nested": {"dhan_access_token": "x"}})
    assert "access_token" not in out
    assert out["ok"] is True
    assert "dhan_access_token" not in out["nested"]


def test_build_founder_status_has_no_secret_strings() -> None:
    blob = build_founder_status()
    text = str(blob).lower()
    assert "eyj" not in text
    assert blob["orders"] == "REFUSED"
    assert blob["promote"] is False
    assert "agents" in blob
    assert "services" in blob
