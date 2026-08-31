from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

EXPECTED_TRAJECTORY_SHA256 = "6c45852d95ce583aa95e39d6560ce2ef61a8f1e84e51c01cc38292c113cd1d22"
GRID_WINDOWS = 181
HORIZON = 6
DEV_FAMILIES = ["helpdesk_identity", "bec_payment", "exfiltration", "itot_change"]
DEV_SEEDS = [21011, 22011, 23011, 24011]
CONFIRMATORY_SEEDS = {
    "helpdesk_identity": [31011, 31148, 31285, 31422],
    "bec_payment": [32011, 32148, 32285, 32422],
    "exfiltration": [33011, 33148, 33285, 33422],
    "itot_change": [34011, 34148, 34285, 34422],
}
ORDER = [
    "A_person", "A_process", "A_technical", "R", "C1", "C2", "C3", "C4",
    "H1", "H2", "P1", "P2", "T1", "T2", "Y",
]
TYPES = {
    "A_person": "anchor", "A_process": "anchor", "A_technical": "anchor", "R": "context",
    "C1": "control", "C2": "control", "C3": "control", "C4": "control",
    "H1": "human", "H2": "human", "P1": "process", "P2": "process",
    "T1": "technical", "T2": "technical", "Y": "technical",
}
CONTROLS = ["C1", "C2", "C3", "C4"]
TARGET = "Y"


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30.0, 30.0)))


def normal_cdf_approx(x: np.ndarray) -> np.ndarray:
    z = np.asarray(x, float)
    sign = np.where(z < 0, -1.0, 1.0)
    a = np.abs(z) / math.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * a)
    erf = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-a * a)
    erf *= sign
    return 0.5 * (1.0 + erf)


def link_probability(eta: np.ndarray, link: str) -> np.ndarray:
    if link == "logistic":
        p = sigmoid(eta)
    elif link == "probit":
        p = normal_cdf_approx(eta)
    elif link == "cloglog":
        p = 1.0 - np.exp(-np.exp(np.clip(eta, -8.0, 5.0)))
    elif link == "soft_threshold":
        p = 0.08 + 0.84 * sigmoid(3.0 * eta)
    else:
        raise ValueError(f"unknown link {link}")
    return np.clip(p, 0.005, 0.995)


def _r(rng: np.random.Generator, lo: float, hi: float) -> float:
    return float(rng.uniform(lo, hi))


def _parent(node: str, lag: int, coef: float) -> dict:
    return {"node": node, "lag": int(lag), "coef": float(coef)}


def _inter(a: str, lag_a: int, b: str, lag_b: int, coef: float) -> dict:
    return {"a": a, "lag_a": int(lag_a), "b": b, "lag_b": int(lag_b), "coef": float(coef)}


def make_world_spec(family: str, seed: int) -> dict:
    if family not in DEV_FAMILIES:
        raise ValueError(family)
    rng = np.random.default_rng(seed)
    rotations = {
        "helpdesk_identity": ["logistic", "probit", "cloglog", "soft_threshold"],
        "bec_payment": ["probit", "cloglog", "soft_threshold", "logistic"],
        "exfiltration": ["cloglog", "soft_threshold", "logistic", "probit"],
        "itot_change": ["soft_threshold", "logistic", "probit", "cloglog"],
    }
    links = rotations[family]
    nodes: dict[str, dict] = {}
    nodes["R"] = {
        "intercept": _r(rng, -1.4, -0.8), "link": links[0],
        "parents": [
            _parent("A_person", 0, _r(rng, .25, .65)), _parent("A_process", 0, _r(rng, .35, .75)),
            _parent("A_technical", 0, _r(rng, .45, .90)), _parent("R", 1, _r(rng, 1.15, 1.75)),
            _parent("C1", 1, _r(rng, -.70, -.30)),
        ],
        "interactions": [_inter("A_process", 0, "A_technical", 0, _r(rng, .20, .55))],
    }
    for i, c in enumerate(CONTROLS):
        anchor = ["A_person", "A_process", "A_technical", "A_technical"][i]
        lag_risk = ["T1", "P2", "T2", "H2"][i]
        parents = [
            _parent("R", 0, _r(rng, .55, 1.00)), _parent(anchor, 0, _r(rng, .20, .55)),
            _parent(c, 1, _r(rng, 1.70, 2.50)), _parent(lag_risk, 1, _r(rng, .25, .65)),
        ]
        if i > 0:
            parents.append(_parent(CONTROLS[i - 1], 1, _r(rng, .10, .35)))
        nodes[c] = {
            "intercept": _r(rng, -2.2, -1.45), "link": "logistic", "parents": parents,
            "interactions": [_inter("R", 0, anchor, 0, _r(rng, .15, .40))],
        }
    nodes["H1"] = {
        "intercept": _r(rng, -2.0, -1.25), "link": links[1],
        "parents": [_parent("A_person", 0, _r(rng, .9, 1.5)), _parent("R", 0, _r(rng, .45, .85)),
                    _parent("C1", 0, _r(rng, -1.45, -.70)), _parent("H1", 1, _r(rng, .45, .95))],
        "interactions": [_inter("A_person", 0, "C1", 0, _r(rng, -.85, -.30))],
    }
    nodes["H2"] = {
        "intercept": _r(rng, -2.1, -1.30), "link": links[2],
        "parents": [_parent("H1", 0, _r(rng, .75, 1.35)), _parent("A_process", 0, _r(rng, .45, .95)),
                    _parent("R", 0, _r(rng, .35, .75)), _parent("C2", 0, _r(rng, -1.40, -.65)),
                    _parent("H2", 1, _r(rng, .35, .85))],
        "interactions": [_inter("H1", 0, "R", 0, _r(rng, .25, .60))],
    }
    nodes["P1"] = {
        "intercept": _r(rng, -2.05, -1.25), "link": links[3],
        "parents": [_parent("H1", 0, _r(rng, .70, 1.30)), _parent("H2", 0, _r(rng, .55, 1.15)),
                    _parent("A_process", 0, _r(rng, .55, 1.05)), _parent("C3", 0, _r(rng, -1.50, -.70)),
                    _parent("R", 1, _r(rng, .20, .55)), _parent("P1", 1, _r(rng, .45, .95))],
        "interactions": [_inter("H1", 0, "A_process", 0, _r(rng, .25, .65))],
    }
    nodes["P2"] = {
        "intercept": _r(rng, -2.15, -1.35), "link": links[0],
        "parents": [_parent("H2", 0, _r(rng, .75, 1.35)), _parent("P1", 0, _r(rng, .45, .95)),
                    _parent("A_technical", 0, _r(rng, .30, .75)), _parent("C2", 0, _r(rng, -1.30, -.60)),
                    _parent("P2", 1, _r(rng, .40, .90))],
        "interactions": [_inter("H2", 0, "A_technical", 0, _r(rng, .20, .55))],
    }
    nodes["T1"] = {
        "intercept": _r(rng, -2.25, -1.35), "link": links[1],
        "parents": [_parent("P1", 0, _r(rng, .85, 1.45)), _parent("P2", 0, _r(rng, .55, 1.10)),
                    _parent("A_technical", 0, _r(rng, .70, 1.25)), _parent("C4", 0, _r(rng, -1.65, -.75)),
                    _parent("T1", 1, _r(rng, .55, 1.10))],
        "interactions": [_inter("P1", 0, "C4", 0, _r(rng, -.75, -.25))],
    }
    nodes["T2"] = {
        "intercept": _r(rng, -2.35, -1.45), "link": links[2],
        "parents": [_parent("P2", 0, _r(rng, .80, 1.40)), _parent("T1", 0, _r(rng, .45, .95)),
                    _parent("A_technical", 0, _r(rng, .50, 1.00)), _parent("C3", 0, _r(rng, -1.50, -.70)),
                    _parent("T2", 1, _r(rng, .50, 1.05))],
        "interactions": [_inter("P2", 0, "A_technical", 0, _r(rng, .20, .55))],
    }
    family_extra = {
        "helpdesk_identity": ("H1", "P2", _r(rng, .35, .75)),
        "bec_payment": ("H2", "P1", _r(rng, .35, .75)),
        "exfiltration": ("P2", "T1", _r(rng, .30, .70)),
        "itot_change": ("H1", "T2", _r(rng, .20, .55)),
    }[family]
    src, dst, coef = family_extra
    nodes[dst]["parents"].append(_parent(src, 0, coef))
    nodes["Y"] = {
        "intercept": _r(rng, -3.0, -1.95), "link": links[3],
        "parents": [_parent("T1", 0, _r(rng, 1.00, 1.70)), _parent("T2", 0, _r(rng, 1.05, 1.80)),
                    _parent("H2", 0, _r(rng, .35, .75)), _parent("R", 0, _r(rng, .35, .75)),
                    _parent("C1", 0, _r(rng, -1.15, -.50)), _parent("C4", 0, _r(rng, -1.35, -.60)),
                    _parent("Y", 1, _r(rng, .70, 1.35))],
        "interactions": [_inter("T1", 0, "T2", 0, _r(rng, .40, .85)),
                         _inter("R", 0, "C4", 0, _r(rng, -.70, -.25))],
    }
    return {"family": family, "seed": int(seed), "horizon": HORIZON, "order": ORDER, "types": TYPES,
            "controls": CONTROLS, "target": TARGET, "nodes": nodes, "hidden_confounder_present": False,
            "real_anchor_nodes": ["A_person", "A_process", "A_technical"]}


def _value(states: np.ndarray, idx: dict[str, int], t: int, node: str, lag: int) -> np.ndarray:
    pt = t - lag
    if pt < 0:
        return np.zeros(states.shape[0], dtype=float)
    return states[:, pt, idx[node]].astype(float)


def simulate(spec: dict, anchors: np.ndarray, seed: int, interventions: dict[str, int] | None = None,
             uniforms: np.ndarray | None = None) -> np.ndarray:
    anchors = np.asarray(anchors, dtype=np.int8)
    if anchors.ndim != 3 or anchors.shape[1:] != (HORIZON, 3):
        raise ValueError(f"anchors shape must be (n,{HORIZON},3), got {anchors.shape}")
    n = anchors.shape[0]
    idx = {x: i for i, x in enumerate(ORDER)}
    states = np.zeros((n, HORIZON, len(ORDER)), dtype=np.int8)
    states[:, :, idx["A_person"]] = anchors[:, :, 0]
    states[:, :, idx["A_process"]] = anchors[:, :, 1]
    states[:, :, idx["A_technical"]] = anchors[:, :, 2]
    rng = np.random.default_rng(seed)
    if uniforms is None:
        uniforms = rng.random((n, HORIZON, len(ORDER)))
    interventions = interventions or {}
    for t in range(HORIZON):
        for node in ORDER[3:]:
            j = idx[node]
            if node in interventions:
                states[:, t, j] = int(interventions[node])
                continue
            ns = spec["nodes"][node]
            eta = np.full(n, float(ns["intercept"]), dtype=float)
            for p in ns["parents"]:
                eta += float(p["coef"]) * _value(states, idx, t, p["node"], int(p["lag"]))
            for z in ns["interactions"]:
                a = _value(states, idx, t, z["a"], int(z["lag_a"]))
                b = _value(states, idx, t, z["b"], int(z["lag_b"]))
                eta += float(z["coef"]) * a * b
            states[:, t, j] = (uniforms[:, t, j] < link_probability(eta, ns["link"])).astype(np.int8)
    return states


def flatten_states(states: np.ndarray, world_id: str, devices: list[str]) -> pd.DataFrame:
    n = len(devices)
    d: dict[str, Iterable] = {"trajectory_id": np.repeat(np.arange(n), HORIZON),
                              "device": np.repeat(np.asarray(devices, dtype=object), HORIZON),
                              "time": np.tile(np.arange(HORIZON), n),
                              "world": np.repeat(world_id, n * HORIZON)}
    flat = states.reshape(n * HORIZON, len(ORDER))
    for j, node in enumerate(ORDER):
        d[node] = flat[:, j]
    return pd.DataFrame(d)


def unique_devices(path: Path) -> list[str]:
    seen: set[str] = set()
    for q in pd.read_csv(path, usecols=["device"], chunksize=500_000):
        seen.update(q["device"].astype(str).tolist())
    return sorted(seen)


def allocate_devices(devices: list[str], devices_per_world: int = 1500) -> dict[str, list[str]]:
    ordered = sorted(devices, key=lambda d: stable_hash("dchag-v3-ss-oracle-001-device-order|" + d))
    required = 20 * devices_per_world
    if len(ordered) < required:
        raise RuntimeError(f"need at least {required} devices, found {len(ordered)}")
    ordered = ordered[:required]
    world_ids = [f"dev_{f}" for f in DEV_FAMILIES]
    for family in DEV_FAMILIES:
        for r in range(1, 5):
            world_ids.append(f"confirm_{family}_{r}")
    return {wid: ordered[i * devices_per_world:(i + 1) * devices_per_world] for i, wid in enumerate(world_ids)}


def extract_anchors(path: Path, world_devices: dict[str, list[str]], stage: str) -> dict[str, np.ndarray]:
    selected = [w for w in world_devices if (w.startswith("dev_") if stage == "development" else w.startswith("confirm_"))]
    device_to_world: dict[str, tuple[str, int]] = {}
    arrays: dict[str, np.ndarray] = {}
    starts: dict[str, np.ndarray] = {}
    for wid in selected:
        devs = world_devices[wid]
        arrays[wid] = np.zeros((len(devs), HORIZON, 3), dtype=np.int8)
        starts[wid] = np.array([stable_hash(f"dchag-v3-ss-oracle-001-segment|{wid}|{d}") % 176 for d in devs], dtype=int)
        for i, d in enumerate(devs):
            device_to_world[d] = (wid, i)
    usecols = ["device", "window_idx", "H_present", "P_present", "T_present"]
    for q in pd.read_csv(path, usecols=usecols, chunksize=400_000):
        q["device"] = q["device"].astype(str)
        q = q[q["device"].isin(device_to_world)]
        for row in q.itertuples(index=False):
            wid, i = device_to_world[row.device]
            rel = int(row.window_idx) - int(starts[wid][i])
            if 0 <= rel < HORIZON:
                arrays[wid][i, rel] = [int(bool(row.H_present)), int(bool(row.P_present)), int(bool(row.T_present))]
    return arrays


def schema_for(spec: dict, world_id: str) -> dict:
    return {"world": world_id, "family": spec["family"], "horizon": HORIZON, "order": ORDER, "types": TYPES,
            "controls": CONTROLS, "target": TARGET, "anchor_nodes": ["A_person", "A_process", "A_technical"],
            "estimand": "E[Y_5(do(Ck_0:5=0))-Y_5(do(Ck_0:5=1))] with other controls natural"}


def true_edges(spec: dict) -> list[list]:
    edges: set[tuple] = set()
    for child, ns in spec["nodes"].items():
        for p in ns["parents"]:
            edges.add((p["node"], int(p["lag"]), child))
        for z in ns["interactions"]:
            edges.add((z["a"], int(z["lag_a"]), child)); edges.add((z["b"], int(z["lag_b"]), child))
    return [list(x) for x in sorted(edges)]


def oracle_effects(spec: dict, anchors: np.ndarray, seed: int, reps: int) -> dict:
    if reps < 1:
        raise ValueError("oracle reps must be >=1")
    n = anchors.shape[0]
    expanded = np.repeat(anchors, reps, axis=0)
    rng = np.random.default_rng(seed)
    uniforms = rng.random((n * reps, HORIZON, len(ORDER)))
    yj = ORDER.index(TARGET)
    out: dict[str, dict] = {}
    for c in CONTROLS:
        s0 = simulate(spec, expanded, seed + 11, interventions={c: 0}, uniforms=uniforms)
        s1 = simulate(spec, expanded, seed + 11, interventions={c: 1}, uniforms=uniforms)
        y0 = s0[:, -1, yj].astype(float).reshape(n, reps)
        y1 = s1[:, -1, yj].astype(float).reshape(n, reps)
        unit_diff = (y0 - y1).mean(axis=1)
        out[c] = {"risk_do0": float(y0.mean()), "risk_do1": float(y1.mean()),
                  "risk_reduction": float(unit_diff.mean()),
                  "oracle_se_across_anchor_units": float(unit_diff.std(ddof=1) / math.sqrt(n)),
                  "anchor_units": int(n), "mc_reps_per_anchor": int(reps)}
    return out


def prevalence_frame(df: pd.DataFrame) -> dict[str, float]:
    return {x: float(df[x].mean()) for x in ORDER}


def build_stage(trajectory: Path, outdir: Path, stage: str, oracle_reps: int,
                devices_per_world: int = 1500, train_n: int = 1100) -> dict:
    if stage not in {"development", "confirmatory"}:
        raise ValueError(stage)
    actual_sha = sha256_file(trajectory)
    if actual_sha != EXPECTED_TRAJECTORY_SHA256:
        raise RuntimeError(f"trajectory SHA mismatch: {actual_sha}")
    if stage == "confirmatory" and oracle_reps < 100:
        raise RuntimeError("confirmatory oracle requires >=100 MC reps per anchor")
    if train_n >= devices_per_world:
        raise ValueError("train_n must be smaller than devices_per_world")
    devices = unique_devices(trajectory)
    allocation = allocate_devices(devices, devices_per_world)
    anchor_arrays = extract_anchors(trajectory, allocation, stage)
    if stage == "development":
        worlds = [(f"dev_{f}", f, s) for f, s in zip(DEV_FAMILIES, DEV_SEEDS)]
    else:
        worlds = [(f"confirm_{f}_{r}", f, s) for f in DEV_FAMILIES for r, s in enumerate(CONFIRMATORY_SEEDS[f], 1)]
    summary = {"stage": stage, "trajectory_sha256": actual_sha, "unique_source_devices": len(devices),
               "devices_per_world": devices_per_world, "train_units_per_world": train_n,
               "test_units_per_world": devices_per_world - train_n, "worlds": {},
               "guardrails": {"attack_or_red_team_labels_read": False, "LANL_defensive_intervention_inferred": False,
                              "real_anchor_treated_as_causal_truth": False, "hidden_confounder_present": False,
                              "estimator_private_SCM_access": False, "confirmatory_hyperparameter_tuning": False,
                              "confirmatory_world_replacement": False}}
    for world_id, family, seed in worlds:
        devs = allocation[world_id]; anchors = anchor_arrays[world_id]
        split_order = sorted(range(len(devs)), key=lambda i: stable_hash(f"dchag-v3-ss-oracle-001-split|{world_id}|{devs[i]}"))
        tr_idx = np.array(split_order[:train_n], dtype=int); te_idx = np.array(split_order[train_n:], dtype=int)
        spec = make_world_spec(family, seed)
        train_states = simulate(spec, anchors[tr_idx], seed + 10001)
        test_states = simulate(spec, anchors[te_idx], seed + 20001)
        train_df = flatten_states(train_states, world_id, [devs[i] for i in tr_idx])
        test_df = flatten_states(test_states, world_id, [devs[i] for i in te_idx])
        pub = outdir / "public" / world_id; prv = outdir / "private" / world_id
        pub.mkdir(parents=True, exist_ok=True); prv.mkdir(parents=True, exist_ok=True)
        train_df.to_csv(pub / "train.csv", index=False); test_df.to_csv(pub / "test.csv", index=False)
        write_json(pub / "schema.json", schema_for(spec, world_id)); write_json(prv / "world.json", spec)
        write_json(prv / "true_edges.json", true_edges(spec))
        oracle = oracle_effects(spec, anchors, seed + 90001, oracle_reps); write_json(prv / "oracle_effects.json", oracle)
        files = [pub / "train.csv", pub / "test.csv", pub / "schema.json", prv / "world.json", prv / "true_edges.json", prv / "oracle_effects.json"]
        write_json(outdir / "freeze" / f"{world_id}.json", {str(p.relative_to(outdir)): sha256_file(p) for p in files})
        anchor_prev = {"A_person": float(anchors[:, :, 0].mean()), "A_process": float(anchors[:, :, 1].mean()),
                       "A_technical": float(anchors[:, :, 2].mean()),
                       "units_with_all_three_at_least_once": float(np.mean(np.all(anchors.max(axis=1) == 1, axis=1))),
                       "all_zero_units": int(np.sum(np.all(anchors == 0, axis=(1, 2))))}
        summary["worlds"][world_id] = {"family": family, "seed": seed, "anchor_prevalence": anchor_prev,
                                         "train_prevalence": prevalence_frame(train_df), "test_prevalence": prevalence_frame(test_df),
                                         "oracle_effects": oracle, "true_edge_count": len(true_edges(spec)),
                                         "train_rows": int(len(train_df)), "test_rows": int(len(test_df))}
    write_json(outdir / f"SEMISYNTHETIC_{stage.upper()}_BUILD_SUMMARY.json", summary)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trajectory", type=Path, required=True); ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--stage", choices=["development", "confirmatory"], required=True); ap.add_argument("--oracle-reps", type=int, default=30)
    args = ap.parse_args()
    s = build_stage(args.trajectory, args.outdir, args.stage, args.oracle_reps)
    print(json.dumps({"stage": s["stage"], "worlds": list(s["worlds"]), "guardrails": s["guardrails"]}, indent=2))


if __name__ == "__main__":
    main()
