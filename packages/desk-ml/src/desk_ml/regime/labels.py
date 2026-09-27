"""Causal minute-level regime labeller for one index session.

Feed completed 1m bars in order with `RegimeLabeller.update(bar)`; the label it returns for minute t
is built only from bars up to and including t (streaming state, nothing is revised later).

Primary label (one of): trend_up, trend_down, range, unknown (warm-up).
Vol label (at most one): vol_expansion, vol_compression.
Session flags: expiry_day, gap_day.

Inputs: index 1m OHLC(V), realised volatility (short vs long window of 1m log returns), Wilder
ADX/DMI, distance of the close from session VWAP (TWAP of typical price when the tape has no
volume), opening gap versus the prior close, and minutes to the next expiry.
Every threshold lives in `LabelConfig` (config/regime.yaml `labels:`), so validated lab values can
replace the defaults without code changes.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence

IST = timezone(timedelta(hours=5, minutes=30))

TREND_UP = "trend_up"
TREND_DOWN = "trend_down"
RANGE = "range"
UNKNOWN = "unknown"
VOL_EXPANSION = "vol_expansion"
VOL_COMPRESSION = "vol_compression"
EXPIRY_DAY = "expiry_day"
GAP_DAY = "gap_day"
PRIMARY_LABELS = (TREND_UP, TREND_DOWN, RANGE, UNKNOWN)


@dataclass(frozen=True)
class LabelConfig:
    version: str = "v0-default-unvalidated"
    adx_period: int = 14
    adx_trend_min: float = 22.0
    vwap_confirm_bps: float = 3.0
    rv_short: int = 15
    rv_long: int = 60
    rv_min_long: int = 20
    vol_expansion_ratio: float = 1.5
    vol_compression_ratio: float = 0.6
    gap_pct: float = 0.5
    expiry_close_hhmm: str = "15:30"

    @classmethod
    def from_dict(cls, raw: Optional[Mapping[str, Any]]) -> "LabelConfig":
        raw = dict(raw or {})
        unknown = sorted(set(raw) - {f.name for f in fields(cls)})
        if unknown:
            raise ValueError(f"unknown regime label keys: {unknown}")
        base = cls()
        kw = {k: type(getattr(base, k))(v) for k, v in raw.items()}
        return cls(**kw)


def _ist_date(ts: int) -> date:
    return datetime.fromtimestamp(int(ts), IST).date()


def next_expiry(session: date, expiry_dates: Iterable[str]) -> Optional[date]:
    future = []
    for raw in expiry_dates or ():
        try:
            d = date.fromisoformat(str(raw)[:10])
        except ValueError:
            continue
        if d >= session:
            future.append(d)
    return min(future) if future else None


class RegimeLabeller:
    """Streaming labeller. One instance per index per session."""

    def __init__(
        self,
        cfg: Optional[LabelConfig] = None,
        *,
        prior_close: Optional[float] = None,
        expiry_dates: Sequence[str] = (),
    ) -> None:
        self.cfg = cfg or LabelConfig()
        self.prior_close = float(prior_close) if prior_close else None
        self.expiry_dates = tuple(str(d) for d in expiry_dates or ())
        n = int(self.cfg.adx_period)
        self._n = n
        self._prev: Optional[dict[str, float]] = None
        self._count = 0
        self._tr_sum = self._pdm_sum = self._mdm_sum = 0.0
        self._atr = self._pdm = self._mdm = None  # Wilder-smoothed sums after the first n bars
        self._dx: list[float] = []
        self._adx: Optional[float] = None
        self._pv = self._v = self._tp_sum = 0.0
        self._all_volume = True
        self._rets: deque[float] = deque(maxlen=max(int(self.cfg.rv_long), int(self.cfg.rv_short)))
        self._open: Optional[float] = None
        self._last_ts: Optional[int] = None

    def update(self, bar: Mapping[str, Any]) -> dict[str, Any]:
        ts = int(bar["ts"])
        if self._last_ts is not None and ts <= self._last_ts:
            raise ValueError(f"bars must be strictly increasing in time ({ts} after {self._last_ts})")
        self._last_ts = ts
        o, h, l, c = (float(bar[k]) for k in ("open", "high", "low", "close"))
        vol = bar.get("volume")
        if self._open is None:
            self._open = o
        self._count += 1
        self._update_dmi(h, l, c)
        self._update_vwap(h, l, c, vol)
        if self._prev is not None and self._prev["close"] > 0 and c > 0:
            self._rets.append(math.log(c / self._prev["close"]))
        self._prev = {"high": h, "low": l, "close": c}
        return self._label(ts, c)

    # -- features ---------------------------------------------------------------------------
    def _update_dmi(self, h: float, l: float, c: float) -> None:
        p = self._prev
        if p is None:
            return
        tr = max(h - l, abs(h - p["close"]), abs(l - p["close"]))
        up, down = h - p["high"], p["low"] - l
        pdm = up if up > down and up > 0 else 0.0
        mdm = down if down > up and down > 0 else 0.0
        n = self._n
        if self._atr is None:
            self._tr_sum += tr
            self._pdm_sum += pdm
            self._mdm_sum += mdm
            if self._count - 1 == n:
                self._atr, self._pdm, self._mdm = self._tr_sum, self._pdm_sum, self._mdm_sum
            else:
                return
        else:
            self._atr = self._atr - self._atr / n + tr
            self._pdm = self._pdm - self._pdm / n + pdm
            self._mdm = self._mdm - self._mdm / n + mdm
        pdi, mdi = self._di()
        s = pdi + mdi
        dx = 100.0 * abs(pdi - mdi) / s if s > 0 else 0.0
        if self._adx is None:
            self._dx.append(dx)
            if len(self._dx) == n:
                self._adx = sum(self._dx) / n
        else:
            self._adx = (self._adx * (n - 1) + dx) / n

    def _di(self) -> tuple[float, float]:
        if not self._atr:
            return 0.0, 0.0
        return 100.0 * self._pdm / self._atr, 100.0 * self._mdm / self._atr

    def _update_vwap(self, h: float, l: float, c: float, vol: Any) -> None:
        tp = (h + l + c) / 3.0
        self._tp_sum += tp
        try:
            v = float(vol) if vol is not None else 0.0
        except (TypeError, ValueError):
            v = 0.0
        if v > 0:
            self._pv += tp * v
            self._v += v
        else:
            self._all_volume = False

    def vwap(self) -> Optional[float]:
        if self._count == 0:
            return None
        if self._all_volume and self._v > 0:
            return self._pv / self._v
        return self._tp_sum / self._count  # ponytail: TWAP when the index tape has no volume

    @staticmethod
    def _std(xs: Sequence[float]) -> Optional[float]:
        if len(xs) < 2:
            return None
        m = sum(xs) / len(xs)
        return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))

    # -- label ------------------------------------------------------------------------------
    def _label(self, ts: int, close: float) -> dict[str, Any]:
        cfg = self.cfg
        pdi, mdi = self._di()
        vwap = self.vwap()
        vwap_bps = (close - vwap) / vwap * 1e4 if vwap else None
        adx = self._adx
        if adx is None or vwap_bps is None:
            primary = UNKNOWN
        elif adx >= cfg.adx_trend_min and pdi > mdi and vwap_bps >= cfg.vwap_confirm_bps:
            primary = TREND_UP
        elif adx >= cfg.adx_trend_min and mdi > pdi and vwap_bps <= -cfg.vwap_confirm_bps:
            primary = TREND_DOWN
        else:
            primary = RANGE

        rets = list(self._rets)
        short = self._std(rets[-int(cfg.rv_short):]) if len(rets) >= int(cfg.rv_short) else None
        long_ = self._std(rets[-int(cfg.rv_long):]) if len(rets) >= int(cfg.rv_min_long) else None
        ratio = short / long_ if short is not None and long_ else None
        vol = None
        if ratio is not None:
            if ratio >= cfg.vol_expansion_ratio:
                vol = VOL_EXPANSION
            elif ratio <= cfg.vol_compression_ratio:
                vol = VOL_COMPRESSION

        gap_pct = None
        if self.prior_close and self._open:
            gap_pct = (self._open - self.prior_close) / self.prior_close * 100.0
        gap_day = gap_pct is not None and abs(gap_pct) >= cfg.gap_pct

        session = _ist_date(ts)
        exp = next_expiry(session, self.expiry_dates)
        tte_min = None
        if exp is not None:
            hh, mm = (int(x) for x in cfg.expiry_close_hhmm.split(":"))
            exp_close = datetime(exp.year, exp.month, exp.day, hh, mm, tzinfo=IST).timestamp()
            tte_min = max(0.0, (exp_close - (ts + 60)) / 60.0)
        expiry_day = exp is not None and exp == session

        labels = [primary] + ([vol] if vol else []) + ([EXPIRY_DAY] if expiry_day else []) + ([GAP_DAY] if gap_day else [])
        return {
            "ts": ts,
            "primary": primary,
            "vol": vol,
            "expiry_day": bool(expiry_day),
            "gap_day": bool(gap_day),
            "labels": labels,
            "features": {
                "n_bars": self._count,
                "adx": _r(adx),
                "pdi": _r(pdi) if adx is not None else None,
                "mdi": _r(mdi) if adx is not None else None,
                "vwap": _r(vwap),
                "vwap_dist_bps": _r(vwap_bps),
                "vwap_kind": "vwap" if self._all_volume and self._v > 0 else "twap",
                "rv_short": _r(short, 8),
                "rv_long": _r(long_, 8),
                "rv_ratio": _r(ratio),
                "gap_pct": _r(gap_pct),
                "tte_min": _r(tte_min, 1),
                "expiry": exp.isoformat() if exp else None,
            },
            "version": cfg.version,
        }


def _r(x: Optional[float], nd: int = 4) -> Optional[float]:
    if x is None or not math.isfinite(x):
        return None
    return round(float(x), nd)


def label_bars(
    bars: Sequence[Mapping[str, Any]],
    cfg: Optional[LabelConfig] = None,
    *,
    prior_close: Optional[float] = None,
    expiry_dates: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """Label every completed bar of one session (streaming; label t never sees bars after t)."""
    lab = RegimeLabeller(cfg, prior_close=prior_close, expiry_dates=expiry_dates)
    return [lab.update(b) for b in bars]


__all__ = [
    "EXPIRY_DAY", "GAP_DAY", "LabelConfig", "PRIMARY_LABELS", "RANGE", "RegimeLabeller", "TREND_DOWN",
    "TREND_UP", "UNKNOWN", "VOL_COMPRESSION", "VOL_EXPANSION", "label_bars", "next_expiry",
]
