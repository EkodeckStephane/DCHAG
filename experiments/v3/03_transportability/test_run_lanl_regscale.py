import numpy as np

from run_lanl_regscale import REFERENCE_N, edge_names, sampled_counts, select_parents


def test_reference_size_is_frozen():
    assert REFERENCE_N == 6400


def test_edge_names_are_lag1_only():
    assert edge_names("H_login", [0, 2]) == [
        "H_login[t-1]->H_login[t]",
        "T_network[t-1]->H_login[t]",
    ]


def test_sampled_counts_use_exact_indices():
    states = np.zeros((3, 5, 3), dtype=np.uint8)
    states[0, 0, 0] = 1
    states[0, 1, 1] = 1
    mask = np.array([True, True, False])
    idx = np.array([0, 1, 4, 5])
    neg, pos = sampled_counts(states, mask, idx, target_index=1)
    assert neg.sum() + pos.sum() == 4
    assert pos.sum() == 1


def test_selector_returns_valid_parent_indices():
    neg = np.array([100, 20, 30, 10, 30, 10, 10, 5])
    pos = np.array([5, 10, 10, 20, 20, 30, 30, 100])
    s = select_parents(neg, pos, 0.05)
    assert s["selected"]
    assert all(i in (0, 1, 2) for i in s["selected"])
