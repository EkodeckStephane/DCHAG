# V3-LANL-STRUCT-001 — frozen external learned-structure protocol

Status: frozen before model fitting/scoring.

## Purpose

Test whether the hardened v2 DCHAG-Learned structure-selection mechanism yields reproducible, predictive temporal dependencies on an external operational LANL trajectory representation.

This is an **observational temporal-structure stability and transportability experiment**. It is not a causal-DAG validation because LANL does not provide interventional ground truth for these dependencies.

## Immutable source

Use only the retained primary artifact from `V3-LANL-TRAJ-001`:

- GitHub Actions run: `32498616088`;
- artifact: `dchag-v3-lanl-trajectory-300s` (`9453590911`);
- artifact ZIP SHA-256: `d6cb979953d4f68bd45b464ee74105dcd4b41ed1d41c976889d7bb931028150b`;
- member: `LANL_TRAJECTORY_300S.csv.gz`;
- member SHA-256: `6c45852d95ce583aa95e39d6560ce2ef61a8f1e84e51c01cc38292c113cd1d22`;
- window width: 300 s;
- window indices: `0..180`;
- devices: `31,243`.

Missing device-window rows in the sparse retained artifact are interpreted as zero observed events for the three frozen channels, because the source streams cover the frozen overlap interval and the trajectory builder emits a row whenever a retained device has any mapped activity in that window.

## Disjoint structural channels

To prevent tautological learned edges caused by one raw event being mapped to more than one DCHAG evidence type, the structure experiment does **not** use the broad `H_present`, `P_present`, or `T_host_present` columns.

For each device-window define exactly three binary channels from mutually exclusive raw event classes:

1. `H_login = 1` iff `logon_success_4624 + logon_failure_4625 > 0`;
2. `P_process = 1` iff `process_start_4688 + process_end_4689 > 0`;
3. `T_network = 1` iff `net_out_flows + net_in_flows > 0`.

Thus a process event cannot simultaneously create `H_login`, and a host event cannot create `T_network`.

This conservative H channel represents observable person-associated login activity, not intention, compliance, susceptibility, or psychological state.

## Temporal candidate set

Only lag-1 parents are admissible. For each target channel at window `t`, candidates are:

- `H_login[t-1]`;
- `P_process[t-1]`;
- `T_network[t-1]`.

No same-window edge is admissible because events were aggregated into 300-s windows and their within-window ordering is not retained. Therefore no causal direction is inferred from same-window co-occurrence.

## Frozen DCHAG-Learned mechanism

Carry forward the hardened v2 confirmatory hyperparameters without LANL tuning:

- L1 logistic conditional screening: `C = 0.05`;
- ranking by absolute screening coefficient;
- maximum parents = `10` (effective maximum is three here);
- if L1 selects none, use the hardened-v2 mutual-information fallback for one parent;
- local logistic refit with selected main effects plus all selected pairwise interactions: `C = 0.7`.

The source provenance for these values is the recovered v2 snapshot SHA-256 `d821d3f6e5a6f73efd7935f0cc2223f55e029b1730edb1fbfd8bfc2d0b7dace3`, archived on branch `dchag-v3-v2-provenance`.

## Device-level transportability design

Assign every device deterministically to one of five folds by SHA-256 of its identifier modulo 5. For each fold:

- fit structure/local mechanisms on the other four device folds over all transitions `t=1..180`;
- score probabilities on the held-out device fold;
- record the learned lag-1 edge set and main-effect signs.

No device appears in both train and test for a given fold.

## Predictive comparators

For every target channel compare:

1. `DCHAG_Learned_Lag1`: selected cross-channel lag-1 model;
2. `SelfLag`: logistic model using only the target's own lag-1 state;
3. `Prevalence`: constant probability equal to training prevalence.

These comparators assess external predictive utility only; they are not causal estimators in this experiment.

## Primary endpoints

1. edge-selection frequency across the five device folds;
2. pairwise Jaccard similarity of learned edge sets across folds;
3. sign consistency of selected main effects;
4. out-of-fold Brier score and Brier Skill Score relative to training-prevalence prediction for each target;
5. Brier difference versus `SelfLag` for each target.

## Secondary temporal-stability diagnostic

Fit the same frozen selector on all devices separately for target windows `1..90` and `91..180`. Report early/late edge-set Jaccard and sign agreement. This diagnostic is descriptive and does not alter the five-fold primary analysis.

## Statistical handling

The five device folds are the primary reproducibility units for structural selection. Predictive Brier values are reported out-of-fold. No p-value is used to promote causal claims. Any device-block bootstrap, if added later, is a predictive uncertainty sensitivity analysis and must be separately versioned.

## Guardrails

- no red-team/attack labels;
- no private simulator DAG or coefficients;
- no defensive control `C`;
- no intervention effect;
- no same-window direction;
- no hyperparameter tuning on LANL;
- no claim that a selected edge is a causal edge.

## Interpretation boundary

A positive result may support the claim that DCHAG's sparse temporal structure-selection machinery can produce stable and predictively useful typed dependencies on an external operational trace under a conservative observational contract. It cannot establish causal identification, intervention validity, human intention, or control effectiveness.
