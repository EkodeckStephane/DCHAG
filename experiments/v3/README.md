# DCHAG v3 experimental workspace

This directory is the persistent experimental memory for DCHAG v3. No manuscript claim may be promoted from this workspace unless it is traceable to a versioned experiment record and retained result artifact.

## Scientific objective

DCHAG v3 extends the frozen v2 causal-fidelity study toward externally anchored, transportability-aware, and confounding-aware cyber decision support. The v2 null/non-superiority findings against the dense sequential g-formula remain valid and must not be overwritten or selectively replaced.

## Workstreams

1. `01_external_datasets/` — dataset discovery, eligibility audit, licensing and provenance.
2. `02_semisynthetic/` — externally anchored semi-synthetic intervention benchmarks.
3. `03_transportability/` — leave-one-workflow/domain-out transfer experiments.
4. `04_hidden_confounding/` — graded latent-confounding and identification-boundary experiments.
5. `05_decision_uncertainty/` — control ranking under uncertainty and rank-reversal analysis.
6. `06_scaling/` — computational and graph-size scaling.

Directories are materialized when their first protocol is frozen. Empty directories are intentionally not tracked.

## Mandatory experiment lifecycle

Each experiment must follow this order:

1. state the research question and hypothesis;
2. freeze dataset/version/provenance and protocol;
3. record seed(s), environment and commit SHA;
4. run without editing the primary endpoint after inspection;
5. retain raw outputs and logs;
6. score with a separate script where feasible;
7. append the outcome to `EXPERIMENT_LEDGER.md`;
8. keep negative, null and failed results;
9. commit before beginning the next logically independent experiment.

## Evidence rule

The manuscript is downstream of this repository. Numerical manuscript claims must map to a retained result and the code/configuration that generated it.

## v2 boundary

The authoritative v2 package recovered from the project archive is identified by SHA-256:

`d821d3f6e5a6f73efd7935f0cc2223f55e029b1730edb1fbfd8bfc2d0b7dace3  DCHAG_GitHub_V2_FULL.zip`

The recovered package passes 33/33 tests. Its confirmatory study contains 16 independent worlds and must remain distinguishable from the older four-workflow public benchmark currently on `main`.
