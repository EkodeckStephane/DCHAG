# V3-OPTC-INGEST-001-C1 — retained failed execution

## Status

FAILED. This run is retained as scientific/debugging evidence and is not eligible for manuscript claims.

## Execution

- GitHub Actions run: `33063142611`
- job: `98486625967`
- execution PR: `#18`
- PR base: `617b0ae93048775531befec6b4638c91437ea67c`
- PR head: `5a37dd87a16f8813f1c41190e90c2d403bb0ba3f`
- checked-out PR merge-ref: `8789833b13820714ebc4981240a98a616a260d9b`

## What passed

- frozen protocol/amendment/C1 files present;
- mapping and temporal regression tests: 7/7 passed;
- immutable source download succeeded;
- source identity matched exactly: 5,649,857 bytes and Git blob SHA-1 `25279a41030981ead9bf6134432aa6112429eb82`;
- red-team ground truth was not read.

## Failure observed

The ingestion produced 10,000 source records but:

- mapping failures: 10,000/10,000;
- typed observations: 0;
- valid timestamps: 0.

The post-ingestion guardrail therefore failed before provenance freezing and artifact upload. No result artifact was promoted.

## Root cause

Inspection of the exact immutable source blob showed that its `timestamp` field is an ISO-8601 string with timezone offset, e.g. `2019-09-23T15:47:55.538-04:00`. The frozen adapter used `int(timestamp)`, and the ingestion temporal collector likewise attempted `int(timestamp)`. Thus the same schema mismatch caused both all-record mapping failure and zero temporal coverage.

This is an implementation/schema-normalization defect, not a reason to substitute the source, change H/P/T semantics, or relax the guardrails.

## Required correction

A separately frozen C2 must normalize supported numeric or ISO-8601 timestamps to Unix epoch milliseconds in one shared function used by both mapping and ingestion. All source identity, H/P/T mapping, exclusion, and claim-boundary rules remain unchanged.
