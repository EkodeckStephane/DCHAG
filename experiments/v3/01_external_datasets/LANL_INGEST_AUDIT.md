# V3-LANL-INGEST-001 — result audit

## Execution identity

- GitHub Actions run: `32492306966`
- PR execution branch: `dchag-v3-lanl-ingest-run`
- head commit: `51a4dccad81113a606ca4e231d42efd2695d55a8`
- result artifact ID: `9451370240`
- artifact ZIP SHA-256: `dd760ca287760262d58841bc3de78e15e806230e4fcb3e893b973c3250b14fd0`
- retained JSON SHA-256 before commit: `7cd97ae83888a6c693d229b0f93a9b2ef09837d0f59286f9011d89e8b4e7cdbe`

All workflow steps completed successfully, including the frozen mapping/ingestion tests, source downloads, source integrity recording, full streaming ingestion, no-C/no-ground-truth guardrail assertions, and aggregate artifact upload.

## Frozen source integrity

- host `wls_day-02.bz2`: 484,427,415 bytes; SHA-256 `e6faf4c57f688d60403111000787b855604e3c188d1e58a3e020ef5811e32527`;
- network `netflow_day-02.bz2`: 1,077,270,484 bytes; SHA-256 `7e1a148ec1828ff829b613e026769f038a9bc699e5f3d85c4652f4058df9f019`.

## Primary outcomes

The frozen parser consumed:

- 64,844,144 host records, with 64,844,144 parsed and 0 malformed;
- 115,949,436 network records, with 115,949,436 parsed and 0 malformed.

The adapter emitted 200,384,872 typed observations:

- `H`: 19,591,292 (9.7768%);
- `P`: 16,677,252 (8.3226%);
- `T`: 164,116,328 (81.9006%).

The host side exposed 10,432 unique de-identified person accounts, 5,895 process names, 137,941 process IDs, 6,551,136 unique observed `(user, host, logon_id)` keys and 951,738 unique observed `(user, host, process_id)` keys.

## Host/network linkage

- unique host-side devices: 12,151;
- unique network devices: 23,521;
- intersection: 11,558;
- union: 24,114;
- Jaccard: 0.4793066;
- 95.12% of host-side device identifiers appear in the network stream;
- 49.14% of network device identifiers appear in the host stream.

This is strong evidence for identifier-level cross-source linkage feasibility, but identifier overlap alone is not a causal edge.

## Temporal audit

Host timestamps cover `[86400, 172799]`, exactly 24 hours, with no within-stream order violations. Network timestamps cover `[118781, 172799]`, approximately 15.005 hours, also with no order violations.

Therefore day 02 is the earliest released day containing both source files, but the released netflow file does **not** cover the whole 24-hour host interval. Any downstream host/network trajectory experiment must either restrict to the actual overlap window `[118781, 172799]` or model source availability explicitly. It must not call the entire day a fully synchronized 24-hour window.

## Human-evidence audit

Of the 64,844,144 host records:

- 19,591,292 (30.21%) reference a de-identified person account matching `User<digits>`;
- 33,741,371 (52.03%) reference a machine account ending in `$`;
- 11,507,637 (17.75%) reference named/other accounts;
- 3,844 are missing the selected account field.

The pre-execution mapping correction that restricted `H` to the de-identified person namespace was therefore material: treating every nonempty `UserName` as human evidence would have severely inflated H coverage.

## Scientific conclusion

`V3-LANL-INGEST-001` passes its observational-ingestibility objective. DCHAG v3 can ingest a large real operational host/network slice with complete parsing under the frozen schema, produce all three observational H/P/T evidence classes, retain millions of session/process linkage keys, and match most host devices to the network stream.

This result does **not** establish counterfactual intervention effects, attacker intent, causal-edge correctness, causal superiority, or defensive-control effectiveness. No attack/red-team labels were read and no `C` intervention was inferred.

## Next admissible experiment

Construct real observational trajectories only within the genuine cross-source overlap window `[118781, 172799]`, with a pre-registered temporal aggregation/windowing policy and no red-team labels. The next block should test trajectory construction, typed-state occupancy, path continuity, and structure-learning feasibility before any semi-synthetic intervention layer is introduced.
