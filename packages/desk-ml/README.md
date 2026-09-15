# packages/desk-ml — ML-001 + ML-002 overlays

Unsupervised **ML-001** (KMeans k=4 + IsolationForest) and **ML-002** (OU on MIX-FORM residual + VWMA MRR windows 40/60/90) on 1m INDEX + ATM CE + ATM PE triples.

**Not** the 30s dual-tape poll. **Not** MIX param writes. **Not** orders. Fast path stays deterministic (`desk_divergence`). Score **after bar close**. FOLLOW-GAP overlay HOLDs new paper CE/PE.

Specs: [`ML_001_LOCAL_PATTERN.md`](../../teams/04_quant/docs/ML_001_LOCAL_PATTERN.md) · [`BOOK_MODEL_TUNE.md`](../../teams/06_backtesting/docs/BOOK_MODEL_TUNE.md)

```bash
pip install -e packages/desk-ml
python -m desk_ml inventory --calendar-days 21
python -m desk_ml fit --underlying NIFTY --seed 14
python -m desk_ml score --underlying NIFTY
python -m desk_ml mrr-fit --underlying NIFTY
python -m desk_ml book-tune --calendar-days 21
```

Empty / non-overlapping cache → `DATA_INSUFFICIENT`. Models land in `data/recon/ml/` (gitignored). `production_params_written: false`. **NO_PROMOTE**. Cluster/MRR numbers are counts, not a win rate.
