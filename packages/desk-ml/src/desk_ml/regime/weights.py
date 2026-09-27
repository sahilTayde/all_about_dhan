"""Adaptive, regime-conditional analyst weights for the boss (roadmap PR-012). Paper only.

Each analyst keeps decayed hit/miss counts per regime bucket plus a pooled bucket. A hit is:
  * closed trade: the analyst spoke the trade's side and the trade netted > 0, or spoke the other
    side and the trade netted < 0 (silent analysts are not scored);
  * matured vote: the index moved the analyst's way by more than a dead band `vote_horizon_min`
    completed minutes after the vote.
Nothing is scored before that information exists (the caller passes the outcome time; the runner
only calls `apply_outcome` once the trade has closed or the horizon bar has completed).

Weight = static weight x multiplier. The multiplier comes from a two-level Beta shrinkage:
    pooled  = (hits + k0 * 0.5) / (n + k0)
    regime  = (hits_r + k1 * pooled) / (n_r + k1)       (pooled if n_r < min_samples_regime)
    mult    = clip(1 + gain * 2 * (regime - 0.5), floor, cap)   (1.0 if n < min_samples)
then no analyst may exceed `max_share` of the roster's total weight (water-filling cap).

State is JSON, written atomically (tmp + fsync + rename) with a schema number and a version
counter that must match on save (optimistic lock against a concurrent writer).
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from collections import Counter
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

SCHEMA = 1
POOLED = "__all__"
DAY_S = 86400.0


@dataclass(frozen=True)
class WeightConfig:
    enabled: bool = True
    state_path: str = "data/recon/regime/weights_state.json"
    static_weights: Optional[dict] = None
    condition_on: str = "primary"
    prior_strength: float = 20.0
    regime_prior_strength: float = 10.0
    min_samples: float = 30.0
    min_samples_regime: float = 10.0
    half_life_days: float = 10.0
    gain: float = 1.0
    floor: float = 0.5
    cap: float = 1.5
    max_share: float = 0.25
    trade_outcome_weight: float = 1.0
    vote_outcome_weight: float = 0.2
    vote_horizon_min: int = 15
    vote_dead_band_bps: float = 3.0

    @classmethod
    def from_dict(cls, raw: Optional[Mapping[str, Any]]) -> "WeightConfig":
        raw = dict(raw or {})
        unknown = sorted(set(raw) - {f.name for f in fields(cls)})
        if unknown:
            raise ValueError(f"unknown regime weight keys: {unknown}")
        cfg = cls(**raw)
        if not (0 < cfg.floor <= 1.0 <= cfg.cap):
            raise ValueError("weights: need 0 < floor <= 1 <= cap")
        if not (0 < cfg.max_share <= 1.0) or cfg.half_life_days <= 0:
            raise ValueError("weights: need 0 < max_share <= 1 and half_life_days > 0")
        return cfg

    def static(self, analyst: str) -> float:
        return float((self.static_weights or {}).get(analyst, 1.0))


class StateVersionConflict(RuntimeError):
    """The state file changed on disk since it was loaded."""


class WeightState:
    def __init__(self, cfg: Optional[WeightConfig] = None) -> None:
        self.cfg = cfg or WeightConfig()
        self.version = 0
        self.buckets: dict[str, dict[str, list[float]]] = {}  # analyst -> bucket -> [hits, misses, ts]
        self.applied: dict[str, int] = {}  # outcome id -> outcome ts (idempotent re-replays)
        self.last_outcome_ts: Optional[int] = None

    # -- decay ------------------------------------------------------------------------------
    def _decay(self, dt: float) -> float:
        return 0.5 ** (max(0.0, dt) / (self.cfg.half_life_days * DAY_S))

    def counts(self, analyst: str, bucket: str, now_ts: int) -> tuple[float, float]:
        row = (self.buckets.get(analyst) or {}).get(bucket)
        if not row:
            return 0.0, 0.0
        f = self._decay(now_ts - row[2])
        return row[0] * f, row[1] * f

    def _add(self, analyst: str, bucket: str, hit: bool, w: float, ts: int) -> None:
        row = self.buckets.setdefault(analyst, {}).setdefault(bucket, [0.0, 0.0, float(ts)])
        if ts >= row[2]:
            f = self._decay(ts - row[2])
            row[0], row[1], row[2] = row[0] * f, row[1] * f, float(ts)
        else:
            w *= self._decay(row[2] - ts)
        row[0 if hit else 1] += w

    def apply_outcome(
        self, outcome_id: str, ts: int, bucket: str, samples: Iterable[tuple[str, bool]], weight: float,
    ) -> bool:
        """Score one matured outcome for every analyst in `samples`. False if already applied."""
        if outcome_id in self.applied:
            return False
        rows = list(samples)
        for analyst, hit in rows:
            self._add(analyst, bucket, bool(hit), float(weight), int(ts))
            self._add(analyst, POOLED, bool(hit), float(weight), int(ts))
        self.applied[outcome_id] = int(ts)
        self.last_outcome_ts = max(int(ts), self.last_outcome_ts or int(ts))
        return True

    # -- weights ----------------------------------------------------------------------------
    def multiplier(self, analyst: str, bucket: str, now_ts: int) -> dict[str, Any]:
        c = self.cfg
        h, m = self.counts(analyst, POOLED, now_ts)
        n = h + m
        if n < c.min_samples:
            return {"mult": 1.0, "n": round(n, 3), "p": None, "why": "min_samples"}
        pooled = (h + c.prior_strength * 0.5) / (n + c.prior_strength)
        hr, mr = self.counts(analyst, bucket, now_ts)
        nr = hr + mr
        if nr >= c.min_samples_regime:
            p = (hr + c.regime_prior_strength * pooled) / (nr + c.regime_prior_strength)
            why = "regime"
        else:
            p, why = pooled, "pooled"
        mult = min(c.cap, max(c.floor, 1.0 + c.gain * 2.0 * (p - 0.5)))
        return {"mult": round(mult, 6), "n": round(n, 3), "n_regime": round(nr, 3), "p": round(p, 6), "why": why}

    def weights(self, roster: Sequence[str], bucket: str, now_ts: int) -> dict[str, float]:
        raw = {a: self.cfg.static(a) * self.multiplier(a, bucket, now_ts)["mult"] for a in roster}
        return cap_shares(raw, self.cfg.max_share)

    # -- persistence ------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "version": self.version, "last_outcome_ts": self.last_outcome_ts,
            "half_life_days": self.cfg.half_life_days, "buckets": self.buckets, "applied": self.applied,
            "paper_only": True,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any], cfg: Optional[WeightConfig] = None) -> "WeightState":
        if int(raw.get("schema", -1)) != SCHEMA:
            raise ValueError(f"weight state schema {raw.get('schema')} != {SCHEMA}")
        st = cls(cfg)
        st.version = int(raw.get("version") or 0)
        st.last_outcome_ts = raw.get("last_outcome_ts")
        st.buckets = {a: {b: [float(x) for x in row] for b, row in bk.items()} for a, bk in (raw.get("buckets") or {}).items()}
        st.applied = {str(k): int(v) for k, v in (raw.get("applied") or {}).items()}
        return st

    @classmethod
    def load(cls, path: Path, cfg: Optional[WeightConfig] = None) -> "WeightState":
        path = Path(path)
        if not path.is_file():
            return cls(cfg)
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")), cfg)

    def prune(self, keep_half_lives: float = 10.0) -> None:
        if self.last_outcome_ts is None:
            return
        horizon = self.last_outcome_ts - keep_half_lives * self.cfg.half_life_days * DAY_S
        self.applied = {k: v for k, v in self.applied.items() if v >= horizon}

    def save(self, path: Path) -> int:
        """Atomic write. Raises StateVersionConflict if the file moved on since this state was loaded."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            on_disk = int(json.loads(path.read_text(encoding="utf-8")).get("version") or 0)
            if on_disk != self.version:
                raise StateVersionConflict(f"{path}: on-disk version {on_disk}, loaded {self.version}")
        elif self.version != 0:
            raise StateVersionConflict(f"{path}: missing, loaded version {self.version}")
        self.prune()
        self.version += 1
        blob = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        fd, tmp = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(blob + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except BaseException:
            self.version -= 1
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return self.version


def cap_shares(weights: Mapping[str, float], max_share: float) -> dict[str, float]:
    """Lower the largest weights until none exceeds `max_share` of the total (no-op if infeasible)."""
    out = {k: float(v) for k, v in weights.items()}
    if not out or max_share >= 1.0 or max_share * len(out) < 1.0:
        return out
    capped: set[str] = set()
    while True:
        free = sum(v for k, v in out.items() if k not in capped)
        c = max_share * free / (1.0 - max_share * len(capped))
        over = [k for k, v in out.items() if k not in capped and v > c + 1e-12]
        if not over:
            for k in capped:
                out[k] = c
            return out
        capped.update(over)


def weighted_picker(
    votes: Sequence[Any],
    weights: Mapping[str, float],
    *,
    prev: Any = None,
    closed: Any = None,
    classified: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """`picker.picker_majority` with each spoken vote counted at its weight instead of 1.

    With every weight 1.0 it returns exactly what `picker_majority` returns (tested). The 8-7 rule
    becomes: margin within one mean weight and the smaller side at least seven mean weights.
    """
    from dataclasses import asdict

    from desk_ml import picker as pk

    def w(v: Any) -> float:
        return float(weights.get(v.source, 1.0))

    spoken = [v for v in votes if isinstance(v, pk.Vote) and v.spoken() and w(v) > 0]
    w_ce = sum(w(v) for v in spoken if v.side == "CE")
    w_pe = sum(w(v) for v in spoken if v.side == "PE")
    base: dict[str, Any] = {
        "promote": False, "layer": "HYPOTHESIS", "execution": "refused", "llm": False,
        "votes": [asdict(v) if isinstance(v, pk.Vote) else dict(v) for v in votes],
        "n_spoken": len(spoken),
        "n_ce": sum(1 for v in spoken if v.side == "CE"),
        "n_pe": sum(1 for v in spoken if v.side == "PE"),
        "side": None, "action": "HOLD", "skip": pk.HOLD_NO_SPOKEN, "detail": pk.DETAIL_NO_SPOKEN,
        "reason_class": None,
        "note": "Weighted picker (regime shadow). STRAT-001–014 vote, they do not fill. NO_PROMOTE.",
        "weighted": True, "w_ce": round(w_ce, 6), "w_pe": round(w_pe, 6),
    }
    if not spoken:
        return base
    eq = lambda a, b: math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)  # noqa: E731
    mean_w = (w_ce + w_pe) / len(spoken)
    if w_ce > 0 and w_pe > 0 and eq(w_ce, w_pe):
        return {**base, "detail": pk.DETAIL_TIE, "skip": pk.HOLD_TIE}
    if w_ce > 0 and w_pe > 0 and abs(w_ce - w_pe) <= mean_w * (1 + 1e-9) and min(w_ce, w_pe) >= 7 * mean_w * (1 - 1e-9):
        return {**base, "detail": pk.DETAIL_CLOSE, "skip": pk.HOLD_CLOSE}

    class_w: dict[str, float] = {}
    class_side: dict[str, Counter] = {}
    for v in spoken:
        class_w[v.reason_class] = class_w.get(v.reason_class, 0.0) + w(v)
        class_side.setdefault(v.reason_class, Counter())[str(v.side)] += w(v)
    ranked = sorted(class_w.items(), key=lambda kv: kv[1], reverse=True)  # stable: ties keep first-seen order
    if w_ce > 0 and w_pe > 0:
        if len(ranked) >= 2 and eq(ranked[0][1], ranked[1][1]):
            return {**base, "detail": pk.DETAIL_SOUP, "skip": pk.HOLD_SOUP, "reason_class": "SOUP"}
        win_class = ranked[0][0]
        ce_c, pe_c = float(class_side[win_class].get("CE", 0)), float(class_side[win_class].get("PE", 0))
        if eq(ce_c, pe_c):
            return {**base, "detail": pk.DETAIL_TIE, "skip": pk.HOLD_TIE, "reason_class": win_class}
        side = "CE" if ce_c > pe_c else "PE"
    else:
        side = "CE" if w_ce > w_pe else "PE"
        win_class = ranked[0][0] if ranked else pk.REASON_CONFIRM

    idx_dir = (classified or {}).get("index_direction") or (classified or {}).get("direction")
    if (side == "CE" and idx_dir == "DOWN") or (side == "PE" and idx_dir == "UP") or pk._index_against(side, prev, closed):
        return {**base, "side": None, "detail": pk.DETAIL_INDEX, "skip": pk.HOLD_INDEX_AGAINST,
                "reason_class": win_class, "held_side": side}
    return {**base, "side": side, "action": "TICKET", "skip": None, "detail": pk.DETAIL_OK, "reason_class": win_class}
