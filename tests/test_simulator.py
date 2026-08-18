from pathlib import Path
import csv,json
import numpy as np
from dchag import load_config,DCHAGEngine
from simulator.world import WorldSimulator
ROOT=Path(__file__).resolve().parents[1]

def test_vectorized_world_matches_reference_semantics():
    cfg=load_config(ROOT/'configs/helpdesk_identity.yaml')
    world=WorldSimulator(cfg); exo=world.draw_exogenous(12,777)
    batch=world.simulate(exogenous=exo,interventions=dict(cfg.baseline_controls))
    for i in range(12):
        exo_i=[{node.id:float(exo[i,t,j]) for j,node in enumerate(cfg.nodes)} for t in range(cfg.horizon)]
        tr=DCHAGEngine(cfg).evaluate(exogenous=exo_i,interventions=dict(cfg.baseline_controls))
        ref=np.array([[tr.states[t][node.id] for node in cfg.nodes] for t in range(cfg.horizon)],dtype=np.int8)
        assert np.array_equal(ref,batch.states[i])

def test_benchmark_manifests_enforce_ground_truth_separation():
    for p in (ROOT/'configs').glob('*.yaml'):
        cfg=load_config(p); m=json.loads((ROOT/'benchmarks'/cfg.name/'manifest.json').read_text())
        assert all('ground_truth/' not in x for x in m['estimator_allowed_files'])
        assert all(x.startswith('ground_truth/') for x in m['estimator_forbidden_files'])
        assert 'train_observed.csv' in m['estimator_allowed_files']

def test_observed_files_do_not_expose_exogenous_or_probabilities():
    for p in (ROOT/'configs').glob('*.yaml'):
        cfg=load_config(p); b=ROOT/'benchmarks'/cfg.name
        header=next(csv.reader((b/'train_observed.csv').open(encoding='utf-8')))
        lowered=' '.join(header).lower()
        assert 'exogenous' not in lowered
        assert 'probabilit' not in lowered
        assert set(n.id for n in cfg.nodes).issubset(header)

def test_ground_truth_controls_have_nonnegative_protective_effect_in_fixtures():
    for p in (ROOT/'configs').glob('*.yaml'):
        cfg=load_config(p); effects=json.loads((ROOT/'benchmarks'/cfg.name/'ground_truth/intervention_effects.json').read_text())
        assert len(effects)==4
        assert all(e['risk_reduction']>0 for e in effects)
        assert all(e['paired_se']<0.003 for e in effects)

def test_ground_truth_stability_independent_seed():
    cfg=load_config(ROOT/'configs/data_exfiltration.yaml'); sim=WorldSimulator(cfg)
    a=sim.intervention_ground_truth('dlp_enforcement',n=30000,seed=91)
    b=sim.intervention_ground_truth('dlp_enforcement',n=30000,seed=92)
    combined=(a['paired_se']**2+b['paired_se']**2)**0.5
    assert abs(a['risk_reduction']-b['risk_reduction']) <= 4*combined

def test_observability_variant_rates_and_complete_human_process_mask():
    for p in (ROOT/'configs').glob('*.yaml'):
        cfg=load_config(p); meta=json.loads((ROOT/'benchmarks'/cfg.name/'variants/manifest.json').read_text())
        for rate in [10,30,50]:
            got=meta[f'test_missing_{rate:02d}']['fraction']
            assert abs(got-rate/100)<0.01
        assert meta['test_human_process_unobserved']['fraction']==1.0
        assert meta['train_human_process_unobserved']['fraction']==1.0
