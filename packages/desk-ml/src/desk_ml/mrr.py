"""ML-002: OU on MIX-FORM residual + VWMA(MRR) window. Overlay HOLD. NO_PROMOTE.

Book mapping (smile / Derman): OU on residual, not implied vol. Half-life is a
snap-back metaphor, not a vega trade. FOLLOW-GAP overlay HOLDs new CE/PE.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Sequence

from desk_ml.features import Triple, build_feature_rows
from desk_ml.model import OVERLAY_HOLD, OVERLAY_NONE, premium_divergence_pattern
from desk_ml.persist import ml_dir, repo_root, save_bundle
from desk_ml.tape import load_premium_ohlcv, load_triples

MRR_WINDOWS = (40, 60, 90)
Z_HOLD = 2.0
MODEL_VERSION = "ml002-mrr-ou-v1"
EPS = 1e-12


def ols_beta(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    xx = 0.0
    xy = 0.0
    n = min(len(x), len(y))
    if n < 8:
        return None
    for i in range(n):
        xx += x[i] * x[i]
        xy += x[i] * y[i]
    if xx < EPS:
        return None
    return xy / xx


def ou_ar1(series: Sequence[float]) -> dict[str, Any]:
    """Discrete OU via AR(1) on demeaned residual. Not a vol model."""
    if len(series) < 16:
        return {"status": "DATA_INSUFFICIENT", "n": len(series), "phi": None, "kappa": None, "half_life_bars": None}
    mu = sum(series) / len(series)
    demeaned = [v - mu for v in series]
    num = 0.0
    den = 0.0
    for i in range(1, len(demeaned)):
        num += demeaned[i] * demeaned[i - 1]
        den += demeaned[i - 1] * demeaned[i - 1]
    if den < EPS:
        return {"status": "DATA_INSUFFICIENT", "n": len(series), "phi": None, "kappa": None, "half_life_bars": None, "mu": mu}
    phi = num / den
    out: dict[str, Any] = {
        "status": "FIT_OK",
        "n": len(series),
        "mu": round(mu, 8),
        "phi": round(phi, 6),
        "kappa": None,
        "half_life_bars": None,
        "mean_reverting": False,
    }
    if 0.0 < phi < 1.0:
        kappa = -math.log(phi)
        out["kappa"] = round(kappa, 6)
        out["half_life_bars"] = round(math.log(2.0) / kappa, 3) if kappa > EPS else None
        out["mean_reverting"] = True
    else:
        out["status"] = "NOT_MEAN_REVERTING"
        out["note"] = "phi not in (0,1); residual is not an OU snap-back on this window"
    return out


def vwma(closes: Sequence[float], volumes: Sequence[float], length: int) -> list[Optional[float]]:
    out: list[Optional[float]] = []
    for i in range(len(closes)):
        if i + 1 < length:
            out.append(None)
            continue
        sl_c = closes[i + 1 - length : i + 1]
        sl_v = volumes[i + 1 - length : i + 1]
        den = sum(sl_v)
        if den <= 0:
            out.append(sum(sl_c) / length)
        else:
            out.append(sum(c * v for c, v in zip(sl_c, sl_v)) / den)
    return out


def rolling_z(values: Sequence[float], length: int) -> list[Optional[float]]:
    out: list[Optional[float]] = []
    for i in range(len(values)):
        if i + 1 < length:
            out.append(None)
            continue
        chunk = values[i + 1 - length : i + 1]
        m = sum(chunk) / length
        var = sum((v - m) ** 2 for v in chunk) / (length - 1)
        if var < EPS:
            out.append(None)
            continue
        out.append((values[i] - m) / math.sqrt(var))
    return out


def _follow_gap(row: dict) -> bool:
    return premium_divergence_pattern(row["idx_ret"], row["ce_ret"], row["pe_ret"])


def score_window(
    rows: Sequence[dict],
    *,
    window: int,
    k_ce: float,
    k_pe: float,
    pe_closes: Sequence[float],
    pe_vols: Sequence[float],
) -> dict[str, Any]:
    ce_resid = [row["ce_ret"] - k_ce * row["idx_ret"] for row in rows]
    pe_resid = [row["pe_ret"] - k_pe * row["idx_ret"] for row in rows]
    residual = [0.5 * (a + b) for a, b in zip(ce_resid, pe_resid)]
    zs = rolling_z(residual, window)
    mrr = vwma(list(pe_closes), list(pe_vols), window)
    n_scored = 0
    n_follow_gap = 0
    n_z_hold = 0
    n_hold = 0
    abs_z: list[float] = []
    last: Optional[dict[str, Any]] = None
    for i, row in enumerate(rows):
        z = zs[i]
        if z is None:
            continue
        n_scored += 1
        gap = _follow_gap(row)
        z_flag = abs(z) >= Z_HOLD
        if gap:
            n_follow_gap += 1
        if z_flag:
            n_z_hold += 1
        overlay = OVERLAY_HOLD if (gap or z_flag) else OVERLAY_NONE
        if overlay == OVERLAY_HOLD:
            n_hold += 1
        abs_z.append(abs(z))
        reason = "PREMIUM_DIVERGENCE" if gap else ("RESIDUAL_Z" if z_flag else "REGIME_OK")
        last = {
            "ts": row["ts"],
            "overlay": overlay,
            "reason_code": reason,
            "follow_gap": gap,
            "residual_z": round(float(z), 6),
            "pe_mrr": None if mrr[i] is None else round(float(mrr[i]), 6),
            "pe_close": row.get("pe_close"),
            "allow_new_paper_ce_pe": overlay == OVERLAY_NONE,
        }
    ou = ou_ar1(residual)
    mean_abs_z = (sum(abs_z) / len(abs_z)) if abs_z else None
    return {
        "window": window,
        "n_feature_rows": len(rows),
        "n_scored": n_scored,
        "n_follow_gap": n_follow_gap,
        "n_z_hold": n_z_hold,
        "n_hold_overlay": n_hold,
        "mean_abs_z": None if mean_abs_z is None else round(mean_abs_z, 6),
        "ou": ou,
        "last": last,
        "promote": False,
        "win_rate": None,
        "production_params_written": False,
    }


def pick_preferred(tweaks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """At most 3 windows. Prefer mean-reverting OU with finite half-life; not a promote."""
    ok = [
        t
        for t in tweaks
        if t.get("n_scored", 0) >= 16 and (t.get("ou") or {}).get("mean_reverting")
    ]
    if not ok:
        return {
            "window": None,
            "reason": "DATA_INSUFFICIENT: no MRR window in {40,60,90} produced a mean-reverting OU on residual",
            "status": "DATA_INSUFFICIENT",
        }
    def key(t: dict[str, Any]) -> tuple[float, float]:
        hl = float((t.get("ou") or {}).get("half_life_bars") or 1e9)
        maz = float(t.get("mean_abs_z") or 1e9)
        return (hl, maz)

    best = min(ok, key=key)
    return {
        "window": best["window"],
        "reason": "smallest OU half-life among mean-reverting windows (in-sample counts only)",
        "status": "CANDIDATE",
        "half_life_bars": (best.get("ou") or {}).get("half_life_bars"),
        "mean_abs_z": best.get("mean_abs_z"),
        "n_hold_overlay": best.get("n_hold_overlay"),
        "n_scored": best.get("n_scored"),
    }


def mrr_fit_underlying(
    underlying: str,
    *,
    root=None,
    windows: Sequence[int] = MRR_WINDOWS,
    persist: bool = True,
    triples: Optional[Sequence[Triple]] = None,
    min_ts: Optional[int] = None,
    max_ts: Optional[int] = None,
) -> dict[str, Any]:
    base = root or repo_root()
    if triples is None:
        triples, tape_meta = load_triples(underlying, root=base, min_ts=min_ts, max_ts=max_ts)
    else:
        tape_meta = {"aligned_triples": len(triples), "source": "caller"}
    rows = build_feature_rows(list(triples))
    if len(rows) < 16:
        return {
            "ok": False,
            "status": "DATA_INSUFFICIENT",
            "model_id": "ML-002",
            "underlying": underlying.upper(),
            "n_feature_rows": len(rows),
            "tape": tape_meta,
            "note": "Need ≥16 aligned 1m feature rows. Cache only; no live Dhan.",
            "promote": False,
            "win_rate": None,
            "production_params_written": False,
            "execution": "refused",
            "verdict": "NO_PROMOTE",
            "gate": "BACKTEST_REQUIRED",
        }
    idx_rets = [r["idx_ret"] for r in rows]
    k_ce = ols_beta(idx_rets, [r["ce_ret"] for r in rows])
    k_pe = ols_beta(idx_rets, [r["pe_ret"] for r in rows])
    if k_ce is None or k_pe is None:
        return {
            "ok": False,
            "status": "DATA_INSUFFICIENT",
            "model_id": "ML-002",
            "reason": "OLS beta undefined on this tape",
            "tape": tape_meta,
            "promote": False,
            "production_params_written": False,
        }
    pe_map = load_premium_ohlcv(underlying, "pe", root=base)
    pe_closes: list[float] = []
    pe_vols: list[float] = []
    for row in rows:
        pair = pe_map.get(int(row["ts"]))
        pe_closes.append(float(row["pe_close"]))
        pe_vols.append(0.0 if pair is None else float(pair[1]))
    wins = list(windows)[:3]
    tweaks = [
        score_window(rows, window=w, k_ce=k_ce, k_pe=k_pe, pe_closes=pe_closes, pe_vols=pe_vols) for w in wins
    ]
    preferred = pick_preferred(tweaks)
    bundle = {
        "ok": True,
        "status": "FIT_OK",
        "model_id": "ML-002",
        "algorithm": "ou_residual+vwma_mrr",
        "model_version": MODEL_VERSION,
        "underlying": underlying.upper(),
        "k_ce": round(k_ce, 6),
        "k_pe": round(k_pe, 6),
        "windows_tried": wins,
        "max_tweaks": 3,
        "tweaks": tweaks,
        "preferred": preferred,
        "tape": tape_meta,
        "n_feature_rows": len(rows),
        "win_rate": None,
        "verdict": "NO_PROMOTE",
        "promote": False,
        "production_params_written": False,
        "gate": "BACKTEST_REQUIRED",
        "execution": "refused",
        "llm": False,
        "layer": "HYPOTHESIS",
        "note": (
            "OU half-life and HOLD counts are in-sample descriptions of residual snap-back. "
            "Not a win rate. FOLLOW-GAP overlay HOLDs new paper CE/PE. No MIX write."
        ),
    }
    if persist:
        path = ml_dir(base) / f"ml002_mrr_ou_{underlying.upper()}.json"
        save_bundle(path, bundle)
        bundle["path"] = str(path)
    return bundle
