from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "q1_dense_sequential_gformula"
B = 2000


def exact_signflip_p(d):
    d = np.asarray(d, float)
    obs = abs(d.mean())
    n = len(d)
    count = 0
    for bits in range(2 ** n):
        signs = np.array([1 if (bits >> i) & 1 else -1 for i in range(n)])
        if abs((d * signs).mean()) >= obs - 1e-15:
            count += 1
    return count / (2 ** n)


def bootstrap_mean_ci(d, seed=8172611):
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(B, len(d)))
    vals = d[idx].mean(axis=1)
    return float(np.quantile(vals, .025)), float(np.quantile(vals, .975))


def main():
    est = pd.read_csv(OUT / "effect_estimates.csv")
    gt = pd.read_csv(ROOT / "benchmarks" / "ground_truth_summary.csv")
    scored = est.merge(gt[["context", "control", "risk_reduction"]], on=["context", "control"], suffixes=("_estimate", "_truth"))
    scored["signed_error"] = scored.risk_reduction_estimate - scored.risk_reduction_truth
    scored["absolute_error"] = scored.signed_error.abs()
    scored.to_csv(OUT / "effect_accuracy.csv", index=False)

    retained = pd.read_csv(ROOT / "results" / "processed" / "effect_accuracy.csv")
    dchag = retained[retained.model == "DCHAG_full"].sort_values(["context", "control"])
    q = scored.sort_values(["context", "control"])
    assert list(zip(dchag.context, dchag.control)) == list(zip(q.context, q.control))
    d = dchag.absolute_error.to_numpy(float) - q.absolute_error.to_numpy(float)
    lo, hi = bootstrap_mean_ci(d)
    comparison = pd.DataFrame([{
        "comparator": "CrossFittedDenseSequentialGFormula",
        "dchag_mae": float(dchag.absolute_error.mean()),
        "comparator_mae": float(q.absolute_error.mean()),
        "mean_abs_error_difference_DCHAG_minus_comparator": float(d.mean()),
        "median_difference": float(np.median(d)),
        "ci95_low": lo,
        "ci95_high": hi,
        "p_exact_signflip": exact_signflip_p(d),
    }])
    comparison.to_csv(OUT / "paired_effect_comparison.csv", index=False)

    ranks = []
    for context, sub in q.groupby("context"):
        true = sub.set_index("control")["risk_reduction_truth"]
        pred = sub.set_index("control")["risk_reduction_estimate"].reindex(true.index)
        best = true.idxmax(); selected = pred.idxmax()
        regret = 0.0 if true[best] == 0 else float((true[best] - true[selected]) / true[best])
        ranks.append({
            "context": context,
            "kendall_tau": float(kendalltau(true.to_numpy(), pred.to_numpy()).statistic),
            "spearman_rho": float(spearmanr(true.to_numpy(), pred.to_numpy()).statistic),
            "selected_control": selected,
            "best_true_control": best,
            "normalized_regret": regret,
        })
    rdf = pd.DataFrame(ranks)
    rdf.to_csv(OUT / "ranking.csv", index=False)
    pd.DataFrame([{
        "mean_kendall": float(rdf.kendall_tau.mean()),
        "mean_spearman": float(rdf.spearman_rho.mean()),
        "mean_regret": float(rdf.normalized_regret.mean()),
    }]).to_csv(OUT / "ranking_summary.csv", index=False)
    (OUT / "scoring_manifest.json").write_text(json.dumps({
        "date": "2026-08-17",
        "ground_truth_read_after_estimation_freeze": True,
        "bootstrap_replicates": B,
        "exact_signflip_pairs": int(len(d)),
    }, indent=2), encoding="utf-8")
    print(comparison.to_string(index=False))
    print(rdf.to_string(index=False))

if __name__ == "__main__":
    main()
