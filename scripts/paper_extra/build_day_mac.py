"""Build full-day 1m set for 2026-10-13 (paper/research only). Sources: Dhan /charts/intraday 1m (src_detail=dhan_api_1m)
+ live recorder quote_snapshots converted to 1m bars (src_detail=live_tape, only for minutes the API lacks). Never invents prices.
Usage: build_day.py <api_run_dir> <tape_dir> <outdir>"""
import sys,json,glob,os,numpy as np,pandas as pd,datetime as dt
RUN,TAPE,OUT=sys.argv[1:4]; IST=dt.timezone(dt.timedelta(hours=5,minutes=30)); DAY=os.environ.get("PX_DAY","2026-10-13"); EXP=os.environ.get("PX_EXP",DAY)
def ld(fp):
    j=json.load(open(fp)); df=pd.DataFrame({k:j[k] for k in ("open","high","low","close","timestamp")})
    for k in ("volume","open_interest"): df[k]=j.get(k,[0]*len(df))
    t=pd.to_datetime(df.timestamp,unit="s",utc=True).dt.tz_convert("Asia/Kolkata"); df["ts"]=df.timestamp.astype(int)
    df["day"]=t.dt.strftime("%Y-%m-%d"); df["m"]=t.dt.hour*60+t.dt.minute; df["tsx"]=t; return df
# --- live tape -> 1m bars (mid else ltp; stale dropped; minute = first 16 chars of ltt-less event ts)
rows=[]
for l in open(os.path.join(TAPE,"quote_snapshots.jsonl")):
    j=json.loads(l); p=j["payload"]
    if p.get("stale"): continue
    px=p.get("mid") or p.get("ltp")
    if not px: continue
    rows.append((p["instrument_id"],j["timestamp"][:16],float(px)))
LT=pd.DataFrame(rows,columns=["iid","minute","px"])
LB=LT.groupby(["iid","minute"]).px.agg(open="first",high="max",low="min",close="last").reset_index() if len(LT) else pd.DataFrame()
if len(LB) and os.environ.get("PX_CUTOFF_M"):   # complete minutes only (the minute still forming is dropped)
    _c=int(os.environ["PX_CUTOFF_M"]); LB=LB[(LB.minute.str[11:13].astype(int)*60+LB.minute.str[14:16].astype(int))<_c]
LB.to_csv(os.path.join(OUT,"live_tape_1m.csv"),index=False)
# --- options (today) in hf_opt1m format, API first, tape fills
opts=[]
for fp in [p for p in glob.glob(os.path.join(RUN,"*_*_*_*.json")) if not os.path.basename(p).startswith("IDX_")]:
    und,exp,K,ot=os.path.basename(fp)[:-5].split("_"); d=ld(fp); d=d[d.day==DAY]
    d=d.assign(trading_day=DAY,symbol=und,strike=int(K),option_type=ot,expiry=exp,src_detail="dhan_api_1m"); opts.append(d)
O=pd.concat(opts,ignore_index=True)
if len(LB):
    LB["und"]=LB.iid.str.split(":").str[1]; LB["expiry"]=LB.iid.str.split(":").str[2]; LB["strike"]=LB.iid.str.split(":").str[3].astype(float).astype(int); LB["option_type"]=LB.iid.str.split(":").str[4]
    LB["m"]=LB.minute.str[11:13].astype(int)*60+LB.minute.str[14:16].astype(int)
    have=set(zip(O.symbol,O.strike,O.option_type,O.m)); add=LB[[ (u,k,o,m) not in have for u,k,o,m in zip(LB.und,LB.strike,LB.option_type,LB.m)]]
    if len(add):
        A=pd.DataFrame(dict(open=add.open,high=add.high,low=add.low,close=add.close,volume=0,open_interest=0,m=add.m,day=DAY,trading_day=DAY,symbol=add.und,strike=add.strike,option_type=add.option_type,expiry=add.expiry,src_detail="live_tape"))
        A["tsx"]=pd.to_datetime(DAY)+pd.to_timedelta(A.m,unit="min"); A["tsx"]=A.tsx.dt.tz_localize("Asia/Kolkata"); O=pd.concat([O,A],ignore_index=True)
O["timestamp"]=O.tsx; O=O.drop(columns=["tsx","ts"],errors="ignore").sort_values(["symbol","strike","option_type","m"])
O.to_parquet(os.path.join(OUT,f"opt1m_{DAY}.parquet"),index=False)
# --- index base rows (NIFTY) for days after the lab base_1m (2026-09-03) through today
I=ld(os.path.join(RUN,"IDX_NIFTY.json")); I=I[(I.day>"2026-09-03")&(I.m>=555)&(I.m<=929)].copy(); I["src"]="hist"; I["src_detail"]="dhan_api_1m"
S=ld(os.path.join(RUN,"IDX_SENSEX.json")); S=S[(S.day>"2026-09-03")&(S.m>=555)&(S.m<=929)].copy(); S["src_detail"]="dhan_api_1m"
S.drop(columns=["tsx"]).to_parquet(os.path.join(OUT,"sensex_idx_1m.parquet"),index=False)
def nexttue(d):
    x=dt.date.fromisoformat(d); return (x+dt.timedelta(days=(1-x.weekday())%7)).isoformat()
I["expiry"]=I.day.map(nexttue); I.loc[I.day==DAY,"expiry"]=EXP
I["dte"]=[np.busday_count(a,b) for a,b in zip(I.day,I.expiry)]; I["dte_cal"]=[(dt.date.fromisoformat(b)-dt.date.fromisoformat(a)).days for a,b in zip(I.day,I.expiry)]
I["tp"]=(I.high+I.low+I.close)/3; I["twap"]=I.groupby("day").tp.transform(lambda s:s.expanding().mean())
for c in ("ce_o","ce_h","ce_l","ce_c","pe_o","pe_h","pe_l","pe_c","kce_close","kpe_close","bnf"): I[c]=np.nan
N=O[(O.symbol=="NIFTY")&(O.expiry==EXP)].set_index(["strike","option_type","m"])
t=I.day==DAY
for i in I.index[t]:
    m=I.at[i,"m"]; a=int(round(I.at[i,"close"]/50)*50); kc,kp=a-100,a+100; I.at[i,"kce_close"]=kc; I.at[i,"kpe_close"]=kp
    for K,ot,p in ((kc,"CE","ce"),(kp,"PE","pe")):
        if (K,ot,m) in N.index:
            r=N.loc[(K,ot,m)]; r=r.iloc[0] if isinstance(r,pd.DataFrame) else r
            for a_,b_ in (("o","open"),("h","high"),("l","low"),("c","close")): I.at[i,f"{p}_{a_}"]=r[b_]
I=I.drop(columns=["tp","tsx","timestamp","volume","open_interest"],errors="ignore")
B=pd.read_parquet("/Users/sahiltayde/paper_extra_rt/dhan/output/lab_round7b/base_1m.parquet"); B["src_detail"]="lab_base_1m"
X=pd.concat([B[B.day<="2026-09-03"],I],ignore_index=True).sort_values(["day","m"]).reset_index(drop=True)
hm=X.src.isin(["mac","hist"]); D=X[hm].groupby("day").agg(H=("high","max"),L=("low","min"),C=("close","last"))
tr=np.maximum(D.H-D.L,np.maximum(abs(D.H-D.C.shift()),abs(D.L-D.C.shift()))); A=tr.ewm(alpha=1/14,adjust=False).mean().shift()
nd=X.day>"2026-09-03"; X.loc[nd,"atr14"]=X.loc[nd,"day"].map(A)
X.to_parquet(os.path.join(OUT,"base_1m_aug.parquet"),index=False)
# coverage report
tm=set(I[t].m); exp=list(range(555,max(tm)+1)) if tm else []
cov=dict(day=DAY,index_minutes=len(tm),index_first=min(tm) if tm else None,index_last=max(tm) if tm else None,index_missing=[m for m in exp if m not in tm],
 option_series=int(O.groupby(["symbol","strike","option_type"]).ngroups),option_rows_api=int((O.src_detail=="dhan_api_1m").sum()),option_rows_tape=int((O.src_detail=="live_tape").sum()),
 ce_o_missing_today=int(I[t].ce_o.isna().sum()),pe_o_missing_today=int(I[t].pe_o.isna().sum()),hist_days_added=sorted(set(I.day))[:1]+sorted(set(I.day))[-1:],n_days_added=int(I.day.nunique()))
json.dump(cov,open(os.path.join(OUT,"coverage.json"),"w"),indent=1); print(json.dumps(cov))
