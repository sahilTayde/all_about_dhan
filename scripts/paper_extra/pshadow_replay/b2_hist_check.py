import sys,os,numpy as np,pandas as pd
LAB="/workspace/dhan/research/lab"; sys.path[:0]=[LAB,LAB+"/lib",LAB+"/2026-10-11_stress"]
cwd=os.getcwd(); os.chdir(LAB+"/2026-10-11_stress"); import stress as S; os.chdir(cwd)
from path1m import run_path_sf
M=pd.read_parquet("/workspace/dhan/output/lab_round7b/base_1m.parquet",columns=["day","m","open","high","low","close","src"]); M=M[M.src.isin(["mac","hist"])]
OHL={d:g.sort_values("m") for d,g in M.groupby("day")}
def b2_caps(k):
    d=S.days[k]; g=S.GD[d]; x=OHL[d].set_index("m").reindex(g.m.values)
    o,h,l=(x[c].values.astype(float) for c in ("open","high","low")); c=g.close.values.astype(float); m=g.m.values.astype(int); tw=g.twap.values.astype(float)
    out=[]
    for e,sg,kw,itm in S.B2(k,g,S.RULES["B2"][1]):
        if e is None or e>=len(g)-2: continue
        p0=(g.ce_c if sg>0 else g.pe_c).values[e]
        if not np.isfinite(p0) or p0<=1: continue
        dl=.54
        if itm=="ITM100": p0+=54
        elif itm: p0+=27; dl=.60
        kw=dict(kw); sf=kw.pop("stop_frac",None)
        if sf: kw["stop_pts"]=sf*p0/dl
        z,lvl,st=run_path_sf(o,h,l,c,m,tw,e,sg,**kw); out.append((d,int(m[e]),"CE" if sg>0 else "PE",int(m[z]),bool(st)))
    return out
if __name__=="__main__":
    mine=[t for k in range(25,len(S.days)) if "2023-08-01"<=S.days[k]<="2026-07-02" for t in b2_caps(k)]
    b=pd.read_csv(LAB+"/2026-10-12_desk_tree/hist_B2Q01_trades.csv"); b=b[(b.rule=="B2")&(b.model=="HOUSE")&(b.day>="2023-08-01")&(b.day<="2026-07-02")]
    res=sorted((r.day,int(r.ent_m),r.side,int(r.exit_m),bool(r.stopped)) for r in b.itertuples())
    print("B2 mine",len(mine),"research",len(res),"equal",sorted(mine)==res, sorted(set(mine)^set(res))[:5])
    print("kw",S.RULES["B2"])
