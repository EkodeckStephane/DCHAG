from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

DAYS = (6, 7, 8, 9, 10)
CHANNELS = ("H_person_login", "P_process", "T_network")
CORE_EDGES = (
    "P_process[t-1]->P_process[t]",
    "P_process[t-1]->T_network[t]",
    "T_network[t-1]->T_network[t]",
)


def load_result(path: Path) -> dict:
    r = json.loads(path.read_text(encoding="utf-8"))
    if r.get("status") != "PASS":
        raise RuntimeError(f"non-PASS day result: {path}")
    return r


def aggregate(results: list[dict]) -> dict:
    by_day = {int(r["day"]): r for r in results}
    if set(by_day) != set(DAYS):
        raise RuntimeError(f"expected days {list(DAYS)}, got {sorted(by_day)}")

    ordered = [by_day[d] for d in DAYS]
    fixed_edges = np.array([r["aggregate"]["FixedFull"]["mean_selected_edges_per_fold"] for r in ordered], float)
    scaled_edges = np.array([r["aggregate"]["ScaledFull"]["mean_selected_edges_per_fold"] for r in ordered], float)

    edge_frequency = Counter()
    sign_frequency: dict[str, Counter] = {}
    h_fallback = 0
    day_summaries = {}

    for d, r in zip(DAYS, ordered):
        scaled = r["aggregate"]["ScaledFull"]
        edge_frequency.update(scaled["edge_frequency"])
        for fold in r["fold_results"]:
            variant = fold["variants"]["ScaledFull"]
            h_fallback += int(bool(variant["nodes"]["H_person_login"].get("fallback_used", False)))
            for edge, sign in variant.get("signs", {}).items():
                sign_frequency.setdefault(edge, Counter())[str(int(sign))] += 1

        day_summaries[str(d)] = {
            "interval_start": r["diagnostics"]["interval_start"],
            "interval_end": r["diagnostics"]["interval_end"],
            "n_windows": r["diagnostics"]["n_windows"],
            "unique_devices": r["diagnostics"]["unique_devices"],
            "host_records": r["diagnostics"]["host"]["parsed"],
            "network_records": r["diagnostics"]["network"]["parsed"],
            "person_login_events": r["diagnostics"]["host"]["person_login_events"],
            "excluded_nonperson_login_events": r["diagnostics"]["host"]["excluded_nonperson_login_events"],
            "FixedFull_mean_edges": r["aggregate"]["FixedFull"]["mean_selected_edges_per_fold"],
            "ScaledFull_mean_edges": scaled["mean_selected_edges_per_fold"],
            "brier": {
                target: {
                    "ScaledFull": scaled["brier"][target]["model"],
                    "SelfLag": scaled["brier"][target]["SelfLag"],
                    "Scaled_better_than_SelfLag": bool(scaled["brier"][target]["model"] < scaled["brier"][target]["SelfLag"]),
                }
                for target in CHANNELS
            },
        }

    p_wins = sum(day_summaries[str(d)]["brier"]["P_process"]["Scaled_better_than_SelfLag"] for d in DAYS)
    t_wins = sum(day_summaries[str(d)]["brier"]["T_network"]["Scaled_better_than_SelfLag"] for d in DAYS)
    h_wins = sum(day_summaries[str(d)]["brier"]["H_person_login"]["Scaled_better_than_SelfLag"] for d in DAYS)

    criteria = {
        "C1_sparsity_5_of_5": bool(np.all(scaled_edges < fixed_edges)),
        "C2_P_beats_SelfLag_at_least_4_of_5": bool(p_wins >= 4),
        "C3_T_beats_SelfLag_at_least_4_of_5": bool(t_wins >= 4),
        "C4_core_edges_at_least_20_of_25": bool(all(edge_frequency[e] >= 20 for e in CORE_EDGES)),
    }
    criteria["all_primary_criteria_pass"] = bool(all(criteria.values()))

    return {
        "experiment_id": "V3-LANL-PT-EXT-001",
        "status": "PASS",
        "days": list(DAYS),
        "day_summaries": day_summaries,
        "density": {
            "FixedFull_day_mean_edges": fixed_edges.tolist(),
            "ScaledFull_day_mean_edges": scaled_edges.tolist(),
            "FixedFull_mean_across_days": float(fixed_edges.mean()),
            "ScaledFull_mean_across_days": float(scaled_edges.mean()),
            "Scaled_to_Fixed_density_ratio": float(scaled_edges.mean()/fixed_edges.mean()),
        },
        "predictive_wins_vs_SelfLag": {
            "H_person_login": int(h_wins),
            "P_process": int(p_wins),
            "T_network": int(t_wins),
        },
        "scaled_edge_frequency_across_25_folds": dict(sorted(edge_frequency.items())),
        "scaled_sign_frequency": {e: dict(sorted(c.items())) for e, c in sorted(sign_frequency.items())},
        "H_person_login_fallback_count_across_25_folds": int(h_fallback),
        "criteria": criteria,
        "guardrails": {
            "posthoc_day_selection": False,
            "posthoc_hyperparameter_selection": False,
            "H_repair_performed": False,
            "causal_edge_claim": False,
        },
        "interpretation_boundary": "Extended temporal observational transportability only; no causal or intervention claim.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    result = aggregate([load_result(p) for p in args.inputs])
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
