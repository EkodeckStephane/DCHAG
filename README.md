# DCHAG

**DCHAG** is a reproducible research implementation of **Dynamic Causal Human Attack Graphs** for counterfactual cyber-risk analysis. It represents observable human decisions, business-process states, technical compromise states, and defensive controls inside one typed temporal structural causal model. The framework estimates compromise risk under explicit defensive interventions and evaluates control effects against paired simulator-known intervention effects.

Repository: **https://github.com/EkodeckStephane/DCHAG**

## 1. Context

Cyber-risk analysis increasingly combines attack graphs, human-factor modeling, business-process analysis, dynamic risk assessment, and causal inference. Each line contributes an important part of the problem: attack graphs represent reachable compromise paths; human-centered models capture decision and susceptibility factors; process-aware models connect cyber events to organizational workflows; causal models support intervention analysis.

A practical security decision, however, often spans all of these layers simultaneously. A helpdesk operator may approve an identity-reset request, a business workflow may authorize the next step, and a technical control may then determine whether the attacker reaches a protected asset. Security teams therefore need a model that can represent the complete socio-technical chain and answer a direct operational question: **which defensive intervention changes compromise risk, by how much, and which attack paths remain after that intervention?**

DCHAG addresses this problem through a typed temporal causal attack-graph semantics and an executable intervention engine. The repository accompanies the study **“Dynamic Causal Human Attack Graphs for Counterfactual Cyber Risk”** and contains its reproducibility materials independently of submission-specific manuscript files.

## 2. Problem

Existing research provides several strong building blocks. Human-aware and multilayer attack graphs represent people, access, organizational or business layers, and network states. Dynamic causal attack graphs represent evolving technical compromise. Process-aware cyber-risk models connect attacks with mission and workflow dependencies. Structural causal models support intervention and counterfactual reasoning for cyber-defense decisions.

The remaining research problem concerns their **joint operational semantics and validation**. A security model intended for counterfactual control selection must connect:

1. observable human decision/event states;
2. business-process and workflow states;
3. technical attack and compromise states;
4. temporal evolution across these state families;
5. defensive controls represented as structural interventions;
6. explicit compromise-risk effects for those interventions;
7. direct validation of estimated effects against known intervention outcomes;
8. portability of the same causal engine across distinct operational workflows.

DCHAG treats this complete contract as the scientific object of study.

## 3. Research question

> **Can a typed temporal socio-technical attack graph estimate the effect of defensive interventions with high causal fidelity while preserving the same causal semantics across distinct human–process–technical workflows?**

The repository also evaluates the conditions shaping this answer: partial observability, structural misspecification, removal of human/process/temporal structure, control ranking, path recovery, and computational scaling.

## 4. Proposed solution

DCHAG defines a time-indexed graph

\[
G_t=(V_H\cup V_P\cup V_T,E_t),
\]

where `V_H` contains observable human decision/event variables, `V_P` contains business-process states, and `V_T` contains technical security states. Each endogenous variable follows a structural equation

\[
X_i := f_i(\mathrm{Pa}(X_i),U_i).
\]

Defensive controls enter the model through structural interventions. For a target compromise variable `Y` and control `C`, DCHAG evaluates the change in compromise probability associated with the intervention and propagates that intervention through the temporal socio-technical graph.

### 4.1 Typed socio-technical causal semantics

The implementation keeps human, process, and technical states explicitly typed. This supports path-level inspection of how a compromise chain moves across organizational and technical boundaries while preserving one executable causal semantics.

### 4.2 Structural defensive interventions

Controls are represented as modifications to the structural causal system. This gives each evaluated control a precise intervention target and produces a counterfactual compromise-risk estimate tied to the same model used for path reasoning.

### 4.3 Intervention-effect validation

The benchmark simulator contains known structural equations and can generate paired outcomes under selected controls. These paired intervention outcomes provide a direct oracle for measuring effect-estimation error, control ranking, regret, and path recovery.

### 4.4 Cross-workflow portability

The same DCHAG engine is evaluated in four operational contexts:

- helpdesk / identity compromise;
- business-email-compromise / payment authorization;
- data-exfiltration approval;
- IT/OT maintenance and change.

Workflow configuration changes the domain variables, event vocabulary, control definitions, and structural parameters while preserving the core causal engine and intervention semantics.

## 5. Research assets and means used

The study combines formal causal modeling, executable simulation, reproducible software experimentation, strong causal and risk baselines, robustness analysis, and statistical evaluation.

### Software and environment

- Python 3.11;
- NumPy, pandas, SciPy, scikit-learn, PyYAML;
- pytest for regression and semantic tests;
- deterministic YAML workflow configurations;
- frozen experiment manifests and scoring scripts;
- fixed random seeds for simulator generation and retained analyses.

The reproducible environment is defined in `environment.yml` and `pyproject.toml`.

### Benchmark construction

The simulator generates socio-technical trajectories from explicit structural equations. Each workflow contains human, process, technical, and control variables over a fixed temporal horizon. The retained benchmark provides observational trajectories for estimator fitting and paired intervention runs for causal-effect scoring.

The four workflow configurations are stored under `configs/`, and benchmark generation is implemented in `simulator/`.

### Comparison methods

The repository contains:

- the full DCHAG estimator;
- an observational outcome model;
- qualitative and SEAG-inspired risk scores;
- structural DCHAG ablations;
- a cross-fitted causal g-formula baseline;
- a dense sequential g-formula baseline using rich observable histories.

The dense sequential g-formula provides the strongest causal comparison in the retained evaluation because it can exploit time-varying observed history while remaining independent of DCHAG's supplied causal topology.

## 6. Main experimental results

The retained results characterize both the validated strengths of DCHAG and the operating conditions that shape causal accuracy.

### 6.1 Intervention-effect fidelity

Across the 16 workflow-control evaluation units, DCHAG reaches a mean absolute intervention-effect error of **0.003906**. The observational outcome comparator reaches **0.016110**, giving DCHAG a mean absolute-error reduction of approximately **0.0122**; the paired bootstrap interval for the DCHAG-minus-comparator difference is entirely below zero.

Structural ablations show substantially larger effect errors:

| Model | Mean intervention-effect MAE |
|---|---:|
| **DCHAG full** | **0.003906** |
| Observational outcome | 0.016110 |
| DCHAG without human structure | 0.039203 |
| DCHAG without temporal structure | 0.049972 |
| DCHAG technical-only | 0.054763 |
| DCHAG without process structure | 0.055248 |

The paired Holm-corrected comparisons between full DCHAG and each structural ablation are significant in the retained analysis. These results directly support the contribution of the human, process, and temporal causal structure to intervention-effect recovery.

### 6.2 Strong causal baseline

The dense sequential g-formula reaches effect MAE **0.006206**, while DCHAG reaches **0.003906** on the same 16 workflow-control units. Both methods identify the highest-effect control in all four evaluated workflows, yielding zero normalized regret for the selected control.

The paired effect-error difference is **-0.00230** in favor of DCHAG, with a 95% interval spanning zero and an exact sign-flip `p = 0.159119`. This result establishes **competitive effect fidelity against a strong longitudinal causal estimator**, while DCHAG additionally supplies the typed attack-path semantics, explicit intervention targets, and cross-workflow causal contract evaluated elsewhere in the benchmark.

### 6.3 Control ranking

For the full DCHAG model:

- mean Kendall rank correlation: **0.8333**;
- mean Spearman rank correlation: **0.9000**;
- mean normalized control-selection regret: **0.0000**.

The best true control is recovered in each of the four workflows.

### 6.4 Path recovery and structural ablation

The complete DCHAG model reaches mean path precision, recall, and F1 of **1.000** across the retained simulator workflows. Removing structural components reduces path recovery:

| Variant | Mean precision | Mean recall | Mean F1 |
|---|---:|---:|---:|
| **DCHAG full** | **1.000** | **1.000** | **1.000** |
| No human layer | 1.000 | 0.846 | 0.907 |
| No process layer | 1.000 | 0.658 | 0.759 |
| Technical-only | 1.000 | 0.658 | 0.759 |
| No temporal structure | 0.689 | 0.561 | 0.594 |

This ablation localizes the contribution of the socio-technical and temporal representation to causal-path recovery.

### 6.5 Partial observability

Under random event missingness, intervention-effect MAE evolves from **0.003906** with complete evidence to **0.004060** at 10% missingness, **0.004413** at 30%, and **0.006010** at 50%. Mean path F1 evolves from **1.000** to **0.957**, **0.858**, and **0.737**, respectively.

These curves quantify the evidence-coverage range over which the retained estimator preserves low intervention-effect error and useful path reconstruction.

### 6.6 Structural misspecification

The structural-edge-drop experiment reaches mean intervention-effect MAE **0.01520** and mean path F1 **0.875**. The result provides a direct sensitivity measure for topology quality and motivates explicit validation of causal structure when DCHAG is transferred to operational environments.

### 6.7 Scaling

The retained scaling study exercises graph size, event volume, and control count. Representative measured runs include:

- 12 attack nodes: ~0.047 s;
- 100 attack nodes: ~0.490 s;
- 400 attack nodes: ~2.136 s;
- 1,000 event rows: ~0.951 s;
- 3,000 event rows: ~3.012 s;
- 16 controls: ~1.234 s.

These measurements characterize the reference implementation's practical operating envelope and provide a baseline for future optimization.

## 7. Scientific positioning

DCHAG sits at the intersection of five established research lines:

- attack graphs and probabilistic attack graphs;
- human-aware and multilayer socio-technical attack graphs;
- business-process and mission-aware cyber-risk modeling;
- dynamic causal attack graphs and temporal cyber-risk models;
- structural causal inference for cyber-defense interventions.

Prior work already provides important portions of this landscape. Multilayer attack graphs connect human, access, business, and network layers. Process-aware risk models connect cyber events with business and mission dependencies. Dynamic causal attack graphs add temporal causal propagation. Causal cyber-defense studies use SCMs, interventions, and counterfactual reasoning for mitigation decisions. Process-mining research also estimates causal intervention effects over event logs.

DCHAG's specific contribution is the **joint executable contract** formed by:

1. explicit human-decision, process-state, and technical-state node types;
2. time-unrolled structural causal semantics across those node families;
3. defensive controls represented as structural interventions in the same model;
4. compromise-risk effects evaluated directly against paired simulator intervention effects;
5. path-level causal evidence and control ranking generated by the same engine;
6. one unchanged causal engine exercised across four distinct workflows;
7. ablation, missingness, misspecification, and scaling analyses tied to that same contract.

The novelty claim therefore rests on this integrated, experimentally validated causal semantics and effect-fidelity contract. Individual ingredients remain grounded in their respective established literatures.

## 8. Repository structure

```text
DCHAG/
├── dchag/                       # Core typed temporal causal engine
├── estimation/                  # Fitted SCM / effect estimation
├── simulator/                   # Structural-equation benchmark generator
├── simulator/world_configs/     # Simulator world definitions
├── configs/                     # Four retained workflow configurations
├── baselines/                   # Observational, risk-score and causal baselines
├── benchmarks/                  # Generated benchmark worlds and oracle summaries
├── experiments/                 # Frozen run/scoring protocols and amendments
├── results/
│   ├── raw/                     # Retained raw experiment outputs
│   ├── processed/               # Aggregated effect/ranking/path/robustness tables
│   ├── statistics/              # Paired tests and confidence intervals
│   ├── q1_causal_baseline/      # Cross-fitted g-formula comparison
│   └── q1_dense_sequential_gformula/ # Strong longitudinal causal baseline
├── spec/                        # Formal specification, ontology and threat model
├── tests/                       # Semantic, simulator, estimator and baseline tests
├── environment.yml
├── pyproject.toml
└── SHA256SUMS.txt
```

The public repository is focused on the executable scientific artifact and reproducibility materials. Submission documents and internal editorial-audit material are maintained separately.

## 9. Reproducibility procedure

### 9.1 Prerequisites

Recommended environment:

- Linux, macOS, or WSL2;
- Python 3.11+;
- at least 8 GB RAM for the retained benchmark scale;
- sufficient storage for regenerated benchmark trajectories and experiment outputs.

### 9.2 Clone

```bash
git clone https://github.com/EkodeckStephane/DCHAG.git
cd DCHAG
```

### 9.3 Create the environment

Using Conda/Mamba:

```bash
conda env create -f environment.yml
conda activate dchag
```

or with a standard Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\Activate.ps1    # PowerShell
pip install --upgrade pip
pip install -e .
```

### 9.4 Run the semantic/software tests first

```bash
PYTHONPATH=. pytest -q
```

The retained release passes **29/29 tests** covering the core engine, estimator, simulator, specification contracts, and causal baselines.

### 9.5 Generate the benchmark worlds

```bash
PYTHONPATH=. python simulator/generate_benchmarks.py
```

The generator uses the retained workflow/world configurations and fixed seeds. The resulting benchmark directories contain observational trajectories and the simulator-side structures required by the experiment pipeline.

### 9.6 Run the retained experiment suite

```bash
PYTHONPATH=. python experiments/run_retained.py
PYTHONPATH=. python experiments/score_retained.py
```

These scripts generate the primary prediction, intervention-effect, ranking, path and ablation outputs.

### 9.7 Run robustness analysis

```bash
PYTHONPATH=. python experiments/run_robustness.py
```

The retained robustness protocol evaluates random missingness, human/process observability reduction, and structural-edge perturbation.

### 9.8 Run the strong causal baselines

Cross-fitted g-formula:

```bash
PYTHONPATH=. python experiments/run_q1_causal_baseline.py
PYTHONPATH=. python experiments/score_q1_causal_baseline.py
```

Dense sequential g-formula:

```bash
PYTHONPATH=. python experiments/run_q1_dense_sequential_gformula.py
PYTHONPATH=. python experiments/score_q1_dense_sequential_gformula.py
```

The protocol amendments under `experiments/` record the causal-baseline designs and the order in which prediction outputs and intervention ground truth were frozen/scored.

### 9.9 Run scaling analysis

```bash
PYTHONPATH=. python experiments/run_scaling.py
```

Scaling results are written to `results/processed/scaling_results.csv`.

### 9.10 Inspect retained outputs

Key files include:

```text
results/processed/effect_accuracy.csv
results/processed/effect_model_summary.csv
results/processed/control_ranking.csv
results/processed/control_ranking_summary.csv
results/processed/path_metrics.csv
results/processed/path_metric_summary.csv
results/processed/robustness_summary.csv
results/processed/scaling_results.csv
results/statistics/effect_error_pairwise_tests.csv
results/q1_dense_sequential_gformula/paired_effect_comparison.csv
```

## 10. Integrity and provenance

DCHAG separates scientific configuration, benchmark generation, estimation, scoring, and statistical analysis. The retained workflow records fixed seeds, experiment manifests, pre-scoring hashes for causal-baseline outputs, and repository-wide SHA-256 checksums.

Key integrity mechanisms include:

- fixed workflow configurations under `configs/`;
- formal causal and intervention contracts under `spec/`;
- experiment manifests under `experiments/`;
- pre-scoring hashes in the causal-baseline result directories;
- `SHA256SUMS.txt` for the reproducibility snapshot;
- regression tests covering causal-engine and simulator behavior.

The submitted study identifies an immutable Git commit so the evaluated artifact can be retrieved independently of later repository development.

## 11. Scope, interpretation, and future validation

The current causal-effect oracle is established in controlled synthetic socio-technical worlds whose structural equations are known. This design enables direct measurement of intervention-effect fidelity, which is the central validation target of the study.

Operational transfer requires a corresponding causal-identification basis: randomized interventions, quasi-experimental evidence, validated structural assumptions, or another defensible identification design. The retained missingness and structural-edge-drop experiments quantify sensitivity to two major transfer conditions: evidence coverage and topology quality.

The natural next validation step is therefore an organizational or cyber-range study where selected human, process, and technical controls can be intervened upon prospectively and compared with DCHAG's pre-specified effect estimates.

## 12. Authors

- Stéphane Gaël R. Ekodeck
- **Serge Alain Ebele — corresponding author**
- Arthur Ulrich Ewane
- Chantal Marguerite Mveh-Abia
- René Ndoundam

## 13. Citation

Citation metadata will be frozen with the final manuscript metadata and immutable reproducibility commit. Until then, cite the repository as:

```text
Ekodeck, S. G. R.; Ebele, S. A.; Ewane, A. U.; Mveh-Abia, C. M.; Ndoundam, R.
DCHAG: Dynamic Causal Human Attack Graphs for Counterfactual Cyber Risk.
GitHub repository: https://github.com/EkodeckStephane/DCHAG
```

## 14. License

The software license will be added after final author confirmation. Source provenance and authorship remain preserved in the repository history.