# V3-LANL-MULTIDAY-001 — frozen out-of-development multi-day validation

Status: frozen before inspection of LANL day-03/day-04/day-05 results.

## Motivation and correction boundary

The earlier `V3-LANL-STRUCT-001` protocol described `H_login` as person-associated, but its retained day-02 trajectory counted EventID 4624/4625 regardless of whether `UserName` identified a de-identified person, a machine account ending in `$`, or a named/system account. Therefore the prior H-channel semantic claim is not valid as written.

This experiment corrects the H semantics before out-of-development validation. The previous day-02 results remain immutable and may still be discussed as a generic login-event-channel diagnostic, but not as evidence about person-associated human activity.

## Data split fixed before confirmatory inspection

- Day 02: development/semantic-correction day only.
- Days 03, 04, 05: the next three chronological LANL days and the only confirmatory days in this experiment.
- No result from days 03–05 may be used to alter channel definitions, the candidate-set, folds, or regularization.

LANL publishes host data by day 01–90 and netflow by day 02–90. The source URLs are fixed as:

- `https://lanl.ma.ic.ac.uk/data/2017/wls/wls_day-DD.bz2`
- `https://lanl.ma.ic.ac.uk/data/2017/netflow/netflow_day-DD.bz2`

for DD in 02, 03, 04, 05. SHA-256 identities are computed and retained by the frozen run. Day-02 identities must reproduce the already retained hashes.

## Per-day observational interval

For each day:

1. theoretical day start = `(day-1)*86400`;
2. theoretical day end = `day*86400-1`;
3. start = maximum of theoretical start, first valid host timestamp, and first valid netflow timestamp;
4. after the single full stream pass, end = minimum of theoretical end, latest parsed host timestamp, and latest parsed netflow timestamp;
5. 300-s windows originate at that mechanically determined start.

This rule is fixed before reading any model result and prevents missing early netflow coverage from being silently represented as observed zeros.

## Corrected mutually exclusive channels

For each device×300-s window:

- `H_person_login = 1` iff at least one EventID 4624 or 4625 has a de-identified person account matching `^User[0-9]+$`;
- `P_process = 1` iff at least one EventID 4688 or 4689 occurs;
- `T_network = 1` iff at least one netflow has the device as source or destination.

Machine accounts ending `$`, `SYSTEM`, named service/system accounts, and missing usernames cannot activate `H_person_login`.

No host event can activate `T_network`; no process EventID can activate `H_person_login`. Only lag-1 edges are admissible.

## Candidate structures

For every target at time t, the only candidate parents are the three corrected channels at t-1. Same-window edges are forbidden.

Two screening variants are evaluated on identical deterministic five-fold device splits:

1. `FixedFull`: hardened-v2 L1 screen with `C=0.05`.
2. `ScaledFull` candidate: `C = 0.05 * 6400 / n_train_transitions`.

`6400` is the median training-row scale of the recovered v2 confirmatory worlds and was frozen before this multi-day experiment. Both variants use the same maximum-parent rule and the same local logistic refit `C=0.7` with pairwise interactions. The v2 mutual-information fallback remains active if the L1 screen selects no parent.

The `ScaledFull` formula is evaluated, not tuned, on days 03–05. No alternative C values are searched.

## Fold assignment

Devices are assigned deterministically by SHA-256(device) modulo 5. For each fold, training uses four device folds and scoring uses the held-out fold. Device identifiers do not cross train/test within a fold.

## Predictive comparators

For each target:

- FixedFull;
- ScaledFull;
- SelfLag;
- training prevalence.

Brier score and Brier Skill Score relative to prevalence are descriptive predictive endpoints only.

## Primary confirmatory endpoints across days 03–05

1. mean selected-edge count per fold for FixedFull and ScaledFull on each day;
2. ScaledFull/FixedFull density ratio across the three day-level means;
3. frequency of each ScaledFull edge across all 15 confirmatory folds;
4. day-level Brier for each target under FixedFull, ScaledFull and SelfLag;
5. whether ScaledFull reduces edge count on each confirmatory day;
6. whether ScaledFull beats SelfLag on each confirmatory day for each target.

No single endpoint is allowed to redefine the method after inspection. No p-value is used to infer causal validity from three days.

## Day-02 correction output

Day 02 is rerun with the corrected `H_person_login` definition only to quantify the impact of the semantic correction and to provide a like-for-like development reference. It is excluded from all confirmatory day aggregates.

## Guardrails

- no red-team or attack labels;
- no simulator truth;
- no control C or defensive intervention;
- no counterfactual effect;
- no same-window direction;
- no LANL hyperparameter search;
- no causal-edge claim;
- days 03–05 remain out-of-development.

## Claim boundary

A positive multi-day result may support observational transportability of a typed lagged dependency mechanism across consecutive operational days. It cannot validate causal identification, human intention, control effectiveness, or counterfactual risk reduction.
