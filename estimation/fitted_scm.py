from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import math
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from dchag.config import ModelConfig

@dataclass(frozen=True)
class FittedNode:
    id: str
    type: str
    intercept: float
    parents: tuple[tuple[str,int,float], ...]  # node, lag, fitted coef

@dataclass
class FittedSCM:
    name: str
    horizon: int
    nodes: tuple[FittedNode,...]
    target: str
    baseline_controls: dict[str,int]
    source_config_name: str

    @property
    def node_map(self): return {n.id:n for n in self.nodes}
    @property
    def controls(self): return tuple(n.id for n in self.nodes if n.type=='control')

    @staticmethod
    def _sigmoid(x): return 1/(1+np.exp(-np.clip(x,-35,35)))

    def simulate(self,n:int,seed:int,*,interventions:dict[str,int]|None=None,fixed_context:dict[str,int]|None=None,fixed_sequences:dict[str,np.ndarray]|None=None):
        ints=dict(interventions or {}); fixed=dict(fixed_context or {}); seq=dict(fixed_sequences or {})
        rng=np.random.default_rng(seed)
        idx={n.id:i for i,n in enumerate(self.nodes)}
        states=np.zeros((n,self.horizon,len(self.nodes)),dtype=np.int8)
        for t in range(self.horizon):
            for j,node in enumerate(self.nodes):
                if node.id in seq:
                    arr=np.asarray(seq[node.id]);
                    if arr.shape!=(n,self.horizon): raise ValueError(f'fixed sequence shape mismatch for {node.id}')
                    states[:,t,j]=arr[:,t].astype(np.int8); continue
                if node.id in fixed:
                    states[:,t,j]=int(fixed[node.id]); continue
                if node.type=='control' and node.id in ints:
                    states[:,t,j]=int(ints[node.id]); continue
                eta=np.full(n,node.intercept,dtype=float)
                for pid,lag,coef in node.parents:
                    pt=t-lag
                    pv=0 if pt<0 else states[:,t,idx[pid]] if lag==0 else states[:,pt,idx[pid]]
                    eta += coef*pv
                p=self._sigmoid(eta)
                states[:,t,j]=(rng.random(n)<p).astype(np.int8)
        return states

    def estimate_effect(self,control:str,n:int=50000,seed:int=0,fixed_context:dict[str,int]|None=None):
        base=dict(self.baseline_controls); treat=dict(base); treat[control]=1
        # common random numbers are achieved by replaying identical RNG seed
        b=self.simulate(n,seed,interventions=base,fixed_context=fixed_context)
        q=self.simulate(n,seed,interventions=treat,fixed_context=fixed_context)
        idx={n.id:i for i,n in enumerate(self.nodes)}; yj=idx[self.target]
        y0=b[:,-1,yj].astype(float); y1=q[:,-1,yj].astype(float); d=y0-y1
        return {'baseline_risk':float(y0.mean()),'intervention_risk':float(y1.mean()),'risk_reduction':float(d.mean()),
                'paired_se':float(d.std(ddof=1)/math.sqrt(n))}

    def predict_trajectory_risk(self,df:pd.DataFrame,*,mc:int=300,seed:int=0)->np.ndarray:
        """Prospective target risk conditional on observed context/control sequences, integrating H/P/T states."""
        tids=np.sort(df['trajectory_id'].unique()); ntraj=len(tids)
        fixed_nodes=[n.id for n in self.nodes if n.type in {'context','control'}]
        seq={}
        indexed=df.set_index(['trajectory_id','time'])
        for node in fixed_nodes:
            base=np.array([[float(indexed.loc[(tid,t),node]) for t in range(self.horizon)] for tid in tids],dtype=float)
            if not np.all(np.isfinite(base)):
                raise ValueError(f'missing fixed context/control sequence: {node}')
            seq[node]=np.repeat(base,mc,axis=0)
        st=self.simulate(ntraj*mc,seed,fixed_sequences=seq)
        idx={n.id:i for i,n in enumerate(self.nodes)}; y=st[:,-1,idx[self.target]].reshape(ntraj,mc)
        return y.mean(axis=1)

    def observed_target_probabilities(self,df:pd.DataFrame)->np.ndarray:
        node=self.node_map[self.target]
        use=df[df['time']==self.horizon-1].copy()
        eta=np.full(len(use),node.intercept,dtype=float)
        # lagged target parents need values from earlier trajectory rows
        all_df=df.set_index(['trajectory_id','time'])
        for pid,lag,coef in node.parents:
            if lag==0:
                vals=use[pid].fillna(0).to_numpy(float)
            else:
                vals=[]
                for tid in use['trajectory_id']:
                    key=(tid,self.horizon-1-lag)
                    vals.append(float(all_df.loc[key,pid]) if key in all_df.index and pd.notna(all_df.loc[key,pid]) else 0.0)
                vals=np.array(vals)
            eta += coef*vals
        return self._sigmoid(eta)


def _root_logit(y:np.ndarray)->float:
    p=(y.sum()+0.5)/(len(y)+1.0)
    return float(np.log(p/(1-p)))


def fit_scm(cfg:ModelConfig,train_csv:str|Path,*,drop_types:set[str]|None=None,drop_lags:bool=False,
            parent_filter=None)->FittedSCM:
    drop_types=set(drop_types or set())
    df=pd.read_csv(train_csv)
    kept=[n for n in cfg.nodes if n.type not in drop_types]
    kept_ids={n.id for n in kept}
    fitted=[]
    grouped=df.groupby('trajectory_id',sort=False)
    for node in kept:
        y_raw=pd.to_numeric(df[node.id],errors='coerce').to_numpy(float)
        ps=[]; Xcols=[]
        for p in node.parents:
            if p.node not in kept_ids: continue
            if drop_lags and p.lag>0: continue
            if parent_filter is not None and not parent_filter(node,p): continue
            if p.lag==0:
                col=pd.to_numeric(df[p.node],errors='coerce').to_numpy(float)
            else:
                shifted=grouped[p.node].shift(p.lag)
                # Values before the start of a trajectory are structural zeros; missing observed parents remain NaN.
                shifted=shifted.where(df['time']>=p.lag,0.0)
                col=pd.to_numeric(shifted,errors='coerce').to_numpy(float)
            Xcols.append(col); ps.append((p.node,p.lag))
        if Xcols:
            X=np.column_stack(Xcols)
            mask=np.isfinite(y_raw) & np.all(np.isfinite(X),axis=1)
            y=y_raw[mask].astype(int); X=X[mask]
        else:
            mask=np.isfinite(y_raw); y=y_raw[mask].astype(int); X=None
        if len(y)==0:
            intercept=0.0; coefs=[]
        elif not Xcols or len(np.unique(y))<2:
            intercept=_root_logit(y); coefs=[]
        else:
            model=LogisticRegression(C=1e6,solver='liblinear',max_iter=300,fit_intercept=True)
            model.fit(X,y)
            intercept=float(model.intercept_[0]); coefs=[float(x) for x in model.coef_[0]]
        parents=tuple((pid,lag,coef) for (pid,lag),coef in zip(ps,coefs))
        fitted.append(FittedNode(node.id,node.type,intercept,parents))
    if cfg.target not in {n.id for n in fitted}:
        raise ValueError('target removed by ablation')
    baselines={c:v for c,v in cfg.baseline_controls.items() if c in {n.id for n in fitted}}
    return FittedSCM(cfg.name,cfg.horizon,tuple(fitted),cfg.target,baselines,cfg.name)
