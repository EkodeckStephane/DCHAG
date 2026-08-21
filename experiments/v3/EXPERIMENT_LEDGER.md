# DCHAG v3 experiment ledger

This ledger is append-only in scientific meaning: existing outcomes may be corrected only by adding an explicit correction note that preserves the original record and explains the reason.

| ID | RQ | Workstream | Hypothesis / purpose | Dataset / world | Protocol | Code commit | Status | Primary endpoint | Result | Statistical evidence | Conclusion |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V3-BOOT-001 | Infrastructure | repository | Establish persistent, versioned experimental memory before new experiments | DCHAG repository | `experiments/v3/README.md` | `8c2201803b4fe842f0bc6c9b70596fc73da7f65d` | PASS | repository state | v3 workspace created | n/a | Future v3 work must be committed and traceable |
| V2-RECOVERY-001 | v2 provenance | baseline | Verify recovered v2 scientific package before using it as v3 baseline | `DCHAG_GitHub_V2_FULL.zip` | recovered frozen v2 package | local recovered package SHA-256 `d821d3f6e5a6f73efd7935f0cc2223f55e029b1730edb1fbfd8bfc2d0b7dace3` | PASS | software test suite | 33/33 tests passed | pytest | Recovered v2 package is internally executable; synchronization to GitHub remains a separate provenance action |
| V3-EXT-001 | external validity | `01_external_datasets` | Identify external anchors before model scoring and prevent observational attack labels from being treated as intervention truth | LANL Unified / LANL multi-source / OpTC / CERT Insider Threat | `experiments/v3/01_external_datasets/PROTOCOL.md` | `1ee529db48fbada1f430ace34cf83d4643d8d307` | PASS | eligibility audit | LANL and OpTC retained as primary real/operational anchors; CERT retained only as synthetic socio-technical anchor | source-document audit; no performance statistics | v3 external evidence must be multi-source and must separate causal-effect recovery, external transportability and semantic portability |
| V3-OPTC-MAP-001 | external validity | `01_external_datasets` | Freeze a conservative OpTC eCAR→DCHAG mapping before performance inspection | OpTC eCAR schema | `experiments/v3/01_external_datasets/OPTC_MAPPING.md` | adapter `006d40fb8b1dc63db32ba673646819f0e542fd6b`; tests `1adc0ec73caec4359a84cc2c11f1562a223df5ec`; mapping `b971a0ab4a7715f0924b1f0e9485ace862605464` | PASS | mapping regression cases | PROCESS+principal→H+P; technical no-principal→T; FILE+principal→H+T; invalid IDs normalized; missing timestamp rejected | deterministic regression assertions | OpTC can anchor observable H/P/T evidence without inventing C or exposing red-team truth to the adapter |
| V3-OPTC-INGEST-001 | external validity | `01_external_datasets` | Quantify H/P/T observational coverage on an immutable public OpTC eCAR sample | `brbickel/ecar-challenge:data.json` @ `45b7c7c85ddce4b44f84f68af7822c5466a7077d` | `experiments/v3/01_external_datasets/OPTC_INGEST_PROTOCOL.md` | provenance `c31c3a8eba6a20219f468475db1e279ca2171d70`; ingester `e0b829b111f2a33f4c0b2245f64068d6c6bf9966`; workflow `1b6ea646e1ceade06256587291ea05456d3bd04a` | FROZEN | H/P/T coverage, mapping failures, schema completeness, temporal coverage | execution result not yet asserted; source blob identity is frozen as 5,649,857 bytes / Git SHA-1 `25279a41030981ead9bf6134432aa6112429eb82` | none until retained aggregate artifact is inspected | No scientific claim promoted; connector/runtime transfer limitation is recorded rather than replaced by estimated statistics |

## Status vocabulary

- `PLANNED`: hypothesis/protocol not yet frozen.
- `FROZEN`: protocol frozen; execution not yet scored.
- `RUNNING`: execution artifacts being generated.
- `PASS`: experiment completed and evidence retained; does not mean the hypothesis was supported.
- `NULL`: completed with a null primary finding.
- `NEGATIVE`: completed with a result opposing the directional hypothesis.
- `FAILED`: execution/protocol failure; failure record is retained.
- `INVALIDATED`: result cannot support a claim due to a documented defect; original record remains in history.

## Claim promotion rule

A result is manuscript-eligible only when the ledger row identifies the exact protocol, code revision, retained result path, primary endpoint, and statistical evidence where applicable.
