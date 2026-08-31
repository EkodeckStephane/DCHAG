# DCHAG adversarial validation protocol v2

Status: frozen before confirmatory scoring.
Date: 2026-08-18.

## Purpose

This validation extends the original correctly-specified simulator study with a harder setting designed to test DCHAG when the estimator does not receive the ground-truth edge set or ground-truth local equation family.

## Separation rules

1. Ground-truth world specifications are stored only under `benchmarks/validation_v2/private_worlds/` and are forbidden to estimator code.
2. Estimator inputs are restricted to observed train/test CSV files plus the public observable schema (node names, node types, temporal order, target name, control names, horizon).
3. Edge selection is data-driven from a dense temporally admissible candidate set. Ground-truth parents, coefficients, interactions and hidden variables are unavailable to estimators.
4. Prediction/effect files are hashed and frozen before oracle intervention effects or true edge sets are scored.
5. Development worlds and confirmatory worlds use disjoint seeds. Hyperparameters selected on the development worlds are frozen before confirmatory scoring.

## Data-generating stressors

- heterogeneous topologies with branching paths and variable numbers of human/process/technical nodes;
- horizons 4--6;
- persistent context and defensive-control states;
- observed treatment-confounder feedback through time-varying operational pressure;
- mixed probit/logistic/threshold/noisy-OR-like local mechanisms;
- pairwise interactions absent from the estimator's structural specification;
- separate matched latent-confounding sensitivity arm.

## Development rule

Four development worlds (one per workflow family) are used only to choose the sparse parent-cap among {4, 6}. The chosen value is the one with lower mean intervention-effect MAE, with ties broken toward the smaller model. No other hyperparameter may be changed after development scoring.

## Confirmatory sample

- 16 independent observed-world DGPs: 4 workflow families x 4 independently generated topologies/parameters.
- 4 matched latent-confounded DGPs, one paired to the first confirmatory world in each family.
- 4 sustained defensive interventions per world.

## Estimators

- DCHAG-Learned: data-driven sparse temporal structure + local logistic models with selected pairwise interactions.
- Dense sequential g-formula: same observed temporal ordering, all admissible history features, regularized local logistic models with pairwise interactions.
- Observational association baseline: endpoint logistic association model.

Neither DCHAG-Learned nor dense g-formula receives the true DAG.

## Primary outcomes

At the independent-world level:

1. intervention-effect MAE;
2. signed effect bias;
3. relative absolute effect error;
4. Kendall/Spearman control-ranking agreement and top-control regret;
5. prospective Brier Skill Score against the empirical prevalence reference;
6. learned-edge precision/recall/F1 (DCHAG-Learned only, scored post-freeze);
7. latent-confounding MAE increase relative to matched observed worlds.

## Inference

Estimator comparisons use the 16 independent worlds as paired units, not the 64 world-control rows. Report mean paired difference, world-block bootstrap 95% CI, and exact two-sided sign-flip p-value. Control-level values remain descriptive only.

## Interpretation

The original four-world benchmark remains a calibration experiment under supplied correct topology. Confirmatory claims about robustness to structure uncertainty and equation-family mismatch are based only on this v2 campaign.
