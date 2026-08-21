from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, math
import numpy as np
import pandas as pd
from scipy.special import ndtr

LINKS = ("logistic", "probit", "cloglog", "soft_threshold")


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def link_probability(eta: np.ndarray, link: str) -> np.ndarray:
    if link == "logistic":
        p = sigmoid(eta)
    elif link == "probit":
        p = ndtr(eta)
    elif link == "cloglog":
        p = 1.0 - np.exp(-np.exp(np.clip(eta, -8, 5)))
    elif link == "soft_threshold":
        p = 0.08 + 0.84 * sigmoid(3.0 * eta)
    else:
        raise ValueError(link)
    return np.clip(p, 0.005, 0.995)


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: str | Path, obj) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def flatten_frame(states: np.ndarray, node_ids: list[str]) -> pd.DataFrame:
    n, h, _ = states.shape
    d = {"trajectory_id": np.repeat(np.arange(n), h), "time": np.tile(np.arange(h), n)}
    flat = states.reshape(n*h, len(node_ids))
    for j, nid in enumerate(node_ids): d[nid] = flat[:, j]
    return pd.DataFrame(d)


def exact_signflip_p(diffs: np.ndarray) -> float:
    diffs = np.asarray(diffs, float)
    diffs = diffs[np.isfinite(diffs)]
    n = len(diffs)
    if n == 0: return float("nan")
    obs = abs(float(diffs.mean()))
    if n <= 20:
        total = 1 << n; ge = 0
        for mask in range(total):
            signs = np.fromiter((1.0 if (mask >> i) & 1 else -1.0 for i in range(n)), float, count=n)
            ge += abs(float(np.mean(diffs * signs))) >= obs - 1e-15
        return ge / total
    rng = np.random.default_rng(99181)
    vals = []
    for _ in range(200000):
        signs = rng.choice([-1.0,1.0], size=n)
        vals.append(abs(float(np.mean(diffs*signs))))
    return float(np.mean(np.asarray(vals) >= obs))


def bootstrap_mean_ci(values: np.ndarray, seed: int = 99182, reps: int = 10000):
    values = np.asarray(values, float)
    rng = np.random.default_rng(seed)
    sims = np.empty(reps)
    n = len(values)
    for i in range(reps): sims[i] = np.mean(values[rng.integers(0,n,size=n)])
    return float(np.quantile(sims,.025)), float(np.quantile(sims,.975))


def rank_metrics(true_eff: dict[str,float], est_eff: dict[str,float]):
    from scipy.stats import kendalltau, spearmanr
    cs = sorted(true_eff)
    t = np.array([true_eff[c] for c in cs], float)
    e = np.array([est_eff[c] for c in cs], float)
    kt = float(kendalltau(t,e).statistic)
    sp = float(spearmanr(t,e).statistic)
    best_est = cs[int(np.argmax(e))]
    best_true = float(np.max(t))
    regret = best_true - float(true_eff[best_est])
    denom = max(abs(best_true), 1e-12)
    return kt, sp, regret/denom, best_est
