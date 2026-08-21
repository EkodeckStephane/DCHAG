# DCHAG v3 experiment ledger

This ledger is append-only in scientific meaning: existing outcomes may be corrected only by adding an explicit correction note that preserves the original record and explains the reason.

| ID | RQ | Workstream | Hypothesis / purpose | Dataset / world | Protocol | Code commit | Status | Primary endpoint | Result | Statistical evidence | Conclusion |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V3-BOOT-001 | Infrastructure | repository | Establish persistent, versioned experimental memory before new experiments | DCHAG repository | `experiments/v3/README.md` | `8c2201803b4fe842f0bc6c9b70596fc73da7f65d` | PASS | repository state | v3 workspace created | n/a | Future v3 work must be committed and traceable |
| V2-RECOVERY-001 | v2 provenance | baseline | Verify recovered v2 scientific package before using it as v3 baseline | `DCHAG_GitHub_V2_FULL.zip` | recovered frozen v2 package | local recovered package SHA-256 `d821d3f6e5a6f73efd7935f0cc2223f55e029b1730edb1fbfd8bfc2d0b7dace3` | PASS | software test suite | 33/33 tests passed | pytest | Recovered v2 package is internally executable; synchronization to GitHub remains a separate provenance action |
| V3-EXT-001 | external validity | `01_external_datasets` | Identify external anchors before model scoring and prevent observational attack labels from being treated as intervention truth | LANL Unified / LANL multi-source / OpTC / CERT Insider Threat | `experiments/v3/01_external_datasets/PROTOCOL.md` | `1ee529db48fbada1f430ace34cf83d4643d8d307` | PASS | eligibility audit | LANL and OpTC retained as primary real/operational anchors; CERT retained only as synthetic socio-technical anchor | source-document audit; no performance statistics | v3 external evidence must be multi-source and must separate causal-effect recovery, external transportability and semantic portability |

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
