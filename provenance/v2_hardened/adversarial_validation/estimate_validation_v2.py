from __future__ import annotations
from pathlib import Path
import argparse, itertools, json, math, time
import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss
from adversarial_validation.common import read_json, write_json, sha256

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/"benchmarks"/"validation_v2"/"public"
RESULTS=ROOT/"results"/"validation_v2"

class ConstantModel:
    def __init__(self,p): self.p=float(np.clip(p,.001,.999))
    def predict(self,X): return np.full(len(X),self.p,float)

class SparseLocalModel:
    def __init__(self, feature_names, selected, model=None, constant=None):
        self.feature_names=list(feature_names); self.selected=list(selected); self.model=model; self.constant=constant
        self.pairs=list(itertools.combinations(range(len(self.selected)),2))
    def _z(self,X):
        if not self.selected: return np.zeros((len(X),0))
        q=X[:,self.selected]
        if self.pairs:
            inter=np.column_stack([q[:,a]*q[:,b] for a,b in self.pairs])
            q=np.column_stack([q,inter])
        return q
    def predict(self,X):
        if self.constant is not None:return np.full(len(X),self.constant,float)
        z=self._z(X); return self.model.predict_proba(z)[:,1]

class DenseLocalModel:
    def __init__(self,model=None,constant=None): self.model=model;self.constant=constant
    def predict(self,X):
        if self.constant is not None:return np.full(len(X),self.constant,float)
        return self.model.predict_proba(X)[:,1]


def candidate_features(df,schema,node):
    order=schema["order"]; pos=order.index(node); grouped=df.groupby("trajectory_id",sort=False)
    names=[]; cols=[]
    # same-slice predecessors preserve temporal/event order but do not reveal true edges
    for p in order[:pos]:
        names.append(f"{p}@0"); cols.append(pd.to_numeric(df[p],errors="coerce").to_numpy(float))
    # full lag-1 observed history is admissible for every node
    for p in order:
        names.append(f"{p}@-1")
        s=grouped[p].shift(1).where(df["time"]>=1,0.0)
        cols.append(pd.to_numeric(s,errors="coerce").to_numpy(float))
    X=np.column_stack(cols) if cols else np.zeros((len(df),0))
    y=pd.to_numeric(df[node],errors="coerce").to_numpy(float)
    mask=np.isfinite(y)&np.all(np.isfinite(X),axis=1)
    return names,X[mask],y[mask].astype(int)


def fit_sparse(train,schema,max_parents):
    models={}; selected_edges=[]
    for ni,node in enumerate(schema["order"]):
        names,X,y=candidate_features(train,schema,node)
        if len(y)==0 or len(np.unique(y))<2:
            p=(float(np.mean(y)) if len(y) else .5);models[node]=SparseLocalModel(names,[],constant=float(np.clip(p,.001,.999)));continue
        if X.shape[1]==0:
            models[node]=SparseLocalModel(names,[],constant=float(np.clip(np.mean(y),.001,.999)));continue
        # Development-v2.1 structure selector: an L1-penalized local temporal model
        # ranks conditionally informative parents from the complete admissible set.
        # It receives no ground-truth edges or coefficients.
        screen=LogisticRegression(penalty="l1",C=.05,solver="liblinear",max_iter=500,fit_intercept=True)
        screen.fit(X,y)
        score=np.abs(screen.coef_[0])
        ranked=np.argsort(-score)
        selected=[int(i) for i in ranked if score[i]>1e-6][:max_parents]
        if not selected:
            mi=mutual_info_classif(X,y,discrete_features=True,random_state=83000+ni)
            ranked=np.argsort(-mi); selected=[int(ranked[0])]
        temp=SparseLocalModel(names,selected)
        Z=temp._z(X)
        lr=LogisticRegression(C=.7,solver="lbfgs",max_iter=500,fit_intercept=True)
        lr.fit(Z,y); temp.model=lr;models[node]=temp
        for i in selected:
            raw=names[i]; p,lag=raw.rsplit("@",1); selected_edges.append([p,0 if lag=="0" else 1,node])
    return models,selected_edges


def fit_dense(train,schema):
    models={}
    for ni,node in enumerate(schema["order"]):
        names,X,y=candidate_features(train,schema,node)
        if len(y)==0 or len(np.unique(y))<2 or X.shape[1]==0:
            p=(float(np.mean(y)) if len(y) else .5);models[node]=DenseLocalModel(constant=float(np.clip(p,.001,.999)));continue
        m=HistGradientBoostingClassifier(loss="log_loss",learning_rate=.07,max_iter=80,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=1.0,random_state=84000+ni)
        m.fit(X,y);models[node]=DenseLocalModel(model=m)
    return models


def _feature_matrix_from_state(schema,node,states,t):
    order=schema["order"];idx={x:i for i,x in enumerate(order)};pos=order.index(node); n=states.shape[0]
    cols=[]
    for p in order[:pos]: cols.append(states[:,t,idx[p]].astype(float))
    for p in order:
        cols.append(np.zeros(n,float) if t==0 else states[:,t-1,idx[p]].astype(float))
    return np.column_stack(cols) if cols else np.zeros((n,0))


def simulate_model(models,schema,n,seed,interventions=None,fixed_sequences=None,uniforms=None):
    order=schema["order"];idx={x:i for i,x in enumerate(order)};h=schema["horizon"];controls=set(schema["controls"]);interventions=interventions or {};fixed_sequences=fixed_sequences or {}
    states=np.zeros((n,h,len(order)),dtype=np.int8)
    if uniforms is None:
        rng=np.random.default_rng(seed); uniforms=rng.random((n,h,len(order)))
    else:
        uniforms=np.asarray(uniforms,float)
        if uniforms.shape!=(n,h,len(order)): raise ValueError("uniform shape mismatch")
    for t in range(h):
        for j,node in enumerate(order):
            if node in fixed_sequences:
                states[:,t,j]=fixed_sequences[node][:,t];continue
            if node in controls and node in interventions:
                states[:,t,j]=int(interventions[node]);continue
            X=_feature_matrix_from_state(schema,node,states,t);p=models[node].predict(X)
            states[:,t,j]=(uniforms[:,t,j]<p).astype(np.int8)
    return states


def effect_estimates(models,schema,seed,n=8000):
    # Evaluate baseline + four sustained interventions in one vectorized simulation.
    # The same node/time uniforms are repeated across regimes, preserving common random numbers.
    controls=list(schema["controls"]); regimes=[None]+controls; k=len(regimes);h=schema["horizon"];order=schema["order"]
    rng=np.random.default_rng(seed); u0=rng.random((n,h,len(order))); uniforms=np.concatenate([u0 for _ in regimes],axis=0)
    fixed={}
    for c in controls:
        blocks=[]
        for selected in regimes:
            val=1 if selected==c else int(schema["baseline_controls"][c])
            blocks.append(np.full((n,h),val,dtype=np.int8))
        fixed[c]=np.concatenate(blocks,axis=0)
    st=simulate_model(models,schema,n*k,seed,fixed_sequences=fixed,uniforms=uniforms)
    yidx=order.index(schema["target"]); y=st[:,-1,yidx].reshape(k,n);y0=y[0].astype(float)
    rows=[]
    for ri,c in enumerate(controls,1):
        y1=y[ri].astype(float);d=y0-y1
        rows.append({"control":c,"baseline_risk":float(y0.mean()),"intervention_risk":float(y1.mean()),"risk_reduction":float(d.mean()),"mc_se":float(d.std(ddof=1)/math.sqrt(n))})
    return rows

def prospective_risk(models,schema,test,seed,mc=35):
    ids=np.sort(test.trajectory_id.unique()); indexed=test.set_index(["trajectory_id","time"]);h=schema["horizon"]
    fixed={}
    for node in [x for x in schema["order"] if schema["types"][x] in {"context","control"}]:
        arr=np.array([[int(indexed.loc[(tid,t),node]) for t in range(h)] for tid in ids],dtype=np.int8)
        fixed[node]=np.repeat(arr,mc,axis=0)
    st=simulate_model(models,schema,len(ids)*mc,seed,fixed_sequences=fixed);yidx=schema["order"].index(schema["target"])
    return ids,st[:,-1,yidx].reshape(len(ids),mc).mean(axis=1)


def observational_effects(train,schema):
    h=schema["horizon"];q=train[train.time==h-1].copy();features=[x for x in schema["order"] if schema["types"][x] in {"context","control"}]
    X=q[features].to_numpy(float);y=q[schema["target"]].to_numpy(int)
    lr=LogisticRegression(C=1.0,solver="lbfgs",max_iter=500).fit(X,y)
    rows=[]
    base=np.zeros((len(q),len(features)),float)
    for j,f in enumerate(features):
        if schema["types"][f]=="context": base[:,j]=q[f].to_numpy(float)
        else: base[:,j]=schema["baseline_controls"][f]
    p0=lr.predict_proba(base)[:,1]
    for c in schema["controls"]:
        z=base.copy();z[:,features.index(c)]=1;p1=lr.predict_proba(z)[:,1]
        rows.append({"control":c,"baseline_risk":float(p0.mean()),"intervention_risk":float(p1.mean()),"risk_reduction":float((p0-p1).mean()),"mc_se":None})
    return rows


def run_tag(tag,max_parents,outdir):
    pub=PUBLIC/tag;schema=read_json(pub/"schema.json");train=pd.read_csv(pub/"train.csv");test=pd.read_csv(pub/"test.csv");outdir.mkdir(parents=True,exist_ok=True)
    t0=time.time(); sparse,edges=fit_sparse(train,schema,max_parents);sparse_fit=time.time()-t0
    t0=time.time();dense=fit_dense(train,schema);dense_fit=time.time()-t0
    rows=[]
    for model_name,model,seed in [("DCHAG_Learned",sparse,91001),("Dense_Sequential_GFormula",dense,92001)]:
        for r in effect_estimates(model,schema,seed,n=8000): rows.append({"world":tag,"model":model_name,**r})
    for r in observational_effects(train,schema):rows.append({"world":tag,"model":"Observational_Association",**r})
    pd.DataFrame(rows).to_csv(outdir/"effect_estimates.csv",index=False)
    ids,p1=prospective_risk(sparse,schema,test,93001);_,p2=prospective_risk(dense,schema,test,94001)
    end=test[test.time==schema["horizon"]-1].sort_values("trajectory_id");y=end[schema["target"]].to_numpy(int)
    pred=pd.DataFrame({"trajectory_id":ids,"y_true":y,"DCHAG_Learned":p1,"Dense_Sequential_GFormula":p2})
    pred.to_csv(outdir/"trajectory_predictions.csv",index=False)
    write_json(outdir/"learned_edges.json",sorted({tuple(e) for e in edges}))
    write_json(outdir/"run_metadata.json",{"world":tag,"max_parents":max_parents,"sparse_fit_seconds":sparse_fit,"dense_fit_seconds":dense_fit,"estimator_private_world_access":False})
    files=["effect_estimates.csv","trajectory_predictions.csv","learned_edges.json","run_metadata.json"]
    write_json(outdir/"freeze_manifest.json",{"status":"predictions_frozen_before_oracle_scoring","files":{f:sha256(outdir/f) for f in files},"public_inputs":{"schema":sha256(pub/"schema.json"),"train":sha256(pub/"train.csv"),"test":sha256(pub/"test.csv")}})
    print(tag,"frozen",outdir)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--set",choices=["development","confirmatory","latent"],required=True);ap.add_argument("--max-parents",type=int,default=None);ap.add_argument("--tag",default=None);a=ap.parse_args()
    if a.max_parents is None:
        hp=read_json(ROOT/"experiments"/"validation_v2"/"FROZEN_HYPERPARAMETERS.json");maxp=int(hp["max_parents"])
    else:maxp=a.max_parents
    if a.set=="development":tags=sorted(p.name for p in PUBLIC.glob("dev_*"));base=RESULTS/"development"/f"cap{maxp}"
    elif a.set=="confirmatory":tags=sorted(p.name for p in PUBLIC.glob("confirm_*"));base=RESULTS/"confirmatory"/"frozen_predictions"
    else:tags=sorted(p.name for p in PUBLIC.glob("latent_*"));base=RESULTS/"latent"/"frozen_predictions"
    if a.tag is not None:
        if a.tag not in tags: raise ValueError(f"tag not in set: {a.tag}")
        tags=[a.tag]
    for tag in tags: run_tag(tag,maxp,base/tag)

if __name__=="__main__":main()
