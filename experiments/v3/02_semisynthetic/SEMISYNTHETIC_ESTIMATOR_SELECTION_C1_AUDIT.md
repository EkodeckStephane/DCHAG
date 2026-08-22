# Audit — V3-SS-SEL-001-C1

## Why a correction was required

`V3-SS-SEL-001` was completed before a post-selection implementation audit established that `trajectory_id` is split-local: train IDs are `0..1099` and test IDs are `0..399`. The original selector concatenated the two public splits and keyed anchors only by numeric ID, collapsing the protocol-required 1,500 standardization trajectories into 1,100 slots and overwriting 400 train anchor slots with test anchors.

The defect was found **before any confirmatory world was generated or scored**. The original cap-8 result is therefore preserved but invalidated for Stage-B authorization.

## Pre-registered correction

`SEMISYNTHETIC_ESTIMATOR_SELECTION_CORRECTION_C1.md` froze the correction before corrected candidate scores were computed. Only anchor assembly changed:

- train anchors reconstructed within train: 1,100;
- test anchors reconstructed within test: 400;
- the two tensors concatenated without numeric-ID deduplication;
- required standardization population: 1,500 per world.

Candidates `{6,8,10}`, L1 `C=0.05`, refit `C=0.7`, feature rules, 100 MC replicates, primary MAE rule, tie rule and the original common-random-number seed namespace were unchanged.

## Independent reconstruction check

Using the immutable Stage-A artifact `9462315359`, the corrected train+test A_* sequences produce the same A_person/A_process/A_technical prevalences as the original generator's 1,500-device build summary in all four worlds. Maximum absolute difference: **0**.

This demonstrates that the correction reconstructs the intended generator population rather than substituting a new benchmark.

## Execution identity

- GitHub Actions run: `32602846144`;
- job: `97103604127`;
- execution head: `6e6a60ed3b6cd7c1ed6255f5e75bbfce50ba6f8e`;
- artifact: `9483381372`, `dchag-v3-semisynthetic-estimator-selection-c1`;
- artifact ZIP SHA-256: `43963f4c4b3df068e11365c6e282540359c3e9198e7144de006f2a9d738e74b8`;
- corrected result member SHA-256: `aac4c50bc5d6d11426d624c466105e1a474c49606e3b3d84a5484b28277fea90`;
- corrected frozen estimator member SHA-256: `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`;
- selection code SHA-256: `6f021d0c0a70c1a4603d773aab6d4ddef28a1594c2f2b040edc893ecb777e708`.

All workflow stages passed, including the regression test that deliberately creates overlapping split-local IDs and the real-artifact assertion that every candidate×world record uses 1,500 standardization anchors.

## Corrected primary result

| max_parents | Mean world effect MAE | Mean signed bias | Mean Kendall | Mean Spearman | Top-control accuracy | Mean edge F1 |
|---:|---:|---:|---:|---:|---:|---:|
| 6 | 0.00558417 | -0.00142806 | 0.9167 | 0.9500 | 1.000 | **0.88633** |
| **8** | **0.00477806** | +0.00199028 | 0.9167 | 0.9500 | 1.000 | 0.82737 |
| 10 | 0.00622486 | +0.00320736 | 0.8333 | 0.9000 | 1.000 | 0.79998 |

The corrected frozen rule again selects **max_parents = 8**. The cap-8 advantage over cap 6 is now about `0.00080611` in mean development-world effect MAE.

The prior invalid result had also selected cap 8, but that coincidence does not rehabilitate the original run; Stage B is authorized only by the corrected C1 freeze.

Cap 6 remains better on the secondary edge-F1 diagnostic. This counter-evidence is retained. Secondary structure recovery was never permitted to override the pre-registered effect-MAE selection criterion.

## Per-world cap-8 effect MAE

- BEC/payment: approximately `0.004068`;
- exfiltration: approximately `0.001609`;
- helpdesk/identity: approximately `0.007028`;
- IT/OT change: approximately `0.006407`.

All four development worlds still identify C4 as their true and estimated top control under cap 8, yielding development top-control accuracy 1.0 and normalized regret 0. No MI fallback node occurred.

## Active Stage-B freeze

The active `FROZEN_SEMISYNTHETIC_ESTIMATOR.json` now corresponds to `V3-SS-SEL-001-C1` and records:

- status `ACTIVE`;
- `max_parents = 8`;
- screening `C=0.05`;
- local refit `C=0.7`;
- 100 intervention MC replicates per anchor;
- `standardization_anchor_units_per_world = 1500`;
- `split_local_trajectory_ids_qualified_by_split = true`;
- confirmatory tuning disabled.

The exact historical invalidated Stage-A freeze remains preserved under `history/V3-SS-SEL-001/`.

## Guardrails

- confirmatory worlds generated: **0**;
- confirmatory worlds scored: **0**;
- confirmatory tuning: **false**;
- candidate set changed after inspection: **false**;
- private SCM access during estimator fit: **false**.

## Audit conclusion

`V3-SS-SEL-001-C1` is **PASS** and supersedes `V3-SS-SEL-001` for Stage-B authorization. The selected cap remains 8, now under protocol-compliant 1,500-anchor standardization. The corrected development numbers remain tuning evidence only and are not manuscript-level RQ1 confirmation.
