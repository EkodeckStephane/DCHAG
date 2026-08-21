from __future__ import annotations
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd
from common import sigmoid, world_seed, default_worlds, make_world, hidden_common_value

ROOT=Path(__file__).resolve().parents[1]

def hash_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def generate_world(world_id:str, *, output_root:Path, private_root:Path, n_train:int, n_test:int):
    world=make_world(world_id)
    horizon=world['horizon']; nodes=world['nodes']; controls=world['controls']; baseline_controls=world['baseline_controls']; hidden=world.get('hidden_confounder')
    order={n:i for i,n in enumerate(nodes)}
    def one_split(n:int,seed:int):
        rng=np.random.default_rng(seed); rows=[]
        for tr in range(n):
            st={}
            for t in range(horizon):
                hidden_value=hidden_common_value(hidden,rng) if hidden else None
                row={'trajectory_id':tr,'time':t}
                for node in nodes:
                    nid=node['id'];typ=node['type']
                    if typ=='control':
                        if t==0: val=int(rng.random()<node.get('base_p',0.5))
                        else:
                            prev=st[(t-1,nid)]; stay=node.get('persistence',0.8)
                            val=prev if rng.random()<stay else int(rng.random()<node.get('base_p',0.5))
                    elif typ=='context':
                        if t==0: val=int(rng.random()<node.get('base_p',0.5))
                        else:
                            prev=st[(t-1,nid)]; stay=node.get('persistence',0.8)
                            val=prev if rng.random()<stay else int(rng.random()<node.get('base_p',0.5))
                    else:
                        eta=node.get('intercept',-1.0)
                        for p in node.get('parents',[]):
                            pt=t-int(p.get('lag',0)); pv=0 if pt<0 else st[(pt,p['node'])]
                            eta+=float(p['coef'])*pv
                        for inter in node.get('interactions',[]):
                            p1,p2=inter['parents']; lag1=int(p1.get('lag',0));lag2=int(p2.get('lag',0));
                            pt1=t-lag1;pt2=t-lag2
                            v1=0 if pt1<0 else st[(pt1,p1['node'])];v2=0 if pt2<0 else st[(pt2,p2['node'])]
                            eta+=float(inter['coef'])*v1*v2
                        if hidden and nid in hidden.get('children',{}): eta += float(hidden['children'][nid])*hidden_value
                        link=node.get('link','logit')
                        if link=='logit': p=sigmoid(eta)
                        elif link=='probit':
                            from math import erf,sqrt
                            p=0.5*(1+erf(eta/sqrt(2)))
                        elif link=='cloglog': p=1-np.exp(-np.exp(np.clip(eta,-8,8)))
                        elif link=='soft_threshold': p=0.05+0.9*sigmoid(2.5*eta)
                        else: raise ValueError(link)
                        val=int(rng.random()<p)
                    st[(t,nid)]=val;row[nid]=val
                rows.append(row)
        return pd.DataFrame(rows)
    out=output_root/world_id;out.mkdir(parents=True,exist_ok=True)
    train=one_split(n_train,world_seed(world_id,'train'));test=one_split(n_test,world_seed(world_id,'test'))
    train.to_csv(out/'train.csv',index=False);test.to_csv(out/'test.csv',index=False)
    schema={'world_id':world_id,'horizon':horizon,'node_types':{n['id']:n['type'] for n in nodes},'node_order':[n['id'] for n in nodes],
            'controls':controls,'baseline_controls':baseline_controls,'target':world['target']}
    (out/'schema.json').write_text(json.dumps(schema,indent=2,sort_keys=True))
    manifest={'world_id':world_id,'train_rows':len(train),'test_rows':len(test),'train_trajectories':n_train,'test_trajectories':n_test,
              'train_sha256':hash_file(out/'train.csv'),'test_sha256':hash_file(out/'test.csv'),'schema_sha256':hash_file(out/'schema.json')}
    (out/'data_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True))
    priv=private_root/world_id;priv.mkdir(parents=True,exist_ok=True)
    (priv/'world.json').write_text(json.dumps(world,indent=2,sort_keys=True))
    edges=[]
    for n in nodes:
        for p in n.get('parents',[]):edges.append({'parent':p['node'],'child':n['id'],'lag':int(p.get('lag',0)),'coef':float(p['coef'])})
    (priv/'true_edges.json').write_text(json.dumps(edges,indent=2,sort_keys=True))
    return manifest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-root',default=str(ROOT/'benchmarks/validation_v2/public'));ap.add_argument('--private-root',default=str(ROOT/'benchmarks/validation_v2/private_worlds'))
    ap.add_argument('--n-train',type=int,default=2500);ap.add_argument('--n-test',type=int,default=1500);ap.add_argument('--world',action='append')
    a=ap.parse_args();worlds=a.world or default_worlds()
    manifests=[]
    for w in worlds:
        m=generate_world(w,output_root=Path(a.output_root),private_root=Path(a.private_root),n_train=a.n_train,n_test=a.n_test);manifests.append(m);print(w,m)
    Path(a.output_root).mkdir(parents=True,exist_ok=True);(Path(a.output_root)/'validation_manifest.json').write_text(json.dumps(manifests,indent=2,sort_keys=True))
if __name__=='__main__':main()
