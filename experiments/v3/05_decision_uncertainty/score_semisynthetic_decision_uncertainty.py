from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

EXPERIMENT_ID = "V3-SS-DEC-001"
MODELS = ["DCHAG_Learned", "Dense_Sequential_GFormula"]
FAMILIES = ["bec_payment", "exfiltration", "helpdesk_identity", "itot_change"]
WORLDS = sorted([f"confirm_{family}_{i}" for family in FAMILIES for i in range(1, 5)])
CONTROLS = ["C1", "C2", "C3", "C4"]
BOOTSTRAP_REPS = 40
MC_REPS = 25
WORLD_BOOTSTRAP_REPS = 10000
PRIMARY_BOOTSTRAP_SEED = 20260845
COMPARATOR_BOOTSTRAP_SEED = 20260846


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


def deterministic_top(effects: dict[str, float]) -> str:
    return sorted(effects, key=lambda c: (-effects[c], c))[0]


def rank_metrics(reference: dict[str, float], estimate: dict[str, float]) -> tuple[float, float]:
    controls = sorted(reference)
    a = np.array([reference[c] for c in controls], dtype=float)
    b = np.array([estimate[c] for c in controls], dtype=float)
    return float(kendalltau(a, b).statistic), float(spearmanr(a, b).statistic)


def exact_signflip(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    if len(values) != 16:
        raise RuntimeError("exact sign-flip requires 16 independent world values")
    observed = float(values.mean())
    means = np.empty(2 ** len(values), dtype=float)
    for i, signs in enumerate(itertools.product([-1.0, 1.0], repeat=len(values))):
        means[i] = float(np.mean(values * np.asarray(signs, dtype=float)))
    p = float(np.mean(np.abs(means) >= abs(observed) - 1e-15))
    return {"observed_mean": observed, "assignments": int(len(means)), "exact_two_sided_p": p}


def world_bootstrap(values: np.ndarray, seed: int) -> dict:
    values = np.asarray(values, dtype=float)
    if len(values) != 16:
        raise RuntimeError("world bootstrap requires 16 independent world values")
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(WORLD_BOOTSTRAP_REPS, len(values)), replace=True).mean(axis=1)
    return {
        "reps": WORLD_BOOTSTRAP_REPS,
        "seed": seed,
        "bootstrap_mean": float(samples.mean()),
        "ci_95": [float(x) for x in np.quantile(samples, [0.025, 0.975])],
    }


def discover_worlds(root: Path) -> dict[str, Path]:
    found = {}
    for world in WORLDS:
        candidates = list(root.rglob(f"{world}/FREEZE_MANIFEST.json"))
        if len(candidates) != 1:
            raise RuntimeError(f"expected exactly one frozen artifact for {world}, got {len(candidates)}")
        found[world] = candidates[0].parent
    extra = [p.parent.name for p in root.rglob("FREEZE_MANIFEST.json") if p.parent.name not in WORLDS]
    if extra:
        raise RuntimeError(f"unexpected decision estimation worlds: {extra}")
    return found


def verify_world(path: Path, world: str) -> None:
    manifest = json.loads((path / "FREEZE_MANIFEST.json").read_text())
    md = json.loads((path / "run_metadata.json").read_text())
    if manifest.get("experiment_id") != EXPERIMENT_ID or manifest.get("world") != world:
        raise RuntimeError(f"freeze identity mismatch: {world}")
    if manifest.get("status") != "decision_uncertainty_outputs_frozen_before_private_scoring":
        raise RuntimeError(f"world not frozen before scoring: {world}")
    if int(manifest.get("bootstrap_reps")) != BOOTSTRAP_REPS or int(manifest.get("standardization_anchor_units")) != 1500:
        raise RuntimeError(f"freeze count mismatch: {world}")
    if int(manifest.get("mc_reps_per_anchor")) != MC_REPS or manifest.get("private_scoring_material_access"):
        raise RuntimeError(f"freeze privacy/MC mismatch: {world}")
    if md.get("selection_experiment_id") != "V3-SS-SEL-001-C1" or int(md.get("max_parents")) != 8:
        raise RuntimeError(f"frozen estimator mismatch: {world}")
    if int(md.get("bootstrap_reps")) != BOOTSTRAP_REPS or int(md.get("bootstrap_cluster_size")) != 1100:
        raise RuntimeError(f"bootstrap metadata mismatch: {world}")
    if int(md.get("standardization_anchor_units")) != 1500 or int(md.get("mc_reps_per_anchor")) != MC_REPS:
        raise RuntimeError(f"integration metadata mismatch: {world}")
    if md.get("estimator_private_SCM_access") or md.get("target_outcomes_used_for_fit") or md.get("hyperparameter_retuning"):
        raise RuntimeError(f"estimator leakage/tuning guardrail failed: {world}")
    if md.get("world_replacement") or md.get("bootstrap_replacement_after_results"):
        raise RuntimeError(f"replacement guardrail failed: {world}")
    for name, digest in manifest["files"].items():
        if sha256_file(path / name) != digest:
            raise RuntimeError(f"frozen file hash mismatch: {world}/{name}")
    diag = pd.read_csv(path / "bootstrap_diagnostics.csv")
    if len(diag) != BOOTSTRAP_REPS or set(diag.bootstrap_replicate) != set(range(1, BOOTSTRAP_REPS + 1)):
        raise RuntimeError(f"bootstrap diagnostic replicate mismatch: {world}")
    if not (diag.sampled_clusters == 1100).all():
        raise RuntimeError(f"bootstrap sampled cluster count mismatch: {world}")
    full = pd.read_csv(path / "full_sample_effects.csv")
    boot = pd.read_csv(path / "bootstrap_effects.csv")
    if len(full) != 8 or len(boot) != BOOTSTRAP_REPS * 8:
        raise RuntimeError(f"effect row count mismatch: {world}")
    if set(full.model) != set(MODELS) or set(full.control) != set(CONTROLS):
        raise RuntimeError(f"full-sample model/control mismatch: {world}")
    if set(boot.model) != set(MODELS) or set(boot.control) != set(CONTROLS):
        raise RuntimeError(f"bootstrap model/control mismatch: {world}")
    if not (full.anchor_units == 1500).all() or not (boot.anchor_units == 1500).all():
        raise RuntimeError(f"anchor count mismatch in effects: {world}")
    if not (full.mc_reps_per_anchor == MC_REPS).all() or not (boot.mc_reps_per_anchor == MC_REPS).all():
        raise RuntimeError(f"MC count mismatch in effects: {world}")


def load_rq1_tops(rq1_root: Path) -> dict[tuple[str, str], str]:
    path = rq1_root / "world_metrics.csv"
    if not path.is_file():
        raise RuntimeError("audited RQ1 world_metrics.csv missing")
    df = pd.read_csv(path)
    sub = df[df.model.isin(MODELS)].copy()
    if set(sub.world) != set(WORLDS) or len(sub) != len(WORLDS) * len(MODELS):
        raise RuntimeError("RQ1 world/model set mismatch")
    return {(r.world, r.model): str(r.selected_control) for r in sub.itertuples()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--estimation-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--rq1-results", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    worlds = discover_worlds(args.estimation_root)
    for world, path in worlds.items():
        verify_world(path, world)
    rq1_tops = load_rq1_tops(args.rq1_results)

    decision_rows = []
    pair_rows = []
    world_rows = []
    rq1_checks = []
    for world in WORLDS:
        path = worlds[world]
        private = args.private_root / world
        oracle_path = private / "oracle_effects.json"
        if not oracle_path.is_file():
            raise RuntimeError(f"private oracle missing: {world}")
        oracle_obj = json.loads(oracle_path.read_text())
        oracle = {c: float(oracle_obj[c]["risk_reduction"]) for c in CONTROLS}
        oracle_top = deterministic_top(oracle)
        full = pd.read_csv(path / "full_sample_effects.csv")
        boot = pd.read_csv(path / "bootstrap_effects.csv")
        for model in MODELS:
            full_sub = full[full.model == model]
            full_effects = {r.control: float(r.risk_reduction) for r in full_sub.itertuples()}
            full_top = deterministic_top(full_effects)
            rq1_top = rq1_tops[(world, model)]
            rq1_checks.append({
                "world": world,
                "family": family_from_world(world),
                "model": model,
                "rq4_full_top_control": full_top,
                "audited_rq1_top_control": rq1_top,
                "same_top_control": full_top == rq1_top,
            })
            top_switches = []
            oracle_correct = []
            regrets = []
            oracle_kendalls = []
            oracle_spearmans = []
            full_kendalls = []
            margins = []
            selected_tops = []
            pair_accum = {(a, b): [] for a, b in itertools.combinations(CONTROLS, 2)}
            for b in range(1, BOOTSTRAP_REPS + 1):
                rep = f"b{b:02d}"
                sub = boot[(boot.model == model) & (boot.bootstrap_replicate == b)]
                if len(sub) != len(CONTROLS):
                    raise RuntimeError(f"bootstrap control rows missing: {world}/{model}/{b}")
                est = {r.control: float(r.risk_reduction) for r in sub.itertuples()}
                selected = deterministic_top(est)
                sorted_controls = sorted(CONTROLS, key=lambda c: (-est[c], c))
                margin = float(est[sorted_controls[0]] - est[sorted_controls[1]])
                ok = selected == oracle_top
                regret = float((oracle[oracle_top] - oracle[selected]) / max(abs(oracle[oracle_top]), 1e-12))
                k_oracle, s_oracle = rank_metrics(oracle, est)
                k_full, _ = rank_metrics(full_effects, est)
                switch = selected != full_top
                top_switches.append(float(switch))
                oracle_correct.append(float(ok))
                regrets.append(regret)
                oracle_kendalls.append(k_oracle)
                oracle_spearmans.append(s_oracle)
                full_kendalls.append(k_full)
                margins.append(margin)
                selected_tops.append(selected)
                decision_rows.append({
                    "world": world,
                    "family": family_from_world(world),
                    "model": model,
                    "bootstrap_replicate": b,
                    "selected_control": selected,
                    "full_sample_top_control": full_top,
                    "top_control_switched": switch,
                    "oracle_top_control": oracle_top,
                    "oracle_top_correct": ok,
                    "normalized_oracle_regret": regret,
                    "kendall_vs_oracle": k_oracle,
                    "spearman_vs_oracle": s_oracle,
                    "kendall_vs_full_sample": k_full,
                    "top_runnerup_margin": margin,
                })
                for a, c in itertools.combinations(CONTROLS, 2):
                    full_sign = np.sign(full_effects[a] - full_effects[c])
                    boot_sign = np.sign(est[a] - est[c])
                    reversal_or_tie = boot_sign != full_sign
                    pair_accum[(a, c)].append(float(reversal_or_tie))
            counts = pd.Series(selected_tops).value_counts().sort_index().to_dict()
            world_rows.append({
                "world": world,
                "family": family_from_world(world),
                "model": model,
                "full_sample_top_control": full_top,
                "audited_rq1_top_control": rq1_top,
                "oracle_top_control": oracle_top,
                "top_switch_rate": float(np.mean(top_switches)),
                "oracle_top_accuracy": float(np.mean(oracle_correct)),
                "mean_normalized_oracle_regret": float(np.mean(regrets)),
                "mean_kendall_vs_oracle": float(np.mean(oracle_kendalls)),
                "mean_spearman_vs_oracle": float(np.mean(oracle_spearmans)),
                "mean_kendall_vs_full_sample": float(np.mean(full_kendalls)),
                "mean_top_runnerup_margin": float(np.mean(margins)),
                "min_top_runnerup_margin": float(np.min(margins)),
                "distinct_top_controls": int(len(counts)),
                "top_control_counts": json.dumps({str(k): int(v) for k, v in counts.items()}, sort_keys=True),
            })
            for (a, c), vals in pair_accum.items():
                pair_rows.append({
                    "world": world,
                    "family": family_from_world(world),
                    "model": model,
                    "control_a": a,
                    "control_b": c,
                    "reversal_or_tie_rate_vs_full": float(np.mean(vals)),
                })

    decision_df = pd.DataFrame(decision_rows)
    world_df = pd.DataFrame(world_rows)
    pair_df = pd.DataFrame(pair_rows)
    rq1_df = pd.DataFrame(rq1_checks)
    decision_df.to_csv(args.outdir / "bootstrap_decisions.csv", index=False)
    world_df.to_csv(args.outdir / "world_decision_stability.csv", index=False)
    pair_df.to_csv(args.outdir / "pairwise_rank_reversals.csv", index=False)
    rq1_df.to_csv(args.outdir / "rq1_reference_check.csv", index=False)

    model_summary = []
    for model in MODELS:
        wm = world_df[world_df.model == model]
        dm = decision_df[decision_df.model == model]
        model_summary.append({
            "model": model,
            "mean_world_top_switch_rate": float(wm.top_switch_rate.mean()),
            "mean_world_oracle_top_accuracy": float(wm.oracle_top_accuracy.mean()),
            "mean_world_normalized_oracle_regret": float(wm.mean_normalized_oracle_regret.mean()),
            "mean_world_kendall_vs_oracle": float(wm.mean_kendall_vs_oracle.mean()),
            "mean_world_spearman_vs_oracle": float(wm.mean_spearman_vs_oracle.mean()),
            "mean_world_kendall_vs_full_sample": float(wm.mean_kendall_vs_full_sample.mean()),
            "mean_bootstrap_top_runnerup_margin": float(dm.top_runnerup_margin.mean()),
            "worlds_with_any_top_switch": int((wm.top_switch_rate > 0).sum()),
            "worlds_with_rq4_full_top_different_from_rq1": int((wm.full_sample_top_control != wm.audited_rq1_top_control).sum()),
        })
    model_summary_df = pd.DataFrame(model_summary)
    model_summary_df.to_csv(args.outdir / "model_decision_summary.csv", index=False)

    d = world_df[world_df.model == MODELS[0]].set_index("world").loc[WORLDS]
    g = world_df[world_df.model == MODELS[1]].set_index("world").loc[WORLDS]
    d_values = d.top_switch_rate.to_numpy(float)
    g_values = g.top_switch_rate.to_numpy(float)
    diff = d_values - g_values
    primary_boot = world_bootstrap(d_values, PRIMARY_BOOTSTRAP_SEED)
    secondary_boot = world_bootstrap(diff, COMPARATOR_BOOTSTRAP_SEED)
    signflip = exact_signflip(diff)

    result = {
        "experiment_id": EXPERIMENT_ID,
        "status": "PASS",
        "n_independent_worlds": 16,
        "bootstrap_cluster_resamples_per_world": BOOTSTRAP_REPS,
        "mc_reps_per_anchor": MC_REPS,
        "standardization_anchor_units_per_world": 1500,
        "primary_endpoint": {
            "name": "DCHAG mean world-level top-control switch rate under cluster-bootstrap training perturbation",
            "mean_switch_rate": float(d_values.mean()),
            "world_bootstrap": primary_boot,
        },
        "secondary_dchag_minus_dense_switch_rate": {
            "mean_difference": float(diff.mean()),
            "world_bootstrap": secondary_boot,
            "exact_signflip": signflip,
        },
        "model_summary": {r["model"]: {k: v for k, v in r.items() if k != "model"} for r in model_summary},
        "rq1_full_reference_top_control_discrepancies": {
            model: int(((world_df.model == model) & (world_df.full_sample_top_control != world_df.audited_rq1_top_control)).sum())
            for model in MODELS
        },
        "guardrails": {
            "all_16_world_estimation_outputs_frozen_before_private_scoring": True,
            "independent_unit_is_world_not_bootstrap_replicate": True,
            "bootstrap_reps_per_world": BOOTSTRAP_REPS,
            "bootstrap_clusters_sampled_per_replicate": 1100,
            "standardization_anchor_units_per_world": 1500,
            "mc_reps_per_anchor": MC_REPS,
            "active_corrected_estimator_unchanged": True,
            "dense_comparator_unchanged": True,
            "estimator_private_SCM_access": False,
            "hyperparameter_retuning": False,
            "world_replacement": False,
            "bootstrap_replacement": False,
        },
        "claim_boundary": "Finite-sample decision stability in the frozen semi-synthetic benchmark only. This is not posterior uncertainty, real-world uncertainty calibration, real defensive-control effectiveness, arbitrary distribution-shift robustness, or real-LANL causal identification.",
    }
    write_json(args.outdir / "SEMISYNTHETIC_DECISION_UNCERTAINTY_RESULTS.json", result)
    result_files = sorted(p for p in args.outdir.iterdir() if p.is_file() and p.name != "RESULT_SHA256.txt")
    (args.outdir / "RESULT_SHA256.txt").write_text("".join(f"{sha256_file(p)}  {p.name}\n" for p in result_files), encoding="utf-8")
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "status": "PASS", "primary_mean_switch_rate": float(d_values.mean())}, sort_keys=True))


if __name__ == "__main__":
    main()
