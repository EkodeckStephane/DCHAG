# V3-SS-SEL-001 — frozen Stage-A estimator-selection protocol

Freeze date: 2026-08-22.

Status: **FROZEN before candidate performance is computed or inspected**.

## Purpose

Select the single DCHAG learned sparse sequential-estimator configuration that will be locked before generation or scoring of the 16 `V3-SS-CONF-001` confirmatory worlds.

Only the four retained `V3-SS-DEV-001` development worlds may be used. Confirmatory device blocks, seeds, generated trajectories, private SCMs, oracle effects, or true edges must not be generated or inspected during this experiment.

## Immutable Stage-A input

GitHub Actions run: `32526360956`.

Artifact: `dchag-v3-semisynthetic-development`, artifact id `9462315359`.

Artifact ZIP SHA-256:

`ca33420fe43da84d85b2785f9a845534cc22399f2ea30ed9fda416c64ecbecb5`

The four development worlds are:

- `dev_helpdesk_identity`;
- `dev_bec_payment`;
- `dev_exfiltration`;
- `dev_itot_change`.

Each contains 1,100 training trajectories and 400 held-out test trajectories, horizon 6. The private SCM/oracle files are available to the **development scorer only**; the estimator must fit from public training data and public schema only.

## Frozen candidate family

The hardened-v2 selector is transferred without changing its screening or local-refit regularization because the Stage-A training size is 6,600 rows/world, close to the v2 development scale. The only candidate degree of freedom is maximum selected parents.

Candidates:

`max_parents ∈ {6, 8, 10}`.

For every candidate:

- admissible current-slice features = variables preceding the response node in public event order;
- admissible lag-1 features = the full observed public variable history;
- lag-1 features are zero at time 0;
- anchors `A_person`, `A_process`, `A_technical` are exogenous observed channels and are not fitted as response mechanisms;
- L1 conditional screening uses `LogisticRegression(penalty="l1", C=0.05, solver="liblinear", max_iter=500, fit_intercept=True)`;
- selected features are ranked by absolute screening coefficient and truncated to `max_parents`;
- if all L1 coefficients are zero, deterministic mutual-information ranking is used as the frozen fallback;
- the local mechanism is refit with `LogisticRegression(C=0.7, solver="lbfgs", max_iter=500, fit_intercept=True)` on selected main effects plus all pairwise selected-feature interactions;
- no candidate-specific threshold, penalty, link, feature family, or fallback may be altered after results are inspected.

## Development effect estimation

After fitting on the 1,100 public training trajectories only, intervention risk is standardized over the fixed real-anchor sequences from all 1,500 development-world devices, matching the frozen development oracle target population. Generated non-anchor outcomes/controls from the held-out 400 trajectories are not used for fitting or intervention standardization.

For each control `C1..C4`, estimate

`E[Y_5(do(Ck_0:5=0)) - Y_5(do(Ck_0:5=1))]`

by Monte-Carlo g-computation through the learned local mechanisms. Other controls remain under their learned natural mechanisms and may respond to intervened history. The two intervention regimes use paired common random numbers. Use exactly 100 Monte-Carlo replicates per anchor trajectory/regime for candidate selection.

## Frozen primary selection score

For each world and candidate, compute the mean absolute error across the four control effects against the retained Stage-A development oracle.

Primary candidate score = **unweighted mean of the four world-level effect MAEs**. Thus the four workflow families, not the 16 world-control rows, receive equal weight.

Selection rule:

1. choose the candidate with the smallest primary score;
2. an exact numerical tie within `1e-12` is broken in favor of the smaller `max_parents`;
3. no statistical-significance test is used to choose the candidate;
4. the selected cap is locked even if the difference is small or an alternative has better secondary diagnostics.

## Secondary diagnostics — report but do not select on them

For each candidate report:

- per-world and aggregate signed effect bias;
- Kendall and Spearman control-ranking agreement;
- top-control accuracy and normalized regret;
- learned-edge precision, recall and F1 against development true edges, scored only after learned outputs are frozen;
- held-out prospective Brier score at final time on the 400 public test trajectories;
- number of learned edges and MI-fallback count.

The dense sequential g-formula and observational-association comparator are not used to select `max_parents`; they are reserved as frozen confirmatory comparators and may be run on Stage A only as implementation diagnostics after the DCHAG cap has been selected.

## Output freeze

Before any confirmatory world is generated, retain:

- candidate-level and world-level development scores;
- the selected `max_parents`;
- exact estimator constants and software versions;
- code SHA-256 / commit identity;
- fitted-development output hashes;
- a `FROZEN_SEMISYNTHETIC_ESTIMATOR.json` file containing the configuration that Stage B must consume verbatim.

Any later estimator change requires a new experiment identifier and invalidates use of the original `V3-SS-CONF-001` protocol until a new untouched confirmatory set exists.

## Guardrails

The result must assert:

- `confirmatory_worlds_generated = 0`;
- `confirmatory_worlds_scored = 0`;
- `confirmatory_hyperparameter_tuning = false`;
- `estimator_private_SCM_access = false` during fitting;
- private development SCM/oracle access occurs only in the development scorer;
- no candidate is dropped or added after candidate results are inspected.

## Claim boundary

`V3-SS-SEL-001` is a development/tuning experiment. Its numerical performance is not manuscript evidence for RQ1 causal fidelity. Only the subsequently untouched `V3-SS-CONF-001` worlds can support the confirmatory causal-recovery claim.
