from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from run_lanl_structure import (
    CHANNELS,
    LOCAL_C,
    PATTERNS,
    add_interactions,
    load_panel,
    score_counts,
    stable_fold,
    transition_counts,
    weighted_binary_mi,
    weighted_rows,
)

REFERENCE_N = 6400
FIXED_C = 0.05
VARIANTS = ("FixedFull", "ScaledFull", "Matched6400")


def select_parents(neg: np.ndarray, pos: np.ndarray, c_value: float) -> dict:
    X, y, w = weighted_rows(neg, pos)
    screen = LogisticRegression(
        penalty="l1", C=c_value, solver="liblinear",
        max_iter=500, fit_intercept=True,
    )
    screen.fit(X, y, sample_weight=w)
    coef = screen.coef_[0]
    selected = [int(i) for i in np.argsort(-np.abs(coef)) if abs(coef[i]) > 1e-6]
    fallback = False
    if not selected:
        selected = [int(np.argmax([weighted_binary_mi(neg, pos, i) for i in range(3)]))]
        fallback = True
    return {
        "selected": selected,
        "screen_coefficients": [float(x) for x in coef],
        "fallback_used": fallback,
    }


def fit_full_local_probabilities(neg: np.ndarray, pos: np.ndarray, selected: list[int]) -> list[float]:
    X, y, w = weighted_rows(neg, pos)
    Z = add_interactions(X, selected)
    model = LogisticRegression(C=LOCAL_C, solver="lbfgs", max_iter=500, fit_intercept=True)
    model.fit(Z, y, sample_weight=w)
    return [float(x) for x in model.predict_proba(add_interactions(PATTERNS, selected))[:, 1]]


def sampled_counts(states: np.ndarray, train_mask: np.ndarray, sample_idx: np.ndarray, target_index: int):
    s = states[train_mask]
    width = s.shape[1] - 1
    dev = sample_idx // width
    t0 = sample_idx % width
    x = s[dev, t0, :]
    y = s[dev, t0 + 1, target_index]
    code = (x[:, 0] * 4 + x[:, 1] * 2 + x[:, 2]).astype(np.int8)
    neg = np.bincount(code[y == 0], minlength=8).astype(np.int64)
    pos = np.bincount(code[y == 1], minlength=8).astype(np.int64)
    return neg, pos


def edge_names(target: str, selected: list[int]) -> list[str]:
    return sorted(f"{CHANNELS[i]}[t-1]->{target}[t]" for i in selected)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trajectory", required=True, type=Path)
    ap.add_argument("--output", default="LANL_REGSCALE_RESULTS.json", type=Path)
    args = ap.parse_args()

    devices, states = load_panel(args.trajectory)
    folds = np.array([stable_fold(str(d), 5) for d in devices], dtype=np.int8)
    fold_results = []

    for fold in range(5):
        train_mask = folds != fold
        test_mask = ~train_mask
        n_train_transitions = int(train_mask.sum() * (states.shape[1] - 1))
        scaled_c = FIXED_C * REFERENCE_N / n_train_transitions
        rng = np.random.default_rng(73000 + fold)
        sample_idx = rng.choice(n_train_transitions, size=REFERENCE_N, replace=False)

        variants = {v: {"edges": [], "targets": {}} for v in VARIANTS}
        for j, target in enumerate(CHANNELS):
            full_neg, full_pos = transition_counts(states, train_mask, j)
            test_neg, test_pos = transition_counts(states, test_mask, j)
            sample_neg, sample_pos = sampled_counts(states, train_mask, sample_idx, j)

            selections = {
                "FixedFull": select_parents(full_neg, full_pos, FIXED_C),
                "ScaledFull": select_parents(full_neg, full_pos, scaled_c),
                "Matched6400": select_parents(sample_neg, sample_pos, FIXED_C),
            }
            for variant, selection in selections.items():
                selected = selection["selected"]
                probs = np.asarray(fit_full_local_probabilities(full_neg, full_pos, selected), float)
                brier = score_counts(test_neg, test_pos, probs)
                edges = edge_names(target, selected)
                variants[variant]["edges"].extend(edges)
                variants[variant]["targets"][target] = {
                    "selected_parents": [CHANNELS[i] for i in selected],
                    "selected_parent_count": len(selected),
                    "screen_coefficients": selection["screen_coefficients"],
                    "fallback_used": selection["fallback_used"],
                    "heldout_brier": brier,
                    "n_test_transitions": int((test_neg + test_pos).sum()),
                }

        fixed_brier = {t: variants["FixedFull"]["targets"][t]["heldout_brier"] for t in CHANNELS}
        for variant in VARIANTS:
            variants[variant]["edges"] = sorted(set(variants[variant]["edges"]))
            variants[variant]["selected_edge_count"] = len(variants[variant]["edges"])
            variants[variant]["brier_delta_vs_fixed"] = {
                t: variants[variant]["targets"][t]["heldout_brier"] - fixed_brier[t] for t in CHANNELS
            }

        fold_results.append({
            "fold": fold,
            "n_train_devices": int(train_mask.sum()),
            "n_test_devices": int(test_mask.sum()),
            "n_train_transitions": n_train_transitions,
            "scaled_C": scaled_c,
            "matched_sample_size": REFERENCE_N,
            "matched_sample_seed": 73000 + fold,
            "variants": variants,
        })

    aggregate = {}
    for variant in VARIANTS:
        edge_freq = {}
        selected_counts = []
        fallback_count = 0
        weighted_brier = {t: 0.0 for t in CHANNELS}
        weights = {t: 0 for t in CHANNELS}
        for f in fold_results:
            vr = f["variants"][variant]
            selected_counts.append(vr["selected_edge_count"])
            for e in vr["edges"]:
                edge_freq[e] = edge_freq.get(e, 0) + 1
            for t in CHANNELS:
                tr = vr["targets"][t]
                fallback_count += int(tr["fallback_used"])
                weighted_brier[t] += tr["heldout_brier"] * tr["n_test_transitions"]
                weights[t] += tr["n_test_transitions"]
        aggregate[variant] = {
            "selected_edge_count_by_fold": selected_counts,
            "mean_selected_edge_count": float(np.mean(selected_counts)),
            "edge_selection_frequency": dict(sorted(edge_freq.items())),
            "fallback_target_fits": fallback_count,
            "out_of_fold_brier": {t: weighted_brier[t] / weights[t] for t in CHANNELS},
        }

    aggregate["ScaledFull"]["brier_delta_vs_FixedFull"] = {
        t: aggregate["ScaledFull"]["out_of_fold_brier"][t] - aggregate["FixedFull"]["out_of_fold_brier"][t]
        for t in CHANNELS
    }
    aggregate["Matched6400"]["brier_delta_vs_FixedFull"] = {
        t: aggregate["Matched6400"]["out_of_fold_brier"][t] - aggregate["FixedFull"]["out_of_fold_brier"][t]
        for t in CHANNELS
    }

    result = {
        "experiment_id": "V3-LANL-REGSCALE-001",
        "status": "PASS",
        "diagnostic_only": True,
        "reference": {
            "v2_confirmatory_median_train_rows": REFERENCE_N,
            "fixed_C": FIXED_C,
            "scaled_C_rule": "0.05 * 6400 / n_train_transitions",
            "matched_sample_rule": "6400 transitions without replacement; seed=73000+fold",
            "local_refit": "full training fold; C=0.7; selected main effects plus pairwise interactions",
        },
        "source": {"trajectory_sha256": "6c45852d95ce583aa95e39d6560ce2ef61a8f1e84e51c01cc38292c113cd1d22", "n_devices": int(len(devices)), "n_windows": int(states.shape[1])},
        "folds": fold_results,
        "aggregate": aggregate,
        "guardrails": {
            "attack_or_red_team_labels_read": False,
            "defensive_intervention_C_inferred": False,
            "counterfactual_effect_claim": False,
            "same_window_edges_allowed": False,
            "variant_selected_by_LANL_performance": False,
            "parent_experiment_rewritten": False,
        },
        "claim_boundary": "diagnoses screening sample-size portability; does not select a replacement v3 regularizer",
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "aggregate": aggregate}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
