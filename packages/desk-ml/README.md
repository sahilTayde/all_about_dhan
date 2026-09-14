# packages/desk-ml — ML-001 local pattern overlay

Unsupervised **KMeans (k=4)** + **IsolationForest** on 1m INDEX + ATM CE + ATM PE triples.

**Not** the 30s dual-tape poll. **Not** MIX param writes. **Not** orders. Fast path stays deterministic (`desk_divergence`). This package scores **after bar close** and emits `HOLD` / `DIVERGENCE` / regime labels only.

Spec: [`teams/04_quant/docs/ML_001_LOCAL_PATTERN.md`](../../teams/04_quant/docs/ML_001_LOCAL_PATTERN.md)

```bash
pip install -e packages/desk-ml
python -m desk_ml fit --underlying NIFTY
python -m desk_ml score --underlying NIFTY
```

Holiday / empty cache → `DATA_INSUFFICIENT`. Models land in `data/recon/ml/` (gitignored). `NO_PROMOTE`. No win rates.
