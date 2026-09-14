"""Param × TF × underlying × tape grid. Always emit a row. NO_PROMOTE."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from backtest_engine.costs import apply_round_trip_many
from backtest_engine.fetch import INDEX_YAML, fetch_chunk, fetch_range, load_cached_series
from backtest_engine.indicators import Bar
from backtest_engine.resample import resample
from backtest_engine.simulate import Trade, simulate_leans
from backtest_engine.tv_ep.adapters import get_adapter, registry_meta
from backtest_engine.tv_ep.catalog import CatalogEntry, load_catalog
from backtest_engine.tv_ep.mapping import (
    after_cost_note,
    count_lean_sides,
    side_label,
    tune_hint,
)
from backtest_engine.tv_ep.regime import regime_doc, regime_labels

IST = timezone(timedelta(hours=5, minutes=30))
TIMEFRAMES = (1, 3, 5, 15)
UNDERLYINGS = ("NIFTY", "SENSEX", "BANKNIFTY")
TAPES = ("INDEX", "PREMIUM")
INDEX_IDS = {name: (sid, seg, inst) for name, sid, seg, inst in INDEX_YAML}


def _event_dates(root: Path) -> tuple[set[str], str]:
    cal = root / "teams" / "06_backtesting" / "docs" / "refs" / "NEWS_CALENDAR.yaml"
    if not cal.is_file():
        return set(), "DATA_INSUFFICIENT"
    text = cal.read_text(encoding="utf-8")
    if "days: []" in text or "status: DATA_INSUFFICIENT" in text:
        dates: set[str] = set()
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("- date:"):
                dates.add(line.split(":", 1)[1].strip())
        if not dates:
            return set(), "DATA_INSUFFICIENT"
        return dates, "RECORDED"
    return set(), "DATA_INSUFFICIENT"


def _trim_years(bars: list[Bar], years: float) -> list[Bar]:
    if not bars or years <= 0:
        return bars
    cutoff = int(bars[-1].ts) - int(years * 365 * 86400)
    return [b for b in bars if b.ts >= cutoff]


def _load_index_bars(
    underlying: str,
    *,
    client: Any,
    fetch_live: bool,
    years: float,
) -> tuple[list[Bar], str]:
    meta = INDEX_IDS.get(underlying)
    if meta is None:
        return [], "DATA_INSUFFICIENT: unknown underlying"
    sid, seg, inst = meta
    cached = load_cached_series(
        security_id=str(sid),
        exchange_segment=seg,
        instrument=inst,
        interval=1,
    )
    if cached:
        return _trim_years(cached, years), ""
    if fetch_live and client is not None:
        blob = fetch_range(
            client,
            security_id=str(sid),
            exchange_segment=seg,
            instrument=inst,
            interval=1,
            years=years,
        )
        bars = list(blob.get("bars") or [])
        if bars:
            return _trim_years(bars, years), ""
        errs = blob.get("errors") or ["empty"]
        return [], f"DATA_INSUFFICIENT: INDEX fetch {underlying}: {errs[0]}"
    return [], f"DATA_INSUFFICIENT: no INDEX 1m cache for {underlying}"


def _long_premium_leans(leans: list[str], contract_side: str) -> list[str]:
    """Buy-only option tape: long the cached contract; opposite lean exits."""
    want = contract_side if contract_side in ("CE", "PE") else "PE"
    out: list[str] = []
    for x in leans:
        if x == want:
            out.append("CE")
        elif x in ("CE", "PE"):
            out.append("PE")
        else:
            out.append("HOLD")
    return out


def _load_premium_tape_bars(underlying: str, root: Path) -> tuple[list[Bar], str, str]:
    """ATM rolling 1m PE from gather_premium_tape JSON (not a fixed strike)."""
    folder = root / "data" / "recon" / "premium_tape"
    if not folder.is_dir():
        return [], "", ""
    merged: dict[int, Bar] = {}
    for path in sorted(folder.glob(f"{underlying}_ATM_1m_*.json")):
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for row in blob.get("pe") or []:
            ts = int(row.get("ts") or 0)
            if not ts:
                continue
            merged[ts] = Bar(
                ts=ts,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row.get("volume") or 0),
            )
    bars = [merged[k] for k in sorted(merged)]
    if bars:
        return bars, "", "PE"
    return [], "", ""


def _load_premium_bars(
    underlying: str,
    root: Path,
    *,
    prefer_strike: Optional[int] = 23500,
) -> tuple[list[Bar], str, str, dict[str, Any]]:
    """Prefer founder NIFTY 23500 PE OPTIDX cache; else universe; else ATM premium_tape."""
    meta: dict[str, Any] = {"underlying": underlying, "source": None}
    uni = root / "data" / "recon" / "itm_strike_universe.json"
    if uni.is_file():
        try:
            blob = json.loads(uni.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            blob = {}
        uni_ul = str(blob.get("underlying") or "NIFTY").upper()
        if uni_ul == underlying:
            legs = list(blob.get("itm_pe") or []) + list(blob.get("itm_ce") or [])
            if prefer_strike:
                legs = sorted(
                    legs,
                    key=lambda leg: (
                        0 if int(leg.get("strike") or 0) == int(prefer_strike) else 1,
                        0 if str(leg.get("security_id")) == "47298" else 1,
                    ),
                )
            for leg in legs:
                sid = str(leg.get("security_id") or "")
                if not sid:
                    continue
                bars = load_cached_series(
                    security_id=sid,
                    exchange_segment="NSE_FNO",
                    instrument="OPTIDX",
                    interval=1,
                )
                if bars:
                    side = "PE" if leg in (blob.get("itm_pe") or []) else "CE"
                    # itm_pe/itm_ce identity: strike 23500 is PE in this universe
                    if int(leg.get("strike") or 0) >= int(blob.get("spot") or 0):
                        side = "PE"
                    elif int(leg.get("strike") or 0) <= int(blob.get("spot") or 0):
                        side = "CE" if leg in (blob.get("itm_ce") or []) else "PE"
                    if any(x.get("security_id") == sid for x in (blob.get("itm_pe") or [])):
                        side = "PE"
                    meta.update(
                        {
                            "source": "ohlc_optidx_cache",
                            "security_id": sid,
                            "strike": leg.get("strike"),
                            "expiry": blob.get("expiry"),
                            "bars": len(bars),
                            "first_ts": bars[0].ts,
                            "last_ts": bars[-1].ts,
                        }
                    )
                    return bars, "", side, meta
    tape_bars, _, side = _load_premium_tape_bars(underlying, root)
    if tape_bars:
        meta.update(
            {
                "source": "premium_tape_atm_pe",
                "bars": len(tape_bars),
                "first_ts": tape_bars[0].ts,
                "last_ts": tape_bars[-1].ts,
                "note": "Rolling ATM PE — not a fixed 23500 contract",
            }
        )
        return tape_bars, "", side or "PE", meta
    if not uni.is_file():
        return [], (
            "DATA_INSUFFICIENT: no OPTIDX premium tape "
            "(missing data/recon/itm_strike_universe.json and premium_tape)"
        ), "", meta
    return [], f"DATA_INSUFFICIENT: no OPTIDX 1m cache for {underlying}", "", meta


def _score_row(trades: list[Trade], event_dates: set[str], *, apply_costs: bool) -> dict[str, Any]:
    costed = apply_round_trip_many(trades) if apply_costs else trades
    score = [t for t in costed if t.session not in event_dates]
    pts = [t.points for t in score]
    wins = sum(1 for p in pts if p > 0)
    n = len(pts)
    return {
        "trade_count": n,
        "wins": wins,
        "losses": n - wins,
        "win_rate": (wins / n) if n else None,
        "gross_points": round(sum(t.points for t in trades), 6),
        "after_cost_points": round(sum(t.points for t in costed), 6) if apply_costs else None,
        "cost_model": "HYPOTHESIS_OPTION_RT_1PCT" if apply_costs else "INDEX_PROXY_NO_OPTION_HAIRCUT",
        "score_sample_points": round(sum(pts), 6) if pts else None,
        "score_sample_n": n,
        "event_trades_excluded": len(trades) - n,
    }


def _regime_split(
    trades: list[Trade], bars: list[Bar], labels: list[str], *, apply_costs: bool
) -> dict[str, Any]:
    by_ts = {b.ts: labels[i] for i, b in enumerate(bars)}
    buckets: dict[str, list[Trade]] = {"TREND": [], "RANGE": [], "UNKNOWN": []}
    for t in trades:
        buckets.setdefault(by_ts.get(t.entry_ts, "UNKNOWN"), []).append(t)
    out: dict[str, Any] = {}
    for name, group in buckets.items():
        if not group:
            continue
        costed = apply_round_trip_many(group) if apply_costs else group
        out[name] = {
            "trade_count": len(group),
            "after_cost_points": round(sum(x.points for x in costed), 6) if apply_costs else None,
            "gross_points": round(sum(x.points for x in group), 6),
        }
    return out


def cell_status(row: dict[str, Any]) -> str:
    if row.get("gap"):
        return "DATA_INSUFFICIENT"
    n = int(row.get("trade_count") or 0)
    after = row.get("after_cost_points")
    rank_pts = after if after is not None else row.get("gross_points")
    if n < 5:
        return "PARK"
    if rank_pts is None or float(rank_pts) <= 0:
        return "TESTED_FAIL"
    return "WATCH"


def _empty_row(
    entry: CatalogEntry,
    *,
    underlying: str,
    tf: int,
    tape: str,
    params: dict[str, float],
    gap: str,
    adapter_gap: str = "",
) -> dict[str, Any]:
    row = {
        "mix_id": entry.mix_id,
        "ep_id": entry.ep_id,
        "adapter": entry.adapter,
        "title": entry.title,
        "name": entry.title,
        "underlying": underlying,
        "tf": f"{tf}m",
        "tape": tape,
        "side": "NONE",
        "buy_ce_signals": 0,
        "buy_pe_signals": 0,
        "exit_flat_signals": 0,
        "buy_ce_trades": 0,
        "buy_pe_trades": 0,
        "params": params,
        "gap": gap,
        "trade_count": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": None,
        "gross_points": None,
        "after_cost_points": None,
        "score_sample_points": None,
        "promotion": "NO_PROMOTE",
        "customer_slash": False,
        "unvalidated": True,
        "tv_tester_clone": False,
    }
    row["status"] = cell_status(row)
    row["after_cost_note"] = after_cost_note(row)
    row["tune_hint"] = tune_hint(row, adapter_gap=adapter_gap)
    return row


def run_tv_ep_grid(
    client: Any = None,
    *,
    entries: Optional[list[CatalogEntry]] = None,
    timeframes: tuple[int, ...] = TIMEFRAMES,
    underlyings: tuple[str, ...] = ("NIFTY", "SENSEX"),
    tapes: tuple[str, ...] = TAPES,
    bars_by_key: Optional[dict[tuple[str, str], list[Bar]]] = None,
    fetch_live: bool = False,
    years: float = 0.25,
    write: bool = False,
    use_009: bool = False,
    prefer_strike: Optional[int] = None,
    root: Optional[Path] = None,
) -> dict[str, Any]:
    """Run the factory grid. Fixture bars via bars_by_key[(underlying, tape)].

    fetch_live hits Dhan history only when True (CLI --refresh-cache). Default is cache/fixture.
    use_009 flatten/skip is off for short fixture windows; enable on long INDEX books.
    prefer_strike is used only when OPTIDX universe cache exists — never invent 23500 PE.
    """
    from datetime import datetime

    from dhan_client.config import repo_root

    from backtest_engine.tv_ep.board import write_board

    base = root or repo_root()
    if fetch_live and client is not None and bars_by_key is None:
        end = datetime.now(IST).replace(hour=15, minute=40, second=0, microsecond=0)
        start = end - timedelta(days=max(21, int(years * 365)))
        for name, sid, seg, inst in INDEX_YAML:
            fetch_chunk(
                client,
                security_id=str(sid),
                exchange_segment=seg,
                instrument=inst,
                interval=1,
                from_dt=start,
                to_dt=end,
            )
        # Founder 23500 PE (itm_strike_universe sid 47298) — history fetch only.
        fetch_chunk(
            client,
            security_id="47298",
            exchange_segment="NSE_FNO",
            instrument="OPTIDX",
            interval=1,
            from_dt=start,
            to_dt=end,
        )
    catalog = entries if entries is not None else load_catalog(base / "refernece_tradingview" / "editors_picks" / "catalog.json")
    event_dates, event_status = _event_dates(base)
    rows: list[dict[str, Any]] = []
    tape_cache: dict[tuple[str, str], tuple[list[Bar], str, str]] = {}
    tapes_used: dict[str, Any] = {}

    ul_list = list(underlyings)
    if bars_by_key is not None:
        extra = sorted({k[0] for k in bars_by_key if k[0] not in ul_list})
        ul_list.extend(extra)
    elif "BANKNIFTY" not in ul_list:
        # Include BANKNIFTY only when INDEX cache exists (founder rule).
        cached_bn, _ = _load_index_bars("BANKNIFTY", client=client, fetch_live=False, years=years)
        if cached_bn:
            ul_list.append("BANKNIFTY")

    for ul in ul_list:
        for tape in tapes:
            key = (ul, tape)
            if bars_by_key is not None and key in bars_by_key:
                side = "PE" if tape == "PREMIUM" else ""
                tape_cache[key] = (bars_by_key[key], "", side)
                tapes_used[f"{ul}/{tape}"] = {
                    "source": "fixture",
                    "bars": len(bars_by_key[key]),
                }
            elif bars_by_key is not None:
                tape_cache[key] = ([], f"DATA_INSUFFICIENT: fixture missing {ul}/{tape}", "")
                tapes_used[f"{ul}/{tape}"] = {"source": None, "bars": 0}
            elif tape == "INDEX":
                bars, gap = _load_index_bars(
                    ul, client=client, fetch_live=fetch_live, years=years
                )
                tape_cache[key] = (bars, gap, "")
                tapes_used[f"{ul}/{tape}"] = {
                    "source": "ohlc_index_cache" if bars else None,
                    "security_id": INDEX_IDS.get(ul, ("", "", ""))[0],
                    "bars": len(bars),
                    "first_ts": bars[0].ts if bars else None,
                    "last_ts": bars[-1].ts if bars else None,
                    "gap": gap or None,
                    "trim_years": years,
                }
            else:
                bars, gap, side, meta = _load_premium_bars(
                    ul, base, prefer_strike=prefer_strike
                )
                tape_cache[key] = (bars, gap, side)
                tapes_used[f"{ul}/{tape}"] = {**meta, "gap": gap or None}

    for entry in catalog:
        adapter = get_adapter(entry.adapter)
        grids = adapter.param_grid(entry) if adapter.ported else [{}]
        for ul in ul_list:
            for tape in tapes:
                bars_1m, tape_gap, contract_side = tape_cache[(ul, tape)]
                for tf in timeframes:
                    for params in grids:
                        agap = adapter.gap or ""
                        if not adapter.ported or adapter.leans is None:
                            rows.append(
                                _empty_row(
                                    entry,
                                    underlying=ul,
                                    tf=tf,
                                    tape=tape,
                                    params=params,
                                    gap=(
                                        "DATA_INSUFFICIENT: unported Editor Pick "
                                        f"{entry.ep_id} — stub adapter, no Python port"
                                    ),
                                    adapter_gap=agap,
                                )
                            )
                            continue
                        if tape_gap or len(bars_1m) < 80:
                            rows.append(
                                _empty_row(
                                    entry,
                                    underlying=ul,
                                    tf=tf,
                                    tape=tape,
                                    params=params,
                                    gap=tape_gap
                                    or f"DATA_INSUFFICIENT: {len(bars_1m)} bars < 80",
                                    adapter_gap=agap,
                                )
                            )
                            continue
                        bars = resample(bars_1m, tf)
                        if len(bars) < 60:
                            rows.append(
                                _empty_row(
                                    entry,
                                    underlying=ul,
                                    tf=tf,
                                    tape=tape,
                                    params=params,
                                    gap=f"DATA_INSUFFICIENT: {tf}m resample n={len(bars)}",
                                    adapter_gap=agap,
                                )
                            )
                            continue
                        mapped_leans = adapter.leans(bars, params)
                        side_counts = count_lean_sides(mapped_leans)
                        sim_leans = mapped_leans
                        if tape == "PREMIUM":
                            # Cached OPTIDX is one contract: opposite lean = exit, not a fake other strike.
                            sim_leans = _long_premium_leans(
                                mapped_leans, contract_side or "PE"
                            )
                        trades = simulate_leans(
                            bars,
                            sim_leans,
                            strategy_id=entry.mix_id,
                            underlying=ul,
                            use_009=use_009,
                        )
                        labels = regime_labels(bars)
                        apply_costs = tape == "PREMIUM"
                        scored = _score_row(trades, event_dates, apply_costs=apply_costs)
                        buy_ce_tr = sum(1 for t in trades if t.side == "CE")
                        buy_pe_tr = sum(1 for t in trades if t.side == "PE")
                        # INDEX: CE/PE trades are BUY_CE / BUY_PE proxy. PREMIUM: trades follow cached contract.
                        if tape == "INDEX":
                            ce_n, pe_n = buy_ce_tr, buy_pe_tr
                        else:
                            ce_n = side_counts["buy_ce_signals"]
                            pe_n = side_counts["buy_pe_signals"]
                        row = {
                            "mix_id": entry.mix_id,
                            "ep_id": entry.ep_id,
                            "adapter": entry.adapter,
                            "title": entry.title,
                            "name": entry.title,
                            "underlying": ul,
                            "tf": f"{tf}m",
                            "tape": tape,
                            "premium_contract_side": contract_side or None,
                            "side": side_label(
                                buy_ce_n=ce_n,
                                buy_pe_n=pe_n,
                                exit_n=side_counts["exit_flat_signals"],
                            ),
                            "buy_ce_signals": side_counts["buy_ce_signals"],
                            "buy_pe_signals": side_counts["buy_pe_signals"],
                            "exit_flat_signals": side_counts["exit_flat_signals"],
                            "buy_ce_trades": buy_ce_tr if tape == "INDEX" else (
                                buy_ce_tr if (contract_side or "PE") == "CE" else 0
                            ),
                            "buy_pe_trades": buy_pe_tr if tape == "INDEX" else (
                                buy_ce_tr if (contract_side or "PE") == "PE" else buy_pe_tr
                            ),
                            "params": params,
                            "gap": None,
                            "regime_split": _regime_split(
                                trades, bars, labels, apply_costs=apply_costs
                            ),
                            "promotion": "NO_PROMOTE",
                            "customer_slash": False,
                            "unvalidated": True,
                            "tv_tester_clone": False,
                            **scored,
                        }
                        row["status"] = cell_status(row)
                        row["after_cost_note"] = after_cost_note(row)
                        row["tune_hint"] = tune_hint(row, adapter_gap=agap)
                        rows.append(row)

    report = {
        "title": "TV Editor Picks factory grid",
        "mode": "PAPER",
        "promotion": "NO_PROMOTE",
        "orders": "refused",
        "research_ready_for_programming": False,
        "id_namespace": "MIX-TV-EP-*",
        "keep_all_strat_001_014": True,
        "honesty": [
            "Paper ranks only. Not customer /. Not a win-rate claim.",
            "INDEX points ≠ option P/L. PREMIUM tape only when OPTIDX cache exists.",
            "Option 1% haircut applies to PREMIUM tape only. INDEX is proxy points.",
            "NEWS_CALENDAR empty → SCORE_SAMPLE not a true NORMAL set.",
            "WATCH ≠ promote. TESTED_FAIL / PARK / DATA_INSUFFICIENT stay on the board.",
        ],
        "regime": regime_doc(),
        "event_calendar": event_status,
        "adapters": registry_meta(),
        "catalog": [e.as_meta() for e in catalog],
        "tapes_used": tapes_used,
        "prefer_strike": prefer_strike,
        "timeframes": [f"{t}m" for t in timeframes],
        "cells": rows,
        "counts": {
            "cells": len(rows),
            "WATCH": sum(1 for r in rows if r["status"] == "WATCH"),
            "TESTED_FAIL": sum(1 for r in rows if r["status"] == "TESTED_FAIL"),
            "PARK": sum(1 for r in rows if r["status"] == "PARK"),
            "DATA_INSUFFICIENT": sum(1 for r in rows if r["status"] == "DATA_INSUFFICIENT"),
        },
        "updated_at": datetime.now(tz=IST).isoformat(),
    }
    if write:
        write_board(report, base)
    return report
