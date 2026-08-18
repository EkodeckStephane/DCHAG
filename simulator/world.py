from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from dchag.config import ModelConfig
from dchag.errors import InterventionError

@dataclass
class BatchTrajectory:
    states: np.ndarray  # n x horizon x nodes, int8
    probabilities: np.ndarray  # n x horizon x nodes, float
    exogenous: np.ndarray  # n x horizon x nodes, float
    node_ids: tuple[str,...]

    def node_index(self,node:str)->int:
        return self.node_ids.index(node)

class WorldSimulator:
    """Vectorized ground-truth simulator.

    It uses the frozen world configuration but exposes only generated observations to the estimator.
    The estimator is not given coefficients or exogenous draws.
    """
    def __init__(self,cfg:ModelConfig):
        self.cfg=cfg
        self.node_ids=tuple(n.id for n in cfg.nodes)
        self.index={n.id:i for i,n in enumerate(cfg.nodes)}

    @staticmethod
    def _sigmoid(x:np.ndarray)->np.ndarray:
        return 1.0/(1.0+np.exp(-np.clip(x,-35,35)))

    def draw_exogenous(self,n:int,seed:int)->np.ndarray:
        rng=np.random.default_rng(seed)
        return rng.random((n,self.cfg.horizon,len(self.cfg.nodes)),dtype=np.float64)

    def simulate(self,n:int|None=None,seed:int|None=None,*,exogenous:np.ndarray|None=None,interventions:dict[str,int]|None=None)->BatchTrajectory:
        ints=dict(interventions or {})
        for c,v in ints.items():
            if c not in self.cfg.controls: raise InterventionError(f'unknown control: {c}')
            if int(v) not in (0,1): raise InterventionError('control values must be binary')
        if exogenous is None:
            if n is None or seed is None: raise ValueError('n+seed or exogenous required')
            exogenous=self.draw_exogenous(n,seed)
        else:
            n=int(exogenous.shape[0])
        if exogenous.shape!=(n,self.cfg.horizon,len(self.cfg.nodes)):
            raise ValueError('exogenous shape mismatch')
        states=np.zeros_like(exogenous,dtype=np.int8)
        probs=np.zeros_like(exogenous,dtype=np.float64)
        for t in range(self.cfg.horizon):
            for j,node in enumerate(self.cfg.nodes):
                if node.type=='control' and node.id in ints:
                    p=np.full(n,float(ints[node.id])); val=p.astype(np.int8)
                else:
                    eta=np.full(n,node.intercept,dtype=np.float64)
                    for parent in node.parents:
                        pt=t-parent.lag
                        if pt<0:
                            pv=0.0
                        else:
                            pj=self.index[parent.node]
                            pv=states[:,t,pj] if parent.lag==0 else states[:,pt,pj]
                        eta += parent.coef*pv
                    if node.equation=='logistic_bernoulli':
                        p=self._sigmoid(eta); val=(exogenous[:,t,j] < p).astype(np.int8)
                    else:
                        p=(eta>=node.threshold).astype(float); val=p.astype(np.int8)
                states[:,t,j]=val; probs[:,t,j]=p
        return BatchTrajectory(states,probs,exogenous,self.node_ids)

    def intervention_ground_truth(self,control:str,*,n:int=100000,seed:int=0)->dict:
        exo=self.draw_exogenous(n,seed)
        base_int=dict(self.cfg.baseline_controls)
        treat_int=dict(base_int); treat_int[control]=1
        b=self.simulate(exogenous=exo,interventions=base_int)
        q=self.simulate(exogenous=exo,interventions=treat_int)
        yj=self.index[self.cfg.target]
        y0=b.states[:,-1,yj].astype(float); y1=q.states[:,-1,yj].astype(float)
        d=y0-y1
        out={
            'control':control,'n':n,'seed':seed,
            'baseline_risk':float(y0.mean()),'intervention_risk':float(y1.mean()),
            'risk_reduction':float(d.mean()),
            'paired_se':float(d.std(ddof=1)/math.sqrt(n)),
        }
        # pre-treatment context strata, valid because the root context is unaffected by intervention
        if 'high_risk_context' in self.index:
            cj=self.index['high_risk_context']; ctx=b.states[:,0,cj]
            out['strata']={}
            for s in (0,1):
                m=(ctx==s)
                ds=d[m]; b0=y0[m]; q1=y1[m]
                out['strata'][str(s)]={
                    'n':int(m.sum()),'baseline_risk':float(b0.mean()),'intervention_risk':float(q1.mean()),
                    'risk_reduction':float(ds.mean()),'paired_se':float(ds.std(ddof=1)/math.sqrt(max(1,m.sum()))) if m.sum()>1 else 0.0}
        return out
