from __future__ import annotations
from pathlib import Path
import csv, re
try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required for ontology validation") from exc

ROOT = Path(__file__).resolve().parents[1]

def validate() -> list[str]:
    errors=[]
    ont=yaml.safe_load((ROOT/'spec/ontology.yaml').read_text(encoding='utf-8'))
    if set(ont['attack_state_types']) != {'human','process','technical'}:
        errors.append('attack_state_types must be exactly human/process/technical')
    if ont['edge_requirements']['lag_min'] != 0:
        errors.append('lag_min must be 0')
    if ont['edge_requirements']['same_slice_self_loop'] is not False:
        errors.append('same-slice self loops must be prohibited')
    if ont['intervention_requirements']['operation'] != 'surgical_assignment_replacement':
        errors.append('intervention operator mismatch')
    rows=list(csv.DictReader((ROOT/'spec/rq_hypothesis_metric_map.csv').open(encoding='utf-8')))
    if not rows:
        errors.append('empty RQ map')
    ids=[r['Hypothesis ID'] for r in rows]
    if len(ids)!=len(set(ids)):
        errors.append('duplicate hypothesis IDs')
    formal=(ROOT/'spec/dchag_formal_specification.md').read_text(encoding='utf-8')
    for token in ['do(C=c)','Intervention locality','Replay determinism','Portability contract']:
        if token not in formal:
            errors.append(f'missing formal token: {token}')
    return errors

if __name__=='__main__':
    errs=validate()
    if errs:
        print('\n'.join('FAIL: '+x for x in errs)); raise SystemExit(1)
    print('PASS: DCHAG Phase-1 specification validation')
