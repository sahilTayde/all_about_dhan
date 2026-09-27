"""Read-only query helpers over the analytics warehouse (for the Founder page and the CLI).

Every helper opens the file with `mode=ro`, so a caller can never write it. A missing warehouse
returns `[]` (or `{"ok": False}` for status) instead of raising: the page shows "no data yet".
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from warehouse.etl import FACT_TABLES, PERIODS, default_analytics_db


def _ro(db: Path | None) -> sqlite3.Connection | None:
    path = Path(db or default_analytics_db())
    if not path.is_file():
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _select(db: Path | None, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
    conn = _ro(db)
    if conn is None:
        return []
    try:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()


def _where(
    col: str,
    since: str | None,
    until: str | None,
    extra: tuple[tuple[str, Any], ...] = (),
) -> tuple[str, tuple]:
    parts, args = [], []
    if since:
        parts.append(f"{col} >= ?")
        args.append(since)
    if until:
        parts.append(f"{col} <= ?")
        args.append(until)
    for clause, value in extra:
        if value is not None:
            parts.append(clause)
            args.append(value)
    return (" WHERE " + " AND ".join(parts)) if parts else "", tuple(args)


def pnl(
    db: Path | None = None,
    *,
    period: str = "day",
    book_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """P&L and win rate per period and book. `period` is day | week (Monday) | month (YYYY-MM).

    `since` / `until` are IST dates and filter on the trade day before grouping.
    """
    if period not in PERIODS:
        raise ValueError(f"period must be one of {tuple(PERIODS)}")
    expr = PERIODS[period]
    where, args = _where("day", since, until, (("book_id = ?", book_id),))
    where = (where + " AND" if where else " WHERE") + " filled = 1 AND day IS NOT NULL"
    sql = (
        f"SELECT {expr} AS period, book_id, COUNT(*) AS n_trades, SUM(net_pnl > 0) AS n_wins, "
        "ROUND(100.0 * SUM(net_pnl > 0) / COUNT(*), 2) AS win_rate_pct, ROUND(SUM(gross_pnl), 2) AS gross_pnl, "
        "ROUND(SUM(charges), 2) AS charges, ROUND(SUM(net_pnl), 2) AS net_pnl, "
        "ROUND(AVG(entry_slippage), 4) AS avg_entry_slippage, ROUND(AVG(exit_slippage), 4) AS avg_exit_slippage "
        f"FROM trades{where} GROUP BY {expr}, book_id ORDER BY period DESC, book_id LIMIT ?"
    )
    return _select(db, sql, (*args, int(limit)))


def exit_reasons(
    db: Path | None = None,
    *,
    book_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    where, args = _where("day", since, until, (("book_id = ?", book_id),))
    return _select(
        db,
        f"SELECT * FROM exit_reasons{where} ORDER BY day DESC, n_trades DESC LIMIT ?",
        (*args, int(limit)),
    )


def model_attribution(
    db: Path | None = None,
    *,
    since: str | None = None,
    until: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Per model/analyst named on the ticket: trades, wins, net P&L (a trade counts once per model it names)."""
    where, args = _where("day", since, until)
    sql = (
        "SELECT model, COUNT(DISTINCT day) AS n_days, SUM(n_trades) AS n_trades, SUM(n_wins) AS n_wins, "
        "ROUND(100.0 * SUM(n_wins) / SUM(n_trades), 2) AS win_rate_pct, ROUND(SUM(net_pnl), 2) AS net_pnl "
        f"FROM model_attribution{where} GROUP BY model ORDER BY net_pnl DESC LIMIT ?"
    )
    return _select(db, sql, (*args, int(limit)))


def stage_attribution(
    db: Path | None = None,
    *,
    since: str | None = None,
    until: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Counts per stage (boss / risk / desk / exit) and reason; exit rows also carry net P&L."""
    where, args = _where("day", since, until)
    sql = (
        "SELECT stage, outcome, reason, SUM(n) AS n, ROUND(SUM(net_pnl), 2) AS net_pnl "
        f"FROM stage_attribution{where} GROUP BY stage, outcome, reason ORDER BY stage, n DESC LIMIT ?"
    )
    return _select(db, sql, (*args, int(limit)))


def analyst_votes(
    db: Path | None = None,
    *,
    since: str | None = None,
    until: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    where, args = _where("day", since, until)
    sql = (
        "SELECT analyst_id, signal, SUM(n) AS n, ROUND(SUM(n * avg_confidence) / SUM(n), 4) AS avg_confidence "
        f"FROM analyst_vote_summary{where} GROUP BY analyst_id, signal ORDER BY analyst_id, n DESC LIMIT ?"
    )
    return _select(db, sql, (*args, int(limit)))


def slippage(
    db: Path | None = None,
    *,
    book_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Per day and book: average slippage, fill price minus decision price, premium points per unit.

    Books are long premium, so a positive entry slippage is a cost and a positive exit slippage
    (sold above the decision price) is a gain. `slippage_cost_inr` nets both legs; + is money lost.
    """
    where, args = _where("day", since, until, (("book_id = ?", book_id),))
    where = (where + " AND" if where else " WHERE") + " filled = 1"
    sql = (
        "SELECT day, book_id, COUNT(*) AS n_trades, COUNT(entry_slippage) AS n_entry_measured, "
        "ROUND(AVG(entry_slippage), 4) AS avg_entry_slippage, COUNT(exit_slippage) AS n_exit_measured, "
        "ROUND(AVG(exit_slippage), 4) AS avg_exit_slippage, "
        "ROUND(SUM((COALESCE(entry_slippage, 0) - COALESCE(exit_slippage, 0)) * COALESCE(qty, 0)), 2) "
        "AS slippage_cost_inr "
        f"FROM trades{where} GROUP BY day, book_id ORDER BY day DESC, book_id LIMIT ?"
    )
    return _select(db, sql, (*args, int(limit)))


def charges(
    db: Path | None = None,
    *,
    period: str = "day",
    since: str | None = None,
    until: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Charge components per period from the paper book breakdown (ledger charge lines are in `charges`)."""
    if period not in PERIODS:
        raise ValueError(f"period must be one of {tuple(PERIODS)}")
    expr = PERIODS[period]
    where, args = _where("day", since, until)
    where = (where + " AND" if where else " WHERE") + " filled = 1 AND day IS NOT NULL"
    cols = ", ".join(
        f"ROUND(SUM({c}), 2) AS {c}"
        for c in ("brokerage", "stt", "exchange", "sebi", "stamp", "gst", "charges")
    )
    sql = f"SELECT {expr} AS period, COUNT(*) AS n_trades, {cols} FROM trades{where} GROUP BY {expr} ORDER BY period DESC LIMIT ?"
    return _select(db, sql, (*args, int(limit)))


def rejects(db: Path | None = None, *, limit: int = 200) -> list[dict[str, Any]]:
    """Quarantined lines / fields / files: file, line number (0 = whole file), field, reason, sample."""
    return _select(
        db,
        "SELECT src_file, line_no, field, reason, sample FROM rejects ORDER BY src_file, line_no LIMIT ?",
        (int(limit),),
    )


def etl_status(db: Path | None = None) -> dict[str, Any]:
    conn = _ro(db)
    if conn is None:
        return {
            "ok": False,
            "db": str(db or default_analytics_db()),
            "note": "no warehouse yet; run python -m warehouse.etl run",
        }
    try:
        counts = {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in FACT_TABLES
        }
        counts["trades"] = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        last = conn.execute(
            "SELECT * FROM etl_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        days = conn.execute(
            "SELECT MIN(day), MAX(day) FROM trades WHERE filled = 1"
        ).fetchone()
        return {
            "ok": True,
            "db": str(db or default_analytics_db()),
            "counts": counts,
            "trade_days": {"first": days[0], "last": days[1]},
            "last_run": dict(last) if last else None,
        }
    finally:
        conn.close()
