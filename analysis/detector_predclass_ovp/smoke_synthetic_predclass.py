"""
Synthetic numpy-only smoke mirror for judge_predclass.py (sandbox has no sklearn).
Validates: (1) machinery sound; (2) a meaningful binary candidate adds HDG > 0;
(3) FOIL MECHANIC: permuting that candidate (independent stream, SAME split) collapses
HDG to ~0. NO real pred, NO inheritance touched. Mirrors loop structure & RNG plumbing only.
"""
import numpy as np

FOIL_SEED_XOR = 0xF011

def standardize(Xtr, Xte):
    mu = Xtr.mean(0); sd = Xtr.std(0); sd[sd == 0] = 1.0
    return (Xtr - mu) / sd, (Xte - mu) / sd

def logfit(X, y, iters=30):
    # IRLS logistic with tiny ridge for stability; X already standardized, add intercept
    Xi = np.column_stack([np.ones(len(X)), X]); w = np.zeros(Xi.shape[1])
    for _ in range(iters):
        p = 1/(1+np.exp(-Xi@w)); W = np.clip(p*(1-p), 1e-6, None)
        z = Xi.T*(W); H = z@Xi + 1e-6*np.eye(Xi.shape[1]); g = Xi.T@(y-p)
        w += np.linalg.solve(H, g)
    return w

def proba(w, X):
    Xi = np.column_stack([np.ones(len(X)), X]); return 1/(1+np.exp(-Xi@w))

def auc(y, s):
    o = np.argsort(s, kind="mergesort"); r = np.empty(len(s)); r[o] = np.arange(1, len(s)+1)
    # average ties
    order = np.argsort(s, kind="mergesort"); ss = s[order]; i = 0
    while i < len(ss):
        j = i
        while j+1 < len(ss) and ss[j+1] == ss[i]: j += 1
        if j > i:
            avg = (r[order[i:j+1]]).mean(); r[order[i:j+1]] = avg
        i = j+1
    n1 = y.sum(); n0 = len(y)-n1
    if n1 == 0 or n0 == 0: return 0.5
    return (r[y == 1].sum() - n1*(n1+1)/2)/(n1*n0)

def strat_split(y, rs):
    rng = np.random.default_rng(rs); idx = np.arange(len(y)); tr = []; te = []
    for c in np.unique(y):
        ci = idx[y == c]; rng.shuffle(ci); h = len(ci)//2; tr += list(ci[:h]); te += list(ci[h:])
    return np.array(tr), np.array(te)

def hdg_loop(B, y, cand, master, reps=200):
    children = np.random.SeedSequence(master).spawn(reps)
    foil_children = np.random.SeedSequence(master ^ FOIL_SEED_XOR).spawn(reps)
    d = np.empty(reps); df = np.empty(reps)
    for r in range(reps):
        ss = int(np.random.default_rng(children[r]).integers(0, 2**31-1))
        itr, ite = strat_split(y, ss); ytr, yte = y[itr], y[ite]
        X1tr, X1te = standardize(B[itr].reshape(-1,1), B[ite].reshape(-1,1))
        a1 = auc(yte, proba(logfit(X1tr, ytr), X1te))
        X2 = np.column_stack([B, cand])
        X2tr, X2te = standardize(X2[itr], X2[ite])
        d[r] = auc(yte, proba(logfit(X2tr, ytr), X2te)) - a1
        # foil: permute cand, independent stream, SAME split
        cp = cand.copy(); np.random.default_rng(foil_children[r]).shuffle(cp)
        X2f = np.column_stack([B, cp]); X2ftr, X2fte = standardize(X2f[itr], X2f[ite])
        df[r] = auc(yte, proba(logfit(X2ftr, ytr), X2fte)) - a1
    return float(np.median(d)), float(np.median(df))

rng = np.random.default_rng(7)
n = 2000
# meaningful binary m correlated with correctness; B (confidence) carries SOME but not all of it
m = (rng.random(n) < 0.33).astype(float)           # ~33% class-1, like pred's 652/2000
base = 0.45 + 0.30*m                                # m lifts correctness prob (the intercept asymmetry)
y = (rng.random(n) < base).astype(int)
B = np.clip(0.6 + 0.15*m + 0.20*rng.standard_normal(n), 0.5, 1.0)  # B partially tracks m
null = (rng.random(n) < 0.33).astype(float)        # null binary, same marginal, unrelated to y

D_m, Df_m = hdg_loop(B, y, m, 0xC1A55D)
D_null, Df_null = hdg_loop(B, y, null, 0xC1A55D)
print("meaningful binary : D=%.5f   foil(permuted)=%.5f" % (D_m, Df_m))
print("null binary       : D=%.5f   foil(permuted)=%.5f" % (D_null, Df_null))
ok1 = D_m > 0.01                      # meaningful candidate adds gain
ok2 = abs(Df_m) < 0.01                # FOIL collapses the meaningful candidate's gain
ok3 = abs(D_null) < 0.01              # null adds ~nothing
ok4 = abs(Df_null) < 0.01             # null's foil also ~nothing
print("SMOKE:", "PASS" if (ok1 and ok2 and ok3 and ok4) else "FAIL",
      "| meaningful_gain>0.01:%s foil_collapses:%s null~0:%s null_foil~0:%s" % (ok1, ok2, ok3, ok4))
