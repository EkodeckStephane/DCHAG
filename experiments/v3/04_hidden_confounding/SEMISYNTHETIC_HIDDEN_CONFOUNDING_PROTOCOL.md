# V3-SS-HC-001 — Frozen semi-synthetic hidden-confounding sensitivity protocol

## Analysis status

This protocol is frozen before generation or scoring of any hidden-confounding variant. `V3-SS-HC-001` is a prospective sensitivity experiment distinct from RQ1 and the locked-secondary RQ2 LOFO analysis. All generated levels, worlds, failures, and negative results must be retained. No level, world, estimator configuration, or endpoint may be changed after output inspection.

## Scientific purpose

Quantify how an unobserved time-varying common cause of defensive-control deployment and downstream adverse outcome degrades causal-effect recovery. The experiment tests the identification boundary of DCHAG rather than assuming robustness to unmeasured confounding.

The analysis does not treat LANL labels or operational activity as intervention truth. Real LANL trajectories supply only the immutable anchor sequences already used by the audited RQ1 benchmark. The causal truth remains the explicit semi-synthetic SCM.

## Immutable parent benchmark

Parent worlds are the 16 audited `V3-SS-CONF-001` confirmatory worlds. Parent public artifact: `9489870327`, ZIP SHA-256 `0f1c6ebe2c46b65a649d9b3e27d8f4c3b375fa6797cae39a76b8dcd9645a9ff3`. Parent private artifact: `9489870511`, ZIP SHA-256 `898dde43e340d2852c43eab940fe46b6dc9652d2620dcf79705c061fcad03278`. Parent scored result: `9489911175`, ZIP SHA-256 `dad2d38262c01f5f499c58b1b44229a8908fc29cb7cf6d41fefb51461d3f6a24`.

All 16 world names, family assignments, base SCM specifications, six-window anchors, 1,100/400 train/test split, and split-local trajectory IDs are inherited unchanged. The hidden-confounding generator may read the parent endogenous outcomes only to recover file/schema structure; generated outcomes must be simulated anew from the base private SCM and the frozen latent process. Public estimators receive no parent or generated private SCM/oracle material.

## Frozen latent process

A binary latent variable `U_t` is generated for every trajectory and time window but is never written to public train/test files or public schema.

At `t=0`:

`P(U_0=1) = logistic(-0.70 + 0.25 A_person + 0.25 A_process + 0.25 A_technical)`.

For `t>0`:

`P(U_t=1) = logistic(-1.10 + 1.90 U_{t-1} + 0.20 A_person + 0.20 A_process + 0.20 A_technical)`.

The latent process is therefore persistent and partially anchor-associated while remaining unobserved.

For an observed node `j`, its original base-SCM linear predictor is augmented by `lambda * gamma_j * U_t`. Frozen nonzero `gamma_j` values are:

- `C1=0.55`, `C2=0.70`, `C3=0.65`, `C4=0.80`;
- `H1=0.25`, `H2=0.30`, `P1=0.25`, `P2=0.30`, `T1=0.35`, `T2=0.40`;
- `Y=1.00`.

`R` and the three real-anchor nodes receive no direct latent coefficient. Positive latent coefficients on both controls and `Y` create treatment-confounder feedback in the observed data: higher latent pressure tends to trigger more defensive controls while independently increasing adverse-outcome risk.

## Frozen severity levels

The audited RQ1 benchmark is the immutable `lambda=0` reference and is not regenerated.

Exactly two new nonzero levels are generated:

- moderate: `lambda=0.50`;
- strong: `lambda=1.00`.

No intermediate, alternative, or replacement level may be introduced after inspection of results.

## Randomness and common-random-number rules

Natural-data simulation seeds and oracle seeds are deterministic SHA-256-derived namespaces containing experiment ID, severity, world, and purpose. Within each world/severity/control oracle comparison, the same latent-`U` uniforms and observed-node uniforms are used for sustained `do(C_k=0)` and `do(C_k=1)` regimes. The latent process remains natural under intervention. This preserves paired common random numbers and isolates the sustained control intervention.

The generated public train/test trajectories remain 1,100/400 split-local units per world. Oracle standardization uses all 1,500 split-qualified anchor units and exactly 100 paired Monte Carlo replicates per anchor/regime.

## Estimators

No estimator is retuned for hidden confounding.

DCHAG uses the active corrected estimator freeze `V3-SS-SEL-001-C1`, SHA-256 `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`: L1 screening `C=0.05`, cap 8, local logistic refit `C=0.7`, same interactions and fallback rules.

The dense sequential g-formula comparator remains the exact RQ1 frozen comparator: `HistGradientBoostingClassifier(loss="log_loss", learning_rate=0.07, max_iter=80, max_leaf_nodes=15, min_samples_leaf=30, l2_regularization=1.0)`, node-specific random state `84000 + node_index`.

Both estimators are fit only to generated public observed variables. Neither estimator receives `U`, the private SCM, oracle effects, true edges, or any private scoring material.

## Physical leakage firewall

Generation produces separate public and private artifacts per severity. Public artifacts contain only observed train/test CSVs and schema/manifests; `U`, base/private world specifications, oracle effects, and true-edge files are forbidden. Estimator jobs download only the public artifact for their severity. All 32 severity×world estimator outputs must be frozen and hash-verified before private scoring artifacts are downloaded.

## Estimands and endpoints

For each world, severity, model, and control, the causal estimand remains:

`ATE_k = E[Y_5(do(Ck_0:5=0)) - Y_5(do(Ck_0:5=1))]`,

with other controls natural, anchors fixed, and latent `U` natural.

Primary RQ3 endpoint: the strong-confounding DCHAG world-level MAE penalty relative to the audited RQ1 world on the same 16 worlds,

`Penalty_w = MAE_DCHAG(lambda=1.0,w) - MAE_DCHAG(lambda=0,w)`.

The primary summary is the mean of the 16 independent world penalties, a 10,000-replicate world bootstrap 95% CI with seed `20260824`, and the exhaustive `2^16=65,536` two-sided sign-flip test. A positive penalty with bootstrap lower bound above zero supports measurable degradation; any other outcome is retained without reinterpretation.

Secondary endpoints are: moderate DCHAG penalty; dense-g moderate/strong penalties; within-level DCHAG-minus-dense effect-MAE differences; signed bias; Kendall and Spearman control-effect ranking; top-control accuracy and normalized regret; held-out final-`Y` Brier/BSS; observed-edge recovery metrics for DCHAG; and per-family summaries.

A monotonicity diagnostic reports the fraction of worlds satisfying `MAE(lambda=0) <= MAE(lambda=0.5) <= MAE(lambda=1.0)` for each model. It is descriptive and cannot override the primary endpoint.

## Claim boundary

A PASS status means the frozen sensitivity experiment completed and evidence was retained; it does not mean DCHAG is robust or superior. The experiment can support statements about sensitivity of causal-effect recovery to explicitly injected latent confounding in this semi-synthetic SCM. It cannot establish causal identification under arbitrary hidden confounding, transport hidden causal mechanisms to real organizations, infer LANL intervention effects, or reinterpret operational attack/red-team labels as causal truth.
