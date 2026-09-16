"""Replay HOLD overlays vs later ATM premium. Diagnostic only. No win rate. No MIX write."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from desk_ml.features import Triple, build_feature_rows, vectors_from_rows
from desk_ml.fit import fit_from_rows, score_features_dict
from desk_ml.model import OVERLAY_HOLD, premium_divergence_pattern
from desk_ml.mrr import MRR_WINDOWS, Z_HOLD, ols_beta, rolling_z
from desk_ml.persist import pack_estimators
from desk_ml.tape import embargo_train_rows, load_triples

HORIZON_BARS = 15
EPS = 1e-9


def _fwd(now: float, later: float) -> Optional[float]:
    if abs(now) < EPS:
        return None
    return (later - now) / abs(now)


def _mean(vals: Sequence[float]) -> Optional[float]:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 6)


def _bucket(name: str, holds: Sequence[bool], straddles: Sequence[Optional[float]]) -> dict[str, Any]:
    on: list[float] = []
    off: list[float] = []
    for flag, fwd in zip(holds, straddles):
        if fwd is None:
            continue
        (on if flag else off).append(fwd)
    return {
        "rule": name,
        "n_hold": sum(1 for h in holds if h),
        "n_trade": sum(1 for h in holds if not h),
        "mean_straddle_fwd_when_hold": _mean(on),
        "mean_straddle_fwd_when_not_hold": _mean(off),
        "note": (
            "Negative straddle fwd = ATM CE+PE bled. HOLD is useful if "
            "mean_when_hold is worse (more negative) than mean_when_not_hold. "
            "Not a win rate."
        ),
    }


def replay_hold(
    underlying: str,
    *,
    root=None,
    triples: Optional[Sequence[Triple]] = None,
    horizon_bars: int = HORIZON_BARS,
    seed: int = 14,
    embargo_bars: int = 5,
    windows: Sequence[int] = MRR_WINDOWS,
) -> dict[str, Any]:
    if triples is None:
        used, tape = load_triples(underlying, root=root)
    else:
        used, tape = list(triples), {"aligned_triples": len(triples), "source": "caller"}
    rows = build_feature_rows(used)
    horizon = max(1, int(horizon_bars))
    if len(rows) < 16 + horizon:
        return {
            "ok": False,
            "status": "DATA_INSUFFICIENT",
            "underlying": underlying.upper(),
            "n_feature_rows": len(rows),
            "tape": tape,
            "win_rate": None,
            "promote": False,
            "production_params_written": False,
            "note": f"Need ≥{16 + horizon} feature rows for fit + {horizon}-bar forward.",
        }
    train, embargo = embargo_train_rows(rows, embargo_bars=embargo_bars)
    if len(train) < 16:
        return {
            "ok": False,
            "status": "DATA_INSUFFICIENT",
            "embargo": embargo,
            "win_rate": None,
            "promote": False,
            "production_params_written": False,
        }
    fitted = fit_from_rows(train, seed=seed)
    bundle = pack_estimators(
        scaler=fitted["scaler"],
        kmeans=fitted["kmeans"],
        cluster_labels=fitted["cluster_labels"],
        forest=fitted["forest"],
    )
    idx_rets = [r["idx_ret"] for r in rows]
    k_ce = ols_beta(idx_rets, [r["ce_ret"] for r in rows])
    k_pe = ols_beta(idx_rets, [r["pe_ret"] for r in rows])
    residual: list[float] = []
    if k_ce is not None and k_pe is not None:
        residual = [
            0.5 * ((r["ce_ret"] - k_ce * r["idx_ret"]) + (r["pe_ret"] - k_pe * r["idx_ret"]))
            for r in rows
        ]
    zs_by_window = {int(w): rolling_z(residual, int(w)) if residual else [] for w in list(windows)[:3]}

    names = ("idx_ret", "ce_ret", "pe_ret", "spread_chg", "abs_residual")
    gap_flags: list[bool] = []
    ml001_flags: list[bool] = []
    ml002_flags: list[bool] = []
    union_flags: list[bool] = []
    straddles: list[Optional[float]] = []
    n = len(rows)
    for i, row in enumerate(rows):
        later = i + horizon
        if later >= n:
            continue
        ce_f = _fwd(float(row["ce_close"]), float(rows[later]["ce_close"]))
        pe_f = _fwd(float(row["pe_close"]), float(rows[later]["pe_close"]))
        straddle = None if ce_f is None or pe_f is None else 0.5 * (ce_f + pe_f)
        feat = {name: float(row[name]) for name in names}
        scored = score_features_dict(feat, bundle)
        gap = premium_divergence_pattern(row["idx_ret"], row["ce_ret"], row["pe_ret"])
        ml001 = scored.get("overlay") == OVERLAY_HOLD
        z_hold = False
        pref_w = int(list(windows)[:3][-1]) if windows else 90
        zs = zs_by_window.get(pref_w) or []
        if i < len(zs) and zs[i] is not None:
            z_hold = abs(float(zs[i])) >= Z_HOLD
        gap_flags.append(gap)
        ml001_flags.append(ml001)
        ml002_flags.append(z_hold)
        union_flags.append(gap or ml001 or z_hold)
        straddles.append(straddle)

    rules = [
        _bucket("FOLLOW_GAP", gap_flags, straddles),
        _bucket("ML-001_HOLD", ml001_flags, straddles),
        _bucket("ML-002_Z>=2", ml002_flags, straddles),
        _bucket("UNION_HOLD", union_flags, straddles),
    ]
    return {
        "ok": True,
        "status": "REPLAY_OK",
        "job": "ML_HOLD_REPLAY",
        "underlying": underlying.upper(),
        "horizon_bars": horizon,
        "horizon_note": "1m bars; 15 ≈ 15 minutes. ATM CE+PE straddle return, not lots×₹.",
        "n_scored": len(straddles),
        "n_feature_rows": n,
        "tape": tape,
        "embargo": embargo,
        "k_ce": None if k_ce is None else round(float(k_ce), 6),
        "k_pe": None if k_pe is None else round(float(k_pe), 6),
        "ml002_window": int(list(windows)[:3][-1]) if windows else 90,
        "rules": rules,
        "win_rate": None,
        "promote": False,
        "production_params_written": False,
        "oos_claim": False,
        "execution": "refused",
        "gate": "BACKTEST_REQUIRED",
        "verdict": "NO_PROMOTE",
        "note": (
            "ML bucket is HOLD/WATCH, not MIX-DEFAULT-BUY. "
            "PAPER_TRAIN_NO_DENY bypasses HOLD. Replay does not write MIX params."
        ),
    }
