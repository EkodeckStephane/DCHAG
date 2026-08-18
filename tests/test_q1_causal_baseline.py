from pathlib import Path
import pandas as pd

from baselines.causal_gformula import CrossFittedFlexibleGFormula
from dchag.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def test_q1_gformula_features_exclude_realized_mediators():
    cfg = load_config(ROOT / "configs" / "helpdesk_identity.yaml")
    est = CrossFittedFlexibleGFormula(cfg)
    features = est.feature_columns
    assert all(c.startswith("high_risk_context@") or any(c.startswith(f"{ctl}@") for ctl in cfg.controls) for c in features)
    assert not any("approve_reset" in c or "reset_authorized" in c or "privileged_access" in c for c in features)


def test_q1_gformula_smoke_estimates_all_controls():
    cfg = load_config(ROOT / "configs" / "helpdesk_identity.yaml")
    df = pd.read_csv(ROOT / "benchmarks" / "helpdesk_identity" / "train_observed.csv")
    # A deterministic small trajectory sample is sufficient for a smoke test.
    keep = sorted(df.trajectory_id.unique())[:800]
    small = df[df.trajectory_id.isin(keep)].copy()
    est = CrossFittedFlexibleGFormula(cfg, n_splits=2, fold_seed=260817)
    rows = est.estimate_effects(small)
    assert {r.control for r in rows} == set(cfg.controls)
    assert all(-1.0 <= r.risk_reduction <= 1.0 for r in rows)


def test_q1_positivity_reports_baseline_and_interventions():
    cfg = load_config(ROOT / "configs" / "helpdesk_identity.yaml")
    df = pd.read_csv(ROOT / "benchmarks" / "helpdesk_identity" / "train_observed.csv")
    keep = sorted(df.trajectory_id.unique())[:800]
    small = df[df.trajectory_id.isin(keep)].copy()
    est = CrossFittedFlexibleGFormula(cfg)
    p = est.positivity_diagnostics(small)
    assert len(p) == 1 + len(cfg.controls)
    assert "baseline" in set(p.regime)
    assert (p.expected_support_count >= 0).all()

from baselines.dense_sequential_gformula import CrossFittedDenseSequentialGFormula


def test_dense_sequential_uses_dense_history_not_sparse_parent_edges():
    cfg = load_config(ROOT / "configs" / "helpdesk_identity.yaml")
    est = CrossFittedDenseSequentialGFormula(cfg, n_splits=2, mc_per_trajectory=2)
    names = est._feature_names("compromise")
    # Dense history contains variables outside compromise's sparse true parent set.
    assert "cur:approve_reset" in names
    assert "cur:manager_callback" in names
    assert "lag:strong_verification" in names


def test_dense_sequential_smoke_estimates_all_controls():
    cfg = load_config(ROOT / "configs" / "helpdesk_identity.yaml")
    df = pd.read_csv(ROOT / "benchmarks" / "helpdesk_identity" / "train_observed.csv")
    keep = sorted(df.trajectory_id.unique())[:300]
    small = df[df.trajectory_id.isin(keep)].copy()
    est = CrossFittedDenseSequentialGFormula(cfg, n_splits=2, mc_per_trajectory=2, simulation_seed_base=91)
    rows = est.estimate_effects(small)
    assert {r.control for r in rows} == set(cfg.controls)
    assert all(-1.0 <= r.risk_reduction <= 1.0 for r in rows)


def test_dense_sequential_local_positivity_reports_all_cells():
    cfg = load_config(ROOT / "configs" / "helpdesk_identity.yaml")
    df = pd.read_csv(ROOT / "benchmarks" / "helpdesk_identity" / "train_observed.csv")
    est = CrossFittedDenseSequentialGFormula(cfg)
    p = est.local_positivity(df)
    assert len(p) == len(cfg.controls) * cfg.horizon * 2
    assert p.empirical_target_probability.between(0, 1).all()
