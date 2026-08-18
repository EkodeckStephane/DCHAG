from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from dchag.config import ModelConfig

class ObservationalOutcomeBaseline:
    """Strong observational comparator using full context and control histories."""
    def __init__(self,cfg:ModelConfig): self.cfg=cfg; self.model=None; self.feature_names=[]; self.context_cols=[]; self.context_rows=None
    def _trajectory_frame(self,df:pd.DataFrame):
        parts=[]
        ctx=df.pivot(index='trajectory_id',columns='time',values='high_risk_context'); ctx.columns=[f'high_risk_context@{int(t)}' for t in ctx.columns];parts.append(ctx)
        for c in self.cfg.controls:
            piv=df.pivot(index='trajectory_id',columns='time',values=c); piv.columns=[f'{c}@{int(t)}' for t in piv.columns];parts.append(piv)
        x=pd.concat(parts,axis=1).reset_index()
        y=df[df.time==self.cfg.horizon-1][['trajectory_id',self.cfg.target]].set_index('trajectory_id')
        x['y']=x.trajectory_id.map(y[self.cfg.target]).astype(int)
        return x
    def fit(self,df:pd.DataFrame):
        x=self._trajectory_frame(df); self.feature_names=[c for c in x.columns if c not in {'trajectory_id','y'}]
        self.context_cols=[c for c in self.feature_names if c.startswith('high_risk_context@')]
        self.context_rows=x[self.context_cols].copy().reset_index(drop=True)
        self.model=LogisticRegression(C=1e6,solver='liblinear',max_iter=300).fit(x[self.feature_names],x.y)
        return self
    def predict_proba(self,df:pd.DataFrame):
        x=self._trajectory_frame(df); return self.model.predict_proba(x[self.feature_names])[:,1]
    def association_effect(self,control:str):
        n=len(self.context_rows); base=self.context_rows.copy(); treat=self.context_rows.copy()
        for c in self.cfg.controls:
            for t in range(self.cfg.horizon):
                col=f'{c}@{t}'; base[col]=self.cfg.baseline_controls[c]; treat[col]=1 if c==control else self.cfg.baseline_controls[c]
        base=base[self.feature_names]; treat=treat[self.feature_names]
        pb=self.model.predict_proba(base)[:,1]; pt=self.model.predict_proba(treat)[:,1]
        return {'baseline_risk':float(pb.mean()),'intervention_risk':float(pt.mean()),'risk_reduction':float((pb-pt).mean())}
