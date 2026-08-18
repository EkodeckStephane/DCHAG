# Q1 causal-baseline amendment v1.0

Date frozen: 2026-08-17
Status: FROZEN BEFORE EXECUTION
Reason: the Q1 novelty-falsification audit identified prior work in business-process monitoring that estimates intervention effects from event logs, including causal-effect and doubly robust estimators. The retained DCHAG comparison set therefore requires a stronger observational causal comparator before manuscript freeze.

## Scientific purpose

This amendment does not alter the original confirmatory analysis or its frozen results. It adds a post-freeze adversarial comparator whose output will be retained regardless of direction. Its purpose is to test whether DCHAG's intervention-effect fidelity remains distinguishable from a flexible causal g-computation estimator trained on the same observational trajectories.

## Estimand

For each context and control c, estimate the same population risk-reduction estimand used by DCHAG:

Delta_c = E[Y(do(C=a0))] - E[Y(do(C=ac))],

where a0 fixes every defensive control to its baseline value at every time point and ac fixes control c to 1 at every time point while all other controls remain at baseline. The ground-truth simulator remains unread during estimation.

## Comparator: CrossFittedFlexibleGFormula

Unit: trajectory.
Training data: the existing frozen `benchmarks/<context>/train_observed.csv` only (12,000 trajectories/context).
Outcome: terminal target state at horizon-1.
Adjustment variables: complete observed root context history (`high_risk_context@t`).
Treatment variables: complete control history (`control@t`) for every control and time point.
No realized human/process/technical mediator is used as an adjustment feature.

Estimator:
- 5-fold stratified cross-fitting by trajectory;
- fixed fold seed 260817;
- outcome learner: `sklearn.ensemble.HistGradientBoostingClassifier`;
- `max_iter=250`, `learning_rate=0.05`, `max_leaf_nodes=31`, `min_samples_leaf=50`, `l2_regularization=1.0`, `early_stopping=False`;
- within each held-out fold, standardize every trajectory twice: all controls at baseline and selected control active at every time point;
- average held-out predicted risk differences across all trajectories.

The estimator is a causal g-formula comparator under conditional exchangeability, consistency and positivity for the specified sustained regimes. It is intentionally more flexible than the retained logistic `ObservationalOutcome` comparator.

## Positivity diagnostic

For each context and target regime:
- report the number of observed training trajectories exactly matching the full regime;
- fit treatment-assignment logistic models for every control/time indicator from same-time root context;
- report the mean and minimum estimated probability of the requested full regime and the expected support count (sum of regime probabilities).

No inverse-probability or doubly robust full-regime estimate will be promoted as a primary comparator when exact-regime support is sparse. This restriction is fixed before results are seen.

## Metrics

Primary extension metric: absolute error |estimated Delta_c - simulator truth Delta_c| on all 16 context-control pairs.
Summary: MAE across 16 pairs.
Paired comparison against DCHAG: paired absolute-error difference, bootstrap 95% CI over the 16 context-control pairs, and two-sided paired sign-flip/permutation test using the same deterministic exhaustive/sign-flip convention as the retained effect audit where applicable.
Secondary: Kendall tau, Spearman rho and top-control regret from estimated effects.

## Decision rule

- If DCHAG retains materially lower effect MAE and paired evidence supports the difference, the manuscript may state that DCHAG improves intervention-effect fidelity over both parametric observational standardization and the frozen flexible causal g-formula comparator in this synthetic benchmark.
- If the flexible causal comparator is statistically indistinguishable, the manuscript must remove any empirical superiority claim and frame DCHAG around explicit typed causal semantics, auditability and workflow invariance.
- If the flexible causal comparator is better, this negative result must be retained and the Q1 positioning must be re-scoped before submission.

No hyperparameter, feature, metric or decision-rule change is allowed after the first execution without a versioned amendment that preserves the original output.
