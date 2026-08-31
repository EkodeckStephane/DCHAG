# V3-OPTC-INGEST-001 — frozen pilot ingestion protocol

## Objective

Measure whether a real OpTC eCAR sample can be represented by the frozen DCHAG v3 observational H/P/T contract without using red-team annotations as model inputs and without making causal-effect claims.

## Frozen source

- Repository: `brbickel/ecar-challenge`
- Commit: `45b7c7c85ddce4b44f84f68af7822c5466a7077d`
- Path: `data.json`
- Expected byte size: `5,649,857`
- Expected Git blob SHA-1: `25279a41030981ead9bf6134432aa6112429eb82`

The raw sample is not copied into the DCHAG repository. The acquisition script verifies both size and Git blob identity before any analysis.

## Frozen mapping

Use `optc_adapter.py` without modification after inspection of performance outputs:

- nonempty `principal` -> observable user-associated `H` evidence;
- `object == PROCESS` -> `P` process-transition evidence;
- other eCAR object types -> `T` technical evidence;
- no `C` variable is inferred from observational telemetry.

## Primary endpoints

1. number of source records and mapping failures;
2. counts of H, P and T typed observations;
3. fraction/count of records carrying `principal` and `hostname`;
4. missing `actorID` and `objectID` counts;
5. source object/action distributions;
6. number and span of valid timestamps and whether source order is nondecreasing.

## Exclusions and causal boundary

- `OpTCRedTeamGroundTruth.pdf` is not read by the ingestion code.
- Attack annotations are not used to define H/P/T variables.
- The pilot does not estimate a defensive-control effect and cannot validate counterfactual fidelity.
- Any later use of red-team truth is post-freeze evaluation evidence only and must be documented separately.

## Execution

`run_optc_ingest.py` produces aggregate-only `OPTC_INGEST_RESULTS.json`. The GitHub Actions workflow `.github/workflows/dchag-v3-optc-ingest.yml` runs the frozen adapter tests before ingestion and uploads the aggregate result as an artifact.

## Current execution state

Protocol and code are frozen. At freeze time, the ChatGPT GitHub connector can identify the 5.65 MB blob but does not return its contents, and the local execution container cannot fetch raw GitHub content. No aggregate result is therefore asserted until an execution artifact is available and inspected.
