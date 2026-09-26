"""Health monitor: stale-data alarm in market hours, liveness, recon, vetoes, disk, Telegram."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from health import HealthMonitor, in_market_hours
from health import monitor as mon
from ledger import Ledger, load_rates

REPO = Path(__file__).resolve().parents[3]
MON_1030 = datetime.fromisoformat("2026-09-28T10:30:00+05:30")  # Monday, market open


@pytest.fixture(autouse=True)
def no_telegram(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)


def setup(tmp_path, *, recorder_age=None, paper_age=60, status="running", now=MON_1030):
    recon = tmp_path / "data" / "recon"
    recon.mkdir(parents=True)
    if recorder_age is not None:
        # recorder writes naive local time: datetime.now().isoformat()
        naive_local = (now - timedelta(seconds=recorder_age)).astimezone().replace(tzinfo=None)
        lines = [{"timestamp": (naive_local - timedelta(minutes=1)).isoformat(), "status": "running"},
                 {"timestamp": naive_local.isoformat(), "status": status, "dry_run": False, "error_count": 0}]
        (recon / "recorder_heartbeat.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    if paper_age is not None:
        stamp = (now - timedelta(seconds=paper_age)).isoformat(timespec="seconds")
        (recon / "ml_paper_dashboard.json").write_text(json.dumps({"as_of_ist": stamp, "heartbeat": {"as_of_ist": stamp, "alive": True}}))
    return HealthMonitor(recon, tmp_path / "data" / "ledger" / "ledger.sqlite", tmp_path / "data" / "health", min_free_gb=0)


def alerts(m):
    return [json.loads(x) for x in m.alerts_path.read_text().splitlines()] if m.alerts_path.exists() else []


def test_market_hours():
    assert in_market_hours(MON_1030)
    assert not in_market_hours(datetime.fromisoformat("2026-09-28T09:14:00+05:30"))
    assert not in_market_hours(datetime.fromisoformat("2026-09-28T15:31:00+05:30"))
    assert not in_market_hours(datetime.fromisoformat("2026-09-26T10:30:00+05:30"))  # Saturday


def test_stale_recorder_in_market_hours_raises_alarm(tmp_path):
    m = setup(tmp_path, recorder_age=6 * 60)
    status = m.run_once(MON_1030)
    rec = status["checks"]["recorder"]
    assert status["ok"] is False and rec["ok"] is False and rec["severity"] == "CRITICAL"
    assert "stale" in rec["message"] and "6.0 min" in rec["message"]
    (a,) = alerts(m)
    assert (a["event"], a["check"]) == ("ALERT", "recorder")
    assert json.loads(m.status_path.read_text())["checks"]["recorder"]["ok"] is False


def test_fresh_recorder_is_ok(tmp_path):
    m = setup(tmp_path, recorder_age=120)
    status = m.run_once(MON_1030)
    assert status["ok"] is True and alerts(m) == []


def test_stale_data_outside_market_hours_is_not_an_alarm(tmp_path):
    saturday = datetime.fromisoformat("2026-09-26T10:30:00+05:30")
    m = setup(tmp_path, recorder_age=3 * 3600, paper_age=3 * 3600, now=saturday)
    assert m.run_once(saturday)["ok"] is True
    evening = datetime.fromisoformat("2026-09-28T18:00:00+05:30")
    assert m.run_once(evening)["ok"] is True and alerts(m) == []


def test_missing_heartbeat_and_data_stale_status(tmp_path):
    m = setup(tmp_path, recorder_age=None)
    assert "no heartbeat" in m.run_once(MON_1030)["checks"]["recorder"]["message"]
    m2 = setup(tmp_path / "b", recorder_age=30, status="DATA_STALE")
    assert "DATA_STALE" in m2.run_once(MON_1030)["checks"]["recorder"]["message"]


def test_paper_engine_liveness(tmp_path):
    m = setup(tmp_path, recorder_age=30, paper_age=10 * 60)
    pe = m.run_once(MON_1030)["checks"]["paper_engine"]
    assert pe["ok"] is False and "stale" in pe["message"]


def test_alert_dedupe_realert_and_recovery(tmp_path):
    m = setup(tmp_path, recorder_age=6 * 60)

    def recorder_events():
        return [a["event"] for a in alerts(m) if a["check"] == "recorder"]

    m.run_once(MON_1030)
    m.run_once(MON_1030 + timedelta(minutes=1))  # still stale, not re-alerted yet
    assert recorder_events() == ["ALERT"]
    m.run_once(MON_1030 + timedelta(minutes=16))
    assert recorder_events() == ["ALERT", "ALERT"]
    fresh = MON_1030 + timedelta(minutes=17)
    with open(m.recon_dir / "recorder_heartbeat.jsonl", "a") as f:
        f.write(json.dumps({"timestamp": fresh.astimezone().replace(tzinfo=None).isoformat(), "status": "running"}) + "\n")
    m.run_once(fresh)
    assert recorder_events() == ["ALERT", "ALERT", "RECOVERED"]


def test_recon_mismatch_and_critical_vetoes_from_ledger(tmp_path):
    m = setup(tmp_path, recorder_age=30)
    led = Ledger(m.ledger_path, rates=load_rates(REPO / "config" / "charges.yaml"))
    led.record_recon([{"kind": "ORPHAN_BROKER", "key": "43210"}], MON_1030)
    led.record_decision({"ts": MON_1030, "client_order_id": "a", "action": "ENTRY", "approved": False,
                         "reason_code": "MAX_DAILY_LOSS", "reason": "daily loss limit hit", "critical": True})
    led.record_decision({"ts": MON_1030, "client_order_id": "b", "action": "ENTRY", "approved": False,
                         "reason_code": "TIME_GATE", "reason": "late", "critical": False})
    s = m.run_once(MON_1030)
    assert s["checks"]["reconciliation"]["ok"] is False and "ORPHAN_BROKER" in s["checks"]["reconciliation"]["message"]
    assert s["checks"]["risk_vetoes"]["ok"] is False and "MAX_DAILY_LOSS" in s["checks"]["risk_vetoes"]["message"]
    assert m.run_once(MON_1030 + timedelta(seconds=60))["checks"]["risk_vetoes"]["ok"] is True  # same veto not repeated
    led.record_recon([], MON_1030 + timedelta(minutes=2))
    led.record_decision({"ts": MON_1030, "client_order_id": "c", "action": "ENTRY", "approved": False,
                         "reason_code": "KILL_SWITCH", "reason": "founder kill switch is on", "critical": True})
    s = m.run_once(MON_1030 + timedelta(minutes=2))
    assert s["checks"]["reconciliation"]["ok"] is True and "KILL_SWITCH" in s["checks"]["risk_vetoes"]["message"]
    got = [(a["event"], a["check"]) for a in alerts(m)]
    assert got == [("ALERT", "reconciliation"), ("ALERT", "risk_vetoes"), ("RECOVERED", "reconciliation"), ("ALERT", "risk_vetoes")]


def test_latest_entry_veto_shows_ticket_risk_without_failing_status(tmp_path):
    """MAX_LOSS_PER_TRADE is not critical. The reason and the rupee risk still show on status."""
    m = setup(tmp_path, recorder_age=30)
    led = Ledger(m.ledger_path, rates=load_rates(REPO / "config" / "charges.yaml"))
    led.record_decision({
        "ts": MON_1030, "client_order_id": "maxloss", "action": "ENTRY", "approved": False,
        "reason_code": "MAX_LOSS_PER_TRADE",
        "reason": "risk ₹14,000 exceeds max_loss_per_trade ₹5,000",
        "critical": False, "intent": {"ticket_risk_inr": 14000},
    })
    status = m.run_once(MON_1030)
    assert status["ok"] is True and status["checks"]["risk_vetoes"]["ok"] is True
    veto = status["latest_entry_veto"]
    assert veto["reason_code"] == "MAX_LOSS_PER_TRADE"
    assert veto["ticket_risk_inr"] == 14000
    assert "14,000" in veto["reason"]
    assert alerts(m) == []


def test_low_disk_alarm(tmp_path):
    m = setup(tmp_path, recorder_age=30)
    m.min_free_gb = 10**9
    assert m.run_once(MON_1030)["checks"]["disk"]["severity"] == "WARN"


def test_telegram_only_when_both_env_vars_set(tmp_path, monkeypatch, caplog):
    sent = []
    monkeypatch.setattr(mon.urllib.request, "urlopen", lambda url, data, timeout: sent.append((url, data)))
    setup(tmp_path, recorder_age=6 * 60).run_once(MON_1030)
    assert sent == []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:SECRET")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    setup(tmp_path / "b", recorder_age=6 * 60).run_once(MON_1030)
    assert len(sent) == 1 and sent[0][0] == "https://api.telegram.org/bot123:SECRET/sendMessage"
    assert b"chat_id=42" in sent[0][1] and b"recorder" in sent[0][1]
    monkeypatch.setattr(mon.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    assert mon.send_telegram("x") is False and "SECRET" not in caplog.text
