# V3-SS-DEC-001 — Frozen decision-uncertainty protocol

## Status

FROZEN before any RQ4 bootstrap execution or scoring.

## Purpose

Quantify how finite-sample perturbation of the observed training trajectories changes the defensive-control ranking produced by the already frozen DCHAG estimator, and compare that decision stability with the unchanged dense sequential g-formula comparator. This is a decision-stability analysis conditional on the semi-synthetic benchmark and the frozen model classes; it is not a posterior distribution, a confidence statement about real organizations, or evidence that observational LANL data identify real control effectiveness.

## Immutable parent evidence

- Parent benchmark: audited `V3-SS-CONF-001` public/private artifacts and 16 confirmatory world identities.
- Public parent artifact: `9489870327`, SHA-256 `0f1c6ebe2c46b65a649d9b3e27d8f4c3b375fa6797cae39a76b8dcd9645a9ff3`.
- Private parent artifact: `9489870511`, SHA-256 `898dde43e340d2852c43eab940fe46b6dc9652d2620dcf79705c061fcad03278`.
- Audited RQ1 result artifact: `9489911175`, SHA-256 `dad2d38262c01f5f499c58b1b44229a8908fc29cb7cf6d41fefb51461d3f6a24`.
- Active DCHAG freeze: `V3-SS-SEL-001-C1`, SHA-256 `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`, `max_parents=8`, screening `C=.05`, local refit `C=.7`.
- Dense comparator remains exactly the RQ1 `HistGradientBoostingClassifier` configuration; no hyperparameter may be changed.

## Worlds and independent units

Exactly the same 16 RQ1 confirmatory worlds are used: four each from `helpdesk_identity`, `bec_payment`, `exfiltration`, and `itot_change`. The 16 worlds are the independent inferential units. Bootstrap replicates nested within a world are perturbation replicates and must never be treated as 640 independent observations.

## Finite-sample perturbation

For each world, generate exactly 40 cluster-bootstrap training samples. Each bootstrap draw samples 1,100 original training `trajectory_id` clusters with replacement from the 1,100 observed training trajectories. All six time rows belonging to a selected trajectory are copied together. Duplicate selected trajectories are assigned distinct new bootstrap trajectory IDs so that lag construction does not merge duplicate clusters.

No test outcomes, private SCM fields, oracle effects, true edges, or latent variables may be read by an estimator job. The target standardization population is fixed to the 1,500 split-qualified public anchor trajectories (1,100 train anchors + 400 test anchors) from the same world.

Bootstrap seed for replicate `b` in world `w` is the deterministic SHA-256-derived seed from `V3-SS-DEC-001|bootstrap|w|b`, for `b=1,...,40`. No bootstrap draw may be regenerated or replaced because of an unfavorable result.

## Effect integration within each bootstrap fit

Each bootstrap-refitted estimator computes sustained `do(Ck_0:5=0)` versus `do(Ck_0:5=1)` effects for `C1`–`C4` over all 1,500 target anchors. To keep the nested resampling analysis computationally bounded, the bootstrap perturbation layer uses exactly 25 paired common-random-number Monte Carlo replicates per anchor/regime. This MC count is frozen before execution and is used only for RQ4 ranking-stability perturbations; it does not replace the 100-replicate RQ1 point estimates.

For each world and model, a full-sample public reference ranking is recomputed once using the same RQ4 25-replicate integration namespace. The scorer must additionally compare that full-sample ranking with the already audited RQ1 point-estimate ranking to detect any material MC-induced top-control discrepancy. If the top control differs solely because of the lower RQ4 MC integration, RQ4 is not invalidated, but the discrepancy must be reported and the switch-rate endpoint interpreted relative to the RQ4 full-sample reference only.

## Primary endpoint

For DCHAG, the primary endpoint is the **world-level top-control switch rate**: within each world, the fraction of 40 bootstrap fits whose selected top control differs from that world’s RQ4 full-sample DCHAG top control. The reported overall primary statistic is the unweighted mean of the 16 world-level switch rates.

Uncertainty for the overall mean uses 10,000 bootstrap resamples of the 16 worlds, seed `20260845`. No inference treats within-world bootstrap replicates as independent worlds.

## Secondary endpoints

For both DCHAG and dense-g:

- world-level top-control switch rate and its 16-world mean;
- oracle-best-control accuracy of each bootstrap decision, revealed only after all public estimates are frozen;
- normalized oracle regret of each bootstrap decision;
- Kendall and Spearman rank correlation with the private oracle control ordering;
- Kendall rank correlation with the model’s own full-sample RQ4 ranking;
- pairwise control-order reversal rates for all six control pairs relative to the full-sample model ranking;
- distribution of estimated top-versus-runner-up effect margin;
- number and identity of distinct controls selected as top across the 40 perturbations.

A paired DCHAG-minus-dense world-level switch-rate difference is secondary. It uses 10,000 world bootstrap resamples, seed `20260846`, plus the exhaustive 65,536 sign-flip assignments across 16 world-level differences. These statistics cannot be promoted to an estimator-superiority claim unless the direction and interval support such a statement; even then the claim is limited to finite-sample decision stability in this frozen benchmark.

## Scoring firewall

Estimator jobs receive only public RQ1 world data and the active frozen estimator configuration. All 16 world artifacts, containing all 40 bootstrap fits for both models, must be hash-frozen before any scoring job downloads the private RQ1 oracle artifact. The scoring job then computes oracle correctness/regret/rank metrics. No refitting, tuning, bootstrap replacement, or world replacement is permitted after private scoring material is available.

## Guardrails

The final result must assert:

- 16 fixed worlds;
- 40 bootstrap cluster resamples per world;
- 1,100 sampled training clusters per bootstrap replicate;
- 1,500 split-qualified target anchors per effect estimate;
- 25 paired MC replicates per anchor/regime for the RQ4 perturbation layer;
- active corrected DCHAG freeze unchanged;
- dense comparator unchanged;
- no private SCM/oracle access by estimator jobs;
- no tuning, world replacement, or bootstrap replacement;
- all estimation outputs frozen before private scoring.

## Claim boundary

A low switch rate supports stability of the selected control to the specified finite-sample perturbation in this semi-synthetic benchmark. A high switch rate supports a decision-instability limitation. Neither result establishes real-world causal-effect identification, uncertainty calibration in a new organization, robustness to arbitrary distribution shift, or correctness of real defensive-control recommendations.
