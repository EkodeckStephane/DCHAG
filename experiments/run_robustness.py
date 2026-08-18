from __future__ import annotations
from pathlib import Path
import argparse,json,time,csv
import pandas as pd
from sklearn.metrics import brier_score_loss,log_loss
from dchag import load_config
from estimation import fit_scm
from experiments.run_retained import impute_states,path_scores,rss_mb
ROOT=Path(__file__).resolve().parents[1]
VALID={'missing_10','missing_30','missing_50','human_process_unobserved','structural_edge_drop'}

def run(context,variant):
    if variant not in VALID: raise ValueError(variant)
    cfg=load_config(ROOT/'configs'/f'{context}.yaml'); b=ROOT/'benchmarks'/context; out=ROOT/'results'/'raw'/context;out.mkdir(parents=True,exist_ok=True)
    complete=pd.read_csv(b/'test_observed.csv'); y=complete[complete.time==cfg.horizon-1].sort_values('trajectory_id')[cfg.target].to_numpy(int)
    if variant.startswith('missing_'):
        trainp=b/'variants'/f'train_{variant}.csv'; testp=b/'variants'/f'test_{variant}.csv'; kwargs={}; seed_off={'missing_10':0,'missing_30':100,'missing_50':200}[variant]
    elif variant=='human_process_unobserved':
        trainp=b/'variants'/'train_human_process_unobserved.csv';testp=b/'variants'/'test_human_process_unobserved.csv';kwargs={'drop_types':{'human','process'}};seed_off=300
    else:
        trainp=b/'train_observed.csv';testp=b/'test_observed.csv';
        drop=json.loads((ROOT/'experiments/structural_edge_drop.json').read_text())['dropped'][context];drop_set={(d['child'],d['parent'],d['lag']) for d in drop}
        kwargs={'parent_filter':lambda node,p:(node.id,p.node,p.lag) not in drop_set};seed_off=400
    t0=time.perf_counter();m=fit_scm(cfg,trainp,**kwargs); fitsec=time.perf_counter()-t0
    testv=pd.read_csv(testp)
    path_input=impute_states(m,testv) if variant.startswith('missing_') else testv
    ps=path_scores(cfg,m,complete,path_input)
    t0=time.perf_counter();pred=m.predict_trajectory_risk(testv,mc=300,seed=57000+seed_off);predsec=time.perf_counter()-t0
    bs=float(brier_score_loss(y,pred));ll=float(log_loss(y,pred.clip(1e-6,1-1e-6)))
    rows=[]
    for ci,c in enumerate(cfg.controls):
        t0=time.perf_counter();e=m.estimate_effect(c,n=50000,seed=58000+seed_off+ci);esec=time.perf_counter()-t0
        rows.append([context,variant,c,e['risk_reduction'],e['paired_se'],bs,ll,ps['precision'],ps['recall'],ps['f1'],fitsec,predsec,esec,rss_mb()])
    path=out/f'robustness_{variant}.csv'
    pd.DataFrame(rows,columns=['context','variant','control','risk_reduction','estimator_se','brier','log_loss','path_precision','path_recall','path_f1','fit_seconds','prediction_seconds','effect_seconds','ru_maxrss_mb']).to_csv(path,index=False)
    print(context,variant,'frozen',path)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--context',required=True);ap.add_argument('--variant',required=True,choices=sorted(VALID));a=ap.parse_args();run(a.context,a.variant)
