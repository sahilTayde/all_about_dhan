"""Honest-selection helpers adopted from the 2026-11-13 GitHub repo harvest (teams/01_research/docs/REPO_HARVEST.md).
numpy only, no data needed, so every lab can import it. Re-implemented from the papers / ideas; no code copied
(pypbo is AGPL, freqtrade GPL: ideas only).
  pbo_cscv     probability of backtest overfitting (Bailey, Borwein, Lopez de Prado, Zhu 2014; CSCV). We had SPA (is ANY variant
               real?) and DSR; PBO asks: how often does the in-sample best land below the out-of-sample median?
  stepm        Romano-Wolf (2005) step-down: WHICH variants beat 0, family-wise error controlled (arch.bootstrap.StepM idea).
  effective_n  number of independent trials in a correlated grid (participation ratio), the N for a deflated Sharpe.
  lookahead    freqtrade's lookahead-analysis idea, generic form of playbook_lab.selftest33: scramble every value after the
               decision index and assert the feature/signal at that index did not change.
Run:  python scripts/lab5y/honest_stats.py      (known answers; ~10 s)"""
import math, itertools, numpy as np


def _sharpe(X):  # columns = variants
    return X.mean(0) / (X.std(0, ddof=1) + 1e-12)


def pbo_cscv(M, S=10, metric=_sharpe):
    """M: (T periods, N variants) P&L, e.g. daily P&L with 0 on no-trade days. S even: T split into S contiguous blocks; every choice
    of S/2 blocks is in-sample (IS), the rest out-of-sample (OOS). For each split take the IS-best variant, find its relative OOS rank
    w in (0, 1), logit = ln(w / (1 - w)). PBO = share of splits with logit <= 0 (IS winner at or below the OOS median).
    Returns dict(pbo, logits, deg) where deg = slope of OOS metric on IS metric of the winners (< 0: selection hurts OOS).
    ponytail: S=10 -> 252 splits; ceiling S=16 (12,870 splits) before it gets slow on 250k variants; chunk N if needed."""
    M = np.asarray(M, float); T, N = M.shape; assert S % 2 == 0 and T >= 2 * S and N >= 2
    blocks = np.array_split(np.arange(T), S); lg, isb, oosb = [], [], []
    for c in itertools.combinations(range(S), S // 2):
        ii = np.concatenate([blocks[j] for j in c]); oo = np.concatenate([blocks[j] for j in range(S) if j not in c])
        a, b = metric(M[ii]), metric(M[oo]); n = int(np.argmax(a))
        w = ((b < b[n]).sum() + 0.5 * ((b == b[n]).sum() - 1) + 1) / (N + 1)  # rank of the winner in OOS, ties split
        lg.append(math.log(w / (1 - w))); isb.append(a[n]); oosb.append(b[n])
    lg = np.array(lg); deg = float(np.polyfit(isb, oosb, 1)[0]) if np.std(isb) > 0 else float("nan")
    return dict(pbo=float((lg <= 0).mean()), logits=lg, deg=deg, splits=len(lg))


def _stat_boot_idx(n, B, q, rg):
    """stationary bootstrap (Politis-Romano) index matrix (B, n), mean block 1/q; same scheme as sweep_lab.spa."""
    I = np.empty((B, n), int); I[:, 0] = rg.integers(n, size=B)
    for t in range(1, n):
        new = rg.random(B) < q; I[:, t] = np.where(new, rg.integers(n, size=B), (I[:, t - 1] + 1) % n)
    return I


def stepm(X, alpha=0.05, B=1000, q=0.2, seed=7):
    """Romano-Wolf step-down on studentized means. X: (V variants, n days). Returns sorted indices of variants whose mean daily
    P&L is > 0 with family-wise error <= alpha (one-sided, benchmark 0). Empty list = nothing is real."""
    X = np.asarray(X, float); V, n = X.shape; rg = np.random.default_rng(seed); rn = math.sqrt(n)
    mu = X.mean(1); sd = X.std(1, ddof=1) + 1e-12; t = rn * mu / sd
    I = _stat_boot_idx(n, B, q, rg); Tb = np.empty((B, V))
    for b in range(B): Tb[b] = rn * (X[:, I[b]].mean(1) - mu) / sd  # centred bootstrap t
    active = np.ones(V, bool); out = []
    while active.any():
        c = np.quantile(Tb[:, active].max(1), 1 - alpha); rej = active & (t > c)
        if not rej.any(): break
        out += list(np.flatnonzero(rej)); active &= ~rej
    return sorted(int(v) for v in out)


def lookahead(fn, arrays, i, seed=7, tol=1e-9):
    """fn(arrays) -> dict (or scalar) of features/signals for decision index i, computed from `arrays` (dict name -> 1-D/2-D numpy
    array, axis 0 = minute). Every value after index i is scrambled (x uniform 0.5..1.5, plus a sign flip on half of them) and fn is
    re-run. Returns the list of keys whose value changed (empty = no look-ahead seen at i). Catches the E33 bugs: a bar that closes
    after i, a whole-day max/min, and a negative index (a[i - 60] with i < 60 wraps to the END of the day)."""
    rg = np.random.default_rng(seed); r0 = fn(arrays); A2 = {}
    for k, a in arrays.items():
        a = np.array(a, float, copy=True); m = len(a) - i - 1
        if m > 0: a[i + 1:] *= rg.uniform(0.5, 1.5, (m,) + a.shape[1:]) * rg.choice([-1.0, 1.0], (m,) + a.shape[1:])
        A2[k] = a
    r1 = fn(A2); r0 = r0 if isinstance(r0, dict) else {"value": r0}; r1 = r1 if isinstance(r1, dict) else {"value": r1}
    bad = []
    for k in r0:
        a, b = r0[k], r1.get(k)
        try: same = (a == b) or (np.isnan(a) and np.isnan(b)) or abs(a - b) <= tol
        except TypeError: same = a == b
        if not same: bad.append(k)
    return bad


def lookahead_scan(fn_i, arrays, slots, seed=7):
    """fn_i(arrays, i) -> features at decision index i. Runs `lookahead` at every slot; returns {slot: [leaking keys]} (empty = clean).
    Use before any frozen rule is scored (E39+): one call per feature function over its decision slots."""
    out = {}
    for i in slots:
        bad = lookahead(lambda a: fn_i(a, i), arrays, i, seed)
        if bad: out[i] = bad
    return out


def effective_n(X):
    """effective number of independent trials among correlated variants: participation ratio of the eigenvalues of the correlation
    matrix, (sum l)^2 / sum l^2. Use as N in a deflated Sharpe (sweep_lab.dsr_family) instead of the raw variant count, which
    over-deflates near-duplicate grids. X: (V variants, n days); constant rows are dropped. Ceiling: V ~ 5k (V x V matrix)."""
    X = np.asarray(X, float); X = X[X.std(1) > 0]
    if len(X) < 2: return float(len(X))
    l = np.clip(np.linalg.eigvalsh(np.corrcoef(X)), 0, None); return float(l.sum() ** 2 / (l ** 2).sum())


def selftest():
    rg = np.random.default_rng(1)
    # PBO: pure noise -> about 0.5 (the IS winner is a random OOS draw); one variant with a real drift -> about 0
    noise = rg.normal(0, 1, (500, 60)); p0 = pbo_cscv(noise)["pbo"]
    sig = noise.copy(); sig[:, 7] += 0.4; p1 = pbo_cscv(sig)["pbo"]
    assert 0.3 <= p0 <= 0.7 and p1 < 0.05, (p0, p1)
    # regime-flip grid: each variant earns +0.5 in one half and loses 0.5 in the other (what looks best IS is worst OOS) -> PBO > 0.5
    over = rg.normal(0, 1, (500, 60)); h = np.where(np.arange(500) < 250, 0.5, -0.5)
    for v in range(60): over[:, v] += h if v % 2 else -h
    p2 = pbo_cscv(over)["pbo"]; assert p2 > 0.8, p2
    # tiny exact case: 2 variants, A wins the first half, B the second; S=2 -> 2 splits, each IS winner is OOS-worst -> PBO 1
    t2 = np.zeros((4, 2)); t2[:2, 0] = [1, 1.1]; t2[2:, 1] = [1, 1.1]
    assert pbo_cscv(t2, S=2)["pbo"] == 1.0
    # Fable's exact cases: A = +1 then -1, B the opposite, 2 blocks -> PBO 1.0; a constant +1 edge over noise -> PBO 0.0
    ab = np.array([[1.0, -1.0], [1.1, -1.1], [-1.0, 1.0], [-1.1, 1.1]]); assert pbo_cscv(ab, S=2)["pbo"] == 1.0
    ce = rg.normal(0, 1, (400, 30)); ce[:, 3] += 1.0; assert pbo_cscv(ce, S=8)["pbo"] == 0.0
    # effective N: 20 identical columns -> 1; 20 independent (identity correlation) -> 20; two blocks of 10 identical -> 2
    base = rg.normal(0, 1, 500); assert abs(effective_n(np.tile(base, (20, 1))) - 1) < 1e-6
    Z = np.linalg.qr(rg.normal(0, 1, (500, 20)))[0].T; Z -= Z.mean(1, keepdims=True); Z = np.linalg.qr(Z.T)[0].T  # exactly uncorrelated
    assert abs(effective_n(Z) - 20) < 1e-6, effective_n(Z)
    b2 = rg.normal(0, 1, 500); b2 -= b2 @ (base - base.mean()) / ((base - base.mean()) ** 2).sum() * (base - base.mean())  # orthogonal
    assert abs(effective_n(np.vstack([np.tile(base, (10, 1)), np.tile(b2, (10, 1))])) - 2) < 1e-6
    # StepM: 200 noise variants + 3 with a strong mean -> exactly those 3; pure noise -> none
    X = rg.normal(0, 1, (203, 250)); X[[5, 50, 150]] += 0.5; got = stepm(X, B=500)
    assert got == [5, 50, 150], got
    assert stepm(rg.normal(0, 1, (200, 250)), B=500) == []
    # lookahead: honest features pass; a future bar, a whole-day max and a wrapped negative index are caught
    s = np.cumsum(rg.normal(0, 1, 375)) + 100; A = dict(spot=s)
    honest = lambda a: dict(last=a["spot"][30], r15=a["spot"][30] / a["spot"][15] - 1, hi=a["spot"][:31].max())
    assert lookahead(honest, A, 30) == []
    leaky = lambda a: dict(last=a["spot"][30], next=a["spot"][31], dayhi=a["spot"].max(), r60=a["spot"][30] / a["spot"][30 - 60] - 1)
    assert lookahead(leaky, A, 30) == ["next", "dayhi", "r60"], lookahead(leaky, A, 30)
    # Fable's scan case: the E33 wrap bug s[i - 60] leaks at exactly the 60 slots i = 0..59 of a 300-point rising series
    up = dict(spot=np.arange(1.0, 301.0)); wrap = lambda a, i: dict(r60=a["spot"][i] / a["spot"][i - 60] - 1)
    sc = lookahead_scan(wrap, up, range(300)); assert sorted(sc) == list(range(60)), sorted(sc)[:5]
    trail = lambda a, i: dict(m=a["spot"][max(0, i - 9):i + 1].mean()); assert lookahead_scan(trail, up, range(300)) == {}
    cent = lambda a, i: dict(m=a["spot"][max(0, i - 5):i + 6].mean()); assert sorted(lookahead_scan(cent, up, range(300))) == list(range(299))
    bar5 = lambda a: dict(close5=a["spot"][34])   # the 5m bar CONTAINING minute 32 closes at minute 34: the E33 bug (a)
    assert lookahead(bar5, A, 32) == ["close5"] and lookahead(bar5, A, 34) == []
    print(f"honest_stats selftest OK (PBO noise {p0:.2f}, signal {p1:.2f}, overfit grid {p2:.2f}; exact cases 1.0 / 0.0; effective N 1 / 20 / 2; StepM finds 3/3, 0 in noise; "
          "lookahead catches next bar, day max, wrapped index (60/60 slots), centred mean, open 5m bar)")


if __name__ == "__main__":
    selftest()
