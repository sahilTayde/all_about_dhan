"""Fit / score ML-001. Holiday-safe: cache only. Never writes production MIX params."""

from __future__ import annotations

from collections import Counter
from typing import Any, Optional, Sequence

from desk_ml.features import Triple, build_feature_rows, vectors_from_rows
from desk_ml.model import IsolationForest, KMeans, StandardScaler, name_clusters, score_row
from desk_ml.persist import (
    MODEL_VERSION,
    default_model_path,
    load_bundle,
    pack_estimators,
    save_bundle,
    unpack_estimators,
)
from desk_ml.tape import embargo_train_rows, labels_from_paper_ledger, load_dual_tape_triples, load_triples, thin_hold


def fit_from_rows(rows: Sequence[dict], *, seed: int = 14, k: int = 4) -> dict[str, Any]:
    X = vectors_from_rows(rows)
    scaler = StandardScaler.fit(X)
    Xs = scaler.transform(X)
    kmeans = KMeans(k=k, seed=seed).fit(Xs)
    cents_orig = [scaler.inverse(c) for c in kmeans.centroids]
    labels = name_clusters(cents_orig)
    forest = IsolationForest(seed=seed).fit(Xs)
    assigned = kmeans.predict(Xs)
    names = ("idx_ret", "ce_ret", "pe_ret", "spread_chg", "abs_residual")
    return {
        "scaler": scaler,
        "kmeans": kmeans,
        "cluster_labels": labels,
        "forest": forest,
        "cluster_sizes": dict(Counter(labels[i] for i in assigned)),
        "n_rows": len(X),
        "centroids_orig": {
            labels[i]: {name: round(cents_orig[i][j], 6) for j, name in enumerate(names)}
            for i in range(k)
        },
    }


def fit_underlying(
    underlying: str,
    *,
    root=None,
    seed: int = 14,
    persist: bool = True,
    triples: Optional[Sequence[Triple]] = None,
    min_ts: Optional[int] = None,
    max_ts: Optional[int] = None,
    embargo_bars: int = 5,
) -> dict[str, Any]:
    if triples is None:
        triples, tape_meta = load_triples(underlying, root=root, min_ts=min_ts, max_ts=max_ts)
    else:
        tape_meta = {"aligned_triples": len(triples), "source": "caller"}
    rows = build_feature_rows(list(triples))
    train_rows, embargo = embargo_train_rows(rows, embargo_bars=embargo_bars)
    if len(train_rows) < 16:
        return {
            "ok": False,
            "status": "DATA_INSUFFICIENT",
            "underlying": underlying.upper(),
            "n_feature_rows": len(rows),
            "embargo": embargo,
            "tape": tape_meta,
            "note": "Need ≥16 aligned 1m feature rows after embargo. Holiday: do not fetch live Dhan.",
            "promote": False,
            "execution": "refused",
            "production_params_written": False,
        }
    fitted = fit_from_rows(train_rows, seed=seed)
    supervised = labels_from_paper_ledger(root)
    bundle = {
        "underlying": underlying.upper(),
        "algorithm": "kmeans+isolation_forest",
        "model_version": MODEL_VERSION,
        "k": 4,
        "seed": seed,
        "n_rows": fitted["n_rows"],
        "n_feature_rows": len(rows),
        "cluster_sizes": fitted["cluster_sizes"],
        "centroids_orig": fitted["centroids_orig"],
        "train_window": {"from_ts": train_rows[0]["ts"], "to_ts": train_rows[-1]["ts"]},
        "embargo": embargo,
        "tape": tape_meta,
        "supervised": supervised,
        "win_rate": None,
        "verdict": "NO_PROMOTE",
        "promote": False,
        "production_params_written": False,
        "session_note": "cache-only fit; embargo is leakage hygiene not CPCV/OOS; no live Dhan; no MIX param write",
        **pack_estimators(
            scaler=fitted["scaler"],
            kmeans=fitted["kmeans"],
            cluster_labels=fitted["cluster_labels"],
            forest=fitted["forest"],
        ),
    }
    if persist:
        path = default_model_path(underlying, root=root)
        save_bundle(path, bundle)
        bundle["path"] = str(path)
    bundle["ok"] = True
    bundle["status"] = "FIT_OK"
    return bundle


def score_last(
    underlying: str,
    *,
    root=None,
    model_path=None,
    triples: Optional[Sequence[Triple]] = None,
    source: str = "cache",
) -> dict[str, Any]:
    path = model_path or default_model_path(underlying, root=root)
    if not path.is_file():
        return thin_hold(
            underlying=underlying,
            reason=f"no model at {path} — run python -m desk_ml fit first",
        )
    bundle = load_bundle(path)
    scaler, kmeans, labels, forest = unpack_estimators(bundle)
    src = (source or "cache").strip().lower()
    if triples is not None:
        used = list(triples)
        tape_meta: dict[str, Any] = {"aligned_triples": len(used), "source": "caller"}
    elif src in {"dual-tape", "dual_tape", "live-paper"}:
        used, tape_meta = load_dual_tape_triples(underlying, root=root)
        if len(used) < 2:
            return thin_hold(
                underlying=underlying,
                reason="DATA_INSUFFICIENT: need ≥2 dual-tape ticks with INDEX+ATM CE+PE LTP",
                tape=tape_meta,
            )
    else:
        used, tape_meta = load_triples(underlying, root=root)
    rows = build_feature_rows(used)
    if not rows:
        return thin_hold(
            underlying=underlying,
            reason="no feature rows to score after bar close",
            tape=tape_meta,
        )
    last = rows[-1]
    names = ("idx_ret", "ce_ret", "pe_ret", "spread_chg", "abs_residual")
    x_orig = [last[name] for name in names]
    x_scaled = scaler.transform([x_orig])[0]
    scored = score_row(x_scaled=x_scaled, x_orig=x_orig, kmeans=kmeans, cluster_labels=labels, forest=forest)
    follow_gap_hold = bool(scored.get("premium_divergence")) or scored.get("overlay") == "HOLD"
    scored.update(
        {
            "ok": True,
            "status": "SCORE_OK",
            "underlying": underlying.upper(),
            "ts": last["ts"],
            "model_version": bundle.get("model_version"),
            "score_source": tape_meta.get("source"),
            "tape": tape_meta,
            "follow_gap": follow_gap_hold,
            "session_action": "HOLD" if follow_gap_hold else "WATCH_ONLY",
            "production_params_written": False,
            "oos_claim": False,
            "attach": (
                "Call after 1m bar close (or dual-tape tick with two LTPs). "
                "FOLLOW-GAP / overlay HOLD keeps the dealer from new paper CE/PE. "
                "Never overrides deterministic hard stops. ExecutionClient not used."
            ),
        }
    )
    return scored


def score_features_dict(features: dict[str, float], bundle: dict[str, Any]) -> dict[str, Any]:
    scaler, kmeans, labels, forest = unpack_estimators(bundle)
    names = ("idx_ret", "ce_ret", "pe_ret", "spread_chg", "abs_residual")
    x_orig = [float(features[n]) for n in names]
    x_scaled = scaler.transform([x_orig])[0]
    return score_row(x_scaled=x_scaled, x_orig=x_orig, kmeans=kmeans, cluster_labels=labels, forest=forest)
