"""Run paper books on a large HQ chunk. Writes recon JSON. Nothing promotes."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.config import repo_root
from dhan_client.futidx import FutIdxContract, contracts_as_dicts, parse_futidx_csv

from backtest_engine.algos import (
    daily_lean_at_open,
    mixed_index_veto,
    run_strat_001,
    run_strat_003,
    run_strat_006,
    strat_003_leans,
)
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate import Trade, trades_as_dicts

IST = timezone(timedelta(hours=5, minutes=30))

NOT_CODED = (
    ("STRAT-004", "PARKED", "EMA lengths NOT_IN_EN"),
    ("STRAT-005", "OVERLAY", "strike overlay needs option history"),
    ("STRAT-010", "PARKED", "order-flow history DATA_INSUFFICIENT"),
    ("STRAT-011", "WAITING", "reversal alt; not default mix"),
    ("STRAT-012", "WAITING", "candle overlay detail WAITING"),
    ("STRAT-013", "WAITING", "sell credit — not Phase-1 buy"),
    ("STRAT-014", "WAITING", "call ratio sell — not Phase-1 buy"),
)


def _resolve_futidx(client: DhanClient) -> dict[str, Any]:
    try:
        text = client.instruments.fetch_scrip_master_text(detailed=True)
        contracts = parse_futidx_csv(text)
        if len(contracts) < 3:
            compact = client.instruments.fetch_scrip_master_text(detailed=False)
            extra = parse_futidx_csv(compact)
            contracts = {**extra, **contracts}
        return {
            "ok": True,
            "contracts": contracts_as_dicts(contracts),
            "by_name": {k: contracts[k] for k in contracts},
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "contracts": [], "by_name": {}}


def _book_row(book_id: str, trades: list[Trade], extra: dict[str, Any]) -> dict[str, Any]:
    rating = rate_trades(trades, book_id=book_id)
    rating.update(extra)
    rating["trade_sample"] = trades_as_dicts(trades[:8])
    rating["trade_count"] = len(trades)
    return rating


def run_books(client: DhanClient, *, years: float = 5.0, interval: int = 1) -> dict[str, Any]:
    fut = _resolve_futidx(client)
    contracts: dict[str, FutIdxContract] = fut.get("by_name") or {}

    index_series: dict[str, dict[str, Any]] = {}
    fut_series: dict[str, dict[str, Any]] = {}
    for name, sid, seg, inst in INDEX_YAML:
        index_series[name] = fetch_range(
            client,
            security_id=sid,
            exchange_segment=seg,
            instrument=inst,
            interval=interval,
            years=years,
        )
        contract = contracts.get(name)
        if contract is not None:
            fut_series[name] = fetch_range(
                client,
                security_id=contract.security_id,
                exchange_segment=contract.exchange_segment,
                instrument="FUTIDX",
                interval=interval,
                years=years,
                oi=True,
            )

    # STRAT-008 veto from INDEX 3m (or native) leans
    daily: dict[str, dict[str, str]] = {}
    index_3m: dict[str, Any] = {}
    for name, series in index_series.items():
        bars = series.get("bars") or []
        work = resample(bars, 3) if interval == 1 else bars
        index_3m[name] = work
        daily[name] = daily_lean_at_open(work, strat_003_leans(work, equal_weight_vwap=True))
    veto = mixed_index_veto(daily)

    books: list[dict[str, Any]] = []
    for name, series in index_series.items():
        bars_1m = series.get("bars") or []
        bars_3m = index_3m.get(name) or []
        extra = {
            "underlying": name,
            "tape": "INDEX",
            "origin": "PROJECT",
            "volume_note": "INDEX volume UNKNOWN vs FUTIDX",
            "bar_count": series.get("bar_count"),
            "interval_native": interval,
        }
        books.append(
            _book_row(
                f"STRAT-003/{name}/INDEX-1m-resample-3m",
                run_strat_003(
                    bars_3m,
                    underlying=name,
                    veto_sessions=veto,
                    equal_weight_vwap=True,
                    strategy_id="STRAT-003",
                ),
                {**extra, "filters": ["007", "008", "009"], "tf": "3m-resample"},
            )
        )
        books.append(
            _book_row(
                f"MIX-DEFAULT-BUY/{name}/INDEX-3m",
                run_strat_003(
                    bars_3m,
                    underlying=name,
                    veto_sessions=veto,
                    equal_weight_vwap=True,
                    strategy_id="MIX-DEFAULT-BUY",
                ),
                {**extra, "filters": ["007", "008", "009", "003-primary"], "tf": "3m-resample"},
            )
        )
        books.append(
            _book_row(
                f"STRAT-001/{name}/INDEX-1m",
                run_strat_001(bars_1m, underlying=name, veto_sessions=veto),
                {**extra, "origin": "PROJECT_MIX", "tf": "60m+5m"},
            )
        )
        books.append(
            _book_row(
                f"STRAT-006/{name}/INDEX-1m-resample-2m",
                run_strat_006(bars_1m, underlying=name, veto_sessions=veto),
                {**extra, "origin": "DHAN-DERIVED-tf / PROJECT tape", "tf": "2m-resample", "vix": "DATA_INSUFFICIENT"},
            )
        )

    for name, series in fut_series.items():
        bars_1m = series.get("bars") or []
        bars_3m = resample(bars_1m, 3) if bars_1m else []
        extra = {
            "underlying": name,
            "tape": "FUTIDX",
            "origin": "DHAN-DERIVED-003-closest",
            "bar_count": series.get("bar_count"),
            "security_id": series.get("security_id"),
            "errors": series.get("errors"),
        }
        books.append(
            _book_row(
                f"STRAT-003/{name}/FUTIDX-1m-resample-3m",
                run_strat_003(bars_3m, underlying=name, veto_sessions=veto, strategy_id="STRAT-003"),
                {**extra, "filters": ["007", "008", "009"], "tf": "3m-resample"},
            )
        )

    parked = [
        {
            "book_id": sid,
            "rating": "NOT_CODED",
            "validated": False,
            "promote": False,
            "status": status,
            "reason": why,
            "option_pnl": None,
        }
        for sid, status, why in NOT_CODED
    ]

    report = {
        "as_of_ist": datetime.now(IST).isoformat(),
        "years_requested": years,
        "interval": interval,
        "metrics_claimed": False,
        "research_ready_for_programming": False,
        "keep_current_strategy": True,
        "promote": False,
        "pnl_unit": "UNDERLYING_POINTS_PROXY",
        "option_pnl": None,
        "news_filter": "DATA_INSUFFICIENT",
        "veto_008_days": sorted(veto),
        "futidx": {"ok": fut.get("ok"), "contracts": fut.get("contracts"), "error": fut.get("error")},
        "index_meta": {
            k: {kk: vv for kk, vv in v.items() if kk != "bars"} for k, v in index_series.items()
        },
        "futidx_meta": {
            k: {kk: vv for kk, vv in v.items() if kk != "bars"} for k, v in fut_series.items()
        },
        "books": books,
        "not_coded": parked,
        "note": (
            "Win rates are proxy underlying-point trades, not option fills, not customer P/L. "
            "09 must review. RETUNE_GATE: nothing promotes. Orders refused."
        ),
    }
    out = repo_root() / "data" / "recon"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"BACKTEST_BOOKS_{datetime.now(IST).date().isoformat()}.json"
    slim = json.loads(json.dumps(report, default=str))
    path.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    report["wrote"] = str(path)
    return report
