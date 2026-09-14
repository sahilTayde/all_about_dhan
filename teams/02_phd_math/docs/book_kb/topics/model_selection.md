# Exam note — model selection (KMeans / IsolationForest vs logistic vs no RL on tick)

**Layer:** `HYPOTHESIS` (ML-001) + `VALIDATION` (what we refused)  
**Chair:** phd_statistics + 04 algo · [`ML_001_LOCAL_PATTERN.md`](../../../../04_quant/docs/ML_001_LOCAL_PATTERN.md) · **NO_PROMOTE**

## What the oral wants

Pick the **simplest model that matches the label budget**. Day-1 labels are thin. Unsupervised **regime / outlier** overlays can run without a win-rate target. Supervised models need **thick, non-leaky** labels. Reinforcement learning on 30s/tick I/O is the wrong capacity: slow, unstable, and it invites a live Super Order fantasy.

TOKEN_ML: local rules → later logit/tree → later GBM. **No** blocking LLM on the market-hours fast path. **No** embeddings as day-1 KB.

## Tokens for FTS

model selection, KMeans, IsolationForest, logistic, RL tick, ML-001, unsupervised first, SKIPPED_THIS_TICKET

## Desk mapping

| Model | When | Desk use |
|-------|------|----------|
| **KMeans k=4** | Unsupervised, features idx/ce/pe ret + spread + \|ε\| | Regime labels `TREND_*` / `RANGE` / `DIVERGE` — **not** BUY_CE/PE |
| **IsolationForest** | Outlier overlay | Assist HOLD; second tripwire with residual z |
| **Logistic / tree** | Only if labels are thick | `DATA_INSUFFICIENT` / `SKIPPED_THIS_TICKET` until then; MIX-ML-LOGIT rows stay metrics-null |
| **Deep RL / transformers** | Not on 30s path | Rejected — do not use RL on tick |
| **LLM** | Async counsel | Compact state; not alpha |

Features: **no invented greeks**. Overlay must not override hard stops or publish the customer ticket.

## DATA_INSUFFICIENT

Holiday fit (INDEX ∩ ATM tape) printed **cluster sizes**, not edge. Walk-forward vs `desk_divergence` is UNKNOWN. Supervised CE/PE outcome labels: not a SCORE_SAMPLE promote set.

## Exam trap

“KMeans found four regimes so we have four strategies.” Clusters are **partitions**. RL on ticks “to maximize paper P/L” is **out of policy**.
