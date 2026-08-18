# Q1 causal-baseline amendment v1.1 — dense sequential g-formula

Date frozen: 2026-08-17
Status: FROZEN BEFORE EXECUTION
Relationship to v1.0: post-v1.0 adversarial extension. The v1.0 full-history outcome g-formula revealed sparse support for complete sustained regimes. This amendment is fixed before executing the estimator below and will be retained regardless of result direction.

## Scientific purpose

Test whether DCHAG's intervention-effect fidelity survives comparison with a longitudinal g-computation model that factorizes the observed state process sequentially. The comparator deliberately avoids DCHAG's sparse parent graph: every attack-state variable is predicted from a dense admissible history. This tests whether the reported effect advantage is attributable only to comparing against a high-dimensional endpoint regression.

## Estimand

For each workflow and candidate control c, estimate the same sustained-regime population risk reduction as the frozen experiment:

Delta_c = E[Y(do(C=a0))] - E[Y(do(C=ac))],

where all controls are held at their baseline value at every time under a0, and ac activates only c at every time. Simulator ground truth is not read during fitting or estimation.

## Comparator: CrossFittedDenseSequentialGFormula

Unit: trajectory.
Training data: frozen observed training trajectories only (12,000/workflow).
Cross-fitting: 5 folds, trajectory-level, shuffled with seed 260817.
State learner: logistic regression with C=1e6, liblinear solver, max_iter=1000.

For each non-context, non-control attack-state node, the pooled longitudinal regression uses:

1. current root context;
2. every current control;
3. every earlier attack-state variable in the declared within-slice evaluation order;
4. one-step lag of root context, every control, and every attack-state variable.

The comparator receives the variable/evaluation order needed to replay a longitudinal process, but it receives no DCHAG parent edges, no simulator coefficients, no ground-truth effects, and no human/process/technical type-specific parent restriction. Consequently the true sparse parent set is contained inside a deliberately dense admissible history.

Held-out context histories are replayed under each sustained intervention. State transitions are sampled sequentially from the fold-specific fitted regressions. Baseline and intervention scenarios use common random numbers. Monte Carlo replication: 20 simulated paths per held-out context trajectory, giving 240,000 simulated paths per sustained regime/workflow across five folds. Seed family: 811700 + fold index.

## Positivity diagnostic

In addition to the complete-regime diagnostic retained in v1.0, report empirical local treatment support by workflow, control, time and current context stratum. For each target intervention state, record observed count and empirical probability. A local target probability below 0.05 is flagged as a severe support warning.

## Metrics and decision rule

Primary: absolute error of Delta_c on all 16 workflow-control pairs and MAE across pairs.
Paired comparison against DCHAG: difference in absolute error, 95% paired bootstrap CI with 2,000 replicates, and exact two-sided sign-flip test over 16 pairs.
Secondary: Kendall tau, Spearman rho and top-control normalized regret.

Decision rule:
- If DCHAG remains materially more accurate, report the dense sequential comparator and its local-positivity diagnostics, with claims confined to this synthetic benchmark and supplied structural assumptions.
- If results are statistically unresolved, remove effect-superiority language and emphasize explicit typed semantics, auditability and invariant workflow contract.
- If the dense sequential comparator is more accurate, retain the negative result and re-scope the manuscript before submission.

No estimator setting may be changed after first execution without a new versioned amendment preserving this output.
