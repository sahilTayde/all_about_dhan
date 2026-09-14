"""CLI: python -m backtest_engine.run_tv_ep_grid  (also tv-ep-grid)."""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.indicators import Bar
from backtest_engine.tv_ep.grid import run_tv_ep_grid


def synthetic_bars(n: int = 240, *, trend: bool = True) -> list[Bar]:
    """IST-session-ish 1m bars. Fixture only — not Dhan tape."""
    from datetime import datetime, timedelta, timezone

    ist = timezone(timedelta(hours=5, minutes=30))
    start = datetime(2026, 8, 3, 9, 15, tzinfo=ist)
    out: list[Bar] = []
    px = 24000.0
    for i in range(n):
        ts = int((start + timedelta(minutes=i)).timestamp())
        drift = 3.0 if (trend and i < n // 2) else (-2.5 if trend and i >= n // 2 else 0.2)
        osc = 12.0 if (i // 20) % 2 == 0 else -8.0
        px = px + drift + (osc * 0.05)
        out.append(
            Bar(
                ts=ts,
                open=px - 1.0,
                high=px + 4.0,
                low=px - 4.0,
                close=px,
                volume=100.0,
            )
        )
    return out


def fixture_bars() -> dict[tuple[str, str], list[Bar]]:
    idx = synthetic_bars(280, trend=True)
    prem = [
        Bar(
            ts=b.ts,
            open=max(20.0, (b.open - 23900) * 0.4 + 80),
            high=max(20.0, (b.high - 23900) * 0.4 + 82),
            low=max(15.0, (b.low - 23900) * 0.4 + 78),
            close=max(20.0, (b.close - 23900) * 0.4 + 80),
            volume=b.volume,
        )
        for b in idx
    ]
    return {
        ("NIFTY", "INDEX"): idx,
        ("NIFTY", "PREMIUM"): prem,
        ("SENSEX", "INDEX"): idx,
        ("SENSEX", "PREMIUM"): prem,
    }


def run(
    *,
    dry_run: bool = True,
    fetch_live: bool = False,
    write: bool = True,
    fixture: bool = False,
    client: Optional[Any] = None,
) -> dict[str, Any]:
    bars = fixture_bars() if (dry_run or fixture) else None
    live_client = client
    if fetch_live and live_client is None:
        live_client = DhanClient(dry_run=False)
    return run_tv_ep_grid(
        live_client,
        bars_by_key=bars,
        fetch_live=bool(fetch_live and not dry_run),
        write=write,
        use_009=not (dry_run or fixture),
        root=repo_root(),
    )


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="TV-EP factory grid. PAPER. NO_PROMOTE.")
    p.add_argument("--fixture", action="store_true", help="Synthetic bars (CI).")
    p.add_argument("--write", action="store_true", help="Write data/recon board.")
    args = p.parse_args(argv)
    report = run(dry_run=True, fetch_live=False, write=args.write, fixture=True)
    slim = {k: v for k, v in report.items() if k != "cells"}
    slim["cells_head"] = [
        {
            "mix_id": r["mix_id"],
            "tape": r["tape"],
            "tf": r["tf"],
            "underlying": r["underlying"],
            "status": r["status"],
            "trade_count": r["trade_count"],
            "after_cost_points": r.get("after_cost_points"),
            "gap": r.get("gap"),
        }
        for r in (report.get("cells") or [])[:12]
    ]
    print(json.dumps(slim, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
