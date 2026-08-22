import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

MODULE_PATH = Path(__file__).with_name("select_semisynthetic_estimator.py")
spec = importlib.util.spec_from_file_location("sssel", MODULE_PATH)
sssel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sssel)


def test_feature_specs_include_current_predecessors_and_full_lag1():
    order = ["A", "B", "C"]
    specs = sssel.feature_specs(order, "B")
    assert specs == [
        ("A", 0, "A@0"),
        ("A", 1, "A@-1"),
        ("B", 1, "B@-1"),
        ("C", 1, "C@-1"),
    ]


def test_design_zero_fills_time0_lags_by_trajectory():
    df = pd.DataFrame({
        "trajectory_id": [0, 0, 1, 1],
        "time": [0, 1, 0, 1],
        "A": [1, 0, 0, 1],
        "B": [0, 1, 1, 0],
    })
    X, y, specs, data = sssel.design(df, ["A", "B"], "B")
    names = [s[2] for s in specs]
    a_lag = X[:, names.index("A@-1")]
    assert a_lag.tolist() == [0.0, 1.0, 0.0, 0.0]
    assert y.tolist() == [0, 1, 1, 0]


def test_augment_has_main_and_all_pairwise_interactions():
    X = np.array([[1, 0, 1], [1, 1, 0]], dtype=float)
    Z = sssel.augment(X, [0, 1, 2])
    assert Z.shape == (2, 6)
    assert Z[0].tolist() == [1, 0, 1, 0, 1, 0]


def test_rank_metrics_identifies_best_control_and_zero_regret():
    true = {"C1": 0.1, "C2": 0.3, "C3": 0.2}
    est = {"C1": 0.05, "C2": 0.25, "C3": 0.15}
    out = sssel.rank_metrics(true, est)
    assert out["top_control_true"] == "C2"
    assert out["top_control_selected"] == "C2"
    assert out["top_control_correct"] is True
    assert out["normalized_regret"] == 0.0


def test_candidate_constants_are_frozen():
    assert sssel.CAPS == [6, 8, 10]
    assert sssel.SCREENING_C == 0.05
    assert sssel.LOCAL_C == 0.7
    assert sssel.MC_REPS == 100
