"""Paper champion board: VWAP-assumed backtest + ranked leaderboard for Tuesday watch.

PAPER only. NO_PROMOTE. Live Dhan orders refused.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.config import load_settings, repo_root

from backtest_engine.clocks import session_date_ist
from backtest_engine.costs import apply_round_trip
from backtest_engine.fetch import fetch_chunk
from backtest_engine.indicators import Bar
from backtest_engine.itm_champions import CHAMPIONS, champions_meta
from backtest_engine.resample import resample
from backtest_engine.simulate import Trade

IST = timezone(timedelta(hours=5, minutes=30))
LOT = 65


def _log(msg: str) -> None:
    print(f"[champions] {msg}", file=sys.stderr, flush=True)


def load_bars(client: DhanClient, sid: str, start: datetime, end: datetime) -> list[Bar]:
    bars, err = fetch_chunk(
        client,
        security_id=str(sid),
        exchange_segment="NSE_FNO",
        instrument="OPTIDX",
        interval=1,
        from_dt=start,
        to_dt=end,
        oi=True,
    )
    if err and not bars:
        _log(f"fail {sid}: {err}")
        return []
    return bars


def simulate(
    bars: list[Bar],
    entry: list[bool],
    exit_: list[bool],
    *,
    side: str,
    strategy_id: str,
    sl: Optional[float],
    tp: Optional[float],
) -> list[Trade]:
    trades: list[Trade] = []
    in_pos = False
    entry_px = entry_ts = 0.0
    stop = target = None
    for i, bar in enumerate(bars):
        sess = session_date_ist(bar.ts)
        if in_pos:
            reason = xpx = xts = None
            if stop is not None and bar.low <= stop:
                reason, xts, xpx = "stop_loss", bar.ts, stop
            elif target is not None and bar.high >= target:
                reason, xts, xpx = "target", bar.ts, target
            elif exit_[i]:
                if i + 1 < len(bars):
                    reason, xts, xpx = "exit_signal", bars[i + 1].ts, bars[i + 1].open
                else:
                    reason, xts, xpx = "exit_signal", bar.ts, bar.close
            if reason:
                trades.append(
                    Trade(
                        strategy_id,
                        "NIFTY",
                        side,
                        int(entry_ts),
                        int(xts),
                        float(entry_px),
                        float(xpx),
                        float(xpx) - float(entry_px),
                        reason,
                        sess,
                    )
                )
                in_pos = False
                stop = target = None
            continue
        if entry[i]:
            if i + 1 >= len(bars):
                break
            entry_ts, entry_px = bars[i + 1].ts, bars[i + 1].open
            in_pos = True
            stop = entry_px * (1 - sl) if sl else None
            target = entry_px * (1 + tp) if tp else None
    if in_pos and bars:
        b = bars[-1]
        trades.append(
            Trade(
                strategy_id,
                "NIFTY",
                side,
                int(entry_ts),
                b.ts,
                float(entry_px),
                b.close,
                b.close - float(entry_px),
                "series_end",
                session_date_ist(b.ts),
            )
        )
    return trades


def streak_stats(points: list[float]) -> dict[str, Any]:
    """Current streak + max win/loss streaks from chronological P/L points."""
    cur = 0
    cur_kind = None  # "W" | "L"
    max_w = max_l = 0
    run = 0
    run_kind = None
    for p in points:
        kind = "W" if p > 0 else "L"
        if run_kind == kind:
            run += 1
        else:
            run_kind = kind
            run = 1
        if kind == "W":
            max_w = max(max_w, run)
        else:
            max_l = max(max_l, run)
        cur_kind = kind
        cur = run if run_kind == kind else 1
    # recompute current from end
    if not points:
        return {
            "current_streak": 0,
            "current_streak_kind": None,
            "max_win_streak": 0,
            "max_loss_streak": 0,
        }
    last = "W" if points[-1] > 0 else "L"
    n = 0
    for p in reversed(points):
        k = "W" if p > 0 else "L"
        if k != last:
            break
        n += 1
    return {
        "current_streak": n,
        "current_streak_kind": last,
        "max_win_streak": max_w,
        "max_loss_streak": max_l,
    }


def board_row(
    *,
    champ_id: str,
    name: str,
    family: str,
    tf: str,
    side: str,
    strike: int,
    security_id: str,
    trades: list[Trade],
) -> dict[str, Any]:
    costed = [apply_round_trip(t) for t in trades]
    pts = [t.points for t in trades]
    wins = sum(1 for p in pts if p > 0)
    losses = len(pts) - wins
    gross = sum(pts) * LOT
    after = sum(t.points for t in costed) * LOT
    streaks = streak_stats(pts)
    return {
        "champion_id": champ_id,
        "name": name,
        "family": family,
        "tf": tf,
        "side": side,
        "strike": strike,
        "security_id": security_id,
        "lot": LOT,
        "trade_count": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / len(trades)) if trades else None,
        "success_pct": round(100.0 * wins / len(trades), 1) if trades else None,
        "gross_pnl_inr": round(gross, 2),
        "after_cost_pnl_inr": round(after, 2),
        **streaks,
        "recent_trades": [
            {
                "session": t.session,
                "entry_px": t.entry_px,
                "exit_px": t.exit_px,
                "points": round(t.points, 4),
                "pnl_inr_1lot": round(t.points * LOT, 2),
                "reason": t.reason,
                "win": t.points > 0,
            }
            for t in trades[-8:]
        ],
    }


def pick_watch_contracts(uni: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Near-spot ITM PE×3 + ITM CE×2 for paper board (not all 20 — readable Tuesday board)."""
    pe = sorted(uni["itm_pe"], key=lambda x: x["strike"])
    ce = sorted(uni["itm_ce"], key=lambda x: -x["strike"])
    # closest ITM PE (lowest PE strike >= spot) first three, closest CE first two
    watches = [("PE", x) for x in pe[:3]] + [("CE", x) for x in ce[:2]]
    return watches


def aggregate_by_champion(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from collections import defaultdict

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        buckets[r["champion_id"]].append(r)

    out: list[dict[str, Any]] = []
    for cid, group in buckets.items():
        trades = sum(g["trade_count"] for g in group)
        wins = sum(g["wins"] for g in group)
        after = sum(g["after_cost_pnl_inr"] for g in group)
        gross = sum(g["gross_pnl_inr"] for g in group)
        # stitch streaks roughly from last legs' recent points order is per-contract —
        # use win_rate + max streaks across contracts
        max_w = max(g["max_win_streak"] for g in group)
        max_l = max(g["max_loss_streak"] for g in group)
        # current streak: take the contract with most recent non-zero trades' current
        cur = max(group, key=lambda g: g["trade_count"])
        out.append(
            {
                "champion_id": cid,
                "name": group[0]["name"],
                "family": group[0]["family"],
                "tf": group[0]["tf"],
                "contracts": len(group),
                "trade_count": trades,
                "wins": wins,
                "losses": trades - wins,
                "win_rate": (wins / trades) if trades else None,
                "success_pct": round(100.0 * wins / trades, 1) if trades else None,
                "gross_pnl_inr": round(gross, 2),
                "after_cost_pnl_inr": round(after, 2),
                "max_win_streak": max_w,
                "max_loss_streak": max_l,
                "current_streak": cur["current_streak"],
                "current_streak_kind": cur["current_streak_kind"],
                "legs": group,
            }
        )
    out.sort(key=lambda r: (r["after_cost_pnl_inr"], r["success_pct"] or 0), reverse=True)
    for i, row in enumerate(out, start=1):
        row["rank"] = i
    return out


def main() -> int:
    root = repo_root()
    uni = json.loads((root / "data" / "recon" / "itm_strike_universe.json").read_text())
    client = DhanClient(load_settings())
    start = datetime(2026, 8, 1, 9, 15, tzinfo=IST)
    end = datetime(2026, 9, 12, 15, 30, tzinfo=IST)

    watches = pick_watch_contracts(uni)
    cache: dict[str, list[Bar]] = {}
    for side, meta in watches:
        sid = str(meta["security_id"])
        _log(f"fetch {side} {meta['strike']} sid={sid}")
        cache[sid] = load_bars(client, sid, start, end)
        _log(f"  bars={len(cache[sid])}")
        time.sleep(0.25)

    leg_rows: list[dict[str, Any]] = []
    for champ in CHAMPIONS:
        for side, meta in watches:
            if champ.prefer_side != "BOTH" and champ.prefer_side != side:
                continue
            sid = str(meta["security_id"])
            bars_1m = cache.get(sid) or []
            if len(bars_1m) < 100:
                continue
            bars = bars_1m if champ.tf_minutes == 1 else resample(bars_1m, champ.tf_minutes)
            if len(bars) < 40:
                continue
            entry, exit_ = champ.signals(bars)
            trades = simulate(
                bars,
                entry,
                exit_,
                side=side,
                strategy_id=champ.id,
                sl=champ.sl,
                tp=champ.tp,
            )
            leg_rows.append(
                board_row(
                    champ_id=champ.id,
                    name=champ.name,
                    family=champ.family,
                    tf=f"{champ.tf_minutes}m",
                    side=side,
                    strike=int(meta["strike"]),
                    security_id=sid,
                    trades=trades,
                )
            )

    leaderboard = aggregate_by_champion(leg_rows)
    champion = leaderboard[0] if leaderboard else None

    report = {
        "title": "ITM champion paper leaderboard",
        "mode": "PAPER",
        "promotion": "NO_PROMOTE",
        "orders": "refused",
        "live_auto_trade": "REFUSED",
        "lot": LOT,
        "vwap_mode": (
            "IST session VWAP — use OPTIDX volume when >0; "
            "equal-weight assume on zero-volume bars (offline / sparse tape)."
        ),
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "spot": uni["spot"],
        "expiry": uni["expiry"],
        "watch_contracts": [
            {"side": s, "strike": m["strike"], "security_id": m["security_id"]}
            for s, m in watches
        ],
        "champions_catalog": champions_meta(),
        "leaderboard": leaderboard,
        "champion_of_board": (
            {
                "champion_id": champion["champion_id"],
                "name": champion["name"],
                "success_pct": champion["success_pct"],
                "after_cost_pnl_inr": champion["after_cost_pnl_inr"],
                "current_streak": champion["current_streak"],
                "current_streak_kind": champion["current_streak_kind"],
            }
            if champion
            else None
        ),
        "tuesday_runbook": {
            "status": "CODE_READY",
            "do": [
                "Start market-hours PAPER watch only (no live Super Orders).",
                "Prefer ITM PE near spot for MIX-CHAMP-EMA-ST-* first.",
                "Compare VWAP-gated champions once live volume fills session VWAP.",
                "Refresh this board from recon JSON / API — ranks by after-cost P/L.",
            ],
            "do_not": [
                "Do not auto-place Dhan orders.",
                "Do not promote to STRAT/customer default.",
                "Do not trust 1m cross families from strike sweep (bled after costs).",
            ],
            "cli": "PYTHONPATH=packages/backtest/src:packages/dhan-client/src python -m backtest_engine.run_itm_champions",
        },
        "next_action_items": [
            "1) Freeze top Tuesday paper recipe after 1 live session of board evidence.",
            "2) Walk-forward same champions on another expiry / OOS week.",
            "3) Only then discuss longer paper book — still NO_PROMOTE / no live orders.",
        ],
        "honesty": [
            "This board is historical Aug–Sep lab ranks until live paper ticks overwrite it.",
            "Assumed VWAP ≠ exchange-printed VWAP; live session volume improves the gate.",
            "Multiple-testing bias: sweep already peeked at these families.",
        ],
        "updated_at": datetime.now(tz=IST).isoformat(),
    }

    out = root / "data" / "recon" / "itm_champion_leaderboard.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    mock = root / "apps" / "web" / "public" / "mock" / "itm_champion_leaderboard.json"
    mock.parent.mkdir(parents=True, exist_ok=True)
    mock.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _log(f"wrote {out}")

    slim = {
        "champion_of_board": report["champion_of_board"],
        "leaderboard_top": [
            {
                "rank": r["rank"],
                "id": r["champion_id"],
                "success_pct": r["success_pct"],
                "after_cost_pnl_inr": r["after_cost_pnl_inr"],
                "streak": f"{r['current_streak_kind'] or '-'}{r['current_streak']}",
                "trades": r["trade_count"],
            }
            for r in leaderboard[:6]
        ],
        "path": str(out),
    }
    print(json.dumps(slim, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
