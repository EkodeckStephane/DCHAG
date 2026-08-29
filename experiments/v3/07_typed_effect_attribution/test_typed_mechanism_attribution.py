from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
for p in (HERE, SEMISYNTH):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import tma_common as tma


def test_coalition_enumeration_and_keys():
    c = tma.coalition_list()
    assert len(c) == 32 and len(set(c)) == 32
    assert tuple() in c and tuple(tma.BLOCKS) in c
    assert tma.coalition_key(tuple()) == "empty"
    assert tma.coalition_key(("P", "H")) == "H+P"


def test_shapley_efficiency_arbitrary_characteristic_function():
    vals = {}
    weights = {"H": 0.11, "P": -0.04, "T": 0.08, "C": 0.03, "R": -0.02}
    direct = 0.07
    for coalition in tma.coalition_list():
        vals[coalition] = direct + sum(weights[g] for g in coalition) + (0.015 if {"H", "T"}.issubset(coalition) else 0.0)
    phi = tma.shapley_from_values(vals)
    assert abs(vals[tuple(tma.BLOCKS)] - (vals[tuple()] + sum(phi.values()))) < 1e-12


def test_common_seed_does_not_encode_coalition():
    a = tma.stable_seed(f"{tma.EXPERIMENT_ID}|w|m|C1|mechanism-replay")
    b = tma.stable_seed(f"{tma.EXPERIMENT_ID}|w|m|C1|mechanism-replay")
    assert a == b


def test_exact_signflip_bounds_and_symmetry():
    x = np.array([0.1, -0.2, 0.3, -0.4])
    p = tma.exact_signflip_p(x)
    assert 0 <= p <= 1
    assert p == tma.exact_signflip_p(-x)
