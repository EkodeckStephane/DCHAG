# DCHAG v3 reproducibility snapshot

## Authoritative publication snapshot

Status: **PASS**

Snapshot ID: `DCHAG-V3-PUBLICATION-SNAPSHOT-001-C1`

The publication snapshot was generated from the aligned `dchag-v3` scientific source after the root README, experiment ledger, manuscript claim matrix, scientific closure audit, and typed mechanism-attribution evidence were synchronized.

### Source identity

- Source branch: `dchag-v3`
- Source commit archived by the workflow: `5b750a25c87a6c8d1fdecc93124ada14386ea18f`
- Source tree: `0dc9413289c659661a89fa2175d265c449353df0`
- Technical trigger head: `6294481b3b5bd7014b6181bb3277325dc721ed7b`
- Authoritative workflow run: `33387392159`
- Snapshot artifact ID: `9756095310`

### Artifact integrity

- GitHub artifact ZIP digest: `sha256:4a08a84473a1ac0eeb41a228bc3f4393ecd675390772b244d48471a54c3f9189`
- Deterministic source archive SHA-256: `2323344451a461a33575f330ea8bb4a6b01b1edb92284c359d01d85e6a04f73c`
- Generated `SHA256SUMS.txt` SHA-256: `3ae315522a9664d8960c781e75f6967723574fd466867c710a9d15b41682120a`
- Files hashed in the archived source, excluding the manifest itself: **363**
- Independent local verification: **363/363 PASS**
- The manifest does not contain a self-reference.

The artifact contains `DCHAG_V3_PUBLICATION_SNAPSHOT.tar.gz`, `SHA256SUMS.txt`, `ARCHIVE_SHA256.txt`, and `SNAPSHOT_METADATA.json`.

## Required evidence present

The independently unpacked snapshot contains the publication-facing root README and the normative v3 evidence controls, including:

- `experiments/v3/EXPERIMENT_LEDGER.md`
- `experiments/v3/MANUSCRIPT_CLAIM_MATRIX.md`
- `experiments/v3/SCIENTIFIC_CLOSURE_AUDIT.md`
- RQ1 confirmatory audit
- RQ2 leave-one-family-out audit
- RQ3 hidden-confounding audit
- RQ4 decision-uncertainty audit
- computational scaling audit
- OpTC C1 failure and C2 correction/audit
- typed mechanism-attribution audit.

## Retained packaging correction history

The predecessor snapshot run `33387158615` (PR #21) is retained as a failed packaging attempt. It generated the archive successfully and verified every substantive file, but its newly generated `SHA256SUMS.txt` accidentally included itself in the checksum list. Consequently, only the self-check failed. The workflow was corrected to exclude the manifest from its own enumeration; no scientific code, result, seed, estimator configuration, benchmark world, or claim was changed.

## Publication branch policy

A frozen publication-snapshot branch is created from the post-record, post-manifest `dchag-v3` state. That branch is immutable evidence metadata plus the synchronized scientific source. `main` remains intentionally unchanged until the deliberate public-release synchronization decision represented by draft PR #1.

## Claim boundary

This snapshot freezes the measured evidence; it does not expand it. In particular:

- principal scalar causal-effect fidelity is competitive/statistically compatible with dense sequential g-formula, without a superiority or formal-equivalence claim;
- the positive typed mechanism-attribution result is a distinct semi-synthetic SCM endpoint and does not overwrite the principal scalar-effect result;
- LANL and OpTC provide observational portability evidence, not intervention truth or real defensive-control effectiveness;
- negative, null, failed, corrected, and comparator-favorable results remain part of the authoritative record.
