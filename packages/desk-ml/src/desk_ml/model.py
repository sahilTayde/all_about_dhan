"""Stdlib KMeans + IsolationForest. Fast enough for 1m overlay; no sklearn required."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from desk_ml.features import FEATURE_NAMES

OVERLAY_HOLD = "HOLD"
OVERLAY_DIVERGENCE = "DIVERGENCE"
OVERLAY_NONE = "NONE"
IDX_FLAT = 1e-5
PREM_FLAT = 1e-4


def _harmonic(n: int) -> float:
    if n <= 1:
        return 0.0
    return sum(1.0 / i for i in range(1, n + 1))


def c_factor(n: int) -> float:
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    return 2.0 * _harmonic(n - 1) - 2.0 * (n - 1) / n


def _sqdist(a: Sequence[float], b: Sequence[float]) -> float:
    return sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))


class StandardScaler:
    def __init__(self, mean: Sequence[float], std: Sequence[float]) -> None:
        self.mean = [float(x) for x in mean]
        self.std = [max(float(s), 1e-9) for s in std]

    @classmethod
    def fit(cls, X: Sequence[Sequence[float]]) -> "StandardScaler":
        if not X:
            raise ValueError("DATA_INSUFFICIENT: no rows to scale")
        d = len(X[0])
        n = len(X)
        mean = [sum(row[j] for row in X) / n for j in range(d)]
        var = [sum((row[j] - mean[j]) ** 2 for row in X) / n for j in range(d)]
        return cls(mean, [math.sqrt(v) for v in var])

    def transform(self, X: Sequence[Sequence[float]]) -> list[list[float]]:
        return [[(row[j] - self.mean[j]) / self.std[j] for j in range(len(self.mean))] for row in X]

    def inverse(self, row: Sequence[float]) -> list[float]:
        return [row[j] * self.std[j] + self.mean[j] for j in range(len(self.mean))]

    def to_dict(self) -> dict[str, list[float]]:
        return {"mean": list(self.mean), "std": list(self.std)}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StandardScaler":
        return cls(payload["mean"], payload["std"])


class KMeans:
    def __init__(self, k: int = 4, *, n_init: int = 8, max_iter: int = 40, seed: int = 14) -> None:
        self.k = k
        self.n_init = n_init
        self.max_iter = max_iter
        self.seed = seed
        self.centroids: list[list[float]] = []
        self.inertia_: float = float("inf")

    def _init_plus(self, X: Sequence[Sequence[float]], rng: random.Random) -> list[list[float]]:
        cents = [list(X[rng.randrange(len(X))])]
        while len(cents) < self.k:
            dists = [min(_sqdist(row, c) for c in cents) for row in X]
            total = sum(dists) or 1.0
            r = rng.random() * total
            acc = 0.0
            pick = X[-1]
            for row, d2 in zip(X, dists):
                acc += d2
                if acc >= r:
                    pick = row
                    break
            cents.append(list(pick))
        return cents

    def fit(self, X: Sequence[Sequence[float]]) -> "KMeans":
        if len(X) < self.k:
            raise ValueError(f"DATA_INSUFFICIENT: need ≥{self.k} rows for KMeans, got {len(X)}")
        d = len(X[0])
        best_c: list[list[float]] = []
        best_in = float("inf")
        for init_i in range(self.n_init):
            rng = random.Random(self.seed + init_i * 17)
            cents = self._init_plus(X, rng)
            for _ in range(self.max_iter):
                buckets: list[list[Sequence[float]]] = [[] for _ in range(self.k)]
                for row in X:
                    j = min(range(self.k), key=lambda i: _sqdist(row, cents[i]))
                    buckets[j].append(row)
                new: list[list[float]] = []
                for i, bucket in enumerate(buckets):
                    if not bucket:
                        new.append(list(X[rng.randrange(len(X))]))
                        continue
                    new.append([sum(p[j] for p in bucket) / len(bucket) for j in range(d)])
                if all(_sqdist(a, b) < 1e-12 for a, b in zip(cents, new)):
                    cents = new
                    break
                cents = new
            inertia = sum(min(_sqdist(row, c) for c in cents) for row in X)
            if inertia < best_in:
                best_in = inertia
                best_c = cents
        self.centroids = best_c
        self.inertia_ = best_in
        return self

    def predict(self, X: Sequence[Sequence[float]]) -> list[int]:
        if not self.centroids:
            raise RuntimeError("KMeans not fitted")
        return [min(range(self.k), key=lambda i: _sqdist(row, self.centroids[i])) for row in X]


def name_clusters(centroids_orig: Sequence[Sequence[float]]) -> dict[int, str]:
    k = len(centroids_orig)
    if k != 4:
        raise ValueError("ML-001 names exactly 4 clusters")
    idx = list(range(k))
    mapping: dict[int, str] = {}
    diverge = max(idx, key=lambda i: abs(centroids_orig[i][4]))
    mapping[diverge] = "DIVERGE"
    rest = [i for i in idx if i != diverge]
    rng = min(rest, key=lambda i: abs(centroids_orig[i][0]))
    mapping[rng] = "RANGE"
    rest = [i for i in rest if i != rng]
    up = max(rest, key=lambda i: centroids_orig[i][0])
    mapping[up] = "TREND_UP"
    mapping[[i for i in rest if i != up][0]] = "TREND_DN"
    return mapping


@dataclass
class IsolationNode:
    size: int
    external: bool
    feat: int = 0
    thr: float = 0.0
    left: Optional["IsolationNode"] = None
    right: Optional["IsolationNode"] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"size": self.size, "external": self.external}
        if not self.external:
            payload["feat"] = self.feat
            payload["thr"] = self.thr
            payload["left"] = self.left.to_dict() if self.left else None
            payload["right"] = self.right.to_dict() if self.right else None
        return payload

    @classmethod
    def from_dict(cls, payload: Optional[dict[str, Any]]) -> Optional["IsolationNode"]:
        if not payload:
            return None
        node = cls(size=int(payload["size"]), external=bool(payload["external"]))
        if not node.external:
            node.feat = int(payload.get("feat") or 0)
            node.thr = float(payload.get("thr") or 0.0)
            node.left = cls.from_dict(payload.get("left"))
            node.right = cls.from_dict(payload.get("right"))
        return node


class IsolationForest:
    def __init__(self, *, n_trees: int = 50, sample_size: int = 256, contamination: float = 0.08, seed: int = 14) -> None:
        self.n_trees = n_trees
        self.sample_size = sample_size
        self.contamination = contamination
        self.seed = seed
        self.trees: list[IsolationNode] = []
        self.threshold: float = 1.0
        self.sample_n: int = sample_size

    def fit(self, X: Sequence[Sequence[float]]) -> "IsolationForest":
        if len(X) < 8:
            raise ValueError("DATA_INSUFFICIENT: IsolationForest needs ≥8 rows")
        self.sample_n = min(self.sample_size, len(X))
        height_limit = max(1, int(math.ceil(math.log2(self.sample_n))))
        rng = random.Random(self.seed)
        self.trees = []
        for _ in range(self.n_trees):
            sample = [X[rng.randrange(len(X))] for _ in range(self.sample_n)]
            self.trees.append(self._grow(sample, 0, height_limit, rng))
        scores = self.anomaly_scores(X)
        ranked = sorted(scores, reverse=True)
        cut = max(1, int(round(self.contamination * len(ranked))))
        self.threshold = ranked[min(cut - 1, len(ranked) - 1)]
        return self

    def _grow(self, X: Sequence[Sequence[float]], depth: int, height_limit: int, rng: random.Random) -> IsolationNode:
        if len(X) <= 1 or depth >= height_limit:
            return IsolationNode(size=len(X), external=True)
        d = len(X[0])
        feat = rng.randrange(d)
        lo = min(row[feat] for row in X)
        hi = max(row[feat] for row in X)
        if hi - lo < 1e-15:
            return IsolationNode(size=len(X), external=True)
        thr = lo + rng.random() * (hi - lo)
        left = [row for row in X if row[feat] < thr]
        right = [row for row in X if row[feat] >= thr]
        if not left or not right:
            return IsolationNode(size=len(X), external=True)
        node = IsolationNode(size=len(X), external=False, feat=feat, thr=thr)
        node.left = self._grow(left, depth + 1, height_limit, rng)
        node.right = self._grow(right, depth + 1, height_limit, rng)
        return node

    def path_length(self, row: Sequence[float], node: IsolationNode, depth: int = 0) -> float:
        if node.external:
            return depth + c_factor(node.size)
        child = node.left if row[node.feat] < node.thr else node.right
        if child is None:
            return float(depth)
        return self.path_length(row, child, depth + 1)

    def anomaly_scores(self, X: Sequence[Sequence[float]]) -> list[float]:
        cn = c_factor(self.sample_n)
        if cn <= 0:
            return [0.0] * len(X)
        out = []
        for row in X:
            avg = sum(self.path_length(row, t) for t in self.trees) / max(len(self.trees), 1)
            out.append(2.0 ** (-avg / cn))
        return out

    def is_outlier(self, score: float) -> bool:
        return score >= self.threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_trees": self.n_trees,
            "sample_size": self.sample_size,
            "sample_n": self.sample_n,
            "contamination": self.contamination,
            "seed": self.seed,
            "threshold": self.threshold,
            "trees": [t.to_dict() for t in self.trees],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "IsolationForest":
        forest = cls(
            n_trees=int(payload.get("n_trees") or 50),
            sample_size=int(payload.get("sample_size") or 256),
            contamination=float(payload.get("contamination") or 0.08),
            seed=int(payload.get("seed") or 14),
        )
        forest.sample_n = int(payload.get("sample_n") or forest.sample_size)
        forest.threshold = float(payload.get("threshold") or 1.0)
        forest.trees = []
        for raw in payload.get("trees") or []:
            node = IsolationNode.from_dict(raw)
            if node is not None:
                forest.trees.append(node)
        return forest


def premium_divergence_pattern(idx_ret: float, ce_ret: float, pe_ret: float) -> bool:
    if idx_ret < -IDX_FLAT and pe_ret <= PREM_FLAT:
        return True
    if idx_ret > IDX_FLAT and ce_ret <= PREM_FLAT:
        return True
    return False


def score_row(*, x_scaled: Sequence[float], x_orig: Sequence[float], kmeans: KMeans, cluster_labels: dict[int, str], forest: IsolationForest) -> dict[str, Any]:
    cluster = kmeans.predict([list(x_scaled)])[0]
    regime = cluster_labels.get(cluster, "RANGE")
    if_score = forest.anomaly_scores([list(x_scaled)])[0]
    outlier = forest.is_outlier(if_score)
    idx_ret, ce_ret, pe_ret = float(x_orig[0]), float(x_orig[1]), float(x_orig[2])
    prem_div = premium_divergence_pattern(idx_ret, ce_ret, pe_ret)
    z_resid = float(x_scaled[4]) if len(x_scaled) > 4 else 0.0
    residual_flag = z_resid >= 1.25
    overlay = OVERLAY_NONE
    reason = "REGIME_OK"
    if prem_div:
        overlay = OVERLAY_HOLD
        reason = "PREMIUM_DIVERGENCE"
    elif regime == "DIVERGE" or (outlier and residual_flag):
        overlay = OVERLAY_HOLD
        reason = "REGIME_DIVERGE" if regime == "DIVERGE" else "RESIDUAL_IF"
    elif outlier:
        overlay = OVERLAY_DIVERGENCE
        reason = "IF_OUTLIER"
    return {
        "regime": regime,
        "cluster": cluster,
        "overlay": overlay,
        "reason_code": reason,
        "if_score": round(if_score, 6),
        "if_outlier": outlier,
        "residual_z": round(z_resid, 6),
        "premium_divergence": prem_div,
        "allow_new_paper_ce_pe": overlay == OVERLAY_NONE,
        "promote": False,
        "execution": "refused",
        "llm": False,
        "layer": "HYPOTHESIS",
        "feature_names": list(FEATURE_NAMES),
        "features": {name: float(x_orig[i]) for i, name in enumerate(FEATURE_NAMES)},
    }
