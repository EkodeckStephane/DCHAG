from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import run_scaling_benchmark as run
import score_scaling_benchmark as score


def test_unique_configuration_set_is_frozen():
    assert run.unique_configurations() == [
        (12, 600),
        (24, 300),
        (24, 600),
        (24, 1200),
        (36, 600),
        (48, 600),
    ]
    assert set(run.unique_configurations()) == score.expected_configurations()


def test_generator_is_deterministic_and_complete():
    a, schema_a = run.generate_dataset(12, 40, 1)
    b, schema_b = run.generate_dataset(12, 40, 1)
    assert schema_a == schema_b
    assert a.equals(b)
    assert len(a) == 40 * run.HORIZON
    assert a.trajectory_id.nunique() == 40
    assert schema_a["endogenous_count"] == 12
    assert schema_a["total_observed_nodes"] == 15
    assert schema_a["target"] == "Y"
    assert schema_a["controls"] == ["C1", "C2", "C3", "C4"]
    assert set(a["split"]) == {"train", "test"}


def test_train_test_split_counts():
    frame, _ = run.generate_dataset(12, 50, 2)
    train, test = run.split_frame(frame)
    assert train.trajectory_id.nunique() == 40
    assert test.trajectory_id.nunique() == 10
    assert len(train) == 40 * run.HORIZON
    assert len(test) == 10 * run.HORIZON


def test_loglog_slope_exact_power():
    x = np.array([1.0, 2.0, 4.0, 8.0])
    y = 3.0 * x ** 1.5
    out = score.slope_loglog(x, y)
    assert abs(out["slope"] - 1.5) < 1e-12
    assert out["r2_log_space"] > 0.999999999


def test_dchag_parent_cap_on_small_smoke_fit():
    frozen = run.SEMISYNTH / "FROZEN_SEMISYNTHETIC_ESTIMATOR.json"
    result = run.fit_single("dchag", 12, 40, 1, frozen)
    assert result["model"] == "dchag"
    assert result["max_selected_parents"] <= run.EXPECTED_CAP
    assert result["private_oracle_access"] is False
    assert result["hyperparameter_tuning"] is False
    assert result["configuration_replacement"] is False
    assert result["fit_seconds"] > 0
    assert result["peak_rss_mib"] > 0
