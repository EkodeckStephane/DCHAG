from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
if str(SEMISYNTH) not in sys.path:
    sys.path.insert(0, str(SEMISYNTH))

import run_semisynthetic_decision_uncertainty as dec  # noqa: E402
import score_semisynthetic_decision_uncertainty as score  # noqa: E402


def toy_train() -> pd.DataFrame:
    rows = []
    for tid in range(1100):
        for t in range(6):
            rows.append({"trajectory_id": tid, "time": t, "A_person": tid % 2, "A_process": (tid + t) % 2, "A_technical": (tid // 2 + t) % 2, "R": 0, "C1": 0, "C2": 0, "C3": 0, "C4": 0, "H1": 0, "H2": 0, "P1": 0, "P2": 0, "T1": 0, "T2": 0, "Y": 0})
    return pd.DataFrame(rows)


def test_frozen_counts():
    assert dec.BOOTSTRAP_REPS == 40
    assert dec.MC_REPS == 25
    assert score.BOOTSTRAP_REPS == 40
    assert score.MC_REPS == 25
    assert score.WORLD_BOOTSTRAP_REPS == 10000


def test_cluster_bootstrap_requalifies_duplicate_trajectories():
    train = toy_train()
    boot, positions = dec.cluster_bootstrap(train, 6, 7)
    assert len(positions) == 1100
    assert boot.trajectory_id.nunique() == 1100
    assert len(boot) == 6600
    assert np.array_equal(boot.trajectory_id.to_numpy(), np.repeat(np.arange(1100), 6))
    assert np.array_equal(boot.time.to_numpy(), np.tile(np.arange(6), 1100))


def test_cluster_bootstrap_is_deterministic():
    train = toy_train()
    a, p1 = dec.cluster_bootstrap(train, 6, 999)
    b, p2 = dec.cluster_bootstrap(train, 6, 999)
    assert np.array_equal(p1, p2)
    assert a.equals(b)


def test_deterministic_top_tie_breaks_lexicographically():
    effects = {"C1": 0.1, "C2": 0.5, "C3": 0.5, "C4": 0.2}
    assert score.deterministic_top(effects) == "C2"


def test_exact_signflip_enumerates_all_world_assignments():
    vals = np.linspace(-0.01, 0.02, 16)
    out = score.exact_signflip(vals)
    assert out["assignments"] == 65536
    assert 0 <= out["exact_two_sided_p"] <= 1


def test_six_control_pairs():
    pairs = list(itertools.combinations(score.CONTROLS, 2))
    assert len(pairs) == 6
    assert pairs[0] == ("C1", "C2")
    assert pairs[-1] == ("C3", "C4")


def test_world_bootstrap_requires_16_values_and_is_deterministic():
    vals = np.arange(16, dtype=float) / 100.0
    a = score.world_bootstrap(vals, 123)
    b = score.world_bootstrap(vals, 123)
    assert a == b
    assert a["reps"] == 10000
    assert len(a["ci_95"]) == 2
