from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

from baselines.causal_gformula import CrossFittedFlexibleGFormula
from dchag.config import load_config

ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = ["bec_payment", "data_exfiltration", "helpdesk_identity", "it_ot_maintenance"]


def main():
    out = ROOT / "results" / "q1_causal_baseline"
    out.mkdir(parents=True, exist_ok=True)
    all_est = []
    all_pos = []
    for context in CONTEXTS:
        cfg = load_config(ROOT / "configs" / f"{context}.yaml")
        train = pd.read_csv(ROOT / "benchmarks" / context / "train_observed.csv")
        est = CrossFittedFlexibleGFormula(cfg, n_splits=5, fold_seed=260817)
        for row in est.estimate_effects(train):
            all_est.append({
                "context": context,
                "model": "CrossFittedFlexibleGFormula",
                "control": row.control,
                "baseline_risk": row.baseline_risk,
                "intervention_risk": row.intervention_risk,
                "risk_reduction": row.risk_reduction,
                "n_trajectories": row.n_trajectories,
                "folds": row.folds,
                "fold_seed": 260817,
            })
        all_pos.append(est.positivity_diagnostics(train))

    pd.DataFrame(all_est).to_csv(out / "effect_estimates.csv", index=False)
    pd.concat(all_pos, ignore_index=True).to_csv(out / "positivity_diagnostics.csv", index=False)
    (out / "estimation_manifest.json").write_text(json.dumps({
        "date": "2026-08-17",
        "status": "estimates_frozen_before_ground_truth_scoring",
        "amendment": "experiments/q1_causal_baseline_amendment_v1_0.md",
        "ground_truth_read_by_estimator": False,
        "contexts": CONTEXTS,
        "model": "CrossFittedFlexibleGFormula",
        "folds": 5,
        "fold_seed": 260817,
    }, indent=2), encoding="utf-8")
    print("Q1 causal baseline estimates frozen; ground truth not read")


if __name__ == "__main__":
    main()
