from __future__ import annotations
from pathlib import Path
import argparse,csv,json,time,resource
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss,log_loss
from dchag import load_config
from estimation import fit_scm
from baselines.observational_outcome import ObservationalOutcomeBaseline
from baselines.risk_scores import SEAGInspiredRiskBaseline,QualitativeRiskMatrixBaseline

ROOT=Path(__file__).resolve().parents[1]
MODEL_SPECS={
    'DCHAG_full':{},
    'DCHAG_technical_only':{'drop_types':{'human','process'}},
    'DCHAG_no_human':{'drop_types':{'human'}},
    'DCHAG_no_process':{'drop_types':{'process'}},
    'DCHAG_no_temporal':{'drop_lags':True},
}

def rss_mb():
    x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(x/1024.0 if x>10_000 else x/(1024.0*1024.0))

def true_active_set(cfg,state_by_time):
    t=cfg.horizon-1; seen=set(); result=set()
    def visit(nid,tt):
        key=(nid,tt)
        if key in seen or tt<0:return
        seen.add(key)
        if int(state_by_time[tt].get(nid,0))!=1:return
        if nid!=cfg.target and cfg.node_map[nid].type in {'human','process','technical'}: result.add(f'{nid}@{tt}')
        for p in cfg.node_map[nid].parents:
            pt=tt-p.lag
            if p.coef>0 and pt>=0 and cfg.node_map[p.node].type in {'human','process','technical'}:
                if int(state_by_time[pt].get(p.node,0))==1: visit(p.node,pt)
    if int(state_by_time[t].get(cfg.target,0))==1: visit(cfg.target,t)
    return result

def fitted_active_set(model,state_by_time):
    t=model.horizon-1; node_map=model.node_map; seen=set();result=set()
    def visit(nid,tt):
        key=(nid,tt)
        if key in seen or tt<0 or nid not in node_map:return
        seen.add(key)
        val=state_by_time[tt].get(nid,0)
        if pd.isna(val) or int(val)!=1:return
        node=node_map[nid]
        if nid!=model.target and node.type in {'human','process','technical'}: result.add(f'{nid}@{tt}')
        for pid,lag,coef in node.parents:
            pt=tt-lag
            if coef>0 and pt>=0 and pid in node_map and node_map[pid].type in {'human','process','technical'}:
                pv=state_by_time[pt].get(pid,0)
                if not pd.isna(pv) and int(pv)==1: visit(pid,pt)
    if not pd.isna(state_by_time[t].get(model.target,0)) and int(state_by_time[t].get(model.target,0))==1: visit(model.target,t)
    return result

def path_scores(cfg,model,complete_df,observed_df=None):
    observed_df=complete_df if observed_df is None else observed_df
    truth={tid:g.sort_values('time') for tid,g in complete_df.groupby('trajectory_id')}
    obs={tid:g.sort_values('time') for tid,g in observed_df.groupby('trajectory_id')}
    vals=[]
    for tid,g in truth.items():
        if int(g.iloc[-1][cfg.target])!=1: continue
        tstates=[r.to_dict() for _,r in g.iterrows()]; ostates=[r.to_dict() for _,r in obs[tid].iterrows()]
        a=true_active_set(cfg,tstates); b=fitted_active_set(model,ostates)
        tp=len(a&b); prec=tp/len(b) if b else (1.0 if not a else 0.0); rec=tp/len(a) if a else 1.0
        f1=2*prec*rec/(prec+rec) if prec+rec else 0.0
        vals.append((prec,rec,f1))
    arr=np.array(vals,float)
    return {'n_target_positive':len(vals),'precision':float(arr[:,0].mean()),'recall':float(arr[:,1].mean()),'f1':float(arr[:,2].mean())} if len(vals) else {'n_target_positive':0,'precision':1,'recall':1,'f1':1}

def impute_states(model,df):
    out=df.copy().sort_values(['trajectory_id','time']).reset_index(drop=True)
    idx={(int(r.trajectory_id),int(r.time)):i for i,r in out[['trajectory_id','time']].iterrows()}
    node_map=model.node_map
    for tid in sorted(out.trajectory_id.unique()):
        for t in range(model.horizon):
            ri=idx[(int(tid),t)]
            for node in model.nodes:
                if node.id not in out.columns or pd.notna(out.at[ri,node.id]): continue
                eta=node.intercept
                for pid,lag,coef in node.parents:
                    pt=t-lag
                    pv=0.0 if pt<0 else out.at[idx[(int(tid),pt)],pid]
                    if pd.isna(pv): pv=0.0
                    eta+=coef*float(pv)
                p=1/(1+np.exp(-np.clip(eta,-35,35)));out.at[ri,node.id]=int(p>=0.5)
    return out

def dump_model(model):
    return {'name':model.name,'target':model.target,'baseline_controls':model.baseline_controls,
            'nodes':[{'id':n.id,'type':n.type,'intercept':n.intercept,'parents':[{'node':p[0],'lag':p[1],'coef':p[2]} for p in n.parents]} for n in model.nodes]}

def run(context,stage="all"):
    cfg_path=ROOT/'configs'/f'{context}.yaml'; cfg=load_config(cfg_path)
    b=ROOT/'benchmarks'/context; out=ROOT/'results'/'raw'/context;out.mkdir(parents=True,exist_ok=True)
    train=pd.read_csv(b/'train_observed.csv'); test=pd.read_csv(b/'test_observed.csv')
    y=test[test.time==cfg.horizon-1].sort_values('trajectory_id')[cfg.target].to_numpy(int)
    tids=np.sort(test.trajectory_id.unique())
    runtime=[]; models={}; params={}
    for mi,(name,kwargs) in enumerate(MODEL_SPECS.items()):
        t0=time.perf_counter(); model=fit_scm(cfg,b/'train_observed.csv',**kwargs); dt=time.perf_counter()-t0
        models[name]=model;params[name]=dump_model(model);runtime.append([name,'fit',dt,rss_mb()])
    # comparison baselines
    t0=time.perf_counter();obs=ObservationalOutcomeBaseline(cfg).fit(train);runtime.append(['ObservationalOutcome','fit',time.perf_counter()-t0,rss_mb()])
    t0=time.perf_counter();seag=SEAGInspiredRiskBaseline(cfg).fit(train);runtime.append(['SEAGInspiredRisk','fit',time.perf_counter()-t0,rss_mb()])
    t0=time.perf_counter();matrix=QualitativeRiskMatrixBaseline(cfg).fit(train);runtime.append(['QualitativeRiskMatrix','fit',time.perf_counter()-t0,rss_mb()])

    # Freeze effect estimates before any scoring stage sees simulator truth.
    effect_rows=[]
    for mi,(name,model) in enumerate(models.items()):
        for ci,c in enumerate(cfg.controls):
            seed=51000+1000*list(MODEL_SPECS).index(name)+100*list(sorted((ROOT/'configs').glob('*.yaml'))).index(cfg_path)+ci
            t0=time.perf_counter(); e=model.estimate_effect(c,n=50000,seed=seed);dt=time.perf_counter()-t0
            effect_rows.append([context,name,c,e['baseline_risk'],e['intervention_risk'],e['risk_reduction'],e['paired_se'],seed])
            runtime.append([name,f'effect:{c}',dt,rss_mb()])
    for c in cfg.controls:
        e=obs.association_effect(c);effect_rows.append([context,'ObservationalOutcome',c,e['baseline_risk'],e['intervention_risk'],e['risk_reduction'],'',''])
    with (out/'effect_estimates.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['context','model','control','baseline_risk','intervention_risk','risk_reduction','estimator_se','seed']);w.writerows(effect_rows)

    # Prospective probability predictions from context/control history only for structural models.
    pred={'trajectory_id':tids,'y_true':y}
    for mi,(name,model) in enumerate(models.items()):
        t0=time.perf_counter();p=model.predict_trajectory_risk(test,mc=300,seed=55000+mi);runtime.append([name,'risk_prediction',time.perf_counter()-t0,rss_mb()]);pred[name]=p
    pred['ObservationalOutcome']=obs.predict_proba(test);pred['SEAGInspiredRisk']=seag.predict_proba(test);pred['QualitativeRiskMatrix']=matrix.predict_proba(test)
    pd.DataFrame(pred).to_csv(out/'risk_predictions.csv',index=False)

    # Path metrics from complete observational state projection.
    path=[]
    for name,model in models.items():
        s=path_scores(cfg,model,test);path.append([context,name,s['n_target_positive'],s['precision'],s['recall'],s['f1']])
    pd.DataFrame(path,columns=['context','model','n_target_positive','precision','recall','f1']).to_csv(out/'path_metrics.csv',index=False)

    # Persist the frozen main block before optional robustness stages.
    (out/'model_parameters.json').write_text(json.dumps(params,indent=2,sort_keys=True),encoding='utf-8')
    pd.DataFrame(runtime,columns=['model','operation','seconds','ru_maxrss_mb']).to_csv(out/'runtime_main.csv',index=False)
    (out/'main_complete.json').write_text(json.dumps({'context':context,'status':'main_predictions_frozen','ground_truth_read':False},indent=2),encoding='utf-8')
    if stage=='main':
        print(context,'main predictions frozen',out)
        return

    # Robustness models and estimates.
    robust=[]
    variants=['missing_10','missing_30','missing_50']
    for vi,v in enumerate(variants):
        train_path=b/'variants'/f'train_{v}.csv';test_path=b/'variants'/f'test_{v}.csv'
        t0=time.perf_counter();m=fit_scm(cfg,train_path);runtime.append([f'DCHAG_{v}','fit',time.perf_counter()-t0,rss_mb()])
        testv=pd.read_csv(test_path);imputed=impute_states(m,testv)
        ps=path_scores(cfg,m,test,imputed)
        p=m.predict_trajectory_risk(testv,mc=300,seed=57000+vi)
        bs=float(brier_score_loss(y,p));ll=float(log_loss(y,np.clip(p,1e-6,1-1e-6)))
        for ci,c in enumerate(cfg.controls):
            e=m.estimate_effect(c,n=50000,seed=58000+100*vi+ci)
            robust.append([context,v,c,e['risk_reduction'],e['paired_se'],bs,ll,ps['precision'],ps['recall'],ps['f1']])
    # no human/process observability -> technical-only estimator
    v='human_process_unobserved'; train_path=b/'variants'/f'train_{v}.csv';test_path=b/'variants'/f'test_{v}.csv'
    m=fit_scm(cfg,train_path,drop_types={'human','process'});testv=pd.read_csv(test_path);ps=path_scores(cfg,m,test,testv);p=m.predict_trajectory_risk(testv,mc=300,seed=59000);bs=float(brier_score_loss(y,p));ll=float(log_loss(y,np.clip(p,1e-6,1-1e-6)))
    for ci,c in enumerate(cfg.controls):
        e=m.estimate_effect(c,n=50000,seed=59100+ci);robust.append([context,v,c,e['risk_reduction'],e['paired_se'],bs,ll,ps['precision'],ps['recall'],ps['f1']])
    # frozen structural edge drop
    drop=json.loads((ROOT/'experiments/structural_edge_drop.json').read_text())['dropped'][context];drop_set={(d['child'],d['parent'],d['lag']) for d in drop}
    filt=lambda node,p:(node.id,p.node,p.lag) not in drop_set
    m=fit_scm(cfg,b/'train_observed.csv',parent_filter=filt);ps=path_scores(cfg,m,test);p=m.predict_trajectory_risk(test,mc=300,seed=59500);bs=float(brier_score_loss(y,p));ll=float(log_loss(y,np.clip(p,1e-6,1-1e-6)))
    for ci,c in enumerate(cfg.controls):
        e=m.estimate_effect(c,n=50000,seed=59600+ci);robust.append([context,'structural_edge_drop',c,e['risk_reduction'],e['paired_se'],bs,ll,ps['precision'],ps['recall'],ps['f1']])
    pd.DataFrame(robust,columns=['context','variant','control','risk_reduction','estimator_se','brier','log_loss','path_precision','path_recall','path_f1']).to_csv(out/'robustness_estimates.csv',index=False)

    pd.DataFrame(runtime,columns=['model','operation','seconds','ru_maxrss_mb']).to_csv(out/'runtime_all.csv',index=False)
    (out/'run_complete.json').write_text(json.dumps({'context':context,'status':'predictions_frozen','ground_truth_read':False},indent=2),encoding='utf-8')
    print(context,'predictions frozen',out)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--context',required=True);ap.add_argument('--stage',choices=['main','all'],default='all');args=ap.parse_args();run(args.context,args.stage)
