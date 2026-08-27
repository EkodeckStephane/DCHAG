from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

EXPERIMENT_ID = "V3-SCALE-001"
GRAPH_SIZES = [12, 24, 36, 48]
GRAPH_TRAJECTORIES = 600
SAMPLE_GRAPH_SIZE = 24
SAMPLE_TRAJECTORIES = [300, 600, 1200]
REPLICATES = [1, 2, 3]
MODELS = ["dchag", "dense"]
HORIZON = 6


def expected_configurations() -> set[tuple[int, int]]:
    configs = {(m, GRAPH_TRAJECTORIES) for m in GRAPH_SIZES}
    configs.update({(SAMPLE_GRAPH_SIZE, n) for n in SAMPLE_TRAJECTORIES})
    return configs


def slope_loglog(x: np.ndarray, y: np.ndarray) -> dict:
    if np.any(x <= 0) or np.any(y <= 0):
        raise RuntimeError("log-log slope requires positive x and y")
    coef = np.polyfit(np.log(x.astype(float)), np.log(y.astype(float)), 1)
    pred = np.polyval(coef, np.log(x.astype(float)))
    ss_res = float(np.sum((np.log(y.astype(float)) - pred) ** 2))
    ss_tot = float(np.sum((np.log(y.astype(float)) - np.log(y.astype(float)).mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return {"slope": float(coef[0]), "intercept": float(coef[1]), "r2_log_space": float(r2)}


def validate_raw(df: pd.DataFrame) -> None:
    required = {
        "experiment_id", "model", "endogenous_nodes", "trajectories", "train_rows", "replicate",
        "fit_seconds", "baseline_rss_mib", "peak_rss_mib", "incremental_peak_rss_mib", "final_y_brier",
        "admissible_feature_specs", "private_oracle_access", "hyperparameter_tuning", "configuration_replacement",
    }
    if not required.issubset(df.columns):
        raise RuntimeError(f"missing raw scaling columns: {sorted(required - set(df.columns))}")
    if set(df["experiment_id"]) != {EXPERIMENT_ID}:
        raise RuntimeError("experiment ID mismatch")
    if set(df["model"]) != set(MODELS):
        raise RuntimeError("model set mismatch")
    if df[["fit_seconds", "peak_rss_mib", "incremental_peak_rss_mib", "final_y_brier"]].isna().any().any():
        raise RuntimeError("non-finite primary or sanity metrics")
    if not np.isfinite(df[["fit_seconds", "peak_rss_mib", "incremental_peak_rss_mib", "final_y_brier"]].to_numpy(float)).all():
        raise RuntimeError("non-finite scaling values")
    if (df["fit_seconds"] <= 0).any() or (df["peak_rss_mib"] <= 0).any():
        raise RuntimeError("non-positive timing or memory metric")
    if df["private_oracle_access"].astype(bool).any() or df["hyperparameter_tuning"].astype(bool).any() or df["configuration_replacement"].astype(bool).any():
        raise RuntimeError("scaling guardrail violated")

    actual_configs = set(map(tuple, df[["endogenous_nodes", "trajectories"]].drop_duplicates().to_numpy(int)))
    if actual_configs != expected_configurations():
        raise RuntimeError(f"configuration set mismatch: {actual_configs}")
    for m, n in sorted(expected_configurations()):
        sub = df[(df.endogenous_nodes == m) & (df.trajectories == n)]
        for model in MODELS:
            ss = sub[sub.model == model]
            if sorted(ss.replicate.astype(int).tolist()) != REPLICATES:
                raise RuntimeError(f"replicate set mismatch for m={m}, n={n}, model={model}")
    dchag = df[df.model == "dchag"]
    if dchag["max_selected_parents"].isna().any() or (dchag["max_selected_parents"].astype(int) > 8).any():
        raise RuntimeError("DCHAG parent cap violated")


def medians(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "fit_seconds", "baseline_rss_mib", "peak_rss_mib", "incremental_peak_rss_mib", "final_y_brier",
        "admissible_feature_specs", "selected_edges", "selected_edge_density", "mi_fallback_nodes",
    ]
    agg = df.groupby(["endogenous_nodes", "trajectories", "train_rows", "model"], as_index=False)[cols].median(numeric_only=True)
    agg = agg.rename(columns={c: f"median_{c}" for c in cols})
    return agg.sort_values(["endogenous_nodes", "trajectories", "model"]).reset_index(drop=True)


def row_for(summary: pd.DataFrame, m: int, n: int, model: str) -> pd.Series:
    sub = summary[(summary.endogenous_nodes == m) & (summary.trajectories == n) & (summary.model == model)]
    if len(sub) != 1:
        raise RuntimeError(f"summary row missing/duplicated for m={m}, n={n}, model={model}")
    return sub.iloc[0]


def paired_ratio(summary: pd.DataFrame, m: int, n: int, metric: str) -> float | None:
    d = float(row_for(summary, m, n, "dchag")[metric])
    g = float(row_for(summary, m, n, "dense")[metric])
    if d <= 0:
        return None
    return float(g / d)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.raw)
    validate_raw(df)
    summary = medians(df)

    graph_slopes = {}
    sample_slopes = {}
    for model in MODELS:
        g = summary[(summary.model == model) & (summary.trajectories == GRAPH_TRAJECTORIES) & summary.endogenous_nodes.isin(GRAPH_SIZES)].sort_values("endogenous_nodes")
        if g.endogenous_nodes.astype(int).tolist() != GRAPH_SIZES:
            raise RuntimeError(f"graph axis incomplete for {model}")
        graph_slopes[model] = slope_loglog(g.endogenous_nodes.to_numpy(float), g.median_fit_seconds.to_numpy(float))

        s = summary[(summary.model == model) & (summary.endogenous_nodes == SAMPLE_GRAPH_SIZE) & summary.trajectories.isin(SAMPLE_TRAJECTORIES)].sort_values("trajectories")
        if s.trajectories.astype(int).tolist() != SAMPLE_TRAJECTORIES:
            raise RuntimeError(f"sample axis incomplete for {model}")
        sample_slopes[model] = slope_loglog(s.train_rows.to_numpy(float), s.median_fit_seconds.to_numpy(float))

    largest_graph = {
        "endogenous_nodes": max(GRAPH_SIZES),
        "trajectories": GRAPH_TRAJECTORIES,
        "dense_over_dchag_fit_time_ratio": paired_ratio(summary, max(GRAPH_SIZES), GRAPH_TRAJECTORIES, "median_fit_seconds"),
        "dense_over_dchag_incremental_memory_ratio": paired_ratio(summary, max(GRAPH_SIZES), GRAPH_TRAJECTORIES, "median_incremental_peak_rss_mib"),
    }
    largest_sample = {
        "endogenous_nodes": SAMPLE_GRAPH_SIZE,
        "trajectories": max(SAMPLE_TRAJECTORIES),
        "dense_over_dchag_fit_time_ratio": paired_ratio(summary, SAMPLE_GRAPH_SIZE, max(SAMPLE_TRAJECTORIES), "median_fit_seconds"),
        "dense_over_dchag_incremental_memory_ratio": paired_ratio(summary, SAMPLE_GRAPH_SIZE, max(SAMPLE_TRAJECTORIES), "median_incremental_peak_rss_mib"),
    }

    dchag_graph = summary[(summary.model == "dchag") & (summary.trajectories == GRAPH_TRAJECTORIES) & summary.endogenous_nodes.isin(GRAPH_SIZES)].sort_values("endogenous_nodes")
    density = [
        {
            "endogenous_nodes": int(r.endogenous_nodes),
            "total_observed_nodes": int(r.endogenous_nodes + 3),
            "median_selected_edges": float(r.median_selected_edges),
            "median_admissible_feature_specs": float(r.median_admissible_feature_specs),
            "median_selected_edge_density": float(r.median_selected_edge_density),
        }
        for _, r in dchag_graph.iterrows()
    ]

    result = {
        "experiment_id": EXPERIMENT_ID,
        "status": "PASS",
        "pass_definition": "protocol-complete benchmark with all frozen configurations and replicates retained; PASS is not estimator superiority",
        "n_raw_rows": int(len(df)),
        "n_unique_configurations": int(len(expected_configurations())),
        "replicates_per_model_configuration": len(REPLICATES),
        "graph_axis": {
            "endogenous_nodes": GRAPH_SIZES,
            "trajectories": GRAPH_TRAJECTORIES,
            "fit_time_loglog": graph_slopes,
            "dchag_minus_dense_slope": float(graph_slopes["dchag"]["slope"] - graph_slopes["dense"]["slope"]),
        },
        "sample_axis": {
            "endogenous_nodes": SAMPLE_GRAPH_SIZE,
            "trajectories": SAMPLE_TRAJECTORIES,
            "fit_time_loglog": sample_slopes,
            "dchag_minus_dense_slope": float(sample_slopes["dchag"]["slope"] - sample_slopes["dense"]["slope"]),
        },
        "largest_graph_configuration": largest_graph,
        "largest_sample_configuration": largest_sample,
        "dchag_graph_density": density,
        "guardrails": {
            "private_oracle_access": False,
            "hyperparameter_tuning": False,
            "configuration_or_replicate_replacement": False,
            "dchag_parent_cap_respected": True,
            "all_frozen_configurations_present": True,
        },
        "claim_boundary": "Observed runtime/memory scaling on this frozen synthetic benchmark and runner only; not an asymptotic complexity proof, production latency claim, causal-validity result, or universal superiority result.",
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.outdir / "SCALING_CONFIGURATION_MEDIANS.csv", index=False)
    (args.outdir / "SCALING_RESULTS.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "status": "PASS",
        "graph_slope_dchag": graph_slopes["dchag"]["slope"],
        "graph_slope_dense": graph_slopes["dense"]["slope"],
        "sample_slope_dchag": sample_slopes["dchag"]["slope"],
        "sample_slope_dense": sample_slopes["dense"]["slope"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
