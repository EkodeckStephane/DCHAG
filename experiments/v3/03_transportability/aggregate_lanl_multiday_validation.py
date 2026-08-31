from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

CHANNELS = ("H_person_login", "P_process", "T_network")
CONFIRMATORY_DAYS = (3, 4, 5)


def load_result(path: Path) -> dict:
    r = json.loads(path.read_text(encoding="utf-8"))
    if r.get("status") != "PASS":
        raise RuntimeError(f"non-PASS day result: {path}")
    return r


def aggregate(results: list[dict]) -> dict:
    by_day = {int(r["day"]): r for r in results}
    required = {2, 3, 4, 5}
    if set(by_day) != required:
        raise RuntimeError(f"expected days {sorted(required)}, got {sorted(by_day)}")

    confirm = [by_day[d] for d in CONFIRMATORY_DAYS]
    day_summaries = {}
    for d, r in sorted(by_day.items()):
        day_summaries[str(d)] = {
            "role": r["role"],
            "interval_start": r["diagnostics"]["interval_start"],
            "interval_end": r["diagnostics"]["interval_end"],
            "n_windows": r["diagnostics"]["n_windows"],
            "unique_devices": r["diagnostics"]["unique_devices"],
            "person_login_events": r["diagnostics"]["host"]["person_login_events"],
            "excluded_nonperson_login_events": r["diagnostics"]["host"]["excluded_nonperson_login_events"],
            "FixedFull_mean_edges": r["aggregate"]["FixedFull"]["mean_selected_edges_per_fold"],
            "ScaledFull_mean_edges": r["aggregate"]["ScaledFull"]["mean_selected_edges_per_fold"],
            "FixedFull_edge_frequency": r["aggregate"]["FixedFull"]["edge_frequency"],
            "ScaledFull_edge_frequency": r["aggregate"]["ScaledFull"]["edge_frequency"],
            "brier": {
                target: {
                    "FixedFull": r["aggregate"]["FixedFull"]["brier"][target]["model"],
                    "ScaledFull": r["aggregate"]["ScaledFull"]["brier"][target]["model"],
                    "SelfLag": r["aggregate"]["ScaledFull"]["brier"][target]["SelfLag"],
                    "Scaled_relative_change_vs_fixed": r["aggregate"]["ScaledFull"]["brier"][target]["relative_change_vs_fixed"],
                } for target in CHANNELS
            },
        }

    fixed_edges = np.array([r["aggregate"]["FixedFull"]["mean_selected_edges_per_fold"] for r in confirm], float)
    scaled_edges = np.array([r["aggregate"]["ScaledFull"]["mean_selected_edges_per_fold"] for r in confirm], float)
    confirmatory = {
        "days": list(CONFIRMATORY_DAYS),
        "density": {
            "FixedFull_day_mean_edges": [float(x) for x in fixed_edges],
            "ScaledFull_day_mean_edges": [float(x) for x in scaled_edges],
            "FixedFull_mean_across_days": float(fixed_edges.mean()),
            "ScaledFull_mean_across_days": float(scaled_edges.mean()),
            "Scaled_to_Fixed_density_ratio": float(scaled_edges.mean() / fixed_edges.mean()) if fixed_edges.mean() else None,
            "Scaled_reduces_edges_each_day": bool(np.all(scaled_edges < fixed_edges)),
        },
        "prediction": {},
        "scaled_edge_frequency_across_15_folds": {},
    }

    all_edges = set()
    for r in confirm:
        all_edges.update(r["aggregate"]["ScaledFull"]["edge_frequency"])
    confirmatory["scaled_edge_frequency_across_15_folds"] = {
        e: int(sum(r["aggregate"]["ScaledFull"]["edge_frequency"].get(e, 0) for r in confirm))
        for e in sorted(all_edges)
    }
    confirmatory["scaled_edges_selected_in_all_15_folds"] = [
        e for e, n in confirmatory["scaled_edge_frequency_across_15_folds"].items() if n == 15
    ]

    for target in CHANNELS:
        fixed = np.array([r["aggregate"]["FixedFull"]["brier"][target]["model"] for r in confirm], float)
        scaled = np.array([r["aggregate"]["ScaledFull"]["brier"][target]["model"] for r in confirm], float)
        selflag = np.array([r["aggregate"]["ScaledFull"]["brier"][target]["SelfLag"] for r in confirm], float)
        confirmatory["prediction"][target] = {
            "FixedFull_day_brier": [float(x) for x in fixed],
            "ScaledFull_day_brier": [float(x) for x in scaled],
            "SelfLag_day_brier": [float(x) for x in selflag],
            "FixedFull_mean_day_brier": float(fixed.mean()),
            "ScaledFull_mean_day_brier": float(scaled.mean()),
            "SelfLag_mean_day_brier": float(selflag.mean()),
            "Scaled_relative_change_vs_fixed_mean_day": float((scaled.mean() - fixed.mean()) / fixed.mean()) if fixed.mean() else None,
            "Scaled_minus_SelfLag_mean_day": float(scaled.mean() - selflag.mean()),
            "Scaled_better_than_SelfLag_each_day": bool(np.all(scaled < selflag)),
        }

    return {
        "experiment_id": "V3-LANL-MULTIDAY-001",
        "status": "PASS",
        "development_day": 2,
        "confirmatory_days": list(CONFIRMATORY_DAYS),
        "day_summaries": day_summaries,
        "confirmatory": confirmatory,
        "interpretation_boundary": "Days 03-05 are out-of-development observational transportability tests. No selected edge is interpreted as causal and no intervention effect is estimated.",
        "guardrails": {
            "attack_or_red_team_labels_read": False,
            "defensive_intervention_C_inferred": False,
            "counterfactual_effect_claim": False,
            "posthoc_hyperparameter_selection": False,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    result = aggregate([load_result(p) for p in args.inputs])
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["confirmatory"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
