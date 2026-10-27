import numpy as np, pandas as pd, lab, lab2
from lab import DAYS, KEYS, run, summ, idx_at
# volatility-filtered ORB: trade only when opening-range width is in top part of its own trailing 60-day distribution (no look-ahead)
def sig_orb_vol(om=30, pct=0.67, last=780, lo_pct=0.0):
    hist={}
    for k in KEYS:
        s=k[0]; m,o,h,l,c=DAYS[k]; a=idx_at(m,555+om)
        if a<5 or m[0]>560: continue
        w=(h[:a].max()-l[:a].min())/o[0]; H=hist.setdefault(s,[])
        ok=len(H)>=60 and np.mean(np.array(H[-60:])<w)>=pct and np.mean(np.array(H[-60:])<w)>=lo_pct
        H.append(w)
        if not ok: continue
        hi,lo=h[:a].max(),l[:a].min()
        for j in range(a,len(m)):
            if m[j]>=last: break
            if c[j]>hi: yield k,j+1,1; break
            if c[j]<lo: yield k,j+1,-1; break
# does OR width predict rest-of-day range? (vol clustering check)
for s in ("NIFTY","SENSEX"):
    w=[];r=[]
    for k in KEYS:
        if k[0]!=s: continue
        m,o,h,l,c=DAYS[k]; a=idx_at(m,585)
        if a<5 or m[0]>560: continue
        w.append((h[:a].max()-l[:a].min())/o[0]); r.append((h[a:].max()-l[a:].min())/o[0])
    print(s,"corr(OR30 width, rest-of-day range) =",round(np.corrcoef(w,r)[0,1],2))
for sym in ("NIFTY","SENSEX","BANKNIFTY"):
    for om in (15,30):
        for pct in (0.5,0.8):
            print(summ(run((x for x in sig_orb_vol(om,pct) if x[0][0]==sym),stop=0.003,trail=0.005),f"{sym} ORB{om} volpct>{pct} trail"),flush=True)
