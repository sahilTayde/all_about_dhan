"""V2-18 pre-market: PRE_MARKET_SUMMARY, event-day holds, HAR inputs. Paper only.

Uses prior-session data only (no session-day bars). available_ts is the run time
and must be before 09:15 IST. Idempotent: same inputs rewrite the same bytes.
Never writes checkout data/. No network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from warehouse.calendar import IST, NonTradingDay, resolve_trading_day

OPEN = time(9, 15)
SCHEMA = "pre-market-v2-18"


def assert_not_checkout_data(path: Path) -> Path:
    resolved = path.resolve()
    cur = resolved
    while cur != cur.parent:
        if cur.name == "data" and (cur.parent / ".git").is_dir():
            raise ValueError(f"refusing to write under checkout data/: {resolved}")
        cur = cur.parent
    return resolved


def _as_ist(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("timestamps must be tz-aware")
    return ts.astimezone(IST)


def har_forecast(daily_rv: list[float]) -> float:
    """HAR-RV: 0.5 RV_d + 0.3 RV_w + 0.2 RV_m from prior daily realised vols."""
    if not daily_rv:
        return 0.0
    rv_d, rv_w, rv_m = daily_rv[-1], sum(daily_rv[-5:]) / len(daily_rv[-5:]), sum(daily_rv[-22:]) / len(daily_rv[-22:])
    return round(0.5 * rv_d + 0.3 * rv_w + 0.2 * rv_m, 6)


def atr14(bars: list[dict[str, Any]]) -> float | None:
    if len(bars) < 2:
        return None
    trs: list[float] = []
    prev = float(bars[0]["close"])
    for b in bars[1:]:
        high, low, close = float(b["high"]), float(b["low"]), float(b["close"])
        trs.append(max(high - low, abs(high - prev), abs(low - prev)))
        prev = close
    window = trs[-14:]
    return round(sum(window) / len(window), 6) if window else None


def publish(
    session: date | None,
    *,
    now: datetime,
    prior_bars: list[dict[str, Any]],
    intermarket: dict[str, float],
    event_days: dict[str, str],
    dest: Path,
) -> dict[str, Any]:
    session = resolve_trading_day(session, now)
    now_ist = _as_ist(now)
    if now_ist.time() >= OPEN:
        raise ValueError("pre-market must run before 09:15 IST")
    for bar in prior_bars:
        if date.fromisoformat(str(bar["date"])) >= session:
            raise ValueError("session-day data is not allowed in pre-market")
    holds = []
    reason = event_days.get(session.isoformat())
    if reason:
        holds.append({"kind": "EVENT_DAY", "reason": reason})
    closes = [float(b["close"]) for b in prior_bars]
    rvs = [abs(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes))] if len(closes) > 1 else []
    payload = {
        "session": session.isoformat(),
        "previous_close": closes[-1] if closes else None,
        "atr14": atr14(prior_bars),
        "har_forecast": har_forecast(rvs),
        "intermarket_closes": dict(sorted(intermarket.items())),
        "holds": holds,
        "basket_inputs": {
            "underlyings": ["NIFTY", "BANKNIFTY", "SENSEX"],
            "previous_close": closes[-1] if closes else None,
        },
        "headline_net": None,
    }
    body, _ = json.dumps(payload, sort_keys=True, separators=(",", ":")), None
    event_id = hashlib.sha256(f"{SCHEMA}|{session.isoformat()}|{body}".encode()).hexdigest()[:32]
    env = {
        "v": 2,
        "event_type": "PRE_MARKET_SUMMARY",
        "event_id": event_id,
        "stream": "sig:premarket",
        "source": "premarket",
        "event_ts": now_ist.isoformat(timespec="seconds"),
        "available_ts": now_ist.isoformat(timespec="seconds"),
        "timestamp": now_ist.isoformat(timespec="seconds"),
        "account_id": None,
        "correlation_id": None,
        "causation_id": None,
        "payload": payload,
    }
    dest = assert_not_checkout_data(dest)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"PRE_MARKET_SUMMARY.{session.isoformat()}.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(env, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out)
    return env


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="V2-18 pre-market publish (paper; no network)")
    p.add_argument("--session", default=None, help="optional YYYY-MM-DD (else derived from --now)")
    p.add_argument("--now", required=True, help="tz-aware ISO timestamp")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--prior", required=True, type=Path, help="JSON list of prior daily bars")
    p.add_argument("--events", type=Path, default=None, help="JSON map date→reason")
    p.add_argument("--intermarket", type=Path, default=None)
    args = p.parse_args(argv)
    bars = json.loads(args.prior.read_text(encoding="utf-8"))
    events = json.loads(args.events.read_text(encoding="utf-8")) if args.events else {}
    inter = json.loads(args.intermarket.read_text(encoding="utf-8")) if args.intermarket else {}
    try:
        env = publish(
            date.fromisoformat(args.session) if args.session else None,
            now=datetime.fromisoformat(args.now),
            prior_bars=bars,
            intermarket=inter,
            event_days=events,
            dest=args.out,
        )
    except NonTradingDay as exc:
        print(json.dumps({"error": "non-trading-day", "detail": str(exc)}, sort_keys=True))
        return 2
    print(
        json.dumps({"event_id": env["event_id"], "available_ts": env["available_ts"], "holds": env["payload"]["holds"]})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
