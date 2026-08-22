# V3-SS-CONF-001 — frozen confirmatory execution and scoring protocol

Freeze date: 2026-08-22.

Status: **FROZEN before generation, estimation, or scoring of any of the 16 reserved confirmatory worlds**.

This document operationalizes Stage B of `SEMISYNTHETIC_ORACLE_PROTOCOL.md`. It does not change the already frozen confirmatory seeds, device blocks, SCM families, intervention estimand, or primary endpoints.

## 1. Preconditions

Stage B is permitted only because `V3-SS-SEL-001` has completed and frozen one estimator configuration:

- `FROZEN_SEMISYNTHETIC_ESTIMATOR.json`;
- retained member SHA-256: `8d592bf54b5103501391c79204829dff88b1fb4831841022cfea2687d0660105`;
- selected `max_parents = 8`;
- L1 screening `C=0.05`;
- local logistic refit `C=0.7`;
- confirmatory tuning disabled.

The primary estimator configuration may not be altered during Stage B.

The semi-synthetic generator remains the frozen builder introduced at commit `4042d61fd66f130197ceed22fb0903640c95e63c`. Any code change to the world-generating mechanisms, device allocation, world seeds, or anchor extraction requires a new confirmatory experiment identifier and a new untouched world set.

## 2. Confirmatory worlds

The 16 worlds are exactly the device blocks 4–19 and seeds already frozen in `SEMISYNTHETIC_ORACLE_PROTOCOL.md`: four independent worlds for each of:

1. helpdesk/identity;
2. BEC/payment;
3. exfiltration;
4. IT/OT change.

No world may be dropped, regenerated with a new seed, substituted, or rerun under changed mechanisms because of an unfavorable result.

Each world retains 1,500 devices, 1,100 train and 400 held-out test trajectories, horizon 6.

The confirmatory oracle uses exactly **100 paired Monte-Carlo replicates per anchor unit/regime**.

## 3. Physical public/private separation

The confirmatory workflow has three sequential jobs.

### Job A — generation

The frozen builder may create `public/` and `private/` material in its isolated workspace because oracle construction requires the known SCM. Before any estimator runs, Job A emits two different immutable artifacts:

- **public benchmark artifact**: only `public/<world>/{train.csv,test.csv,schema.json}` plus a public hash manifest;
- **private scoring artifact**: only `private/<world>/{world.json,true_edges.json,oracle_effects.json}` plus private/hash metadata and the confirmatory build summary.

The public artifact must contain no private SCM coefficient, oracle effect, or true-edge file.

### Job B — estimation and output freeze

Job B downloads **only the public benchmark artifact**. It has no private artifact in its filesystem and no code path to the private scorer inputs. It fits the three frozen comparators and writes effect estimates, held-out predictions, learned DCHAG edges, metadata, and SHA-256 freeze manifests.

Job B uploads an immutable **frozen estimation artifact**. Scoring is forbidden until this upload has completed.

### Job C — private scoring

Job C downloads the already uploaded frozen estimation artifact and the private scoring artifact. It first verifies every per-world estimation freeze manifest. Only then may it read oracle effects or true edges. It scores and aggregates the pre-registered endpoints.

This artifact boundary is the operational enforcement of `estimator_private_SCM_access = false`.

## 4. Frozen DCHAG estimator

DCHAG uses `FROZEN_SEMISYNTHETIC_ESTIMATOR.json` verbatim:

- cap 8;
- same-slice public-order predecessors;
- full public lag-1 observed history;
- lag-1 zero at time 0;
- L1 logistic screening, `C=0.05`, `liblinear`, max_iter 500;
- deterministic MI fallback if and only if all L1 coefficients are zero;
- local logistic refit, `C=0.7`, `lbfgs`, max_iter 500;
- selected main effects plus all selected pairwise interactions.

Anchors are fixed exogenous observed sequences and are never fitted as responses.

## 5. Frozen dense sequential g-formula comparator

The dense comparator uses the **same temporally admissible public feature set** as DCHAG but performs no sparse screening.

For every non-anchor node, fit:

`HistGradientBoostingClassifier(loss="log_loss", learning_rate=0.07, max_iter=80, max_leaf_nodes=15, min_samples_leaf=30, l2_regularization=1.0)`.

Use deterministic node-specific `random_state = 84000 + node_index`.

Constant-response nodes use their clipped empirical prevalence. Anchors remain fixed external sequences.

The dense comparator receives no private SCM information and no true edges.

## 6. Frozen observational-association comparator

The noncausal comparator is intentionally cross-sectional and cannot emulate sustained intervention dynamics.

At final time `t=5`, fit one logistic regression:

`Y_5 ~ R_5 + C1_5 + C2_5 + C3_5 + C4_5`

using public training trajectories only, with `LogisticRegression(C=1.0, solver="lbfgs", max_iter=500)`.

For each target control `Ck`, estimate an adjusted observational risk difference by predicting every final-time training row twice while holding observed `R_5` and the other three observed controls fixed:

`Assoc_k = mean[p(Y=1 | Ck=0, observed others) - p(Y=1 | Ck=1, observed others)]`.

This comparator is explicitly **not** a sustained `do(Ck_0:5)` estimator and must be labelled observational association in all outputs and manuscript text.

## 7. Frozen effect-estimation Monte Carlo

For DCHAG and dense-g, intervention standardization uses the fixed six-step anchor sequences from all 1,500 public trajectories in each world, matching the oracle target population.

The models are fitted on the 1,100 training trajectories only. Generated held-out H/P/T/R/C/Y values are not used for fitting or intervention standardization.

For each control and estimator, simulate sustained `do(Ck=0)` and `do(Ck=1)` with all other controls following their learned natural policies. Use exactly **100 paired common-random-number replicates per anchor trajectory/regime**.

The estimated risk reduction is:

`mean(Y_5(do(Ck=0))) - mean(Y_5(do(Ck=1)))`.

## 8. Frozen held-out predictive endpoint

For DCHAG and dense-g only, final-time prospective risk on each of the 400 held-out trajectories is estimated by 100 Monte-Carlo simulations **conditioned only on that trajectory's fixed six-step A_person/A_process/A_technical anchors**. All generated R/C/H/P/T states follow the learned natural mechanisms.

Brier score is computed against held-out observed `Y_5`.

Brier skill score uses as reference the training-world final-time `Y` prevalence:

`BSS = 1 - Brier_model / mean((Y_test - prevalence_train)^2)`.

The association comparator has no prospective Brier endpoint.

## 9. DCHAG edge endpoint

`learned_edges.json` is frozen in Job B before scoring. Job C compares it against the private `true_edges.json` and reports precision, recall, and F1 per world plus unweighted world means.

The edge metric is diagnostic of generated-structure recovery. It is not evidence of causal edges in LANL.

## 10. World-level scoring

For each world and model, compute:

- intervention-effect MAE across the four controls;
- signed effect bias;
- Kendall tau and Spearman rho for the four-control ranking;
- selected top control;
- top-control accuracy;
- normalized regret relative to the true best control;
- DCHAG edge metrics where applicable;
- DCHAG/dense held-out Brier and BSS where applicable.

The 16 worlds are the independent confirmatory units. The 64 world-control rows are not treated as independent replicates.

## 11. Frozen DCHAG-versus-dense inference

Let `d_w = MAE_DCHAG,w - MAE_Dense,w` for each of the 16 worlds.

Report:

- the mean `d_w`;
- a 95% world-block bootstrap percentile interval using **10,000** resamples of the 16 worlds with replacement and RNG seed `20260822`;
- the **exact two-sided sign-flip p-value** over all `2^16 = 65,536` sign assignments, using the absolute mean difference as the statistic.

This inference describes paired effect-fidelity difference. It does not change the claim boundary: DCHAG is not required to beat dense-g for the experiment to be valid.

## 12. Family reporting

In addition to the overall 16-world results, report descriptive unweighted means by the four frozen workflow families. No family-specific significance claim is primary.

## 13. Positivity and anchor diagnostics

Before interpreting causal-recovery failures, retain per-world:

- final and overall control prevalences;
- minimum/maximum empirical control prevalence over `(time, R_t)` strata with at least 20 training rows;
- anchor prevalences;
- all-zero anchor-unit count;
- generated train/test Y prevalence.

A positivity issue narrows interpretation; it does not authorize changing or deleting a world.

## 14. Guardrails

Every retained confirmatory result must assert:

- `confirmatory_hyperparameter_tuning = false`;
- `confirmatory_world_replacement = false`;
- `estimator_private_SCM_access = false`;
- `attack_or_red_team_labels_read = false`;
- `LANL_defensive_intervention_inferred = false`;
- `real_anchor_treated_as_causal_truth = false`;
- `hidden_confounder_present = false` for RQ1;
- `estimation_outputs_frozen_before_private_scoring = true`.

## 15. Claim boundary

A completed `V3-SS-CONF-001` may support causal-effect recovery and control-ranking fidelity **only on this explicitly identified, real-trajectory-anchored semi-synthetic benchmark**.

It cannot establish causal effects in LANL, attacker intent in LANL, or real defensive-control effectiveness. Observational LANL transportability and semi-synthetic causal fidelity remain separate evidence streams.
