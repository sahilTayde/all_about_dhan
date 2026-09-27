"""One JSONL row per decision minute. Log only. Default on. Never places an order.

Rows go to ``data/shadow/<YYYY-MM-DD>.jsonl`` under the engine root. The directory
is created at runtime and gitignored. A failure here is logged and swallowed by
`safe_log_shadow` so the paper engine keeps its ticket.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from desk_ml.picker import decision_brief, shadow_picker_majority
from desk_ml.shadow_flow import STRIKE_STEP, near_money_totals, order_flow_score
from desk_ml.shadow_hari import hari_forecast
from desk_ml.shadow_volsize import volsize_row

log = logging.getLogger("desk_ml.shadow_log")
IST = timezone(timedelta(hours=5, minutes=30))
SCHEMA = "shadow-v1"


def shadow_logging_enabled(engine: Any = None) -> bool:
    """Default on. ``engine.shadow_log`` wins, then env ``SHADOW_LOG`` (0/off/false)."""
    if engine is not None and getattr(engine, "shadow_log", None) is not None:
        return bool(engine.shadow_log)
    raw = os.environ.get("SHADOW_LOG", "1").strip().lower()
    return raw not in {"0", "off", "false", "no"}


def _minute_key(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=IST).strftime("%Y-%m-%dT%H:%M")


def _day(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=IST).date().isoformat()


def _closes(bars: Optional[Sequence[Any]]) -> list[float]:
    out: list[float] = []
    for bar in bars or []:
        if isinstance(bar, dict):
            raw = bar.get("close")
        else:
            raw = getattr(bar, "close", None)
        try:
            if raw is not None:
                out.append(float(raw))
        except (TypeError, ValueError):
            continue
    return out


def _prior_closes(engine: Any, underlying: str) -> Optional[list[float]]:
    stored = getattr(engine, "shadow_prior_minute_closes", None)
    if not isinstance(stored, dict):
        return None
    rows = stored.get(underlying.upper())
    if not rows:
        return None
    return _closes(rows) if isinstance(rows[0], dict) else [float(x) for x in rows]


def _push_flow(engine: Any, underlying: str, snap: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    box = getattr(engine, "_shadow_flow_snaps", None)
    if not isinstance(box, dict):
        box = {}
        engine._shadow_flow_snaps = box  # type: ignore[attr-defined]
    hist = list(box.get(underlying) or [])
    if snap is not None:
        hist.append(snap)
    hist = hist[-5:]
    box[underlying] = hist
    return hist


def build_shadow_row(
    engine: Any,
    *,
    underlying: str,
    ts: int,
    votes: Sequence[Any],
    picker: dict[str, Any],
    live_lots: Optional[int] = None,
    prev: Any = None,
    closed: Any = None,
    classified: Optional[dict[str, Any]] = None,
    bars_1m: Optional[Sequence[Any]] = None,
    logit: Optional[dict[str, Any]] = None,
    wing_quotes: Optional[dict] = None,
    atm: Optional[float] = None,
    spot: Optional[float] = None,
) -> dict[str, Any]:
    """One decision-minute record. Does not read or write orders."""
    und = underlying.upper()
    shadow = shadow_picker_majority(votes, prev=prev, closed=closed, classified=classified)
    live = decision_brief(picker)
    shadow_view = decision_brief(shadow)
    closes = _closes(bars_1m)
    hari = hari_forecast(closes, prior_day_closes=_prior_closes(engine, und), spot=spot)
    step = STRIKE_STEP.get(und, 50.0)
    snap = near_money_totals(wing_quotes, atm=atm, step=step)
    flow = order_flow_score(_push_flow(engine, und, snap))
    p = None
    if isinstance(logit, dict) and logit.get("p") is not None:
        try:
            p = float(logit["p"])
        except (TypeError, ValueError):
            p = None
    return {
        "schema": SCHEMA,
        "ts": int(ts),
        "minute_ist": _minute_key(ts),
        "index": und,
        "live": live,
        "shadow": shadow_view,
        "agree": live["action"] == shadow_view["action"] and live["side"] == shadow_view["side"],
        "logit_p": p,
        "hari": hari,
        "order_flow": flow,
        "volsize_7b": volsize_row(em30=hari.get("em30"), live_lots=live_lots),
    }


def shadow_path(engine: Any, ts: int) -> Optional[Path]:
    root = getattr(engine, "root", None)
    if root is None:
        return None
    return Path(root) / "data" / "shadow" / f"{_day(ts)}.jsonl"


def append_shadow_row(engine: Any, row: dict[str, Any]) -> Optional[Path]:
    path = shadow_path(engine, int(row["ts"]))
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    return path


def log_decision_shadow(engine: Any, **kwargs: Any) -> Optional[dict[str, Any]]:
    """Write at most one row per index per IST minute. May raise; caller catches."""
    if not shadow_logging_enabled(engine):
        return None
    ctx = getattr(engine, "ctx", None)
    if ctx is not None and not getattr(ctx, "write", True):
        return None  # write=False replays (lab, parity, offline verification) write nothing
    ts = int(kwargs["ts"])
    und = str(kwargs["underlying"]).upper()
    seen = getattr(engine, "_shadow_minutes", None)
    if not isinstance(seen, set):
        seen = set()
        engine._shadow_minutes = seen  # type: ignore[attr-defined]
    key = (und, ts // 60)
    if key in seen:
        # Still keep the chain window warm between logged minutes.
        step = STRIKE_STEP.get(und, 50.0)
        snap = near_money_totals(kwargs.get("wing_quotes"), atm=kwargs.get("atm"), step=step)
        _push_flow(engine, und, snap)
        return None
    row = build_shadow_row(engine, **kwargs)
    append_shadow_row(engine, row)
    seen.add(key)
    return row


def safe_log_shadow(engine: Any, **kwargs: Any) -> Optional[dict[str, Any]]:
    """Paper-engine hook. Logs the exception and returns None. Does not re-raise."""
    try:
        return log_decision_shadow(engine, **kwargs)
    except Exception:
        log.exception("shadow log failed")
        return None
