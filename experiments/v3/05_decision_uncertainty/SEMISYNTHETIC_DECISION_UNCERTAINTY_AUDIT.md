# V3-SS-DEC-001 independent audit

## Status

**PASS — protocol-complete.** This status means that the frozen RQ4 experiment completed with retained evidence. It does not mean that DCHAG is superior to the dense comparator.

## Authoritative execution

The first protocol-complete execution is authoritative:

- workflow run: `32869550752`
- execution PR: `#15` (`dchag-v3-semisynth-decision-run`)
- PR head: `eb46279b09b7a988e766db0f85b7f48aa8ff0c33`
- pull-request merge ref checked out by Actions: `72bcf7647ee6357f1d401a48a4276d8e23d6d2c0`
- frozen workflow base on `dchag-v3`: `b264d8ea001af3748e289a861d8dfca00c6ff0ce`
- final scored artifact: `9572481389`
- artifact ZIP SHA-256: `a11c24ec369f4d324b686fb3a8b6f28fbadd9d278e96e8d1615fc56c823ceef1`

All workflow phases passed: public-input preparation, sixteen target-outcome-free world estimations, freeze verification before private material access, and private scoring.

A later administrative duplicate was triggered as run `32880101209` through PR `#16`. It occurred after the successful first execution had already completed. It is explicitly excluded from scientific use and cannot replace, select among, or improve the run-1 result.

## Frozen design verified

The retained result reports and the workflow guardrails agree on:

- 16 independent confirmatory worlds;
- 40 trajectory-cluster bootstrap fits per world and model;
- 1,100 sampled training clusters per bootstrap replicate;
- 1,500 split-qualified target anchors per world;
- 25 paired Monte Carlo replicates per anchor/regime;
- unchanged active estimator `V3-SS-SEL-001-C1`, `max_parents=8`;
- unchanged dense sequential g-formula comparator;
- no target test outcome, private SCM, oracle, or true-edge access by estimator jobs;
- all sixteen estimation outputs frozen before private scoring;
- no hyperparameter retuning, world replacement, or post-result bootstrap replacement.

The bootstrap replicates are perturbations, not independent inferential units. The 16 worlds remain the units for the world-level confidence interval and sign-flip comparison.

## Primary result: DCHAG decision stability

DCHAG's mean world-level probability that cluster-bootstrap training perturbation changes the full-sample top control is:

`0.0015625` (0.15625%).

Only one of the sixteen worlds exhibits any top-control switch. With 10,000 world-level bootstrap samples and frozen seed `20260845`, the independently reproduced interval is:

- bootstrap mean: `0.0015662500000000002`
- 95% CI: `[0.0, 0.004687500000000001]`

Thus, within this frozen semi-synthetic benchmark, top-control selection is highly stable under the specified finite-sample perturbation.

## Dense comparator and paired result

Dense sequential g-formula has exactly the same mean world-level top-control switch rate, `0.0015625`, and also switches in one world.

The paired world-level DCHAG-minus-dense difference is exactly `0.0`:

- 10,000 world bootstrap samples, seed `20260846`;
- 95% CI `[0.0, 0.0]`;
- exhaustive 65,536-assignment sign-flip test: two-sided `p=1.0`.

There is therefore no evidence of a DCHAG advantage in the primary top-control switch endpoint. The result is equality on this realized frozen endpoint, not a general equivalence theorem.

## The only top-control switch

For both DCHAG and dense-g, the sole switch occurs in:

- world: `confirm_helpdesk_identity_1`
- bootstrap replicate: `13`
- full-sample top: `C4`
- bootstrap top: `C1`
- oracle top: `C4`
- normalized oracle regret for that replicate: `0.543388509472547`

Each model selects `C4` in 39/40 perturbations and `C1` once. This failure is retained and must not be removed or rerun away.

## Secondary decision-quality results

Across worlds and bootstrap perturbations:

| Endpoint | DCHAG | Dense sequential g-formula |
|---|---:|---:|
| Oracle top-control accuracy | 0.9984375 | 0.9984375 |
| Mean normalized oracle regret | 0.0008490445460508547 | 0.0008490445460508547 |
| Mean Kendall vs oracle | 0.8029391498294353 | 0.7901041666666668 |
| Mean Spearman vs oracle | 0.8619257117688026 | 0.85 |
| Mean top-vs-runner-up margin | 0.10165691666666668 | 0.09703316666666668 |

Lower-ranked controls are less stable than the top decision. The largest mean pairwise reversal-or-tie rates are DCHAG `C2/C3=0.1984375`, `C1/C3=0.171875`, `C1/C2=0.1359375`; dense-g `C1/C3=0.2390625`, `C2/C3=0.1953125`, `C1/C2=0.078125`. Hence the appropriate claim is strong top-control stability, not complete rank-order invariance.

## RQ1 reference consistency

All 32 world×model RQ4 full-sample top controls agree with the audited RQ1 top controls. There are zero DCHAG discrepancies and zero dense-g discrepancies. Thus the reduced RQ4 Monte Carlo integration did not change any full-sample top-control decision.

## Independent recomputation

The artifact was downloaded outside the Actions scoring job and audited locally. Checks passed:

- ZIP SHA-256 equals GitHub artifact digest;
- all six scored-result members match `RESULT_SHA256.txt`;
- `world_decision_stability.csv`: 32 rows;
- `bootstrap_decisions.csv`: 1,280 rows;
- `pairwise_rank_reversals.csv`: 192 rows;
- `rq1_reference_check.csv`: 32 rows;
- DCHAG and dense aggregate summaries recomputed exactly;
- primary 10,000-replicate bootstrap reproduced exactly with seed `20260845`;
- paired bootstrap reproduced exactly with seed `20260846`;
- exhaustive 65,536 sign-flip result reproduced exactly.

Retained member SHA-256 values:

- `SEMISYNTHETIC_DECISION_UNCERTAINTY_RESULTS.json`: `77ce02a4f6e336b2684e0bb15ffffde78063e0224be207ad0a1ba6ee903246e1`
- `bootstrap_decisions.csv`: `5562d7e30881c1486f27feb5e4ac36dd31b8814fc76f4117292b14bcdee71060`
- `model_decision_summary.csv`: `d55d2f9fb7912d03a32afc23177ec042f72572322315cf60288e9e948b63a926`
- `pairwise_rank_reversals.csv`: `df9d8ad4d2068dfa99675b72c63ae0c484c4d01db6799ba9b537b32aba8b16a0`
- `rq1_reference_check.csv`: `2387288c0fd92e06dd32ae1b042eea0a783016c9f665c572d14737b38ef3a1ac`
- `world_decision_stability.csv`: `721215ae1a3f46f4777182576d0432340d466b9bcd394b1640ee5ba499a7d8c3`

## Claim boundary

RQ4 supports the statement that the **top control is highly stable to the frozen trajectory-cluster bootstrap perturbation in these sixteen semi-synthetic worlds**. It does not establish posterior uncertainty, calibrated real-world uncertainty, real defensive-control effectiveness, arbitrary distribution-shift robustness, or causal identification in real LANL data. It also provides no primary-endpoint superiority of DCHAG over dense-g.
