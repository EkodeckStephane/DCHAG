from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(SEMISYNTH) not in sys.path:
    sys.path.insert(0, str(SEMISYNTH))

import run_semisynthetic_lofo_estimators as run
import score_semisynthetic_lofo as score


def canonical_schema():
    order = [
        "A_person", "A_process", "A_technical", "R", "C1", "C2", "C3", "C4",
        "H1", "H2", "P1", "P2", "T1", "T2", "Y",
    ]
    return {
        "anchor_nodes": ["A_person", "A_process", "A_technical"],
        "controls": ["C1", "C2", "C3", "C4"],
        "horizon": 6,
        "order": order,
        "target": "Y",
        "types": {node: ("anchor" if node.startswith("A_") else "technical") for node in order},
    }


def test_frozen_fold_partition_is_exact_and_exhaustive():
    all_targets = []
    for family in run.FAMILIES:
        targets = run.expected_target_worlds(family)
        sources = run.expected_source_worlds(family)
        assert len(targets) == 4
        assert len(sources) == 12
        assert not set(targets) & set(sources)
        assert sorted(targets + sources) == run.WORLDS
        all_targets.extend(targets)
    assert sorted(all_targets) == run.WORLDS


def test_source_trajectory_ids_are_world_qualified(tmp_path):
    schema = canonical_schema()
    source_root = tmp_path / "source_train"
    source_root.mkdir()
    heldout = "helpdesk_identity"
    worlds = run.expected_source_worlds(heldout)
    base = pd.DataFrame({
        "trajectory_id": np.repeat(np.arange(1100, dtype=np.int64), 6),
        "time": np.tile(np.arange(6, dtype=np.int64), 1100),
    })
    for j, node in enumerate(schema["order"]):
        base[node] = ((base["trajectory_id"] + base["time"] + j) % 2).astype(np.int8)
    for world in worlds:
        base.to_csv(source_root / f"{world}.csv", index=False)
    pooled, counts = run.qualify_source_train(source_root, worlds, schema)
    assert pooled["trajectory_id"].nunique() == 13200
    assert len(pooled) == 13200 * 6
    assert len(counts) == 12
    ranges = [(v["qualified_id_min"], v["qualified_id_max"]) for v in counts.values()]
    assert len(ranges) == len(set(ranges))
    assert all(hi - lo == 1099 for lo, hi in ranges)


def test_target_anchor_loader_preserves_split_local_identity(tmp_path):
    schema = canonical_schema()
    path = tmp_path / "target.npz"
    train = np.zeros((1100, 6, 3), dtype=np.int8)
    test = np.ones((400, 6, 3), dtype=np.int8)
    np.savez_compressed(path, train_anchors=train, test_anchors=test, test_ids=np.arange(400, dtype=np.int64))
    all_anchors, test_anchors, test_ids = run.load_target_anchors(path, schema)
    assert all_anchors.shape == (1500, 6, 3)
    assert test_anchors.shape == (400, 6, 3)
    assert np.array_equal(test_ids, np.arange(400))
    assert np.all(all_anchors[:1100] == 0)
    assert np.all(all_anchors[1100:] == 1)


def test_lofo_seed_namespace_is_deterministic_and_distinct():
    a = run.stable_seed("V3-SS-LOFO-001|effects|bec_payment|confirm_bec_payment_1|DCHAG_LOFO|C1")
    b = run.stable_seed("V3-SS-LOFO-001|effects|bec_payment|confirm_bec_payment_1|DCHAG_LOFO|C1")
    c = run.stable_seed("V3-SS-LOFO-001|effects|bec_payment|confirm_bec_payment_1|Dense_LOFO|C1")
    assert a == b
    assert a != c


def test_family_signflip_is_exact_16_assignments():
    x = np.array([-0.01, 0.02, -0.03, 0.04])
    out = score.exact_family_signflip(x)
    assert out["assignments"] == 16
    assert 0.0 <= out["exact_two_sided_p_descriptive"] <= 1.0
    assert abs(out["observed_mean_difference"] - x.mean()) < 1e-15


def test_hierarchical_bootstrap_is_frozen_and_deterministic():
    rows = []
    for fi, family in enumerate(score.FAMILIES):
        for wi in range(4):
            rows.append({"world": f"w{fi}_{wi}", "family": family, "difference": 0.01 * (fi - wi)})
    df = pd.DataFrame(rows)
    a = score.hierarchical_bootstrap(df)
    b = score.hierarchical_bootstrap(df)
    assert a == b
    assert a["reps"] == 10000
    assert a["seed"] == 20260823
    assert len(a["ci_95"]) == 2


def test_clean_input_rejects_forbidden_target_oracle_file(tmp_path):
    root = tmp_path / "clean"
    (root / "source_train").mkdir(parents=True)
    (root / "target_anchors").mkdir(parents=True)
    heldout = "bec_payment"
    fold = {
        "experiment_id": run.EXPERIMENT_ID,
        "heldout_family": heldout,
        "source_worlds": run.expected_source_worlds(heldout),
        "target_worlds": run.expected_target_worlds(heldout),
    }
    (root / "fold.json").write_text(json.dumps(fold))
    (root / "canonical_schema.json").write_text(json.dumps(canonical_schema()))
    forbidden = root / "target_anchors" / "oracle_effects.json"
    forbidden.write_text("{}")
    files = {
        "fold.json": run.sha256_file(root / "fold.json"),
        "canonical_schema.json": run.sha256_file(root / "canonical_schema.json"),
        "target_anchors/oracle_effects.json": run.sha256_file(forbidden),
    }
    (root / "LOFO_INPUT_MANIFEST.json").write_text(json.dumps({"experiment_id": run.EXPERIMENT_ID, "files": files}))
    try:
        run.verify_clean_input(root, heldout)
    except RuntimeError as exc:
        assert "forbidden" in str(exc).lower()
    else:
        raise AssertionError("forbidden target oracle material was not rejected")
