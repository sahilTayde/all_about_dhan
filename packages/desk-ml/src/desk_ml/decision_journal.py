"""Append-only paper decision journal. One JSONL row per stage per candidate.

Paper / dual-tape only. Never invents a print. MIX-* is stripped from actor text.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from desk_ml.reliability import append_line, read_jsonl

IST = timezone(timedelta(hours=5, minutes=30))
JOURNAL_REL = Path("data") / "recon" / "decision_journal"

STAGES = ("analyst", "desk", "overlay", "boss", "imm", "in_trade", "exit")
DECISIONS = ("pass", "skip", "fill", "exit")

ACTOR_PLAIN = {
    "MIX-DEFAULT-BUY": "Desk default",
    "MIX-FORM-FOLLOWS": "Form-follows",
    "MIX-ML-LOGIT": "Logit",
    "MIX-ML-LOGIT-XR": "Logit + XR",
    "MIX-ML-GREEKS": "Greeks",
    "MIX-TV-EP-024": "TV-EP lab",
    "MIX-SYNTH-A": "Synth A",
    "MIX-SYNTH-B": "Synth B",
    "R01_PDIV_5_ALL_H20": "Premium divergence",
    "R01_B3A_VOL": "Premium divergence · high vol",
    "B8B_B3A_EX_CHOPPY": "High-vol skip-chop",
    "R07_MOM3_TREND": "Momentum",
    "B8A_R07_NO_PRE1030": "Momentum after 10:30",
    "follows": "Form-follows",
    "logit": "Logit",
    "xr": "Logit + XR",
    "greeks": "Greeks",
    "picker": "Boss picker",
    "observer": "Observer",
    "overlay": "Overlay",
    "desk": "Desk",
    "imm": "Paper fill",
}

REASON_PLAIN = {
    "HOLD_MAJORITY": "Picker hold — no desk ticket",
    "FOLLOW_GAP": "Observer veto: wing did not confirm",
    "OBSERVER_VETO_WING_DEAD": "Observer veto: wing did not confirm",
    "SOD_ONE_OPEN": "One ticket already open on this index",
    "NO_NEW_AFTER_1516": "Too late in the session",
    "NO_NEW_AFTER_1515": "Too late in the session",
    "PATH_KIND_HOLD": "Skipped: coil market",
    "SIDEWAYS_HOLD": "Skipped: coil market",
    "OVERLAY_COIL": "Skipped: coil market",
    "CANCEL_AGAINST": "Thesis broke",
    "CANCEL_NO_PROGRESS": "Exited: no progress",
    "COVER_LONG_UNWIND": "Long unwind",
    "TARGET": "Target hit",
    "STOP": "Stop hit",
    "TIME": "Time exit",
    "DEALER_HOLD": "Analyst hold",
    "NO_SIDE": "No CE/PE this bar",
}


def _ist(ts: Any) -> Optional[str]:
    if ts is None or ts == "":
        return None
    if isinstance(ts, str) and "T" in ts:
        return ts
    try:
        return datetime.fromtimestamp(int(ts), tz=IST).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return None


def _day(ts_ist: Optional[str], ts: Any = None) -> Optional[str]:
    stamp = ts_ist or _ist(ts)
    return stamp[:10] if stamp else None


def plain_actor(raw: Any) -> str:
    if raw is None or raw == "":
        return "Desk"
    s = str(raw).strip()
    if s in ACTOR_PLAIN:
        return ACTOR_PLAIN[s]
    u = s.upper()
    if u in ACTOR_PLAIN:
        return ACTOR_PLAIN[u]
    if u.startswith("MIX-"):
        return s.replace("MIX-", "").replace("-", " ").strip() or "Desk"
    return s


def plain_reason(raw: Any, fallback: str = "Recorded") -> str:
    if raw is None or raw == "":
        return fallback
    s = str(raw).strip()
    if s in REASON_PLAIN:
        return REASON_PLAIN[s]
    u = s.upper()
    if u in REASON_PLAIN:
        return REASON_PLAIN[u]
    if u.startswith("MIX-") or "MIX-" in u:
        s = re.sub(r"MIX-[A-Z0-9_-]+", "", s).strip(" :,-")
    return s or fallback


def journal_path(root: Path, day: str) -> Path:
    return Path(root) / JOURNAL_REL / f"{day}.jsonl"


def candidate_id(*, underlying: str, side: Any, ts: Any, trade_id: Any = None) -> str:
    if trade_id:
        return str(trade_id)
    stamp = _ist(ts) or "unknown"
    return f"{str(underlying).upper()}:{side or 'HOLD'}:{stamp[:16]}"


def make_row(
    *,
    ts: Any,
    underlying: str,
    candidate_id: str,
    stage: str,
    actor: str,
    decision: str,
    reason: str,
    inputs: Optional[Mapping[str, Any]] = None,
    trade_id: Any = None,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage}")
    if decision not in DECISIONS:
        raise ValueError(f"unknown decision {decision}")
    ts_ist = _ist(ts)
    row = {
        "ts": int(ts) if str(ts).isdigit() or isinstance(ts, int) else None,
        "ts_ist": ts_ist,
        "underlying": str(underlying or "").upper(),
        "candidate_id": str(candidate_id),
        "stage": stage,
        "actor": plain_actor(actor),
        "decision": decision,
        "reason": plain_reason(reason),
        "inputs": _clean_inputs(inputs or {}),
        "orders": "REFUSED",
        "promote": False,
    }
    if trade_id:
        row["trade_id"] = str(trade_id)
    if "MIX-" in json.dumps(row):
        row["actor"] = plain_actor(row["actor"])
        row["reason"] = plain_reason(row["reason"])
        row["inputs"] = _clean_inputs(row["inputs"])
    return row


def _clean_inputs(fields: Mapping[str, Any]) -> dict[str, Any]:
    keep = ("day_type", "phase", "vix", "premium", "sl", "target", "side")
    out: dict[str, Any] = {}
    for key in keep:
        val = fields.get(key)
        if val is None or val == "":
            continue
        if isinstance(val, str) and val.upper().startswith("MIX-"):
            continue
        out[key] = val
    return out


class DecisionJournal:
    """Append-only JSONL. One row per (candidate_id, stage). Never deletes."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self._seen: set[tuple[str, str]] = set()

    def path_for(self, ts: Any, ts_ist: Optional[str] = None) -> Optional[Path]:
        day = _day(ts_ist, ts)
        return journal_path(self.root, day) if day else None

    def _load_seen(self, path: Path) -> None:
        rows = read_jsonl(path) or []
        for row in rows:
            cid = str(row.get("candidate_id") or "")
            stage = str(row.get("stage") or "")
            if cid and stage:
                self._seen.add((cid, stage))

    def append(self, row: Mapping[str, Any]) -> bool:
        cid = str(row.get("candidate_id") or "")
        stage = str(row.get("stage") or "")
        if not cid or stage not in STAGES:
            return False
        key = (cid, stage)
        path = self.path_for(row.get("ts"), row.get("ts_ist"))
        if path is None:
            return False
        if key not in self._seen and path.is_file():
            self._load_seen(path)
        if key in self._seen:
            return False
        append_line(path, json.dumps(row, default=str))
        self._seen.add(key)
        return True

    def append_many(self, rows: Iterable[Mapping[str, Any]]) -> int:
        return sum(1 for row in rows if self.append(row))


def load_rows(
    root: Path,
    *,
    day: Optional[str] = None,
    candidate_id: Optional[str] = None,
    underlying: Optional[str] = None,
    limit: int = 240,
) -> list[dict[str, Any]]:
    folder = Path(root) / JOURNAL_REL
    if day:
        paths = [journal_path(root, day)]
    else:
        paths = sorted(folder.glob("*.jsonl"))[-3:] if folder.is_dir() else []
    out: list[dict[str, Any]] = []
    for path in paths:
        for row in read_jsonl(path) or []:
            if candidate_id and str(row.get("candidate_id")) != str(candidate_id) and str(row.get("trade_id") or "") != str(candidate_id):
                continue
            if underlying and str(row.get("underlying") or "").upper() != str(underlying).upper():
                continue
            out.append(row)
    return out[-limit:]


def _spoken(vote: Any) -> bool:
    if isinstance(vote, Mapping):
        if vote.get("spoken") is False:
            return False
        return bool(vote.get("side") or vote.get("spoken"))
    return bool(getattr(vote, "side", None))


def _vote_source(vote: Any) -> str:
    if isinstance(vote, Mapping):
        return str(vote.get("source") or "Analyst")
    return str(getattr(vote, "source", None) or "Analyst")


def _vote_side(vote: Any) -> Optional[str]:
    if isinstance(vote, Mapping):
        side = vote.get("side")
    else:
        side = getattr(vote, "side", None)
    return str(side) if side else None


def _pos_attr(pos: Any, name: str) -> Any:
    if pos is None:
        return None
    if isinstance(pos, Mapping):
        return pos.get(name)
    return getattr(pos, name, None)


def _inputs(step: Mapping[str, Any], pos: Any = None) -> dict[str, Any]:
    classified = step.get("index_regime") or {}
    if not isinstance(classified, Mapping):
        classified = {}
    ts_ist = _ist(step.get("ts"))
    phase = None
    if ts_ist and "T" in ts_ist:
        hhmm = ts_ist[11:16]
        phase = "open" if hhmm < "10:30" else ("close" if hhmm >= "14:30" else "mid")
    return {
        "day_type": classified.get("regime") or classified.get("session_kind") or step.get("market_kind"),
        "phase": phase,
        "vix": classified.get("vix") or classified.get("iv") or classified.get("india_vix"),
        "premium": _pos_attr(pos, "entry") or _pos_attr(pos, "last_ltp"),
        "sl": _pos_attr(pos, "stop"),
        "target": _pos_attr(pos, "target"),
        "side": _pos_attr(pos, "side") or (step.get("picker") or {}).get("side"),
    }


def _overlay_skip(step: Mapping[str, Any], skip: Optional[Mapping[str, Any]]) -> Optional[str]:
    reason = str((skip or {}).get("reason") or "")
    if reason and _stage_for_reason(reason) == "overlay":
        return reason
    if step.get("overlay_follow_gap") or (isinstance(step.get("follow_gap"), bool) and step.get("follow_gap")):
        return "FOLLOW_GAP"
    classified = step.get("index_regime") or {}
    if isinstance(classified, Mapping) and str(classified.get("regime") or "").upper() in {"CHOP", "CHOPPY", "SIDEWAYS"}:
        if not (step.get("desk") or {}).get("opened_this_tick"):
            return "PATH_KIND_HOLD"
    return None


def _stage_for_reason(reason: str) -> str:
    r = str(reason or "").upper()
    if any(k in r for k in ("COIL", "CHOP", "SIDEWAYS", "REGIME", "PATH_KIND", "NO_NEW", "OVERLAY", "VOL_")):
        return "overlay"
    if any(k in r for k in ("HOLD", "VETO", "FOLLOW_GAP", "PICKER", "OBSERVER")):
        return "boss"
    if any(k in r for k in ("SOD_ONE", "SOD_LAB", "CAPITAL", "DESK")):
        return "desk"
    if any(k in r for k in ("DEALER", "NO_SIDE", "ANALYST")):
        return "analyst"
    return "overlay"


def rows_from_step(
    step: Mapping[str, Any],
    *,
    opens: Any = None,
    skips: Optional[Iterable[Mapping[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Emit journal rows from one paper-loop last_step. Missing stages stay unwritten (UI: waiting)."""
    und = str(step.get("underlying") or "").upper()
    ts = step.get("ts")
    if not und or ts is None:
        return []
    picker = step.get("picker") if isinstance(step.get("picker"), Mapping) else {}
    observer = step.get("observer") if isinstance(step.get("observer"), Mapping) else {}
    desk = step.get("desk") if isinstance(step.get("desk"), Mapping) else {}
    votes = [v for v in (step.get("analyst_votes") or []) if isinstance(v, (Mapping, object))]
    spoken = [v for v in votes if _spoken(v)]
    opened = bool(desk.get("opened_this_tick"))
    pos = None
    trade_id = None
    items = opens.items() if isinstance(opens, Mapping) else []
    for (_book, u), p in items:
        if str(u).upper() == und:
            pos = p
            trade_id = _pos_attr(p, "trade_id")
            break
    skip = None
    for row in reversed(list(skips or [])):
        if str(row.get("underlying") or "").upper() == und and (not row.get("ts") or int(row.get("ts") or 0) == int(ts)):
            skip = row
            break
    side = picker.get("side") or _vote_side(spoken[0]) if spoken else None
    if pos is not None:
        side = _pos_attr(pos, "side") or side
    cid = candidate_id(underlying=und, side=side, ts=ts, trade_id=trade_id)
    inputs = _inputs(step, pos)
    if side:
        inputs["side"] = side
    rows: list[dict[str, Any]] = []

    def add(stage: str, decision: str, actor: str, reason: str) -> None:
        rows.append(
            make_row(
                ts=ts,
                underlying=und,
                candidate_id=cid,
                stage=stage,
                actor=actor,
                decision=decision,
                reason=reason,
                inputs=inputs,
                trade_id=trade_id,
            )
        )

    interesting = opened or bool(spoken) or bool(skip) or picker.get("action") in {"TICKET", "HOLD"}
    if not interesting:
        return []

    if spoken:
        add("analyst", "pass", _vote_source(spoken[0]), f"{plain_actor(_vote_source(spoken[0]))} spoke")
    elif skip and _stage_for_reason(str(skip.get("reason") or "")) == "analyst":
        add("analyst", "skip", "Analyst", str(skip.get("reason") or "NO_SIDE"))

    overlay_reason = _overlay_skip(step, skip)
    picker_action = str(picker.get("action") or "")
    observer_action = str(observer.get("action") or "")

    if opened or picker_action == "TICKET":
        add("desk", "pass", "Desk", f"{side or ''} ticket".strip())
    elif skip and _stage_for_reason(str(skip.get("reason") or "")) == "desk":
        add("desk", "skip", "Desk", str(skip.get("reason")))

    if overlay_reason and not opened:
        add("overlay", "skip", "Overlay", overlay_reason)
    elif opened or picker_action == "TICKET":
        add("overlay", "pass", "Overlay", inputs.get("day_type") or "Filters passed")

    if opened or (picker_action == "TICKET" and observer_action in {"ALLOW", ""}):
        add("boss", "pass", "Boss picker", f"Buy {side}" if side else "Ticket")
    elif picker_action == "HOLD" and spoken:
        add("boss", "skip", "Boss picker", "HOLD_MAJORITY")
    elif observer_action in {"VETO"}:
        add("boss", "skip", "Observer", str(observer.get("reason") or "FOLLOW_GAP"))
    elif skip and _stage_for_reason(str(skip.get("reason") or "")) == "boss":
        add("boss", "skip", "Boss picker", str(skip.get("reason")))

    if opened:
        add("imm", "fill", "Paper fill", "Paper fill")
        add("in_trade", "pass", "Desk", "Trade in progress")
    return rows


def row_from_close(closed: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    tid = closed.get("trade_id")
    und = closed.get("underlying")
    ts = closed.get("closed_ts") or closed.get("last_updated_ts") or closed.get("ts")
    if not tid or not und or ts is None:
        return None
    return make_row(
        ts=ts,
        underlying=str(und),
        candidate_id=str(tid),
        stage="exit",
        actor="Desk",
        decision="exit",
        reason=str(closed.get("exit_reason") or "Closed"),
        inputs={
            "premium": closed.get("exit") or closed.get("entry"),
            "sl": closed.get("stop"),
            "target": closed.get("target"),
            "side": closed.get("side"),
            "day_type": closed.get("index_regime") or closed.get("market_kind_close"),
        },
        trade_id=tid,
    )


def journal_enabled(engine: Any) -> bool:
    """Hooks write only when the replay ctx asked for writes. Missing ctx = silent."""
    ctx = getattr(engine, "ctx", None)
    if ctx is None:
        return False
    return bool(getattr(ctx, "write", False))


def record_engine_step(engine: Any) -> list[dict[str, Any]]:
    root = getattr(engine, "root", None)
    step = getattr(engine, "last_step", None) or {}
    if root is None or not step:
        return []
    rows = rows_from_step(step, opens=getattr(engine, "opens", None), skips=getattr(engine, "skips", None))
    DecisionJournal(Path(root)).append_many(rows)
    return rows


def record_close(engine: Any, closed: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    root = getattr(engine, "root", None)
    row = row_from_close(closed)
    if root is None or row is None:
        return row
    DecisionJournal(Path(root)).append(row)
    return row


_HOOK_ORIG: dict[str, Any] = {"close": None, "step": None}


def install_engine_hooks() -> bool:
    """Wrap paper_scalp close/step without editing the frozen file. Idempotent."""
    from desk_ml import paper_scalp as ps

    if getattr(ps._close, "_decision_journal", False):
        return False

    orig_close = ps._close
    orig_step = ps.step_decide
    _HOOK_ORIG["close"] = orig_close
    _HOOK_ORIG["step"] = orig_step

    def _close(engine: Any, pos: Any, *args: Any, **kwargs: Any) -> Any:
        out = orig_close(engine, pos, *args, **kwargs)
        if journal_enabled(engine) and getattr(engine, "closed", None):
            try:
                record_close(engine, engine.closed[-1])
            except Exception:
                pass
        return out

    def step_decide(engine: Any, s: Any, votes: Any, *args: Any, **kwargs: Any) -> Any:
        out = orig_step(engine, s, votes, *args, **kwargs)
        if journal_enabled(engine):
            try:
                record_engine_step(engine)
            except Exception:
                pass
        return out

    _close._decision_journal = True  # type: ignore[attr-defined]
    step_decide._decision_journal = True  # type: ignore[attr-defined]
    ps._close = _close
    ps.step_decide = step_decide
    return True


def uninstall_engine_hooks() -> bool:
    """Restore paper_scalp close/step. For tests that must not leak wraps."""
    from desk_ml import paper_scalp as ps

    orig_close = _HOOK_ORIG["close"]
    orig_step = _HOOK_ORIG["step"]
    if orig_close is None or orig_step is None:
        return False
    ps._close = orig_close
    ps.step_decide = orig_step
    _HOOK_ORIG["close"] = None
    _HOOK_ORIG["step"] = None
    return True
