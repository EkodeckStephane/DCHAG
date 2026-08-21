# V3-LANL-REGSCALE-001 — audited diagnostic

## Execution identity

- GitHub Actions run: `32507337989`
- result artifact: `9455737789`
- artifact ZIP SHA-256: `9eba05f34eac84de1474fdbc7a788b31c1721383ae08a4e7f5067a8703952ce1`
- result JSON SHA-256: `3d75fb360a63f0cc303c5aa998102cac7c5db6b666288a5cadce8f6ad475e34c`

The source trajectory, device folds, disjoint observational channels and lag-1-only candidate graph are identical to V3-LANL-STRUCT-001. The parent result is not modified.

## Frozen reference scale

Recovered v2 confirmatory manifests show 1,600 training trajectories per world and horizons 4–6, producing 6,400–9,600 rows, median 6,400. This median was frozen before diagnostic execution.

## Edge-selection diagnosis

The unchanged full-data `C=0.05` condition reproduces the parent result exactly: 9 selected edges in each of five folds.

Sample-size-normalized screening (`ScaledFull`) selects `[6,5,5,6,6]` edges across the folds, mean `5.6`. Screening `6,400` deterministic transitions with the original `C=0.05` (`Matched6400`) selects `[5,5,6,4,6]`, mean `5.2`.

Thus two independently defined scale controls both remove a substantial portion of the saturation. Their recurring structural pattern is similar: `P_process[t-1]→H_login`, `P_process[t-1]→P_process`, `P_process[t-1]→T_network`, and `T_network[t-1]→T_network` are selected in all folds by both diagnostics; `H_login[t-1]→P_process`, `H_login[t-1]→T_network`, and `T_network[t-1]→H_login` disappear in all folds under both.

This supports the narrow diagnosis that the original fixed screening `C` is not sample-size portable from the v2 confirmatory scale to the millions of LANL transitions. It does not prove that the remaining edges are causal or that either diagnostic rule is the correct v3 selector.

## Predictive cost

`ScaledFull` relative Brier increases versus FixedFull are approximately `0.007%` for H_login, `2.516%` for P_process, and `0.021%` for T_network. `Matched6400` increases are approximately `0.286%`, `2.552%`, and `0.021%`, respectively.

The diagnostic therefore shows that substantial sparsity can be recovered with very little held-out predictive loss for H and T and a measurable but still modest absolute loss for P. This trade-off is descriptive; no variant is selected as a new method from these data.

## Decision for subsequent validation

`ScaledFull` may be taken forward as a **candidate** sample-size-normalized selector because its rule was defined from the recovered v2 scale and uses the entire training fold. This is a design rationale, not a performance-based winner declaration. It must be validated on unseen data under a new frozen protocol before it can become part of DCHAGv3.

## Guardrails

No attack labels, controls, interventional truth, same-window directions or causal claims are introduced. V3-LANL-STRUCT-001 remains intact as the negative sparse-selectivity result that motivated this diagnostic.
