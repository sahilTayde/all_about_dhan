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
from desk_ml.tape import labels_from_paper_ledger, load_triples


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
) -> dict[str, Any]:
    if triples is None:
        triples, tape_meta = load_triples(underlying, root=root)
    else:
        tape_meta = {"aligned_triples": len(triples), "source": "caller"}
    rows = build_feature_rows(list(triples))
    if len(rows) < 16:
        return {
            "ok": False,
            "status": "DATA_INSUFFICIENT",
            "underlying": underlying.upper(),
            "n_feature_rows": len(rows),
            "tape": tape_meta,
            "note": "Need ≥16 aligned 1m feature rows. Holiday: do not fetch live Dhan.",
            "promote": False,
            "execution": "refused",
        }
    fitted = fit_from_rows(rows, seed=seed)
    supervised = labels_from_paper_ledger(root)
    bundle = {
        "underlying": underlying.upper(),
        "algorithm": "kmeans+isolation_forest",
        "model_version": MODEL_VERSION,
        "k": 4,
        "seed": seed,
        "n_rows": fitted["n_rows"],
        "cluster_sizes": fitted["cluster_sizes"],
        "centroids_orig": fitted["centroids_orig"],
        "train_window": {"from_ts": rows[0]["ts"], "to_ts": rows[-1]["ts"]},
        "tape": tape_meta,
        "supervised": supervised,
        "win_rate": None,
        "verdict": "NO_PROMOTE",
        "promote": False,
        "production_params_written": False,
        "session_note": "2026-09-14 Ganesh Chaturthi — NSE closed; fit historical recon cache only",
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


def score_last(underlying: str, *, root=None, model_path=None, triples: Optional[Sequence[Triple]] = None) -> dict[str, Any]:
    path = model_path or default_model_path(underlying, root=root)
    if not path.is_file():
        return {
            "ok": False,
            "status": "DATA_INSUFFICIENT",
            "reason": f"no model at {path} — run python -m desk_ml fit first",
            "promote": False,
        }
    bundle = load_bundle(path)
    scaler, kmeans, labels, forest = unpack_estimators(bundle)
    if triples is None:
        triples, tape_meta = load_triples(underlying, root=root)
    else:
        tape_meta = {"aligned_triples": len(triples), "source": "caller"}
    rows = build_feature_rows(list(triples))
    if not rows:
        return {
            "ok": False,
            "status": "DATA_INSUFFICIENT",
            "reason": "no feature rows to score after bar close",
            "tape": tape_meta,
            "promote": False,
        }
    last = rows[-1]
    names = ("idx_ret", "ce_ret", "pe_ret", "spread_chg", "abs_residual")
    x_orig = [last[name] for name in names]
    x_scaled = scaler.transform([x_orig])[0]
    scored = score_row(x_scaled=x_scaled, x_orig=x_orig, kmeans=kmeans, cluster_labels=labels, forest=forest)
    scored.update(
        {
            "ok": True,
            "status": "SCORE_OK",
            "underlying": underlying.upper(),
            "ts": last["ts"],
            "model_version": bundle.get("model_version"),
            "tape": tape_meta,
            "attach": (
                "Call after 1m bar close. Overlay HOLD/DIVERGENCE may keep the dealer "
                "from new paper CE/PE; never overrides deterministic hard stops; never orders."
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
