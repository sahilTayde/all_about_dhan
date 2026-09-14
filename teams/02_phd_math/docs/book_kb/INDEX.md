# PhD book KB — exam notes (not the books)

**Layer:** `VALIDATION` + `HYPOTHESIS` desk mapping  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Copyright:** We **do not** download, store, or FTS-ingest full copyrighted books. These files are **original study notes** written as if a candidate sat the exam after reading the **published** works, then applied them to **this** DhanHQ index-options signal desk.

**RAG:** `python -m agent_rag rebuild` then `python -m agent_rag query "theta decay"` or `"intrinsic"` — kind `phd_book_kb`. FTS5 tokens, **no embeddings**. Ingest globs `book_kb/*.md` **and** `book_kb/topics/*.md`.

**Must not:** treat notes as edge; invent IV/delta; promote MIX; place orders.

| File | Book (cite) / topic | Desk hook |
|------|---------------------|-----------|
| [00_CROSSWALK.md](00_CROSSWALK.md) | all seven | How ideas **combine** |
| [01_tulchinsky_finding_alphas.md](01_tulchinsky_finding_alphas.md) | Tulchinsky — *Finding Alphas* | Alpha factory vs KEEP_ALL MIX |
| [02_kakushadze_151.md](02_kakushadze_151.md) | Kakushadze — *151 Trading Strategies* (inferred) | Catalog, do not discard |
| [03_derman_models_behaving_badly.md](03_derman_models_behaving_badly.md) | Derman — *Models.Behaving.Badly* | Model ≠ market |
| [04_gliner_global_macro.md](04_gliner_global_macro.md) | Gliner — *Global Macro Trading* | NEWS_DAY / regime HOLD |
| [05_volatility_smile.md](05_volatility_smile.md) | Derman/Miller — *The Volatility Smile* (Wiley) | Smile vs our missing IV |
| [06_trades_quotes_prices.md](06_trades_quotes_prices.md) | Bouchaud et al. — *Trades, Quotes and Prices* | Fill, stale, next-bar |
| [07_afml.md](07_afml.md) | López de Prado — *Advances in Financial Machine Learning* | Leakage, ML-001 |
| [08_EXAM_DESK_PLAYBOOK.md](08_EXAM_DESK_PLAYBOOK.md) | synthesis | Formulas we may **code** |

## Topics (original mechanics — not book text)

| File | Oral | Desk hook |
|------|------|-----------|
| [topics/theta_decay.md](topics/theta_decay.md) | Calendar haircut on long premium | Weekly death; we **pay** theta |
| [topics/gamma.md](topics/gamma.md) | Convexity / Γ | EXPIRY pin; no invented GEX |
| [topics/delta.md](topics/delta.md) | First-order; ≠ P(win) | Store HQ Δ or spot-ITM fallback |
| [topics/vega_iv_realized.md](topics/vega_iv_realized.md) | Vega; IV vs realized | `DATA_INSUFFICIENT` without IV series |
| [topics/intrinsic_time_value.md](topics/intrinsic_time_value.md) | Intrinsic vs time value | Compute from spot + last |
| [topics/pricing_hq_greeks.md](topics/pricing_hq_greeks.md) | Compute vs HQ null greeks | Null ≠ 0; WS has no greeks |
| [topics/poc_volume_profile.md](topics/poc_volume_profile.md) | POC / VP | **HYPOTHESIS** not law |
| [topics/smart_money_oi.md](topics/smart_money_oi.md) | “Smart money” | OI / 3m chain only; no conspiracy |
| [topics/levels.md](topics/levels.md) | S/R, rounds, OR | Named constructors; no soup on `/` |
| [topics/price_change_premium_residual.md](topics/price_change_premium_residual.md) | Index vs premium | `MIX-FORM-*` + [`INDEX_CE_PE_EDA.md`](../INDEX_CE_PE_EDA.md) |
| [topics/overfitting.md](topics/overfitting.md) | Leakage / one-day proof | SCORE_SAMPLE vs ANALOG |
| [topics/model_selection.md](topics/model_selection.md) | KMeans/IF vs logistic | No RL on tick |
| [topics/parameter_fit_retune_gate.md](topics/parameter_fit_retune_gate.md) | Fit ≠ retune | `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` |

Self-review law (06): [`QUANT_SELF_REVIEW_LOOP.md`](../../../06_backtesting/docs/QUANT_SELF_REVIEW_LOOP.md).
