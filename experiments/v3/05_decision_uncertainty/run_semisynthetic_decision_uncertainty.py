from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
if str(SEMISYNTH) not in sys.path:
    sys.path.insert(0, str(SEMISYNTH))

import select_semisynthetic_estimator as sel  # noqa: E402
import run_semisynthetic_confirmatory_estimators as base  # noqa: E402

EXPERIMENT_ID = "V3-SS-DEC-001"
EXPECTED_FROZEN_ESTIMATOR_SHA256 = "d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31"
EXPECTED_CAP = 8
BOOTSTRAP_REPS = 40
MC_REPS = 25
ANCHORS = ["A_person", "A_process", "A_technical"]
MODELS = ["DCHAG_Learned", "Dense_Sequential_GFormula"]


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_seed(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16) % (2**32)


def split_anchors(train: pd.DataFrame, test: pd.DataFrame, horizon: int) -> np.ndarray:
    a_train = sel.anchor_tensor_one_split(train, horizon)
    a_test = sel.anchor_tensor_one_split(test, horizon)
    if len(a_train) != 1100 or len(a_test) != 400:
        raise RuntimeError("split-qualified anchor count mismatch")
    anchors = np.concatenate([a_train, a_test], axis=0)
    if len(anchors) != 1500:
        raise RuntimeError("decision standardization requires exactly 1,500 anchors")
    return anchors


def cluster_bootstrap(train: pd.DataFrame, horizon: int, seed: int) -> tuple[pd.DataFrame, np.ndarray]:
    data = train.sort_values(["trajectory_id", "time"]).reset_index(drop=True)
    ids = np.array(sorted(data.trajectory_id.unique()))
    n = len(ids)
    if n != 1100 or len(data) != n * horizon:
        raise RuntimeError("training cluster count mismatch")
    if not np.array_equal(data.trajectory_id.to_numpy(), np.repeat(ids, horizon)):
        raise RuntimeError("training trajectories are not complete contiguous blocks")
    if not np.array_equal(data.time.to_numpy(), np.tile(np.arange(horizon), n)):
        raise RuntimeError("training time grid mismatch")
    rng = np.random.default_rng(seed)
    positions = rng.integers(0, n, size=n, endpoint=False)
    row_idx = (positions[:, None] * horizon + np.arange(horizon)[None, :]).reshape(-1)
    boot = data.iloc[row_idx].copy().reset_index(drop=True)
    boot["trajectory_id"] = np.repeat(np.arange(n, dtype=np.int64), horizon)
    if boot.trajectory_id.nunique() != 1100 or len(boot) != 1100 * horizon:
        raise RuntimeError("bootstrap requalification failed")
    return boot, positions


def intervention_effects(models, schema: dict, anchors: np.ndarray, world: str, model_name: str, replicate: str) -> list[dict]:
    n = len(anchors)
    if n != 1500:
        raise RuntimeError("effect standardization requires 1,500 anchors")
    expanded = np.repeat(anchors, MC_REPS, axis=0)
    h = int(schema["horizon"])
    nonanchors = [node for node in schema["order"] if node not in ANCHORS]
    rows = []
    for control in schema["controls"]:
        seed = stable_seed(f"{EXPERIMENT_ID}|effects|{world}|{replicate}|{model_name}|{control}")
        rng = np.random.default_rng(seed)
        uniforms = rng.random((n * MC_REPS, h, len(nonanchors)), dtype=np.float64)
        y0 = base.simulate_final(models, schema, expanded, control, 0, uniforms).astype(float).reshape(n, MC_REPS)
        y1 = base.simulate_final(models, schema, expanded, control, 1, uniforms).astype(float).reshape(n, MC_REPS)
        unit_diff = (y0 - y1).mean(axis=1)
        rows.append({
            "world": world,
            "model": model_name,
            "control": control,
            "replicate": replicate,
            "risk_do0": float(y0.mean()),
            "risk_do1": float(y1.mean()),
            "risk_reduction": float(unit_diff.mean()),
            "mc_se_across_anchor_units": float(unit_diff.std(ddof=1) / math.sqrt(n)),
            "anchor_units": int(n),
            "mc_reps_per_anchor": MC_REPS,
            "effect_seed": int(seed),
        })
    return rows


def fit_models(train: pd.DataFrame, schema: dict):
    t0 = time.time()
    dchag = sel.fit_world(train, schema, EXPECTED_CAP)
    dchag_seconds = time.time() - t0
    t0 = time.time()
    dense = base.fit_dense(train, schema)
    dense_seconds = time.time() - t0
    return dchag, dense, dchag_seconds, dense_seconds


def run_world(public_root: Path, frozen_estimator: Path, world: str, outroot: Path) -> None:
    if sha256_file(frozen_estimator) != EXPECTED_FROZEN_ESTIMATOR_SHA256:
        raise RuntimeError("active corrected frozen estimator SHA-256 mismatch")
    frozen = json.loads(frozen_estimator.read_text())
    if frozen.get("status") != "ACTIVE" or frozen.get("experiment_id") != "V3-SS-SEL-001-C1":
        raise RuntimeError("corrected estimator is not active")
    if frozen.get("max_parents") != EXPECTED_CAP or frozen.get("confirmatory_tuning_allowed"):
        raise RuntimeError("frozen estimator configuration mismatch")
    if frozen.get("standardization_anchor_units_per_world") != 1500 or not frozen.get("split_local_trajectory_ids_qualified_by_split"):
        raise RuntimeError("split-local anchor guardrail missing")

    pub = public_root / world
    if not pub.is_dir() or not world.startswith("confirm_"):
        raise RuntimeError(f"invalid public world: {world}")
    forbidden = {"world.json", "oracle_effects.json", "true_edges.json"}
    if any(p.name in forbidden for p in pub.rglob("*") if p.is_file()):
        raise RuntimeError("private scoring material leaked into estimator input")

    schema = json.loads((pub / "schema.json").read_text())
    train = pd.read_csv(pub / "train.csv")
    test = pd.read_csv(pub / "test.csv")
    horizon = int(schema["horizon"])
    if train.trajectory_id.nunique() != 1100 or test.trajectory_id.nunique() != 400:
        raise RuntimeError("public train/test count mismatch")
    anchors = split_anchors(train, test, horizon)

    full_dchag, full_dense, full_dchag_seconds, full_dense_seconds = fit_models(train, schema)
    full_rows = []
    full_rows.extend(intervention_effects(full_dchag, schema, anchors, world, MODELS[0], "full"))
    full_rows.extend(intervention_effects(full_dense, schema, anchors, world, MODELS[1], "full"))

    bootstrap_rows = []
    diag_rows = []
    total_fit_seconds = {MODELS[0]: full_dchag_seconds, MODELS[1]: full_dense_seconds}
    for b in range(1, BOOTSTRAP_REPS + 1):
        bootstrap_seed = stable_seed(f"{EXPERIMENT_ID}|bootstrap|{world}|{b}")
        boot, positions = cluster_bootstrap(train, horizon, bootstrap_seed)
        dchag, dense, d_seconds, g_seconds = fit_models(boot, schema)
        total_fit_seconds[MODELS[0]] += d_seconds
        total_fit_seconds[MODELS[1]] += g_seconds
        rep = f"b{b:02d}"
        for row in intervention_effects(dchag, schema, anchors, world, MODELS[0], rep):
            row.update({"bootstrap_replicate": b, "bootstrap_seed": int(bootstrap_seed)})
            bootstrap_rows.append(row)
        for row in intervention_effects(dense, schema, anchors, world, MODELS[1], rep):
            row.update({"bootstrap_replicate": b, "bootstrap_seed": int(bootstrap_seed)})
            bootstrap_rows.append(row)
        diag_rows.append({
            "world": world,
            "bootstrap_replicate": b,
            "bootstrap_seed": int(bootstrap_seed),
            "sampled_clusters": 1100,
            "unique_original_clusters": int(len(np.unique(positions))),
        })

    out = outroot / world
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(full_rows).to_csv(out / "full_sample_effects.csv", index=False)
    pd.DataFrame(bootstrap_rows).to_csv(out / "bootstrap_effects.csv", index=False)
    pd.DataFrame(diag_rows).to_csv(out / "bootstrap_diagnostics.csv", index=False)
    write_json(out / "run_metadata.json", {
        "experiment_id": EXPERIMENT_ID,
        "world": world,
        "family": schema["family"],
        "selection_experiment_id": "V3-SS-SEL-001-C1",
        "frozen_estimator_sha256": EXPECTED_FROZEN_ESTIMATOR_SHA256,
        "max_parents": EXPECTED_CAP,
        "bootstrap_reps": BOOTSTRAP_REPS,
        "bootstrap_cluster_size": 1100,
        "bootstrap_unit": "trajectory_id six-row cluster",
        "standardization_anchor_units": 1500,
        "mc_reps_per_anchor": MC_REPS,
        "full_sample_fit_seconds": {MODELS[0]: full_dchag_seconds, MODELS[1]: full_dense_seconds},
        "total_fit_seconds": total_fit_seconds,
        "estimator_private_SCM_access": False,
        "target_outcomes_used_for_fit": False,
        "hyperparameter_retuning": False,
        "world_replacement": False,
        "bootstrap_replacement_after_results": False,
        "all_estimates_scored_private_after_freeze": False,
    })
    files = ["full_sample_effects.csv", "bootstrap_effects.csv", "bootstrap_diagnostics.csv", "run_metadata.json"]
    write_json(out / "FREEZE_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "world": world,
        "status": "decision_uncertainty_outputs_frozen_before_private_scoring",
        "files": {name: sha256_file(out / name) for name in files},
        "public_inputs": {name: sha256_file(pub / name) for name in ["schema.json", "train.csv", "test.csv"]},
        "bootstrap_reps": BOOTSTRAP_REPS,
        "standardization_anchor_units": 1500,
        "mc_reps_per_anchor": MC_REPS,
        "private_scoring_material_access": False,
    })
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "world": world, "status": "FROZEN", "bootstrap_reps": BOOTSTRAP_REPS}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--frozen-estimator", type=Path, required=True)
    parser.add_argument("--world", required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    run_world(args.public_root, args.frozen_estimator, args.world, args.outdir)


if __name__ == "__main__":
    main()
