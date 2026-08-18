from __future__ import annotations
from pathlib import Path
import csv,json,hashlib
import numpy as np
from dchag import load_config, config_sha256
from simulator.world import WorldSimulator

ROOT=Path(__file__).resolve().parents[1]

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save_long_observed(path:Path,batch,cfg,trajectory_offset=0):
    fields=['trajectory_id','time']+list(batch.node_ids)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(fields)
        for i in range(batch.states.shape[0]):
            for t in range(cfg.horizon):
                w.writerow([trajectory_offset+i,t]+[int(x) for x in batch.states[i,t,:]])

def save_event_log(path:Path,batch,cfg,max_trajectories=2000):
    attack_types={'human','process','technical'}
    with path.open('w',encoding='utf-8') as f:
        for i in range(min(max_trajectories,batch.states.shape[0])):
            for t in range(cfg.horizon):
                for j,node in enumerate(cfg.nodes):
                    if node.type in attack_types and batch.states[i,t,j]==1:
                        rec={'trajectory_id':i,'timestamp':t,'actor':node.type,'action':node.id,
                             'resource':cfg.metadata.get('domain',cfg.name),'attributes':{'value':1}}
                        f.write(json.dumps(rec,sort_keys=True)+'\n')

def main():
    bench_root=ROOT/'benchmarks'; bench_root.mkdir(exist_ok=True)
    summary=[]
    for k,p in enumerate(sorted((ROOT/'simulator'/'world_configs').glob('*.yaml'))):
        cfg=load_config(p); sim=WorldSimulator(cfg)
        out=bench_root/cfg.name; (out/'ground_truth').mkdir(parents=True,exist_ok=True)
        train_seed=10100+k; test_seed=20200+k; gt_seed=30300+k
        train=sim.simulate(n=12000,seed=train_seed)
        test=sim.simulate(n=3000,seed=test_seed)
        save_long_observed(out/'train_observed.csv',train,cfg)
        save_long_observed(out/'test_observed.csv',test,cfg)
        save_event_log(out/'event_log.jsonl',test,cfg,max_trajectories=2000)
        # complete simulator truth kept in a separate guarded subdirectory
        np.savez_compressed(out/'ground_truth/test_full.npz',states=test.states,probabilities=test.probabilities,
                            exogenous=test.exogenous,node_ids=np.array(test.node_ids,dtype=object))
        effects=[]
        for c in cfg.controls:
            effects.append(sim.intervention_ground_truth(c,n=60000,seed=gt_seed))
        (out/'ground_truth/intervention_effects.json').write_text(json.dumps(effects,indent=2,sort_keys=True),encoding='utf-8')
        manifest={
            'benchmark_version':'1.0','context':cfg.name,'config_file':str(p.relative_to(ROOT)),
            'config_sha256':config_sha256(p),'train_trajectories':12000,'test_trajectories':3000,
            'horizon':cfg.horizon,'train_seed':train_seed,'test_seed':test_seed,'ground_truth_seed':gt_seed,
            'ground_truth_pairs_per_control':60000,
            'estimator_allowed_files':['train_observed.csv','test_observed.csv','event_log.jsonl','manifest.json'],
            'estimator_forbidden_files':['ground_truth/test_full.npz','ground_truth/intervention_effects.json'],
            'controls':list(cfg.controls),'target':cfg.target,
        }
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding='utf-8')
        manifest['files']={q.name:sha(q) for q in [out/'train_observed.csv',out/'test_observed.csv',out/'event_log.jsonl']}
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding='utf-8')
        for e in effects: summary.append([cfg.name,e['control'],e['baseline_risk'],e['intervention_risk'],e['risk_reduction'],e['paired_se']])
    with (bench_root/'ground_truth_summary.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['context','control','baseline_risk','intervention_risk','risk_reduction','paired_se']);w.writerows(summary)

if __name__=='__main__': main()
