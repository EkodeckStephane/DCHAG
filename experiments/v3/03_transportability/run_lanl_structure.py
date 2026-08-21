from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

CHANNELS = ("H_login", "P_process", "T_network")
EXPECTED_MEMBER_SHA256 = "6c45852d95ce583aa95e39d6560ce2ef61a8f1e84e51c01cc38292c113cd1d22"
N_WINDOWS = 181
SCREEN_C = 0.05
LOCAL_C = 0.7
MAX_PARENTS = 10


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_fold(device: str, k: int = 5) -> int:
    d = hashlib.sha256(device.encode("utf-8")).digest()
    return int.from_bytes(d[:8], "big") % k


def load_panel(path: Path) -> tuple[np.ndarray, np.ndarray]:
    actual = sha256_file(path)
    if actual != EXPECTED_MEMBER_SHA256:
        raise RuntimeError(f"trajectory SHA-256 mismatch: {actual}")
    usecols = [
        "window_idx", "device",
        "logon_success_4624", "logon_failure_4625",
        "process_start_4688", "process_end_4689",
        "net_out_flows", "net_in_flows",
    ]
    df = pd.read_csv(path, usecols=usecols)
    devices = np.array(sorted(df["device"].astype(str).unique()), dtype=object)
    cat = pd.Categorical(df["device"].astype(str), categories=devices)
    dev_idx = cat.codes.astype(np.int32)
    windows = df["window_idx"].to_numpy(np.int16)
    if windows.min() != 0 or windows.max() != N_WINDOWS - 1:
        raise RuntimeError(f"unexpected window range {windows.min()}..{windows.max()}")
    keys = dev_idx.astype(np.int64) * N_WINDOWS + windows.astype(np.int64)
    if np.unique(keys).size != len(keys):
        raise RuntimeError("duplicate device-window rows in retained trajectory")

    states = np.zeros((len(devices), N_WINDOWS, len(CHANNELS)), dtype=np.uint8)
    h = (
        df["logon_success_4624"].to_numpy(np.int64)
        + df["logon_failure_4625"].to_numpy(np.int64)
        > 0
    ).astype(np.uint8)
    p = (
        df["process_start_4688"].to_numpy(np.int64)
        + df["process_end_4689"].to_numpy(np.int64)
        > 0
    ).astype(np.uint8)
    t = (
        df["net_out_flows"].to_numpy(np.int64)
        + df["net_in_flows"].to_numpy(np.int64)
        > 0
    ).astype(np.uint8)
    states[dev_idx, windows, 0] = h
    states[dev_idx, windows, 1] = p
    states[dev_idx, windows, 2] = t
    return devices, states


PATTERNS = np.array(
    [[(code >> 2) & 1, (code >> 1) & 1, code & 1] for code in range(8)],
    dtype=float,
)


def transition_counts(
    states: np.ndarray,
    device_mask: np.ndarray,
    target_index: int,
    t_start: int = 1,
    t_end: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    if t_end is None:
        t_end = states.shape[1] - 1
    s = states[device_mask]
    x = s[:, t_start - 1:t_end, :].reshape(-1, 3)
    y = s[:, t_start:t_end + 1, target_index].reshape(-1)
    code = (x[:, 0] * 4 + x[:, 1] * 2 + x[:, 2]).astype(np.int8)
    neg = np.bincount(code[y == 0], minlength=8).astype(np.int64)
    pos = np.bincount(code[y == 1], minlength=8).astype(np.int64)
    return neg, pos


def weighted_binary_mi(neg: np.ndarray, pos: np.ndarray, feature_index: int) -> float:
    counts = np.zeros((2, 2), dtype=float)
    for pattern in range(8):
        x = int(PATTERNS[pattern, feature_index])
        counts[x, 0] += neg[pattern]
        counts[x, 1] += pos[pattern]
    total = counts.sum()
    if total <= 0:
        return 0.0
    px = counts.sum(axis=1) / total
    py = counts.sum(axis=0) / total
    mi = 0.0
    for x in range(2):
        for y in range(2):
            pxy = counts[x, y] / total
            if pxy > 0 and px[x] > 0 and py[y] > 0:
                mi += pxy * np.log(pxy / (px[x] * py[y]))
    return float(mi)


def weighted_rows(neg: np.ndarray, pos: np.ndarray):
    X, y, w = [], [], []
    for code in range(8):
        if neg[code] > 0:
            X.append(PATTERNS[code]); y.append(0); w.append(neg[code])
        if pos[code] > 0:
            X.append(PATTERNS[code]); y.append(1); w.append(pos[code])
    return np.asarray(X, float), np.asarray(y, int), np.asarray(w, float)


def add_interactions(X: np.ndarray, selected: list[int]) -> np.ndarray:
    if not selected:
        return np.zeros((len(X), 0), float)
    z = X[:, selected]
    pairs = list(itertools.combinations(range(len(selected)), 2))
    if pairs:
        inter = np.column_stack([z[:, a] * z[:, b] for a, b in pairs])
        z = np.column_stack([z, inter])
    return z


def fit_sparse_from_counts(neg: np.ndarray, pos: np.ndarray, target_index: int) -> dict:
    X, y, w = weighted_rows(neg, pos)
    total_pos = float(pos.sum())
    total = float(neg.sum() + pos.sum())
    prevalence = total_pos / total if total else 0.5
    if len(np.unique(y)) < 2:
        p = float(np.clip(prevalence, 1e-6, 1 - 1e-6))
        return {
            "selected": [], "screen_coefficients": [0.0, 0.0, 0.0],
            "main_coefficients": [], "intercept": float(np.log(p / (1-p))),
            "pattern_probabilities": [prevalence] * 8,
            "fallback_used": False, "prevalence": prevalence,
        }

    screen = LogisticRegression(
        penalty="l1", C=SCREEN_C, solver="liblinear",
        max_iter=500, fit_intercept=True,
    )
    screen.fit(X, y, sample_weight=w)
    coeff = screen.coef_[0]
    ranked = np.argsort(-np.abs(coeff))
    selected = [int(i) for i in ranked if abs(coeff[i]) > 1e-6][:MAX_PARENTS]
    fallback = False
    if not selected:
        mis = [weighted_binary_mi(neg, pos, i) for i in range(3)]
        selected = [int(np.argmax(mis))]
        fallback = True

    Z = add_interactions(X, selected)
    local = LogisticRegression(C=LOCAL_C, solver="lbfgs", max_iter=500, fit_intercept=True)
    local.fit(Z, y, sample_weight=w)
    probs = local.predict_proba(add_interactions(PATTERNS, selected))[:, 1]
    return {
        "selected": selected,
        "screen_coefficients": [float(x) for x in coeff],
        "main_coefficients": [float(x) for x in local.coef_[0][:len(selected)]],
        "intercept": float(local.intercept_[0]),
        "pattern_probabilities": [float(x) for x in probs],
        "fallback_used": fallback,
        "prevalence": prevalence,
    }


def fit_self_from_counts(neg: np.ndarray, pos: np.ndarray, target_index: int) -> dict:
    xvals, yvals, weights = [], [], []
    for code in range(8):
        x = int(PATTERNS[code, target_index])
        if neg[code] > 0:
            xvals.append([x]); yvals.append(0); weights.append(neg[code])
        if pos[code] > 0:
            xvals.append([x]); yvals.append(1); weights.append(pos[code])
    X = np.asarray(xvals, float); y = np.asarray(yvals, int); w = np.asarray(weights, float)
    prevalence = float(pos.sum() / max(1, neg.sum() + pos.sum()))
    if len(np.unique(y)) < 2:
        return {"pattern_probabilities": [prevalence] * 8, "prevalence": prevalence}
    m = LogisticRegression(C=1e6, solver="lbfgs", max_iter=300)
    m.fit(X, y, sample_weight=w)
    probs = m.predict_proba(PATTERNS[:, [target_index]])[:, 1]
    return {"pattern_probabilities": [float(x) for x in probs], "prevalence": prevalence}


def score_counts(neg: np.ndarray, pos: np.ndarray, probs: np.ndarray) -> float:
    total = (neg + pos).sum()
    if total == 0:
        return float("nan")
    err = (neg * probs**2 + pos * (1.0 - probs)**2).sum()
    return float(err / total)


def fit_structure(states: np.ndarray, mask: np.ndarray, t_start=1, t_end=180) -> dict:
    node_results, edges, signs = {}, [], {}
    for j, target in enumerate(CHANNELS):
        neg, pos = transition_counts(states, mask, j, t_start, t_end)
        model = fit_sparse_from_counts(neg, pos, j)
        selected_names = [CHANNELS[i] for i in model["selected"]]
        model["selected_names"] = selected_names
        node_results[target] = model
        for parent in selected_names:
            edges.append(f"{parent}[t-1]->{target}[t]")
        for parent, coef in zip(selected_names, model["main_coefficients"]):
            signs[f"{parent}[t-1]->{target}[t]"] = int(np.sign(coef))
    return {"nodes": node_results, "edges": sorted(edges), "signs": signs}


def jaccard(a, b) -> float:
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def sign_agreement(a: dict, b: dict) -> float | None:
    shared = set(a) & set(b)
    if not shared:
        return None
    return float(np.mean([a[k] == b[k] for k in shared]))


def evaluate_fold(states, train_mask, test_mask, structure) -> dict:
    out = {}
    total_weight = 0
    weighted = {"DCHAG_Learned_Lag1": 0.0, "SelfLag": 0.0, "Prevalence": 0.0}
    for j, target in enumerate(CHANNELS):
        tr_neg, tr_pos = transition_counts(states, train_mask, j)
        te_neg, te_pos = transition_counts(states, test_mask, j)
        sparse = structure["nodes"][target]
        self_model = fit_self_from_counts(tr_neg, tr_pos, j)
        p_sparse = np.asarray(sparse["pattern_probabilities"], float)
        p_self = np.asarray(self_model["pattern_probabilities"], float)
        p_prev = np.full(8, sparse["prevalence"], float)
        b_sparse = score_counts(te_neg, te_pos, p_sparse)
        b_self = score_counts(te_neg, te_pos, p_self)
        b_prev = score_counts(te_neg, te_pos, p_prev)
        n = int((te_neg + te_pos).sum())
        out[target] = {
            "n_test_transitions": n,
            "test_positive_rate": float(te_pos.sum() / max(1, n)),
            "brier": {"DCHAG_Learned_Lag1": b_sparse, "SelfLag": b_self, "Prevalence": b_prev},
            "bss_vs_prevalence": 1.0 - b_sparse / b_prev if b_prev > 0 else None,
            "brier_difference_dchag_minus_self": b_sparse - b_self,
        }
        total_weight += n
        for key, val in [("DCHAG_Learned_Lag1", b_sparse), ("SelfLag", b_self), ("Prevalence", b_prev)]:
            weighted[key] += n * val
    out["_macro"] = {
        "total_test_transitions": total_weight,
        "weighted_brier": {k: v / total_weight for k, v in weighted.items()},
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trajectory", required=True, type=Path)
    ap.add_argument("--output", default="LANL_STRUCTURE_RESULTS.json", type=Path)
    args = ap.parse_args()

    devices, states = load_panel(args.trajectory)
    folds = np.array([stable_fold(str(d), 5) for d in devices], dtype=np.int8)
    fold_sizes = {str(i): int(np.sum(folds == i)) for i in range(5)}

    fold_results = []
    for fold in range(5):
        test_mask = folds == fold
        train_mask = ~test_mask
        structure = fit_structure(states, train_mask)
        evaluation = evaluate_fold(states, train_mask, test_mask, structure)
        fold_results.append({
            "fold": fold,
            "n_train_devices": int(train_mask.sum()),
            "n_test_devices": int(test_mask.sum()),
            "edges": structure["edges"],
            "signs": structure["signs"],
            "nodes": {
                target: {
                    "selected_names": structure["nodes"][target]["selected_names"],
                    "screen_coefficients": structure["nodes"][target]["screen_coefficients"],
                    "main_coefficients": structure["nodes"][target]["main_coefficients"],
                    "fallback_used": structure["nodes"][target]["fallback_used"],
                    "train_prevalence": structure["nodes"][target]["prevalence"],
                }
                for target in CHANNELS
            },
            "evaluation": evaluation,
        })

    pairwise = []
    for a, b in itertools.combinations(range(5), 2):
        pairwise.append({
            "fold_a": a, "fold_b": b,
            "edge_jaccard": jaccard(fold_results[a]["edges"], fold_results[b]["edges"]),
            "sign_agreement_on_shared_edges": sign_agreement(fold_results[a]["signs"], fold_results[b]["signs"]),
        })

    all_edges = sorted(set().union(*(set(f["edges"]) for f in fold_results)))
    edge_frequency = {e: sum(e in f["edges"] for f in fold_results) for e in all_edges}
    sign_frequency = {}
    for e in all_edges:
        vals = [f["signs"][e] for f in fold_results if e in f["signs"]]
        sign_frequency[e] = {
            "n_selected": len(vals),
            "positive": sum(v > 0 for v in vals),
            "negative": sum(v < 0 for v in vals),
            "zero": sum(v == 0 for v in vals),
        }

    aggregate = {}
    for target in CHANNELS:
        weights = np.array([f["evaluation"][target]["n_test_transitions"] for f in fold_results], float)
        aggregate[target] = {}
        for model in ("DCHAG_Learned_Lag1", "SelfLag", "Prevalence"):
            vals = np.array([f["evaluation"][target]["brier"][model] for f in fold_results], float)
            aggregate[target][model] = float(np.average(vals, weights=weights))
        prev = aggregate[target]["Prevalence"]
        aggregate[target]["bss_vs_prevalence"] = 1.0 - aggregate[target]["DCHAG_Learned_Lag1"] / prev if prev > 0 else None
        aggregate[target]["brier_difference_dchag_minus_self"] = aggregate[target]["DCHAG_Learned_Lag1"] - aggregate[target]["SelfLag"]

    all_mask = np.ones(len(devices), dtype=bool)
    early = fit_structure(states, all_mask, 1, 90)
    late = fit_structure(states, all_mask, 91, 180)

    result = {
        "experiment_id": "V3-LANL-STRUCT-001",
        "status": "PASS",
        "source": {"trajectory_sha256": EXPECTED_MEMBER_SHA256, "window_width_seconds": 300, "n_windows": N_WINDOWS, "n_devices": int(len(devices))},
        "channels": list(CHANNELS),
        "candidate_rule": "lag-1 only; no same-window edges",
        "hyperparameters": {"screening": "L1 logistic conditional screening", "screening_C": SCREEN_C, "local_model_C": LOCAL_C, "max_parents": MAX_PARENTS, "mi_fallback": True, "lanl_tuning": False},
        "fold_sizes": fold_sizes,
        "folds": fold_results,
        "edge_selection_frequency": edge_frequency,
        "edge_sign_frequency": sign_frequency,
        "pairwise_fold_stability": pairwise,
        "pairwise_edge_jaccard_summary": {
            "min": float(min(x["edge_jaccard"] for x in pairwise)),
            "median": float(np.median([x["edge_jaccard"] for x in pairwise])),
            "max": float(max(x["edge_jaccard"] for x in pairwise)),
        },
        "out_of_fold": aggregate,
        "early_late_stability": {
            "early_target_windows": [1, 90], "late_target_windows": [91, 180],
            "early_edges": early["edges"], "late_edges": late["edges"],
            "edge_jaccard": jaccard(early["edges"], late["edges"]),
            "sign_agreement_on_shared_edges": sign_agreement(early["signs"], late["signs"]),
        },
        "guardrails": {"attack_or_red_team_labels_read": False, "defensive_intervention_C_inferred": False, "counterfactual_effect_claim": False, "same_window_edges_allowed": False, "hyperparameters_tuned_on_LANL": False},
        "claim_boundary": "observational temporal structure stability and predictive device-level transportability only",
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "n_devices": result["source"]["n_devices"], "jaccard": result["pairwise_edge_jaccard_summary"], "edge_frequency": result["edge_selection_frequency"], "oof": result["out_of_fold"], "early_late": result["early_late_stability"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
