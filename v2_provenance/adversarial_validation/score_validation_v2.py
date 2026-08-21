from __future__ import annotations
from pathlib import Path
import argparse, json, hashlib
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss
from adversarial_validation.common import read_json,write_json,sha256,rank_metrics,bootstrap_mean_ci,exact_signflip_p
from adversarial_validation.generate_validation_v2 import simulate

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"benchmarks"/"validation_v2";PUBLIC=BASE/"public";PRIVATE=BASE/"private_worlds";RESULTS=ROOT/"results"/"validation_v2"


def oracle_effects(tag,n=30000):
    w=read_json(PRIVATE/tag/"world.json");base=dict(w["baseline_controls"]);idx={x:i for i,x in enumerate(w["order"])};yj=idx[w["target"]];seed=151000+int(hashlib.sha256(tag.encode()).hexdigest()[:6],16)%100000
    b=simulate(w,n,seed,interventions=base);y0=b[:,-1,yj].astype(float);out={}
    for c in w["controls"]:
        q=dict(base);q[c]=1;s=simulate(w,n,seed,interventions=q);y1=s[:,-1,yj].astype(float);d=y0-y1
        out[c]={"true_baseline_risk":float(y0.mean()),"true_intervention_risk":float(y1.mean()),"true_effect":float(d.mean()),"oracle_se":float(d.std(ddof=1)/np.sqrt(n))}
    return out


def score_edges(tag, learned_path):
    true={tuple(x) for x in read_json(PRIVATE/tag/"true_edges.json")}; est={tuple(x) for x in read_json(learned_path)}
    tp=len(true&est);prec=tp/len(est) if est else 0.0;rec=tp/len(true) if true else 1.0;f1=2*prec*rec/(prec+rec) if prec+rec else 0.0
    return {"edge_precision":prec,"edge_recall":rec,"edge_f1":f1,"true_edges":len(true),"learned_edges":len(est)}


def score_tag(tag,outdir,oracle_n=30000):
    freeze=read_json(outdir/"freeze_manifest.json")
    for f,h in freeze["files"].items():
        if sha256(outdir/f)!=h: raise RuntimeError(f"freeze hash mismatch {tag} {f}")
    oracle=oracle_effects(tag,oracle_n)
    est=pd.read_csv(outdir/"effect_estimates.csv");rows=[]
    for _,r in est.iterrows():
        o=oracle[r.control];err=float(r.risk_reduction-o["true_effect"])
        rows.append({**r.to_dict(),**o,"signed_error":err,"abs_error":abs(err),"relative_abs_error":abs(err)/max(abs(o["true_effect"]),1e-6)})
    eff=pd.DataFrame(rows)
    schema=read_json(PUBLIC/tag/"schema.json")
    train=pd.read_csv(PUBLIC/tag/"train.csv");pred=pd.read_csv(outdir/"trajectory_predictions.csv")
    prevalence=float(train[train.time==schema["horizon"]-1][schema["target"]].mean());ref_brier=float(np.mean((pred.y_true-prevalence)**2))
    model_metrics=[]
    for m in ["DCHAG_Learned","Dense_Sequential_GFormula","Observational_Association"]:
        q=eff[eff.model==m];true={r.control:float(r.true_effect) for _,r in q.iterrows()};estimate={r.control:float(r.risk_reduction) for _,r in q.iterrows()}
        kt,sp,regret,best=rank_metrics(true,estimate)
        mm={"world":tag,"model":m,"effect_mae":float(q.abs_error.mean()),"signed_bias":float(q.signed_error.mean()),"relative_abs_error":float(q.abs_error.sum()/max(np.abs(q.true_effect).sum(),1e-6)),"kendall":kt,"spearman":sp,"normalized_regret":regret,"selected_control":best}
        if m in pred.columns:
            bs=float(brier_score_loss(pred.y_true,pred[m]));mm["brier"]=bs;mm["brier_reference"]=ref_brier;mm["bss"]=1-bs/ref_brier if ref_brier>0 else float("nan")
        model_metrics.append(mm)
    edge=score_edges(tag,outdir/"learned_edges.json")
    model_metrics[0].update(edge)
    return eff,pd.DataFrame(model_metrics)


def score_development():
    caps=[4,6];rows=[]
    tags=sorted(p.name for p in PUBLIC.glob("dev_*"))
    for cap in caps:
        for tag in tags:
            out=RESULTS/"development"/f"cap{cap}"/tag
            eff,_=score_tag(tag,out,oracle_n=20000)
            q=eff[eff.model=="DCHAG_Learned"]
            rows.append({"cap":cap,"world":tag,"mae":float(q.abs_error.mean())})
    df=pd.DataFrame(rows);df.to_csv(RESULTS/"development"/"development_scores.csv",index=False)
    means=df.groupby("cap").mae.mean();chosen=int(means.idxmin())
    hp={"max_parents":chosen,"selection_rule":"lower mean development-world intervention-effect MAE; tie -> smaller cap","candidates":caps,"development_mean_mae":{str(int(k)):float(v) for k,v in means.items()},"protocol_sha256":sha256(ROOT/"experiments"/"validation_v2"/"FROZEN_PROTOCOL_v2.md")}
    write_json(ROOT/"experiments"/"validation_v2"/"FROZEN_HYPERPARAMETERS.json",hp)
    print(df);print("chosen",chosen,hp)


def aggregate(set_name):
    base=RESULTS/set_name/"frozen_predictions"; tags=sorted(p.name for p in base.iterdir() if p.is_dir())
    all_eff=[];all_world=[]
    for tag in tags:
        e,w=score_tag(tag,base/tag,oracle_n=30000);all_eff.append(e);all_world.append(w)
    eff=pd.concat(all_eff,ignore_index=True);world=pd.concat(all_world,ignore_index=True)
    score_dir=RESULTS/set_name/"scored";score_dir.mkdir(parents=True,exist_ok=True);eff.to_csv(score_dir/"effect_accuracy.csv",index=False);world.to_csv(score_dir/"world_metrics.csv",index=False)
    summary=world.groupby("model",dropna=False).agg(n_worlds=("world","count"),effect_mae=("effect_mae","mean"),signed_bias=("signed_bias","mean"),relative_abs_error=("relative_abs_error","mean"),kendall=("kendall","mean"),spearman=("spearman","mean"),normalized_regret=("normalized_regret","mean"),bss=("bss","mean")).reset_index()
    summary.to_csv(score_dir/"model_summary.csv",index=False)
    if set_name=="confirmatory":
        piv=world.pivot(index="world",columns="model",values="effect_mae")
        d=(piv["DCHAG_Learned"]-piv["Dense_Sequential_GFormula"]).to_numpy(float);lo,hi=bootstrap_mean_ci(d);p=exact_signflip_p(d)
        comp={"n_independent_worlds":len(d),"mean_dchag_minus_dense_mae":float(d.mean()),"bootstrap95_low":lo,"bootstrap95_high":hi,"exact_signflip_p":p}
        write_json(score_dir/"paired_world_inference.json",comp)
        print(summary.to_string(index=False));print(comp)
    else:
        print(summary.to_string(index=False))
    return world


def latent_sensitivity():
    latent=aggregate("latent")
    confirm=pd.read_csv(RESULTS/"confirmatory"/"scored"/"world_metrics.csv")
    rows=[]
    for _,r in latent[latent.model.isin(["DCHAG_Learned","Dense_Sequential_GFormula"])].iterrows():
        fam=r.world.split("_")[1];match=f"confirm_{fam}_1";q=confirm[(confirm.world==match)&(confirm.model==r.model)].iloc[0]
        rows.append({"family":fam,"model":r.model,"observed_world":match,"latent_world":r.world,"observed_mae":q.effect_mae,"latent_mae":r.effect_mae,"mae_increase":r.effect_mae-q.effect_mae})
    df=pd.DataFrame(rows);df.to_csv(RESULTS/"latent"/"scored"/"matched_latent_sensitivity.csv",index=False);print(df.to_string(index=False))


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--stage",choices=["development","confirmatory","latent"],required=True);a=ap.parse_args()
    if a.stage=="development":score_development()
    elif a.stage=="confirmatory":aggregate("confirmatory")
    else:latent_sensitivity()
if __name__=="__main__":main()
