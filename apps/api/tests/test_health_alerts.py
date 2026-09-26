import json

from fastapi.testclient import TestClient

from api import health_alerts
from api.main import create_app


def test_health_routes_read_monitor_files(tmp_path, monkeypatch):
    monkeypatch.setattr(health_alerts, "HEALTH_DIR", tmp_path)
    client = TestClient(create_app())

    assert client.get("/health/status").json()["ok"] is None
    assert client.get("/health/alerts").json() == {"alerts": [], "count": 0}

    (tmp_path / "status.json").write_text(json.dumps({"ok": False, "checks": {"recorder": {"ok": False}}}))
    rows = [{"event": "ALERT", "check": "recorder"}, {"event": "RECOVERED", "check": "recorder"}]
    (tmp_path / "alerts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows) + "not json\n")

    assert client.get("/health/status").json()["checks"]["recorder"]["ok"] is False
    body = client.get("/health/alerts", params={"limit": 2}).json()
    assert body["count"] == 1 and body["alerts"][0]["event"] == "RECOVERED"  # newest first, bad line skipped
    assert client.get("/health/alerts", params={"limit": 0}).status_code == 422
    assert client.post("/health/alerts").status_code == 405  # read-only
    assert client.get("/health").json()["ok"] is True  # existing route unchanged
