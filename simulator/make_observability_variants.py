from pathlib import Path
import csv,json
import numpy as np
from dchag import load_config

ROOT=Path(__file__).resolve().parents[1]
for k,p in enumerate(sorted((ROOT/'configs').glob('*.yaml'))):
    cfg=load_config(p); b=ROOT/'benchmarks'/cfg.name; vd=b/'variants';vd.mkdir(exist_ok=True)
    meta={}
    attack=[n.id for n in cfg.nodes if n.type in {'human','process','technical'} and n.id!=cfg.target]
    human_process=[n.id for n in cfg.nodes if n.type in {'human','process'}]
    for split in ['train','test']:
        rows=list(csv.DictReader((b/f'{split}_observed.csv').open(encoding='utf-8'))); fields=list(rows[0].keys())
        for rate in [0.10,0.30,0.50]:
            rng=np.random.default_rng(40400+k*1000+(0 if split=='train' else 500)+int(rate*100))
            out=[];masked=0;eligible=0
            for r in rows:
                q=dict(r)
                for c in attack:
                    eligible+=1
                    if rng.random()<rate: q[c]='';masked+=1
                out.append(q)
            name=f'{split}_missing_{int(rate*100):02d}'
            path=vd/f'{name}.csv'
            with path.open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
            meta[name]={'file':path.name,'masked_cells':masked,'eligible_cells':eligible,'fraction':masked/eligible}
        out=[];masked=0;eligible=0
        for r in rows:
            q=dict(r)
            for c in human_process: eligible+=1;q[c]='';masked+=1
            out.append(q)
        name=f'{split}_human_process_unobserved';path=vd/f'{name}.csv'
        with path.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
        meta[name]={'file':path.name,'masked_cells':masked,'eligible_cells':eligible,'fraction':1.0}
    (vd/'manifest.json').write_text(json.dumps(meta,indent=2,sort_keys=True),encoding='utf-8')
