"""Persist chain snapshots and MARKET_SIGNAL JSON. Never write secrets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from desk_intel.schema import ChainSnapshot, MarketSignal, SentimentWindow, StrikeRow, normalize_poll_mode
from desk_intel.time_ist import now_ist, now_ist_iso


def _dump(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def snapshot_path(root: Path, snapshots_dir: str, underlying: str, *, suffix: str = "") -> Path:
    now = now_ist()
    name = now.strftime("%H%M%S") + (f"_{suffix}" if suffix else "")
    return root / snapshots_dir / underlying / now.strftime("%Y-%m-%d") / f"{name}.json"


def signal_path(root: Path, signals_dir: str, *, suffix: str = "morning") -> Path:
    now = now_ist()
    return root / signals_dir / now.strftime("%Y-%m-%d") / f"{now.strftime('%H%M%S')}_{suffix}.json"


def last_snapshot_path(root: Path, snapshots_dir: str, underlying: str) -> Path:
    return root / snapshots_dir / underlying / "last.json"


def save_snapshot(
    root: Path,
    snapshots_dir: str,
    snap: ChainSnapshot,
    *,
    remember_last: bool = True,
) -> Path:
    path = snapshot_path(root, snapshots_dir, snap.underlying, suffix=snap.mode)
    _dump(path, snap.to_dict())
    if remember_last:
        _dump(last_snapshot_path(root, snapshots_dir, snap.underlying), snap.to_dict())
    return path


def save_signals(root: Path, signals_dir: str, signals: list[MarketSignal], *, suffix: str) -> Path:
    path = signal_path(root, signals_dir, suffix=suffix)
    return _dump(path, [s.to_dict() for s in signals])


def save_json(path: Path, payload: Any) -> Path:
    return _dump(path, payload)


def market_signal_from_dict(raw: dict[str, Any]) -> MarketSignal:
    return MarketSignal(
        id=str(raw.get("id") or ""),
        underlying=str(raw.get("underlying") or ""),
        lean=raw.get("lean") or "NEUTRAL",
        confidence=float(raw.get("confidence") or 0),
        risk_regime=raw.get("risk_regime") or "MIXED",
        reasons=list(raw.get("reasons") or []),
        vetoes=list(raw.get("vetoes") or []),
        timestamp=str(raw.get("timestamp") or now_ist_iso()),
        news_bias=raw.get("news_bias") or "MIXED",
        chain_bias=raw.get("chain_bias") or "NEUTRAL",
        tags=list(raw.get("tags") or []),
        expiry=raw.get("expiry"),
        atm_strike=raw.get("atm_strike"),
        dry_run=bool(raw.get("dry_run", True)),
        layer=str(raw.get("layer") or "HYPOTHESIS"),
        compliance=str(raw.get("compliance") or ""),
        paper_signal=raw.get("paper_signal") if isinstance(raw.get("paper_signal"), dict) else None,
        stage=raw.get("stage") or "WATCH",
        outcome=raw.get("outcome"),
        still_valid=bool(raw.get("still_valid", False)),
        sentiment_windows=_sentiment_windows_from_raw(raw.get("sentiment_windows")),
    )


def _sentiment_windows_from_raw(raw: Any) -> list[SentimentWindow]:
    if not isinstance(raw, list):
        return []
    out: list[SentimentWindow] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            SentimentWindow(
                horizon=str(item.get("horizon") or ""),
                lean=item.get("lean") or "NEUTRAL",
                confidence=float(item.get("confidence") or 0),
                news_bias=item.get("news_bias") or "MIXED",
                chain_lean=item.get("chain_lean") or "NEUTRAL",
                mock=bool(item.get("mock", True)),
                note=str(item.get("note") or ""),
            )
        )
    return out


def load_signals_for_day(root: Path, signals_dir: str, day: str) -> list[MarketSignal]:
    folder = root / signals_dir / day
    if not folder.is_dir():
        return []
    by_id: dict[str, MarketSignal] = {}
    for path in sorted(folder.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = raw if isinstance(raw, list) else [raw]
        for item in rows:
            if not isinstance(item, dict):
                continue
            sig = market_signal_from_dict(item)
            if sig.id:
                by_id[sig.id] = sig
    return list(by_id.values())


def snapshot_from_dict(raw: dict[str, Any]) -> ChainSnapshot:
    strikes = []
    for row in raw.get("strikes") or []:
        strikes.append(
            StrikeRow(
                strike=float(row.get("strike") or 0),
                ce_oi=int(row.get("ce_oi") or 0),
                pe_oi=int(row.get("pe_oi") or 0),
                ce_oi_prev=int(row.get("ce_oi_prev") or 0),
                pe_oi_prev=int(row.get("pe_oi_prev") or 0),
                ce_volume=int(row.get("ce_volume") or 0),
                pe_volume=int(row.get("pe_volume") or 0),
                ce_ltp=row.get("ce_ltp"),
                pe_ltp=row.get("pe_ltp"),
                ce_security_id=row.get("ce_security_id"),
                pe_security_id=row.get("pe_security_id"),
                ce_gamma=row.get("ce_gamma"),
                pe_gamma=row.get("pe_gamma"),
                ce_delta=row.get("ce_delta"),
                pe_delta=row.get("pe_delta"),
            )
        )
    return ChainSnapshot(
        underlying=str(raw.get("underlying") or ""),
        expiry=raw.get("expiry"),
        spot=raw.get("spot"),
        as_of_ist=str(raw.get("as_of_ist") or now_ist().isoformat()),
        mode=normalize_poll_mode(raw.get("mode") or "full_chain_3m"),
        dry_run=bool(raw.get("dry_run")),
        strikes=strikes,
        source=str(raw.get("source") or "dhan_option_chain"),
        note=str(raw.get("note") or ""),
    )


def latest_snapshot(root: Path, snapshots_dir: str, underlying: str) -> Optional[ChainSnapshot]:
    """Prefer remembered last.json, then fall back to the newest timestamped file."""
    last = last_snapshot_path(root, snapshots_dir, underlying)
    if last.is_file():
        raw = json.loads(last.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return snapshot_from_dict(raw)
    folder = root / snapshots_dir / underlying
    if not folder.is_dir():
        return None
    files = sorted(p for p in folder.rglob("*.json") if p.name != "last.json")
    if not files:
        return None
    raw = json.loads(files[-1].read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    return snapshot_from_dict(raw)
