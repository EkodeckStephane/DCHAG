from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

EXPERIMENT_ID = "V3-SS-HC-001"
LEVELS = {"moderate": 0.50, "strong": 1.00}
MODELS = ["DCHAG_Learned", "Dense_Sequential_GFormula"]
MODEL_SHORT = {"DCHAG_Learned": "DCHAG", "Dense_Sequential_GFormula": "Dense"}
FAMILIES = ["bec_payment", "exfiltration", "helpdesk_identity", "itot_change"]
WORLDS = sorted([f"confirm_{family}_{i}" for family in FAMILIES for i in range(1, 5)])
BOOTSTRAP_REPS = 10000
BOOTSTRAP_SEED = 20260824


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


def family_from_world(world: str) -> str:
    for family in FAMILIES:
        if world.startswith(f"confirm_{family}_"):
            return family
    raise ValueError(world)


def verify_estimation_world(root: Path, level: str, world: str) -> Path:
    p = root / level / world
    if not p.is_dir():
        raise RuntimeError(f"missing frozen estimation: {level}/{world}")
    m = json.loads((p / "freeze_manifest.json").read_text())
    md = json.loads((p / "run_metadata.json").read_text())
    if m.get("status") != "estimation_outputs_frozen_before_private_scoring":
        raise RuntimeError(f"estimation not frozen: {level}/{world}")
    if int(m.get("standardization_anchor_units")) != 1500:
        raise RuntimeError("standardization anchor count mismatch")
    if md.get("selection_experiment_id") != "V3-SS-SEL-001-C1":
        raise RuntimeError("selection freeze mismatch")
    if md.get("estimator_private_SCM_access") or md.get("confirmatory_hyperparameter_tuning") or md.get("confirmatory_world_replacement"):
        raise RuntimeError("estimator guardrail mismatch")
    if int(md.get("standardization_anchor_units")) != 1500:
        raise RuntimeError("metadata anchor count mismatch")
    for name, digest in m["files"].items():
        if sha256_file(p / name) != digest:
            raise RuntimeError(f"frozen estimation hash mismatch: {level}/{world}/{name}")
    return p


def rank_metrics(true_effects: dict[str, float], estimates: dict[str, float]) -> dict:
    controls = sorted(true_effects)
    truth = np.array([true_effects[c] for c in controls], dtype=float)
    est = np.array([estimates[c] for c in controls], dtype=float)
    k = float(kendalltau(truth, est).statistic)
    s = float(spearmanr(truth, est).statistic)
    best = controls[int(np.argmax(truth))]
    selected = controls[int(np.argmax(est))]
    regret = float((true_effects[best] - true_effects[selected]) / max(abs(true_effects[best]), 1e-12))
    return {
        "kendall": k,
        "spearman": s,
        "true_best_control": best,
        "selected_control": selected,
        "top_control_correct": selected == best,
        "normalized_regret": regret,
    }


def edge_metrics(learned_path: Path, true_path: Path) -> dict:
    learned = {tuple(x) for x in json.loads(learned_path.read_text())}
    truth = {tuple(x) for x in json.loads(true_path.read_text())}
    tp = len(learned & truth)
    precision = tp / len(learned) if learned else 0.0
    recall = tp / len(truth) if truth else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "learned_edges": len(learned),
        "true_edges": len(truth),
        "edge_precision": precision,
        "edge_recall": recall,
        "edge_f1": f1,
    }


def exact_signflip(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    observed = float(values.mean())
    n = len(values)
    if n != 16:
        raise RuntimeError("exact sign-flip expects 16 independent worlds")
    means = np.empty(2**n, dtype=float)
    for i, signs in enumerate(itertools.product([-1.0, 1.0], repeat=n)):
        means[i] = float(np.mean(values * np.asarray(signs)))
    p = float(np.mean(np.abs(means) >= abs(observed) - 1e-15))
    return {"observed_mean": observed, "assignments": int(2**n), "exact_two_sided_p": p}


def bootstrap_ci(values: np.ndarray, seed: int) -> dict:
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(BOOTSTRAP_REPS, len(values)), replace=True).mean(axis=1)
    return {
        "reps": BOOTSTRAP_REPS,
        "seed": seed,
        "bootstrap_mean": float(samples.mean()),
        "ci_95": [float(x) for x in np.quantile(samples, [0.025, 0.975])],
    }


def load_rq1_baseline(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path / "world_metrics.csv")
    required = set(WORLDS)
    if set(df["world"]) != required:
        raise RuntimeError("RQ1 baseline world set mismatch")
    if not set(MODELS).issubset(set(df["model"])):
        raise RuntimeError("RQ1 baseline model set mismatch")
    return df[df["model"].isin(MODELS)].copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--estimation-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--rq1-results", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    rq1 = load_rq1_baseline(args.rq1_results)
    rq1_key = {(r.world, r.model): float(r.effect_mae) for r in rq1.itertuples()}

    world_rows = []
    effect_rows = []
    edge_rows = []
    for level_name, level_value in LEVELS.items():
        private_level = args.private_root / level_name / "private"
        if not private_level.is_dir():
            raise RuntimeError(f"missing private level root: {level_name}")
        for world in WORLDS:
            est_dir = verify_estimation_world(args.estimation_root, level_name, world)
            prv = private_level / world
            oracle = json.loads((prv / "oracle_effects.json").read_text())
            effects = pd.read_csv(est_dir / "effect_estimates.csv")
            pred = json.loads((est_dir / "prediction_metrics.json").read_text())
            true_effects = {c: float(oracle[c]["risk_reduction"]) for c in sorted(oracle)}
            for model in MODELS:
                sub = effects[effects.model == model].copy()
                if set(sub.control) != set(true_effects):
                    raise RuntimeError(f"control set mismatch: {level_name}/{world}/{model}")
                estimates = {r.control: float(r.risk_reduction) for r in sub.itertuples()}
                errors = np.array([estimates[c] - true_effects[c] for c in sorted(true_effects)], dtype=float)
                rank = rank_metrics(true_effects, estimates)
                row = {
                    "level": level_name,
                    "lambda": level_value,
                    "world": world,
                    "family": family_from_world(world),
                    "model": model,
                    "effect_mae": float(np.mean(np.abs(errors))),
                    "signed_bias": float(np.mean(errors)),
                    "brier": float(pred[model]["brier"]),
                    "bss": float(pred[model]["bss"]) if pred[model]["bss"] is not None else np.nan,
                    **rank,
                }
                if model == "DCHAG_Learned":
                    em = edge_metrics(est_dir / "learned_edges.json", prv / "true_edges.json")
                    row.update(em)
                    edge_rows.append({"level": level_name, "lambda": level_value, "world": world, "family": family_from_world(world), **em})
                world_rows.append(row)
                for c in sorted(true_effects):
                    effect_rows.append({
                        "level": level_name,
                        "lambda": level_value,
                        "world": world,
                        "family": family_from_world(world),
                        "model": model,
                        "control": c,
                        "oracle_effect": true_effects[c],
                        "estimated_effect": estimates[c],
                        "error": estimates[c] - true_effects[c],
                        "absolute_error": abs(estimates[c] - true_effects[c]),
                    })

    wm = pd.DataFrame(world_rows)
    ea = pd.DataFrame(effect_rows)
    edges = pd.DataFrame(edge_rows)
    wm.to_csv(args.outdir / "world_metrics.csv", index=False)
    ea.to_csv(args.outdir / "effect_accuracy.csv", index=False)
    edges.to_csv(args.outdir / "dchag_edge_metrics.csv", index=False)

    numeric = ["effect_mae", "signed_bias", "kendall", "spearman", "top_control_correct", "normalized_regret", "brier", "bss"]
    model_summary = wm.groupby(["level", "lambda", "model"], as_index=False)[numeric].mean()
    model_summary.to_csv(args.outdir / "model_summary.csv", index=False)
    family_summary = wm.groupby(["level", "lambda", "family", "model"], as_index=False)[numeric].mean()
    family_summary.to_csv(args.outdir / "family_summary.csv", index=False)

    penalty_rows = []
    for r in wm.itertuples():
        baseline = rq1_key[(r.world, r.model)]
        penalty_rows.append({
            "level": r.level,
            "lambda": r._2 if hasattr(r, "_2") else getattr(r, "lambda"),
            "world": r.world,
            "family": r.family,
            "model": r.model,
            "effect_mae": r.effect_mae,
            "rq1_effect_mae": baseline,
            "confounding_penalty": r.effect_mae - baseline,
        })
    penalty = pd.DataFrame(penalty_rows)
    if "lambda" not in penalty.columns:
        penalty["lambda"] = penalty["level"].map(LEVELS)
    penalty.to_csv(args.outdir / "confounding_penalty.csv", index=False)
    penalty_summary = penalty.groupby(["level", "lambda", "model"], as_index=False)[["effect_mae", "rq1_effect_mae", "confounding_penalty"]].mean()
    penalty_summary.to_csv(args.outdir / "confounding_penalty_summary.csv", index=False)

    inference = {}
    for level_name in LEVELS:
        inference[level_name] = {}
        for model in MODELS:
            vals = penalty[(penalty.level == level_name) & (penalty.model == model)].sort_values("world")["confounding_penalty"].to_numpy(float)
            inference[level_name][model] = {
                "mean_penalty": float(vals.mean()),
                "bootstrap": bootstrap_ci(vals, BOOTSTRAP_SEED + (0 if level_name == "moderate" else 10) + (0 if model == "DCHAG_Learned" else 1)),
                "exact_signflip": exact_signflip(vals),
            }
    strong_d = wm[wm.level == "strong"].pivot(index="world", columns="model", values="effect_mae")
    d = (strong_d["DCHAG_Learned"] - strong_d["Dense_Sequential_GFormula"]).to_numpy(float)
    inference["strong_dchag_minus_dense"] = {
        "mean_difference": float(d.mean()),
        "bootstrap": bootstrap_ci(d, BOOTSTRAP_SEED + 20),
        "exact_signflip": exact_signflip(d),
        "status": "secondary comparator; not the primary RQ3 endpoint",
    }
    write_json(args.outdir / "paired_hidden_confounding_inference.json", inference)

    monotonic = {}
    for model in MODELS:
        base = pd.Series({w: rq1_key[(w, model)] for w in WORLDS})
        mod = wm[(wm.level == "moderate") & (wm.model == model)].set_index("world")["effect_mae"]
        strong = wm[(wm.level == "strong") & (wm.model == model)].set_index("world")["effect_mae"]
        ok = (base <= mod) & (mod <= strong)
        monotonic[model] = {"worlds_monotonic": int(ok.sum()), "n_worlds": 16, "fraction": float(ok.mean())}

    primary = inference["strong"]["DCHAG_Learned"]
    result = {
        "experiment_id": EXPERIMENT_ID,
        "status": "PASS",
        "n_worlds": 16,
        "levels": LEVELS,
        "primary_endpoint": "strong-confounding DCHAG effect-MAE penalty relative to audited RQ1",
        "primary": primary,
        "inference": inference,
        "monotonicity": monotonic,
        "model_summary": {
            level: {
                MODEL_SHORT[model]: model_summary[(model_summary.level == level) & (model_summary.model == model)].iloc[0].to_dict()
                for model in MODELS
            }
            for level in LEVELS
        },
        "guardrails": {
            "all_32_estimation_outputs_frozen_before_private_scoring": True,
            "estimator_private_SCM_access": False,
            "hidden_confounder_observed_by_estimator": False,
            "hyperparameter_retuning": False,
            "world_or_level_replacement": False,
            "target_anchor_units_per_world": 1500,
            "mc_reps_per_anchor": 100,
        },
        "claim_boundary": "Sensitivity evidence is limited to the explicit semi-synthetic latent-confounding mechanism. PASS means protocol-complete, not robustness or superiority. No real LANL intervention or hidden-mechanism identification claim is supported.",
    }
    write_json(args.outdir / "SEMISYNTHETIC_HIDDEN_CONFOUNDING_RESULTS.json", result)
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "primary_mean_penalty": primary["mean_penalty"], "primary_ci": primary["bootstrap"]["ci_95"], "primary_p": primary["exact_signflip"]["exact_two_sided_p"]}, sort_keys=True))


if __name__ == "__main__":
    main()
