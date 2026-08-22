# Amendment C1 to V3-SS-CONF-001 execution protocol

Freeze date: 2026-08-22.

Status: **FROZEN before any confirmatory world generation**.

## Reason

`SEMISYNTHETIC_CONFIRMATORY_EXECUTION_PROTOCOL.md` was frozen while `V3-SS-SEL-001` was believed valid. Before any confirmatory world was generated, the split-local `trajectory_id` defect documented in `SEMISYNTHETIC_ESTIMATOR_SELECTION_CORRECTION_C1.md` invalidated that selection run.

`V3-SS-SEL-001-C1` has now completed under the original frozen candidate set/rule with correct 1,500-anchor standardization and again selected cap 8.

## Replaced Stage-B precondition

The original Stage-B estimator precondition is replaced by:

- active experiment: `V3-SS-SEL-001-C1`;
- active file: `experiments/v3/02_semisynthetic/FROZEN_SEMISYNTHETIC_ESTIMATOR.json`;
- exact active file SHA-256: `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`;
- status: `ACTIVE`;
- `max_parents = 8`;
- `standardization_anchor_units_per_world = 1500`;
- `split_local_trajectory_ids_qualified_by_split = true`;
- confirmatory tuning disabled.

The historical invalidated freeze remains under `history/V3-SS-SEL-001/` and is prohibited from Stage B.

## Confirmatory implementation requirement

Any confirmatory effect-standardization code must reconstruct train and test anchor tensors separately and concatenate the tensors. It must never concatenate train/test rows and deduplicate/key them only by numeric `trajectory_id`, because those IDs are split-local.

For every confirmatory world the estimator job must assert:

- training anchor units = 1,100;
- test anchor units = 400;
- effect-standardization anchor units = 1,500.

## Unchanged protocol elements

All other provisions of `SEMISYNTHETIC_CONFIRMATORY_EXECUTION_PROTOCOL.md` remain unchanged, including:

- 16 frozen worlds and seeds;
- generator mechanisms and device allocation;
- public/private physical artifact separation;
- DCHAG/dense/association definitions;
- 100 paired MC replicates per anchor;
- output freeze before private scoring;
- world-level endpoints and 16-world independence;
- 10,000 world bootstrap samples with seed 20260822;
- exact 65,536-assignment sign-flip test;
- claim boundaries.

No confirmatory world had been generated or scored when this amendment was frozen.
