# V3-LANL-PT-EXT-001 — frozen extended temporal validation

Status: FROZEN before inspection of LANL day-06/day-07/day-08/day-09/day-10 results.

## Purpose

`V3-LANL-MULTIDAY-001` showed mixed/partial support on days 03–05: the frozen sample-size-scaled selector substantially reduced graph density, retained predictive value for `P_process` and `T_network`, but did not improve corrected `H_person_login` over SelfLag. This experiment tests whether the P/T result persists across a longer unseen temporal block without tuning or redefining the model.

## Fixed temporal block

The validation days are exactly the next five chronological LANL days not used in development or prior confirmation:

- day 06;
- day 07;
- day 08;
- day 09;
- day 10.

No day may be dropped, replaced, or added after inspection of its result. All five are confirmatory for this experiment.

## Frozen data construction

The exact `run_lanl_multiday_validation.py` implementation already retained on branch `dchag-v3` is reused unchanged.

For each day:

- LANL Unified host file: `wls_day-DD.bz2`;
- LANL Unified netflow file: `netflow_day-DD.bz2`;
- the common interval is determined mechanically from the theoretical day bounds and the first/latest valid timestamps of both streams;
- device×300-s windows are used;
- deterministic device folds use SHA-256(device) modulo 5.

Source SHA-256 values are computed and retained by the run.

## Frozen disjoint channels

- `H_person_login`: EventID 4624/4625 only when the user matches `^User[0-9]+$`;
- `P_process`: EventID 4688/4689;
- `T_network`: device observed as source or destination in netflow.

Machine/system/non-person login accounts cannot activate H. No host event activates T. Only lag-1 dependencies are admissible.

## Frozen models

Two variants are evaluated on identical five-fold device splits:

1. `FixedFull`: hardened-v2 L1 screening with `C=0.05`.
2. `ScaledFull`: `C = 0.05 * 6400 / n_train_transitions`.

No hyperparameter search is permitted. Local logistic refit remains `C=0.7` with pairwise interactions. The inherited mutual-information fallback remains active only if the L1 screen selects no parent; fallback use is reported explicitly.

## Primary confirmatory criteria

The experiment is not allowed to redefine success after inspection.

### C1 — sparsity transfer

`ScaledFull` must select fewer edges than `FixedFull` on **all 5/5 days**.

### C2 — P predictive transfer

For `P_process`, `ScaledFull` must have lower held-out Brier than `SelfLag` on **at least 4/5 days**.

### C3 — T predictive transfer

For `T_network`, `ScaledFull` must have lower held-out Brier than `SelfLag` on **at least 4/5 days**.

### C4 — P/T structural recurrence

Each of the three previously confirmed observational lagged dependencies must appear in at least **20/25 folds** across days 06–10:

- `P_process[t-1] -> P_process[t]`;
- `P_process[t-1] -> T_network[t]`;
- `T_network[t-1] -> T_network[t]`.

The 20/25 threshold is frozen before execution and is not a causal-probability threshold.

## Secondary H endpoint

`H_person_login` is retained as a secondary negative-control-like endpoint for descriptive monitoring only. It does **not** contribute to the experiment's success criteria. No retuning, alternative H definition, or H-specific model is allowed in this run.

Report:

- ScaledFull vs SelfLag Brier by day;
- L1 fallback frequency for H across 25 folds;
- selected incoming H edges and their frequencies.

## Additional descriptive endpoints

- FixedFull and ScaledFull mean selected edges per day;
- aggregate density ratio;
- edge frequencies over 25 folds;
- coefficient-sign recurrence for selected P/T edges;
- parsed host/network volume and malformed-record counts;
- person-login events and excluded non-person login events.

## Guardrails

- no red-team or attack labels;
- no simulator truth;
- no defensive intervention C;
- no counterfactual effect estimation;
- no same-window direction;
- no per-day tuning;
- no post-hoc day selection;
- no causal-edge claim;
- no H repair using days 06–10.

## Claim boundary

A positive result may support **extended temporal observational transportability** of the scale-aware sparse P/T lagged-dependency mechanism. It cannot establish causal identification, human intention, control effectiveness, attack causality, or counterfactual risk reduction.

<!-- Execution-trigger comment only; frozen scientific semantics are unchanged. -->
