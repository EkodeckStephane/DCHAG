# DCHAG

**DCHAG** is the reproducibility repository for **Dynamic Causal Human Attack Graphs for Counterfactual Cyber Risk**. It implements an auditable typed temporal structural causal model connecting human (`H`), process/workflow (`P`), technical (`T`), and defensive-control (`C`) variables in one intervention framework.

Repository: **https://github.com/EkodeckStephane/DCHAG**

> Scientific source of truth: `dchag-v3`. The public `main` branch is intentionally not synchronized until the final publication-release gate is approved.

## 1. Scientific objective

Cyber compromise can propagate through human decisions, organizational workflows, and technical states. DCHAG evaluates sustained defensive-control interventions while preserving an explicit typed temporal structure that can be audited at both scalar-effect and mechanism-attribution levels.

The v3 evidence program separates four questions that must not be conflated:

1. causal-effect recovery in explicit semi-synthetic SCM worlds with intervention truth;
2. transportability and identification boundaries;
3. observational portability on real LANL and OpTC telemetry;
4. engineering/scaling behavior.

## 2. Principal confirmatory result

The authoritative principal study is `V3-SS-CONF-001`, evaluated on **16 pre-reserved LANL-anchored semi-synthetic worlds** (four workflow families, four worlds per family).

- DCHAG mean intervention-effect MAE: **0.01131125**.
- Dense sequential g-formula MAE: **0.01180677**.
- Paired world-level DCHAG−dense difference: **−0.000495521**.
- 10,000-bootstrap 95% CI: **[−0.002568289, 0.001717745]**.
- Exact 65,536-assignment sign-flip p-value: **0.6671143**.
- Both methods recover the simulator highest-effect control in **16/16** worlds with zero normalized regret.
- DCHAG semi-synthetic structural edge F1: **0.81533**.
- Dense-g is slightly better on the held-out predictive Brier/BSS secondary endpoint.

**Interpretation:** DCHAG and dense sequential g-formula have competitive/statistically compatible scalar causal-effect fidelity in this benchmark. The evidence does **not** establish DCHAG superiority or formal equivalence.

## 3. Distinct positive typed-attribution result

`V3-TMA-001-C1` evaluates typed mechanism-replay attribution in the same immutable semi-synthetic SCM benchmark using a separate pre-specified endpoint.

- DCHAG mean typed mechanism-attribution error (TMAE): **0.00273528**.
- Dense sequential g-formula TMAE: **0.00385100**.
- Paired difference: **−0.00111572**.
- 10,000-bootstrap 95% CI: **[−0.00153806, −0.00072592]**.
- Exact sign-flip p-value: **0.00009155**.
- DCHAG has lower TMAE in **15/16** worlds.
- Dominant-mechanism accuracy: **59/64** for DCHAG versus **55/64** for dense-g.

This result is endpoint-specific. It does **not** revise the null/non-superiority scalar-effect comparison above and does not establish natural indirect effects or real-world causal mechanisms.

## 4. Transportability, identification, and decision boundaries

### Cross-family transport (`V3-SS-LOFO-001`)

Learning endogenous mechanisms only from the other three workflow families materially degrades both methods:

- DCHAG LOFO MAE: **0.03291823**;
- dense-g LOFO MAE: **0.03156333**;
- DCHAG−dense mean: **+0.00135490**;
- hierarchical-bootstrap 95% CI: **[−0.00316520, 0.00576903]**.

Both still recover the highest-effect control in 16/16 held-out worlds. No DCHAG transport-superiority claim is supported.

### Hidden confounding (`V3-SS-HC-001`)

Under the frozen strong latent-confounding mechanism, DCHAG MAE rises to **0.01791604**, a **+0.00660479** penalty relative to RQ1 (95% CI **[0.00415806, 0.00904929]**, exact p=**0.00024414**). Dense-g degrades more under this particular mechanism, but this does not establish general robustness to arbitrary hidden confounding.

### Finite-sample decision stability (`V3-SS-DEC-001`)

With 40 trajectory-cluster bootstraps per world/model, DCHAG and dense-g both have mean top-control switch rate **0.0015625**. Only one of sixteen worlds switches, and the same switch occurs for both methods. This is high benchmark-specific top-choice stability, not a DCHAG-specific advantage or posterior-uncertainty result.

## 5. Real observational portability

### LANL

The LANL workstream demonstrates large-scale observational H/P/T ingestion and temporal trajectory construction. The primary 300-s artifact contains **2,642,689 active device-window rows over 31,243 devices**. On unseen days, scale-aware sparse models preserve recurrent observational P→P, P→T, and T→T dependencies and useful P/T prediction. The corrected human-login (`H`) endpoint remains weak/negative and is retained as such.

LANL provides **no intervention oracle**. These results do not establish real causal edges, real defensive-control effectiveness, or attacker intent.

### OpTC

The corrected OpTC C2 pilot maps **10,000/10,000** immutable eCAR records with zero mapping failures. Record-level typed coverage is H **98.90%**, P **4.47%**, and T **95.53%**; all timestamps normalize across a **127.23-s** span. Raw source order is nonchronological and explicit event-time handling is therefore required.

The preceding C1 execution failed completely because ISO-8601-with-timezone timestamps were incorrectly normalized. That failed run is preserved in provenance rather than hidden.

## 6. Computational scaling

`V3-SCALE-001` shows lower absolute DCHAG fit time at every frozen tested point. The dense/DCHAG fit-time ratio reaches **4.321×** at 48 endogenous nodes and **3.653×** at 24 nodes / 1,200 trajectories.

This is not a universal scaling advantage: DCHAG has steeper observed log-log fit-time slopes (graph **1.546 vs 1.405**; sample **0.597 vs 0.301**) and no consistent memory advantage.

## 7. Repository structure

```text
DCHAG/
├── dchag/                         # Core typed temporal causal engine
├── estimation/                    # Fitted SCM / intervention estimation
├── simulator/                     # Benchmark generator
├── configs/                       # Workflow configurations
├── baselines/                     # Observational and causal comparators
├── experiments/
│   └── v3/
│       ├── 01_external_datasets/
│       ├── 02_semisynthetic/
│       ├── 03_transportability/
│       ├── 04_hidden_confounding/
│       ├── 05_decision_uncertainty/
│       ├── 06_scaling/
│       ├── 07_typed_effect_attribution/
│       ├── EXPERIMENT_LEDGER.md
│       ├── MANUSCRIPT_CLAIM_MATRIX.md
│       └── SCIENTIFIC_CLOSURE_AUDIT.md
├── provenance/
├── tests/
├── environment.yml
├── pyproject.toml
└── SHA256SUMS.txt
```

Manuscript/editorial files are maintained separately from the reproducibility source tree.

## 8. Reproducibility and provenance

Create the repository environment and run software tests first:

```bash
conda env create -f environment.yml
conda activate dchag
PYTHONPATH=. pytest -q
```

The v3 experiments are governed by frozen protocols, exact seeds, artifact identities, public/private estimator firewalls, and GitHub Actions workflows under `.github/workflows/`. The authoritative mapping from claim to protocol, commit, workflow run, artifact digest, and admissible interpretation is:

- `experiments/v3/EXPERIMENT_LEDGER.md`;
- `experiments/v3/MANUSCRIPT_CLAIM_MATRIX.md`;
- experiment-specific `*_AUDIT.md` and `*_AUDITED_SUMMARY.json` files.

The recovered hardened-v2 reference package is separately identified by SHA-256 `d821d3f6e5a6f73efd7935f0cc2223f55e029b1730edb1fbfd8bfc2d0b7dace3` and passes its retained 33/33 recovery tests. It must remain distinguishable from the v3 evidence program.

## 9. Mandatory interpretation boundaries

The repository deliberately preserves unfavorable and null outcomes. Publication-facing statements must respect the following boundaries:

- no DCHAG superiority claim for principal scalar causal-effect MAE;
- no formal-equivalence claim without a pre-specified equivalence test;
- no real LANL/OpTC causal-effect or control-effectiveness claim;
- no general hidden-confounding robustness claim;
- no DCHAG-specific advantage for finite-sample top-control stability;
- no better asymptotic-scaling or general memory-efficiency claim;
- no use of the positive typed-attribution endpoint to overwrite the scalar-effect non-superiority result.

## 10. Authors

- Stéphane Gaël R. Ekodeck
- **Serge Alain Ebele — corresponding author**
- Arthur Ulrich Ewane
- Chantal Marguerite Mveh-Abia
- René Ndoundam
