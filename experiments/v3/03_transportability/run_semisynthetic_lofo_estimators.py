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

EXPERIMENT_ID = "V3-SS-LOFO-001"
EXPECTED_FROZEN_ESTIMATOR_SHA256 = "d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31"
EXPECTED_CAP = 8
MC_REPS = 100
ANCHORS = ["A_person", "A_process", "A_technical"]
FAMILIES = ["bec_payment", "exfiltration", "helpdesk_identity", "itot_change"]
WORLDS = sorted([f"confirm_{family}_{i}" for family in FAMILIES for i in range(1, 5)])


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_seed(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16) % (2**32)


def family_from_world(world: str) -> str:
    if not world.startswith("confirm_"):
        raise ValueError(f"not a confirmatory world: {world}")
    for family in FAMILIES:
        if world.startswith(f"confirm_{family}_"):
            return family
    raise ValueError(f"unknown world family: {world}")


def expected_target_worlds(heldout_family: str) -> list[str]:
    if heldout_family not in FAMILIES:
        raise ValueError(f"unknown held-out family: {heldout_family}")
    return [f"confirm_{heldout_family}_{i}" for i in range(1, 5)]


def expected_source_worlds(heldout_family: str) -> list[str]:
    targets = set(expected_target_worlds(heldout_family))
    return sorted(w for w in WORLDS if w not in targets)


def schema_signature(schema: dict) -> dict:
    return {
        "horizon": int(schema["horizon"]),
        "order": list(schema["order"]),
        "anchor_nodes": list(schema["anchor_nodes"]),
        "controls": list(schema["controls"]),
        "target": schema["target"],
        "types": dict(schema["types"]),
    }


def qualify_source_train(source_root: Path, source_worlds: list[str], schema: dict) -> tuple[pd.DataFrame, dict]:
    pieces = []
    counts = {}
    horizon = int(schema["horizon"])
    for world_index, world in enumerate(sorted(source_worlds), start=1):
        path = source_root / f"{world}.csv"
        if not path.is_file():
            raise RuntimeError(f"missing source train file: {path}")
        df = pd.read_csv(path)
        required = set(schema["order"]) | {"trajectory_id", "time"}
        if not required.issubset(df.columns):
            raise RuntimeError(f"source train columns incomplete for {world}")
        ids = np.array(sorted(df["trajectory_id"].unique()))
        if len(ids) != 1100 or len(df) != 1100 * horizon:
            raise RuntimeError(f"source train count mismatch for {world}")
        if ids.min() != 0 or ids.max() != 1099:
            raise RuntimeError(f"unexpected source-local trajectory IDs for {world}")
        q = df.copy()
        q["trajectory_id"] = world_index * 100000 + q["trajectory_id"].astype(np.int64)
        q["source_world"] = world
        pieces.append(q)
        counts[world] = {
            "local_trajectories": 1100,
            "qualified_id_min": int(world_index * 100000),
            "qualified_id_max": int(world_index * 100000 + 1099),
        }
    pooled = pd.concat(pieces, ignore_index=True)
    if pooled["trajectory_id"].nunique() != 13200:
        raise RuntimeError("pooled source qualification failed: expected 13,200 unique trajectories")
    if len(pooled) != 13200 * horizon:
        raise RuntimeError("pooled source row count mismatch")
    return pooled, counts


def load_target_anchors(path: Path, schema: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not path.is_file():
        raise RuntimeError(f"missing target-anchor file: {path}")
    with np.load(path, allow_pickle=False) as z:
        train_anchors = np.asarray(z["train_anchors"], dtype=np.int8)
        test_anchors = np.asarray(z["test_anchors"], dtype=np.int8)
        test_ids = np.asarray(z["test_ids"], dtype=np.int64)
    expected_train = (1100, int(schema["horizon"]), len(ANCHORS))
    expected_test = (400, int(schema["horizon"]), len(ANCHORS))
    if train_anchors.shape != expected_train or test_anchors.shape != expected_test:
        raise RuntimeError(f"target anchor tensor shape mismatch: {path.name}")
    if test_ids.shape != (400,) or not np.array_equal(test_ids, np.arange(400, dtype=np.int64)):
        raise RuntimeError(f"target test ID mismatch: {path.name}")
    all_anchors = np.concatenate([train_anchors, test_anchors], axis=0)
    if all_anchors.shape[0] != 1500:
        raise RuntimeError("target standardization must contain exactly 1,500 split-qualified anchor units")
    return all_anchors, test_anchors, test_ids


def intervention_effects(models, schema: dict, anchors: np.ndarray, heldout_family: str, world: str, model_name: str):
    n = len(anchors)
    if n != 1500:
        raise RuntimeError("LOFO effect standardization requires exactly 1,500 target anchors")
    expanded = np.repeat(anchors, MC_REPS, axis=0)
    nonanchors = [node for node in schema["order"] if node not in ANCHORS]
    h = int(schema["horizon"])
    rows = []
    for control in schema["controls"]:
        seed = stable_seed(f"{EXPERIMENT_ID}|effects|{heldout_family}|{world}|{model_name}|{control}")
        rng = np.random.default_rng(seed)
        uniforms = rng.random((n * MC_REPS, h, len(nonanchors)), dtype=np.float64)
        y0 = base.simulate_final(models, schema, expanded, control, 0, uniforms).astype(float).reshape(n, MC_REPS)
        y1 = base.simulate_final(models, schema, expanded, control, 1, uniforms).astype(float).reshape(n, MC_REPS)
        unit_diff = (y0 - y1).mean(axis=1)
        rows.append({
            "heldout_family": heldout_family,
            "world": world,
            "model": model_name,
            "control": control,
            "risk_do0": float(y0.mean()),
            "risk_do1": float(y1.mean()),
            "risk_reduction": float(unit_diff.mean()),
            "mc_se_across_anchor_units": float(unit_diff.std(ddof=1) / math.sqrt(n)),
            "anchor_units": int(n),
            "mc_reps_per_anchor": MC_REPS,
            "seed": int(seed),
        })
    return rows


def predictions_from_anchors(models, schema: dict, test_anchors: np.ndarray, test_ids: np.ndarray, heldout_family: str, world: str, model_name: str):
    n = len(test_anchors)
    if n != 400:
        raise RuntimeError("LOFO target prediction requires exactly 400 test anchors")
    expanded = np.repeat(test_anchors, MC_REPS, axis=0)
    nonanchors = [node for node in schema["order"] if node not in ANCHORS]
    seed = stable_seed(f"{EXPERIMENT_ID}|prediction|{heldout_family}|{world}|{model_name}")
    rng = np.random.default_rng(seed)
    uniforms = rng.random((n * MC_REPS, int(schema["horizon"]), len(nonanchors)), dtype=np.float64)
    y = base.simulate_final(models, schema, expanded, None, 0, uniforms).astype(float).reshape(n, MC_REPS)
    return test_ids.copy(), y.mean(axis=1), int(seed)


def verify_clean_input(root: Path, heldout_family: str) -> dict:
    manifest_path = root / "LOFO_INPUT_MANIFEST.json"
    fold_path = root / "fold.json"
    schema_path = root / "canonical_schema.json"
    if not manifest_path.is_file() or not fold_path.is_file() or not schema_path.is_file():
        raise RuntimeError("LOFO clean-input metadata missing")
    manifest = json.loads(manifest_path.read_text())
    fold = json.loads(fold_path.read_text())
    if manifest.get("experiment_id") != EXPERIMENT_ID or fold.get("experiment_id") != EXPERIMENT_ID:
        raise RuntimeError("LOFO input experiment ID mismatch")
    if fold.get("heldout_family") != heldout_family:
        raise RuntimeError("LOFO held-out family mismatch")
    if sorted(fold.get("source_worlds", [])) != expected_source_worlds(heldout_family):
        raise RuntimeError("LOFO source-world set mismatch")
    if sorted(fold.get("target_worlds", [])) != expected_target_worlds(heldout_family):
        raise RuntimeError("LOFO target-world set mismatch")
    expected_files = dict(manifest.get("files", {}))
    if not expected_files:
        raise RuntimeError("empty LOFO input manifest")
    for rel, digest in expected_files.items():
        p = root / rel
        if not p.is_file() or sha256_file(p) != digest:
            raise RuntimeError(f"LOFO input hash mismatch: {rel}")
    actual = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.name != "LOFO_INPUT_MANIFEST.json")
    expected = sorted(expected_files)
    if actual != expected:
        raise RuntimeError("LOFO clean-input file set differs from manifest")
    forbidden_names = {"world.json", "oracle_effects.json", "true_edges.json", "test.csv"}
    if any(Path(rel).name in forbidden_names for rel in actual):
        raise RuntimeError("forbidden target/private material present in estimator input")
    return fold


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--frozen-estimator", required=True)
    parser.add_argument("--heldout-family", choices=FAMILIES, required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    root = Path(args.input_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    heldout = args.heldout_family

    if sha256_file(args.frozen_estimator) != EXPECTED_FROZEN_ESTIMATOR_SHA256:
        raise RuntimeError("active corrected frozen-estimator SHA-256 mismatch")
    frozen = json.loads(Path(args.frozen_estimator).read_text())
    if frozen.get("status") != "ACTIVE" or frozen.get("experiment_id") != "V3-SS-SEL-001-C1":
        raise RuntimeError("corrected estimator is not the active freeze")
    if frozen.get("max_parents") != EXPECTED_CAP or frozen.get("standardization_anchor_units_per_world") != 1500:
        raise RuntimeError("LOFO frozen-estimator configuration mismatch")
    if not frozen.get("split_local_trajectory_ids_qualified_by_split") or frozen.get("confirmatory_tuning_allowed"):
        raise RuntimeError("LOFO estimator guardrail mismatch")

    fold = verify_clean_input(root, heldout)
    schema = json.loads((root / "canonical_schema.json").read_text())
    sig = schema_signature(schema)
    if sig["horizon"] != 6 or sig["anchor_nodes"] != ANCHORS or sig["target"] != "Y":
        raise RuntimeError("canonical schema invariant failed")

    source_worlds = expected_source_worlds(heldout)
    target_worlds = expected_target_worlds(heldout)
    source_train, qualification = qualify_source_train(root / "source_train", source_worlds, schema)
    source_final = source_train[source_train["time"] == int(schema["horizon"]) - 1]
    source_final_y_prevalence = float(source_final[schema["target"]].mean())

    t0 = time.time()
    dchag = sel.fit_world(source_train, schema, EXPECTED_CAP)
    dchag_fit_seconds = time.time() - t0
    t0 = time.time()
    dense = base.fit_dense(source_train, schema)
    dense_fit_seconds = time.time() - t0

    source_edges = sel.selected_edges(dchag)
    mi_fallback_nodes = int(sum(bool(model.fallback) for model in dchag.values()))

    effect_rows = []
    prediction_rows = []
    target_counts = {}
    prediction_seeds = {}
    for world in target_worlds:
        anchor_path = root / "target_anchors" / f"{world}.npz"
        all_anchors, test_anchors, test_ids = load_target_anchors(anchor_path, schema)
        target_counts[world] = {"standardization": int(len(all_anchors)), "test_prediction": int(len(test_anchors))}
        effect_rows.extend(intervention_effects(dchag, schema, all_anchors, heldout, world, "DCHAG_LOFO"))
        effect_rows.extend(intervention_effects(dense, schema, all_anchors, heldout, world, "Dense_LOFO"))
        ids1, p1, seed1 = predictions_from_anchors(dchag, schema, test_anchors, test_ids, heldout, world, "DCHAG_LOFO")
        ids2, p2, seed2 = predictions_from_anchors(dense, schema, test_anchors, test_ids, heldout, world, "Dense_LOFO")
        if not np.array_equal(ids1, ids2):
            raise RuntimeError("LOFO prediction ID mismatch between models")
        prediction_seeds[world] = {"DCHAG_LOFO": seed1, "Dense_LOFO": seed2}
        for trajectory_id, dprob, gprob in zip(ids1, p1, p2):
            prediction_rows.append({
                "heldout_family": heldout,
                "world": world,
                "trajectory_id": int(trajectory_id),
                "DCHAG_LOFO": float(dprob),
                "Dense_LOFO": float(gprob),
            })

    effects = pd.DataFrame(effect_rows)
    predictions = pd.DataFrame(prediction_rows)
    if len(effects) != 4 * 2 * 4:
        raise RuntimeError("LOFO effect-row count mismatch")
    if len(predictions) != 4 * 400:
        raise RuntimeError("LOFO prediction-row count mismatch")
    if not (effects.loc[:, "anchor_units"] == 1500).all() or not (effects.loc[:, "mc_reps_per_anchor"] == 100).all():
        raise RuntimeError("LOFO effect MC/anchor guardrail failed")

    effects.to_csv(outdir / "effect_estimates.csv", index=False)
    predictions.to_csv(outdir / "target_predictions.csv", index=False)
    write_json(outdir / "dchag_source_edges.json", [list(edge) for edge in source_edges])
    write_json(outdir / "run_metadata.json", {
        "experiment_id": EXPERIMENT_ID,
        "heldout_family": heldout,
        "source_worlds": source_worlds,
        "target_worlds": target_worlds,
        "source_families": sorted(set(FAMILIES) - {heldout}),
        "source_train_trajectories": int(source_train["trajectory_id"].nunique()),
        "source_train_rows": int(len(source_train)),
        "source_final_y_prevalence": source_final_y_prevalence,
        "source_trajectory_qualification": qualification,
        "target_anchor_counts": target_counts,
        "dchag_fit_seconds": dchag_fit_seconds,
        "dense_fit_seconds": dense_fit_seconds,
        "dchag_source_learned_edges": len(source_edges),
        "dchag_mi_fallback_nodes": mi_fallback_nodes,
        "prediction_seeds": prediction_seeds,
        "max_parents": EXPECTED_CAP,
        "screening_C": 0.05,
        "local_model_C": 0.7,
        "mc_reps_per_anchor": MC_REPS,
        "frozen_estimator_sha256": EXPECTED_FROZEN_ESTIMATOR_SHA256,
        "target_endogenous_or_outcome_data_used_for_fit": False,
        "target_family_used_for_hyperparameter_selection": False,
        "private_SCM_or_oracle_access": False,
        "target_standardization_anchor_only": True,
        "confirmatory_world_replacement": False,
        "rq2_analysis_class": "locked_secondary_post_RQ1",
        "fold_manifest": fold,
    })

    freeze_files = [
        outdir / "effect_estimates.csv",
        outdir / "target_predictions.csv",
        outdir / "dchag_source_edges.json",
        outdir / "run_metadata.json",
    ]
    write_json(outdir / "FREEZE_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "heldout_family": heldout,
        "files": {p.name: sha256_file(p) for p in freeze_files},
        "estimator_private_SCM_access": False,
        "target_endogenous_or_outcome_data_used_for_fit": False,
        "target_family_used_for_hyperparameter_selection": False,
        "frozen_before_private_scoring": True,
    })
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "heldout_family": heldout,
        "source_train_trajectories": 13200,
        "target_worlds": 4,
        "effect_rows": len(effects),
        "prediction_rows": len(predictions),
        "dchag_source_edges": len(source_edges),
        "mi_fallback_nodes": mi_fallback_nodes,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
