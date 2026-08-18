from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import json, math
import numpy as np
from .config import ModelConfig
from .errors import InterventionError


def sigmoid(x: float) -> float:
    if x>=0:
        z=math.exp(-x); return 1.0/(1.0+z)
    z=math.exp(x); return z/(1.0+z)

@dataclass
class Trajectory:
    model_name: str
    horizon: int
    states: list[dict[str,int]]
    probabilities: list[dict[str,float]]
    exogenous: list[dict[str,float]]
    interventions: dict[str,int]

    def target_value(self,target:str, time:int|None=None)->int:
        t=self.horizon-1 if time is None else time
        return int(self.states[t][target])

    def to_dict(self):
        return {"model_name":self.model_name,"horizon":self.horizon,"states":self.states,
                "probabilities":self.probabilities,"exogenous":self.exogenous,"interventions":self.interventions}

    def to_json(self)->str:
        return json.dumps(self.to_dict(),sort_keys=True,separators=(",",":"))

    @classmethod
    def from_json(cls,s:str):
        d=json.loads(s); return cls(**d)

@dataclass
class PairedEffect:
    baseline_risk: float
    intervention_risk: float
    risk_reduction: float
    standard_error: float
    paired_differences: np.ndarray

class DCHAGEngine:
    """Reference evaluator. Contexts differ in configuration, not evaluator semantics."""
    def __init__(self,cfg:ModelConfig):
        self.cfg=cfg
        self.node_map=cfg.node_map

    def _validate_interventions(self, interventions:Mapping[str,int]|None)->dict[str,int]:
        out=dict(interventions or {})
        for c,v in out.items():
            if c not in self.node_map or self.node_map[c].type!="control":
                raise InterventionError(f"unknown control intervention: {c}")
            if int(v) not in (0,1):
                raise InterventionError("intervention values must be binary")
            out[c]=int(v)
        return out

    def draw_exogenous(self, seed:int)->list[dict[str,float]]:
        rng=np.random.default_rng(seed)
        return [{n.id:float(rng.random()) for n in self.cfg.nodes} for _ in range(self.cfg.horizon)]

    def evaluate(self, *, seed:int|None=None, exogenous:list[dict[str,float]]|None=None,
                 interventions:Mapping[str,int]|None=None)->Trajectory:
        ints=self._validate_interventions(interventions)
        if exogenous is None:
            if seed is None: raise ValueError("seed or exogenous realization required")
            exogenous=self.draw_exogenous(seed)
        if len(exogenous)!=self.cfg.horizon:
            raise ValueError("exogenous horizon mismatch")
        states=[]; probs=[]
        for t in range(self.cfg.horizon):
            st={}; pr={}
            for node in self.cfg.nodes:
                if node.type=="control" and node.id in ints:
                    val=ints[node.id]; p=float(val)
                else:
                    eta=node.intercept
                    for parent in node.parents:
                        pt=t-parent.lag
                        pv=0 if pt<0 else (st[parent.node] if parent.lag==0 else states[pt][parent.node])
                        eta += parent.coef*pv
                    if node.equation=="logistic_bernoulli":
                        p=sigmoid(eta)
                        u=float(exogenous[t][node.id])
                        if not 0<=u<=1: raise ValueError("exogenous values must lie in [0,1]")
                        val=int(u<p)
                    else:
                        p=float(eta>=node.threshold); val=int(p)
                st[node.id]=int(val); pr[node.id]=float(p)
            states.append(st); probs.append(pr)
        return Trajectory(self.cfg.name,self.cfg.horizon,states,probs,[dict(x) for x in exogenous],ints)

    def paired_effect(self, control:str, value:int=1, *, n:int=10000, seed:int=0)->PairedEffect:
        if control not in self.cfg.controls: raise InterventionError(f"unknown control: {control}")
        baseline=int(self.cfg.baseline_controls.get(control,0))
        rng=np.random.default_rng(seed)
        diffs=np.empty(n,dtype=float)
        base_y=np.empty(n,dtype=float); int_y=np.empty(n,dtype=float)
        for i in range(n):
            exo=[{node.id:float(rng.random()) for node in self.cfg.nodes} for _ in range(self.cfg.horizon)]
            b=self.evaluate(exogenous=exo, interventions={control:baseline}).target_value(self.cfg.target)
            q=self.evaluate(exogenous=exo, interventions={control:int(value)}).target_value(self.cfg.target)
            base_y[i]=b; int_y[i]=q; diffs[i]=b-q
        se=float(diffs.std(ddof=1)/math.sqrt(n)) if n>1 else 0.0
        return PairedEffect(float(base_y.mean()),float(int_y.mean()),float(diffs.mean()),se,diffs)

    def active_attack_subgraph(self,traj:Trajectory,time:int|None=None)->dict[str,list[str]]:
        """Active positive-contribution H/P/T parent edges into active ancestors of target."""
        t=self.cfg.horizon-1 if time is None else time
        target=self.cfg.target
        result={}
        seen=set()
        def visit(node_id:str,tt:int):
            key=(node_id,tt)
            if key in seen or tt<0: return
            seen.add(key)
            if traj.states[tt][node_id]!=1: return
            node=self.node_map[node_id]
            label=f"{node_id}@{tt}"
            parents=[]
            for p in node.parents:
                pt=tt-p.lag
                if p.coef<=0 or pt<0: continue
                if self.node_map[p.node].type not in {"human","process","technical"}: continue
                if traj.states[pt][p.node]==1:
                    pl=f"{p.node}@{pt}"; parents.append(pl); visit(p.node,pt)
            result[label]=sorted(parents)
        visit(target,t)
        return result
