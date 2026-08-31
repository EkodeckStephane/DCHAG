# DCHAG v3 scientific closure audit

## Closure decision

The v3 experimental suite is scientifically closed for the current manuscript. No additional experiment is required merely to obtain a positive result or to make DCHAG outperform the dense comparator. Further experiments should be motivated by a new scientific question, an external-review request, or a newly discovered validity defect.

This closure audit covers the principal causal study, cross-family transport, hidden-confounding sensitivity, decision-stability analysis, computational scaling, LANL observational portability, corrected OpTC observational ingestion, and the later typed mechanism-attribution study.

## Completed evidence blocks

### Principal scalar causal-effect fidelity

`V3-SS-CONF-001` is protocol-complete over 16 pre-reserved worlds. DCHAG effect MAE is 0.01131125 versus 0.01180677 for dense sequential g-formula. The paired world-level difference is −0.000495521 with bootstrap 95% CI [−0.002568289, 0.001717745] and exact sign-flip p=0.6671143.

The admissible interpretation is competitive/statistically compatible scalar effect fidelity. Superiority and formal-equivalence claims remain outside the evidence.

### Typed mechanism attribution

`V3-TMA-001-C1` is complete on the same immutable 16 semi-synthetic SCM worlds using a distinct typed mechanism-replay attribution endpoint. DCHAG mean TMAE is 0.00273528 versus 0.00385100 for dense sequential g-formula; paired difference −0.00111572 with bootstrap 95% CI [−0.00153806, −0.00072592] and exact sign-flip p=0.00009155. DCHAG has lower TMAE in 15/16 worlds; dominant-mechanism accuracy is 59/64 versus 55/64.

This is a genuine positive endpoint, but it does not revise the RQ1 scalar-effect non-superiority result. It is restricted to the explicit semi-synthetic SCM and does not establish natural indirect effects, real LANL/OpTC causal mechanisms, real causal edges, or real defensive-control effectiveness.

### Cross-family transport

`V3-SS-LOFO-001` is complete. DCHAG LOFO MAE is 0.03291823 and dense LOFO MAE 0.03156333. Transfer is materially harder for both estimators; no DCHAG advantage is established.

### Hidden-confounding sensitivity

`V3-SS-HC-001` is complete. Under the frozen strong latent-confounding mechanism, DCHAG MAE becomes 0.01791604, giving a +0.00660479 penalty relative to RQ1 with 95% CI [0.00415806, 0.00904929]. This is an empirical identification limitation. DCHAG degrades less than dense-g under this particular mechanism, which must not be generalized to arbitrary unobserved confounding.

### Decision stability

`V3-SS-DEC-001` is complete. DCHAG and dense-g both have mean top-control switch rate 0.0015625 over 40 trajectory-cluster bootstraps per world/model. The only retained top switch occurs in one of sixteen worlds and is shared by both estimators. This supports benchmark-specific top-choice stability, not full rank invariance or posterior uncertainty calibration.

### Computational scaling

`V3-SCALE-001` is complete. DCHAG has lower absolute fit time at all frozen tested points, including dense/DCHAG ratios 4.321× at 48 endogenous nodes and 3.653× at 24 nodes/1200 trajectories. DCHAG has steeper observed log-log slopes and no consistent memory advantage. The safe claim is a test-range absolute fit-time advantage, not superior asymptotic scaling.

### LANL observational evidence

The LANL ingestion, trajectory, scale-diagnostic, multi-day, and extended P/T workstreams are complete and audited. They establish large-scale H/P/T observational ingestibility, temporal trajectory construction, recurrent P/T observational dependencies, and useful P/T predictive portability. The corrected human-login endpoint remains weak/negative and is retained as such. LANL does not provide intervention truth.

### OpTC corrected observational evidence

The original protocol row `V3-OPTC-INGEST-001` was followed by a retained failed execution `V3-OPTC-INGEST-001-C1` and corrected successful execution `V3-OPTC-INGEST-001-C2`. The C2 run maps 10,000/10,000 immutable pilot records with zero mapping failures, H/P/T record-level coverage 98.90%/4.47%/95.53%, 10,000 valid normalized timestamps over 127.23 s, and a nonchronological raw source order. The authoritative correction supplement is `EXPERIMENT_LEDGER_CORRECTIONS_2026-08-27.md`.

## Provenance defects and corrections retained

The following records remain part of the scientific history and must not be deleted or silently rewritten:

- original `V3-SS-SEL-001`, invalidated because split-local trajectory IDs collided during standardization;
- corrected `V3-SS-SEL-001-C1`, which froze cap 8 using exactly 1,500 split-qualified anchors/world;
- OpTC ingestion C1, failed due to ISO-8601 timestamp normalization mismatch;
- OpTC ingestion C2, corrected without changing source identity or H/P/T semantics;
- non-authoritative duplicate decision-stability execution, explicitly excluded from scientific use;
- all null/unfavorable comparator outcomes documented in the experiment ledger and claim matrix.

## Current manuscript claim boundary

The normative internal control is `MANUSCRIPT_CLAIM_MATRIX.md`. The manuscript-safe empirical story is:

- competitive/statistically compatible principal scalar causal-effect fidelity versus dense-g, without superiority or formal equivalence;
- exact top-control recovery in the principal semi-synthetic worlds for both methods;
- a distinct positive typed mechanism-attribution endpoint favoring DCHAG;
- explicit degradation under leave-one-family-out transfer;
- explicit degradation under strong hidden confounding;
- finite-sample top-choice stability shared by DCHAG and dense-g;
- lower DCHAG fit time over the tested engineering range together with steeper observed scaling slopes and no consistent memory advantage;
- real LANL and corrected OpTC evidence restricted to observational portability/ingestibility.

The positive typed-attribution endpoint must never be used to rewrite the null scalar-effect comparison.

## Repository state and branch policy

- `dchag-v3` is the persistent scientific source of truth.
- `main` remains intentionally unchanged until the final publication-release synchronization gate.
- Draft PR #1 (`dchag-v3` → `main`) remains unmerged.
- Technical execution PRs remain closed without merge after their artifacts are retained and audited.
- The root README, experiment ledger, claim matrix, and this closure audit must agree before the publication snapshot is frozen.

## Final pre-submission gate

Result generation is closed. The remaining actions are repository/package controls:

1. regenerate the repository SHA-256 manifest from the aligned `dchag-v3` content, excluding the manifest itself;
2. freeze a publication/reproducibility snapshot branch at that exact scientific-content head;
3. record the frozen branch/head/tree identity in a dedicated snapshot record on `dchag-v3`;
4. update draft PR #1 with the snapshot identity while keeping it unmerged;
5. perform final manuscript/submission cross-file consistency checks before upload.

## Closure conclusion

The project has a defensible Q1-level evidence profile because null, negative, comparator-favorable, failed, corrected, and positive endpoint-specific results are all preserved. The strongest contribution is not universal estimator superiority. It is an auditable typed temporal intervention framework with competitive scalar effect fidelity, a positive typed mechanism-attribution result, explicit transport and identification limits, stable benchmark-level control choice, observational portability, and measured engineering trade-offs.
