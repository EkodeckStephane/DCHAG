# DCHAG

**DCHAG** is the reproducibility artifact for **Dynamic Causal Human Attack Graphs for Counterfactual Cyber Risk**. It implements a typed temporal structural causal model in which observable human decisions, business/workflow states, technical compromise states, and defensive controls are evaluated in one executable intervention framework.

Repository: **https://github.com/EkodeckStephane/DCHAG**

## 1. Context

Cyber compromise can cross human decisions, organizational authorization steps, and technical state transitions. DCHAG targets defensive decision support at this socio-technical boundary by estimating how explicit control interventions change compromise risk and by exposing the causal paths associated with those effects.

## 2. Problem

The study connects eight requirements in one evaluable contract: human event states, process/workflow states, technical states, temporal evolution, structural defensive interventions, quantitative intervention effects, validation against known paired intervention outcomes, and unchanged-core portability across multiple workflows.

## 3. Research question

> Can a typed temporal socio-technical attack graph estimate defensive-control effects with high causal fidelity while preserving the same causal semantics across distinct human-process-technical workflows?

## 4. Proposed solution

DCHAG represents human (`H`), process (`P`), technical (`T`), and control (`C`) variables in a time-unrolled SCM. Controls are queried through structural interventions. A separate benchmark simulator retains known structural equations and common exogenous realizations, enabling paired baseline/intervention outcomes for direct effect-fidelity scoring.

The same causal engine is exercised across four workflows:

- helpdesk / identity compromise;
- business-email-compromise / payment authorization;
- data-exfiltration approval;
- IT/OT maintenance and change.

## 5. Research assets and means used

The artifact contains the core causal engine, fitted estimator, simulator, four YAML workflow configurations, observational/risk baselines, two causal g-formula comparators, structural ablations, robustness experiments, scaling experiments, retained raw/processed/statistical outputs, fixed seeds, manifests, and regression tests.

## 6. Main experimental results

Across 16 workflow-control units, DCHAG attains mean intervention-effect MAE **0.003906**. The association-based outcome comparator reaches **0.016110**, corresponding to a **75.8% reduction** in mean effect error for DCHAG with Holm-adjusted `p = 0.000244`.

The dense sequential g-formula reaches MAE **0.006206**. Both methods recover the highest-effect control in all four workflows with zero mean top-control regret. DCHAG records mean Kendall rank correlation **0.8333** and mean Spearman correlation **0.9000**.

Structural ablations yield substantially larger effect errors: **0.039203** without human structure, **0.055248** without process structure, **0.049972** without temporal structure, and **0.054763** for technical-only estimation. Full DCHAG reaches mean path F1 **1.000** in the retained simulator workflows. At 50% random evidence missingness, intervention-effect MAE is **0.006010** and mean path F1 is **0.737**. The structural-edge-drop study yields MAE **0.01520** and path F1 **0.875**.

## 7. Scientific positioning

DCHAG builds on established attack-graph, human-aware, business-process, dynamic causal, and SCM-based cyber-defense research. Its specific contribution is the jointly executable and experimentally validated contract formed by typed human/process/technical states, temporal SCM semantics, structural defensive interventions, direct effect scoring against paired intervention truth, path-level evidence, and unchanged-core evaluation across four operational workflows.

## 8. Repository structure

```text
DCHAG/
├── dchag/                       # Core typed temporal causal engine
├── estimation/                  # Fitted SCM / intervention-effect estimation
├── simulator/                   # Structural-equation benchmark generator
├── configs/                     # Four retained workflow configurations
├── baselines/                   # Observational, risk-score and causal baselines
├── benchmarks/                  # Generated benchmark trajectories/oracles
├── experiments/                 # Frozen execution/scoring protocols
├── results/                     # Raw, processed and statistical outputs
├── spec/                        # Formal contracts and ontology material
├── tests/                       # Semantic/estimator/simulator/baseline tests
├── environment.yml
├── pyproject.toml
└── SHA256SUMS.txt
```

Submission documents and independent manuscript-audit files are maintained separately.

## 9. Reproducibility procedure

Create an environment and run the tests first:

```bash
conda env create -f environment.yml
conda activate dchag
PYTHONPATH=. pytest -q
```

The retained freeze passes **29/29 software tests**.

Regenerate benchmark worlds:

```bash
PYTHONPATH=. python simulator/generate_benchmarks.py
```

Run and score the retained experiment suite:

```bash
PYTHONPATH=. python experiments/run_retained.py
PYTHONPATH=. python experiments/score_retained.py
PYTHONPATH=. python experiments/run_robustness.py
```

Run the causal baselines:

```bash
PYTHONPATH=. python experiments/run_q1_causal_baseline.py
PYTHONPATH=. python experiments/score_q1_causal_baseline.py
PYTHONPATH=. python experiments/run_q1_dense_sequential_gformula.py
PYTHONPATH=. python experiments/score_q1_dense_sequential_gformula.py
```

Run scaling analysis:

```bash
PYTHONPATH=. python experiments/run_scaling.py
```

Key retained tables are under `results/processed/`, `results/statistics/`, and `results/q1_dense_sequential_gformula/`.

## 10. Integrity and provenance

The artifact separates benchmark generation, estimator fitting, intervention scoring, statistical analysis, and software tests. Fixed workflow configurations, seeds, protocol amendments, pre-scoring hashes, and SHA-256 manifests support reproducibility and provenance checking.

## 11. Scope and future validation

The current intervention oracle is established in controlled synthetic socio-technical worlds with known structural equations. This design supports direct measurement of intervention-effect fidelity. Operational validation can extend the same protocol to cyber ranges, prospective organizational interventions, or defensible quasi-experimental identification designs.

## 12. Authors

- Stéphane Gaël R. Ekodeck
- **Serge Alain Ebele — corresponding author**
- Arthur Ulrich Ewane
- Chantal Marguerite Mveh-Abia
- René Ndoundam
