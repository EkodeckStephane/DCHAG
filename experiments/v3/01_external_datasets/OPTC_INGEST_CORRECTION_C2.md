# V3-OPTC-INGEST-001-C2 — ISO-8601 timestamp normalization

## Status

FROZEN before any C2 execution or retained C2 aggregate result.

## Parent failure

`V3-OPTC-INGEST-001-C1` / run `33063142611` is retained as FAILED. The immutable 10,000-record source passed identity checks but all records failed mapping and no timestamp was recognized because both adapter and ingester attempted integer conversion of the source `timestamp` field.

Inspection of the exact immutable blob at the frozen commit shows ISO-8601 timestamps with explicit timezone offsets, for example `2019-09-23T15:47:55.538-04:00`.

## Frozen correction

Introduce one shared parser in `optc_adapter.py`:

- accept integer/float epoch values and numeric strings as epoch milliseconds, preserving the previously supported numeric representation;
- accept ISO-8601 strings with an explicit timezone offset or `Z`;
- convert ISO-8601 values to Unix epoch milliseconds in UTC;
- reject missing, malformed, timezone-naive ISO strings, booleans, and non-finite numeric values.

`map_ecar_event()` and `run_optc_ingest.py` must use this same parser. The ingestion temporal endpoint continues to preserve source-record order as frozen in C1.

## Invariants unchanged

- source repository, commit, path, byte size, and Git blob identity;
- H rule: nonempty `principal` -> user-associated H observation;
- P rule: `object == PROCESS` -> P observation;
- all other object types -> T observation;
- no C/control inference;
- no red-team ground-truth access;
- aggregate-only result;
- same source object/action, coverage, mapping-failure, and temporal endpoints;
- no causal-effect claim.

## Required regression tests

1. the exact example `2019-09-23T15:47:55.538-04:00` parses deterministically to its UTC epoch milliseconds;
2. `Z` timestamps are accepted;
3. existing integer timestamp behavior is preserved;
4. timezone-naive ISO timestamps are rejected;
5. `map_ecar_event` maps a representative real-schema FLOW record with ISO timestamp to H+T rather than failing;
6. C1 source-order temporal tests remain PASS.

No mapping or timestamp validation guardrail may be weakened after inspection of C2 results.
