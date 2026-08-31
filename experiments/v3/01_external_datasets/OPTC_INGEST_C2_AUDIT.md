# V3-OPTC-INGEST-001-C2 independent audit

## Scope

This audit covers the corrected OpTC pilot ingestion after the retained C1 failure. It verifies source identity, correction provenance, aggregate mapping invariants, temporal integrity, artifact hashes, and the observational claim boundary.

## Correction history

The original ingestion protocol was frozen before execution. Before a retained result existed, C1 corrected a temporal-summary defect that had sorted timestamps before testing source order. The first C1 execution (`33063142611`) then failed after immutable source acquisition because all 10,000 records failed mapping and no timestamp was recognized. That failure is retained in `OPTC_INGEST_C1_FAILURE.md`.

Inspection of the exact immutable source showed ISO-8601 timestamps with explicit timezone offsets. C2 was frozen before rerun to normalize supported numeric/ISO-8601 timestamps to epoch milliseconds through one shared parser while leaving H/P/T semantics unchanged.

## Authoritative C2 execution

- GitHub Actions run: `33063522641`
- job: `98487893090`
- execution PR: `#19`
- PR base: `5617e5de06203e04552386c40059e751a59307c5`
- PR head: `7174ebdc399aa7737368ab8d5f38cbc93220e01f`
- checked-out PR merge-ref: `91c0b6a86bff559091977fe0759572ec7f69a05f`
- merge-ref provenance confirms the exact head was merged into the exact base and its diff contains only the five-line execution trigger.
- result artifact: `9642733704`
- artifact ZIP SHA-256: `7eb888aa288d0a4fa7c3e2d35629cb6a6d647091a226e2dc6db5e1b4cd7def4f`

The downloaded artifact ZIP independently matches the GitHub digest. Every member listed in `SHA256SUMS.txt` was independently rehashed with zero mismatches. `OPTC_INGEST_RESULTS.json` has SHA-256 `199d39d4d429b3c4af7e17dd9083ee2c9097ae7977128fb6dc658b0076e5c56e`.

## Immutable source identity

The retained aggregate confirms the exact frozen source:

- `brbickel/ecar-challenge`
- commit `45b7c7c85ddce4b44f84f68af7822c5466a7077d`
- `data.json`
- 5,649,857 bytes
- Git blob SHA-1 `25279a41030981ead9bf6134432aa6112429eb82`

No red-team ground truth was used.

## Mapping completeness

The source contains 10,000 records and C2 maps all 10,000 with **zero mapping failures**.

The independently checked deterministic mapping identities are exact:

- H = records with nonempty `principal` = 9,890;
- P = `PROCESS` records = 447;
- T = all non-`PROCESS` records = 9,553;
- total typed observations = 19,890 = 10,000 base P/T observations + 9,890 overlapping H observations.

Record-level observational coverage is therefore:

- H-associated: 98.90%;
- P-associated: 4.47%;
- T-associated: 95.53%;
- hostname present: 100%;
- missing actor ID: 0;
- missing object ID: 0.

These percentages are not mutually exclusive because H is an additional user-associated view of a record that also maps to P or T.

## Temporal integrity

All 10,000 records have valid normalized timestamps.

- minimum: `1569268031308` ms (`2019-09-23T19:47:11.308Z`)
- maximum: `1569268158538` ms (`2019-09-23T19:49:18.538Z`)
- span: 127,230 ms = 127.23 s
- source record order nondecreasing: **false**

The negative source-order endpoint is important and is retained. It means the immutable sample is not presented in chronological event order. Any downstream temporal analysis must sort by normalized event time, or otherwise explicitly model source-order/event-time differences, without claiming the raw record order is chronological.

## Object composition

The largest source object class is FLOW (6,537 records), followed by FILE (2,009), MODULE (490), THREAD (484), PROCESS (447), REGISTRY (20), TASK (9), and USER_SESSION (4). These are descriptive properties of this fixed pilot sample only.

## Claim decision

**PASS** means the corrected frozen adapter completely ingests the immutable pilot sample with verified identity and exact H/P/T mapping invariants.

The manuscript-eligible statement is bounded to semantic portability and observational ingestibility: the frozen mapping can represent this OpTC pilot sample as user-associated, process-transition, and technical evidence without attack annotations or invented controls. The result does not validate causal edges, intervention effects, attacker intent, real defensive-control effectiveness, or generalize automatically from this 127.23-second pilot to the full OpTC corpus.
