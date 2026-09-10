"""SQLite warehouse. Append raw; do not git-add the db file."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from warehouse.hashes import canonical_json, payload_hash
from warehouse.paths import assert_writable_db, default_db
from warehouse.ohlc import normalize_tf, origin_for, resample_minutes, resample_weeks, ts_iso
from warehouse.schema import DDL, SCHEMA_VERSION


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Warehouse:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = assert_writable_db(Path(path) if path else default_db())

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init(self) -> dict[str, Any]:
        with self.connect() as conn:
            conn.executescript(DDL)
            cur = conn.execute(
                "SELECT version FROM schema_migrations WHERE version=?",
                (SCHEMA_VERSION,),
            )
            if cur.fetchone() is None:
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, _utc_now()),
                )
            self._backfill_ohlc(conn)
            conn.commit()
        return {"ok": True, "path": str(self.path), "schema_version": SCHEMA_VERSION}

    def _backfill_ohlc(self, conn: sqlite3.Connection) -> None:
        """Copy legacy bars_1m / bars_5m into ohlc_bars once."""
        try:
            n = int(conn.execute("SELECT COUNT(*) AS n FROM ohlc_bars").fetchone()["n"])
        except sqlite3.OperationalError:
            return
        if n > 0:
            return
        for table, tf in (("bars_1m", "1m"), ("bars_5m", "5m")):
            try:
                rows = conn.execute(
                    f"SELECT symbol, ts, open, high, low, close, volume, oi, source FROM {table}"
                ).fetchall()
            except sqlite3.OperationalError:
                continue
            for row in rows:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO ohlc_bars
                    (symbol, timeframe, ts, open, high, low, close, volume, oi, source, origin)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["symbol"],
                        tf,
                        row["ts"],
                        row["open"],
                        row["high"],
                        row["low"],
                        row["close"],
                        row["volume"],
                        row["oi"],
                        row["source"],
                        origin_for(tf),
                    ),
                )

    def status(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {
                "ok": True,
                "exists": False,
                "path": str(self.path),
                "schema_version": None,
                "counts": {},
            }
        tables = (
            "raw_market_events",
            "bars_1m",
            "bars_5m",
            "ohlc_bars",
            "chain_snapshots",
            "features",
            "signals",
            "ticket_events",
            "outcomes",
            "research_sources",
            "counsel_events",
            "model_runs",
            "chain_strike_rows",
            "option_levels",
            "index_constituents",
        )
        counts: dict[str, int] = {}
        version = None
        with self.connect() as conn:
            row = conn.execute(
                "SELECT MAX(version) AS v FROM schema_migrations"
            ).fetchone()
            version = None if row is None else row["v"]
            for name in tables:
                try:
                    counts[name] = int(
                        conn.execute(f"SELECT COUNT(*) AS n FROM {name}").fetchone()["n"]
                    )
                except sqlite3.OperationalError:
                    counts[name] = 0
            by_tf: dict[str, int] = {}
            try:
                for row in conn.execute(
                    "SELECT timeframe, COUNT(*) AS n FROM ohlc_bars GROUP BY timeframe"
                ):
                    by_tf[str(row["timeframe"])] = int(row["n"])
            except sqlite3.OperationalError:
                by_tf = {}
        return {
            "ok": True,
            "exists": True,
            "path": str(self.path),
            "schema_version": version,
            "counts": counts,
            "ohlc_by_timeframe": by_tf,
            "is_mock_default": True,
        }

    def append_raw_event(
        self,
        *,
        source: str,
        symbol: str,
        segment: str,
        payload: Any,
        received_at: Optional[str] = None,
    ) -> str:
        digest = payload_hash(payload)
        ts = received_at or _utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO raw_market_events
                (source, symbol, segment, received_at, payload_hash, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source, symbol, segment, ts, digest, canonical_json(payload)),
            )
            conn.commit()
        return digest

    def append_bar(
        self,
        *,
        timeframe: str,
        symbol: str,
        ts: str,
        source: str,
        open_: Optional[float] = None,
        high: Optional[float] = None,
        low: Optional[float] = None,
        close: Optional[float] = None,
        volume: Optional[float] = None,
        oi: Optional[float] = None,
        origin: Optional[str] = None,
    ) -> None:
        tf = normalize_tf(timeframe)
        src_origin = origin or origin_for(tf)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO ohlc_bars
                (symbol, timeframe, ts, open, high, low, close, volume, oi, source, origin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (symbol, tf, ts, open_, high, low, close, volume, oi, source, src_origin),
            )
            if tf in {"1m", "5m"}:
                table = "bars_1m" if tf == "1m" else "bars_5m"
                conn.execute(
                    f"""
                    INSERT OR IGNORE INTO {table}
                    (symbol, ts, open, high, low, close, volume, oi, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (symbol, ts, open_, high, low, close, volume, oi, source),
                )
            conn.commit()

    def append_ohlc_rows(
        self,
        *,
        symbol: str,
        timeframe: str,
        rows: list[dict[str, Any]],
        source: str,
        origin: Optional[str] = None,
    ) -> int:
        n = 0
        for row in rows:
            self.append_bar(
                timeframe=timeframe,
                symbol=symbol,
                ts=ts_iso(int(row["ts"])) if isinstance(row.get("ts"), (int, float)) else str(row["ts"]),
                source=source,
                open_=row.get("open"),
                high=row.get("high"),
                low=row.get("low"),
                close=row.get("close"),
                volume=row.get("volume"),
                oi=row.get("oi"),
                origin=origin,
            )
            n += 1
        return n

    def load_bars(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: Optional[int] = None,
        resample_if_empty: bool = True,
    ) -> list[dict[str, Any]]:
        """Read stored candles. 3m/1w resample from 1m/1d if those rows are missing."""
        tf = normalize_tf(timeframe)
        und = symbol.upper()
        with self.connect() as conn:
            sql = (
                "SELECT symbol, timeframe, ts, open, high, low, close, volume, oi, source, origin "
                "FROM ohlc_bars WHERE symbol=? AND timeframe=? ORDER BY ts"
            )
            rows = [dict(r) for r in conn.execute(sql, (und, tf)).fetchall()]
        if rows or not resample_if_empty:
            return rows[-limit:] if limit else rows
        if tf == "3m":
            base = self.load_bars(und, "1m", resample_if_empty=False)
            rebuilt = resample_minutes(
                [
                    {
                        "ts": int(datetime.fromisoformat(r["ts"]).timestamp()),
                        "open": r["open"],
                        "high": r["high"],
                        "low": r["low"],
                        "close": r["close"],
                        "volume": r["volume"],
                        "oi": r["oi"],
                    }
                    for r in base
                ],
                3,
            )
            return (
                [
                    {
                        "symbol": und,
                        "timeframe": "3m",
                        "ts": ts_iso(r["ts"]),
                        "open": r["open"],
                        "high": r["high"],
                        "low": r["low"],
                        "close": r["close"],
                        "volume": r["volume"],
                        "oi": r["oi"],
                        "source": "resample_1m",
                        "origin": "resample_1m",
                    }
                    for r in rebuilt
                ][-limit:]
                if limit
                else [
                    {
                        "symbol": und,
                        "timeframe": "3m",
                        "ts": ts_iso(r["ts"]),
                        "open": r["open"],
                        "high": r["high"],
                        "low": r["low"],
                        "close": r["close"],
                        "volume": r["volume"],
                        "oi": r["oi"],
                        "source": "resample_1m",
                        "origin": "resample_1m",
                    }
                    for r in rebuilt
                ]
            )
        if tf == "1w":
            base = self.load_bars(und, "1d", resample_if_empty=False)
            rebuilt = resample_weeks(
                [
                    {
                        "ts": int(datetime.fromisoformat(r["ts"]).timestamp()),
                        "open": r["open"],
                        "high": r["high"],
                        "low": r["low"],
                        "close": r["close"],
                        "volume": r["volume"],
                        "oi": r["oi"],
                    }
                    for r in base
                ]
            )
            out = [
                {
                    "symbol": und,
                    "timeframe": "1w",
                    "ts": ts_iso(r["ts"]),
                    "open": r["open"],
                    "high": r["high"],
                    "low": r["low"],
                    "close": r["close"],
                    "volume": r["volume"],
                    "oi": r["oi"],
                    "source": "resample_1d",
                    "origin": "resample_1d",
                }
                for r in rebuilt
            ]
            return out[-limit:] if limit else out
        return []

    def append_chain_snapshot(
        self,
        *,
        underlying: str,
        ts: Optional[str] = None,
        expiry: Optional[str] = None,
        atm: Optional[str] = None,
        pcr: Optional[float] = None,
        payload: Optional[Any] = None,
    ) -> str:
        body = payload if payload is not None else {"underlying": underlying, "atm": atm, "pcr": pcr}
        digest = payload_hash(body)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO chain_snapshots
                (underlying, ts, expiry, atm, pcr, payload_hash, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    underlying,
                    ts or _utc_now(),
                    expiry,
                    atm,
                    pcr,
                    digest,
                    canonical_json(body),
                ),
            )
            conn.commit()
        return digest

    def append_features(
        self,
        *,
        symbol: str,
        ts: str,
        feature_set_version: str,
        features: Any,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO features
                (symbol, ts, feature_set_version, feature_json)
                VALUES (?, ?, ?, ?)
                """,
                (symbol, ts, feature_set_version, canonical_json(features)),
            )
            conn.commit()

    def upsert_signal(
        self,
        *,
        signal_id: str,
        ts: Optional[str] = None,
        underlying: str,
        stage: str,
        side: Optional[str] = None,
        levels: Optional[Any] = None,
        model_version: Optional[str] = None,
        feature_set_version: Optional[str] = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO signals
                (signal_id, ts, underlying, stage, side, levels_json,
                 model_version, feature_set_version, is_paper)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(signal_id) DO UPDATE SET
                    ts=excluded.ts,
                    stage=excluded.stage,
                    side=excluded.side,
                    levels_json=excluded.levels_json,
                    model_version=excluded.model_version,
                    feature_set_version=excluded.feature_set_version
                """,
                (
                    signal_id,
                    ts or _utc_now(),
                    underlying,
                    stage,
                    side,
                    None if levels is None else canonical_json(levels),
                    model_version,
                    feature_set_version,
                ),
            )
            conn.commit()

    def append_ticket_event(
        self,
        *,
        signal_id: str,
        new_state: str,
        reason_code: str,
        old_state: Optional[str] = None,
        note: Optional[str] = None,
        ts: Optional[str] = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO ticket_events
                (signal_id, ts, old_state, new_state, reason_code, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (signal_id, ts or _utc_now(), old_state, new_state, reason_code, note),
            )
            conn.commit()

    def append_outcome(
        self,
        *,
        signal_id: str,
        outcome: str,
        exit_reason: Optional[str] = None,
        points: Optional[float] = None,
        is_mock: bool = True,
        ts: Optional[str] = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO outcomes
                (signal_id, outcome, exit_reason, points, is_mock, ts)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    outcome,
                    exit_reason,
                    points,
                    1 if is_mock else 0,
                    ts or _utc_now(),
                ),
            )
            conn.commit()

    def append_research_source(
        self,
        *,
        source_id: str,
        layer: str,
        digest: str,
        url: Optional[str] = None,
        title: Optional[str] = None,
        retrieved_at: Optional[str] = None,
    ) -> None:
        if layer not in {"SOURCE_FACT", "VALIDATION", "HYPOTHESIS"}:
            raise ValueError("layer must be SOURCE_FACT / VALIDATION / HYPOTHESIS")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO research_sources
                (source_id, url, title, retrieved_at, layer, hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source_id, url, title, retrieved_at, layer, digest),
            )
            conn.commit()

    def append_counsel_event(
        self,
        *,
        job_id: str,
        facts: Any,
        prompt_version: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        token_estimate: Optional[int] = None,
        output: Optional[Any] = None,
        verdict: Optional[str] = None,
        together: Optional[str] = None,
        ts: Optional[str] = None,
    ) -> dict[str, str]:
        facts_digest = payload_hash(facts)
        out_digest = payload_hash(output) if output is not None else ""
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO counsel_events
                (job_id, facts_hash, provider, model, prompt_version,
                 token_estimate, output_hash, verdict, together, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    facts_digest,
                    provider,
                    model,
                    prompt_version,
                    token_estimate,
                    out_digest or None,
                    verdict,
                    together,
                    ts or _utc_now(),
                ),
            )
            conn.commit()
        return {"facts_hash": facts_digest, "output_hash": out_digest}

    def lookup_counsel(
        self,
        *,
        job_id: str,
        facts: Any,
        prompt_version: str,
        model: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        facts_digest = payload_hash(facts)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT job_id, facts_hash, provider, model, prompt_version,
                       verdict, together, ts
                FROM counsel_events
                WHERE job_id=? AND facts_hash=? AND prompt_version=?
                  AND (model IS ? OR model=?)
                ORDER BY id DESC LIMIT 1
                """,
                (job_id, facts_digest, prompt_version, model, model),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def insert_chain_snapshot_row(
        self,
        *,
        underlying: str,
        expiry: Optional[str],
        atm: Optional[str],
        pcr: Optional[float],
        payload: Any,
        ts: Optional[str] = None,
    ) -> int:
        digest = self.append_chain_snapshot(
            underlying=underlying,
            ts=ts,
            expiry=expiry,
            atm=atm,
            pcr=pcr,
            payload=payload,
        )
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM chain_snapshots WHERE payload_hash=? ORDER BY id DESC LIMIT 1",
                (digest,),
            ).fetchone()
        return int(row["id"]) if row else 0

    def append_strike_rows(self, snapshot_id: int, rows: list[dict[str, Any]]) -> int:
        n = 0
        with self.connect() as conn:
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO chain_strike_rows (
                        snapshot_id, underlying, expiry, as_of, strike,
                        ce_ltp, pe_ltp, ce_oi, pe_oi, ce_oi_prev, pe_oi_prev,
                        ce_volume, pe_volume, ce_security_id, pe_security_id,
                        ce_delta, pe_delta, ce_gamma, pe_gamma,
                        ce_theta, pe_theta, ce_vega, pe_vega, ce_iv, pe_iv
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        snapshot_id,
                        row.get("underlying"),
                        row.get("expiry"),
                        row.get("as_of"),
                        row.get("strike"),
                        row.get("ce_ltp"),
                        row.get("pe_ltp"),
                        row.get("ce_oi"),
                        row.get("pe_oi"),
                        row.get("ce_oi_prev"),
                        row.get("pe_oi_prev"),
                        row.get("ce_volume"),
                        row.get("pe_volume"),
                        row.get("ce_security_id"),
                        row.get("pe_security_id"),
                        row.get("ce_delta"),
                        row.get("pe_delta"),
                        row.get("ce_gamma"),
                        row.get("pe_gamma"),
                        row.get("ce_theta"),
                        row.get("pe_theta"),
                        row.get("ce_vega"),
                        row.get("pe_vega"),
                        row.get("ce_iv"),
                        row.get("pe_iv"),
                    ),
                )
                n += 1
            conn.commit()
        return n

    def append_option_level(self, row: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO option_levels (
                    snapshot_id, underlying, expiry, as_of, side, strike,
                    entry, stop_hyp, target_hyp, dealer_action, dealer_reason, layer
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row.get("snapshot_id"),
                    row.get("underlying"),
                    row.get("expiry"),
                    row.get("as_of"),
                    row.get("side"),
                    row.get("strike"),
                    row.get("entry"),
                    row.get("stop_hyp"),
                    row.get("target_hyp"),
                    row.get("dealer_action"),
                    row.get("dealer_reason"),
                    row.get("layer") or "HYPOTHESIS",
                ),
            )
            conn.commit()

    def append_constituent_row(self, row: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO index_constituents (
                    as_of, index_id, symbol, security_id, segment,
                    weight_pct, weight_layer, ltp, quote_ok
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    row.get("as_of"),
                    row.get("index_id"),
                    row.get("symbol"),
                    row.get("security_id"),
                    row.get("segment"),
                    row.get("weight_pct"),
                    row.get("weight_layer") or "DATA_INSUFFICIENT",
                    row.get("ltp"),
                    1 if row.get("quote_ok") else 0,
                ),
            )
            conn.commit()
