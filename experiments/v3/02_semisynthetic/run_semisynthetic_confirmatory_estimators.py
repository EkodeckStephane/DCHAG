from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

import select_semisynthetic_estimator as sel

ANCHORS = ["A_person", "A_process", "A_technical"]
EXPECTED_FROZEN_ESTIMATOR_SHA256 = "8d592bf54b5103501391c79204829dff88b1fb4831841022cfea2687d0660105"
EXPECTED_CAP = 8
MC_REPS = 100


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


class DenseLocalModel:
    def __init__(self, specs, model=None, constant=None):
        self.specs = list(specs)
        self.model = model
        self.constant = constant

    def prob_feature_map(self, feature_map: dict[str, np.ndarray]) -> np.ndarray:
        n = len(next(iter(feature_map.values()))) if feature_map else 1
        if self.constant is not None:
            return np.full(n, self.constant, dtype=float)
        X = np.column_stack([feature_map[name] for _, _, name in self.specs])
        return self.model.predict_proba(X)[:, 1]


def fit_dense(train: pd.DataFrame, schema: dict):
    models = {}
    for node_index, node in enumerate(schema["order"]):
        if node in ANCHORS:
            continue
        X, y, specs, _ = sel.design(train, schema["order"], node)
        if len(y) == 0 or len(np.unique(y)) < 2 or X.shape[1] == 0:
            p = float(np.mean(y)) if len(y) else 0.5
            models[node] = DenseLocalModel(specs, constant=float(np.clip(p, 0.001, 0.999)))
            continue
        model = HistGradientBoostingClassifier(
            loss="log_loss",
            learning_rate=0.07,
            max_iter=80,
            max_leaf_nodes=15,
            min_samples_leaf=30,
            l2_regularization=1.0,
            random_state=84000 + node_index,
        )
        model.fit(X, y)
        models[node] = DenseLocalModel(specs, model=model)
    return models


def anchors_with_ids(df: pd.DataFrame, schema: dict):
    data = df.sort_values(["trajectory_id", "time"]).reset_index(drop=True)
    ids = np.array(sorted(data["trajectory_id"].unique()))
    h = int(schema["horizon"])
    if len(data) != len(ids) * h:
        raise RuntimeError("trajectory rows are not complete horizon blocks")
    expected = np.repeat(ids, h)
    if not np.array_equal(data["trajectory_id"].to_numpy(), expected):
        raise RuntimeError("trajectory rows are not ordered into complete blocks")
    times = np.tile(np.arange(h), len(ids))
    if not np.array_equal(data["time"].to_numpy(), times):
        raise RuntimeError("trajectory time grid mismatch")
    anchors = data[ANCHORS].to_numpy(np.int8).reshape(len(ids), h, len(ANCHORS))
    return ids, anchors


def simulate_final(models, schema: dict, anchors: np.ndarray, intervention_control, intervention_value, uniforms: np.ndarray):
    order = schema["order"]
    nonanchors = [node for node in order if node not in ANCHORS]
    n = len(anchors)
    h = int(schema["horizon"])
    if uniforms.shape != (n, h, len(nonanchors)):
        raise ValueError("uniform shape mismatch")
    previous = {node: np.zeros(n, dtype=np.int8) for node in order}
    final_y = None
    for t in range(h):
        current = {anchor: anchors[:, t, i].astype(np.int8) for i, anchor in enumerate(ANCHORS)}
        for k, node in enumerate(nonanchors):
            if node == intervention_control:
                value = np.full(n, int(intervention_value), dtype=np.int8)
            else:
                model = models[node]
                fmap = {}
                for source, lag, name in model.specs:
                    fmap[name] = current[source] if lag == 0 else previous[source]
                probability = model.prob_feature_map(fmap)
                value = (uniforms[:, t, k] < probability).astype(np.int8)
            current[node] = value
        final_y = current[schema["target"]].copy()
        previous = {node: current[node] for node in order}
    return final_y


def intervention_effects(models, schema: dict, anchors: np.ndarray, world: str, model_name: str):
    n = len(anchors)
    expanded = np.repeat(anchors, MC_REPS, axis=0)
    h = int(schema["horizon"])
    nonanchors = [node for node in schema["order"] if node not in ANCHORS]
    rows = []
    for control in schema["controls"]:
        seed = stable_seed(f"V3-SS-CONF-001|effects|{world}|{model_name}|{control}")
        rng = np.random.default_rng(seed)
        uniforms = rng.random((n * MC_REPS, h, len(nonanchors)), dtype=np.float64)
        y0 = simulate_final(models, schema, expanded, control, 0, uniforms).astype(float).reshape(n, MC_REPS)
        y1 = simulate_final(models, schema, expanded, control, 1, uniforms).astype(float).reshape(n, MC_REPS)
        unit_diff = (y0 - y1).mean(axis=1)
        rows.append({
            "world": world,
            "model": model_name,
            "control": control,
            "risk_do0": float(y0.mean()),
            "risk_do1": float(y1.mean()),
            "risk_reduction": float(unit_diff.mean()),
            "mc_se_across_anchor_units": float(unit_diff.std(ddof=1) / math.sqrt(n)),
            "anchor_units": int(n),
            "mc_reps_per_anchor": MC_REPS,
        })
    return rows


def association_effects(train: pd.DataFrame, schema: dict, world: str):
    end = train[train.time == schema["horizon"] - 1].copy()
    features = ["R"] + list(schema["controls"])
    X = end[features].to_numpy(float)
    y = end[schema["target"]].to_numpy(int)
    if len(np.unique(y)) < 2:
        p = float(np.mean(y))
        return [{
            "world": world,
            "model": "Observational_Association",
            "control": c,
            "risk_do0": p,
            "risk_do1": p,
            "risk_reduction": 0.0,
            "mc_se_across_anchor_units": None,
            "anchor_units": int(len(end)),
            "mc_reps_per_anchor": None,
        } for c in schema["controls"]]
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=500, fit_intercept=True, random_state=0)
    model.fit(X, y)
    rows = []
    for control in schema["controls"]:
        j = features.index(control)
        X0 = X.copy(); X0[:, j] = 0.0
        X1 = X.copy(); X1[:, j] = 1.0
        p0 = model.predict_proba(X0)[:, 1]
        p1 = model.predict_proba(X1)[:, 1]
        rows.append({
            "world": world,
            "model": "Observational_Association",
            "control": control,
            "risk_do0": float(p0.mean()),
            "risk_do1": float(p1.mean()),
            "risk_reduction": float((p0 - p1).mean()),
            "mc_se_across_anchor_units": None,
            "anchor_units": int(len(end)),
            "mc_reps_per_anchor": None,
        })
    return rows


def prospective_predictions(models, schema: dict, test: pd.DataFrame, world: str, model_name: str):
    ids, anchors = anchors_with_ids(test, schema)
    n = len(ids)
    expanded = np.repeat(anchors, MC_REPS, axis=0)
    nonanchors = [node for node in schema["order"] if node not in ANCHORS]
    seed = stable_seed(f"V3-SS-CONF-001|prediction|{world}|{model_name}")
    rng = np.random.default_rng(seed)
    uniforms = rng.random((n * MC_REPS, schema["horizon"], len(nonanchors)), dtype=np.float64)
    y = simulate_final(models, schema, expanded, None, 0, uniforms).astype(float).reshape(n, MC_REPS)
    return ids, y.mean(axis=1)


def public_diagnostics(train: pd.DataFrame, test: pd.DataFrame, schema: dict):
    h = int(schema["horizon"])
    out = {
        "train_y_prevalence_final": float(train[train.time == h - 1][schema["target"]].mean()),
        "test_y_prevalence_final": float(test[test.time == h - 1][schema["target"]].mean()),
        "anchor_prevalence_train": {a: float(train[a].mean()) for a in ANCHORS},
        "anchor_prevalence_test": {a: float(test[a].mean()) for a in ANCHORS},
        "control_overall_prevalence_train": {c: float(train[c].mean()) for c in schema["controls"]},
        "control_final_prevalence_train": {c: float(train[train.time == h - 1][c].mean()) for c in schema["controls"]},
        "positivity_time_R_strata_minmax": {},
    }
    for c in schema["controls"]:
        vals = []
        for (_, _), group in train.groupby(["time", "R"], sort=True):
            if len(group) >= 20:
                vals.append(float(group[c].mean()))
        out["positivity_time_R_strata_minmax"][c] = {
            "min": float(min(vals)) if vals else None,
            "max": float(max(vals)) if vals else None,
            "eligible_strata": len(vals),
        }
    _, a_train = anchors_with_ids(train, schema)
    _, a_test = anchors_with_ids(test, schema)
    out["all_zero_anchor_units_train"] = int(np.sum(np.all(a_train == 0, axis=(1, 2))))
    out["all_zero_anchor_units_test"] = int(np.sum(np.all(a_test == 0, axis=(1, 2))))
    return out


def run_world(public_root: Path, frozen_estimator: Path, world: str, outroot: Path):
    if sha256_file(frozen_estimator) != EXPECTED_FROZEN_ESTIMATOR_SHA256:
        raise RuntimeError("frozen estimator SHA-256 mismatch")
    frozen = json.loads(frozen_estimator.read_text())
    if frozen["max_parents"] != EXPECTED_CAP or frozen["screening_C"] != 0.05 or frozen["local_model_C"] != 0.7:
        raise RuntimeError("frozen estimator configuration mismatch")
    if frozen["intervention_mc_reps_per_anchor"] != MC_REPS or frozen["confirmatory_tuning_allowed"]:
        raise RuntimeError("frozen confirmatory settings mismatch")

    pub = public_root / world
    if not pub.is_dir() or not world.startswith("confirm_"):
        raise RuntimeError(f"invalid confirmatory public world: {world}")
    schema = json.loads((pub / "schema.json").read_text())
    train = pd.read_csv(pub / "train.csv")
    test = pd.read_csv(pub / "test.csv")
    if train.trajectory_id.nunique() != 1100 or test.trajectory_id.nunique() != 400:
        raise RuntimeError("confirmatory train/test unit count mismatch")

    all_public = pd.concat([train, test], ignore_index=True)
    _, all_anchors = anchors_with_ids(all_public, schema)

    t0 = time.time()
    dchag = sel.fit_world(train, schema, EXPECTED_CAP)
    dchag_fit_seconds = time.time() - t0
    t0 = time.time()
    dense = fit_dense(train, schema)
    dense_fit_seconds = time.time() - t0

    effect_rows = []
    effect_rows.extend(intervention_effects(dchag, schema, all_anchors, world, "DCHAG_Learned"))
    effect_rows.extend(intervention_effects(dense, schema, all_anchors, world, "Dense_Sequential_GFormula"))
    effect_rows.extend(association_effects(train, schema, world))

    ids1, p1 = prospective_predictions(dchag, schema, test, world, "DCHAG_Learned")
    ids2, p2 = prospective_predictions(dense, schema, test, world, "Dense_Sequential_GFormula")
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
    write_json(out / "learned_edges.json", [list(edge) for edge in sel.selected_edges(dchag)])
    write_json(out / "public_diagnostics.json", public_diagnostics(train, test, schema))
    write_json(out / "prediction_metrics.json", {
        "world": world,
        "train_final_y_prevalence": train_prev,
        "reference_brier": ref_brier,
        "DCHAG_Learned": {"brier": brier1, "bss": 1.0 - brier1 / ref_brier if ref_brier > 0 else None},
        "Dense_Sequential_GFormula": {"brier": brier2, "bss": 1.0 - brier2 / ref_brier if ref_brier > 0 else None},
    })
    write_json(out / "run_metadata.json", {
        "experiment_id": "V3-SS-CONF-001",
        "world": world,
        "family": schema["family"],
        "frozen_estimator_sha256": EXPECTED_FROZEN_ESTIMATOR_SHA256,
        "max_parents": EXPECTED_CAP,
        "dchag_fit_seconds": dchag_fit_seconds,
        "dense_fit_seconds": dense_fit_seconds,
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
    write_json(out / "freeze_manifest.json", {
        "status": "estimation_outputs_frozen_before_private_scoring",
        "world": world,
        "files": {name: sha256_file(out / name) for name in frozen_files},
        "public_inputs": {
            "schema.json": sha256_file(pub / "schema.json"),
            "train.csv": sha256_file(pub / "train.csv"),
            "test.csv": sha256_file(pub / "test.csv"),
        },
        "frozen_estimator_sha256": EXPECTED_FROZEN_ESTIMATOR_SHA256,
    })
    print(json.dumps({"world": world, "status": "FROZEN", "max_parents": EXPECTED_CAP}, sort_keys=True))


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
