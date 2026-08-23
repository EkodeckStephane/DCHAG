# V3-SS-LOFO-001 — Semi-synthetic leave-one-family-out transport protocol

## Status

**FROZEN BEFORE V3-SS-LOFO-001 EXECUTION.**

This protocol is a **locked secondary transportability analysis**, not a pristine confirmatory experiment. The RQ1 confirmatory results from `V3-SS-CONF-001` were already inspected before this protocol was frozen. That chronology is retained explicitly and forbids presenting V3-SS-LOFO-001 as independent confirmatory evidence.

No target-family performance result from this LOFO analysis may be used to retune, replace, or drop a fold after execution begins.

## Research question

**RQ2.** How well do the causal mechanisms learned by DCHAG transport to a semantically different attack family when no target-family outcome/mechanism data are used for fitting, and how does that transfer compare with the frozen dense sequential g-formula comparator?

The purpose is to quantify mechanism-transfer loss under family shift, not to establish causal validity on LANL. The causal oracle remains the explicit semi-synthetic SCM.

## Scientific hypothesis

The analysis is deliberately non-directional at the primary endpoint. We will quantify and compare held-out-family causal-effect error for DCHAG and dense-g without claiming a priori that one must win.

A secondary qualitative expectation is that DCHAG's sparse/control-path representation may retain useful control ranking under family shift, but this expectation cannot override the primary effect-error endpoint.

## Chronology and evidence class

- RQ1 Stage-A development and corrected estimator selection were completed before this protocol.
- RQ1 confirmatory `V3-SS-CONF-001` was completed and audited before this protocol.
- Therefore all RQ2 p-values/intervals, if reported, are descriptive uncertainty summaries for a locked secondary analysis and are not fresh-confirmatory Type-I-error-controlled evidence.
- All null, adverse, rank-reversal, and dense-g-favorable outcomes must be retained.

## Immutable parent material

V3-SS-LOFO-001 reuses the already generated and audited RQ1 confirmatory worlds; it does **not** regenerate or replace them.

### Public benchmark artifact

- GitHub Actions artifact ID: `9489870327`
- Name: `dchag-v3-ss-confirm-public`
- SHA-256: `0f1c6ebe2c46b65a649d9b3e27d8f4c3b375fa6797cae39a76b8dcd9645a9ff3`

### Private SCM/oracle artifact

- GitHub Actions artifact ID: `9489870511`
- Name: `dchag-v3-ss-confirm-private`
- SHA-256: `898dde43e340d2852c43eab940fe46b6dc9652d2620dcf79705c061fcad03278`

### Audited RQ1 scored reference

- Artifact ID: `9489911175`
- Name: `dchag-v3-semisynthetic-confirmatory-results`
- SHA-256: `dad2d38262c01f5f499c58b1b44229a8908fc29cb7cf6d41fefb51461d3f6a24`

The RQ1 scored reference is used only for the pre-specified secondary transfer-penalty calculation; it is not used for model fitting or LOFO hyperparameter selection.

## Frozen estimator configuration

DCHAG uses the active corrected Stage-A freeze:

- selection experiment: `V3-SS-SEL-001-C1`;
- frozen file SHA-256: `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`;
- `max_parents = 8`;
- L1 screening: `penalty="l1"`, `C=0.05`, `solver="liblinear"`, `max_iter=500`;
- local refit: logistic model with `C=0.7`, main effects plus selected pairwise interactions;
- MI fallback only if no non-zero screened coefficient;
- no RQ2 retuning.

Dense sequential g-formula uses the same frozen local learner as RQ1:

- `HistGradientBoostingClassifier`;
- `loss="log_loss"`;
- `learning_rate=0.07`;
- `max_iter=80`;
- `max_leaf_nodes=15`;
- `min_samples_leaf=30`;
- `l2_regularization=1.0`;
- node-specific `random_state = 84000 + node_index`.

No observational-association comparator is included in the primary RQ2 comparison because RQ2 concerns transport of dynamic causal mechanism models. Its omission does not alter the retained RQ1 association result.

## Frozen LOFO folds

The four families are:

1. `helpdesk_identity`;
2. `bec_payment`;
3. `exfiltration`;
4. `itot_change`.

For each fold, one family is the target and all 12 worlds from the other three families are sources.

| Held-out target family | Source families | Target worlds |
|---|---|---|
| `helpdesk_identity` | `bec_payment`, `exfiltration`, `itot_change` | `confirm_helpdesk_identity_1..4` |
| `bec_payment` | `helpdesk_identity`, `exfiltration`, `itot_change` | `confirm_bec_payment_1..4` |
| `exfiltration` | `helpdesk_identity`, `bec_payment`, `itot_change` | `confirm_exfiltration_1..4` |
| `itot_change` | `helpdesk_identity`, `bec_payment`, `exfiltration` | `confirm_itot_change_1..4` |

No fold may be omitted or substituted.

## Source fitting population

For one held-out-family fold:

- use **only the train split** from the 12 source worlds;
- each source world contributes exactly 1,100 trajectories × 6 time points;
- pooled source fitting therefore uses exactly 13,200 source trajectories;
- local `trajectory_id` values are world-local and must be qualified before pooling;
- deterministic qualification is `qualified_id = source_world_index * 100000 + local_trajectory_id`, with source worlds sorted lexicographically and `source_world_index` starting at 1;
- source test splits are not used for fitting.

All schemas must agree exactly on horizon, node order, anchor nodes, controls, target, and node types. The `world` and `family` metadata fields are not predictors and are not supplied as model features.

## Target-family firewall

The target family contributes **no outcome/mechanism fitting data**.

For each target world, the estimator may receive only:

- its six-step sequences of `A_person`, `A_process`, and `A_technical` for the 1,100 train and 400 test trajectories;
- target split-qualified trajectory identifiers needed for deterministic alignment.

The estimator must not read target `R`, controls, H/P/T states, `Y`, true edges, SCM parameters, or oracle effects before its output is frozen.

The workflow must enforce this boundary physically:

1. download the public parent artifact;
2. construct a clean LOFO input containing source-train rows and target-anchor-only arrays;
3. verify counts and hashes;
4. delete the original public artifact tree from the estimator job before model execution;
5. run the estimator only against the clean LOFO input;
6. upload and freeze estimates/predictions/learned edges;
7. only a later scoring job may obtain the private oracle and target public outcomes.

## Target standardization and intervention estimand

For target world `w` and control `Ck`, the estimand remains:

`ATE_w,k = E[Y_5(do(Ck_0:5=0)) - Y_5(do(Ck_0:5=1))]`.

The source-fitted DCHAG/dense model is standardized over the target world's **1,500 anchor sequences** (1,100 train + 400 test anchors). Other controls evolve naturally according to the source-fitted model.

Target-family endogenous states/outcomes are not used to adapt the source model.

## Monte Carlo freeze

- exactly 100 paired common-random-number replicates per target anchor and intervention regime;
- no reduction for runtime;
- stable seed namespace:
  `V3-SS-LOFO-001|effects|<heldout_family>|<target_world>|<model>|<control>`;
- target prospective prediction namespace:
  `V3-SS-LOFO-001|prediction|<heldout_family>|<target_world>|<model>`.

## Prospective target prediction

For each target world, the source-fitted model predicts final `Y_5` for the 400 target test trajectories using **only their anchor sequences**, with 100 Monte Carlo replicates per trajectory.

The estimator output contains probabilities but not target truth. The scoring job joins frozen predictions to target test `Y_5` only after the estimator artifacts are frozen.

Predictive endpoints:

- raw Brier score;
- Brier Skill Score relative to a constant predictor equal to the pooled **source-training** final-Y prevalence for that fold.

No target-outcome prevalence may be used as the estimator's prediction baseline.

## Primary endpoint

For each target world and model:

1. compute absolute error for each of four control effects;
2. define world effect MAE as the mean of those four absolute errors;
3. aggregate across the 16 target worlds.

The primary comparative quantity is:

`D_LOFO = mean_world(MAE_DCHAG_LOFO - MAE_Dense_LOFO)`.

Because source models are shared within folds and the four folds reuse source families, the 16 world errors are not treated as 16 fully independent model-training experiments.

Primary reporting must include:

- all 16 world-level MAEs;
- four held-out-family mean MAEs per model;
- global 16-world descriptive mean MAE per model;
- `D_LOFO`;
- a 10,000-replicate hierarchical bootstrap that resamples the four target families and then the four target worlds within each sampled family, seed `20260823`;
- the four family-level paired differences individually.

No superiority claim may be based solely on a nominal p-value from these four folds. A family-level exact sign-flip calculation over `2^4=16` assignments may be retained as a descriptive sensitivity statistic only.

## Secondary causal-decision endpoints

For DCHAG and dense-g, separately:

- Kendall rank correlation across the four control effects per target world;
- Spearman rank correlation;
- top-control accuracy;
- normalized top-control regret.

For DCHAG only:

- learned-edge count in the pooled source model;
- edge precision, recall and F1 against each target world's known semi-synthetic true edge set.

Structural scores are **semi-synthetic target-SCM portability metrics only** and cannot be promoted as LANL causal-edge evidence.

## Pre-specified transfer penalty relative to RQ1

For each target world and each causal model:

`transfer_penalty_w = MAE_LOFO_w - MAE_RQ1_within_world_w`.

This measures the cost of removing target-world outcome/mechanism fitting. Report:

- world-level transfer penalties;
- mean penalty by held-out family;
- global descriptive mean penalty;
- DCHAG-minus-dense difference in transfer penalty.

The RQ1 reference is fixed by artifact `9489911175` and cannot be recomputed under altered settings.

## Guardrails

The result is invalid if any of the following occurs without an explicit correction protocol frozen before rescoring:

- target endogenous/outcome data enter source model fitting;
- private SCM/oracle data are accessible to an estimator job;
- target family is used to choose `max_parents` or any learner hyperparameter;
- a source or target world is replaced or omitted because of its result;
- fewer than 100 MC replicates are used;
- trajectory IDs are pooled without world qualification;
- target standardization uses anything other than the 1,500 split-qualified anchor sequences;
- scoring occurs before estimator-output hashes are frozen.

## Result classification

`PASS` means the protocol executed successfully and all four folds were retained; it does not imply transportability was strong or that DCHAG beat dense-g.

Scientific interpretation must preserve adverse findings. In particular:

- if both models degrade sharply, report weak mechanism transportability;
- if dense-g transfers better, report it;
- if DCHAG ranks controls well but effect magnitudes degrade, separate decision/ranking transport from effect-fidelity transport;
- if family behavior is heterogeneous, report the family-specific reversals rather than only the global mean.

## Claim boundary

V3-SS-LOFO-001 can support only claims about cross-family transport in the explicit semi-synthetic SCM benchmark. It cannot establish that causal mechanisms, defensive-control effects, or attack pathways transport across real organizations or LANL attack families.
