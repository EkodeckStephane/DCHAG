from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

import select_semisynthetic_estimator as sel
import run_semisynthetic_confirmatory_estimators as base

EXPECTED_FROZEN_ESTIMATOR_SHA256 = "d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31"
EXPECTED_SELECTION_EXPERIMENT = "V3-SS-SEL-001-C1"
EXPECTED_CAP = 8
MC_REPS = 100


def run_world(public_root: Path, frozen_estimator: Path, world: str, outroot: Path):
    if base.sha256_file(frozen_estimator) != EXPECTED_FROZEN_ESTIMATOR_SHA256:
        raise RuntimeError("corrected frozen estimator SHA-256 mismatch")
    frozen = json.loads(frozen_estimator.read_text())
    if frozen.get("status") != "ACTIVE" or frozen.get("experiment_id") != EXPECTED_SELECTION_EXPERIMENT:
        raise RuntimeError("Stage-B estimator is not the active corrected C1 freeze")
    if frozen["max_parents"] != EXPECTED_CAP or frozen["screening_C"] != 0.05 or frozen["local_model_C"] != 0.7:
        raise RuntimeError("corrected frozen estimator configuration mismatch")
    if frozen["intervention_mc_reps_per_anchor"] != MC_REPS or frozen["confirmatory_tuning_allowed"]:
        raise RuntimeError("corrected confirmatory settings mismatch")
    if frozen.get("standardization_anchor_units_per_world") != 1500 or not frozen.get("split_local_trajectory_ids_qualified_by_split"):
        raise RuntimeError("C1 split-local anchor guardrail missing")

    pub = public_root / world
    if not pub.is_dir() or not world.startswith("confirm_"):
        raise RuntimeError(f"invalid confirmatory public world: {world}")
    schema = json.loads((pub / "schema.json").read_text())
    train = pd.read_csv(pub / "train.csv")
    test = pd.read_csv(pub / "test.csv")
    if train.trajectory_id.nunique() != 1100 or test.trajectory_id.nunique() != 400:
        raise RuntimeError("confirmatory train/test unit count mismatch")

    # Critical C1 rule: trajectory_id is split-local. Reconstruct each split separately.
    train_anchors = sel.anchor_tensor_one_split(train, schema["horizon"])
    test_anchors = sel.anchor_tensor_one_split(test, schema["horizon"])
    all_anchors = np.concatenate([train_anchors, test_anchors], axis=0)
    if len(train_anchors) != 1100 or len(test_anchors) != 400 or len(all_anchors) != 1500:
        raise RuntimeError("confirmatory C1 anchor-count invariant failed")

    t0 = time.time()
    dchag = sel.fit_world(train, schema, EXPECTED_CAP)
    dchag_fit_seconds = time.time() - t0
    t0 = time.time()
    dense = base.fit_dense(train, schema)
    dense_fit_seconds = time.time() - t0

    effect_rows = []
    effect_rows.extend(base.intervention_effects(dchag, schema, all_anchors, world, "DCHAG_Learned"))
    effect_rows.extend(base.intervention_effects(dense, schema, all_anchors, world, "Dense_Sequential_GFormula"))
    effect_rows.extend(base.association_effects(train, schema, world))
    if any(int(row["anchor_units"]) != 1500 for row in effect_rows if row["model"] != "Observational_Association"):
        raise RuntimeError("effect standardization did not use 1500 anchors")

    ids1, p1 = base.prospective_predictions(dchag, schema, test, world, "DCHAG_Learned")
    ids2, p2 = base.prospective_predictions(dense, schema, test, world, "Dense_Sequential_GFormula")
    if not np.array_equal(ids1, ids2):
        raise RuntimeError("prediction trajectory IDs mismatch")
    end = test[test.time == schema["horizon"] - 1].sort_values("trajectory_id")
    y_true = end[schema["target"]].to_numpy(int)
    if not np.array_equal(ids1, end.trajectory_id.to_numpy()):
        raise RuntimeError("held-out trajectory alignment mismatch")

    train_prev = float(train[train.time == schema["horizon"] - 1][schema["target"]].mean())
    ref_brier = float(np.mean((y_true - train_prev) ** 2))
    brier1 = float(brier_score_loss(y_true, p1))
    brier2 = float(brier_score_loss(y_true, p2))
    predictions = pd.DataFrame({
        "trajectory_id": ids1,
        "y_true": y_true,
        "DCHAG_Learned": p1,
        "Dense_Sequential_GFormula": p2,
    })

    out = outroot / world
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(effect_rows).to_csv(out / "effect_estimates.csv", index=False)
    predictions.to_csv(out / "trajectory_predictions.csv", index=False)
    base.write_json(out / "learned_edges.json", [list(edge) for edge in sel.selected_edges(dchag)])
    base.write_json(out / "public_diagnostics.json", base.public_diagnostics(train, test, schema))
    base.write_json(out / "prediction_metrics.json", {
        "world": world,
        "train_final_y_prevalence": train_prev,
        "reference_brier": ref_brier,
        "DCHAG_Learned": {"brier": brier1, "bss": 1.0 - brier1 / ref_brier if ref_brier > 0 else None},
        "Dense_Sequential_GFormula": {"brier": brier2, "bss": 1.0 - brier2 / ref_brier if ref_brier > 0 else None},
    })
    base.write_json(out / "run_metadata.json", {
        "experiment_id": "V3-SS-CONF-001",
        "selection_experiment_id": EXPECTED_SELECTION_EXPERIMENT,
        "world": world,
        "family": schema["family"],
        "frozen_estimator_sha256": EXPECTED_FROZEN_ESTIMATOR_SHA256,
        "max_parents": EXPECTED_CAP,
        "dchag_fit_seconds": dchag_fit_seconds,
        "dense_fit_seconds": dense_fit_seconds,
        "train_anchor_units": int(len(train_anchors)),
        "test_anchor_units": int(len(test_anchors)),
        "standardization_anchor_units": int(len(all_anchors)),
        "split_local_trajectory_ids_qualified_by_split": True,
        "estimator_private_SCM_access": False,
        "confirmatory_hyperparameter_tuning": False,
        "confirmatory_world_replacement": False,
        "effect_mc_reps_per_anchor": MC_REPS,
        "prediction_mc_reps_per_anchor": MC_REPS,
    })

    frozen_files = [
        "effect_estimates.csv",
        "trajectory_predictions.csv",
        "learned_edges.json",
        "public_diagnostics.json",
        "prediction_metrics.json",
        "run_metadata.json",
    ]
    base.write_json(out / "freeze_manifest.json", {
        "status": "estimation_outputs_frozen_before_private_scoring",
        "world": world,
        "selection_experiment_id": EXPECTED_SELECTION_EXPERIMENT,
        "files": {name: base.sha256_file(out / name) for name in frozen_files},
        "public_inputs": {
            "schema.json": base.sha256_file(pub / "schema.json"),
            "train.csv": base.sha256_file(pub / "train.csv"),
            "test.csv": base.sha256_file(pub / "test.csv"),
        },
        "frozen_estimator_sha256": EXPECTED_FROZEN_ESTIMATOR_SHA256,
        "standardization_anchor_units": 1500,
    })
    print(json.dumps({"world": world, "status": "FROZEN", "max_parents": EXPECTED_CAP, "anchor_units": 1500}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--frozen-estimator", type=Path, required=True)
    parser.add_argument("--world", required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    run_world(args.public_root, args.frozen_estimator, args.world, args.outdir)


if __name__ == "__main__":
    main()
