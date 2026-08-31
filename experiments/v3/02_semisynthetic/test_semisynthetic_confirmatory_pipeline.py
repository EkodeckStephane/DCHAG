import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import select_semisynthetic_estimator as sel
import run_semisynthetic_confirmatory_estimators_c1 as conf
import score_semisynthetic_confirmatory as score


def _anchor_split(n_units, horizon, marker):
    rows = []
    for tid in range(n_units):
        for t in range(horizon):
            rows.append({
                "trajectory_id": tid,
                "time": t,
                "A_person": marker,
                "A_process": (tid + t) % 2,
                "A_technical": 1,
            })
    return pd.DataFrame(rows)


def test_confirmatory_anchor_standardization_qualifies_split_local_ids():
    train = _anchor_split(3, 2, 0)
    test = _anchor_split(2, 2, 1)
    a_train = sel.anchor_tensor_one_split(train, 2)
    a_test = sel.anchor_tensor_one_split(test, 2)
    combined = np.concatenate([a_train, a_test], axis=0)
    assert combined.shape == (5, 2, 3)
    assert np.all(combined[:3, :, 0] == 0)
    assert np.all(combined[3:, :, 0] == 1)


def test_confirmatory_runner_requires_corrected_c1_freeze():
    assert conf.EXPECTED_SELECTION_EXPERIMENT == "V3-SS-SEL-001-C1"
    assert conf.EXPECTED_CAP == 8
    assert conf.MC_REPS == 100
    assert conf.EXPECTED_FROZEN_ESTIMATOR_SHA256 == "d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31"


def test_exact_signflip_enumerates_all_assignments():
    d = np.array([1.0, 1.0])
    # Means under four sign patterns: -1,0,0,1; two are as extreme as observed |1|.
    assert score.exact_signflip_p(d) == 0.5


def test_edge_metrics_are_set_based():
    out = score.edge_metrics([["A", 1, "B"], ["A", 1, "B"]], [["A", 1, "B"], ["C", 0, "B"]])
    assert out["learned_edges"] == 1
    assert out["true_edges"] == 2
    assert out["edge_precision"] == 1.0
    assert out["edge_recall"] == 0.5


def test_active_frozen_estimator_file_has_c1_guardrails():
    frozen = json.loads((HERE / "FROZEN_SEMISYNTHETIC_ESTIMATOR.json").read_text())
    assert frozen["status"] == "ACTIVE"
    assert frozen["experiment_id"] == "V3-SS-SEL-001-C1"
    assert frozen["max_parents"] == 8
    assert frozen["standardization_anchor_units_per_world"] == 1500
    assert frozen["split_local_trajectory_ids_qualified_by_split"] is True
    assert frozen["confirmatory_tuning_allowed"] is False
