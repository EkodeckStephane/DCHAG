import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import select_semisynthetic_estimator as sssel


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


def _anchor_split(n_units, horizon, marker):
    rows = []
    for trajectory_id in range(n_units):
        for t in range(horizon):
            rows.append({
                "trajectory_id": trajectory_id,
                "time": t,
                "A_person": marker,
                "A_process": (trajectory_id + t) % 2,
                "A_technical": 1,
            })
    return pd.DataFrame(rows)


def test_split_local_trajectory_ids_do_not_collapse_anchor_units():
    train = _anchor_split(3, 2, 0)
    test = _anchor_split(2, 2, 1)  # IDs 0 and 1 deliberately collide with train IDs
    anchors = sssel.anchor_tensor_splits(train, test, 2)
    assert anchors.shape == (5, 2, 3)
    assert np.all(anchors[:3, :, 0] == 0)
    assert np.all(anchors[3:, :, 0] == 1)


def test_candidate_constants_are_frozen_for_correction():
    assert sssel.EXPERIMENT_ID == "V3-SS-SEL-001-C1"
    assert sssel.MC_SEED_NAMESPACE == "V3-SS-SEL-001"
    assert sssel.CAPS == [6, 8, 10]
    assert sssel.SCREENING_C == 0.05
    assert sssel.LOCAL_C == 0.7
    assert sssel.MC_REPS == 100
