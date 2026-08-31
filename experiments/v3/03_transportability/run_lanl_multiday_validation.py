from __future__ import annotations

import argparse
import bz2
import csv
import hashlib
import itertools
import json
import re
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

CHANNELS = ("H_person_login", "P_process", "T_network")
WIDTH_SECONDS = 300
FOLDS = 5
FIXED_C = 0.05
LOCAL_C = 0.7
V2_REFERENCE_TRANSITIONS = 6400
MAX_PARENTS = 10
PERSON_RE = re.compile(r"^User\d+$", re.IGNORECASE)
PATTERNS = np.array(
    [[(code >> 2) & 1, (code >> 1) & 1, code & 1] for code in range(8)],
    dtype=float,
)


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk_size), b""):
            h.update(block)
    return h.hexdigest()


def canonical_host(event: dict) -> str | None:
    value = event.get("LogHost", event.get("Computer"))
    if value in (None, ""):
        return None
    return str(value)


def event_user(event: dict) -> str | None:
    value = event.get("UserName") or event.get("SubjectUserName")
    if value in (None, ""):
        return None
    return str(value)


def first_host_timestamp(path: Path) -> int:
    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                return int(json.loads(line).get("Time"))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    raise RuntimeError("no valid host timestamp")


def first_network_timestamp(path: Path) -> int:
    with bz2.open(path, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.reader(fh):
            if not row:
                continue
            try:
                return int(row[0])
            except (TypeError, ValueError, IndexError):
                continue
    raise RuntimeError("no valid network timestamp")


def _ensure(bits: dict[str, list[int]], device: str) -> list[int]:
    if device not in bits:
        bits[device] = [0, 0, 0]
    return bits[device]


def build_disjoint_panel(day: int, host_path: Path, network_path: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    if day < 2 or day > 90:
        raise ValueError("day must be in [2,90] because network data starts at day 02")
    day_start = (day - 1) * 86400
    day_end = day * 86400 - 1
    h_first = first_host_timestamp(host_path)
    n_first = first_network_timestamp(network_path)
    start = max(day_start, h_first, n_first)
    if start > day_end:
        raise RuntimeError("no common day interval")

    bits: dict[str, list[int]] = {}
    diag = {
        "day": day,
        "day_start": day_start,
        "day_end": day_end,
        "first_host_timestamp": h_first,
        "first_network_timestamp": n_first,
        "interval_start": start,
        "host": {
            "raw_seen": 0, "parsed": 0, "malformed": 0, "missing_device": 0,
            "person_login_events": 0, "excluded_nonperson_login_events": 0,
            "process_events": 0, "max_timestamp": None,
        },
        "network": {
            "raw_seen": 0, "parsed": 0, "malformed": 0,
            "flows": 0, "max_timestamp": None,
        },
        "source_sha256": {
            "host": sha256_file(host_path),
            "network": sha256_file(network_path),
        },
    }

    with bz2.open(host_path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            diag["host"]["raw_seen"] += 1
            try:
                event = json.loads(line)
                ts = int(event.get("Time"))
                eid = int(event["EventID"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                diag["host"]["malformed"] += 1
                continue
            if ts < start:
                continue
            if ts > day_end:
                break
            device = canonical_host(event)
            if device is None:
                diag["host"]["missing_device"] += 1
                continue
            diag["host"]["parsed"] += 1
            diag["host"]["max_timestamp"] = ts
            idx = (ts - start) // WIDTH_SECONDS
            mask = 1 << idx
            if eid in (4624, 4625):
                user = event_user(event)
                if user and PERSON_RE.fullmatch(user):
                    _ensure(bits, device)[0] |= mask
                    diag["host"]["person_login_events"] += 1
                else:
                    diag["host"]["excluded_nonperson_login_events"] += 1
            elif eid in (4688, 4689):
                _ensure(bits, device)[1] |= mask
                diag["host"]["process_events"] += 1

    with bz2.open(network_path, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.reader(fh):
            if not row:
                continue
            diag["network"]["raw_seen"] += 1
            try:
                if len(row) < 4:
                    raise ValueError
                ts = int(row[0])
                src, dst = str(row[2]), str(row[3])
            except (TypeError, ValueError, IndexError):
                diag["network"]["malformed"] += 1
                continue
            if ts < start:
                continue
            if ts > day_end:
                break
            diag["network"]["parsed"] += 1
            diag["network"]["flows"] += 1
            diag["network"]["max_timestamp"] = ts
            idx = (ts - start) // WIDTH_SECONDS
            mask = 1 << idx
            _ensure(bits, src)[2] |= mask
            _ensure(bits, dst)[2] |= mask

    hmax = diag["host"]["max_timestamp"]
    nmax = diag["network"]["max_timestamp"]
    if hmax is None or nmax is None:
        raise RuntimeError("one stream has no observations in common interval")
    end = min(day_end, int(hmax), int(nmax))
    if end < start:
        raise RuntimeError("empty common interval after stream scan")
    n_windows = (end - start) // WIDTH_SECONDS + 1
    diag["interval_end"] = end
    diag["n_windows"] = n_windows
    diag["window_width_seconds"] = WIDTH_SECONDS

    devices = np.array(sorted(bits), dtype=object)
    states = np.zeros((len(devices), n_windows, len(CHANNELS)), dtype=np.uint8)
    for di, device in enumerate(devices):
        for ci, encoded in enumerate(bits[device]):
            value = encoded
            while value:
                low = value & -value
                idx = low.bit_length() - 1
                if idx < n_windows:
                    states[di, idx, ci] = 1
                value ^= low

    diag["unique_devices"] = int(len(devices))
    diag["active_device_windows"] = int(np.any(states > 0, axis=2).sum())
    diag["channel_active_rows"] = {
        CHANNELS[i]: int(states[:, :, i].sum()) for i in range(len(CHANNELS))
    }
    return devices, states, diag


def stable_fold(device: str, k: int = FOLDS) -> int:
    d = hashlib.sha256(device.encode("utf-8")).digest()
    return int.from_bytes(d[:8], "big") % k


def transition_counts(states: np.ndarray, device_mask: np.ndarray, target_index: int) -> tuple[np.ndarray, np.ndarray]:
    s = states[device_mask]
    if s.shape[1] < 2:
        raise RuntimeError("at least two windows are required")
    x = s[:, :-1, :].reshape(-1, 3)
    y = s[:, 1:, target_index].reshape(-1)
    code = (x[:, 0] * 4 + x[:, 1] * 2 + x[:, 2]).astype(np.int8)
    neg = np.bincount(code[y == 0], minlength=8).astype(np.int64)
    pos = np.bincount(code[y == 1], minlength=8).astype(np.int64)
    return neg, pos


def weighted_rows(neg: np.ndarray, pos: np.ndarray):
    X, y, w = [], [], []
    for code in range(8):
        if neg[code] > 0:
            X.append(PATTERNS[code]); y.append(0); w.append(neg[code])
        if pos[code] > 0:
            X.append(PATTERNS[code]); y.append(1); w.append(pos[code])
    return np.asarray(X, float), np.asarray(y, int), np.asarray(w, float)


def weighted_binary_mi(neg: np.ndarray, pos: np.ndarray, feature_index: int) -> float:
    counts = np.zeros((2, 2), dtype=float)
    for code in range(8):
        x = int(PATTERNS[code, feature_index])
        counts[x, 0] += neg[code]
        counts[x, 1] += pos[code]
    total = counts.sum()
    if total <= 0:
        return 0.0
    px = counts.sum(axis=1) / total
    py = counts.sum(axis=0) / total
    out = 0.0
    for x in range(2):
        for y in range(2):
            pxy = counts[x, y] / total
            if pxy > 0 and px[x] > 0 and py[y] > 0:
                out += pxy * np.log(pxy / (px[x] * py[y]))
    return float(out)


def add_interactions(X: np.ndarray, selected: list[int]) -> np.ndarray:
    if not selected:
        return np.zeros((len(X), 0), float)
    z = X[:, selected]
    pairs = list(itertools.combinations(range(len(selected)), 2))
    if pairs:
        z = np.column_stack([z] + [z[:, a] * z[:, b] for a, b in pairs])
    return z


def fit_from_counts(neg: np.ndarray, pos: np.ndarray, screen_c: float) -> dict:
    X, y, w = weighted_rows(neg, pos)
    total = float(neg.sum() + pos.sum())
    prevalence = float(pos.sum() / total) if total else 0.5
    if len(np.unique(y)) < 2:
        p = float(np.clip(prevalence, 1e-6, 1 - 1e-6))
        return {
            "selected": [], "selected_names": [], "fallback_used": False,
            "pattern_probabilities": [p] * 8, "prevalence": prevalence,
            "screen_c": screen_c,
        }

    screen = LogisticRegression(
        penalty="l1", C=screen_c, solver="liblinear",
        max_iter=500, fit_intercept=True,
    )
    screen.fit(X, y, sample_weight=w)
    coef = screen.coef_[0]
    ranked = np.argsort(-np.abs(coef))
    selected = [int(i) for i in ranked if abs(coef[i]) > 1e-6][:MAX_PARENTS]
    fallback = False
    if not selected:
        mis = [weighted_binary_mi(neg, pos, i) for i in range(3)]
        selected = [int(np.argmax(mis))]
        fallback = True

    Z = add_interactions(X, selected)
    local = LogisticRegression(C=LOCAL_C, solver="lbfgs", max_iter=500, fit_intercept=True)
    local.fit(Z, y, sample_weight=w)
    probs = local.predict_proba(add_interactions(PATTERNS, selected))[:, 1]
    main = [float(x) for x in local.coef_[0][:len(selected)]]
    return {
        "selected": selected,
        "selected_names": [CHANNELS[i] for i in selected],
        "fallback_used": fallback,
        "pattern_probabilities": [float(x) for x in probs],
        "prevalence": prevalence,
        "screen_c": float(screen_c),
        "screen_coefficients": [float(x) for x in coef],
        "main_coefficients": main,
    }


def fit_self(neg: np.ndarray, pos: np.ndarray, target_index: int) -> np.ndarray:
    X, y, w = [], [], []
    for code in range(8):
        x = int(PATTERNS[code, target_index])
        if neg[code] > 0:
            X.append([x]); y.append(0); w.append(neg[code])
        if pos[code] > 0:
            X.append([x]); y.append(1); w.append(pos[code])
    X = np.asarray(X, float); y = np.asarray(y, int); w = np.asarray(w, float)
    prevalence = float(pos.sum() / max(1, neg.sum() + pos.sum()))
    if len(np.unique(y)) < 2:
        return np.full(8, prevalence, float)
    model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=300)
    model.fit(X, y, sample_weight=w)
    return model.predict_proba(PATTERNS[:, [target_index]])[:, 1]


def score_counts(neg: np.ndarray, pos: np.ndarray, probs: np.ndarray) -> float:
    total = (neg + pos).sum()
    if total == 0:
        return float("nan")
    return float((neg * probs**2 + pos * (1.0 - probs)**2).sum() / total)


def fit_structure(states: np.ndarray, mask: np.ndarray, screen_c: float) -> dict:
    nodes, edges, signs = {}, [], {}
    for j, target in enumerate(CHANNELS):
        neg, pos = transition_counts(states, mask, j)
        model = fit_from_counts(neg, pos, screen_c)
        nodes[target] = model
        for parent, coef in zip(model["selected_names"], model.get("main_coefficients", [])):
            edge = f"{parent}[t-1]->{target}[t]"
            edges.append(edge)
            signs[edge] = int(np.sign(coef))
    return {"nodes": nodes, "edges": sorted(edges), "signs": signs}


def evaluate(states: np.ndarray, train_mask: np.ndarray, test_mask: np.ndarray, structure: dict) -> dict:
    out = {}
    for j, target in enumerate(CHANNELS):
        tr_neg, tr_pos = transition_counts(states, train_mask, j)
        te_neg, te_pos = transition_counts(states, test_mask, j)
        sparse = structure["nodes"][target]
        p_sparse = np.asarray(sparse["pattern_probabilities"], float)
        p_self = fit_self(tr_neg, tr_pos, j)
        p_prev = np.full(8, sparse["prevalence"], float)
        n = int((te_neg + te_pos).sum())
        b_sparse = score_counts(te_neg, te_pos, p_sparse)
        b_self = score_counts(te_neg, te_pos, p_self)
        b_prev = score_counts(te_neg, te_pos, p_prev)
        out[target] = {
            "n_test_transitions": n,
            "brier": {
                "model": b_sparse,
                "SelfLag": b_self,
                "Prevalence": b_prev,
            },
            "brier_difference_model_minus_self": b_sparse - b_self,
            "bss_vs_prevalence": 1.0 - b_sparse / b_prev if b_prev > 0 else None,
        }
    return out


def aggregate_variant(folds: list[dict], variant: str) -> dict:
    edge_sets = [set(f["variants"][variant]["edges"]) for f in folds]
    all_edges = sorted(set().union(*edge_sets))
    edge_frequency = {e: sum(e in s for s in edge_sets) for e in all_edges}
    pair_j = []
    for a, b in itertools.combinations(range(len(edge_sets)), 2):
        u = edge_sets[a] | edge_sets[b]
        pair_j.append(1.0 if not u else len(edge_sets[a] & edge_sets[b]) / len(u))
    brier = {}
    for target in CHANNELS:
        weights = np.array([f["variants"][variant]["evaluation"][target]["n_test_transitions"] for f in folds], float)
        vals = np.array([f["variants"][variant]["evaluation"][target]["brier"]["model"] for f in folds], float)
        self_vals = np.array([f["variants"][variant]["evaluation"][target]["brier"]["SelfLag"] for f in folds], float)
        prev_vals = np.array([f["variants"][variant]["evaluation"][target]["brier"]["Prevalence"] for f in folds], float)
        brier[target] = {
            "model": float(np.average(vals, weights=weights)),
            "SelfLag": float(np.average(self_vals, weights=weights)),
            "Prevalence": float(np.average(prev_vals, weights=weights)),
        }
        brier[target]["brier_difference_model_minus_self"] = brier[target]["model"] - brier[target]["SelfLag"]
        brier[target]["bss_vs_prevalence"] = 1.0 - brier[target]["model"] / brier[target]["Prevalence"] if brier[target]["Prevalence"] > 0 else None
    return {
        "mean_selected_edges_per_fold": float(np.mean([len(s) for s in edge_sets])),
        "selected_edges_per_fold": [len(s) for s in edge_sets],
        "edge_frequency": edge_frequency,
        "mean_pairwise_edge_jaccard": float(np.mean(pair_j)) if pair_j else 1.0,
        "brier": brier,
    }


def run_day(day: int, host_path: Path, network_path: Path) -> dict:
    devices, states, diagnostics = build_disjoint_panel(day, host_path, network_path)
    folds = np.array([stable_fold(str(d)) for d in devices], dtype=np.int8)
    fold_results = []
    for fold in range(FOLDS):
        test_mask = folds == fold
        train_mask = ~test_mask
        n_train_transitions = int(train_mask.sum() * (states.shape[1] - 1))
        scaled_c = FIXED_C * V2_REFERENCE_TRANSITIONS / max(1, n_train_transitions)
        variants = {}
        for name, screen_c in (("FixedFull", FIXED_C), ("ScaledFull", scaled_c)):
            structure = fit_structure(states, train_mask, screen_c)
            variants[name] = {
                "screen_c": float(screen_c),
                "edges": structure["edges"],
                "signs": structure["signs"],
                "nodes": {
                    target: {
                        "selected_names": structure["nodes"][target]["selected_names"],
                        "fallback_used": structure["nodes"][target]["fallback_used"],
                    } for target in CHANNELS
                },
                "evaluation": evaluate(states, train_mask, test_mask, structure),
            }
        fold_results.append({
            "fold": fold,
            "n_train_devices": int(train_mask.sum()),
            "n_test_devices": int(test_mask.sum()),
            "n_train_transitions": n_train_transitions,
            "variants": variants,
        })

    aggregate = {variant: aggregate_variant(fold_results, variant) for variant in ("FixedFull", "ScaledFull")}
    for target in CHANNELS:
        f = aggregate["FixedFull"]["brier"][target]["model"]
        s = aggregate["ScaledFull"]["brier"][target]["model"]
        aggregate["ScaledFull"]["brier"][target]["relative_change_vs_fixed"] = (s - f) / f if f > 0 else None

    return {
        "experiment_id": "V3-LANL-MULTIDAY-001",
        "status": "PASS",
        "day": day,
        "role": "development-semantic-correction" if day == 2 else "confirmatory-out-of-development",
        "channels": {
            "H_person_login": "EventID 4624/4625 AND de-identified person account matching User<digits>",
            "P_process": "EventID 4688/4689",
            "T_network": "netflow source or destination activity",
        },
        "diagnostics": diagnostics,
        "fold_results": fold_results,
        "aggregate": aggregate,
        "guardrails": {
            "attack_or_red_team_labels_read": False,
            "defensive_intervention_C_inferred": False,
            "counterfactual_effect_claim": False,
            "same_window_edges_allowed": False,
            "lanl_hyperparameter_tuning_performed": False,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", required=True, type=int)
    ap.add_argument("--host", required=True, type=Path)
    ap.add_argument("--network", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    result = run_day(args.day, args.host, args.network)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "day": result["day"],
        "role": result["role"],
        "interval": [result["diagnostics"]["interval_start"], result["diagnostics"]["interval_end"]],
        "unique_devices": result["diagnostics"]["unique_devices"],
        "fixed_edges": result["aggregate"]["FixedFull"]["mean_selected_edges_per_fold"],
        "scaled_edges": result["aggregate"]["ScaledFull"]["mean_selected_edges_per_fold"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
