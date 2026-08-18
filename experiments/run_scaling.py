from __future__ import annotations
import argparse, json, resource, subprocess, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from estimation.fitted_scm import FittedSCM, FittedNode
ROOT=Path(__file__).resolve().parents[1]

def rss_mb():
    x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(x/1024.0 if x>10000 else x/(1024.0*1024.0))

def make_model(n_attack:int,n_controls:int,horizon:int=4)->FittedSCM:
    controls=[FittedNode(f'c{i}','control',-2.0,()) for i in range(n_controls)]
    ctx=FittedNode('context','context',-0.25,())
    nodes=[*controls,ctx]
    prev=None
    for i in range(n_attack):
        typ=('human','process','technical')[i%3]
        ps=[('context',0,0.35)]
        if prev is not None: ps.append((prev,0,0.72))
        if i>=3: ps.append((f'x{i-3}',1,0.34))
        if n_controls: ps.append((f'c{i%n_controls}',0,-0.55))
        nodes.append(FittedNode(f'x{i}',typ,-1.05,tuple(ps)))
        prev=f'x{i}'
    target='x'+str(n_attack-1)
    base={f'c{i}':0 for i in range(n_controls)}
    return FittedSCM(f'scale_{n_attack}_{n_controls}',horizon,tuple(nodes),target,base,'synthetic_scaling')

def prospective_df(ntraj,horizon,n_controls,seed):
    rng=np.random.default_rng(seed); rows=[]
    ctx=rng.integers(0,2,ntraj)
    plans={f'c{i}':rng.binomial(1,0.18,ntraj) for i in range(n_controls)}
    for tid in range(ntraj):
        for t in range(horizon):
            r={'trajectory_id':tid,'time':t,'context':ctx[tid]}
            for i in range(n_controls): r[f'c{i}']=plans[f'c{i}'][tid]
            rows.append(r)
    return pd.DataFrame(rows)

def child(axis,value):
    if axis=='graph':
        m=make_model(int(value),4); t=time.perf_counter(); m.estimate_effect('c0',n=20000,seed=70000+int(value)); sec=time.perf_counter()-t
        return {'axis':axis,'value':int(value),'attack_nodes':int(value),'controls':4,'horizon':4,'mc':20000,'event_rows':None,'seconds':sec,'peak_rss_mb':rss_mb(),'status':'ok'}
    if axis=='events':
        n=int(value);m=make_model(50,4);df=prospective_df(n,4,4,71000+n);t=time.perf_counter();m.predict_trajectory_risk(df,mc=50,seed=72000+n);sec=time.perf_counter()-t
        return {'axis':axis,'value':n,'attack_nodes':50,'controls':4,'horizon':4,'mc':50,'event_rows':n*4,'seconds':sec,'peak_rss_mb':rss_mb(),'status':'ok'}
    if axis=='controls':
        k=int(value);m=make_model(50,k);t=time.perf_counter()
        for i in range(k):m.estimate_effect(f'c{i}',n=10000,seed=73000+100*k+i)
        sec=time.perf_counter()-t
        return {'axis':axis,'value':k,'attack_nodes':50,'controls':k,'horizon':4,'mc':10000,'event_rows':None,'seconds':sec,'peak_rss_mb':rss_mb(),'status':'ok'}
    raise ValueError(axis)

def parent():
    grids={'graph':[12,25,50,100,200,400],'events':[250,1000,3000],'controls':[1,4,8,16]}; rows=[]
    for axis,vals in grids.items():
        for v in vals:
            p=subprocess.run([sys.executable,__file__,'--child','--axis',axis,'--value',str(v)],capture_output=True,text=True)
            if p.returncode==0:
                rows.append(json.loads(p.stdout.strip().splitlines()[-1]))
            else:
                rows.append({'axis':axis,'value':v,'status':'failed','stderr':p.stderr[-500:]})
    out=ROOT/'results'/'processed';out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/'scaling_results.csv',index=False)
    (ROOT/'results'/'raw'/'scaling_run.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(pd.DataFrame(rows).to_string(index=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--child',action='store_true');ap.add_argument('--axis');ap.add_argument('--value')
    a=ap.parse_args()
    if a.child: print(json.dumps(child(a.axis,int(a.value))))
    else: parent()
