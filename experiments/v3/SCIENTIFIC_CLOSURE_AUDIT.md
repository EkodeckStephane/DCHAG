# DCHAG v3 scientific closure audit

## Closure decision

The planned v3 experimental suite is sufficiently frozen and audited for manuscript use. No additional experiment is required merely to obtain a positive result or to make DCHAG outperform the dense comparator. Further experiments should be motivated by a new scientific question, an external-review request, or a newly discovered validity defect.

This closure audit is based on the public `dchag-v3` source-of-truth branch after completion of the principal causal study, cross-family transport, hidden-confounding sensitivity, decision-stability analysis, computational scaling, LANL observational transportability, and corrected OpTC observational ingestion.

## Completed evidence blocks

### Principal causal-effect fidelity

`V3-SS-CONF-001` is protocol-complete over 16 pre-reserved worlds. DCHAG effect MAE is 0.01131125 versus 0.01180677 for dense sequential g-formula. The paired world-level difference is −0.000495521 with bootstrap 95% CI [−0.002568289, 0.001717745] and exact sign-flip p=0.6671143. The admissible interpretation is competitive/statistically compatible effect fidelity. Superiority and formal-equivalence claims remain outside the evidence.

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

## Manuscript consistency audit

The current final manuscript and cover letter already reflect the frozen v3 evidence, including:

- DCHAG 0.01131 versus dense-g 0.01181 in the principal confirmatory benchmark;
- no superiority or formal-equivalence claim;
- LOFO degradation for both methods;
- strong hidden-confounding degradation as an identification boundary;
- shared finite-sample top-control stability;
- lower DCHAG fit time over the tested range together with steeper observed scaling slopes and no consistent memory advantage;
- real LANL and corrected OpTC evidence explicitly separated from causal intervention truth;
- corrected OpTC pilot values: all 10,000 records mapped, zero failures, H/P/T 98.90%/4.47%/95.53%, 127.23-s normalized timestamp span, nonchronological source order.

The internal `MANUSCRIPT_CLAIM_MATRIX.md` is the normative claim boundary for any further text edits.

## Repository state and branch policy

- `dchag-v3` remains the persistent scientific source of truth.
- `main` remains unchanged by this closure action.
- Draft PR #1 (`dchag-v3` → `main`) must remain unmerged until a deliberate public-release synchronization decision is made.
- Technical execution PRs are evidence carriers and should remain closed without merge unless a correction explicitly needs to enter `dchag-v3`.

## Remaining pre-submission work

The remaining work is packaging and consistency control, not result generation:

1. freeze a reproducibility snapshot from the final `dchag-v3` state;
2. record its exact branch/head and SHA-256 in the submission package;
3. verify the snapshot contains the final audits, claim matrix, OpTC C1/C2 correction records, and experiment ledger while excluding manuscript/editorial files according to the package policy;
4. update any submission README/checklist/manifest that still references an older reproducibility snapshot;
5. run the manuscript lint rules and final cross-file title/authorship/corresponding-author checks before upload.

## Closure conclusion

The project now contains a defensible Q1-level evidence profile precisely because it preserves null, negative, corrected, and comparator-favorable results. The principal scientific story is an auditable causal intervention framework with competitive effect fidelity and explicit transport, identification, decision-stability, observational-portability, and engineering boundaries. Publication-facing claims must remain inside those measured boundaries.
