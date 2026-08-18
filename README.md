# DCHAG — Dynamic Causal Human Attack Graphs

DCHAG is a research prototype for typed temporal causal cyber-risk reasoning. It represents observable human decision/event states, business/workflow states, technical security states, and defensive controls in an executable time-unrolled structural causal model. Controls are queried through structural interventions, and the retained benchmark evaluates estimated compromise-risk effects against paired simulator-known intervention effects.

## Scientific scope

The protected contribution is deliberately narrower than human-aware attack graphs, business-process cyber models, dynamic attack graphs, or counterfactual cyber mitigation taken separately. The artifact evaluates one combined causal contract and its effect-fidelity behavior across four workflows under unchanged core semantics.

## Retained workflows

- helpdesk / identity compromise
- BEC / payment authorization
- data-exfiltration approval
- IT/OT maintenance and change

## Main retained evidence

The scientific manuscript reports DCHAG effect MAE 0.003906 and dense sequential g-formula MAE 0.006206 across 16 workflow-control units. Their paired difference is statistically unresolved (exact sign-flip p=0.159119); the artifact therefore does not claim causal-estimator superiority. Structural ablations, missingness, misspecification, prediction, control ranking, and scaling are retained, including weak results.

## Reproduce

Create the Python environment from `environment.yml` or install the package defined by `pyproject.toml`. From the repository root run:

```bash
PYTHONPATH=. pytest -q
```

The retained release passes 29/29 software tests. Experiment manifests and result directories contain the detailed commands, configurations, seeds, processed outputs, and statistical summaries used by the retained runs.

## Structure

`configs/` contains the four workflow configurations. `dchag/` and `estimation/` implement the causal engine and fitted estimator. `simulator/` contains benchmark worlds. `baselines/` contains comparison estimators. `experiments/` contains frozen run/scoring procedures. `results/` contains retained evidence. `tests/` contains regression tests for the causal engine, simulators, baselines, and experiment contracts. Independent manuscript/audit files are intentionally excluded from this public repository.

## Causal-scope limitation

The paired intervention oracle belongs to synthetic simulator worlds. Operational causal claims require corresponding field intervention/quasi-experimental evidence or a separately justified identification design. The topology is supplied in the retained benchmark; it is not learned from data.

## Release status

This repository is the public reproducibility artifact for DCHAG. The immutable commit associated with the submitted manuscript is recorded in the manuscript data-availability statement. Software licensing remains explicitly pending author selection; no license is inferred automatically.
