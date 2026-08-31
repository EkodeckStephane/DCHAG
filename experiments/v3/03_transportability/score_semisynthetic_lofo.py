from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy.stats import kendalltau, spearmanr

EXPERIMENT_ID = "V3-SS-LOFO-001"
FAMILIES = ["bec_payment", "exfiltration", "helpdesk_identity", "itot_change"]
MODELS = ["DCHAG_LOFO", "Dense_LOFO"]
RQ1_MODEL_MAP = {"DCHAG_LOFO": "DCHAG_Learned", "Dense_LOFO": "Dense_Sequential_GFormula"}
BOOTSTRAP_REPS = 10000
BOOTSTRAP_SEED = 20260823


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def family_from_world(world: str) -> str:
    for family in FAMILIES:
        if world.startswith(f"confirm_{family}_"):
            return family
    raise ValueError(f"unknown world family: {world}")


def expected_worlds() -> list[str]:
    return sorted(f"confirm_{family}_{i}" for family in FAMILIES for i in range(1, 5))


def verify_fold_estimation(fold_dir: Path) -> tuple[str, dict]:
    manifest_path = fold_dir / "FREEZE_MANIFEST.json"
    metadata_path = fold_dir / "run_metadata.json"
    if not manifest_path.is_file() or not metadata_path.is_file():
        raise RuntimeError(f"fold freeze metadata missing: {fold_dir}")
    manifest = json.loads(manifest_path.read_text())
    metadata = json.loads(metadata_path.read_text())
    if manifest.get("experiment_id") != EXPERIMENT_ID or metadata.get("experiment_id") != EXPERIMENT_ID:
        raise RuntimeError("LOFO estimation experiment ID mismatch")
    family = manifest.get("heldout_family")
    if family not in FAMILIES or metadata.get("heldout_family") != family:
        raise RuntimeError("LOFO held-out family mismatch in frozen output")
    if manifest.get("estimator_private_SCM_access") is not False:
        raise RuntimeError("private SCM access guardrail failed")
    if manifest.get("target_endogenous_or_outcome_data_used_for_fit") is not False:
        raise RuntimeError("target outcome fitting guardrail failed")
    if manifest.get("target_family_used_for_hyperparameter_selection") is not False:
        raise RuntimeError("target hyperparameter guardrail failed")
    if manifest.get("frozen_before_private_scoring") is not True:
        raise RuntimeError("freeze-before-private-scoring guardrail failed")
    if metadata.get("source_train_trajectories") != 13200:
        raise RuntimeError("source training trajectory count mismatch")
    if metadata.get("target_endogenous_or_outcome_data_used_for_fit") is not False:
        raise RuntimeError("target endogenous access mismatch")
    if metadata.get("private_SCM_or_oracle_access") is not False:
        raise RuntimeError("private oracle access mismatch")
    if metadata.get("target_family_used_for_hyperparameter_selection") is not False:
        raise RuntimeError("target family tuning mismatch")
    files = dict(manifest.get("files", {}))
    expected_names = {"effect_estimates.csv", "target_predictions.csv", "dchag_source_edges.json", "run_metadata.json"}
    if set(files) != expected_names:
        raise RuntimeError(f"unexpected frozen fold file set for {family}: {set(files)}")
    for name, digest in files.items():
        p = fold_dir / name
        if not p.is_file() or sha256_file(p) != digest:
            raise RuntimeError(f"frozen fold hash mismatch: {family}/{name}")
    return family, metadata


def discover_folds(root: Path) -> dict[str, Path]:
    found = {}
    for manifest_path in root.rglob("FREEZE_MANIFEST.json"):
        fold_dir = manifest_path.parent
        family, _ = verify_fold_estimation(fold_dir)
        if family in found:
            raise RuntimeError(f"duplicate LOFO fold for {family}")
        found[family] = fold_dir
    if sorted(found) != sorted(FAMILIES):
        raise RuntimeError(f"expected four frozen LOFO folds, found {sorted(found)}")
    return found


def score_edges(estimated_edges, true_edges) -> dict:
    estimated = {tuple(x) for x in estimated_edges}
    truth = {tuple(x) for x in true_edges}
    tp = len(estimated & truth)
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


def ranking_metrics(truth: dict[str, float], estimates: dict[str, float]) -> dict:
    controls = sorted(truth)
    y = np.array([truth[c] for c in controls], dtype=float)
    p = np.array([estimates[c] for c in controls], dtype=float)
    k = float(kendalltau(y, p).statistic)
    s = float(spearmanr(y, p).statistic)
    true_best = controls[int(np.argmax(y))]
    selected = controls[int(np.argmax(p))]
    denom = max(abs(float(truth[true_best])), 1e-12)
    regret = float((truth[true_best] - truth[selected]) / denom)
    return {
        "kendall": k,
        "spearman": s,
        "true_best_control": true_best,
        "selected_control": selected,
        "top_control_correct": selected == true_best,
        "normalized_regret": regret,
    }


def exact_family_signflip(family_differences: np.ndarray) -> dict:
    x = np.asarray(family_differences, dtype=float)
    if x.shape != (4,):
        raise ValueError("family sign-flip requires exactly four family differences")
    observed = float(x.mean())
    stats = []
    for signs in itertools.product([-1.0, 1.0], repeat=4):
        stats.append(float(np.mean(x * np.asarray(signs))))
    stats = np.asarray(stats)
    p = float(np.mean(np.abs(stats) >= abs(observed) - 1e-15))
    return {
        "observed_mean_difference": observed,
        "assignments": 16,
        "exact_two_sided_p_descriptive": p,
    }


def hierarchical_bootstrap(diff_df: pd.DataFrame) -> dict:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    fams = np.array(sorted(FAMILIES), dtype=object)
    by_family = {fam: diff_df.loc[diff_df["family"] == fam, "difference"].to_numpy(float) for fam in fams}
    if any(len(v) != 4 for v in by_family.values()):
        raise RuntimeError("hierarchical bootstrap requires four worlds in each family")
    draws = np.empty(BOOTSTRAP_REPS, dtype=float)
    for b in range(BOOTSTRAP_REPS):
        selected_families = rng.choice(fams, size=4, replace=True)
        values = []
        for fam in selected_families:
            values.extend(rng.choice(by_family[fam], size=4, replace=True).tolist())
        draws[b] = float(np.mean(values))
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {
        "reps": BOOTSTRAP_REPS,
        "seed": BOOTSTRAP_SEED,
        "ci_95": [float(lo), float(hi)],
        "bootstrap_mean": float(draws.mean()),
        "method": "resample four held-out families with replacement, then four target worlds within each selected family",
        "interpretation": "descriptive uncertainty for locked secondary analysis; not fresh-confirmatory Type-I-error-controlled evidence",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--estimations-root", required=True)
    parser.add_argument("--public-root", required=True)
    parser.add_argument("--private-root", required=True)
    parser.add_argument("--rq1-world-metrics", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    estimations_root = Path(args.estimations_root)
    public_root = Path(args.public_root)
    private_root = Path(args.private_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    folds = discover_folds(estimations_root)
    worlds = expected_worlds()

    effect_parts = []
    prediction_parts = []
    metadata = {}
    edges_by_family = {}
    for family, fold_dir in sorted(folds.items()):
        _, md = verify_fold_estimation(fold_dir)
        metadata[family] = md
        effects = pd.read_csv(fold_dir / "effect_estimates.csv")
        predictions = pd.read_csv(fold_dir / "target_predictions.csv")
        if sorted(effects["world"].unique()) != [f"confirm_{family}_{i}" for i in range(1, 5)]:
            raise RuntimeError(f"effect target-world mismatch for {family}")
        if sorted(predictions["world"].unique()) != [f"confirm_{family}_{i}" for i in range(1, 5)]:
            raise RuntimeError(f"prediction target-world mismatch for {family}")
        if set(effects["model"]) != set(MODELS):
            raise RuntimeError(f"LOFO model set mismatch for {family}")
        if len(effects) != 32 or len(predictions) != 1600:
            raise RuntimeError(f"LOFO frozen row-count mismatch for {family}")
        if not (effects["anchor_units"] == 1500).all() or not (effects["mc_reps_per_anchor"] == 100).all():
            raise RuntimeError(f"LOFO MC/anchor count mismatch for {family}")
        effect_parts.append(effects)
        prediction_parts.append(predictions)
        edges_by_family[family] = json.loads((fold_dir / "dchag_source_edges.json").read_text())

    effects = pd.concat(effect_parts, ignore_index=True)
    predictions = pd.concat(prediction_parts, ignore_index=True)
    if sorted(effects["world"].unique()) != worlds or effects["world"].nunique() != 16:
        raise RuntimeError("LOFO scoring does not contain exactly 16 target worlds")

    accuracy_rows = []
    edge_rows = []
    predictive = {}
    for world in worlds:
        family = family_from_world(world)
        oracle_path = private_root / world / "oracle_effects.json"
        true_edges_path = private_root / world / "true_edges.json"
        public_test_path = public_root / world / "test.csv"
        if not oracle_path.is_file() or not true_edges_path.is_file() or not public_test_path.is_file():
            raise RuntimeError(f"scoring material missing for {world}")
        oracle = json.loads(oracle_path.read_text())
        truth = {c: float(oracle[c]["risk_reduction"]) for c in sorted(oracle)}
        for _, row in effects.loc[effects["world"] == world].iterrows():
            t = truth[row["control"]]
            est = float(row["risk_reduction"])
            r = dict(row)
            r["family"] = family
            r["true_effect"] = t
            r["error"] = est - t
            r["abs_error"] = abs(est - t)
            accuracy_rows.append(r)

        edge = score_edges(edges_by_family[family], json.loads(true_edges_path.read_text()))
        edge["family"] = family
        edge["world"] = world
        edge_rows.append(edge)

        test = pd.read_csv(public_test_path)
        end = test[test["time"] == 5].sort_values("trajectory_id")
        if len(end) != 400 or not np.array_equal(end["trajectory_id"].to_numpy(int), np.arange(400)):
            raise RuntimeError(f"target test truth alignment mismatch for {world}")
        y = end["Y"].to_numpy(float)
        pred = predictions.loc[predictions["world"] == world].sort_values("trajectory_id")
        if len(pred) != 400 or not np.array_equal(pred["trajectory_id"].to_numpy(int), np.arange(400)):
            raise RuntimeError(f"frozen target prediction alignment mismatch for {world}")
        source_prev = float(metadata[family]["source_final_y_prevalence"])
        ref_brier = float(np.mean((y - source_prev) ** 2))
        predictive[world] = {}
        for model in MODELS:
            p = pred[model].to_numpy(float)
            brier = float(np.mean((y - p) ** 2))
            bss = float(1.0 - brier / ref_brier) if ref_brier > 0 else math.nan
            predictive[world][model] = {
                "brier": brier,
                "bss_source_prevalence_reference": bss,
                "source_final_y_prevalence": source_prev,
                "reference_brier": ref_brier,
            }

    accuracy = pd.DataFrame(accuracy_rows)
    edges = pd.DataFrame(edge_rows)
    accuracy.to_csv(outdir / "effect_accuracy.csv", index=False)
    edges.to_csv(outdir / "dchag_target_edge_metrics.csv", index=False)

    world_rows = []
    for world in worlds:
        family = family_from_world(world)
        oracle = json.loads((private_root / world / "oracle_effects.json").read_text())
        truth = {c: float(oracle[c]["risk_reduction"]) for c in sorted(oracle)}
        for model in MODELS:
            part = accuracy[(accuracy["world"] == world) & (accuracy["model"] == model)].copy()
            estimates = {r["control"]: float(r["risk_reduction"]) for _, r in part.iterrows()}
            ranks = ranking_metrics(truth, estimates)
            row = {
                "world": world,
                "family": family,
                "model": model,
                "effect_mae": float(part["abs_error"].mean()),
                "signed_bias": float(part["error"].mean()),
                **ranks,
                "brier": predictive[world][model]["brier"],
                "bss_source_prevalence_reference": predictive[world][model]["bss_source_prevalence_reference"],
            }
            if model == "DCHAG_LOFO":
                erow = edges.loc[edges["world"] == world].iloc[0]
                for key in ["learned_edges", "true_edges", "edge_precision", "edge_recall", "edge_f1"]:
                    row[key] = float(erow[key]) if key not in {"learned_edges", "true_edges"} else int(erow[key])
            else:
                for key in ["learned_edges", "true_edges", "edge_precision", "edge_recall", "edge_f1"]:
                    row[key] = np.nan
            world_rows.append(row)

    world_metrics = pd.DataFrame(world_rows)
    world_metrics.to_csv(outdir / "world_metrics.csv", index=False)

    numeric_summary = [
        "effect_mae", "signed_bias", "kendall", "spearman", "top_control_correct", "normalized_regret",
        "brier", "bss_source_prevalence_reference", "learned_edges", "true_edges", "edge_precision", "edge_recall", "edge_f1",
    ]
    family_summary = world_metrics.groupby(["family", "model"], as_index=False)[numeric_summary].mean(numeric_only=True)
    family_summary.to_csv(outdir / "family_summary.csv", index=False)
    model_summary = world_metrics.groupby("model", as_index=False)[numeric_summary].mean(numeric_only=True)
    model_summary.to_csv(outdir / "model_summary.csv", index=False)

    pivot = world_metrics.pivot(index=["world", "family"], columns="model", values="effect_mae").reset_index()
    pivot["difference"] = pivot["DCHAG_LOFO"] - pivot["Dense_LOFO"]
    pivot.to_csv(outdir / "paired_world_differences.csv", index=False)
    family_diffs = pivot.groupby("family", as_index=False)["difference"].mean()
    family_diffs.to_csv(outdir / "paired_family_differences.csv", index=False)
    bootstrap = hierarchical_bootstrap(pivot[["world", "family", "difference"]])
    signflip = exact_family_signflip(family_diffs.sort_values("family")["difference"].to_numpy(float))
    paired = {
        "estimand": "mean target-world causal-effect MAE_DCHAG_LOFO - MAE_Dense_LOFO",
        "global_16_world_descriptive_mean_difference": float(pivot["difference"].mean()),
        "family_mean_differences": {r["family"]: float(r["difference"]) for _, r in family_diffs.iterrows()},
        "hierarchical_bootstrap": bootstrap,
        "family_level_exact_signflip": signflip,
        "analysis_class": "locked_secondary_post_RQ1",
        "superiority_test_status": "not fresh-confirmatory; do not promote a nominal p-value as independent superiority evidence",
    }
    write_json(outdir / "paired_lofo_inference.json", paired)

    rq1 = pd.read_csv(args.rq1_world_metrics)
    rq1 = rq1[rq1["model"].isin(RQ1_MODEL_MAP.values())][["world", "model", "effect_mae"]].copy()
    rq1_map = {v: k for k, v in RQ1_MODEL_MAP.items()}
    rq1["model"] = rq1["model"].map(rq1_map)
    transfer = world_metrics[["world", "family", "model", "effect_mae"]].merge(
        rq1.rename(columns={"effect_mae": "rq1_within_world_effect_mae"}), on=["world", "model"], how="left", validate="one_to_one"
    )
    if transfer["rq1_within_world_effect_mae"].isna().any():
        raise RuntimeError("RQ1 within-world reference merge incomplete")
    transfer["transfer_penalty"] = transfer["effect_mae"] - transfer["rq1_within_world_effect_mae"]
    transfer.to_csv(outdir / "transfer_penalty.csv", index=False)
    transfer_summary = transfer.groupby(["family", "model"], as_index=False)[["effect_mae", "rq1_within_world_effect_mae", "transfer_penalty"]].mean()
    transfer_summary.to_csv(outdir / "transfer_penalty_family_summary.csv", index=False)
    t_pivot = transfer.pivot(index=["world", "family"], columns="model", values="transfer_penalty").reset_index()
    t_pivot["dchag_minus_dense_transfer_penalty"] = t_pivot["DCHAG_LOFO"] - t_pivot["Dense_LOFO"]
    t_pivot.to_csv(outdir / "paired_transfer_penalty.csv", index=False)

    guardrails = {
        "four_folds_retained": len(folds) == 4,
        "sixteen_target_worlds_retained": world_metrics["world"].nunique() == 16,
        "target_endogenous_or_outcome_data_used_for_fit": False,
        "target_family_used_for_hyperparameter_selection": False,
        "estimator_private_SCM_access": False,
        "estimation_outputs_frozen_before_private_scoring": True,
        "target_standardization_anchor_units": 1500,
        "mc_reps_per_anchor": 100,
        "confirmatory_world_replacement": False,
        "analysis_class": "locked_secondary_post_RQ1",
    }

    model_summary_dict = {}
    for _, row in model_summary.iterrows():
        model_summary_dict[row["model"]] = {
            key: (None if pd.isna(row[key]) else float(row[key]))
            for key in numeric_summary
        }
    transfer_global = transfer.groupby("model")["transfer_penalty"].mean().to_dict()

    result = {
        "experiment_id": EXPERIMENT_ID,
        "status": "PASS",
        "analysis_class": "locked_secondary_post_RQ1",
        "n_folds": 4,
        "n_target_worlds": 16,
        "models": model_summary_dict,
        "paired_dchag_dense": paired,
        "mean_transfer_penalty": {k: float(v) for k, v in transfer_global.items()},
        "dchag_minus_dense_mean_transfer_penalty": float(t_pivot["dchag_minus_dense_transfer_penalty"].mean()),
        "guardrails": guardrails,
        "software": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
        },
        "claim_boundary": "Cross-family transport evidence applies only to the explicit semi-synthetic SCM benchmark and is a locked secondary post-RQ1 analysis. It does not establish transport of causal mechanisms, attack pathways, or defensive-control effects across real organizations or LANL families.",
    }
    write_json(outdir / "SEMISYNTHETIC_LOFO_RESULTS.json", result)

    result_files = [
        outdir / "SEMISYNTHETIC_LOFO_RESULTS.json",
        outdir / "effect_accuracy.csv",
        outdir / "world_metrics.csv",
        outdir / "model_summary.csv",
        outdir / "family_summary.csv",
        outdir / "paired_world_differences.csv",
        outdir / "paired_family_differences.csv",
        outdir / "paired_lofo_inference.json",
        outdir / "dchag_target_edge_metrics.csv",
        outdir / "transfer_penalty.csv",
        outdir / "transfer_penalty_family_summary.csv",
        outdir / "paired_transfer_penalty.csv",
    ]
    (outdir / "RESULT_SHA256.txt").write_text(
        "".join(f"{sha256_file(p)}  {p.name}\n" for p in result_files), encoding="utf-8"
    )
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "status": "PASS",
        "D_LOFO": paired["global_16_world_descriptive_mean_difference"],
        "bootstrap_95_ci": bootstrap["ci_95"],
        "family_signflip_p_descriptive": signflip["exact_two_sided_p_descriptive"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
