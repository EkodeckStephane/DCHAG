from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

BOOTSTRAP_REPS = 10000
BOOTSTRAP_SEED = 20260822
MODELS = ["DCHAG_Learned", "Dense_Sequential_GFormula", "Observational_Association"]


def sha256_file(path: str | Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def safe_rank(true_effects: dict[str, float], estimates: dict[str, float]):
    controls = sorted(true_effects)
    truth = np.array([true_effects[c] for c in controls], float)
    est = np.array([estimates[c] for c in controls], float)
    kt = float(kendalltau(truth, est).statistic)
    sp = float(spearmanr(truth, est).statistic)
    if not np.isfinite(kt):
        kt = 0.0
    if not np.isfinite(sp):
        sp = 0.0
    best = controls[int(np.argmax(truth))]
    selected = controls[int(np.argmax(est))]
    regret = float((true_effects[best] - true_effects[selected]) / max(abs(true_effects[best]), 1e-12))
    return kt, sp, best, selected, selected == best, regret


def edge_metrics(estimated, truth):
    est = {tuple(x) for x in estimated}
    tru = {tuple(x) for x in truth}
    tp = len(est & tru)
    precision = tp / len(est) if est else 0.0
    recall = tp / len(tru) if tru else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "learned_edges": len(est),
        "true_edges": len(tru),
        "edge_precision": precision,
        "edge_recall": recall,
        "edge_f1": f1,
    }


def verify_estimation_world(world_dir: Path):
    manifest = json.loads((world_dir / "freeze_manifest.json").read_text())
    if manifest["status"] != "estimation_outputs_frozen_before_private_scoring":
        raise RuntimeError(f"invalid freeze status for {world_dir.name}")
    for name, expected in manifest["files"].items():
        actual = sha256_file(world_dir / name)
        if actual != expected:
            raise RuntimeError(f"freeze hash mismatch {world_dir.name}/{name}: {actual} != {expected}")
    return manifest


def family_from_world(world: str) -> str:
    if world.startswith("confirm_helpdesk_identity_"):
        return "helpdesk_identity"
    if world.startswith("confirm_bec_payment_"):
        return "bec_payment"
    if world.startswith("confirm_exfiltration_"):
        return "exfiltration"
    if world.startswith("confirm_itot_change_"):
        return "itot_change"
    raise RuntimeError(f"unknown confirmatory family: {world}")


def exact_signflip_p(diffs: np.ndarray) -> float:
    diffs = np.asarray(diffs, float)
    obs = abs(float(diffs.mean()))
    extreme = 0
    total = 1 << len(diffs)
    for mask in range(total):
        signs = np.array([1.0 if (mask >> i) & 1 else -1.0 for i in range(len(diffs))])
        if abs(float(np.mean(signs * diffs))) >= obs - 1e-15:
            extreme += 1
    return extreme / total


def bootstrap_ci(diffs: np.ndarray):
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(diffs)
    samples = np.empty(BOOTSTRAP_REPS, float)
    for b in range(BOOTSTRAP_REPS):
        idx = rng.integers(0, n, size=n)
        samples[b] = float(np.mean(diffs[idx]))
    return float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--estimation-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    worlds = sorted(p.name for p in args.estimation_root.iterdir() if p.is_dir() and p.name.startswith("confirm_"))
    private_worlds = sorted(p.name for p in args.private_root.iterdir() if p.is_dir() and p.name.startswith("confirm_"))
    if worlds != private_worlds or len(worlds) != 16:
        raise RuntimeError(f"confirmatory world mismatch: estimation={len(worlds)}, private={len(private_worlds)}")

    accuracy_rows = []
    world_rows = []
    edge_rows = []
    diagnostics = {}

    for world in worlds:
        epath = args.estimation_root / world
        ppath = args.private_root / world
        verify_estimation_world(epath)
        effects = pd.read_csv(epath / "effect_estimates.csv")
        oracle = json.loads((ppath / "oracle_effects.json").read_text())
        true_edges = json.loads((ppath / "true_edges.json").read_text())
        prediction_metrics = json.loads((epath / "prediction_metrics.json").read_text())
        public_diag = json.loads((epath / "public_diagnostics.json").read_text())
        metadata = json.loads((epath / "run_metadata.json").read_text())
        if metadata["estimator_private_SCM_access"] or metadata["confirmatory_hyperparameter_tuning"] or metadata["confirmatory_world_replacement"]:
            raise RuntimeError(f"guardrail violation in {world}")

        true_effects = {c: float(oracle[c]["risk_reduction"]) for c in sorted(oracle)}
        family = family_from_world(world)
        diagnostics[world] = {"family": family, "public": public_diag}

        for model in MODELS:
            q = effects[effects.model == model].copy()
            if set(q.control) != set(true_effects):
                raise RuntimeError(f"effect control mismatch {world} {model}")
            estimates = {str(r.control): float(r.risk_reduction) for _, r in q.iterrows()}
            signed = np.array([estimates[c] - true_effects[c] for c in sorted(true_effects)], float)
            for c in sorted(true_effects):
                r = q[q.control == c].iloc[0]
                accuracy_rows.append({
                    "world": world,
                    "family": family,
                    "model": model,
                    "control": c,
                    "estimated_effect": estimates[c],
                    "true_effect": true_effects[c],
                    "signed_error": estimates[c] - true_effects[c],
                    "abs_error": abs(estimates[c] - true_effects[c]),
                    "estimated_risk_do0": float(r.risk_do0),
                    "estimated_risk_do1": float(r.risk_do1),
                })
            kt, sp, best, selected, correct, regret = safe_rank(true_effects, estimates)
            row = {
                "world": world,
                "family": family,
                "model": model,
                "effect_mae": float(np.mean(np.abs(signed))),
                "signed_bias": float(np.mean(signed)),
                "kendall": kt,
                "spearman": sp,
                "true_best_control": best,
                "selected_control": selected,
                "top_control_correct": bool(correct),
                "normalized_regret": regret,
                "brier": None,
                "bss": None,
            }
            if model in {"DCHAG_Learned", "Dense_Sequential_GFormula"}:
                row["brier"] = float(prediction_metrics[model]["brier"])
                bss = prediction_metrics[model]["bss"]
                row["bss"] = float(bss) if bss is not None else None
            if model == "DCHAG_Learned":
                em = edge_metrics(json.loads((epath / "learned_edges.json").read_text()), true_edges)
                row.update(em)
                edge_rows.append({"world": world, "family": family, **em})
            world_rows.append(row)

    accuracy = pd.DataFrame(accuracy_rows)
    world_metrics = pd.DataFrame(world_rows)
    edge_df = pd.DataFrame(edge_rows)
    accuracy.to_csv(args.outdir / "effect_accuracy.csv", index=False)
    world_metrics.to_csv(args.outdir / "world_metrics.csv", index=False)
    edge_df.to_csv(args.outdir / "dchag_edge_metrics.csv", index=False)

    summary_rows = []
    for model in MODELS:
        q = world_metrics[world_metrics.model == model]
        summary_rows.append({
            "model": model,
            "n_worlds": int(len(q)),
            "effect_mae": float(q.effect_mae.mean()),
            "signed_bias": float(q.signed_bias.mean()),
            "kendall": float(q.kendall.mean()),
            "spearman": float(q.spearman.mean()),
            "top_control_accuracy": float(q.top_control_correct.mean()),
            "normalized_regret": float(q.normalized_regret.mean()),
            "brier": float(q.brier.dropna().mean()) if q.brier.notna().any() else None,
            "bss": float(q.bss.dropna().mean()) if q.bss.notna().any() else None,
        })
    model_summary = pd.DataFrame(summary_rows)
    model_summary.to_csv(args.outdir / "model_summary.csv", index=False)

    family_rows = []
    for family in sorted(world_metrics.family.unique()):
        for model in MODELS:
            q = world_metrics[(world_metrics.family == family) & (world_metrics.model == model)]
            family_rows.append({
                "family": family,
                "model": model,
                "n_worlds": int(len(q)),
                "effect_mae": float(q.effect_mae.mean()),
                "signed_bias": float(q.signed_bias.mean()),
                "kendall": float(q.kendall.mean()),
                "spearman": float(q.spearman.mean()),
                "top_control_accuracy": float(q.top_control_correct.mean()),
                "normalized_regret": float(q.normalized_regret.mean()),
            })
    pd.DataFrame(family_rows).to_csv(args.outdir / "family_summary.csv", index=False)

    pivot = world_metrics.pivot(index="world", columns="model", values="effect_mae")
    diffs = (pivot["DCHAG_Learned"] - pivot["Dense_Sequential_GFormula"]).to_numpy(float)
    lo, hi = bootstrap_ci(diffs)
    paired = {
        "n_independent_worlds": 16,
        "mean_dchag_minus_dense_effect_mae": float(diffs.mean()),
        "bootstrap_reps": BOOTSTRAP_REPS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap95_low": lo,
        "bootstrap95_high": hi,
        "exact_signflip_assignments": 65536,
        "exact_two_sided_signflip_p": exact_signflip_p(diffs),
    }
    write_json(args.outdir / "paired_dchag_dense_inference.json", paired)
    write_json(args.outdir / "public_diagnostics.json", diagnostics)

    dchag = next(x for x in summary_rows if x["model"] == "DCHAG_Learned")
    dense = next(x for x in summary_rows if x["model"] == "Dense_Sequential_GFormula")
    assoc = next(x for x in summary_rows if x["model"] == "Observational_Association")
    result = {
        "experiment_id": "V3-SS-CONF-001",
        "status": "PASS",
        "n_confirmatory_worlds": 16,
        "models": {"DCHAG_Learned": dchag, "Dense_Sequential_GFormula": dense, "Observational_Association": assoc},
        "paired_dchag_dense_inference": paired,
        "dchag_edge_summary": {
            "precision": float(edge_df.edge_precision.mean()),
            "recall": float(edge_df.edge_recall.mean()),
            "f1": float(edge_df.edge_f1.mean()),
            "learned_edges": float(edge_df.learned_edges.mean()),
        },
        "guardrails": {
            "confirmatory_hyperparameter_tuning": False,
            "confirmatory_world_replacement": False,
            "estimator_private_SCM_access": False,
            "attack_or_red_team_labels_read": False,
            "LANL_defensive_intervention_inferred": False,
            "real_anchor_treated_as_causal_truth": False,
            "hidden_confounder_present": False,
            "estimation_outputs_frozen_before_private_scoring": True,
        },
        "claim_boundary": "Causal-effect recovery evidence applies only to the explicit real-trajectory-anchored semi-synthetic SCM benchmark, not to LANL causal effects or real control effectiveness.",
    }
    write_json(args.outdir / "SEMISYNTHETIC_CONFIRMATORY_RESULTS.json", result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
