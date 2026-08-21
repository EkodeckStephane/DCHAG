# V3-LANL-INGEST-001 — frozen ingestion protocol

## Purpose

Measure whether the frozen LANL→DCHAG observational adapter can ingest a real operational day and retain enough typed H/P/T and temporal linkage evidence for later external-validity experiments.

This experiment does **not** estimate causal intervention effects and does **not** use attack/red-team labels as model inputs.

## Frozen source slice

Use LANL Unified Host and Network Data Set **day 02**, the first day for which both released streams are available:

- host events: `https://lanl.ma.ic.ac.uk/data/2017/wls/wls_day-02.bz2`;
- netflow: `https://lanl.ma.ic.ac.uk/data/2017/netflow/netflow_day-02.bz2`.

The official release publishes host days 01–90 and netflow days 02–90. Day 02 is selected solely because it is the earliest complete cross-source overlap; it is not selected after inspecting DCHAG performance.

The raw compressed files are never committed to the DCHAG repository. The run records downloaded byte sizes and SHA-256 digests in the retained aggregate result.

## Adapter freeze

Use `lanl_adapter.py` with the conservative person-account rule:

- `H`: only authentication/session or process events whose selected account matches `User<digits>`;
- `P`: Windows process start/end (`4688`, `4689`);
- `T`: network flows and non-process host technical events;
- `C`: never inferred from this observational release.

Machine accounts ending in `$` and recognizable system/service accounts must not emit `H`.

## Primary endpoints

1. successful parse fraction for host and network streams;
2. emitted counts and proportions of `H`, `P`, and `T` observations;
3. unique de-identified person accounts associated with `H`;
4. unique host/log/network devices retained;
5. overlap between host-side device identifiers and network endpoints;
6. time-span coverage and within-stream timestamp monotonicity violations;
7. number of user-associated process observations and unique observed login-session keys where available.

## Secondary diagnostics

- Windows EventID distribution;
- account-category distribution (`deidentified_person`, `machine_account`, `named_or_other`, `missing`);
- process-name and process-ID coverage;
- host/network malformed-record counts;
- source file SHA-256 and compressed byte size.

## Claim boundary

A successful run can support only claims about:

- observational ingestibility;
- typed evidence coverage;
- cross-source identifier linkage;
- temporal/path-construction feasibility;
- external operational plausibility.

It cannot establish counterfactual effect recovery, intervention correctness, attacker intent, or causal superiority.

## Failure policy

Any download, decompression, parse, schema, memory, or runner failure is retained as `FAILED` with logs. The protocol is not altered after seeing output; changes require a new experiment ID or explicit correction note.
