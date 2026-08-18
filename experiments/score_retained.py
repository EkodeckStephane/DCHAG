from __future__ import annotations
from pathlib import Path
import csv,json,itertools,math
import numpy as np
import pandas as pd
from scipy.stats import kendalltau,spearmanr
ROOT=Path(__file__).resolve().parents[1]
CONTEXTS=['bec_payment','data_exfiltration','helpdesk_identity','it_ot_maintenance']
CAUSAL_MODELS=['DCHAG_full','ObservationalOutcome','DCHAG_technical_only','DCHAG_no_human','DCHAG_no_process','DCHAG_no_temporal']
RISK_MODELS=['DCHAG_full','ObservationalOutcome','DCHAG_technical_only','DCHAG_no_human','DCHAG_no_process','DCHAG_no_temporal','SEAGInspiredRisk','QualitativeRiskMatrix']
B=2000

def holm(pvals:dict[str,float])->dict[str,float]:
    items=sorted(pvals.items(),key=lambda kv:kv[1]);m=len(items);out={};running=0.0
    for i,(k,p) in enumerate(items):
        adj=min(1.0,(m-i)*p);running=max(running,adj);out[k]=running
    return out

def exact_signflip_p(d):
    d=np.asarray(d,float);obs=abs(d.mean());n=len(d);count=0;tot=2**n
    for bits in range(tot):
        signs=np.array([1 if (bits>>i)&1 else -1 for i in range(n)])
        if abs((d*signs).mean()) >= obs-1e-15: count+=1
    return count/tot

def bootstrap_mean_ci(d,seed):
    d=np.asarray(d,float);rng=np.random.default_rng(seed);idx=rng.integers(0,len(d),size=(B,len(d)));vals=d[idx].mean(axis=1)
    return float(np.quantile(vals,.025)),float(np.quantile(vals,.975))

def predictive_bootstrap(diff_by_ctx,seed):
    rng=np.random.default_rng(seed);obs=float(np.mean([np.mean(x) for x in diff_by_ctx]));vals=np.empty(B)
    for b in range(B):
        vals[b]=np.mean([x[rng.integers(0,len(x),size=len(x))].mean() for x in diff_by_ctx])
    lo,hi=np.quantile(vals,[.025,.975]);le=(np.sum(vals<=0)+1)/(B+1);ge=(np.sum(vals>=0)+1)/(B+1);p=min(1.0,2*min(le,ge))
    return obs,float(lo),float(hi),float(p)

def load_gt():
    gt={}
    for c in CONTEXTS:
        effects=json.loads((ROOT/'benchmarks'/c/'ground_truth/intervention_effects.json').read_text())
        gt[c]={e['control']:e for e in effects}
    return gt

def main():
    gt=load_gt(); processed=ROOT/'results'/'processed';stats=ROOT/'results'/'statistics';processed.mkdir(parents=True,exist_ok=True);stats.mkdir(parents=True,exist_ok=True)
    # Effect scoring
    effect=[]
    for c in CONTEXTS:
        est=pd.read_csv(ROOT/'results'/'raw'/c/'effect_estimates.csv')
        for _,r in est.iterrows():
            truth=gt[c][r.control]['risk_reduction'];err=float(r.risk_reduction)-truth
            effect.append([c,r.model,r.control,truth,float(r.risk_reduction),err,abs(err)])
    eff=pd.DataFrame(effect,columns=['context','model','control','ground_truth','estimate','signed_error','absolute_error']);eff.to_csv(processed/'effect_accuracy.csv',index=False)
    # causal paired inference
    full=eff[eff.model=='DCHAG_full'].sort_values(['context','control'])
    causal_stats=[];pvals={}
    for j,m in enumerate(CAUSAL_MODELS[1:]):
        q=eff[eff.model==m].sort_values(['context','control']);d=full.absolute_error.to_numpy()-q.absolute_error.to_numpy()
        p=exact_signflip_p(d);pvals[m]=p;lo,hi=bootstrap_mean_ci(d,62026+j)
        causal_stats.append([m,float(d.mean()),float(np.median(d)),lo,hi,p])
    hadj=holm(pvals)
    cdf=pd.DataFrame(causal_stats,columns=['comparator','mean_abs_error_difference_DCHAG_minus_comparator','median_difference','ci95_low','ci95_high','p_raw'])
    cdf['p_holm']=cdf.comparator.map(hadj);cdf.to_csv(stats/'effect_error_pairwise_tests.csv',index=False)
    # summary model error
    eff.groupby('model').agg(mean_abs_error=('absolute_error','mean'),median_abs_error=('absolute_error','median'),mean_bias=('signed_error','mean'),rmse=('signed_error',lambda x:float(np.sqrt(np.mean(np.square(x)))))).reset_index().to_csv(processed/'effect_model_summary.csv',index=False)
    # Ranking + regret
    rank=[]
    for c in CONTEXTS:
        truths={ctl:e['risk_reduction'] for ctl,e in gt[c].items()};controls=sorted(truths);tv=np.array([truths[x] for x in controls]);best=max(truths.values())
        for m in CAUSAL_MODELS:
            sub=eff[(eff.context==c)&(eff.model==m)].set_index('control');ev=np.array([sub.loc[x,'estimate'] for x in controls]);
            kt=float(kendalltau(tv,ev).statistic);sr=float(spearmanr(tv,ev).statistic);selected=controls[int(np.argmax(ev))];reg=0.0 if best==0 else (best-truths[selected])/best
            rank.append([c,m,kt,sr,selected,best,truths[selected],reg])
    rdf=pd.DataFrame(rank,columns=['context','model','kendall_tau','spearman_rho','selected_control','best_true_effect','selected_true_effect','normalized_regret']);rdf.to_csv(processed/'control_ranking.csv',index=False)
    rdf.groupby('model').agg(mean_kendall=('kendall_tau','mean'),median_kendall=('kendall_tau','median'),mean_spearman=('spearman_rho','mean'),mean_regret=('normalized_regret','mean'),median_regret=('normalized_regret','median')).reset_index().to_csv(processed/'control_ranking_summary.csv',index=False)
    # Predictive scores + per-sample differences
    risk_rows=[]; score_samples={endpoint:{m:[] for m in RISK_MODELS[1:]} for endpoint in ['brier','log_loss']}
    for c in CONTEXTS:
        d=pd.read_csv(ROOT/'results'/'raw'/c/'risk_predictions.csv');y=d.y_true.to_numpy(int)
        fullp=np.clip(d['DCHAG_full'].to_numpy(float),1e-6,1-1e-6);full_b=(fullp-y)**2;full_l=-(y*np.log(fullp)+(1-y)*np.log(1-fullp))
        for m in RISK_MODELS:
            p=np.clip(d[m].to_numpy(float),1e-6,1-1e-6);bs=(p-y)**2;ll=-(y*np.log(p)+(1-y)*np.log(1-p));risk_rows.append([c,m,float(bs.mean()),float(ll.mean())])
            if m!='DCHAG_full':score_samples['brier'][m].append(full_b-bs);score_samples['log_loss'][m].append(full_l-ll)
    risk=pd.DataFrame(risk_rows,columns=['context','model','brier','log_loss']);risk.to_csv(processed/'predictive_scores.csv',index=False)
    risk.groupby('model').agg(mean_brier=('brier','mean'),mean_log_loss=('log_loss','mean')).reset_index().to_csv(processed/'predictive_score_summary.csv',index=False)
    for ei,endpoint in enumerate(['brier','log_loss']):
        rows=[];praw={}
        for j,m in enumerate(RISK_MODELS[1:]):
            obs,lo,hi,p=predictive_bootstrap(score_samples[endpoint][m],62026+100*ei+j);praw[m]=p;rows.append([m,obs,lo,hi,p])
        adj=holm(praw);df=pd.DataFrame(rows,columns=['comparator','mean_difference_DCHAG_minus_comparator','ci95_low','ci95_high','p_raw']);df['p_holm']=df.comparator.map(adj);df.to_csv(stats/f'{endpoint}_pairwise_tests.csv',index=False)
    # Path metrics
    path=pd.concat([pd.read_csv(ROOT/'results'/'raw'/c/'path_metrics.csv') for c in CONTEXTS],ignore_index=True);path.to_csv(processed/'path_metrics.csv',index=False)
    path.groupby('model').agg(mean_precision=('precision','mean'),mean_recall=('recall','mean'),mean_f1=('f1','mean')).reset_index().to_csv(processed/'path_metric_summary.csv',index=False)
    # Robustness scoring
    rob=[]
    for c in CONTEXTS:
        for v in ['missing_10','missing_30','missing_50','human_process_unobserved','structural_edge_drop']:
            d=pd.read_csv(ROOT/'results'/'raw'/c/f'robustness_{v}.csv')
            for _,r in d.iterrows():
                tr=gt[c][r.control]['risk_reduction'];rob.append([c,v,r.control,tr,float(r.risk_reduction),abs(float(r.risk_reduction)-tr),r.brier,r.log_loss,r.path_precision,r.path_recall,r.path_f1])
    rob=pd.DataFrame(rob,columns=['context','variant','control','ground_truth','estimate','absolute_error','brier','log_loss','path_precision','path_recall','path_f1']);rob.to_csv(processed/'robustness_scored.csv',index=False)
    rob.groupby('variant').agg(mean_effect_mae=('absolute_error','mean'),mean_brier=('brier','mean'),mean_log_loss=('log_loss','mean'),mean_path_recall=('path_recall','mean'),mean_path_f1=('path_f1','mean')).reset_index().to_csv(processed/'robustness_summary.csv',index=False)
    # Missingness curve incl complete values
    full_mae=float(full.absolute_error.mean());fullrisk=risk[risk.model=='DCHAG_full'];full_brier=float(fullrisk.brier.mean());full_ll=float(fullrisk.log_loss.mean());fullpath=path[path.model=='DCHAG_full'];full_rec=float(fullpath.recall.mean());full_f1=float(fullpath.f1.mean())
    curves=[]
    for rate,v in [(0.0,'complete'),(.1,'missing_10'),(.3,'missing_30'),(.5,'missing_50')]:
        if rate==0:vals=(full_mae,full_brier,full_ll,full_rec,full_f1)
        else:
            x=rob[rob.variant==v];vals=(x.absolute_error.mean(),x.brier.mean(),x.log_loss.mean(),x.path_recall.mean(),x.path_f1.mean())
        curves.append([rate,v,*map(float,vals)])
    curve=pd.DataFrame(curves,columns=['missing_fraction','variant','effect_mae','brier','log_loss','path_recall','path_f1']);curve.to_csv(processed/'missingness_curve.csv',index=False)
    auc=[]
    x=curve.missing_fraction.to_numpy()
    for col in ['effect_mae','brier','log_loss','path_recall','path_f1']:
        auc.append([col,float(np.trapezoid(curve[col],x)/(x[-1]-x[0]))])
    pd.DataFrame(auc,columns=['metric','normalized_auc_over_0_to_0.5']).to_csv(processed/'missingness_auc.csv',index=False)
    # Mark scored
    (stats/'scoring_manifest.json').write_text(json.dumps({'date':'2026-08-17','contexts':CONTEXTS,'bootstrap_replicates':B,'ground_truth_read_after_prediction_freeze':True},indent=2),encoding='utf-8')
    print('scoring complete')

if __name__=='__main__': main()
