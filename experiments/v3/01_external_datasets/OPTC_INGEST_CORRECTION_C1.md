# V3-OPTC-INGEST-001-C1 — temporal-order correction

## Status

FROZEN before the first retained OpTC ingestion result.

## Defect identified pre-execution

The original `run_optc_ingest.py` accumulated valid timestamps, sorted the list, and only then evaluated whether adjacent timestamps were nondecreasing. Sorting makes that endpoint tautologically true and therefore cannot measure source-order monotonicity as required by the frozen protocol.

No V3-OPTC-INGEST-001 aggregate result had been retained or promoted when this defect was identified.

## Frozen correction

Only temporal summarization changes:

1. valid timestamps remain in original source-record order;
2. `source_order_nondecreasing` is computed on that unsorted sequence;
3. minimum and maximum timestamps are computed with `min()` and `max()` without mutating order;
4. span remains `max - min`;
5. all source identity checks, mapping semantics, exclusions, counters, and claim boundaries remain unchanged.

A regression test must show that an intentionally out-of-order sequence returns `source_order_nondecreasing = false` while preserving correct min/max/span.

## Claim boundary

This correction restores one observational temporal-integrity endpoint only. It does not introduce causal labels, intervention truth, or any new performance endpoint.
