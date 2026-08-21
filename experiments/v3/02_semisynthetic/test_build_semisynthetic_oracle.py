import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("dchag_ss_builder", HERE / "build_semisynthetic_oracle.py")
ss = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ss
SPEC.loader.exec_module(ss)


def fake_devices(n=30010):
    return [f"Comp{i:06d}" for i in range(n)]


def test_device_allocation_is_deterministic_and_disjoint():
    devices = fake_devices()
    a = ss.allocate_devices(devices, devices_per_world=1500)
    b = ss.allocate_devices(list(reversed(devices)), devices_per_world=1500)
    assert a == b
    flat = [d for block in a.values() for d in block]
    assert len(flat) == 30000
    assert len(set(flat)) == 30000
    assert len(a) == 20


def test_world_spec_contains_no_hidden_confounder_and_has_protective_control_paths():
    for family, seed in zip(ss.DEV_FAMILIES, ss.DEV_SEEDS):
        w = ss.make_world_spec(family, seed)
        assert w["hidden_confounder_present"] is False
        assert w["horizon"] == 6
        assert w["order"] == ss.ORDER
        assert all(c in w["nodes"] for c in ss.CONTROLS)
        assert any(p["node"].startswith("C") and p["coef"] < 0 for p in w["nodes"]["H1"]["parents"])
        assert any(p["node"].startswith("C") and p["coef"] < 0 for p in w["nodes"]["P1"]["parents"])
        assert any(p["node"].startswith("C") and p["coef"] < 0 for p in w["nodes"]["T1"]["parents"])
        assert any(p["node"].startswith("C") and p["coef"] < 0 for p in w["nodes"]["Y"]["parents"])


def test_intervention_fixes_selected_control_and_common_random_numbers_are_deterministic():
    w = ss.make_world_spec("helpdesk_identity", 21011)
    anchors = np.zeros((25, 6, 3), dtype=np.int8)
    anchors[:, :, 2] = 1
    uniforms = np.random.default_rng(123).random((25, 6, len(ss.ORDER)))
    s0 = ss.simulate(w, anchors, 999, interventions={"C2": 0}, uniforms=uniforms)
    s1 = ss.simulate(w, anchors, 999, interventions={"C2": 1}, uniforms=uniforms)
    c2 = ss.ORDER.index("C2")
    assert np.all(s0[:, :, c2] == 0)
    assert np.all(s1[:, :, c2] == 1)
    assert np.array_equal(s0, ss.simulate(w, anchors, 999, interventions={"C2": 0}, uniforms=uniforms))


def test_true_edges_are_temporally_admissible():
    w = ss.make_world_spec("itot_change", 24011)
    pos = {n: i for i, n in enumerate(ss.ORDER)}
    for parent, lag, child in ss.true_edges(w):
        assert lag in (0, 1)
        if lag == 0:
            assert pos[parent] < pos[child]


def test_oracle_returns_all_controls_and_finite_values():
    w = ss.make_world_spec("exfiltration", 23011)
    rng = np.random.default_rng(5)
    probs = np.array([.05, .28, .45]).reshape(1, 1, 3)
    anchors = (rng.random((60, 6, 3)) < probs).astype(np.int8)
    q = ss.oracle_effects(w, anchors, 777, reps=4)
    assert set(q) == set(ss.CONTROLS)
    for v in q.values():
        assert np.isfinite(v["risk_reduction"])
        assert np.isfinite(v["oracle_se_across_anchor_units"])
        assert v["mc_reps_per_anchor"] == 4
        assert v["anchor_units"] == 60
