"""Health monitor: stale data, paper-engine liveness, reconciliation mismatches, critical risk
vetoes, disk space.

Writes data/health/alerts.jsonl (append-only) and data/health/status.json (latest snapshot,
served by apps/api at /health/status and /health/alerts). Optional Telegram push when both
TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set. Read-only towards everything it watches.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import time as _time
import urllib.parse
import urllib.request
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

log = logging.getLogger("health")

IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN, MARKET_CLOSE = time(9, 15), time(15, 30)
STALE_SECONDS = 300
# The live paper cycle re-replays the whole day (O(n^2) late in the session); 30 s would page on a
# healthy engine. A recorded engine error is CRITICAL immediately, whatever its age.
ENGINE_STALE_SECONDS = 120
RECORDER_HEARTBEAT = "recorder_heartbeat.jsonl"  # data-recorder (PR-001), one line per minute
PAPER_DASHBOARD = "ml_paper_dashboard.json"  # desk_ml paper-scalp board (UI; beats refresh it)
ENGINE_HEARTBEAT = "engine_heartbeat.json"  # desk_ml.live_cycle: written only by a finished cycle
EVENT_CHECKS = {"risk_vetoes"}  # alert per new event; no "recovered" message


def in_market_hours(now: datetime) -> bool:
    now = now.astimezone(IST)
    return now.weekday() < 5 and MARKET_OPEN <= now.time() <= MARKET_CLOSE


def parse_ts(value: Any) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.astimezone()  # naive = this machine's local time (recorder uses datetime.now())


def _last_line(path: Path) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            f.seek(max(0, f.seek(0, os.SEEK_END) - 4096))
            lines = [ln for ln in f.read().decode("utf-8", "replace").splitlines() if ln.strip()]
    except OSError:
        return None
    return lines[-1] if lines else None


def _result(check: str, ok: bool, message: str, severity: str = "CRITICAL", last_seen: Optional[datetime] = None) -> dict[str, Any]:
    return {
        "check": check, "ok": ok, "severity": "OK" if ok else severity, "message": message,
        "last_seen": last_seen.isoformat(timespec="seconds") if last_seen else None,
    }


def _freshness(check: str, last_seen: Optional[datetime], now: datetime, problem: Optional[str] = None) -> dict[str, Any]:
    market = in_market_hours(now)
    closed = "" if market else " (market closed)"
    if last_seen is None:
        return _result(check, not market, f"no heartbeat found{closed}")
    age = (now - last_seen).total_seconds()
    if problem:
        return _result(check, not market, f"{problem}{closed}", last_seen=last_seen)
    if market and age > STALE_SECONDS:
        return _result(check, False, f"stale: last update {age / 60:.1f} min ago (limit 5 min in market hours)", last_seen=last_seen)
    return _result(check, True, f"last update {age:.0f}s ago{closed}", last_seen=last_seen)


def check_recorder(recon_dir: Path, now: datetime) -> dict[str, Any]:
    line = _last_line(recon_dir / RECORDER_HEARTBEAT)
    try:
        beat = json.loads(line) if line else {}
    except ValueError:
        beat = {}
    problem = "recorder reports DATA_STALE (repeated fetch errors)" if beat.get("status") == "DATA_STALE" else None
    return _freshness("recorder", parse_ts(beat.get("timestamp")), now, problem)


def check_paper_engine(recon_dir: Path, now: datetime) -> dict[str, Any]:
    """Alive = the last *successful* cycle is fresh and the engine is not failing.

    Reads ``engine_heartbeat.json`` (only a finished cycle writes last_ok). The dashboard's own
    timestamps are refreshed by UI beats between cycles, so they cannot prove the engine works;
    they are used only when no engine heartbeat exists (older loops).
    """
    try:
        hb = json.loads((recon_dir / ENGINE_HEARTBEAT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        hb = None
    if isinstance(hb, dict):
        market = in_market_hours(now)
        closed = "" if market else " (market closed)"
        last_ok = parse_ts(hb.get("last_ok_ist"))
        fails = int(hb.get("consecutive_failures") or 0)
        if fails:
            return _result("paper_engine", not market,
                           f"engine failing: {fails} cycle(s) in a row, last error {hb.get('last_error')}{closed}",
                           last_seen=last_ok)
        if last_ok is None:
            return _result("paper_engine", not market, f"engine has never completed a cycle{closed}")
        age = (now - last_ok).total_seconds()
        if market and age > ENGINE_STALE_SECONDS:
            return _result("paper_engine", False,
                           f"dead or hung: last good cycle {age:.0f}s ago (limit {ENGINE_STALE_SECONDS}s in market hours)",
                           last_seen=last_ok)
        return _result("paper_engine", True, f"last good cycle {age:.0f}s ago{closed}", last_seen=last_ok)
    try:
        board = json.loads((recon_dir / PAPER_DASHBOARD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        board = {}
    beat = board.get("heartbeat") or {}
    if beat.get("engine_error") or beat.get("alive") is False:
        return _result("paper_engine", not in_market_hours(now), f"engine reports failure: {beat.get('engine_error')}")
    return _freshness("paper_engine", parse_ts(beat.get("engine_last_ok_ist") or beat.get("as_of_ist") or board.get("as_of_ist")), now)


def _query(ledger_path: Path, sql: str, args: tuple = ()) -> Optional[list[tuple]]:
    if not ledger_path.exists():
        return None
    conn = sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def check_reconciliation(ledger_path: Path) -> dict[str, Any]:
    rows = _query(ledger_path, "SELECT ts, ok, mismatches_json FROM recon_runs ORDER BY id DESC LIMIT 1")
    if not rows:
        return _result("reconciliation", True, "no reconciliation runs yet")
    ts, ok, mismatches = rows[0]
    if ok:
        return _result("reconciliation", True, f"last run clean at {ts}")
    return _result("reconciliation", False, f"broker vs internal book mismatch at {ts}: {mismatches[:300]}")


def latest_entry_veto(ledger_path: Path, day: str) -> Optional[dict[str, Any]]:
    """Most recent rejected entry today, including the ticket's rupee risk.

    ``MAX_LOSS_PER_TRADE`` is not critical, so the alarm check above does not show it.
    The founder still needs the reason and the ticket risk on ``GET /health/status``.
    """
    rows = _query(
        ledger_path,
        "SELECT ts, reason_code, reason, intent_json FROM risk_decisions "
        "WHERE approved = 0 AND action = 'ENTRY' AND day = ? ORDER BY id DESC LIMIT 1",
        (day,),
    )
    if not rows:
        return None
    ts, code, reason, raw_intent = rows[0]
    ticket_risk = None
    if raw_intent:
        try:
            intent = json.loads(raw_intent)
        except ValueError:
            intent = None
        if isinstance(intent, dict):
            try:
                ticket_risk = float(intent["ticket_risk_inr"]) if intent.get("ticket_risk_inr") is not None else None
            except (TypeError, ValueError, KeyError):
                ticket_risk = None
    return {
        "ts": ts,
        "reason_code": code,
        "reason_text": reason,
        "ticket_risk_inr": ticket_risk,
    }


def check_risk_vetoes(ledger_path: Path, now: datetime, since_id: int) -> tuple[dict[str, Any], int]:
    rows = _query(
        ledger_path,
        "SELECT id, ts, reason_code, reason FROM risk_decisions WHERE critical = 1 AND id > ? AND day = ? ORDER BY id",
        (since_id, now.astimezone(IST).date().isoformat()),
    )
    if not rows:
        return _result("risk_vetoes", True, "no new critical risk vetoes"), since_id
    last_id, ts, code, reason = rows[-1]
    return _result("risk_vetoes", False, f"{len(rows)} critical veto(es); last {code} at {ts}: {reason}"), last_id


def check_disk(path: Path, min_free_gb: float) -> dict[str, Any]:
    while not path.exists() and path != path.parent:
        path = path.parent
    free_gb = shutil.disk_usage(path).free / 1e9
    if free_gb < min_free_gb:
        return _result("disk", False, f"only {free_gb:.1f} GB free (min {min_free_gb} GB)", severity="WARN")
    return _result("disk", True, f"{free_gb:.1f} GB free")


def send_telegram(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=10)
        return True
    except Exception as exc:  # never log the URL: it contains the token
        log.warning("telegram push failed (%s)", type(exc).__name__)
        return False


class HealthMonitor:
    def __init__(
        self,
        recon_dir: Path = Path("data/recon"),
        ledger_path: Path = Path("data/ledger/ledger.sqlite"),
        health_dir: Path = Path("data/health"),
        *,
        min_free_gb: float = 2.0,
        realert_minutes: float = 15,
    ) -> None:
        self.recon_dir, self.ledger_path, self.health_dir = Path(recon_dir), Path(ledger_path), Path(health_dir)
        self.min_free_gb = min_free_gb
        self.realert = timedelta(minutes=realert_minutes)
        self.alerts_path = self.health_dir / "alerts.jsonl"
        self.status_path = self.health_dir / "status.json"

    def _checked(self, name: str, fn: Callable[..., dict[str, Any]], *args: Any) -> dict[str, Any]:
        try:
            return fn(*args)
        except Exception as exc:
            return _result(name, False, f"check crashed: {type(exc).__name__}: {exc}", severity="WARN")

    def run_once(self, now: Optional[datetime] = None) -> dict[str, Any]:
        now = (now or datetime.now(IST)).astimezone(IST)
        try:
            prev = json.loads(self.status_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev = {}
        last_veto_id = int(prev.get("last_veto_id") or 0)
        try:
            vetoes, last_veto_id = check_risk_vetoes(self.ledger_path, now, last_veto_id)
        except Exception as exc:
            vetoes = _result("risk_vetoes", False, f"check crashed: {type(exc).__name__}: {exc}", severity="WARN")
        results = [
            self._checked("recorder", check_recorder, self.recon_dir, now),
            self._checked("paper_engine", check_paper_engine, self.recon_dir, now),
            self._checked("reconciliation", check_reconciliation, self.ledger_path),
            vetoes,
            self._checked("disk", check_disk, self.recon_dir.parent, self.min_free_gb),
        ]
        self.health_dir.mkdir(parents=True, exist_ok=True)
        checks = {}
        for r in results:
            name, before = r["check"], (prev.get("checks") or {}).get(r["check"], {})
            last_alert = parse_ts(before.get("last_alert_at"))
            if not r["ok"]:
                if name in EVENT_CHECKS or before.get("ok", True) or not last_alert or now - last_alert >= self.realert:
                    self._alert(now, "ALERT", r)
                    last_alert = now
            elif before and not before.get("ok", True) and name not in EVENT_CHECKS:
                self._alert(now, "RECOVERED", r)
            checks[name] = {**r, "last_alert_at": last_alert.isoformat(timespec="seconds") if last_alert else None}
        status = {
            "as_of": now.isoformat(timespec="seconds"),
            "market_hours": in_market_hours(now),
            "ok": all(r["ok"] for r in results),
            "checks": checks,
            "last_veto_id": last_veto_id,
            "latest_entry_veto": latest_entry_veto(self.ledger_path, now.astimezone(IST).date().isoformat()),
        }
        tmp = self.status_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.status_path)
        return status

    def _alert(self, now: datetime, event: str, r: dict[str, Any]) -> None:
        rec = {"ts": now.isoformat(timespec="seconds"), "event": event, "check": r["check"],
               "severity": r["severity"], "message": r["message"]}
        try:
            with open(self.alerts_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError as exc:  # a full disk must not stop the monitor from reporting
            log.error("alerts.jsonl unwritable (%s): %s", exc, json.dumps(rec))
        log.log(logging.INFO if event == "RECOVERED" else logging.ERROR, "%s %s: %s", event, r["check"], r["message"])
        send_telegram(f"all_about_dhan {event} {r['check']} ({r['severity']}): {r['message']}")

    def run_forever(self, interval_seconds: float = 60) -> None:
        while True:
            try:
                self.run_once()
            except Exception:
                log.exception("health run failed")
            _time.sleep(interval_seconds)
