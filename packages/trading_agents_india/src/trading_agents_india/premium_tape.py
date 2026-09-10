"""Rolling 1m ATM option-premium tape: fetch, persist, load, dual-master gate.

This is the blocker-remover for MIX-DUAL-INDEX-MASTER and for BUY_* cards in
DESK_SIGNAL_JSON (premium_ohlc_present). Data source is the documented Dhan
POST /charts/rollingoption (Data API, OPTIDX, strike ATM, weekly code 1) —
one call returns both ce and pe arrays. Fail soft: any error is a
DATA_INSUFFICIENT gap, never an invented bar. No orders.

Indicator math mirrors scripts/backtest_mrr.py exactly so live paper-watch and
the shadow backtest can never disagree on semantics.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from trading_agents_india.session_clock import now_ist

IST = timezone(timedelta(hours=5, minutes=30))

_UNDERLYING_HINTS = {
    "NIFTY": ("13", "NSE_FNO"),
    "BANKNIFTY": ("25", "NSE_FNO"),
    "SENSEX": ("51", "BSE_FNO"),
}

MIN_GATE_BARS = 30


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def tape_dir() -> Path:
    path = _repo_root() / "data" / "recon" / "premium_tape"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class TapeBar:
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class PremiumTapeResult:
    underlying: str
    source: str  # dhan_rollingoption_1m | cache | unavailable
    day: str = ""
    ce_count: int = 0
    pe_count: int = 0
    path: str = ""
    data_gaps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _bars_from_side(payload: dict[str, Any], side: str) -> list[TapeBar]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    block = (data or {}).get(side) if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return []
    opens = block.get("open") or []
    highs = block.get("high") or []
    lows = block.get("low") or []
    closes = block.get("close") or []
    vols = block.get("volume") or []
    ts = block.get("timestamp") or []
    n = min(len(opens), len(highs), len(lows), len(closes), len(ts))
    if len(vols) < n:
        vols = list(vols) + [0] * (n - len(vols))
    out: list[TapeBar] = []
    for i in range(n):
        if opens[i] is None or closes[i] is None:
            continue
        try:
            out.append(
                TapeBar(
                    ts=int(ts[i]),
                    open=float(opens[i]),
                    high=float(highs[i] if highs[i] is not None else opens[i]),
                    low=float(lows[i] if lows[i] is not None else opens[i]),
                    close=float(closes[i]),
                    volume=float(vols[i] or 0),
                )
            )
        except (TypeError, ValueError):
            continue
    return out


def _day_of(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=IST).date().isoformat()


def _tape_path(underlying: str, day: str) -> Path:
    return tape_dir() / f"{underlying.upper()}_ATM_1m_{day}.json"


def persist_tape(
    underlying: str,
    *,
    ce: list[TapeBar],
    pe: list[TapeBar],
    source: str,
) -> list[str]:
    """Upsert bars into per-day JSON files (merge by ts). Returns written days."""
    by_day: dict[str, dict[str, dict[int, TapeBar]]] = {}
    for side, bars in (("ce", ce), ("pe", pe)):
        for bar in bars:
            day = _day_of(bar.ts)
            by_day.setdefault(day, {"ce": {}, "pe": {}})[side][bar.ts] = bar
    written: list[str] = []
    for day, sides in sorted(by_day.items()):
        path = _tape_path(underlying, day)
        existing = {"ce": {}, "pe": {}}
        if path.is_file():
            try:
                blob = json.loads(path.read_text(encoding="utf-8"))
                for side in ("ce", "pe"):
                    for row in blob.get(side) or []:
                        bar = TapeBar(**{k: row[k] for k in ("ts", "open", "high", "low", "close", "volume")})
                        existing[side][bar.ts] = bar
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                existing = {"ce": {}, "pe": {}}
        for side in ("ce", "pe"):
            existing[side].update(sides[side])
        payload = {
            "meta": {
                "underlying": underlying.upper(),
                "day": day,
                "interval": "1m",
                "strike": "ATM",
                "source": source,
                "updated_at_ist": now_ist().isoformat(timespec="seconds"),
                "layer": "SOURCE_FACT",
                "note": "Rolling ATM series — strike follows spot; not one fixed contract.",
            },
            "ce": [asdict(existing["ce"][k]) for k in sorted(existing["ce"])],
            "pe": [asdict(existing["pe"][k]) for k in sorted(existing["pe"])],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        written.append(day)
    return written


def load_tape_bars(
    underlying: str,
    *,
    day: Optional[str] = None,
    side: str = "ce",
) -> list[TapeBar]:
    day = day or now_ist().date().isoformat()
    path = _tape_path(underlying, day)
    if not path.is_file():
        return []
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
        rows = blob.get(side) or []
        return [
            TapeBar(**{k: row[k] for k in ("ts", "open", "high", "low", "close", "volume")})
            for row in rows
        ]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return []


def gather_premium_tape(underlying: str, *, prefer_live: bool = False) -> PremiumTapeResult:
    """Fetch today's rolling ATM 1m ce+pe bars and persist. Fail soft."""
    und = underlying.upper()
    today = now_ist().date().isoformat()
    hint = _UNDERLYING_HINTS.get(und)
    if hint is None:
        return PremiumTapeResult(
            underlying=und,
            source="unavailable",
            data_gaps=[f"UNKNOWN: no OPTIDX hint for {und}"],
        )
    if not prefer_live:
        cached = load_tape_bars(und, day=today, side="ce")
        if cached:
            return PremiumTapeResult(
                underlying=und,
                source="cache",
                day=today,
                ce_count=len(cached),
                pe_count=len(load_tape_bars(und, day=today, side="pe")),
                path=str(_tape_path(und, today)),
            )
        return PremiumTapeResult(
            underlying=und,
            source="unavailable",
            data_gaps=["DATA_INSUFFICIENT: premium tape not fetched (live off) and no cache"],
        )
    sid, seg = hint
    try:
        from dhan_client import DhanClient  # type: ignore
    except Exception:
        return PremiumTapeResult(
            underlying=und,
            source="unavailable",
            data_gaps=["DATA_INSUFFICIENT: dhan_client not importable — premium tape skipped"],
        )
    try:
        client = DhanClient(dry_run=False)
        if getattr(client.settings, "dry_run", True):
            client.close()
            return PremiumTapeResult(
                underlying=und,
                source="unavailable",
                data_gaps=["DATA_INSUFFICIENT: Dhan dry_run — premium tape not live"],
            )
        end = now_ist()
        start = end - timedelta(days=1)
        ce: list[TapeBar] = []
        pe: list[TapeBar] = []
        # One call per side — the API only fills the block matching drvOptionType.
        for option_type in ("CALL", "PUT"):
            body = {
                "exchangeSegment": seg,
                "interval": "1",
                "securityId": sid,
                "instrument": "OPTIDX",
                "expiryFlag": "WEEK",
                "expiryCode": 1,
                "strike": "ATM",
                "drvOptionType": option_type,
                "requiredData": ["open", "high", "low", "close", "volume"],
                "fromDate": start.strftime("%Y-%m-%d"),
                "toDate": end.strftime("%Y-%m-%d"),
            }
            raw = client.historical.rolling_option(body)
            payload = raw if isinstance(raw, dict) else {}
            if option_type == "CALL":
                ce = _bars_from_side(payload, "ce") or _bars_from_side(payload, "pe")
            else:
                pe = _bars_from_side(payload, "pe") or _bars_from_side(payload, "ce")
        client.close()
        if not ce and not pe:
            return PremiumTapeResult(
                underlying=und,
                source="unavailable",
                data_gaps=["DATA_INSUFFICIENT: rollingoption returned no ce/pe bars"],
            )
        persist_tape(und, ce=ce, pe=pe, source="dhan_rollingoption_1m")
        today_ce = [b for b in ce if _day_of(b.ts) == today]
        today_pe = [b for b in pe if _day_of(b.ts) == today]
        return PremiumTapeResult(
            underlying=und,
            source="dhan_rollingoption_1m",
            day=today,
            ce_count=len(today_ce),
            pe_count=len(today_pe),
            path=str(_tape_path(und, today)),
        )
    except Exception as exc:  # noqa: BLE001
        return PremiumTapeResult(
            underlying=und,
            source="unavailable",
            data_gaps=[f"DATA_INSUFFICIENT: premium tape {type(exc).__name__}"],
        )


# ---------------------------------------------------------------------------
# Indicator math — kept identical to scripts/backtest_mrr.py.


def _sma(values: list[float], length: int) -> list[Optional[float]]:
    out: list[Optional[float]] = []
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= length:
            running -= values[i - length]
        out.append(running / length if i + 1 >= length else None)
    return out


def _ema(values: list[float], length: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if length <= 0 or len(values) < length:
        return out
    seed = sum(values[:length]) / length
    out[length - 1] = seed
    prev = seed
    k = 2.0 / (length + 1.0)
    for i in range(length, len(values)):
        prev = values[i] * k + prev * (1.0 - k)
        out[i] = prev
    return out


def _wilder_atr(bars: list[TapeBar], period: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(bars)
    if len(bars) < period + 1:
        return out
    trs: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            trs.append(bar.high - bar.low)
        else:
            prev = bars[i - 1].close
            trs.append(max(bar.high - bar.low, abs(bar.high - prev), abs(bar.low - prev)))
    first = sum(trs[1 : period + 1]) / period
    out[period] = first
    prev_atr = first
    for i in range(period + 1, len(bars)):
        prev_atr = (prev_atr * (period - 1) + trs[i]) / period
        out[i] = prev_atr
    return out


def _supertrend_direction(bars: list[TapeBar], period: int = 10, factor: float = 3.0) -> list[Optional[int]]:
    """TradingView-style direction: -1 bullish, +1 bearish."""
    atr = _wilder_atr(bars, period)
    direction: list[Optional[int]] = [None] * len(bars)
    final_upper: list[Optional[float]] = [None] * len(bars)
    final_lower: list[Optional[float]] = [None] * len(bars)
    supertrend: list[Optional[float]] = [None] * len(bars)
    for i, bar in enumerate(bars):
        if atr[i] is None:
            continue
        hl2 = (bar.high + bar.low) / 2.0
        upper = hl2 + factor * atr[i]
        lower = hl2 - factor * atr[i]
        if i == 0 or final_upper[i - 1] is None or final_lower[i - 1] is None:
            final_upper[i] = upper
            final_lower[i] = lower
            direction[i] = 1
            supertrend[i] = upper
            continue
        prev_upper = final_upper[i - 1]
        prev_lower = final_lower[i - 1]
        prev_close = bars[i - 1].close
        assert prev_upper is not None and prev_lower is not None
        final_upper[i] = upper if (upper < prev_upper or prev_close > prev_upper) else prev_upper
        final_lower[i] = lower if (lower > prev_lower or prev_close < prev_lower) else prev_lower
        prev_st = supertrend[i - 1]
        if prev_st is None or prev_st == prev_upper:
            direction[i] = -1 if bar.close > final_upper[i] else 1
        else:
            direction[i] = 1 if bar.close < final_lower[i] else -1
        supertrend[i] = final_lower[i] if direction[i] == -1 else final_upper[i]
    return direction


def _vwma(bars: list[TapeBar], length: int = 20) -> list[Optional[float]]:
    out: list[Optional[float]] = []
    for i in range(len(bars)):
        if i + 1 < length:
            out.append(None)
            continue
        window = bars[i + 1 - length : i + 1]
        den = sum(b.volume for b in window)
        if den <= 0:
            out.append(sum(b.close for b in window) / length)
        else:
            out.append(sum(b.close * b.volume for b in window) / den)
    return out


def _session_vwap(bars: list[TapeBar]) -> list[Optional[float]]:
    out: list[Optional[float]] = []
    last_day = None
    num = 0.0
    den = 0.0
    for bar in bars:
        day = datetime.fromtimestamp(bar.ts, tz=IST).date()
        if day != last_day:
            num = 0.0
            den = 0.0
            last_day = day
        typical = (bar.high + bar.low + bar.close) / 3.0
        weight = bar.volume if bar.volume > 0 else 1.0
        num += typical * weight
        den += weight
        out.append(num / den if den else None)
    return out


def _in_window(ts: int) -> bool:
    t = datetime.fromtimestamp(ts, tz=IST).time()
    m = t.hour * 60 + t.minute
    return (9 * 60 + 20) <= m <= (11 * 60) or (13 * 60 + 30) <= m <= (15 * 60 + 10)


def dual_master_gate(premium_bars: list[TapeBar]) -> dict[str, Any]:
    """Evaluate MIX-DUAL premium conditions on the LAST bar of the tape.

    Same conditions as backtest_mrr.dual_index_master_signals minus the spot
    gate (caller owns spot). Returns per-condition booleans — never a fill.
    """
    if len(premium_bars) < MIN_GATE_BARS:
        return {
            "evaluated": False,
            "reason": f"DATA_INSUFFICIENT: premium bars {len(premium_bars)} < {MIN_GATE_BARS}",
        }
    closes = [b.close for b in premium_bars]
    volumes = [b.volume for b in premium_bars]
    i = len(premium_bars) - 1
    bar = premium_bars[i]
    mrr = _vwma(premium_bars, 20)[i]
    vwap = _session_vwap(premium_bars)[i]
    ema9 = _ema(closes, 9)[i]
    ema21 = _ema(closes, 21)[i]
    vol_ma = _sma(volumes, 20)[i]
    st_dir = _supertrend_direction(premium_bars, 10, 3.0)[i]
    if any(v is None for v in (mrr, vwap, ema9, ema21, vol_ma, st_dir)):
        return {"evaluated": False, "reason": "DATA_INSUFFICIENT: indicator warmup incomplete"}
    conditions = {
        "close_gt_mrr": bar.close > mrr,
        "close_gt_vwap": bar.close > vwap,
        "supertrend_bullish": st_dir == -1,
        "ema9_gt_ema21": ema9 > ema21,
        "volume_spike": bar.volume > vol_ma * 1.3,
        "in_time_window": _in_window(bar.ts),
    }
    return {
        "evaluated": True,
        "all_pass": all(conditions.values()),
        "conditions": conditions,
        "values": {
            "close": bar.close,
            "mrr_vwma20": round(mrr, 4),
            "session_vwap": round(vwap, 4),
            "ema9": round(ema9, 4),
            "ema21": round(ema21, 4),
            "volume": bar.volume,
            "vol_sma20": round(vol_ma, 4),
            "supertrend_dir": st_dir,
            "bar_ts_ist": datetime.fromtimestamp(bar.ts, tz=IST).isoformat(timespec="seconds"),
        },
        "bar_count": len(premium_bars),
    }
