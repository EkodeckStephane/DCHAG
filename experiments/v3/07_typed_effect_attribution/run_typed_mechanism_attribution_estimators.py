from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
for p in (HERE, SEMISYNTH):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import select_semisynthetic_estimator as sel
import run_semisynthetic_confirmatory_estimators as base
import tma_common as tma


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_world(public_root: Path, frozen_estimator: Path, world: str, outroot: Path, mc_reps: int = tma.MC_REPS) -> None:
    if tma.sha256_file(frozen_estimator) != tma.EXPECTED_FREEZE_SHA256:
        raise RuntimeError("corrected frozen-estimator SHA-256 mismatch")
    frozen = json.loads(frozen_estimator.read_text())
    if frozen.get("status") != "ACTIVE" or frozen.get("experiment_id") != "V3-SS-SEL-001-C1":
        raise RuntimeError("typed attribution requires active corrected estimator")
    if frozen.get("max_parents") != tma.EXPECTED_CAP or frozen.get("screening_C") != 0.05 or frozen.get("local_model_C") != 0.7:
        raise RuntimeError("frozen DCHAG configuration mismatch")
    if frozen.get("standardization_anchor_units_per_world") != 1500 or not frozen.get("split_local_trajectory_ids_qualified_by_split"):
        raise RuntimeError("split-qualified standardization invariant missing")
    if frozen.get("confirmatory_tuning_allowed"):
        raise RuntimeError("confirmatory tuning is forbidden")

    pub = public_root / world
    schema = json.loads((pub / "schema.json").read_text())
    train = pd.read_csv(pub / "train.csv")
    test = pd.read_csv(pub / "test.csv")
    if train.trajectory_id.nunique() != 1100 or test.trajectory_id.nunique() != 400:
        raise RuntimeError("world train/test count mismatch")
    train_anchors = sel.anchor_tensor_one_split(train, int(schema["horizon"]))
    test_anchors = sel.anchor_tensor_one_split(test, int(schema["horizon"]))
    anchors = np.concatenate([train_anchors, test_anchors], axis=0)
    if len(anchors) != 1500:
        raise RuntimeError("typed attribution must use exactly 1500 split-qualified anchors")

    t0 = time.time(); dchag = sel.fit_world(train, schema, tma.EXPECTED_CAP); dchag_seconds = time.time() - t0
    t0 = time.time(); dense = base.fit_dense(train, schema); dense_seconds = time.time() - t0

    rows = []
    coalitions = []
    for model_name, models in (("DCHAG_Learned", dchag), ("Dense_Sequential_GFormula", dense)):
        for control in schema["controls"]:
            result = tma.fitted_attribution(models, schema, anchors, world, model_name, control, mc_reps=mc_reps)
            if result["closure_error"] > 1e-10 or result["replay_consistency_error"] > 1e-10:
                raise RuntimeError(f"decomposition identity failed: {world} {model_name} {control}")
            for component, value in result["components"].items():
                rows.append({
                    "world": world, "family": schema["family"], "model": model_name, "control": control,
                    "component": component, "attribution": value,
                    "total_effect_replay": result["total_effect_replay"],
                    "ordinary_effect_same_stream": result["ordinary_effect_same_stream"],
                    "risk_do0": result["risk_do0"], "risk_do1": result["full_risk_do1"],
                    "closure_error": result["closure_error"], "replay_consistency_error": result["replay_consistency_error"],
                    "seed": result["seed"], "anchor_units": result["anchor_units"], "mc_reps_per_anchor": result["mc_reps_per_anchor"],
                })
            for coalition, value in result["coalition_values"].items():
                coalitions.append({"world": world, "family": schema["family"], "model": model_name,
                                   "control": control, "coalition": coalition, "value": value, "seed": result["seed"]})

    out = outroot / world
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "typed_attribution.csv", index=False)
    pd.DataFrame(coalitions).to_csv(out / "coalition_values.csv", index=False)
    write_json(out / "run_metadata.json", {
        "experiment_id": tma.EXPERIMENT_ID, "base_experiment_id": tma.BASE_EXPERIMENT_ID,
        "world": world, "family": schema["family"], "frozen_estimator_sha256": tma.EXPECTED_FREEZE_SHA256,
        "max_parents": tma.EXPECTED_CAP, "standardization_anchor_units": 1500,
        "mc_reps_per_anchor": int(mc_reps), "coalitions_per_control": 32,
        "common_random_numbers_across_coalitions": True,
        "dchag_fit_seconds": dchag_seconds, "dense_fit_seconds": dense_seconds,
        "dchag_learned_edges": len(sel.selected_edges(dchag)),
        "estimator_private_SCM_access": False, "confirmatory_hyperparameter_tuning": False,
        "confirmatory_world_replacement": False, "estimation_outputs_frozen_before_private_scoring": True,
    })
    files = ["typed_attribution.csv", "coalition_values.csv", "run_metadata.json"]
    write_json(out / "FREEZE_MANIFEST.json", {
        "experiment_id": tma.EXPERIMENT_ID, "world": world,
        "status": "estimation_outputs_frozen_before_private_scoring",
        "files": {name: tma.sha256_file(out / name) for name in files},
        "public_inputs": {name: tma.sha256_file(pub / name) for name in ("schema.json", "train.csv", "test.csv")},
        "frozen_estimator_sha256": tma.EXPECTED_FREEZE_SHA256,
    })
    print(json.dumps({"world": world, "status": "FROZEN", "records": len(rows)}, sort_keys=True))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--public-root", type=Path, required=True)
    ap.add_argument("--frozen-estimator", type=Path, required=True)
    ap.add_argument("--world", required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--mc-reps", type=int, default=tma.MC_REPS)
    args = ap.parse_args()
    if not args.world.startswith("confirm_"):
        raise RuntimeError("only confirmatory worlds are eligible")
    run_world(args.public_root, args.frozen_estimator, args.world, args.outdir, args.mc_reps)


if __name__ == "__main__":
    main()
