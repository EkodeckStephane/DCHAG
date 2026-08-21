import numpy as np

from run_lanl_structure import (
    CHANNELS,
    evaluate_fold,
    fit_sparse_from_counts,
    fit_structure,
    jaccard,
    stable_fold,
    transition_counts,
)


def test_stable_fold_is_deterministic():
    assert stable_fold("Comp1") == stable_fold("Comp1")
    assert 0 <= stable_fold("Comp1") < 5


def test_transition_counts_binary_lag():
    states = np.zeros((2, 4, 3), dtype=np.uint8)
    states[0, 0, 0] = 1
    states[0, 1, 1] = 1
    states[0, 2, 2] = 1
    mask = np.array([True, False])
    neg, pos = transition_counts(states, mask, target_index=1, t_start=1, t_end=3)
    assert neg.sum() + pos.sum() == 3
    assert pos.sum() == 1


def test_sparse_fit_returns_only_lag_parents():
    neg = np.array([100, 20, 30, 10, 30, 10, 10, 5])
    pos = np.array([5, 10, 10, 20, 20, 30, 30, 100])
    m = fit_sparse_from_counts(neg, pos, target_index=0)
    assert all(i in (0, 1, 2) for i in m["selected"])
    assert len(m["pattern_probabilities"]) == 8
    assert all(0 <= p <= 1 for p in m["pattern_probabilities"])


def test_fit_structure_and_evaluate_have_no_same_window_notation():
    rng = np.random.default_rng(7)
    states = (rng.random((20, 8, 3)) < np.array([0.2, 0.3, 0.4])).astype(np.uint8)
    train = np.zeros(20, dtype=bool)
    train[:15] = True
    test = ~train
    s = fit_structure(states, train, 1, 7)
    assert all("[t-1]->" in e and e.endswith("[t]") for e in s["edges"])
    ev = evaluate_fold(states, train, test, s)
    assert all(target in ev for target in CHANNELS)
    for target in CHANNELS:
        assert "DCHAG_Learned_Lag1" in ev[target]["brier"]
        assert "SelfLag" in ev[target]["brier"]
        assert "Prevalence" in ev[target]["brier"]


def test_jaccard():
    assert jaccard([], []) == 1.0
    assert jaccard(["a"], ["a"]) == 1.0
    assert jaccard(["a"], ["b"]) == 0.0
