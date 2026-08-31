from __future__ import annotations

import hashlib
import itertools
import math
from pathlib import Path

import numpy as np

EXPERIMENT_ID = "V3-TMA-001-C1"
BASE_EXPERIMENT_ID = "V3-TMA-001"
BLOCKS = ("H", "P", "T", "C", "R")
COMPONENTS = ("direct",) + BLOCKS
ANCHORS = ("A_person", "A_process", "A_technical")
MC_REPS = 100
EXPECTED_CAP = 8
EXPECTED_FREEZE_SHA256 = "d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31"
BOOTSTRAP_REPS = 10000
BOOTSTRAP_SEED = 20260852


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def stable_seed(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16) % (2**32)


def coalition_list() -> list[tuple[str, ...]]:
    return [tuple(BLOCKS[i] for i in range(len(BLOCKS)) if (mask >> i) & 1) for mask in range(1 << len(BLOCKS))]


def coalition_key(coalition) -> str:
    c = tuple(x for x in BLOCKS if x in set(coalition))
    return "empty" if not c else "+".join(c)


def block_for_node(schema: dict, node: str) -> str | None:
    if node == schema["target"] or node in ANCHORS:
        return None
    typ = schema["types"][node]
    return {"human": "H", "process": "P", "technical": "T", "control": "C", "context": "R"}.get(typ)


def _fitted_probability(model, current: dict[str, np.ndarray], previous: dict[str, np.ndarray]) -> np.ndarray:
    fmap = {}
    for source, lag, name in model.specs:
        fmap[name] = current[source] if lag == 0 else previous[source]
    return model.prob_feature_map(fmap)


def simulate_fitted_states(models, schema: dict, anchors: np.ndarray, intervention_control: str,
                           intervention_value: int, uniforms: np.ndarray,
                           baseline_states: np.ndarray | None = None,
                           active_blocks: set[str] | None = None) -> np.ndarray:
    order = list(schema["order"])
    nonanchors = [n for n in order if n not in ANCHORS]
    idx = {n: i for i, n in enumerate(order)}
    n = len(anchors)
    h = int(schema["horizon"])
    if anchors.shape != (n, h, len(ANCHORS)):
        raise ValueError("anchor tensor shape mismatch")
    if uniforms.shape != (n, h, len(nonanchors)):
        raise ValueError(f"uniform shape mismatch: {uniforms.shape}")
    if baseline_states is not None and baseline_states.shape != (n, h, len(order)):
        raise ValueError("baseline state shape mismatch")
    states = np.zeros((n, h, len(order)), dtype=np.int8)
    for ai, anchor in enumerate(ANCHORS):
        states[:, :, idx[anchor]] = anchors[:, :, ai]
    previous = {node: np.zeros(n, dtype=np.int8) for node in order}
    for t in range(h):
        current = {anchor: states[:, t, idx[anchor]] for anchor in ANCHORS}
        for k, node in enumerate(nonanchors):
            j = idx[node]
            if node == intervention_control:
                value = np.full(n, int(intervention_value), dtype=np.int8)
            elif node != schema["target"] and active_blocks is not None and block_for_node(schema, node) not in active_blocks:
                if baseline_states is None:
                    raise ValueError("replay lock requested without baseline")
                value = baseline_states[:, t, j].copy()
            else:
                probability = _fitted_probability(models[node], current, previous)
                value = (uniforms[:, t, k] < probability).astype(np.int8)
            states[:, t, j] = value
            current[node] = value
        previous = {node: states[:, t, idx[node]].copy() for node in order}
    return states


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


def _oracle_value(states: np.ndarray, idx: dict[str, int], t: int, node: str, lag: int) -> np.ndarray:
    pt = t - lag
    if pt < 0:
        return np.zeros(states.shape[0], dtype=float)
    return states[:, pt, idx[node]].astype(float)


def oracle_probability(spec: dict, states: np.ndarray, idx: dict[str, int], t: int, node: str) -> np.ndarray:
    ns = spec["nodes"][node]
    eta = np.full(states.shape[0], float(ns["intercept"]), dtype=float)
    for p in ns["parents"]:
        eta += float(p["coef"]) * _oracle_value(states, idx, t, p["node"], int(p["lag"]))
    for z in ns["interactions"]:
        a = _oracle_value(states, idx, t, z["a"], int(z["lag_a"]))
        b = _oracle_value(states, idx, t, z["b"], int(z["lag_b"]))
        eta += float(z["coef"]) * a * b
    return link_probability(eta, ns["link"])


def simulate_oracle_states(spec: dict, anchors: np.ndarray, intervention_control: str,
                           intervention_value: int, uniforms: np.ndarray,
                           baseline_states: np.ndarray | None = None,
                           active_blocks: set[str] | None = None) -> np.ndarray:
    order = list(spec["order"])
    idx = {n: i for i, n in enumerate(order)}
    n = len(anchors)
    h = int(spec["horizon"])
    if uniforms.shape != (n, h, len(order)):
        raise ValueError("oracle uniform shape mismatch")
    states = np.zeros((n, h, len(order)), dtype=np.int8)
    for ai, anchor in enumerate(ANCHORS):
        states[:, :, idx[anchor]] = anchors[:, :, ai]
    schema = {"types": spec["types"], "target": spec["target"]}
    for t in range(h):
        for node in order[len(ANCHORS):]:
            j = idx[node]
            if node == intervention_control:
                states[:, t, j] = int(intervention_value)
            elif node != spec["target"] and active_blocks is not None and block_for_node(schema, node) not in active_blocks:
                if baseline_states is None:
                    raise ValueError("oracle replay lock requested without baseline")
                states[:, t, j] = baseline_states[:, t, j]
            else:
                p = oracle_probability(spec, states, idx, t, node)
                states[:, t, j] = (uniforms[:, t, j] < p).astype(np.int8)
    return states


def shapley_from_values(values: dict[tuple[str, ...], float]) -> dict[str, float]:
    n = len(BLOCKS)
    out = {}
    for g in BLOCKS:
        phi = 0.0
        rest = [x for x in BLOCKS if x != g]
        for r in range(len(rest) + 1):
            weight = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
            for subset in itertools.combinations(rest, r):
                s = tuple(x for x in BLOCKS if x in set(subset))
                sg = tuple(x for x in BLOCKS if x in set(subset) | {g})
                phi += weight * (values[sg] - values[s])
        out[g] = float(phi)
    return out


def _attribution_from_simulator(simulator, model_or_spec, schema: dict, anchors: np.ndarray,
                                world: str, model_name: str, control: str, mc_reps: int,
                                oracle: bool = False) -> dict:
    if len(anchors) != 1500:
        raise RuntimeError("typed attribution standardization requires exactly 1500 anchors")
    expanded = np.repeat(anchors, mc_reps, axis=0)
    seed = stable_seed(f"{EXPERIMENT_ID}|{world}|{model_name}|{control}|mechanism-replay")
    rng = np.random.default_rng(seed)
    h = int(schema["horizon"])
    if oracle:
        uniforms = rng.random((len(expanded), h, len(schema["order"])), dtype=np.float64)
    else:
        nonanchors = [n for n in schema["order"] if n not in ANCHORS]
        uniforms = rng.random((len(expanded), h, len(nonanchors)), dtype=np.float64)
    def call_sim(intervention_value, baseline_states=None, active_blocks=None):
        if oracle:
            return simulator(model_or_spec, expanded, control, intervention_value, uniforms, baseline_states, active_blocks)
        return simulator(model_or_spec, schema, expanded, control, intervention_value, uniforms, baseline_states, active_blocks)
    baseline = call_sim(0, None, None)
    yj = list(schema["order"]).index(schema["target"])
    y0 = baseline[:, -1, yj].astype(float)
    values: dict[tuple[str, ...], float] = {}
    risk1: dict[tuple[str, ...], float] = {}
    for coalition in coalition_list():
        hybrid = call_sim(1, baseline, set(coalition))
        y1 = hybrid[:, -1, yj].astype(float)
        values[coalition] = float(np.mean(y0 - y1))
        risk1[coalition] = float(y1.mean())
    ordinary = call_sim(1, None, None)
    ordinary_effect = float(np.mean(y0 - ordinary[:, -1, yj].astype(float)))
    full = tuple(BLOCKS)
    direct = float(values[tuple()])
    phi = shapley_from_values(values)
    components = {"direct": direct, **phi}
    closure = abs(values[full] - sum(components.values()))
    replay = abs(values[full] - ordinary_effect)
    return {"world": world, "model": model_name, "control": control, "seed": int(seed),
            "anchor_units": int(len(anchors)), "mc_reps_per_anchor": int(mc_reps),
            "risk_do0": float(y0.mean()), "full_risk_do1": risk1[full],
            "total_effect_replay": float(values[full]), "ordinary_effect_same_stream": ordinary_effect,
            "closure_error": float(closure), "replay_consistency_error": float(replay),
            "components": components,
            "coalition_values": {coalition_key(k): float(v) for k, v in values.items()}}


def fitted_attribution(models, schema: dict, anchors: np.ndarray, world: str, model_name: str,
                       control: str, mc_reps: int = MC_REPS) -> dict:
    return _attribution_from_simulator(simulate_fitted_states, models, schema, anchors, world, model_name,
                                       control, mc_reps, oracle=False)


def oracle_attribution(spec: dict, anchors: np.ndarray, world: str, control: str,
                       mc_reps: int = MC_REPS) -> dict:
    schema = {"order": spec["order"], "target": spec["target"], "horizon": spec["horizon"], "types": spec["types"]}
    return _attribution_from_simulator(simulate_oracle_states, spec, schema, anchors, world, "Oracle_SCM",
                                       control, mc_reps, oracle=True)


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


def bootstrap_ci(diffs: np.ndarray, reps: int = BOOTSTRAP_REPS, seed: int = BOOTSTRAP_SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(diffs)
    vals = np.empty(reps, dtype=float)
    for b in range(reps):
        vals[b] = float(np.mean(diffs[rng.integers(0, n, size=n)]))
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))
