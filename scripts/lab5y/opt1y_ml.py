"""Round-2 F5: walk-forward ML on causal per-minute features (opt1y_lab.feat_table -> OUT/feats.pkl).
For each test month m, fit on months < m only (holdout fit = all dev months, flag --holdout), predict P(fwd30 > 0).
Models: logistic (standardized), sklearn HistGradientBoosting (small, regularized; LightGBM needs libomp, absent), and a momentum-only logistic control (r5,r15,r30,r60).
Writes OUT/preds_{dev|ho}.csv (sym, day, i, model, p, thr_hi, thr_lo) and prints feature importance.
Run (needs sklearn + lightgbm): <v312>/bin/python scripts/lab5y/opt1y_ml.py OUT [--holdout]"""
import sys, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance

OUT = sys.argv[1]; HOLD = "--holdout" in sys.argv; HO = "2026-07-27"
FEAT = ["oi_flow", "oi_flow_w", "pcr", "skew", "dskew", "div_iv", "d_ivatm", "lb", "sc", "sb", "vratio",
        "r5", "r15", "r30", "r60", "rday", "rolled", "m", "dte", "ivatm", "strad_pct", "is_nifty"]
MOM = ["r5", "r15", "r30", "r60"]
F = pd.read_pickle(f"{OUT}/feats.pkl")
F["strad_pct"] = F.straddle / 1.0; F["is_nifty"] = (F.sym == "NIFTY").astype(float)
F["strad_pct"] = F.straddle / F.groupby(["sym", "day"]).straddle.transform("first")
F["mo"] = np.where(F.day < "2025-11-01", "2025-11", F.day.str[:7]); F["y"] = (F.fwd30 > 0).astype(int)
F = F[F.m <= 899 - 30 + 30]  # decision bars only (feats already 09:20..14:59)
dev = F[F.day < HO]; tests = [("ho", F[F.day >= HO], dev)] if HOLD else \
    [(m, dev[dev.mo == m], dev[dev.mo < m]) for m in sorted(dev.mo.unique())[1:]]
models = {
    "logit": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=500)),
    "gbm": lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.03, max_leaf_nodes=15, min_samples_leaf=300,
                                                  l2_regularization=5.0, random_state=0),
    "mom_logit": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.05, max_iter=500)),
}
out, imp = [], []
for m, te, tr in tests:
    for nm, mk in models.items():
        cols = MOM if nm == "mom_logit" else FEAT
        a, b = tr[cols].fillna(0).values, te[cols].fillna(0).values
        md = mk().fit(a, tr.y.values); pt, pe = md.predict_proba(a)[:, 1], md.predict_proba(b)[:, 1]
        hi, lo = np.quantile(pt, 0.9), np.quantile(pt, 0.1)
        out.append(pd.DataFrame(dict(sym=te.sym.values, day=te.day.values, i=te.i.values, model=nm, p=pe, thr_hi=hi, thr_lo=lo)))
        if nm == "gbm":
            pi = permutation_importance(md, b[:20000], te.y.values[:20000], n_repeats=3, random_state=0, scoring="roc_auc")
            imp.append(pd.Series(pi.importances_mean, cols, name=m))
        if nm == "logit": imp.append(pd.Series(md[-1].coef_[0], cols, name=f"{m}_coef"))
        auc = pd.Series(pe).corr(pd.Series(te.fwd30.values), method="spearman")
        print(m, nm, "test IC(p, fwd30)", round(auc, 4), flush=True)
P = pd.concat(out); P.to_csv(f"{OUT}/preds_{'ho' if HOLD else 'dev'}.csv", index=False)
I = pd.concat(imp, axis=1)
g = I[[c for c in I.columns if not str(c).endswith("_coef")]].mean(1).sort_values(ascending=False)
print("GBM permutation importance on the test month (AUC drop, mean over months):"); print(g.round(3).to_string())
c = I[[c for c in I.columns if str(c).endswith("_coef")]].mean(1).sort_values(); print("logit mean coef (standardized):"); print(c.round(3).to_string())
