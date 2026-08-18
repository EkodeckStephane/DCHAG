from __future__ import annotations
from pathlib import Path
import hashlib
import json
import pandas as pd

from baselines.dense_sequential_gformula import CrossFittedDenseSequentialGFormula
from dchag.config import load_config

ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = ["bec_payment", "data_exfiltration", "helpdesk_identity", "it_ot_maintenance"]
OUT = ROOT / "results" / "q1_dense_sequential_gformula"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    estimates, positivity = [], []
    for context in CONTEXTS:
        cfg = load_config(ROOT / "configs" / f"{context}.yaml")
        train_path = ROOT / "benchmarks" / context / "train_observed.csv"
        train = pd.read_csv(train_path)
        est = CrossFittedDenseSequentialGFormula(
            cfg, n_splits=5, fold_seed=260817, mc_per_trajectory=20, simulation_seed_base=811700
        )
        for row in est.estimate_effects(train):
            estimates.append({
                "context": context,
                "model": "CrossFittedDenseSequentialGFormula",
                "control": row.control,
                "baseline_risk": row.baseline_risk,
                "intervention_risk": row.intervention_risk,
                "risk_reduction": row.risk_reduction,
                "n_trajectories": row.n_trajectories,
                "folds": row.folds,
                "mc_per_trajectory": row.mc_per_trajectory,
                "fold_seed": 260817,
                "simulation_seed_base": 811700,
            })
        positivity.append(est.local_positivity(train))
    ep = OUT / "effect_estimates.csv"
    pp = OUT / "local_positivity.csv"
    pd.DataFrame(estimates).to_csv(ep, index=False)
    pd.concat(positivity, ignore_index=True).to_csv(pp, index=False)
    manifest = {
        "date": "2026-08-17",
        "status": "estimates_frozen_before_ground_truth_scoring",
        "amendment": "experiments/q1_causal_baseline_amendment_v1_1.md",
        "ground_truth_read_by_estimator": False,
        "contexts": CONTEXTS,
        "model": "CrossFittedDenseSequentialGFormula",
        "folds": 5,
        "fold_seed": 260817,
        "mc_per_trajectory": 20,
        "simulation_seed_base": 811700,
        "effect_estimates_sha256": sha256(ep),
        "local_positivity_sha256": sha256(pp),
    }
    (OUT / "estimation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    main()
