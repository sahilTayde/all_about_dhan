"""Test for the EP/stop-target fill fix. Independent of score_pass: checks a score CSV against raw Dhan option JSON.
Rules: (1) entry minute > signal minute; (2) a STOP/TARGET exit (index touch inside a minute) is filled at the raw OPEN of the
following minute, so exit minute > entry minute and exit_px == raw open; (3) EP-018 signals sit on a 60m bar close ((m-555)%60==59)."""
import sys,glob,os,json,pandas as pd
F=sys.argv[1]; RUN=os.environ.get("PX_RUN",os.path.expanduser("~/Documents/all_about_dhan/data/paper_extra/2026-10-13/run"))
mm=lambda s:int(s[:2])*60+int(s[3:5])
def ob(K,o):
    j=json.load(open(f"{RUN}/NIFTY_2026-10-13_{K}_{o}.json")); t=pd.to_datetime(j["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata")
    return pd.Series(j["open"],index=t.hour*60+t.minute)
S=pd.read_csv(F); S=S[S.status=="CLOSED"]; bad=[]
for r in S.itertuples():
    sm,em,xm=mm(r.signal_time),mm(r.entry_time),mm(r.exit_time)
    if em<=sm: bad.append(f"{r.strategy} {r.signal_time}: entry not after signal")
    if r.exit_reason in("STOP","TARGET"):
        if xm<=em: bad.append(f"{r.strategy} {r.signal_time}: {r.exit_reason} exit {r.exit_time} not after entry {r.entry_time}")
        elif abs(ob(int(r.strike),r.side)[xm]-r.exit_px)>1e-6: bad.append(f"{r.strategy} {r.signal_time}: {r.exit_reason} exit px {r.exit_px} != raw open {r.exit_time}")
    if r.strategy=="EP-018" and (sm-555)%60!=59: bad.append(f"EP-018 signal {r.signal_time} is not a 60m bar close (look-ahead entry)")
print("\n".join(bad) or "ALL PASS"); sys.exit(1 if bad else 0)
