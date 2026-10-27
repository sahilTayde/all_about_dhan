"""Replay premium_shadow.exit_one against Research trades_a.csv for the 3 sealed configs."""
import sys,json,numpy as np,pandas as pd
P="/workspace/dhan/research/lab/2026-10-13_premium_stops/ps_a.py"; src=open(P).read(); src=src[:src.index("def one(")]
ns={}; exec(compile(src,P,"exec"),ns); sys.path.insert(0,"/workspace/pshadow"); import premium_shadow as PS
T=pd.read_csv("/workspace/dhan/research/lab/2026-10-13_premium_stops/trades_a.csv")
GI={(.2,1.5):0,(.2,2.0):1,(.3,1.5):2,(.3,2.0):3}; bad=0; n=0; fx=[]; CNT={}
for name,(st,off,S,k,dl,peonly) in PS.CONFIGS.items():
    gi=GI[(S,k)]; ex=T[(T.strat==st)&(T.off==off)&(T.grid==gi)]; ex={(r.day,int(r.f)):r for r in ex.itertuples()}
    for s in [s for s in ns["SIG"] if s["strat"]==st and (not peonly or s["sg"]<0)]:
        d,f,sg=s["day"],s["f"],s["sg"]; z=ns["Z0"][d]; e=min(f+s["dl"],z); K=PS.strike(ns["O"][e],sg,off)
        ct=ns["contract"](d,K,"CE" if sg>0 else "PE"); r=ex.get((d,f)); n+=1
        if ct is None: got=dict(status="NO_CONTRACT")
        else: got=PS.exit_one(ct[1],int(ns["MM"][e]),S,k,hold=s["hold"],capx=s["capx"])
        if r is None: bad+=1; print("MISSING research row",name,d,f); continue
        if isinstance(r.reason,str) and r.reason:
            ok=got["status"]==r.reason
        else:
            ok=got["status"]=="CLOSED" and K==r.K and got["em"]==r.em and got["xm"]==r.xm and got["kind"]==r.kind and abs(got["en"]-r.en)<1e-6 and abs(got["ex"]-r.ex)<1e-6
        if not ok: bad+=1; print("MISMATCH",name,d,f,got,r)
        key=(name,got.get("kind"),got["status"])
        if ct is not None and CNT.get(key,0)<20:
            CNT[key]=CNT.get(key,0)+1
            fx.append(dict(name=name,day=d,e_m=int(ns["MM"][e]),hold=s["hold"],capx=s["capx"],K=K,b={str(m):v for m,v in ct[1].items() if int(ns["MM"][e])<=m<=918},exp={k_:got.get(k_) for k_ in("status","em","en","xm","kind","ex","stop_px","target_px")}))
    print(name,"research rows",len(ex))
print("checked",n,"mismatches",bad)
json.dump(fx,open("/workspace/pshadow/fixture_ps.json","w"))
