from pathlib import Path
import json, math
import pytest

from dchag import load_config, DCHAGEngine
from dchag.config import _parse, ConfigError, config_sha256
from dchag.errors import InterventionError
from dchag.engine import Trajectory

ROOT=Path(__file__).resolve().parents[1]
CONFIGS=sorted((ROOT/'configs').glob('*.yaml'))

def test_all_contexts_validate_and_execute_same_engine():
    assert len(CONFIGS)>=4
    for p in CONFIGS:
        cfg=load_config(p)
        eng=DCHAGEngine(cfg)
        tr=eng.evaluate(seed=123)
        assert len(tr.states)==cfg.horizon
        assert cfg.target in tr.states[-1]
        assert set(cfg.attack_nodes).issubset(tr.states[-1])

def test_duplicate_node_rejected():
    d={"name":"x","horizon":1,"target":"y","nodes":[
        {"id":"y","type":"technical","intercept":0},
        {"id":"y","type":"technical","intercept":0}],"baseline_controls":{}}
    with pytest.raises(ConfigError,match='duplicate'):
        _parse(d)

def test_same_slice_forward_reference_rejected():
    d={"name":"x","horizon":1,"target":"y","nodes":[
        {"id":"y","type":"technical","parents":[{"node":"a","coef":1}]},
        {"id":"a","type":"human"}],"baseline_controls":{}}
    with pytest.raises(ConfigError,match='must precede'):
        _parse(d)

def test_negative_lag_rejected():
    d={"name":"x","horizon":1,"target":"y","nodes":[
        {"id":"a","type":"human"},
        {"id":"y","type":"technical","parents":[{"node":"a","coef":1,"lag":-1}]}],"baseline_controls":{}}
    with pytest.raises(ConfigError,match='negative lag'):
        _parse(d)

def test_deterministic_replay_with_fixed_seed():
    cfg=load_config(ROOT/'configs/helpdesk_identity.yaml')
    eng=DCHAGEngine(cfg)
    a=eng.evaluate(seed=991)
    b=eng.evaluate(seed=991)
    assert a.to_json()==b.to_json()

def test_deterministic_counterfactual_replay_same_exogenous():
    cfg=load_config(ROOT/'configs/helpdesk_identity.yaml')
    eng=DCHAGEngine(cfg)
    factual=eng.evaluate(seed=7)
    cf1=eng.evaluate(exogenous=factual.exogenous,interventions={'strong_verification':1})
    cf2=eng.evaluate(exogenous=factual.exogenous,interventions={'strong_verification':1})
    assert cf1.to_json()==cf2.to_json()

def test_serialization_roundtrip():
    cfg=load_config(ROOT/'configs/bec_payment.yaml')
    tr=DCHAGEngine(cfg).evaluate(seed=55)
    restored=Trajectory.from_json(tr.to_json())
    assert restored.to_json()==tr.to_json()

def test_unknown_control_fails():
    cfg=load_config(ROOT/'configs/bec_payment.yaml')
    with pytest.raises(InterventionError):
        DCHAGEngine(cfg).evaluate(seed=1,interventions={'fake_control':1})

def test_intervention_overrides_control_assignment_only():
    cfg=load_config(ROOT/'configs/helpdesk_identity.yaml')
    eng=DCHAGEngine(cfg)
    exo=eng.draw_exogenous(12345)
    base=eng.evaluate(exogenous=exo)
    treated=eng.evaluate(exogenous=exo,interventions={'strong_verification':1})
    # Non-descendant context mechanism is unchanged under common exogenous replay.
    for t in range(cfg.horizon):
        assert base.states[t]['high_risk_context']==treated.states[t]['high_risk_context']
    assert all(treated.states[t]['strong_verification']==1 for t in range(cfg.horizon))

def test_no_effect_control_fixture_exact_paired_replay():
    d={"name":"noeffect","horizon":2,"target":"target","baseline_controls":{"isolated_control":0},"nodes":[
        {"id":"isolated_control","type":"control","intercept":-1},
        {"id":"attack","type":"human","intercept":0.1},
        {"id":"target","type":"technical","intercept":-1,"parents":[{"node":"attack","coef":2.0}]}
    ]}
    cfg=_parse(d); eng=DCHAGEngine(cfg)
    eff=eng.paired_effect('isolated_control',1,n=500,seed=11)
    assert eff.risk_reduction==0.0
    assert (eff.paired_differences==0).all()

def test_monotone_protective_fixture_never_increases_paired_outcome():
    cfg=load_config(ROOT/'configs/data_exfiltration.yaml')
    eng=DCHAGEngine(cfg)
    # Common-random-number structural replay; with protective negative edge and positive attack-chain edges,
    # the intervention cannot create an active attack state in this fixture.
    for seed in range(250):
        exo=eng.draw_exogenous(seed)
        b=eng.evaluate(exogenous=exo,interventions={'dlp_enforcement':0}).target_value(cfg.target)
        q=eng.evaluate(exogenous=exo,interventions={'dlp_enforcement':1}).target_value(cfg.target)
        assert q<=b

def test_active_subgraph_contains_only_attack_state_types():
    cfg=load_config(ROOT/'configs/helpdesk_identity.yaml')
    eng=DCHAGEngine(cfg)
    # Find an active target trajectory deterministically.
    for seed in range(10000):
        tr=eng.evaluate(seed=seed)
        if tr.target_value(cfg.target):
            sub=eng.active_attack_subgraph(tr)
            for label,parents in sub.items():
                node=label.split('@')[0]
                assert cfg.node_map[node].type in {'human','process','technical'}
                for p in parents:
                    pn=p.split('@')[0]
                    assert cfg.node_map[pn].type in {'human','process','technical'}
            break
    else:
        pytest.fail('no active target trajectory found')

def test_config_hash_stable():
    p=ROOT/'configs/helpdesk_identity.yaml'
    assert config_sha256(p)==config_sha256(p)
