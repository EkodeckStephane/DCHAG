# V3-SS-SEL-001-C1 — frozen correction for split-local trajectory identifiers

Freeze date: 2026-08-22.

Status: **FROZEN before corrected candidate scores are computed or inspected**.

## Defect discovered

After `V3-SS-SEL-001` had completed but **before any confirmatory world was generated or scored**, an audit of the retained public Stage-A files found that `trajectory_id` is local to each split:

- training trajectories are numbered `0..1099`;
- held-out test trajectories are numbered `0..399`.

The original Stage-A selection implementation concatenated train and test rows and indexed anchors only by numeric `trajectory_id`. Therefore the 400 test IDs collided with train IDs `0..399`. The implementation produced 1,100 numeric anchor slots instead of the protocol-required 1,500 distinct train+test anchor trajectories, and test rows overwrote the corresponding train anchor slots.

This violates the frozen `V3-SS-SEL-001` rule that intervention standardization use fixed real-anchor sequences from **all 1,500 development-world devices**.

## Scientific consequence

`V3-SS-SEL-001` is **INVALIDATED for estimator selection**. Its cap-8 choice cannot authorize Stage B. The original run, artifact and metrics remain preserved as historical evidence of the defect; they must not be silently replaced or used as confirmatory preconditions.

No `V3-SS-CONF-001` world has been generated or scored. The confirmatory firewall is therefore still intact and a corrected development-only rerun is scientifically permissible.

## Correction scope

The correction changes **only anchor assembly across public train/test splits**:

1. reconstruct the 1,100 training anchor trajectories within the training split;
2. reconstruct the 400 test anchor trajectories within the test split;
3. concatenate those two anchor tensors by array position, not by the split-local numeric `trajectory_id` key;
4. assert exactly 1,500 anchor units per world before effect estimation.

No public generated H/P/T/R/C/Y value from the held-out split is used for fitting or intervention standardization. Only the three exogenous A_* anchor sequences are read from held-out rows, exactly as the original protocol allowed.

## Frozen elements that do not change

The corrected rerun uses exactly the original pre-registered selection design:

- candidates `{6,8,10}`;
- L1 logistic screening `C=0.05`, `liblinear`, max_iter 500;
- local logistic refit `C=0.7`, `lbfgs`, max_iter 500;
- selected main effects plus all pairwise selected interactions;
- same temporally admissible feature set;
- deterministic MI fallback rule;
- exactly 100 paired Monte-Carlo replicates per anchor/regime;
- primary score = unweighted mean of four development-world effect MAEs;
- tie within `1e-12` -> smaller cap;
- secondary metrics cannot override the primary rule;
- same four development worlds and immutable Stage-A artifact `9462315359`;
- no confirmatory data access.

To isolate the correction from Monte-Carlo variation, the corrected run deliberately retains the same deterministic common-random-number seed namespace used by `V3-SS-SEL-001`; only the anchor tensor is corrected.

## Required regression test

A new test must construct train and test data with overlapping numeric `trajectory_id` values and prove that corrected anchor assembly returns the sum of split units rather than the union of numeric IDs.

For the real Stage-A artifact, every corrected world must assert:

- train anchor units = 1,100;
- test anchor units = 400;
- standardization anchor units = 1,500.

## Stage-B block

`SEMISYNTHETIC_CONFIRMATORY_EXECUTION_PROTOCOL.md` is **blocked** until this correction completes and a new active frozen estimator configuration from `V3-SS-SEL-001-C1` is persisted. The earlier cap-8 file is not an eligible Stage-B configuration.

## Claim boundary

This is an implementation/protocol-compliance correction, not a new opportunity to tune the candidates or selection rule. Any corrected result, including a different selected cap, must be accepted as obtained and retained before confirmatory generation.
