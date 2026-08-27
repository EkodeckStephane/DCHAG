# V3-SCALE-001 — Frozen computational and graph-size scaling protocol

## Status

FROZEN before any V3-SCALE-001 benchmark execution or result inspection.

## Purpose

This experiment characterizes the computational scaling of the already frozen DCHAG-C1 estimator relative to the already frozen dense sequential g-formula comparator. It is an engineering/scalability benchmark only. It does not estimate causal validity, transportability, hidden-confounding robustness, or real-world control effectiveness.

## Frozen estimators

DCHAG uses the active corrected estimator freeze from `experiments/v3/02_semisynthetic/FROZEN_SEMISYNTHETIC_ESTIMATOR.json`:

- experiment: `V3-SS-SEL-001-C1`
- SHA-256: `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`
- `max_parents = 8`
- L1 screening `C = 0.05`
- local logistic refit `C = 0.7`
- no hyperparameter tuning is permitted.

Dense-g uses the comparator already frozen for RQ1: `HistGradientBoostingClassifier(loss="log_loss", learning_rate=.07, max_iter=80, max_leaf_nodes=15, min_samples_leaf=30, l2_regularization=1.0)` with the same node-specific random-state rule.

## Controlled scaling generator

The benchmark uses a deterministic sparse dynamic binary generator with horizon 6. The first three variables are the same exogenous anchor names used by the RQ1 estimator code: `A_person`, `A_process`, and `A_technical`. The remaining variables are ordered endogenous nodes containing `R`, `C1`–`C4`, synthetic intermediate nodes, and final target `Y`.

Every endogenous node has at most three data-generating parents chosen deterministically from admissible same-slice predecessors and lag-1 history. Coefficients and intercepts are deterministic functions of node index and replicate seed. The generator is used only to supply non-degenerate benchmark data; its true graph is not used by either fitted estimator.

For each configuration, trajectories are split deterministically 80/20 into train/test sets. The benchmark times model fitting only; deterministic data generation and import/startup time are outside the fit timer.

## Frozen axes and configurations

### Graph-size axis

Fixed at 600 trajectories and horizon 6. The number of endogenous modeled nodes is:

`{12, 24, 36, 48}`

With the three anchors, the corresponding total observed-node counts are `{15, 27, 39, 51}`. The 12-node endogenous configuration matches the RQ1 modeled-node count (3 anchors + 12 endogenous variables = 15 total variables).

### Sample-size axis

Fixed at 24 endogenous modeled nodes and horizon 6. The trajectory counts are:

`{300, 600, 1200}`

The 600-trajectory configuration overlaps the graph-size axis and must be scored only once in the unique-configuration summary.

### Replicates

Three deterministic replicates per unique configuration, using replicate IDs `{1,2,3}`. No replicate may be dropped or replaced because of runtime, memory, accuracy, or comparative outcome.

## Execution environment

The workflow uses one `ubuntu-24.04` GitHub Actions runner for the full suite so DCHAG and dense-g comparisons share one machine allocation. Each estimator/configuration/replicate fit is executed in a fresh child Python process to prevent allocator carry-over between methods. The suite records the runner CPU description, logical CPU count, Python version, dependency freeze, and workflow head.

Frozen Python dependencies:

- numpy 2.4.6
- pandas 3.0.5
- scipy 1.17.0
- scikit-learn 1.8.0
- psutil 7.0.0
- pytest 9.1.1

## Endpoints

Primary computational endpoints, summarized by configuration using the median of three replicates:

1. fit wall-clock seconds;
2. incremental peak resident memory (MiB) above the pre-fit process baseline;
3. log-log graph-size slope of median fit time versus endogenous-node count, separately for DCHAG and dense-g;
4. log-log sample-size slope of median fit time versus training-row count, separately for DCHAG and dense-g.

Secondary endpoints:

- absolute peak RSS;
- held-out final-Y Brier score as a non-optimization sanity check;
- DCHAG selected-edge count and selected-edge density relative to its admissible feature-specification count;
- dense admissible feature-specification count;
- paired dense/DCHAG median fit-time and incremental-memory ratios at the largest graph and sample configurations.

No p-value threshold is used for the runtime endpoints. GitHub-hosted runner timing is an empirical engineering measurement, not a hardware-independent complexity proof. Slopes and ratios must be reported with their observed values rather than converted into a superiority claim.

## Frozen analysis

For each estimator and axis, the scorer fits ordinary least squares to `log(median_fit_seconds)` against `log(size)` over the frozen axis points. The sample-size x-axis is the number of training rows after the frozen 80/20 trajectory split.

The scorer must preserve every replicate and configuration. It must flag any fit failure, non-finite metric, missing replicate, unexpected estimator configuration, or DCHAG parent-cap violation.

## Guardrails

- no RQ1/RQ2/RQ3/RQ4 outcome is used to tune this benchmark;
- no private semi-synthetic oracle is required or read;
- no LANL attack/red-team label is read;
- no estimator hyperparameter is changed;
- no size point or replicate is replaced after inspection;
- benchmark accuracy is not used to select a size point;
- runtime results cannot be promoted as causal-effect superiority.

## Claim boundary

V3-SCALE-001 may support statements about observed computational scaling on the frozen synthetic benchmark and runner environment only. It cannot establish asymptotic complexity, production latency, real-enterprise scalability, causal identification, or universal DCHAG superiority.
