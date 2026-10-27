import sys,os,numpy as np,pandas as pd
L="/workspace/dhan/research/lab/2026-10-12_candle_patterns"; sys.path[:0]=[L,L+"/vendor_lib"]; cwd=os.getcwd(); os.chdir(L)
import common as C; os.chdir(cwd)
def vw_sigs(G,CX,days):
    out=[]
    for d in days:
        if d not in CX: continue
        g=G[d]; X=CX[d]; m=g.m.values; last,cnt=-999,0
        for t,sg,stop in C.signals("VWAP_CONT",g,X):
            if cnt>=C.CAP or m[t]-last<C.GAP: continue
            e=t+1
            if e>=len(m): continue
            S0=g.open.values[e]; R=sg*(S0-stop)
            if R<C.RMIN*X["A"]: R=C.RMIN*X["A"]
            if R>C.RMAX*X["A"]: continue
            p0=(g.ce_o if sg>0 else g.pe_o).values[e]
            if not np.isfinite(p0) or p0<=1: continue
            last,cnt=m[t],cnt+1; out.append((d,int(m[t]),"CE" if sg>0 else "PE"))
    return out
if __name__=="__main__":
    os.chdir(L); G=C.load(); CX=C.context(G); os.chdir(cwd)
    mine=sorted(vw_sigs(G,CX,sorted(CX)))
    t=pd.read_csv(L+"/out/trades_VWAP_CONT.csv").drop_duplicates(["day","sig_m","side"]); res=sorted((r.day,int(r.sig_m),r.side) for r in t.itertuples())
    print("VWAP mine",len(mine),"research",len(res),"equal",mine==res,sorted(set(mine)^set(res))[:5])
