# DCHAG frozen statistical analysis plan

Freeze date: 2026-08-17

This plan is frozen before the main retained experiment grid is executed.

## Experimental unit

The primary causal-comparison unit is a `(context, control)` pair. There are four contexts and four candidate controls per context, giving 16 paired units. Every method is scored against the same retained simulator truth for each unit.

## Primary causal endpoints

1. Absolute error of estimated risk reduction.
2. Signed error (bias) of estimated risk reduction.
3. Per-context Kendall tau between estimated and ground-truth control ranking.
4. Per-context Spearman rho.
5. Normalized regret of the top-ranked control: `(best_true_effect - true_effect_of_selected_control) / best_true_effect`, with zero defined when the best true effect is zero.

## Primary predictive endpoints

- Brier score for final target compromise.
- Log loss for final target compromise.

These are computed per context on the frozen test trajectories. They evaluate probability quality and are not substitutes for causal-effect accuracy.

## Primary comparisons

For causal effect error, DCHAG full is compared pairwise with:

- observational outcome model;
- technical-only SCM;
- no-human SCM;
- no-process SCM;
- no-temporal SCM.

SEAG-inspired and qualitative risk-matrix baselines are excluded from causal-effect tests because they do not define the required intervention estimand.

## Inferential procedure

### Effect-error comparisons

For each comparator, form the 16 paired differences in absolute error: `error_DCHAG - error_baseline`. Report:

- paired mean difference;
- paired median difference;
- 95% percentile bootstrap confidence interval for the paired mean (2,000 resamples of the 16 paired units, seed 62026);
- two-sided paired sign-flip permutation p-value for the mean difference (exact enumeration when feasible; otherwise deterministic Monte Carlo with at least 100,000 sign flips).

Correct the five p-values in this endpoint family with Holm's procedure.

### Predictive-score comparisons

Within each context, use paired trajectory-level score differences. Report the mean difference with a 95% bootstrap interval. Aggregate using a context-stratified bootstrap that resamples trajectories within each context and gives each context equal weight. Holm correction is applied within the Brier-score family and separately within the log-loss family.

### Ranking and regret

Because only four contexts are available, ranking coefficients and regret are reported per context plus mean/median across contexts. Confidence intervals are obtained by resampling contexts only as a sensitivity summary; no asymptotic normal p-value is used as primary evidence.

## Robustness analysis

Missing-evidence variants are evaluated at 0%, 10%, 30%, and 50%. Report each metric at every level and the normalized area under the degradation curve. The `human_process_unobserved` variant is a distinct structural observability stress test and is not placed on the MCAR curve.

A structural-edge-drop stress test removes a frozen 20% of non-control parent edges from the fitted DCHAG graph using seed 73117. This is a misspecification test; it does not retrain or retune the benchmark.

## Effect sizes and interpretation

Statistical significance alone does not establish practical advantage. Every inferential comparison must include the absolute metric difference and confidence interval. Negative or null differences remain in the manuscript and narrow the claims.

## Reproducibility

- benchmark seeds are in each benchmark manifest;
- main estimator seed base: 51000;
- bootstrap seed: 62026;
- structural-misspecification seed: 73117;
- no post-hoc run exclusions;
- any code correction after retained execution increments the experiment manifest version and forces a complete rerun of affected outputs.
