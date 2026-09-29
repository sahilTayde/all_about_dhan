"""Univariate lift, 2-3 feature combos, tree/logit summaries. Train-only."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import replace
from typing import Any

from exitlab.r3_core import FeatRow
from exitlab.r3_ml import fit_logit, fit_tree, tree_rules

CLOCK_FEATS = frozenset({"tod_min", "mins_to_1515", "age_min"})

FEAT_NAMES = [
    "ret_since_entry",
    "pts_since_entry",
    "peak_dd",
    "peak_dd_pts",
    "mom_1",
    "mom_3",
    "mom_5",
    "mom_10",
    "body_wick",
    "range_expand",
    "mins_since_high",
    "vol_chg",
    "oi_chg",
    "idx_1",
    "idx_5",
    "idx_15",
    "dist_vwap",
    "dist_high",
    "dist_low",
    "fh_break",
    "round100",
    "mins_to_1515",
    "iv_chg",
    "tod_min",
    "opp_mom3",
    "delta_proxy",
    "lower_highs_4",
    "age_min",
    "ce",
    "expiry",
    "regime_chop",
    "regime_trend",
]


def _ys(rows: list[FeatRow], which: str = "15") -> list[int]:
    key = {
        "5": "label_5",
        "15": "label_15",
        "30": "label_30",
        "eod": "label_eod",
    }[which]
    return [1 if getattr(r, key) == "GOOD_EXIT" else 0 for r in rows]


def _pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * (len(xs) - 1)))]


def univariate(rows: list[FeatRow], *, which: str = "15") -> list[dict[str, Any]]:
    ys = _ys(rows, which)
    base = (sum(ys) / len(ys)) if ys else 0.0
    out: list[dict[str, Any]] = []
    for name in FEAT_NAMES:
        vals = [(r.feats.get(name), ys[i]) for i, r in enumerate(rows)]
        nums = [(float(v), y) for v, y in vals if v is not None]
        if len(nums) < 40:
            out.append({"feat": name, "n": len(nums), "note": "DATA_INSUFFICIENT"})
            continue
        q25 = _pct([v for v, _ in nums], 0.25)
        q75 = _pct([v for v, _ in nums], 0.75)
        hi = [y for v, y in nums if v >= q75]
        lo = [y for v, y in nums if v <= q25]
        p_hi = sum(hi) / len(hi) if hi else 0.0
        p_lo = sum(lo) / len(lo) if lo else 0.0
        lift_hi = (p_hi / base) if base > 1e-12 else None
        lift_lo = (p_lo / base) if base > 1e-12 else None
        out.append(
            {
                "feat": name,
                "n": len(nums),
                "base_good": base,
                "q25": q25,
                "q75": q75,
                "p_good_high": p_hi,
                "p_good_low": p_lo,
                "lift_high": lift_hi,
                "lift_low": lift_lo,
                "best_dir": "high" if (lift_hi or 0) >= (lift_lo or 0) else "low",
                "best_lift": max(lift_hi or 0, lift_lo or 0),
            }
        )
    out.sort(key=lambda r: -(r.get("best_lift") or 0))
    return out


def combo_table(
    rows: list[FeatRow], uni: list[dict[str, Any]], *, which: str = "15"
) -> list[dict[str, Any]]:
    ys = _ys(rows, which)
    base = (sum(ys) / len(ys)) if ys else 0.0
    top = [u for u in uni if u.get("best_lift") and u.get("n", 0) >= 80][:12]
    cands: list[dict[str, Any]] = []

    def _mask(name: str, direction: str, q25: float, q75: float) -> list[int]:
        hit = []
        for r in rows:
            v = r.feats.get(name)
            if v is None:
                hit.append(0)
                continue
            high_ok = direction == "high" and float(v) >= q75
            low_ok = direction == "low" and float(v) <= q25
            hit.append(1 if high_ok or low_ok else 0)
        return hit

    masks = {
        u["feat"]: (_mask(u["feat"], u["best_dir"], u["q25"], u["q75"]), u["best_dir"])
        for u in top
        if "q25" in u
    }
    names = list(masks)
    # pairs
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            ma, da = masks[names[a]]
            mb, db = masks[names[b]]
            both = [ma[i] and mb[i] for i in range(len(ys))]
            n = sum(both)
            if n < 25:
                continue
            goods = sum(ys[i] for i in range(len(ys)) if both[i])
            p = goods / n
            lift = (p / base) if base > 1e-12 else 0.0
            cands.append(
                {
                    "feats": f"{names[a]}:{da}+{names[b]}:{db}",
                    "n": n,
                    "hit_rate": p,
                    "fire_rate": n / len(ys),
                    "lift": lift,
                    "score": lift * math.sqrt(n),
                    "kind": "pair",
                }
            )
    # triples from the six strongest
    six = names[:6]
    for a in range(len(six)):
        for b in range(a + 1, len(six)):
            for c in range(b + 1, len(six)):
                ma, da = masks[six[a]]
                mb, db = masks[six[b]]
                mc, dc = masks[six[c]]
                both = [ma[i] and mb[i] and mc[i] for i in range(len(ys))]
                n = sum(both)
                if n < 20:
                    continue
                goods = sum(ys[i] for i in range(len(ys)) if both[i])
                p = goods / n
                lift = (p / base) if base > 1e-12 else 0.0
                cands.append(
                    {
                        "feats": f"{six[a]}:{da}+{six[b]}:{db}+{six[c]}:{dc}",
                        "n": n,
                        "hit_rate": p,
                        "fire_rate": n / len(ys),
                        "lift": lift,
                        "score": lift * math.sqrt(n),
                        "kind": "triple",
                    }
                )
    cands.sort(key=lambda r: -r["score"])
    return cands[:20]


def split_slices(rows: list[FeatRow], pred: list[int], ys: list[int]) -> dict[str, Any]:
    def pack(idx: list[int]) -> dict[str, Any]:
        if not idx:
            return {"n": 0, "note": "DATA_INSUFFICIENT"}
        n = len(idx)
        fires = sum(pred[i] for i in idx)
        goods = sum(ys[i] for i in idx if pred[i])
        return {
            "n": n,
            "fires": fires,
            "hit_rate": (goods / fires) if fires else None,
            "fire_rate": fires / n,
        }

    ce = [i for i, r in enumerate(rows) if r.side == "CE"]
    pe = [i for i, r in enumerate(rows) if r.side == "PE"]
    trend = [i for i, r in enumerate(rows) if (r.feats.get("regime_trend") or 0) >= 0.5]
    chop = [i for i, r in enumerate(rows) if (r.feats.get("regime_chop") or 0) >= 0.5]
    exp = [i for i, r in enumerate(rows) if (r.feats.get("expiry") or 0) >= 0.5]
    nex = [i for i, r in enumerate(rows) if (r.feats.get("expiry") or 0) < 0.5]
    return {
        "CE": pack(ce),
        "PE": pack(pe),
        "trend": pack(trend),
        "chop": pack(chop),
        "expiry": pack(exp),
        "normal": pack(nex),
    }


def combo_pred(rows: list[FeatRow], spec: str) -> list[int]:
    parts = spec.split("+")
    out = [1] * len(rows)
    for part in parts:
        name, direction = part.split(":")
        vals = [r.feats.get(name) for r in rows]
        nums = [float(v) for v in vals if v is not None]
        if len(nums) < 10:
            return [0] * len(rows)
        q25, q75 = _pct(nums, 0.25), _pct(nums, 0.75)
        for i, v in enumerate(vals):
            if v is None:
                out[i] = 0
                continue
            ok = float(v) >= q75 if direction == "high" else float(v) <= q25
            if not ok:
                out[i] = 0
    return out


def saved_vs_hold(
    rows: list[FeatRow],
    pred: list[int],
    minutes_by_id: dict[str, list[Any]],
    entry_px: dict[str, float],
) -> float | None:
    """Average pts captured vs sitting: fire at that minute vs last mark."""
    by_entry: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        if pred[i]:
            by_entry[r.entry_id].append(r.i)
    diffs: list[float] = []
    for eid, idxs in by_entry.items():
        path = minutes_by_id.get(eid) or []
        if not path:
            continue
        last = next((m.ltp for m in reversed(path) if m.ltp is not None), None)
        if last is None:
            continue
        first_i = min(idxs)
        if first_i >= len(path) or path[first_i].ltp is None:
            continue
        diffs.append(float(path[first_i].ltp) - float(last))
    if not diffs:
        return None
    return sum(diffs) / len(diffs)


def matrix(rows: list[FeatRow]) -> tuple[list[list[float | None]], list[str]]:
    names = FEAT_NAMES
    xs: list[list[float | None]] = []
    for r in rows:
        xs.append([r.feats.get(n) for n in names])
    return xs, names


def fit_simple_models(rows: list[FeatRow], *, which: str = "15") -> dict[str, Any]:
    ys = _ys(rows, which)
    xs, names = matrix(rows)
    tree = fit_tree(xs, ys, depth=3, min_leaf=max(40, len(ys) // 80))
    logit = fit_logit(xs, ys)
    return {
        "tree_rules": tree_rules(tree, names),
        "logit_ok": bool(logit.get("ok")),
        "logit_w": [
            {"feat": "bias", "w": logit["w"][0]},
            *[
                {"feat": names[j], "w": logit["w"][j + 1]}
                for j in range(len(names))
                if j + 1 < len(logit["w"])
            ],
        ],
        "tree": tree,
        "logit": logit,
        "names": names,
    }


def is_clock_spec(spec: str) -> bool:
    """True when every named feature is a clock / time-of-day column."""
    names = [part.split(":")[0] for part in spec.split("+") if part]
    return bool(names) and all(name in CLOCK_FEATS for name in names)


def permute_labels_within_day(rows: list[FeatRow], *, seed: int) -> list[FeatRow]:
    """Shuffle GOOD_EXIT labels inside each session. Features stay put."""
    rng = random.Random(seed)
    by: dict[str, list[FeatRow]] = defaultdict(list)
    for row in rows:
        by[row.session].append(row)
    out: list[FeatRow] = []
    for grp in by.values():
        labs = [(r.label_5, r.label_15, r.label_30, r.label_eod) for r in grp]
        rng.shuffle(labs)
        for row, lab in zip(grp, labs, strict=False):
            out.append(
                replace(
                    row,
                    label_5=lab[0],
                    label_15=lab[1],
                    label_30=lab[2],
                    label_eod=lab[3],
                )
            )
    return out
