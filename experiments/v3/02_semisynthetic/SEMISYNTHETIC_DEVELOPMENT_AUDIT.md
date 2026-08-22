# Audit — V3-SS-DEV-001

## Scope

This audit covers only the four Stage-A development worlds created under `SEMISYNTHETIC_ORACLE_PROTOCOL.md`. It does not evaluate estimator quality and does not open, generate, score, or inspect any of the sixteen reserved confirmatory worlds.

## Immutable execution identity

- GitHub Actions run: `32526360956`
- job: `96909122486`
- execution head: `a816f5567dcfa24396d9ca2edde380ccadc2f7f7`
- retained artifact: `9462315359` (`dchag-v3-semisynthetic-development`)
- artifact ZIP SHA-256: `ca33420fe43da84d85b2785f9a845534cc22399f2ea30ed9fda416c64ecbecb5`
- frozen protocol commit: `22aca632ff51f4bb2bfa3912aae079903fb76a15`
- builder commit: `4042d61fd66f130197ceed22fb0903640c95e63c`
- test commit: `23d6d8f88eb8ca7eea07532257701c343ef45d57`
- workflow commit: `304eb8c26a56ac01df091f7c1e4e781a50cfb3c0`

The execution PR was technical only and is closed without merge.

## Parent real anchor

The benchmark uses only the immutable 300-s LANL trajectory retained from `V3-LANL-TRAJ-001`:

- artifact `9453590911`;
- artifact ZIP SHA-256 `d6cb979953d4f68bd45b464ee74105dcd4b41ed1d41c976889d7bb931028150b`;
- member `LANL_TRAJECTORY_300S.csv.gz`;
- member SHA-256 `6c45852d95ce583aa95e39d6560ce2ef61a8f1e84e51c01cc38292c113cd1d22`;
- 31,243 unique source devices.

No LANL attack/red-team label or defensive intervention label was used.

## Allocation and leakage audit

The Stage-A artifact contains exactly four development worlds, one per workflow family. Every world contains 1,500 disjoint devices, split deterministically into 1,100 training and 400 held-out test units. With horizon 6, this gives 6,600 train rows and 2,400 test rows per world.

Independent artifact inspection checked all four freeze manifests and all 24 referenced frozen files. Hash mismatches: **0**. Builder regression tests: **5/5 passed**.

Crucially:

- confirmatory worlds generated: **0**;
- confirmatory worlds scored: **0**;
- confirmatory hyperparameter tuning: **false**;
- confirmatory world replacement: **false**.

The development/confirmation firewall therefore remained intact through Stage A.

## Development diagnostics

These values establish benchmark usability only; they are not RQ1 confirmatory results.

- train `Y` prevalence: 0.09197–0.20348;
- test `Y` prevalence: 0.09000–0.19625;
- natural-policy train control prevalence: 0.28833–0.57788;
- retained development oracle effects across 16 world-control pairs: 0.02344–0.25320;
- mean oracle effect across those 16 development pairs: 0.08958;
- oracle Monte-Carlo SE range: 0.000894–0.003705.

Mean development oracle effect by control was C1=0.07687, C2=0.03386, C3=0.05893 and C4=0.18865. These control magnitudes must not be used as evidence of real LANL control effectiveness; they are properties of the explicit semi-synthetic SCM.

## Guardrails

The retained Stage-A record asserts:

- `attack_or_red_team_labels_read = false`;
- `LANL_defensive_intervention_inferred = false`;
- `real_anchor_treated_as_causal_truth = false`;
- `hidden_confounder_present = false` for this RQ1 benchmark;
- `estimator_private_SCM_access = false`;
- `confirmatory_hyperparameter_tuning = false`;
- `confirmatory_world_replacement = false`.

## Audit conclusion

`V3-SS-DEV-001` is **PASS** as a development benchmark construction and integrity experiment. It establishes a traceable real-trajectory-anchored semi-synthetic environment suitable for estimator development. It does **not** provide manuscript-level evidence for causal-effect recovery. Such evidence remains reserved for the untouched sixteen-world `V3-SS-CONF-001` stage after the estimator configuration has been frozen.
