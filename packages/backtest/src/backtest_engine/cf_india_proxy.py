"""Generic Chart Fanatics India adaptation runner (sibling to okala_in_proxy).

Does NOT rewrite okala_in_proxy. Families load observation-gated configs from
data/recon/CF_OPENAI_*_BIND_SUGGEST_*.json india_adaptation + backtest_search_grid.

PAPER / HYPOTHESIS / NO_PROMOTE. win_rate is VALIDATION output only.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Optional, Sequence

from dhan_client.config import repo_root

from backtest_engine.clocks import minutes_ist, session_date_ist, skip_open_009
from backtest_engine.indicators import Bar, _wilder_atr

ROOT = repo_root()
RECON = ROOT / "data/recon"
DATE = "2026-09-07"

# Family slug → OpenAI suggest json
FAMILY_SLUGS = (
    "FABIO",
    "MARCO",
    "MAYNE",
    "MARCI",
    "TORI",
    "TG",
    "KANE",
    "UMAR",
    "FOREST",
    "CARMINE",
    "JADECAP",
    "USMAN",
    "BRANDO",
    "ANDREA",
    "OMOR",
    "YUSH",
    "MARCO-DAV",
)

SL_ATR_MULT = 0.50
TP_SL_RATIO = 1.5
MIN_SL_PTS = {"NIFTY": 8.0, "BANKNIFTY": 20.0, "SENSEX": 10.0}
REGIMES = ("bullish", "bearish", "sideways", "choppy")


@dataclass
class CfIndiaTrade:
    strategy_id: str
    family: str
    underlying: str
    side: str
    entry_ts: int
    exit_ts: int
    entry_px: float
    exit_px: float
    points: float
    reason: str
    session: str
    regime: str
    tf_min: int

    @property
    def win(self) -> bool:
        return self.points > 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["win"] = self.win
        return d


def load_family_suggest(family: str) -> Optional[dict[str, Any]]:
    slug = family.upper().replace("_", "-")
    path = RECON / f"CF_OPENAI_{slug}_BIND_SUGGEST_{DATE}.json"
    if not path.is_file():
        # try underscore-free
        alt = RECON / f"CF_OPENAI_{family}_BIND_SUGGEST_{DATE}.json"
        if alt.is_file():
            path = alt
        else:
            return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def india_decision(family: str) -> str:
    blob = load_family_suggest(family)
    if not blob:
        return "MISSING"
    ia = blob.get("india_adaptation") if isinstance(blob.get("india_adaptation"), dict) else {}
    return str(ia.get("decision") or "UNKNOWN").upper()


def _sma(xs: Sequence[float], n: int) -> Optional[float]:
    if len(xs) < n:
        return None
    return sum(xs[-n:]) / float(n)


def _regime(closes: Sequence[float]) -> str:
    if len(closes) < 40:
        return "sideways"
    fast = _sma(closes, 10)
    slow = _sma(closes, 40)
    if fast is None or slow is None:
        return "sideways"
    diff = (fast - slow) / max(abs(slow), 1e-9)
    # choppy if recent range large vs move
    window = closes[-20:]
    rng = max(window) - min(window)
    move = abs(closes[-1] - closes[-20])
    if rng > 0 and move / rng < 0.25:
        return "choppy"
    if diff > 0.0015:
        return "bullish"
    if diff < -0.0015:
        return "bearish"
    return "sideways"


def _round_magnets(price: float, step: float = 50.0) -> list[float]:
    """Observation-seed round levels (HYPOTHESIS) — not sacred."""
    base = math.floor(price / step) * step
    return [base - step, base, base + step, base + 2 * step]


def simulate_family(
    bars: Sequence[Bar],
    *,
    family: str,
    underlying: str = "NIFTY",
    tf_min: int = 5,
    mix_id: Optional[str] = None,
) -> dict[str, Any]:
    """OHLC observation-gated PA proxy for a CF India family.

    SKIP families return empty trades with honesty status.
    PARTIAL/PORT run a simple round-level fade + ATR risk shell (HYPOTHESIS).
    """
    fam = family.upper()
    decision = india_decision(fam)
    suggest = load_family_suggest(fam) or {}
    ia = suggest.get("india_adaptation") if isinstance(suggest.get("india_adaptation"), dict) else {}
    of_required = bool(ia.get("of_required"))
    mix = mix_id or f"MIX-CF-{fam}-IN-CORE"

    meta = {
        "family": fam,
        "underlying": underlying,
        "tf_min": tf_min,
        "mix_id": mix,
        "india_decision": decision,
        "of_required": of_required,
        "layer": "HYPOTHESIS",
        "NO_PROMOTE": True,
        "win_rate_catalog": None,
        "note": "Sibling runner — does not modify okala_in_proxy",
    }

    if decision == "SKIP":
        return {
            **meta,
            "status": "SKIP",
            "trades": [],
            "n": 0,
            "win_rate": None,
            "skip_reason": ia.get("rationale") or "OpenAI india_adaptation=SKIP",
        }
    if decision == "MISSING":
        return {**meta, "status": "MISSING_OPENAI", "trades": [], "n": 0, "win_rate": None}

    if len(bars) < 80:
        return {**meta, "status": "DATA_INSUFFICIENT", "trades": [], "n": 0, "win_rate": None}

    atr = _wilder_atr(list(bars), 14)
    closes = [b.close for b in bars]
    trades: list[CfIndiaTrade] = []
    i = 40
    while i < len(bars) - 5:
        bar = bars[i]
        if skip_open_009(bar.ts):
            i += 1
            continue
        mins = minutes_ist(bar.ts)
        # NSE cash session soft window (HYPOTHESIS remap of teacher NY preference)
        if mins < 9 * 60 + 30 or mins > 15 * 60:
            i += 1
            continue
        a = atr[i] if i < len(atr) else None
        if a is None or a <= 0:
            i += 1
            continue
        regime = _regime(closes[: i + 1])
        magnets = _round_magnets(bar.close, step=50.0 if underlying != "BANKNIFTY" else 100.0)
        nearest = min(magnets, key=lambda m: abs(m - bar.close))
        dist = abs(bar.close - nearest)
        if dist > 0.35 * a:
            i += 1
            continue
        # fade toward magnet mean-reversion seed
        side = "PE" if bar.close > nearest else "CE"
        sl = max(MIN_SL_PTS.get(underlying, 8.0), SL_ATR_MULT * a)
        tp = sl * TP_SL_RATIO
        entry = bar.close
        exit_px = entry
        exit_ts = bar.ts
        reason = "time"
        for j in range(i + 1, min(i + 12, len(bars))):
            b2 = bars[j]
            if side == "CE":
                if b2.low <= entry - sl:
                    exit_px = entry - sl
                    exit_ts = b2.ts
                    reason = "sl"
                    break
                if b2.high >= entry + tp:
                    exit_px = entry + tp
                    exit_ts = b2.ts
                    reason = "tp"
                    break
            else:
                if b2.high >= entry + sl:
                    exit_px = entry + sl
                    exit_ts = b2.ts
                    reason = "sl"
                    break
                if b2.low <= entry - tp:
                    exit_px = entry - tp
                    exit_ts = b2.ts
                    reason = "tp"
                    break
            exit_px = b2.close
            exit_ts = b2.ts
        pts = (exit_px - entry) if side == "CE" else (entry - exit_px)
        trades.append(
            CfIndiaTrade(
                strategy_id=mix,
                family=fam,
                underlying=underlying,
                side=side,
                entry_ts=bar.ts,
                exit_ts=exit_ts,
                entry_px=entry,
                exit_px=exit_px,
                points=pts,
                reason=reason,
                session=session_date_ist(bar.ts),
                regime=regime,
                tf_min=tf_min,
            )
        )
        i += 8  # cooldown

    wins = sum(1 for t in trades if t.win)
    n = len(trades)
    wr = (wins / n) if n else None
    return {
        **meta,
        "status": "RAN",
        "trades": [t.to_dict() for t in trades],
        "n": n,
        "wins": wins,
        "win_rate": wr,  # VALIDATION research only — do not copy to catalog
        "regimes": {r: sum(1 for t in trades if t.regime == r) for r in REGIMES},
    }


def run_cf_india_grid(
    bars_by_underlying: dict[str, Sequence[Bar]],
    *,
    families: Optional[Sequence[str]] = None,
    tf_min: int = 5,
) -> dict[str, Any]:
    fams = list(families or FAMILY_SLUGS)
    cells = []
    for fam in fams:
        for und, bars in bars_by_underlying.items():
            cell = simulate_family(bars, family=fam, underlying=und, tf_min=tf_min)
            cells.append(cell)
    return {
        "as_of": DATE,
        "layer": "HYPOTHESIS",
        "NO_PROMOTE": True,
        "note": "Generic CF India runner — sibling to okala-in; catalog win_rate stays null",
        "cells": cells,
        "n_cells": len(cells),
        "n_ran": sum(1 for c in cells if c.get("status") == "RAN"),
        "n_skip": sum(1 for c in cells if c.get("status") == "SKIP"),
    }
