from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
from sklearn.metrics import brier_score_loss

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
if str(SEMISYNTH) not in sys.path:
    sys.path.insert(0, str(SEMISYNTH))

import select_semisynthetic_estimator as sel  # noqa: E402
import run_semisynthetic_confirmatory_estimators as base  # noqa: E402

EXPERIMENT_ID = "V3-SCALE-001"
EXPECTED_FROZEN_ESTIMATOR_SHA256 = "d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31"
EXPECTED_SELECTION_EXPERIMENT = "V3-SS-SEL-001-C1"
EXPECTED_CAP = 8
HORIZON = 6
ANCHORS = ["A_person", "A_process", "A_technical"]
GRAPH_SIZES = [12, 24, 36, 48]
GRAPH_TRAJECTORIES = 600
SAMPLE_TRAJECTORIES = [300, 600, 1200]
SAMPLE_GRAPH_SIZE = 24
REPLICATES = [1, 2, 3]
MODELS = ["dchag", "dense"]


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def stable_seed(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16) % (2**32)


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30.0, 30.0)))


def endogenous_names(count: int) -> list[str]:
    if count < 12:
        raise ValueError("scaling benchmark requires at least 12 endogenous nodes")
    intermediate_count = count - 6
    return ["R", "C1", "C2", "C3", "C4"] + [f"X{i:02d}" for i in range(1, intermediate_count + 1)] + ["Y"]


def make_schema(endogenous_count: int) -> dict:
    endo = endogenous_names(endogenous_count)
    order = ANCHORS + endo
    return {
        "experiment_id": EXPERIMENT_ID,
        "horizon": HORIZON,
        "order": order,
        "anchor_nodes": ANCHORS,
        "controls": ["C1", "C2", "C3", "C4"],
        "target": "Y",
        "types": {node: "binary" for node in order},
        "endogenous_count": endogenous_count,
        "total_observed_nodes": len(order),
    }


def generate_dataset(endogenous_count: int, trajectories: int, replicate: int) -> tuple[pd.DataFrame, dict]:
    schema = make_schema(endogenous_count)
    order = schema["order"]
    endo = endogenous_names(endogenous_count)
    seed = stable_seed(f"{EXPERIMENT_ID}|generator|m{endogenous_count}|n{trajectories}|r{replicate}")
    rng = np.random.default_rng(seed)
    n = int(trajectories)
    h = HORIZON

    arrays = {node: np.zeros((n, h), dtype=np.int8) for node in order}
    base_prev = np.array([0.18, 0.34, 0.52], dtype=float)
    for a_idx, anchor in enumerate(ANCHORS):
        arrays[anchor][:, 0] = (rng.random(n) < base_prev[a_idx]).astype(np.int8)
        for t in range(1, h):
            p = np.clip(0.08 + 0.70 * arrays[anchor][:, t - 1] + 0.12 * base_prev[a_idx], 0.03, 0.93)
            arrays[anchor][:, t] = (rng.random(n) < p).astype(np.int8)

    for t in range(h):
        for j, node in enumerate(endo):
            anchor = ANCHORS[(j + replicate) % len(ANCHORS)]
            logit = np.full(n, -1.05 + 0.12 * ((j + replicate) % 5), dtype=float)
            logit += (0.72 + 0.04 * (j % 3)) * arrays[anchor][:, t]
            if j > 0:
                prev_same = endo[j - 1]
                sign = 1.0 if (j + replicate) % 4 else -1.0
                logit += sign * (0.48 + 0.05 * (j % 2)) * arrays[prev_same][:, t]
            if t > 0:
                logit += (0.68 + 0.04 * ((j + 1) % 3)) * arrays[node][:, t - 1]
            p = sigmoid(logit)
            arrays[node][:, t] = (rng.random(n) < p).astype(np.int8)

    frame = pd.DataFrame({
        "trajectory_id": np.repeat(np.arange(n, dtype=np.int64), h),
        "time": np.tile(np.arange(h, dtype=np.int64), n),
    })
    for node in order:
        frame[node] = arrays[node].reshape(-1)

    split_rng = np.random.default_rng(stable_seed(f"{EXPERIMENT_ID}|split|m{endogenous_count}|n{trajectories}|r{replicate}"))
    ids = np.arange(n, dtype=np.int64)
    split_rng.shuffle(ids)
    n_train = int(math.floor(0.8 * n))
    train_ids = set(ids[:n_train].tolist())
    frame["split"] = np.where(frame["trajectory_id"].isin(train_ids), "train", "test")
    return frame, schema


def split_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = frame[frame["split"] == "train"].drop(columns=["split"]).copy()
    test = frame[frame["split"] == "test"].drop(columns=["split"]).copy()
    return train, test


def verify_frozen_estimator(path: Path) -> dict:
    if sha256_file(path) != EXPECTED_FROZEN_ESTIMATOR_SHA256:
        raise RuntimeError("active corrected estimator SHA-256 mismatch")
    frozen = json.loads(path.read_text())
    if frozen.get("status") != "ACTIVE" or frozen.get("experiment_id") != EXPECTED_SELECTION_EXPERIMENT:
        raise RuntimeError("scaling benchmark requires active corrected C1 estimator")
    if frozen.get("max_parents") != EXPECTED_CAP or frozen.get("screening_C") != 0.05 or frozen.get("local_model_C") != 0.7:
        raise RuntimeError("frozen estimator configuration mismatch")
    if frozen.get("confirmatory_tuning_allowed"):
        raise RuntimeError("scaling benchmark cannot tune confirmatory estimator")
    return frozen


class PeakSampler:
    def __init__(self, interval: float = 0.01):
        self.interval = interval
        self.process = psutil.Process(os.getpid())
        self.baseline = self.process.memory_info().rss
        self.peak = self.baseline
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            try:
                self.peak = max(self.peak, self.process.memory_info().rss)
            except psutil.Error:
                pass
            self._stop.wait(self.interval)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2.0)
        try:
            self.peak = max(self.peak, self.process.memory_info().rss)
        except psutil.Error:
            pass


def target_brier(models, model_name: str, test: pd.DataFrame, schema: dict) -> float:
    X, y, _, data = sel.design(test, schema["order"], schema["target"])
    mask = data["time"].to_numpy() == HORIZON - 1
    target_model = models[schema["target"]]
    if model_name == "dchag":
        p = target_model.prob_matrix(X[mask])
    else:
        if target_model.constant is not None:
            p = np.full(int(mask.sum()), target_model.constant, dtype=float)
        else:
            p = target_model.model.predict_proba(X[mask])[:, 1]
    return float(brier_score_loss(y[mask], p))


def fit_single(model_name: str, endogenous_count: int, trajectories: int, replicate: int, frozen_estimator: Path) -> dict:
    verify_frozen_estimator(frozen_estimator)
    frame, schema = generate_dataset(endogenous_count, trajectories, replicate)
    train, test = split_frame(frame)
    train_units = int(train["trajectory_id"].nunique())
    test_units = int(test["trajectory_id"].nunique())
    if train_units != int(math.floor(0.8 * trajectories)) or train_units + test_units != trajectories:
        raise RuntimeError("deterministic train/test split count mismatch")

    gc.collect()
    sampler = PeakSampler()
    sampler.start()
    start = time.perf_counter()
    if model_name == "dchag":
        models = sel.fit_world(train, schema, EXPECTED_CAP)
    elif model_name == "dense":
        models = base.fit_dense(train, schema)
    else:
        raise ValueError(model_name)
    fit_seconds = time.perf_counter() - start
    sampler.stop()

    brier = target_brier(models, model_name, test, schema)
    nonanchors = [node for node in schema["order"] if node not in ANCHORS]
    admissible_specs = int(sum(len(sel.feature_specs(schema["order"], node)) for node in nonanchors))
    selected_edges = None
    selected_density = None
    max_selected_parents = None
    fallback_nodes = None
    if model_name == "dchag":
        selected_edges = int(len(sel.selected_edges(models)))
        selected_density = float(selected_edges / admissible_specs) if admissible_specs else 0.0
        max_selected_parents = int(max((len(m.selected) for m in models.values()), default=0))
        fallback_nodes = int(sum(bool(m.fallback) for m in models.values()))
        if max_selected_parents > EXPECTED_CAP:
            raise RuntimeError("DCHAG parent cap violated")

    mib = 1024.0 * 1024.0
    result = {
        "experiment_id": EXPERIMENT_ID,
        "model": model_name,
        "endogenous_nodes": int(endogenous_count),
        "total_observed_nodes": int(endogenous_count + len(ANCHORS)),
        "trajectories": int(trajectories),
        "train_trajectories": train_units,
        "test_trajectories": test_units,
        "horizon": HORIZON,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "replicate": int(replicate),
        "fit_seconds": float(fit_seconds),
        "baseline_rss_mib": float(sampler.baseline / mib),
        "peak_rss_mib": float(sampler.peak / mib),
        "incremental_peak_rss_mib": float(max(0, sampler.peak - sampler.baseline) / mib),
        "final_y_brier": brier,
        "admissible_feature_specs": admissible_specs,
        "selected_edges": selected_edges,
        "selected_edge_density": selected_density,
        "max_selected_parents": max_selected_parents,
        "mi_fallback_nodes": fallback_nodes,
        "generator_seed": int(stable_seed(f"{EXPERIMENT_ID}|generator|m{endogenous_count}|n{trajectories}|r{replicate}")),
        "private_oracle_access": False,
        "hyperparameter_tuning": False,
        "configuration_replacement": False,
    }
    return result


def unique_configurations() -> list[tuple[int, int]]:
    configs = {(m, GRAPH_TRAJECTORIES) for m in GRAPH_SIZES}
    configs.update({(SAMPLE_GRAPH_SIZE, n) for n in SAMPLE_TRAJECTORIES})
    return sorted(configs)


def run_suite(outdir: Path, frozen_estimator: Path) -> None:
    verify_frozen_estimator(frozen_estimator)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    child = Path(__file__).resolve()
    for endogenous_count, trajectories in unique_configurations():
        for replicate in REPLICATES:
            order = MODELS if replicate % 2 else list(reversed(MODELS))
            for model_name in order:
                cmd = [
                    sys.executable,
                    str(child),
                    "--single",
                    "--model", model_name,
                    "--endogenous", str(endogenous_count),
                    "--trajectories", str(trajectories),
                    "--replicate", str(replicate),
                    "--frozen-estimator", str(frozen_estimator),
                ]
                proc = subprocess.run(cmd, text=True, capture_output=True)
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"child fit failed for m={endogenous_count} n={trajectories} r={replicate} model={model_name}\n"
                        f"stdout={proc.stdout}\nstderr={proc.stderr}"
                    )
                line = proc.stdout.strip().splitlines()[-1]
                row = json.loads(line)
                rows.append(row)
                print(
                    f"SCALE_PROGRESS m={endogenous_count} n={trajectories} r={replicate} model={model_name} "
                    f"fit={row['fit_seconds']:.6f}s",
                    file=sys.stderr,
                    flush=True,
                )

    df = pd.DataFrame(rows).sort_values(["endogenous_nodes", "trajectories", "replicate", "model"]).reset_index(drop=True)
    expected_rows = len(unique_configurations()) * len(REPLICATES) * len(MODELS)
    if len(df) != expected_rows:
        raise RuntimeError(f"expected {expected_rows} scaling rows, got {len(df)}")
    df.to_csv(outdir / "SCALING_RAW_RESULTS.csv", index=False)
    metadata = {
        "experiment_id": EXPERIMENT_ID,
        "status": "raw_benchmark_complete",
        "graph_axis": {"endogenous_nodes": GRAPH_SIZES, "trajectories": GRAPH_TRAJECTORIES},
        "sample_axis": {"endogenous_nodes": SAMPLE_GRAPH_SIZE, "trajectories": SAMPLE_TRAJECTORIES},
        "replicates": REPLICATES,
        "models": MODELS,
        "unique_configurations": [{"endogenous_nodes": m, "trajectories": n} for m, n in unique_configurations()],
        "expected_rows": expected_rows,
        "frozen_estimator_sha256": EXPECTED_FROZEN_ESTIMATOR_SHA256,
        "private_oracle_access": False,
        "hyperparameter_tuning": False,
        "configuration_replacement": False,
    }
    (outdir / "SCALING_RAW_METADATA.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--single", action="store_true")
    mode.add_argument("--suite", action="store_true")
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument("--endogenous", type=int)
    parser.add_argument("--trajectories", type=int)
    parser.add_argument("--replicate", type=int)
    parser.add_argument("--frozen-estimator", type=Path, default=SEMISYNTH / "FROZEN_SEMISYNTHETIC_ESTIMATOR.json")
    parser.add_argument("--outdir", type=Path)
    args = parser.parse_args()

    if args.single:
        if args.model is None or args.endogenous is None or args.trajectories is None or args.replicate is None:
            parser.error("--single requires --model, --endogenous, --trajectories, and --replicate")
        result = fit_single(args.model, args.endogenous, args.trajectories, args.replicate, args.frozen_estimator)
        print(json.dumps(result, sort_keys=True))
    else:
        if args.outdir is None:
            parser.error("--suite requires --outdir")
        run_suite(args.outdir, args.frozen_estimator)


if __name__ == "__main__":
    main()
