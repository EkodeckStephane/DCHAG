from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
if str(SEMISYNTH) not in sys.path:
    sys.path.insert(0, str(SEMISYNTH))

import build_semisynthetic_oracle as base  # noqa: E402
import generate_semisynthetic_hidden_confounding as hc  # noqa: E402
import score_semisynthetic_hidden_confounding as score  # noqa: E402


def test_frozen_levels_and_gamma():
    assert hc.LEVELS == {"moderate": 0.50, "strong": 1.00}
    assert hc.GAMMA == {
        "C1": 0.55, "C2": 0.70, "C3": 0.65, "C4": 0.80,
        "H1": 0.25, "H2": 0.30, "P1": 0.25, "P2": 0.30,
        "T1": 0.35, "T2": 0.40, "Y": 1.00,
    }


def test_level_zero_reproduces_base_observed_simulator():
    spec = base.make_world_spec("bec_payment", 32011)
    rng = np.random.default_rng(123)
    anchors = rng.integers(0, 2, size=(23, base.HORIZON, 3), dtype=np.int8)
    obs = rng.random((23, base.HORIZON, len(base.ORDER)), dtype=np.float64)
    latent = rng.random((23, base.HORIZON), dtype=np.float64)
    hidden_states, u = hc.simulate_hidden(
        spec, anchors, 0.0, 999, observed_uniforms=obs, latent_uniforms=latent
    )
    base_states = base.simulate(spec, anchors, 999, uniforms=obs)
    assert np.array_equal(hidden_states, base_states)
    assert u.shape == (23, base.HORIZON)


def test_latent_path_is_deterministic_and_binary():
    rng = np.random.default_rng(99)
    anchors = rng.integers(0, 2, size=(17, base.HORIZON, 3), dtype=np.int8)
    uniforms = rng.random((17, base.HORIZON))
    a = hc.latent_path(anchors, uniforms)
    b = hc.latent_path(anchors, uniforms)
    assert np.array_equal(a, b)
    assert set(np.unique(a)).issubset({0, 1})


def test_public_frame_has_no_latent_column():
    spec = base.make_world_spec("helpdesk_identity", 31011)
    anchors = np.zeros((5, base.HORIZON, 3), dtype=np.int8)
    states, _ = hc.simulate_hidden(spec, anchors, 1.0, 1234)
    frame = hc.states_to_frame(states, spec["order"])
    assert "U" not in frame.columns
    assert "latent_U" not in frame.columns
    assert list(frame.columns[:2]) == ["trajectory_id", "time"]


def test_exact_signflip_enumerates_all_16_world_assignments():
    vals = np.linspace(0.001, 0.016, 16)
    out = score.exact_signflip(vals)
    assert out["assignments"] == 65536
    assert out["observed_mean"] > 0
    assert 0 <= out["exact_two_sided_p"] <= 1


def test_common_latent_path_under_intervention():
    spec = base.make_world_spec("exfiltration", 33011)
    rng = np.random.default_rng(7)
    anchors = rng.integers(0, 2, size=(19, base.HORIZON, 3), dtype=np.int8)
    obs = rng.random((19, base.HORIZON, len(base.ORDER)))
    latent = rng.random((19, base.HORIZON))
    _, u0 = hc.simulate_hidden(spec, anchors, 1.0, 1, {"C1": 0}, obs, latent)
    _, u1 = hc.simulate_hidden(spec, anchors, 1.0, 1, {"C1": 1}, obs, latent)
    assert np.array_equal(u0, u1)
