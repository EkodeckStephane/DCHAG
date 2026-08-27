# DCHAG v3 experiment-ledger corrections — 2026-08-27

This file is an append-only scientific correction supplement to `EXPERIMENT_LEDGER.md`. It preserves the historical `V3-OPTC-INGEST-001` FROZEN row as the pre-execution protocol state and records the subsequent failed and corrected executions. For OpTC ingestion, the newest valid correction row below is authoritative.

## V3-OPTC-INGEST-001-C1 — FAILED

- Parent protocol: `V3-OPTC-INGEST-001`.
- GitHub Actions run: `33063142611`; job `98486625967`; execution PR `#18`.
- PR base: `617b0ae93048775531befec6b4638c91437ea67c`.
- PR head: `5a37dd87a16f8813f1c41190e90c2d403bb0ba3f`.
- Checked-out merge ref: `8789833b13820714ebc4981240a98a616a260d9b`.
- Frozen mapping/temporal tests: 7/7 PASS.
- Immutable source identity: 5,649,857 bytes; Git blob SHA-1 `25279a41030981ead9bf6134432aa6112429eb82`.
- Observed failure: 10,000/10,000 mapping failures, 0 typed observations, 0 valid timestamps.
- Root cause: the immutable OpTC `timestamp` field is ISO-8601 with timezone offset, whereas the frozen execution attempted integer conversion.
- Scientific status: **FAILED**. This execution is retained as implementation/schema-normalization evidence and is ineligible for manuscript performance claims.
- Retained failure record: `experiments/v3/01_external_datasets/OPTC_INGEST_C1_FAILURE.md`.

## V3-OPTC-INGEST-001-C2 — PASS

- Parent protocol: `V3-OPTC-INGEST-001`.
- Parent failed execution: `V3-OPTC-INGEST-001-C1`.
- Correction scope: normalize supported numeric or ISO-8601 timestamps to Unix epoch milliseconds through the shared frozen normalization path; H/P/T semantics, source identity, exclusions, and causal-claim boundary remain unchanged.
- GitHub Actions run: `33063522641`; job `98487893090`; execution PR `#19`.
- Execution base: `5617e5de06203e04552386c40059e751a59307c5`.
- Execution head: `7174ebdc399aa7737368ab8d5f38cbc93220e01f`.
- Checked-out merge ref: `91c0b6a86bff559091977fe0759572ec7f69a05f`.
- Result artifact: `9642733704`.
- Artifact ZIP SHA-256: `7eb888aa288d0a4fa7c3e2d35629cb6a6d647091a226e2dc6db5e1b4cd7def4f`.
- Result JSON SHA-256: `199d39d4d429b3c4af7e17dd9083ee2c9097ae7977128fb6dc658b0076e5c56e`.
- Immutable source: `brbickel/ecar-challenge`, commit `45b7c7c85ddce4b44f84f68af7822c5466a7077d`, path `data.json`, 5,649,857 bytes, Git blob SHA-1 `25279a41030981ead9bf6134432aa6112429eb82`.
- Records: 10,000.
- Mapping failures: 0.
- Typed observations: H=9,890; P=447; T=9,553; total typed observations=19,890.
- Record-level coverage: H=98.90%; P=4.47%; T=95.53%.
- Principal-associated records: 9,890/10,000; hostname present: 10,000/10,000; missing actor/object IDs: 0/0.
- Valid timestamps: 10,000/10,000; span=127.23 s.
- Raw source record order is not chronologically nondecreasing.
- Guardrails: source identity verified; red-team ground truth unused; control `C` not inferred; deterministic mapping invariants verified; aggregate-only retained artifact; no causal effect estimated.
- Scientific status: **PASS** means corrected protocol-complete observational ingestion. This supports semantic portability and observational ingestibility only.
- Audit: `experiments/v3/01_external_datasets/OPTC_INGEST_C2_AUDIT.md`.
- Audited summary: `experiments/v3/01_external_datasets/OPTC_INGEST_C2_AUDITED_SUMMARY.json`.

## Current OpTC claim boundary

The corrected OpTC result supports deterministic mapping of the immutable pilot into declared H/P/T observational channels and verifies timestamp normalization. It does not provide intervention truth, causal defensive-control effects, attacker intent, or real-organization causal identification. Downstream temporal use must sort or otherwise explicitly handle event time because source record order is nonchronological.
