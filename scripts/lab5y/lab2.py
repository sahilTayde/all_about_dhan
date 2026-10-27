import numpy as np, pandas as pd, lab
from lab import DAYS, KEYS, run, summ, idx_at
def trade_trail(k,i,d,stop=0.003,trail=0.004,exit_m=920):
    m,o,h,l,c=DAYS[k]
    if i>=len(m) or m[i]>=exit_m: return None
    e=o[i]; best=e; sp=e*(1-d*stop); x=None; j=i
    for j in range(i,len(m)):
        if m[j]>=exit_m: x=o[j]; break
        if (d>0 and l[j]<=sp) or (d<0 and h[j]>=sp): x=sp; break
        best=max(best,h[j]) if d>0 else min(best,l[j])
        nsp=best*(1-d*trail); sp=max(sp,nsp) if d>0 else min(sp,nsp)
    if x is None: x=c[-1]
    hrs=(m[j]-m[i])/60; return d*(x-e)/e-lab.RT-lab.TH*hrs, hrs
lab.trade=trade_trail
def prevmap():
    P={}; last={}
    for k in KEYS:
        s,_=k; m,o,h,l,c=DAYS[k]
        P[k]=last.get(s); last[s]=(h.max(),l.min(),c[-1],[(DAYS[k][2].max()-DAYS[k][3].min())])
    return P
PREV=prevmap()
# range history for NR7
RNG={}
for s in ("NIFTY","SENSEX","BANKNIFTY"):
    ks=[k for k in KEYS if k[0]==s]; r=[(DAYS[k][2].max()-DAYS[k][3].min())/DAYS[k][4][-1] for k in ks]
    for n,k in enumerate(ks): RNG[k]=(r[n-1] if n else None, min(r[max(0,n-7):n]) if n>=7 else None)
def sig_pdhl(nr=False,last=840):
    for k in KEYS:
        p=PREV[k]
        if not p: continue
        if nr and not (RNG[k][0] is not None and RNG[k][1] is not None and RNG[k][0]<=RNG[k][1]): continue
        m,o,h,l,c=DAYS[k]
        if m[0]>560: continue
        for j in range(len(m)):
            if m[j]>=last: break
            if c[j]>p[0]: yield k,j+1,1; break
            if c[j]<p[1]: yield k,j+1,-1; break
def sig_revert(at=660,thr=0.008):
    for k in KEYS:
        m,o,h,l,c=DAYS[k]; a=idx_at(m,at)
        if a<20 or m[0]>560: continue
        r=c[a-1]/o[0]-1
        if abs(r)>=thr: yield k,a,-1 if r>0 else 1
for sym in ("NIFTY","SENSEX","BANKNIFTY"):
    for nr in (False,True):
        for st,tr in ((0.003,0.004),(0.004,0.006),(0.002,0.003)):
            print(summ(run((s for s in sig_pdhl(nr) if s[0][0]==sym),stop=st,trail=tr),f"{sym} PDHL nr={nr} st{st} tr{tr}"),flush=True)
    for at in (660,750):
        for thr in (0.006,0.01):
            print(summ(run((s for s in sig_revert(at,thr) if s[0][0]==sym),stop=0.004,trail=0.006),f"{sym} REVERT at{at} thr{thr}"),flush=True)
    for om in (15,30):
        print(summ(run((s for s in lab.sig_orb(om) if s[0][0]==sym),stop=0.003,trail=0.004),f"{sym} ORB{om} trail"),flush=True)
