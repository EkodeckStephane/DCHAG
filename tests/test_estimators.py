from pathlib import Path
import pandas as pd
import numpy as np
from dchag import load_config
from estimation import fit_scm
from baselines.observational_outcome import ObservationalOutcomeBaseline
from baselines.risk_scores import SEAGInspiredRiskBaseline,QualitativeRiskMatrixBaseline
ROOT=Path(__file__).resolve().parents[1]

def test_full_scm_fits_all_contexts_and_ablations_fit_reference_context():
    for p in (ROOT/'configs').glob('*.yaml'):
        cfg=load_config(p); train=ROOT/'benchmarks'/cfg.name/'train_observed.csv'
        m=fit_scm(cfg,train); assert m.target==cfg.target and len(m.nodes)>0
    cfg=load_config(ROOT/'configs/helpdesk_identity.yaml'); train=ROOT/'benchmarks/helpdesk_identity/train_observed.csv'
    models=[fit_scm(cfg,train,drop_types={'human'}),fit_scm(cfg,train,drop_types={'process'}),
            fit_scm(cfg,train,drop_types={'human','process'}),fit_scm(cfg,train,drop_lags=True)]
    for m in models:
        for c in m.controls:
            eff=m.estimate_effect(c,n=300,seed=71); assert -1<=eff['risk_reduction']<=1

def test_observational_baseline_has_four_effect_estimates():
    cfg=load_config(ROOT/'configs/helpdesk_identity.yaml'); df=pd.read_csv(ROOT/'benchmarks/helpdesk_identity/train_observed.csv')
    b=ObservationalOutcomeBaseline(cfg).fit(df)
    vals=[b.association_effect(c)['risk_reduction'] for c in cfg.controls]
    assert len(vals)==4 and all(np.isfinite(vals))

def test_shared_risk_baselines_predict_probabilities():
    cfg=load_config(ROOT/'configs/bec_payment.yaml')
    tr=pd.read_csv(ROOT/'benchmarks/bec_payment/train_observed.csv');te=pd.read_csv(ROOT/'benchmarks/bec_payment/test_observed.csv')
    for b in [SEAGInspiredRiskBaseline(cfg).fit(tr),QualitativeRiskMatrixBaseline(cfg).fit(tr)]:
        p=b.predict_proba(te); assert len(p)==3000; assert np.all((p>=0)&(p<=1))
