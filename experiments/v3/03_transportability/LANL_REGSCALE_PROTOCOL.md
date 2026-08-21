# V3-LANL-REGSCALE-001 — frozen regularization-scale diagnostic

Status: exploratory diagnostic, frozen after V3-LANL-STRUCT-001 and before this diagnostic is executed.

## Motivation

V3-LANL-STRUCT-001 selected all 9/9 admissible lag-1 edges in every fold. This result remains valid and is not replaced. The present experiment tests one specific explanation: whether transferring the hardened-v2 L1 screening parameter `C=0.05` from ~thousands of training rows to ~millions of LANL transitions changes its effective sparsity.

## Frozen size reference

The recovered hardened-v2 confirmatory campaign contains 16 worlds with 1,600 training trajectories each and horizons 4–6. Exact public manifest/schema reconstruction yields 6,400–9,600 training rows, median **6,400**. This value is frozen in `V2_CONFIRMATORY_SCALE_REFERENCE.json` before diagnostic execution.

## Data and folds

Use the identical immutable 300-s LANL trajectory, disjoint channels, lag-1 candidate graph and five deterministic device folds from V3-LANL-STRUCT-001. No attack labels, controls, same-window edges or causal oracle are introduced.

## Three screening conditions

For every fold and target, compare without performance tuning:

1. **FixedFull**: original hardened-v2 screening `C=0.05` on all training transitions. This must reproduce the saturation observed in V3-LANL-STRUCT-001.
2. **ScaledFull**: screening on all training transitions with `C_scaled = 0.05 × 6400 / n_train_transitions`. This is a sample-size normalization rule defined before execution, not selected from LANL results.
3. **Matched6400**: original `C=0.05` on exactly 6,400 deterministically sampled training transitions. Sampling seed is `73000 + fold` and the same sampled transition indices are used for all three targets in that fold.

After parent selection, all variants refit the frozen v2 local logistic model (`C=0.7`, selected main effects + pairwise interactions) on the **full training fold**, so this diagnostic isolates screening scale rather than reducing local-estimation data.

If L1 selects no parent, preserve the v2 mutual-information one-parent fallback. No parent-cap tuning is relevant because only three lag-1 candidates exist.

## Primary diagnostics

- number of selected edges (0–9) by fold and condition;
- edge-selection frequency across folds;
- difference in selected-edge count versus FixedFull;
- held-out-device Brier and Brier difference versus the V3-LANL-STRUCT-001 FixedFull condition.

## Interpretation

Evidence that ScaledFull and/or Matched6400 reduce saturation would support the narrow diagnosis that fixed `C` is not sample-size portable. It would **not** establish that either rule is the correct v3 selector. Any adoption of a modified regularizer requires a later separately frozen validation experiment.

If saturation persists, the sample-size explanation is weakened and the dense lag-1 dependence may instead reflect the external process itself or the coarse three-channel representation.
