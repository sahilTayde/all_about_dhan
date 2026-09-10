"""One-shot paper gather → warehouse. No market-hours loop. No orders."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from warehouse.feasibility import evaluate_long_premium
from warehouse.paths import repo_root
from warehouse.store import Warehouse

FEATURE_SET_VERSION = "gather-v1"
MODEL_VERSION = "none-NO_PROMOTE"
UNDERLYINGS = ("NIFTY", "BANKNIFTY", "SENSEX")
CHAIN_GAP_SEC = 3.2  # HQ unique option-chain spacing
MAX_BARS = 180


def _bar_ts(bar: Any) -> str:
    raw = bar["ts"] if isinstance(bar, dict) else getattr(bar, "ts", None)
    try:
        return datetime.fromtimestamp(int(float(raw)), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _bar_field(bar: Any, name: str) -> Optional[float]:
    try:
        if isinstance(bar, dict):
            return float(bar[name])
        return float(getattr(bar, name))
    except (TypeError, ValueError, KeyError, AttributeError):
        return None


def _compact_watch(watch: Any) -> dict[str, Any]:
    d = watch.to_dict() if hasattr(watch, "to_dict") else dict(watch)
    # Never persist a full OC book.
    keep = (
        "underlying",
        "source",
        "chain_lean",
        "spot",
        "atm_strike",
        "pcr_oi",
        "atm_ce_ltp",
        "atm_pe_ltp",
        "expiry",
        "strike_count",
        "hypothesis_flag",
        "data_gaps",
    )
    return {k: d.get(k) for k in keep}


def _ticket_from_watch(watch: Any, index: Any) -> SimpleNamespace:
    lean = getattr(watch, "chain_lean", "NEUTRAL")
    ltp = getattr(watch, "atm_ce_ltp", None) if lean == "CE" else getattr(watch, "atm_pe_ltp", None)
    if lean not in ("CE", "PE"):
        ltp = getattr(watch, "atm_ce_ltp", None) or getattr(watch, "atm_pe_ltp", None)
    src = "optionchain_atm" if getattr(watch, "source", "") == "dhan_live" else getattr(watch, "source", "")
    return SimpleNamespace(
        premium_lean={
            "source": src,
            "spot": getattr(watch, "spot", None),
            "pcr_oi": getattr(watch, "pcr_oi", None),
            "chain_lean": lean,
            "ltp": ltp,
            "option_ltp": ltp,
        },
        index_bar_meta=index.to_dict() if hasattr(index, "to_dict") else {},
        reasons=[],
    )


def ingest_probe_file(wh: Warehouse, path: Optional[Path] = None) -> Optional[str]:
    """Append latest sanitized paper-probe JSON (no tokens)."""
    recon = repo_root() / "data" / "recon"
    if path is None:
        files = sorted(recon.glob("PAPER_PROBE_*.json"))
        path = files[-1] if files else None
    if path is None or not path.is_file():
        return None
    blob = json.loads(path.read_text(encoding="utf-8"))
    compact = {
        "as_of_ist": blob.get("as_of_ist"),
        "orders": blob.get("orders"),
        "profile_ok": (blob.get("profile") or {}).get("ok"),
        "data_plan": ((blob.get("profile") or {}).get("data") or {}).get("dataPlan"),
        "chains": blob.get("chains"),
        "intraday_5m_index": blob.get("intraday_5m_index"),
    }
    digest = wh.append_raw_event(
        source="paper_probe",
        symbol="MULTI",
        segment="IDX_I",
        payload=compact,
        received_at=str(blob.get("as_of_ist") or ""),
    )
    wh.append_research_source(
        source_id=f"paper-probe-{path.stem}",
        layer="SOURCE_FACT",
        digest=digest,
        title=path.name,
        retrieved_at=str(blob.get("as_of_ist") or ""),
    )
    return digest


def ingest_once(
    *,
    live: bool,
    warehouse: Optional[Warehouse] = None,
    underlyings: tuple[str, ...] = UNDERLYINGS,
    sleep_s: float = CHAIN_GAP_SEC,
    watch_fn=None,
    bars_fn=None,
    score_fn=None,
) -> dict[str, Any]:
    """Fetch INDEX 1m + ATM/PCR once per underlying. Does not start a poll loop."""
    from trading_agents_india.hooks.chain import watch_chain
    from trading_agents_india.hooks.index_bars import fetch_index_bars
    from trading_agents_india.lean_mix import pick_customer_lean

    watch_fn = watch_fn or watch_chain
    bars_fn = bars_fn or fetch_index_bars
    score_fn = score_fn or pick_customer_lean

    wh = warehouse or Warehouse()
    wh.init()
    probe_hash = ingest_probe_file(wh)

    rows: list[dict[str, Any]] = []
    for i, und in enumerate(underlyings):
        if live and i > 0 and sleep_s > 0:
            time.sleep(sleep_s)
        watch = watch_fn(und, prefer_live=live)
        index = bars_fn(und, prefer_live=live)
        compact = _compact_watch(watch)
        compact["index"] = index.to_dict() if hasattr(index, "to_dict") else {"bar_count": 0}
        digest = wh.append_raw_event(
            source="gather_oneshot",
            symbol=und,
            segment="IDX_I",
            payload=compact,
        )
        wh.append_chain_snapshot(
            underlying=und,
            expiry=getattr(watch, "expiry", None),
            atm=None if getattr(watch, "atm_strike", None) is None else str(watch.atm_strike),
            pcr=getattr(watch, "pcr_oi", None),
            payload=compact,
        )
        bars = list(getattr(index, "bars", None) or [])[-MAX_BARS:]
        for bar in bars:
            wh.append_bar(
                timeframe="1m",
                symbol=und,
                ts=_bar_ts(bar),
                source=getattr(index, "source", "unavailable"),
                open_=_bar_field(bar, "open"),
                high=_bar_field(bar, "high"),
                low=_bar_field(bar, "low"),
                close=_bar_field(bar, "close"),
                volume=_bar_field(bar, "volume"),
            )
        features = {
            "pcr_oi": getattr(watch, "pcr_oi", None),
            "atm_strike": getattr(watch, "atm_strike", None),
            "spot": getattr(watch, "spot", None),
            "chain_lean": getattr(watch, "chain_lean", None),
            "last_close": getattr(index, "last_close", None),
            "bar_count": getattr(index, "bar_count", 0),
            "NO_PROMOTE": True,
        }
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        wh.append_features(
            symbol=und,
            ts=now,
            feature_set_version=FEATURE_SET_VERSION,
            features=features,
        )
        ticket = _ticket_from_watch(watch, index)
        score = score_fn(ticket, bars=list(getattr(index, "bars", None) or []))
        decision = evaluate_long_premium(
            entry=score.entry,
            stop=score.stop,
            target=score.target,
            stage=score.stage,
        )
        signal_id = f"paper-{und.lower()}-{now.replace(':', '').replace('+', 'z')}"
        stage = "WATCH"
        if decision.action == "KILL":
            stage = decision.new_state
        elif score.stage in {"WATCH", "EARLY", "VETOED", "PARKED"}:
            stage = score.stage
        wh.upsert_signal(
            signal_id=signal_id,
            ts=now,
            underlying=und,
            stage=stage,
            side=score.lean,
            levels={"entry": score.entry, "stop": score.stop, "target": score.target},
            model_version=MODEL_VERSION,
            feature_set_version=FEATURE_SET_VERSION,
        )
        wh.append_ticket_event(
            signal_id=signal_id,
            old_state="idle",
            new_state=stage,
            reason_code=decision.reason_code,
            note=f"{score.mix_id} {score.lean} NO_PROMOTE; dealer={decision.action}",
        )
        rows.append(
            {
                "underlying": und,
                "chain_source": getattr(watch, "source", None),
                "index_source": getattr(index, "source", None),
                "bar_count": getattr(index, "bar_count", 0),
                "mix_id": score.mix_id,
                "lean": score.lean,
                "mix_stage": score.stage,
                "dealer": decision.to_dict(),
                "signal_id": signal_id,
                "payload_hash": digest,
                "NO_PROMOTE": True,
            }
        )

    return {
        "ok": True,
        "live": live,
        "loop_started": False,
        "orders": "refused",
        "probe_ingested": bool(probe_hash),
        "feature_set_version": FEATURE_SET_VERSION,
        "rows": rows,
        "status": wh.status(),
    }
