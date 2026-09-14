# Exam note — López de Prado, *Advances in Financial Machine Learning*

**Cite:** Marcos López de Prado, *Advances in Financial Machine Learning*, Wiley. Already `lopez_afml` in `workspace.yaml`. **Chair:** phd_statistics.

## What the oral wants

Financial labels **overlap**. Standard k-fold **leaks**. Use **purged / embargoed CV**, fractionally differentiated features if needed, and treat “fit until profitable” as **research fraud**. Meta-labeling is a **second** model (take/skip), not a new strike.

## Tokens for FTS

purged CV, embargo, leakage, meta label, AFML, ML-001, IsolationForest, KMeans

## Desk mapping

| AFML | Ours |
|------|------|
| Features from bars | idx_ret, ce_ret, pe_ret, spread, residual |
| Unsupervised first | ML-001 KMeans k=4 + IsolationForest |
| Meta-label | Dual-tape HOLD = skip the bet (not coded as sklearn yet) |
| No production write | RETUNE_GATE `production_params_written: false` |
| Overlapping 1m | Do not score promote on one session; premium labels leak if bars overlap |

Combine with Tulchinsky: factory of features, **one** gate. Combine with Derman Badly: a leaky CV is a badly behaved model.

## Must not

Deep RL on the 30s path. Embeddings as day-1 (TOKEN_ML: FTS5). Claim cluster counts as win rate.
