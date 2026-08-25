from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
if str(SEMISYNTH) not in sys.path:
    sys.path.insert(0, str(SEMISYNTH))

import build_semisynthetic_oracle as base  # noqa: E402

EXPERIMENT_ID = "V3-SS-HC-001"
LEVELS = {"moderate": 0.50, "strong": 1.00}
ANCHORS = ["A_person", "A_process", "A_technical"]
GAMMA = {
    "C1": 0.55,
    "C2": 0.70,
    "C3": 0.65,
    "C4": 0.80,
    "H1": 0.25,
    "H2": 0.30,
    "P1": 0.25,
    "P2": 0.30,
    "T1": 0.35,
    "T2": 0.40,
    "Y": 1.00,
}
EXPECTED_WORLDS = sorted(
    [f"confirm_{family}_{i}" for family in base.DEV_FAMILIES for i in range(1, 5)]
)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def stable_seed(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16) % (2**32)


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def anchor_tensor_one_split(df: pd.DataFrame, horizon: int) -> np.ndarray:
    data = df.sort_values(["trajectory_id", "time"]).reset_index(drop=True)
    ids = np.array(sorted(data["trajectory_id"].unique()))
    if len(data) != len(ids) * horizon:
        raise RuntimeError("incomplete trajectory blocks")
    if not np.array_equal(data["trajectory_id"].to_numpy(), np.repeat(ids, horizon)):
        raise RuntimeError("trajectory blocks are not contiguous after sorting")
    if not np.array_equal(data["time"].to_numpy(), np.tile(np.arange(horizon), len(ids))):
        raise RuntimeError("trajectory time grid mismatch")
    return data[ANCHORS].to_numpy(np.int8).reshape(len(ids), horizon, len(ANCHORS))


def latent_path(anchors: np.ndarray, uniforms: np.ndarray) -> np.ndarray:
    n, h, _ = anchors.shape
    if uniforms.shape != (n, h):
        raise ValueError("latent uniform shape mismatch")
    u = np.zeros((n, h), dtype=np.int8)
    for t in range(h):
        a = anchors[:, t, :].astype(float)
        if t == 0:
            eta = -0.70 + 0.25 * a[:, 0] + 0.25 * a[:, 1] + 0.25 * a[:, 2]
        else:
            eta = -1.10 + 1.90 * u[:, t - 1] + 0.20 * a[:, 0] + 0.20 * a[:, 1] + 0.20 * a[:, 2]
        p = base.sigmoid(eta)
        u[:, t] = (uniforms[:, t] < p).astype(np.int8)
    return u


def _value(states: np.ndarray, idx: dict[str, int], t: int, node: str, lag: int) -> np.ndarray:
    pt = t - lag
    if pt < 0:
        return np.zeros(states.shape[0], dtype=float)
    return states[:, pt, idx[node]].astype(float)


def simulate_hidden(
    spec: dict,
    anchors: np.ndarray,
    level: float,
    seed: int,
    interventions: dict[str, int] | None = None,
    observed_uniforms: np.ndarray | None = None,
    latent_uniforms: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    anchors = np.asarray(anchors, dtype=np.int8)
    h = int(spec["horizon"])
    order = list(spec["order"])
    if anchors.ndim != 3 or anchors.shape[1:] != (h, 3):
        raise ValueError("anchor tensor shape mismatch")
    n = anchors.shape[0]
    rng = np.random.default_rng(seed)
    if observed_uniforms is None:
        observed_uniforms = rng.random((n, h, len(order)), dtype=np.float64)
    if latent_uniforms is None:
        latent_uniforms = rng.random((n, h), dtype=np.float64)
    if observed_uniforms.shape != (n, h, len(order)):
        raise ValueError("observed uniform shape mismatch")
    if latent_uniforms.shape != (n, h):
        raise ValueError("latent uniform shape mismatch")

    u = latent_path(anchors, latent_uniforms)
    idx = {node: i for i, node in enumerate(order)}
    states = np.zeros((n, h, len(order)), dtype=np.int8)
    for k, anchor in enumerate(ANCHORS):
        states[:, :, idx[anchor]] = anchors[:, :, k]
    interventions = interventions or {}

    for t in range(h):
        for node in order[3:]:
            j = idx[node]
            if node in interventions:
                states[:, t, j] = int(interventions[node])
                continue
            ns = spec["nodes"][node]
            eta = np.full(n, float(ns["intercept"]), dtype=float)
            for p in ns["parents"]:
                eta += float(p["coef"]) * _value(states, idx, t, p["node"], int(p["lag"]))
            for z in ns["interactions"]:
                av = _value(states, idx, t, z["a"], int(z["lag_a"]))
                bv = _value(states, idx, t, z["b"], int(z["lag_b"]))
                eta += float(z["coef"]) * av * bv
            eta += float(level) * float(GAMMA.get(node, 0.0)) * u[:, t].astype(float)
            probability = base.link_probability(eta, ns["link"])
            states[:, t, j] = (observed_uniforms[:, t, j] < probability).astype(np.int8)
    return states, u


def states_to_frame(states: np.ndarray, order: list[str]) -> pd.DataFrame:
    n, h, _ = states.shape
    out = pd.DataFrame(states.reshape(n * h, len(order)), columns=order)
    out.insert(0, "time", np.tile(np.arange(h, dtype=np.int64), n))
    out.insert(0, "trajectory_id", np.repeat(np.arange(n, dtype=np.int64), h))
    return out


def natural_split(spec: dict, anchors: np.ndarray, level_name: str, level: float, world: str, split: str) -> tuple[pd.DataFrame, dict]:
    seed = stable_seed(f"{EXPERIMENT_ID}|natural|{level_name}|{world}|{split}")
    states, u = simulate_hidden(spec, anchors, level, seed)
    frame = states_to_frame(states, list(spec["order"]))
    return frame, {
        "seed": int(seed),
        "latent_prevalence": float(u.mean()),
        "final_y_prevalence": float(frame[frame.time == int(spec["horizon"]) - 1][spec["target"]].mean()),
    }


def oracle_effects(spec: dict, anchors: np.ndarray, level_name: str, level: float, world: str, reps: int = 100) -> dict:
    if len(anchors) != 1500:
        raise RuntimeError("oracle requires exactly 1,500 split-qualified anchors")
    if reps != 100:
        raise RuntimeError("oracle MC repetitions are frozen at 100")
    expanded = np.repeat(anchors, reps, axis=0)
    n = len(anchors)
    h = int(spec["horizon"])
    order = list(spec["order"])
    results = {}
    for control in spec["controls"]:
        seed = stable_seed(f"{EXPERIMENT_ID}|oracle|{level_name}|{world}|{control}")
        rng = np.random.default_rng(seed)
        obs_uniforms = rng.random((len(expanded), h, len(order)), dtype=np.float64)
        u_uniforms = rng.random((len(expanded), h), dtype=np.float64)
        y0, u0 = simulate_hidden(
            spec, expanded, level, seed,
            interventions={control: 0}, observed_uniforms=obs_uniforms, latent_uniforms=u_uniforms,
        )
        y1, u1 = simulate_hidden(
            spec, expanded, level, seed,
            interventions={control: 1}, observed_uniforms=obs_uniforms, latent_uniforms=u_uniforms,
        )
        if not np.array_equal(u0, u1):
            raise RuntimeError("latent common-random-number invariant failed")
        target_idx = order.index(spec["target"])
        d = (
            y0[:, h - 1, target_idx].astype(float).reshape(n, reps)
            - y1[:, h - 1, target_idx].astype(float).reshape(n, reps)
        )
        unit = d.mean(axis=1)
        results[control] = {
            "risk_do0": float(y0[:, h - 1, target_idx].mean()),
            "risk_do1": float(y1[:, h - 1, target_idx].mean()),
            "risk_reduction": float(unit.mean()),
            "oracle_se_across_anchor_units": float(unit.std(ddof=1) / math.sqrt(n)),
            "anchor_units": n,
            "mc_reps_per_anchor": reps,
            "seed": int(seed),
        }
    return results


def validate_parent_worlds(public_root: Path, private_root: Path) -> list[str]:
    pub_worlds = sorted(p.name for p in public_root.iterdir() if p.is_dir() and p.name.startswith("confirm_"))
    prv_worlds = sorted(p.name for p in private_root.iterdir() if p.is_dir() and p.name.startswith("confirm_"))
    if pub_worlds != EXPECTED_WORLDS or prv_worlds != EXPECTED_WORLDS:
        raise RuntimeError("parent confirmatory world set mismatch")
    return pub_worlds


def generate_level(public_root: Path, private_root: Path, outroot: Path, level_name: str, level: float) -> dict:
    worlds = validate_parent_worlds(public_root, private_root)
    level_root = outroot / level_name
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "level_name": level_name,
        "lambda": float(level),
        "worlds": {},
        "guardrails": {
            "hidden_confounder_present": True,
            "hidden_confounder_written_to_public": False,
            "parent_outcomes_reused": False,
            "world_replacement": False,
            "hyperparameter_tuning": False,
            "oracle_mc_reps_per_anchor": 100,
        },
    }
    for world in worlds:
        pub = public_root / world
        prv = private_root / world
        schema = json.loads((pub / "schema.json").read_text())
        spec = json.loads((prv / "world.json").read_text())
        train_parent = pd.read_csv(pub / "train.csv")
        test_parent = pd.read_csv(pub / "test.csv")
        train_anchors = anchor_tensor_one_split(train_parent, int(schema["horizon"]))
        test_anchors = anchor_tensor_one_split(test_parent, int(schema["horizon"]))
        if len(train_anchors) != 1100 or len(test_anchors) != 400:
            raise RuntimeError("parent split counts mismatch")
        all_anchors = np.concatenate([train_anchors, test_anchors], axis=0)

        train, train_diag = natural_split(spec, train_anchors, level_name, level, world, "train")
        test, test_diag = natural_split(spec, test_anchors, level_name, level, world, "test")
        oracle = oracle_effects(spec, all_anchors, level_name, level, world, reps=100)

        public_dir = level_root / "public" / world
        private_dir = level_root / "private" / world
        public_dir.mkdir(parents=True, exist_ok=True)
        private_dir.mkdir(parents=True, exist_ok=True)
        train.to_csv(public_dir / "train.csv", index=False)
        test.to_csv(public_dir / "test.csv", index=False)
        public_schema = dict(schema)
        public_schema["experiment_id"] = EXPERIMENT_ID
        public_schema["hidden_confounder_observed"] = False
        write_json(public_dir / "schema.json", public_schema)

        private_spec = dict(spec)
        private_spec["hidden_confounder_present"] = True
        private_spec["hidden_confounder"] = {
            "name": "U",
            "observed": False,
            "level_name": level_name,
            "lambda": float(level),
            "gamma": GAMMA,
            "initial": "logistic(-0.70 + 0.25*A_person + 0.25*A_process + 0.25*A_technical)",
            "transition": "logistic(-1.10 + 1.90*U_lag1 + 0.20*A_person + 0.20*A_process + 0.20*A_technical)",
        }
        write_json(private_dir / "world.json", private_spec)
        write_json(private_dir / "oracle_effects.json", oracle)
        (private_dir / "true_edges.json").write_text((prv / "true_edges.json").read_text(), encoding="utf-8")

        forbidden = {"U", "latent_U", "world.json", "oracle_effects.json", "true_edges.json"}
        if any(x in train.columns or x in test.columns for x in ["U", "latent_U"]):
            raise RuntimeError("latent confounder leaked into public dataframe")
        if any(p.name in forbidden for p in public_dir.rglob("*") if p.is_file()):
            raise RuntimeError("private file leaked into public world")
        summary["worlds"][world] = {
            "family": schema["family"],
            "train": train_diag,
            "test": test_diag,
            "oracle_effects": oracle,
            "train_trajectories": 1100,
            "test_trajectories": 400,
            "standardization_anchor_units": 1500,
        }
    write_json(level_root / f"SEMISYNTHETIC_HC_{level_name.upper()}_BUILD_SUMMARY.json", summary)
    return summary


def build_manifests(outroot: Path) -> None:
    for level_name in LEVELS:
        level_root = outroot / level_name
        for partition in ["public", "private"]:
            root = level_root / partition
            files = sorted(p for p in root.rglob("*") if p.is_file())
            write_json(
                level_root / f"{partition.upper()}_MANIFEST.json",
                {
                    "experiment_id": EXPERIMENT_ID,
                    "level_name": level_name,
                    "partition": partition,
                    "files": {str(p.relative_to(root)): sha256_file(p) for p in files},
                    "contains_latent_variable_values": partition == "private" and False,
                    "contains_private_SCM_or_oracle": partition == "private",
                },
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-public-root", type=Path, required=True)
    parser.add_argument("--parent-private-root", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    overall = {"experiment_id": EXPERIMENT_ID, "levels": {}, "worlds": 16}
    for name, level in LEVELS.items():
        result = generate_level(args.parent_public_root, args.parent_private_root, args.outdir, name, level)
        overall["levels"][name] = {"lambda": level, "world_count": len(result["worlds"])}
    build_manifests(args.outdir)
    write_json(args.outdir / "SEMISYNTHETIC_HIDDEN_CONFOUNDING_BUILD_SUMMARY.json", overall)
    print(json.dumps(overall, sort_keys=True))


if __name__ == "__main__":
    main()
