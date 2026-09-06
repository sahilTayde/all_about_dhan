"""Session tags for SCORE_SAMPLE vs analog. Historical NEWS_DAY is DATA_INSUFFICIENT.

EXPIRY weekday is FROM_CONTRACT (03) — do not freeze Thursday vs Tuesday.
Proxy: last INDEX session of each ISO week = HYPOTHESIS expiry analog, not law.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

import yaml

from backtest_engine.clocks import session_date_ist
from backtest_engine.simulate import Trade
from dhan_client.config import repo_root

NEWS_CALENDAR_REL = Path("teams/06_backtesting/docs/refs/NEWS_CALENDAR.yaml")


def last_session_of_iso_week(session_dates: Iterable[str]) -> set[str]:
    """HYPOTHESIS expiry proxy: max date per ISO year-week. Not FROM_CONTRACT."""
    buckets: dict[tuple[int, int], str] = {}
    for raw in session_dates:
        d = date.fromisoformat(raw)
        key = d.isocalendar()[:2]
        prev = buckets.get(key)
        if prev is None or raw > prev:
            buckets[key] = raw
    return set(buckets.values())


def load_news_calendar(path: Optional[Path] = None) -> tuple[set[str], str]:
    """Return (dates, status). Empty file / missing → DATA_INSUFFICIENT."""
    cal = path or (repo_root() / NEWS_CALENDAR_REL)
    if not cal.is_file():
        return set(), "DATA_INSUFFICIENT"
    raw = yaml.safe_load(cal.read_text(encoding="utf-8")) or {}
    rows = raw.get("days") or raw.get("news_days") or []
    dates: set[str] = set()
    for row in rows:
        if isinstance(row, str):
            dates.add(row[:10])
        elif isinstance(row, dict) and row.get("date"):
            dates.add(str(row["date"])[:10])
    if not dates:
        return set(), "DATA_INSUFFICIENT"
    return dates, "CALENDAR_FILE"


def analog_gap_sessions(_session_dates: Iterable[str], gap_leans: list[str], bars) -> set[str]:
    """Sessions where a gap lean fired. ANALOG_MEMORY flag, not a score sample."""
    out: set[str] = set()
    n = min(len(gap_leans), len(bars))
    for i in range(n):
        if gap_leans[i] in ("CE", "PE"):
            out.add(session_date_ist(bars[i].ts))
    return out


def tag_session(
    session: str,
    *,
    expiry_proxy: set[str],
    news_days: set[str],
    news_status: str,
    analog_flags: Optional[set[str]] = None,
) -> dict:
    flags: list[str] = []
    analog = analog_flags or set()
    if session in news_days:
        flags.append("NEWS_DAY")
    if session in expiry_proxy:
        flags.append("EXPIRY")
    if "GAP" in analog:
        flags.append("GAP")
    if "CIRCUIT" in analog or "HALT" in analog:
        flags.extend(sorted(analog & {"CIRCUIT", "HALT"}))
    if "NEWS_DAY" in flags:
        kind = "NEWS_DAY"
    elif "EXPIRY" in flags:
        kind = "EXPIRY"
    elif news_status == "DATA_INSUFFICIENT":
        kind = "UNKNOWN"
    else:
        kind = "NORMAL"
    score_ok = (
        kind == "NORMAL"
        and news_status != "DATA_INSUFFICIENT"
        and not ({"GAP", "CIRCUIT", "HALT"} & set(flags))
    )
    return {
        "session": session,
        "session_kind": kind,
        "session_flags": flags,
        "score_sample_member": score_ok,
        "news_filter": news_status,
        "expiry_tag": "HYPOTHESIS_LAST_SESSION_OF_ISO_WEEK",
    }


def filter_trades(
    trades: list[Trade],
    *,
    expiry_proxy: set[str],
    news_days: set[str],
    news_status: str,
    gap_sessions: Optional[set[str]] = None,
    mode: str,
) -> list[Trade]:
    """mode: all | expiry_stripped | score_sample."""
    gap_sessions = gap_sessions or set()
    kept: list[Trade] = []
    for t in trades:
        analog = {"GAP"} if t.session in gap_sessions else set()
        tag = tag_session(
            t.session,
            expiry_proxy=expiry_proxy,
            news_days=news_days,
            news_status=news_status,
            analog_flags=analog,
        )
        if mode == "all":
            kept.append(t)
        elif mode == "expiry_stripped":
            if "EXPIRY" not in tag["session_flags"] and "NEWS_DAY" not in tag["session_flags"]:
                kept.append(t)
        elif mode == "score_sample":
            if tag["score_sample_member"]:
                kept.append(t)
        else:
            raise ValueError(mode)
    return kept


def session_universe_from_trades(trades: Iterable[Trade]) -> set[str]:
    return {t.session for t in trades}


def session_universe_from_bars(bars) -> set[str]:
    return {session_date_ist(b.ts) for b in bars}


def calendar_meta(news_status: str, expiry_n: int, news_n: int) -> dict:
    return {
        "news_filter": news_status,
        "normal_only_valid": news_status != "DATA_INSUFFICIENT",
        "expiry_proxy_n": expiry_n,
        "news_days_n": news_n,
        "expiry_proxy": "HYPOTHESIS_LAST_SESSION_OF_ISO_WEEK",
        "note": (
            "True NORMAL requires a news calendar. Without it, expiry-stripped "
            "is EXPIRY_STRIPPED / news UNKNOWN — not OOS+NORMAL validated."
        ),
    }
