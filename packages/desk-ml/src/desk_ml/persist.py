"""JSON model bundle under data/recon/ml/. Gitignored payloads. No MIX writes."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from desk_ml.features import FEATURE_NAMES, FEATURE_SET_VERSION
from desk_ml.model import IsolationForest, KMeans, StandardScaler

MODEL_VERSION = "ml001-kmeans-if-v1"
IST = timezone(timedelta(hours=5, minutes=30))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def ml_dir(root: Optional[Path] = None) -> Path:
    path = (root or repo_root()) / "data" / "recon" / "ml"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_model_path(underlying: str, *, root: Optional[Path] = None) -> Path:
    return ml_dir(root) / f"ml001_kmeans_if_{underlying.upper()}.json"


def save_bundle(path: Path, bundle: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(bundle)
    payload.setdefault("saved_at_ist", datetime.now(IST).isoformat(timespec="seconds"))
    payload.setdefault("model_version", MODEL_VERSION)
    payload.setdefault("feature_set_version", FEATURE_SET_VERSION)
    payload.setdefault("feature_names", list(FEATURE_NAMES))
    payload.setdefault("promote", False)
    payload.setdefault("verdict", "NO_PROMOTE")
    payload.setdefault("execution", "refused")
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def load_bundle(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pack_estimators(*, scaler: StandardScaler, kmeans: KMeans, cluster_labels: dict[int, str], forest: IsolationForest) -> dict[str, Any]:
    return {
        "scaler": scaler.to_dict(),
        "kmeans": {
            "k": kmeans.k,
            "seed": kmeans.seed,
            "inertia": kmeans.inertia_,
            "centroids_scaled": kmeans.centroids,
        },
        "cluster_labels": {str(k): v for k, v in cluster_labels.items()},
        "isolation_forest": forest.to_dict(),
    }


def unpack_estimators(bundle: dict[str, Any]) -> tuple[StandardScaler, KMeans, dict[int, str], IsolationForest]:
    scaler = StandardScaler.from_dict(bundle["scaler"])
    km_raw = bundle["kmeans"]
    kmeans = KMeans(k=int(km_raw.get("k") or 4), seed=int(km_raw.get("seed") or 14))
    kmeans.centroids = [list(c) for c in km_raw["centroids_scaled"]]
    kmeans.inertia_ = float(km_raw.get("inertia") or 0.0)
    labels = {int(k): str(v) for k, v in (bundle.get("cluster_labels") or {}).items()}
    forest = IsolationForest.from_dict(bundle["isolation_forest"])
    return scaler, kmeans, labels, forest
