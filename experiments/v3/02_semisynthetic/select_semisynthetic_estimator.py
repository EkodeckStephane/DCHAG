from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.stats import kendalltau, spearmanr
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

CAPS = [6, 8, 10]
SCREENING_C = 0.05
LOCAL_C = 0.7
MC_REPS = 100
ANCHORS = ["A_person", "A_process", "A_technical"]
EXPECTED_WORLDS = sorted([
    "dev_helpdesk_identity",
    "dev_bec_payment",
    "dev_exfiltration",
    "dev_itot_change",
])


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


def feature_specs(order: list[str], target: str):
    j = order.index(target)
    return (
        [(node, 0, f"{node}@0") for node in order[:j]]
        + [(node, 1, f"{node}@-1") for node in order]
    )


def design(df: pd.DataFrame, order: list[str], target: str):
    specs = feature_specs(order, target)
    data = df.sort_values(["trajectory_id", "time"]).copy()
    cols = []
    for node, lag, _ in specs:
        if lag == 0:
            cols.append(data[node].to_numpy(float))
        else:
            cols.append(
                data.groupby("trajectory_id", sort=False)[node]
                .shift(1)
                .fillna(0)
                .to_numpy(float)
            )
    return np.column_stack(cols), data[target].to_numpy(int), specs, data


def augment(X: np.ndarray, selected: list[int]) -> np.ndarray:
    if not selected:
        return np.zeros((len(X), 0), dtype=float)
    main = X[:, selected]
    parts = [main]
    for a in range(len(selected)):
        for b in range(a + 1, len(selected)):
            parts.append((main[:, a] * main[:, b])[:, None])
    return np.column_stack(parts)


@dataclass
class LocalModel:
    node: str
    specs: list
    selected: list[int]
    model: object | None
    const: float | None
    fallback: bool

    def prob_matrix(self, X: np.ndarray) -> np.ndarray:
        if self.const is not None:
            return np.full(len(X), self.const, dtype=float)
        return self.model.predict_proba(augment(X, self.selected))[:, 1]

    def prob_feature_map(self, feature_map: dict[str, np.ndarray]) -> np.ndarray:
        if self.const is not None:
            n = len(next(iter(feature_map.values()))) if feature_map else 1
            return np.full(n, self.const, dtype=float)
        X = np.column_stack([feature_map[name] for _, _, name in self.specs])
        return self.prob_matrix(X)


def fit_local(df: pd.DataFrame, order: list[str], node: str, cap: int) -> LocalModel:
    X, y, specs, _ = design(df, order, node)
    if y.min() == y.max():
        return LocalModel(node, specs, [], None, float(y.mean()), False)

    screening = LogisticRegression(
        penalty="l1",
        C=SCREENING_C,
        solver="liblinear",
        max_iter=500,
        fit_intercept=True,
        random_state=0,
    )
    screening.fit(X, y)
    abs_coef = np.abs(screening.coef_[0])
    nonzero = [i for i, value in enumerate(abs_coef) if value > 1e-12]
    fallback = False

    if nonzero:
        selected = sorted(nonzero, key=lambda i: (-abs_coef[i], specs[i][2]))[:cap]
    else:
        mi = mutual_info_classif(X, y, discrete_features=True, random_state=0)
        selected = sorted(range(len(mi)), key=lambda i: (-mi[i], specs[i][2]))[:cap]
        fallback = True

    Z = augment(X, selected)
    if Z.shape[1] == 0:
        return LocalModel(node, specs, [], None, float(y.mean()), fallback)

    local = LogisticRegression(
        C=LOCAL_C,
        solver="lbfgs",
        max_iter=500,
        fit_intercept=True,
        random_state=0,
    )
    local.fit(Z, y)
    return LocalModel(node, specs, selected, local, None, fallback)


def fit_world(train: pd.DataFrame, schema: dict, cap: int):
    return {
        node: fit_local(train, schema["order"], node, cap)
        for node in schema["order"]
        if node not in ANCHORS
    }


def selected_edges(models: dict[str, LocalModel]):
    edges = []
    for target, model in models.items():
        for i in model.selected:
            source, lag, _ = model.specs[i]
            edges.append((source, lag, target))
    return sorted(set(edges))


def anchor_tensor(public_all: pd.DataFrame, horizon: int) -> np.ndarray:
    data = public_all.sort_values(["trajectory_id", "time"])
    ids = sorted(data.trajectory_id.unique())
    out = np.zeros((len(ids), horizon, len(ANCHORS)), dtype=np.int8)
    index = {trajectory_id: i for i, trajectory_id in enumerate(ids)}
    for _, row in data[["trajectory_id", "time"] + ANCHORS].iterrows():
        out[index[row.trajectory_id], int(row.time), :] = [int(row[a]) for a in ANCHORS]
    return out


def simulate(models, schema, anchors, intervention_control, intervention_value, uniforms):
    order = schema["order"]
    nonanchors = [node for node in order if node not in ANCHORS]
    n = len(anchors)
    previous = {node: np.zeros(n, dtype=np.int8) for node in order}
    final_y = None

    for time in range(schema["horizon"]):
        current = {
            anchor: anchors[:, time, i].astype(np.int8)
            for i, anchor in enumerate(ANCHORS)
        }
        for k, node in enumerate(nonanchors):
            if node == intervention_control:
                value = np.full(n, intervention_value, dtype=np.int8)
            else:
                model = models[node]
                fmap = {}
                for source, lag, name in model.specs:
                    fmap[name] = current[source] if lag == 0 else previous[source]
                probability = model.prob_feature_map(fmap)
                value = (uniforms[:, time, k] < probability).astype(np.int8)
            current[node] = value
        final_y = current[schema["target"]].copy()
        previous = {node: current[node] for node in order}
    return float(final_y.mean())


def effect_estimates(models, schema, anchors, world: str, cap: int):
    repeated_anchors = np.repeat(anchors, MC_REPS, axis=0)
    nonanchors = [node for node in schema["order"] if node not in ANCHORS]
    estimates = {}
    for control in schema["controls"]:
        seed = int(
            hashlib.sha256(
                f"V3-SS-SEL-001|{world}|cap{cap}|{control}".encode("utf-8")
            ).hexdigest()[:16],
            16,
        ) % (2**32)
        rng = np.random.default_rng(seed)
        uniforms = rng.random(
            (len(repeated_anchors), schema["horizon"], len(nonanchors)),
            dtype=np.float64,
        )
        risk0 = simulate(models, schema, repeated_anchors, control, 0, uniforms)
        risk1 = simulate(models, schema, repeated_anchors, control, 1, uniforms)
        estimates[control] = {
            "risk_do0": risk0,
            "risk_do1": risk1,
            "risk_reduction": risk0 - risk1,
        }
    return estimates


def rank_metrics(true_effects: dict[str, float], estimates: dict[str, float]):
    controls = sorted(true_effects)
    truth = np.array([true_effects[c] for c in controls], dtype=float)
    estimate = np.array([estimates[c] for c in controls], dtype=float)
    kendall = float(kendalltau(truth, estimate).statistic)
    spearman = float(spearmanr(truth, estimate).statistic)
    best = controls[int(np.argmax(truth))]
    selected = controls[int(np.argmax(estimate))]
    regret = float(
        (true_effects[best] - true_effects[selected])
        / max(abs(true_effects[best]), 1e-12)
    )
    return {
        "kendall": kendall,
        "spearman": spearman,
        "top_control_true": best,
        "top_control_selected": selected,
        "top_control_correct": selected == best,
        "normalized_regret": regret,
    }


def final_y_brier(models, test: pd.DataFrame, schema: dict) -> float:
    model = models[schema["target"]]
    X, y, _, data = design(test, schema["order"], schema["target"])
    mask = data["time"].to_numpy() == schema["horizon"] - 1
    probability = model.prob_matrix(X[mask])
    return float(brier_score_loss(y[mask], probability))


def score_edges(estimated_edges, true_edges):
    truth = {tuple(edge) for edge in true_edges}
    estimated = set(estimated_edges)
    tp = len(truth & estimated)
    precision = tp / len(estimated) if estimated else 0.0
    recall = tp / len(truth) if truth else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "learned_edges": len(estimated),
        "true_edges": len(truth),
        "edge_precision": precision,
        "edge_recall": recall,
        "edge_f1": f1,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-root", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    root = Path(args.dev_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    worlds = sorted(
        p.name for p in (root / "public").iterdir()
        if p.is_dir() and p.name.startswith("dev_")
    )
    if worlds != EXPECTED_WORLDS:
        raise RuntimeError(f"unexpected development worlds: {worlds}")

    rows = []
    details = {}
    for cap in CAPS:
        details[str(cap)] = {}
        for world in worlds:
            schema = json.loads((root / "public" / world / "schema.json").read_text())
            train = pd.read_csv(root / "public" / world / "train.csv")
            test = pd.read_csv(root / "public" / world / "test.csv")
            public_all = pd.concat([train, test], ignore_index=True)

            models = fit_world(train, schema, cap)
            edges = selected_edges(models)
            anchors = anchor_tensor(public_all, schema["horizon"])
            effects = effect_estimates(models, schema, anchors, world, cap)

            oracle = json.loads((root / "private" / world / "oracle_effects.json").read_text())
            true_effects = {
                c: float(oracle[c]["risk_reduction"])
                for c in schema["controls"]
            }
            estimates = {
                c: float(effects[c]["risk_reduction"])
                for c in schema["controls"]
            }
            errors = np.array(
                [estimates[c] - true_effects[c] for c in schema["controls"]],
                dtype=float,
            )
            ranking = rank_metrics(true_effects, estimates)
            edge_metrics = score_edges(
                edges,
                json.loads((root / "private" / world / "true_edges.json").read_text()),
            )
            record = {
                "cap": cap,
                "world": world,
                "effect_mae": float(np.mean(np.abs(errors))),
                "signed_bias": float(np.mean(errors)),
                "brier_final_y": final_y_brier(models, test, schema),
                "mi_fallback_nodes": sum(int(model.fallback) for model in models.values()),
                **ranking,
                **edge_metrics,
            }
            rows.append(record)
            details[str(cap)][world] = {
                "effects": effects,
                "oracle": oracle,
                "metrics": record,
                "learned_edges": [list(edge) for edge in edges],
            }

    world_metrics = pd.DataFrame(rows)
    candidates = []
    for cap in CAPS:
        current = world_metrics[world_metrics.cap == cap]
        candidates.append({
            "cap": cap,
            "primary_mean_world_effect_mae": float(current.effect_mae.mean()),
            "mean_signed_bias": float(current.signed_bias.mean()),
            "mean_kendall": float(current.kendall.mean()),
            "mean_spearman": float(current.spearman.mean()),
            "top_control_accuracy": float(current.top_control_correct.mean()),
            "mean_normalized_regret": float(current.normalized_regret.mean()),
            "mean_edge_f1": float(current.edge_f1.mean()),
            "mean_brier_final_y": float(current.brier_final_y.mean()),
            "total_mi_fallback_nodes": int(current.mi_fallback_nodes.sum()),
        })
    candidates = sorted(
        candidates,
        key=lambda row: (row["primary_mean_world_effect_mae"], row["cap"]),
    )
    selected_cap = candidates[0]["cap"]

    result = {
        "experiment_id": "V3-SS-SEL-001",
        "status": "PASS",
        "candidates": CAPS,
        "selection_rule": "minimum unweighted mean of four world-level effect MAEs; exact tie <=1e-12 -> smaller cap",
        "selected_max_parents": selected_cap,
        "candidate_summary": candidates,
        "world_metrics": rows,
        "software": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "code_sha256": sha256_file(__file__),
        "guardrails": {
            "confirmatory_worlds_generated": 0,
            "confirmatory_worlds_scored": 0,
            "confirmatory_hyperparameter_tuning": False,
            "estimator_private_SCM_access_during_fit": False,
            "private_development_oracle_access_only_in_scorer": True,
            "candidate_set_changed_after_inspection": False,
        },
    }
    write_json(outdir / "SEMISYNTHETIC_ESTIMATOR_SELECTION_RESULTS.json", result)
    write_json(outdir / "SEMISYNTHETIC_ESTIMATOR_SELECTION_DETAILS.json", details)
    world_metrics.to_csv(
        outdir / "SEMISYNTHETIC_ESTIMATOR_SELECTION_WORLD_METRICS.csv",
        index=False,
    )

    frozen = {
        "experiment_id": "V3-SS-SEL-001",
        "max_parents": selected_cap,
        "screening": "L1 logistic conditional screening",
        "screening_C": SCREENING_C,
        "screening_solver": "liblinear",
        "screening_max_iter": 500,
        "local_model": "logistic main effects plus all selected pairwise interactions",
        "local_model_C": LOCAL_C,
        "local_solver": "lbfgs",
        "local_max_iter": 500,
        "mi_fallback": "mutual_info_classif(discrete_features=True, random_state=0), descending MI then feature-name tie break",
        "admissible_current_slice": "public-order predecessors",
        "admissible_lag1": "full public observed history",
        "time0_lag1": 0,
        "intervention_mc_reps_per_anchor": MC_REPS,
        "selection_candidates": CAPS,
        "selection_primary_score": "unweighted mean of four development-world effect MAEs",
        "confirmatory_tuning_allowed": False,
        "selection_code_sha256": sha256_file(__file__),
        "software": result["software"],
    }
    write_json(outdir / "FROZEN_SEMISYNTHETIC_ESTIMATOR.json", frozen)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
