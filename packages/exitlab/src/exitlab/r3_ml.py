"""Tiny no-dep models: CART, logistic, k-means, gradient-boosted stumps."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any


def _gini(ys: Sequence[int]) -> float:
    n = len(ys)
    if n == 0:
        return 0.0
    p = sum(ys) / n
    return 2.0 * p * (1.0 - p)


def _gini_counts(n_pos: int, n: int) -> float:
    if n <= 0:
        return 0.0
    p = n_pos / n
    return 2.0 * p * (1.0 - p)


def _best_split(
    xs: list[list[float | None]], ys: list[int], feat_i: list[int], min_leaf: int
) -> tuple[int, float, float] | None:
    """O(n log n) per feature: running class counts, no list pop."""
    best: tuple[int, float, float] | None = None
    parent = _gini(ys)
    n = len(ys)
    for j in feat_i:
        pairs: list[tuple[float, int]] = []
        for i in range(n):
            raw = xs[i][j]
            if raw is not None:
                pairs.append((float(raw), ys[i]))
        if len(pairs) < min_leaf * 2:
            continue
        pairs.sort(key=lambda p: p[0])
        total_pos = sum(y for _, y in pairs)
        total_n = len(pairs)
        left_pos = 0
        last = None
        for k, (v, y) in enumerate(pairs[:-min_leaf]):
            left_pos += y
            left_n = k + 1
            if last is not None and v == last:
                continue
            if left_n < min_leaf:
                last = v
                continue
            right_n = total_n - left_n
            if right_n < min_leaf:
                break
            right_pos = total_pos - left_pos
            gain = (
                parent
                - (
                    _gini_counts(left_pos, left_n) * left_n
                    + _gini_counts(right_pos, right_n) * right_n
                )
                / total_n
            )
            if best is None or gain > best[2]:
                best = (j, v, gain)
            last = v
    return best


class Node:
    def __init__(self) -> None:
        self.feat: int | None = None
        self.thresh: float = 0.0
        self.left: Node | None = None
        self.right: Node | None = None
        self.prob: float = 0.0
        self.n: int = 0


def fit_tree(
    xs: list[list[float | None]],
    ys: list[int],
    *,
    depth: int = 3,
    min_leaf: int = 40,
    feat_i: list[int] | None = None,
) -> Node:
    feats = feat_i if feat_i is not None else list(range(len(xs[0]) if xs else 0))
    return _fit_node(xs, ys, depth, min_leaf, feats)


def _fit_node(
    xs: list[list[float | None]], ys: list[int], depth: int, min_leaf: int, feat_i: list[int]
) -> Node:
    node = Node()
    node.n = len(ys)
    node.prob = (sum(ys) / len(ys)) if ys else 0.0
    if depth <= 0 or len(ys) < min_leaf * 2:
        return node
    split = _best_split(xs, ys, feat_i, min_leaf)
    if split is None or split[2] <= 1e-9:
        return node
    j, thr, _ = split
    left_x, left_y, right_x, right_y = [], [], [], []
    for i, row in enumerate(xs):
        v = row[j]
        if v is None or v <= thr:
            left_x.append(row)
            left_y.append(ys[i])
        else:
            right_x.append(row)
            right_y.append(ys[i])
    if len(left_y) < min_leaf or len(right_y) < min_leaf:
        return node
    node.feat = j
    node.thresh = thr
    node.left = _fit_node(left_x, left_y, depth - 1, min_leaf, feat_i)
    node.right = _fit_node(right_x, right_y, depth - 1, min_leaf, feat_i)
    return node


def predict_tree(node: Node, row: list[float | None]) -> float:
    cur = node
    while cur.feat is not None and cur.left and cur.right:
        v = row[cur.feat]
        cur = cur.left if v is None or v <= cur.thresh else cur.right
    return cur.prob


def tree_rules(node: Node, names: list[str], prefix: str = "") -> list[str]:
    if node.feat is None:
        return [f"{prefix} -> p={node.prob:.3f} n={node.n}"]
    name = names[node.feat] if node.feat < len(names) else str(node.feat)
    left = tree_rules(node.left, names, f"{prefix}{name}<={node.thresh:.4g} ") if node.left else []
    right = (
        tree_rules(node.right, names, f"{prefix}{name}>{node.thresh:.4g} ") if node.right else []
    )
    return left + right


def _stdize(cols: list[list[float]]) -> tuple[list[list[float]], list[float], list[float]]:
    n = len(cols[0]) if cols else 0
    p = len(cols)
    mu = [sum(c) / n if n else 0.0 for c in cols]
    sd = []
    for j, c in enumerate(cols):
        var = sum((x - mu[j]) ** 2 for x in c) / max(1, n - 1)
        sd.append(math.sqrt(var) if var > 1e-12 else 1.0)
    xs = [[(cols[j][i] - mu[j]) / sd[j] for j in range(p)] for i in range(n)]
    return xs, mu, sd


def fit_logit(
    raw: list[list[float | None]], ys: list[int], *, steps: int = 120, l2: float = 0.2
) -> dict[str, Any]:
    p = len(raw[0]) if raw else 0
    cols: list[list[float]] = [[] for _ in range(p)]
    keep_y: list[int] = []
    for i, row in enumerate(raw):
        # Impute missing as 0 so sparse book/OI columns do not drop the row.
        filled = [0.0 if (v is None or v != v) else float(v) for v in row]
        for j, v in enumerate(filled):
            cols[j].append(v)
        keep_y.append(ys[i])
    if len(keep_y) < 20 or p == 0:
        return {"ok": False, "w": [0.0] * (p + 1), "mu": [0.0] * p, "sd": [1.0] * p}
    xs, mu, sd = _stdize(cols)
    w = [0.0] * (p + 1)
    lr = 0.15
    n = len(keep_y)
    for _ in range(steps):
        grad = [0.0] * (p + 1)
        for i in range(n):
            z = w[0] + sum(w[j + 1] * xs[i][j] for j in range(p))
            z = max(-20.0, min(20.0, z))
            pr = 1.0 / (1.0 + math.exp(-z))
            err = pr - keep_y[i]
            grad[0] += err
            for j in range(p):
                grad[j + 1] += err * xs[i][j]
        for j in range(p + 1):
            pen = l2 * w[j] if j else 0.0
            w[j] -= lr * (grad[j] / n + pen)
    return {"ok": True, "w": w, "mu": mu, "sd": sd}


def predict_logit(model: dict[str, Any], row: list[float | None]) -> float:
    w = model["w"]
    mu = model["mu"]
    sd = model["sd"]
    z = w[0]
    for j, v in enumerate(row):
        if v is None or v != v:
            continue
        z += w[j + 1] * ((float(v) - mu[j]) / (sd[j] or 1.0))
    z = max(-20.0, min(20.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def kmeans(rows: list[list[float]], k: int, *, seed: int, rounds: int = 12) -> dict[str, Any]:
    if not rows:
        return {"ok": False, "centers": [], "k": k}
    rng = random.Random(seed)
    k = min(k, len(rows))
    centers = [list(rows[rng.randrange(len(rows))]) for _ in range(k)]
    assign = [0] * len(rows)
    dim = len(rows[0])
    for _ in range(rounds):
        for i, r in enumerate(rows):
            best, bd = 0, 1e18
            for c, ctr in enumerate(centers):
                d = sum((r[j] - ctr[j]) ** 2 for j in range(dim))
                if d < bd:
                    best, bd = c, d
            assign[i] = best
        for c in range(k):
            members = [rows[i] for i, a in enumerate(assign) if a == c]
            if not members:
                centers[c] = list(rows[rng.randrange(len(rows))])
                continue
            centers[c] = [sum(m[j] for m in members) / len(members) for j in range(dim)]
    return {"ok": True, "centers": centers, "assign": assign, "k": k}


def nearest_center(row: list[float], centers: list[list[float]]) -> int:
    best, bd = 0, 1e18
    for c, ctr in enumerate(centers):
        d = sum((row[j] - ctr[j]) ** 2 for j in range(len(ctr)))
        if d < bd:
            best, bd = c, d
    return best


def fit_boost(
    xs: list[list[float | None]], ys: list[int], *, rounds: int = 12, depth: int = 2
) -> list[Node]:
    """Gradient boosting on probability residuals. No sklearn/LightGBM in this env."""
    trees: list[Node] = []
    pred = [sum(ys) / len(ys) if ys else 0.0] * len(ys)
    resid = [float(ys[i]) - pred[i] for i in range(len(ys))]
    # CART wants 0/1; split residual at 0.
    bin_y = [1 if r > 0 else 0 for r in resid]
    for _ in range(rounds):
        t = fit_tree(xs, bin_y, depth=depth, min_leaf=max(30, len(ys) // 40))
        trees.append(t)
        for i, row in enumerate(xs):
            pred[i] += 0.15 * predict_tree(t, row)
        bin_y = [1 if (ys[i] - pred[i]) > 0 else 0 for i in range(len(ys))]
    return trees


def predict_boost(trees: list[Node], row: list[float | None]) -> float:
    s = 0.0
    for t in trees:
        s += 0.15 * predict_tree(t, row)
    return max(0.0, min(1.0, s))
