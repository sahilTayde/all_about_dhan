"""Live shadow scoring pass for 2026-10-13 (PAPER/RESEARCH ONLY; no broker calls). Signals from the lab's own rule code (loaded read-only,
data path redirected in memory to work/base_1m_aug.parquet; 300-minute day gate relaxed for TODAY only). Prices = real 1m option bars
(work/opt1m_2026-10-13.parquet): entry = OPEN of the minute after the signal minute, exit = CLOSE of the rule's exit minute (R01 family: OPEN of t+21,
as in live3). Qty = lib.lots real (NIFTY 13-Oct 65 x 10 = 650). Costs = lib.costs.net_at dated (day=2026-10-13), 1x & 1.5x. No price invented:
missing bar -> DATA_MISSING. Trade whose exit minute is not reached yet -> OPEN."""
import sys,os,re,types,json,traceback,datetime as dt,numpy as np,pandas as pd; sys.dont_write_bytecode=True
HERE=os.path.dirname(os.path.abspath(__file__)); W=HERE+"/work"; LAB="/Users/sahiltayde/paper_extra_rt/dhan/research/lab"; DAY="2026-10-13"; sys.path[:0]=[LAB+"/lib",LAB]
import costs as CO, lots as LO
QTY=LO.qty("NIFTY",DAY,10)
_rp=pd.read_parquet
VIXX=json.load(open(W+"/vix_daily.json"))
def rp(p,*a,**k):
    p=str(p)
    if p.endswith("lab_round7b/base_1m.parquet"): p=W+"/base_1m_aug.parquet"
    df=_rp(p,*a,**k)
    if p.endswith("global_daily.parquet"):
        df["date"]=df.date.astype(str).str[:10]; add=[d for d in VIXX if d not in set(df.date)]
        if add: df=pd.concat([df,pd.DataFrame({"date":add,"INDIAVIX":[VIXX[d] for d in add]})],ignore_index=True).sort_values("date").reset_index(drop=True)
    return df
pd.read_parquet=rp
def load_mod(name,path,subs=()):
    src=open(path).read()
    for a,b in subs:
        assert a in src,(path,a); src=src.replace(a,b)
    m=types.ModuleType(name); m.__file__=path; sys.modules[name]=m; cwd=os.getcwd(); os.chdir(os.path.dirname(path))
    try: exec(compile(src,path,"exec"),m.__dict__)
    finally: os.chdir(cwd)
    return m
OPT=_rp(W+"/opt1m_2026-10-13.parquet"); OPT=OPT[(OPT.symbol=="NIFTY")&(OPT.expiry==DAY)]
OB={(int(k),o):g.set_index("m") for (k,o),g in OPT.groupby(["strike","option_type"])}
BA=_rp(W+"/base_1m_aug.parquet"); TD=BA[BA.day==DAY].set_index("m"); LASTM=int(TD.index.max())
def hm(m): return None if m is None else f"{int(m)//60:02d}:{int(m)%60:02d}"
def opx(K,ot,m,col):
    g=OB.get((K,ot))
    if g is None or m not in g.index: return None,None
    r=g.loc[m]; r=r.iloc[0] if isinstance(r,pd.DataFrame) else r; return float(r[col]),r.src_detail
def price(strat,sg,sig_m,exit_m,mode="ATM",exit_col="close",why=""):
    ot="CE" if sg>0 else "PE"; ent=sig_m+1
    # FIX 2026-10-13 (Opposition #2): a STOP/TARGET is an index touch INSIDE minute exit_m; the option price at the touch is unknown,
    # so the first fill we can honestly use is the OPEN of the next minute (same rule as fair entry). Never the touch-minute close.
    if why in ("STOP","TARGET") and exit_m is not None: exit_m=exit_m+1; exit_col="open"
    if sig_m not in TD.index: return dict(strategy=strat,signalled="Y",side=ot,status="DATA_MISSING",note=f"no index bar {hm(sig_m)}")
    atm=int(round(TD.at[sig_m,"close"]/50)*50); K=atm-sg*100 if mode=="ITM100" else atm
    r=dict(strategy=strat,signalled="Y",side=ot,strike=K,signal_time=hm(sig_m),entry_time=hm(ent),exit_time=hm(exit_m),exit_reason=why)
    if ent>LASTM: r.update(status="PENDING_ENTRY"); return r
    p0,s0=opx(K,ot,ent,"open")
    if p0 is None: r.update(status="DATA_MISSING",note=f"no {K}{ot} bar at {hm(ent)}"); return r
    r.update(entry_px=p0,entry_src=s0)
    if exit_m is None or exit_m>LASTM or (exit_m==LASTM and LASTM<915 and why in("","open")):
        last,_=opx(K,ot,LASTM,"close"); r.update(status="OPEN",mark_time=hm(LASTM),mark_px=last); return r
    px,s1=opx(K,ot,exit_m,exit_col)
    if px is None: r.update(status="DATA_MISSING",note=f"no {K}{ot} bar at {hm(exit_m)}"); return r
    g,ch,n1,n15=CO.net_at(round(p0,2),round(max(px,.05),2),QTY,"NIFTY",DAY)
    r.update(exit_px=px,exit_src=s1,qty=QTY,pnl_1x=float(n1),pnl_1_5x=float(n15),status="CLOSED"); return r
ROWS=[]; ERR={}
def none(strat,why): ROWS.append(dict(strategy=strat,signalled="N",status=why))
def fam(name,fn):
    try: fn()
    except Exception as e: ERR[name]=f"{type(e).__name__}: {e}"; traceback.print_exc()
TODAY_GATE=[("len(g)>=300]","(len(g)>=300 or d==\"2026-10-13\")]")]
# ---------- PRIM (stress.py + combos CC2/R07) ----------
def prim():
    sys.path[:0]=[LAB+"/2026-10-11_stress",LAB+"/2026-10-11_range_boxes",LAB+"/2026-10-11_bigmove_re"]
    S=load_mod("stress",LAB+"/2026-10-11_stress/stress.py",TODAY_GATE)
    src=open(LAB+"/2026-10-11_combos/combos.py").read(); a=src.index("def CC2("); b=src.index("PRIM={")
    ns=dict(S.__dict__); ns.update(np=np,pd=pd); D=pd.read_parquet(LAB.replace("research/lab","output")+"/lab_round7b/base_1m.parquet",columns=["day","dte","src"]); ns["D"]=D[D.src.isin(["mac","hist"])].groupby("day").dte.first().to_dict()
    import bisect; ns["bisect"]=bisect; exec("def pvix(d): i=bisect.bisect_left(E.VD,d)-1; return E.VV[i]\nimport eng as E\n"+src[a:b],ns)
    h=open(LAB+"/2026-10-11_routed_book/hist.py").read(); hn={"np":np}; exec(h[h.index("def path("):h.index("def trade(")],hn); rpath=hn["path"]
    assert S.days[-1]==DAY, S.days[-1]; k=len(S.days)-1; g=S.GD[DAY]; m=g.m.values; c=g.close.values
    PR={"B2":(S.B2,S.RULES["B2"][1]),"C1":(S.C1,S.RULES["C1"][1]),"RB1":(S.RB1,S.RULES["RB1"][1]),"CC2":(ns["CC2"],{}),"R07":(ns["R07"],{}),"Q01":(S.Q01,S.RULES["Q01"][1])}
    vx=S.VX[DAY]; json.dump(dict(q01_vix_pct=vx[0],q01_vix_chg=vx[1]),open(W+"/q01_ctx.json","w"))
    for pn,(fn,pp) in PR.items():
        sigs=fn(k,g,pp); names=["Q01_ATM","Q01_ITM100"] if pn=="Q01" else [pn]
        if not sigs:
            for n in names: none(n,"NO_SIGNAL"+(f" (VIX pct {vx[0]:.2f}, chg {vx[1]:+.3f}; needs pct>=0.80 & chg>0.02)" if pn=="Q01" else ""))
            continue
        for e,sg,kw,itm in sigs:
            if e is None: continue
            kw=dict(kw); sf=kw.pop("stop_frac",None); sp=kw.pop("stop_pts",None)
            if pn=="Q01":   # signal on 10:00 close, entry 10:01 open
                sm=int(m[e])
                for n,mode in (("Q01_ATM","ATM"),("Q01_ITM100","ITM100")):
                    atm=int(round(c[e]/50)*50); K=atm-sg*100 if mode=="ITM100" else atm; p0,_=opx(K,"CE" if sg>0 else "PE",sm+1,"open")
                    if p0 is None: ROWS.append(price(n,sg,sm,None,mode)); continue
                    e2=e+1 if e+1<len(m) else e; z,mv=rpath(g,e2,sg,kw,sf*p0/.54); why="STOP" if mv is not None else ("TIME" if m[z]-m[e2]>=kw.get("hold",99) else "open")
                    ROWS.append(price(n,sg,sm,int(m[z]),mode,why=why))
            else:   # e already = minute after signal; entry at open of m[e]
                sm=int(m[e])-1; z,mv=rpath(g,e,sg,kw,sp); why="STOP" if mv is not None else ("" if m[z]>=LASTM else "EXIT")
                ROWS.append(price(pn,sg,sm,int(m[z]),why=why or "open"))
# ---------- EP ports ----------
def eps():
    sys.path[:0]=[LAB+"/2026-10-11_tv_ep23"]
    EP=load_mod("engine",LAB+"/2026-10-11_tv_ep23/engine.py",[('M = M[M.groupby("day").m.transform("size") >= 300]','M = M[(M.groupby("day").m.transform("size") >= 300) | (M.day == "2026-10-13")]')])
    EPP=load_mod("ports",LAB+"/2026-10-11_tv_ep23/ports.py")
    TR=pd.read_csv(LAB+"/2026-10-11_tv_ep23/test_results.csv")
    for t in TR.itertuples():
        B=EP.bars(int(t.tf)); T=EP.run(EPP.PORTS[t.ep](B),B); n=0
        for r in T.itertuples():
            if EP.DAY[r.f]!=DAY: continue
            n+=1; sg=int(r.sg); f=int(r.f); x=int(r.x); oc=EPP.PORTS[t.ep](B)["kind"] in("onclose","stopentry")   # stopentry: level touched inside f -> next open
            # FIX: onclose ports (EP-018) signal on the CLOSE of minute f, so entry = OPEN of f+1 (was OPEN of f = before the signal existed)
            sm=int(EP.MM[f]) if oc else int(EP.MM[f])-1
            k=str(r.exit).upper(); xm=int(EP.MM[x]); col="close"
            if k in("SIGNAL","REVERSE"): col="open"; xm=xm+1 if oc else xm   # engine fills O[x] (market) / C[x] (onclose -> next open)
            if xm<=sm: xm=sm+1; col="open"
            ROWS.append(price(t.ep,sg,sm,xm,exit_col=col,why=k))
        if not n: none(t.ep,"NO_SIGNAL")
# ---------- candle ideas ----------
def candles():
    C=load_mod("common",LAB+"/2026-10-12_realprice/v2_candle/common.py",[("if not np.isfinite(A) or A <= 0 or len(g) < 300: continue","if not np.isfinite(A) or A <= 0 or (len(g) < 300 and d != \"2026-10-13\"): continue")])
    C.RULES=json.load(open(LAB+"/2026-10-12_realprice/v2_candle/MINED_RULES.json"))["rules"]
    G=C.load(); CX=C.context(G); assert DAY in CX,"no context for today"; g=G[DAY]; X=CX[DAY]; m=g.m.values
    for v in C.VARS+sorted(C.RULES):
        last,cnt,n=-999,0,0
        for t,sg,stop in C.signals(v,g,X):
            if cnt>=C.CAP or m[t]-last<C.GAP or t+1>=len(m): continue
            last,cnt=m[t],cnt+1; e=t+1; S0=g.open.values[e]; R=sg*(S0-stop)
            if R<C.RMIN*X["A"]: R=C.RMIN*X["A"]
            if R>C.RMAX*X["A"]: continue
            for ex in C.EXITS:
                z,Sx,why=C.sim(g,e,sg,S0-sg*R,R,ex); why=why if not(why=="EOD" and m[z]<915) else "open"
                r=price(f"{C.IDEA(v)}:{v}:{ex}",sg,int(m[t]),int(m[z]),why=why); ROWS.append(r); n+=1
        if not n: none(f"{C.IDEA(v)}:{v}","NO_SIGNAL")
# ---------- R01 / R01_B3A_VOL (live3 spec) ----------
def r01():
    ix=TD.close; CUT=0.00021620371
    def cl(K,o,m): v,_=opx(K,o,m,"close"); return v
    def rv30(t):
        v=[ix[t-j] for j in range(30,-1,-1) if (t-j) in ix.index]
        if len(v)<20: return None
        r=np.diff(np.log(v)); return float(np.sqrt(((r-r.mean())**2).mean()))
    for rule in ("R01","R01_B3A_VOL"):
        busy=-1; n=0; miss=0
        for t in range(max(570,int(ix.index.min())+30),min(891,LASTM+1)):
            if t<=busy: continue
            if t not in ix.index: miss+=1; continue
            pk=next((t-5-j for j in range(3) if (t-5-j) in ix.index),None)
            if pk is None: continue
            a,b=ix[t],ix[pk]
            if abs(a/b-1)>=.0005: continue
            K=int(round(a/50)*50); cc=[cl(K,o,mm) for o,mm in (("CE",t),("CE",pk),("PE",t),("PE",pk))]
            if any(v is None or v<=0 for v in cc): miss+=1; continue
            dv=cc[0]/cc[1]-cc[2]/cc[3]; s=1 if dv>=.1 else -1 if dv<=-.1 else 0
            if s and rule=="R01_B3A_VOL":
                r=rv30(t)
                if r is None or r<CUT: s=0
            if not s: continue
            busy=t+21; n+=1; ROWS.append(price(rule,s,t,t+21,exit_col="open",why="TIME"))
        if not n: none(rule,"NO_SIGNAL"+(f" ({miss} minutes skipped for missing bars)" if miss else ""))
for nm,fn in (("PRIM",prim),("EP",eps),("CANDLES",candles),("R01",r01)): fam(nm,fn)
for s in ["HV_P6_CE","HV_P6_BOTH"]+[f"HV_P{i}_T1_H20" for i in (1,2,3,5,6,7,8,9,10)]+["HV_P4_T2_5M","HV_S1_T1_H20","HV_S2_T1_H20","HV_S3_T1_H20"]+["TV_"+x for x in "UTBOT MLAST SMCBC LORENTZ SQZ MSB_OB OBBB SRCH FVG BRKPROB WAVETR".split()]:
    none(s,"NOT_SCORED_YET (harvest/TV event generators not wired to live data yet)")
for k,v in ERR.items(): ROWS.append(dict(strategy="FAMILY_"+k,signalled="",status="ERROR",note=v))
R=pd.DataFrame(ROWS); stamp=dt.datetime.now(dt.timezone(dt.timedelta(hours=5.5))).strftime("%H%M")
R.insert(0,"run_ist",stamp); R.insert(1,"data_through",hm(LASTM))
R.to_csv(f"{HERE}/score_{stamp}IST.csv",index=False); R.to_csv(f"{HERE}/score_latest.csv",index=False)
cl=R[R.status=="CLOSED"] if "status" in R else R
print("run",stamp,"data through",hm(LASTM),"rows",len(R),"signalled",int((R.signalled=="Y").sum()),"closed",len(cl),
      "errors",ERR)
