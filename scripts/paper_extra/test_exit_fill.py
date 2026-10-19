"""Test for the EP/stop-target fill fix. Independent of score_pass: checks a score CSV against raw Dhan option JSON.
Rules: (1) entry minute > signal minute; (2) a STOP/TARGET exit (index touch inside a minute) is filled at the raw OPEN of the
following minute, so exit minute > entry minute and exit_px == raw open; (2b) 2026-10-19: premium TRAIL and SAFETY_1515 exits follow the same next-minute-OPEN rule; live V2-depth exits (exit_src v2_depth_bid) are
filled at the triggering bid and are checked by test_live_pricer.py instead; (3) EP-018 signals sit on a 60m bar close ((m-555)%60==59)."""
import sys,glob,os,json,pandas as pd
F=sys.argv[1]; RUN=os.environ.get("PX_RUN",os.path.expanduser("~/Documents/all_about_dhan/data/paper_extra/2026-10-13/run"))
mm=lambda s:int(s[:2])*60+int(s[3:5])
def ob(K,o):
    j=json.load(open(f"{RUN}/{os.environ.get('PX_UNDERLYING','NIFTY')}_{os.environ.get('PX_EXP','2026-10-13')}_{K}_{o}.json")); t=pd.to_datetime(j["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata")
    return pd.Series(j["open"],index=t.hour*60+t.minute)
def cb(K,o):
    j=json.load(open(f"{RUN}/{os.environ.get('PX_UNDERLYING','NIFTY')}_{os.environ.get('PX_EXP','2026-10-13')}_{K}_{o}.json")); t=pd.to_datetime(j["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata")
    return pd.Series(j["close"],index=t.hour*60+t.minute)
S=pd.read_csv(F) if F.endswith(".csv") else pd.DataFrame(json.load(open(F))["rows"]).rename(columns={"rule_id":"rule"})
if not F.endswith(".csv"): S=S[S.rule.str.startswith("PX_")&(S.underlying==os.environ.get("PX_UNDERLYING","NIFTY"))]
S=S[S.status=="CLOSED"]; bad=[]
for r in S.itertuples():
    sm,em,xm=mm(r.signal_time),mm(r.entry_time),mm(r.exit_time)
    if em<=sm: bad.append(f"{r.strategy} {r.signal_time}: entry not after signal")
    if r.exit_reason in("STOP","TARGET","TRAIL","SAFETY_1515") and getattr(r,"exit_src","")!="v2_depth_bid":   # 2026-10-19 price exits: 1m path fills next-minute OPEN
        if xm<=em: bad.append(f"{r.strategy} {r.signal_time}: {r.exit_reason} exit {r.exit_time} not after entry {r.entry_time}")
        elif not (xm in ob(int(r.strike),r.side).index and abs(ob(int(r.strike),r.side)[xm]-r.exit_px)<=1e-6) and not (
                r.exit_reason in("TRAIL","SAFETY_1515","STOP","TARGET") and getattr(r,"rule","").startswith("PX_") and xm in cb(int(r.strike),r.side).index
                and abs(cb(int(r.strike),r.side)[xm]-r.exit_px)<=1e-6 and not any(q in ob(int(r.strike),r.side).index for q in (xm+1,xm+2,xm+3))):   # PX: no bar in the next 3 min -> trigger close
            bad.append(f"{r.strategy} {r.signal_time}: {r.exit_reason} exit px {r.exit_px} != raw open {r.exit_time}")
    if r.strategy=="EP-018" and (sm-555)%60!=59: bad.append(f"EP-018 signal {r.signal_time} is not a 60m bar close (look-ahead entry)")
print("\n".join(bad) or "ALL PASS"); sys.exit(1 if bad else 0)
