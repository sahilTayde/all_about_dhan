# packages/desk-ml — ML-001 + ML-002 overlays

Unsupervised **ML-001** (KMeans k=4 + IsolationForest) and **ML-002** (OU on MIX-FORM residual + VWMA MRR windows 40/60/90) on 1m INDEX + ATM CE + ATM PE triples.

**Not** MIX param writes. **Not** orders. Dual-tape poll stays deterministic (`desk_divergence`). Score after bar close **or** ` --source dual-tape`. FOLLOW-GAP overlay HOLDs new paper CE/PE. Session prep: [`SESSION_PREP_ML.md`](../../teams/06_backtesting/docs/SESSION_PREP_ML.md).

Specs: [`ML_001_LOCAL_PATTERN.md`](../../teams/04_quant/docs/ML_001_LOCAL_PATTERN.md) · [`BOOK_MODEL_TUNE.md`](../../teams/06_backtesting/docs/BOOK_MODEL_TUNE.md)

```bash
pip install -e packages/desk-ml
python -m desk_ml inventory --calendar-days 21
python -m desk_ml fit --underlying NIFTY --seed 14 --embargo-bars 5
python -m desk_ml score --underlying NIFTY --source dual-tape
python -m desk_ml mrr-fit --underlying NIFTY
python -m desk_ml book-tune --calendar-days 21
python -m desk_ml replay-hold --underlying NIFTY --horizon-bars 15
python -m desk_ml paper-scalp --replay
```

Empty / non-overlapping cache → `DATA_INSUFFICIENT`. Models land in `data/recon/ml/` (gitignored). `production_params_written: false`. **NO_PROMOTE**. Cluster/MRR numbers are counts, not a win rate.
