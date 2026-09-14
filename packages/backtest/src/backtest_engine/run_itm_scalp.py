"""Run MIX-ITM-OPT-SCALP on OPTIDX 1m (PE yellow + CE blue). PAPER. NO_PROMOTE."""

from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.fetch import fetch_chunk
from backtest_engine.itm_scalp import (
    LAYER,
    MIX_ID,
    ORIGIN,
    ItmScalpParams,
    diamond_overlap,
    simulate_itm_scalp_long,
    sltp_grid_scan,
    summarize_lot_pnl,
)

IST = timezone(timedelta(hours=5, minutes=30))

DEFAULT_PE = {
    "security_id": "47298",
    "strike": 23500,
    "side": "PE",
    "diamond": "yellow",
}
DEFAULT_CE = {
    "security_id": "47285",
    "strike": 23200,
    "side": "CE",
    "diamond": "blue",
}
DEFAULT_EXPIRY = "2026-09-15"
DEFAULT_UNDERLYING = "NIFTY"
DEFAULT_SEGMENT = "NSE_FNO"
DEFAULT_INSTRUMENT = "OPTIDX"


def _log(msg: str) -> None:
    print(f"[itm-scalp] {msg}", file=sys.stderr, flush=True)


def _lot_size_from_master(client: DhanClient, security_id: str) -> tuple[Optional[int], str]:
    try:
        text = client.instruments.fetch_scrip_master_text(detailed=True)
    except Exception as exc:  # noqa: BLE001
        return None, f"instrument_master_error:{exc}"
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if str(row.get("SECURITY_ID") or "").strip() != str(security_id):
            continue
        raw = row.get("LOT_SIZE")
        try:
            return int(float(raw)), "instrument_master_detailed"
        except (TypeError, ValueError):
            return None, f"bad_lot_size:{raw!r}"
    return None, "security_id_not_in_master"


def _parse_dt(s: str, *, end: bool = False) -> datetime:
    # YYYY-MM-DD
    d = datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=IST)
    if end:
        return d.replace(hour=15, minute=30, second=0, microsecond=0)
    return d.replace(hour=9, minute=15, second=0, microsecond=0)


def _write_outputs(payload: dict[str, Any]) -> dict[str, str]:
    recon = repo_root() / "data" / "recon"
    recon.mkdir(parents=True, exist_ok=True)
    mock = repo_root() / "apps" / "web" / "public" / "mock"
    mock.mkdir(parents=True, exist_ok=True)
    paths = {
        "recon": str(recon / "itm_scalp_backtest.json"),
        "mock": str(mock / "itm_scalp_backtest.json"),
    }
    text = json.dumps(payload, indent=2)
    Path(paths["recon"]).write_text(text, encoding="utf-8")
    Path(paths["mock"]).write_text(text, encoding="utf-8")
    return paths


def _leg(
    client: DhanClient,
    *,
    meta: dict[str, Any],
    expiry: str,
    underlying: str,
    from_dt: datetime,
    to_dt: datetime,
    lots: int,
    params: ItmScalpParams,
    run_sltp: bool,
) -> dict[str, Any]:
    sid = str(meta["security_id"])
    side = str(meta["side"])
    strike = int(meta["strike"])
    _log(f"fetch 1m {side} {strike} sid={sid} {from_dt.date()}→{to_dt.date()}")
    bars, err = fetch_chunk(
        client,
        security_id=sid,
        exchange_segment=DEFAULT_SEGMENT,
        instrument=DEFAULT_INSTRUMENT,
        interval=1,
        from_dt=from_dt,
        to_dt=to_dt,
        oi=True,
    )
    lot_size, lot_src = _lot_size_from_master(client, sid)
    out: dict[str, Any] = {
        "diamond": meta.get("diamond"),
        "contract": {
            "underlying": underlying,
            "side": side,
            "strike": strike,
            "expiry": expiry,
            "security_id": sid,
            "exchange_segment": DEFAULT_SEGMENT,
            "instrument": DEFAULT_INSTRUMENT,
            "interval_min": 1,
            "display_name": f"{underlying} {expiry} {strike} {side}",
        },
        "window": {
            "from": from_dt.isoformat(),
            "to": to_dt.isoformat(),
            "bar_count": len(bars),
            "fetch_error": err,
        },
        "lot_size_source": lot_src,
    }
    if err and not bars:
        out["ok"] = False
        out["reason"] = f"DATA_INSUFFICIENT:{err}"
        return out
    if lot_size is None:
        out["ok"] = False
        out["reason"] = f"DATA_INSUFFICIENT:{lot_src}"
        return out

    trades = simulate_itm_scalp_long(
        bars,
        underlying=underlying,
        side=side,
        params=params,
    )
    summary = summarize_lot_pnl(trades, lot_size=lot_size, lots=lots)
    out["ok"] = True
    out["reason"] = "ok"
    out["summary"] = {
        "headline": (
            f"{MIX_ID} · {underlying} {strike} {side} · "
            f"{lots} lot × {lot_size} · 1m"
        ),
        "gross_pnl_inr": summary["gross_pnl_inr"],
        "after_cost_pnl_inr": summary["after_cost_pnl_inr"],
        "gross_points": summary["gross_points"],
        "after_cost_points": summary["after_cost_points"],
        "trade_count": summary["trade_count"],
        "wins": summary["wins"],
        "losses": summary["losses"],
        "win_rate": summary["win_rate"],
        "lot_size": lot_size,
        "lots": lots,
        "quantity": summary["quantity"],
    }
    out["cost_model"] = summary["cost_model"]
    out["trades"] = summary["trades"]
    if run_sltp:
        grid = sltp_grid_scan(
            bars,
            underlying=underlying,
            side=side,
            lot_size=lot_size,
            lots=lots,
            base=params,
        )
        out["sltp_grid_top"] = grid[:8]
        out["sltp_best"] = grid[0] if grid else None
    return out


def run_itm_scalp(
    client: DhanClient,
    *,
    from_date: str = "2026-08-01",
    to_date: str = "2026-09-12",
    lots: int = 1,
    expiry: str = DEFAULT_EXPIRY,
    underlying: str = DEFAULT_UNDERLYING,
    rsi_entry: float = 70.0,
    rsi_exit: float = 68.0,
    poc_mode: str = "session_vwap",
    ma_mode: str = "cross_event",
    fill_mode: str = "next_open",
    exit_mode: str = "ma_or_rsi",
    max_entries_per_session: Optional[int] = None,
    stop_loss_frac: Optional[float] = 0.15,
    target_frac: Optional[float] = 0.30,
    run_sltp_grid: bool = True,
    write: bool = True,
) -> dict[str, Any]:
    from_dt = _parse_dt(from_date)
    to_dt = _parse_dt(to_date, end=True)
    params = ItmScalpParams(
        rsi_entry_th=rsi_entry,
        rsi_exit_th=rsi_exit,
        poc_mode=poc_mode,  # type: ignore[arg-type]
        ma_mode=ma_mode,  # type: ignore[arg-type]
        fill_mode=fill_mode,  # type: ignore[arg-type]
        exit_mode=exit_mode,  # type: ignore[arg-type]
        max_entries_per_session=max_entries_per_session,
        stop_loss_frac=stop_loss_frac,
        target_frac=target_frac,
    )

    pe = _leg(
        client,
        meta=DEFAULT_PE,
        expiry=expiry,
        underlying=underlying,
        from_dt=from_dt,
        to_dt=to_dt,
        lots=lots,
        params=params,
        run_sltp=run_sltp_grid,
    )
    ce = _leg(
        client,
        meta=DEFAULT_CE,
        expiry=expiry,
        underlying=underlying,
        from_dt=from_dt,
        to_dt=to_dt,
        lots=lots,
        params=params,
        run_sltp=run_sltp_grid,
    )

    from backtest_engine.simulate import Trade

    def _as_trades(leg: dict[str, Any]) -> list[Trade]:
        out: list[Trade] = []
        for t in leg.get("trades") or []:
            out.append(
                Trade(
                    strategy_id=t["strategy_id"],
                    underlying=t["underlying"],
                    side=t["side"],
                    entry_ts=t["entry_ts"],
                    exit_ts=t["exit_ts"],
                    entry_px=t["entry_px"],
                    exit_px=t["exit_px"],
                    points=t["points"],
                    reason=t["reason"],
                    session=t["session"],
                )
            )
        return out

    diamonds = diamond_overlap(_as_trades(pe), _as_trades(ce)) if pe.get("ok") and ce.get("ok") else None

    pe_pnl = (pe.get("summary") or {}).get("gross_pnl_inr") or 0
    ce_pnl = (ce.get("summary") or {}).get("gross_pnl_inr") or 0
    pe_ac = (pe.get("summary") or {}).get("after_cost_pnl_inr") or 0
    ce_ac = (ce.get("summary") or {}).get("after_cost_pnl_inr") or 0

    payload: dict[str, Any] = {
        "mix_id": MIX_ID,
        "layer": LAYER,
        "origin": ORIGIN,
        "promotion": "NO_PROMOTE",
        "orders": "refused",
        "verdict": "UNVALIDATED",
        "ok": bool(pe.get("ok") or ce.get("ok")),
        "params": {
            "rsi_length": params.rsi_length,
            "rsi_entry_th": params.rsi_entry_th,
            "rsi_exit_th": params.rsi_exit_th,
            "ema_fast_len": params.ema_fast_len,
            "wma_slow_len": params.wma_slow_len,
            "ema_base_len": params.ema_base_len,
            "poc_mode": params.poc_mode,
            "ma_mode": params.ma_mode,
            "fill_mode": params.fill_mode,
            "exit_mode": params.exit_mode,
            "max_entries_per_session": params.max_entries_per_session,
            "stop_loss_frac": params.stop_loss_frac,
            "target_frac": params.target_frac,
            "note": (
                "Standard ITM Option Scalping (Pine): session VWAP(close), "
                "EMA3×WMA21 crossover entry, MA cross-down or RSI<exit, "
                "optional % SL/TP. Fill=next bar open (TV strategy default)."
            ),
        },
        "api_honesty": [
            "Dhan MCP/API gives OPTIDX 1m OHLC (+OI) only — no chart pane export.",
            "Indicators computed client-side to match this Pine: RSI14, EMA3, WMA21, EMA21, session VWAP(close).",
            "Yellow/blue legs = same rules on PE 23500 and CE 23200.",
        ],
        "fix_note": (
            "Strategy source: Standard ITM Option Scalping Strategy Pine "
            "(session VWAP + crossover + 15/30 SL/TP)."
        ),
        "summary": {
            "headline": (
                f"{MIX_ID} · Aug→Sep · yellow PE {DEFAULT_PE['strike']} + "
                f"blue CE {DEFAULT_CE['strike']} · 1 lot"
            ),
            "pe_gross_pnl_inr": pe_pnl,
            "ce_gross_pnl_inr": ce_pnl,
            "combined_gross_pnl_inr": round(pe_pnl + ce_pnl, 2),
            "pe_after_cost_pnl_inr": pe_ac,
            "ce_after_cost_pnl_inr": ce_ac,
            "combined_after_cost_pnl_inr": round(pe_ac + ce_ac, 2),
            "from": from_dt.isoformat(),
            "to": to_dt.isoformat(),
        },
        "legs": {"PE_yellow": pe, "CE_blue": ce},
        "diamonds": diamonds,
        "honesty": [
            "PAPER / research only — not a customer promote.",
            "Statutory brokerage/STT UNKNOWN; after-cost uses HYPOTHESIS 1% RT slip.",
            "KEEP_ALL: does not replace STRAT-001–014.",
            "No live orders.",
        ],
    }
    if write:
        paths = _write_outputs(payload)
        payload["paths"] = paths
        _log(f"wrote {paths['recon']}")
    return payload
