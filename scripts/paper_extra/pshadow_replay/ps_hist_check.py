import sys,os,types,json,numpy as np,pandas as pd
LAB="/workspace/dhan/research/lab"; sys.path[:0]=[LAB+"/lib",LAB]
def load_mod(name,path,subs=()):
    src=open(path).read()
    for a,b in subs: assert a in src; src=src.replace(a,b)
    m=types.ModuleType(name); m.__file__=path; sys.modules[name]=m; cwd=os.getcwd(); os.chdir(os.path.dirname(path))
    try: exec(compile(src,path,"exec"),m.__dict__)
    finally: os.chdir(cwd)
    return m
G=pd.read_parquet(LAB+"/2026-10-12_scenario_map/tagged.parquet"); G=G[(G.day>="2023-08-01")&(G.day<="2026-07-02")]
# EP-009
sys.path[:0]=[LAB+"/2026-10-11_tv_ep23"]
EP=load_mod("engine",LAB+"/2026-10-11_tv_ep23/engine.py"); EPP=load_mod("ports",LAB+"/2026-10-11_tv_ep23/ports.py")
TR=pd.read_csv(LAB+"/2026-10-11_tv_ep23/test_results.csv"); tf=int(TR[TR.ep=="EP-009"].tf.iloc[0]); print("EP-009 tf",tf, EPP.PORTS["EP-009"](EP.bars(tf))["kind"])
B=EP.bars(tf); T=EP.run(EPP.PORTS["EP-009"](B),B)
mine=sorted((EP.DAY[r.f],int(EP.MM[r.f]),int(r.sg),int(EP.MM[r.x])-int(EP.MM[r.f])) for r in T.itertuples() if "2023-08-01"<=EP.DAY[r.f]<="2026-07-02")
M=pd.read_parquet("/workspace/dhan/output/lab_round7b/base_1m.parquet",columns=["day","m","src"]); M=M[M.src.isin(["mac","hist"])].sort_values(["day","m"]).reset_index(drop=True); M=M[M.groupby("day").m.transform("size")>=300].reset_index(drop=True)
g9=G[G.strat=="EP-009"]; res=sorted((r.day,int(M.m.values[int(r.f)]),int(r.sg),int(r.hold)) for r in g9.itertuples())
print("EP-009 mine",len(mine),"research",len(res),"equal",mine==res); 
if mine!=res: print(sorted(set(mine)^set(res))[:6])
