# V3-SS-HC-001 independent audit

## Scope

This audit covers the prospective hidden-confounding sensitivity experiment executed as GitHub Actions run `32859347437`. The protocol, latent process, severity levels, estimators, primary endpoint, and inference rules were frozen before generation and scoring.

## Execution integrity

The generation job completed successfully. It reproduced the 16 immutable RQ1 parent world identities and generated exactly two nonzero latent-confounding levels: moderate (`lambda=0.50`) and strong (`lambda=1.00`). Public artifacts contain only observed train/test variables and schemas; the latent variable `U`, private SCM specifications, oracle effects, and true-edge files were not exposed to estimator jobs.

Exactly 32 severity×world estimator outputs were produced. Each estimator job downloaded only the public artifact for its severity level, used the active corrected `V3-SS-SEL-001-C1` estimator (cap 8) plus the unchanged dense sequential g-formula comparator, standardized sustained interventions over exactly 1,500 split-qualified anchors, and used 100 Monte Carlo replicates per anchor/regime. All 32 outputs were frozen before private scoring material became available. No hyperparameter retuning, world replacement, or severity replacement occurred.

## Retained artifacts

Final scored artifact: `9567800570`, SHA-256 `8ea7bbe7039f57b2e476b26b062d500925f6f52129f78c8cdabcf83c4a3cc2ea`.

Generated benchmark artifacts:

- moderate public: `9567544928`, SHA-256 `9bc9e3730b9e0f7cc77368b2105af1b3c0cf105a5cc6de78ea79fe4c5c32a46c`;
- moderate private: `9567545827`, SHA-256 `be7cdc988805ba3a4b8026a75066e72a04760b9888dc67eb0a75217bbe4d7745`;
- strong public: `9567547051`, SHA-256 `0f811402d47fda0798adc37cabd75f51a9f5359b9748e7affb48085f73935cb6`;
- strong private: `9567547906`, SHA-256 `69b5016fdc3c2cf4e8fce3f4fb3771a3630f629db15b57d436da0abd7b08d44c`.

All estimator artifacts remain retained in workflow run `32859347437`; their existence is also enforced by the final scorer's all-32 freeze gate.

## Independent reproduction

The final ZIP SHA-256 matched the GitHub artifact digest exactly. Every member covered by `RESULT_SHA256.txt` passed an independent SHA-256 check. Model-level summaries, confounding penalties relative to the audited RQ1 world metrics, the 10,000-replicate bootstrap distributions with their frozen seeds, exhaustive 65,536-assignment sign-flip tests, strong-level DCHAG-minus-dense comparison, monotonicity diagnostic, and DCHAG edge summaries were independently recomputed from the retained CSV outputs.

## Primary RQ3 result

The primary endpoint was fixed as the strong-confounding DCHAG world-level effect-MAE penalty relative to audited RQ1. Mean penalty is `+0.00660479`. The frozen 10,000-replicate bootstrap 95% interval is `[0.00415806, 0.00904929]`, and the exhaustive two-sided sign-flip test gives `p=0.00024414`.

Thus, under the explicitly frozen strong latent mechanism, DCHAG causal-effect recovery degrades measurably. This is an identification/sensitivity limitation and must not be reframed as robustness to unmeasured confounding.

## Secondary results

At moderate confounding, DCHAG effect MAE is `0.01055510` and its penalty relative to RQ1 is `-0.00075615`, with 95% bootstrap interval `[-0.00291282, 0.00142105]` and exact `p=0.51160`. Therefore moderate confounding does not provide evidence of DCHAG degradation under this mechanism.

Dense sequential g-formula has a moderate penalty of `+0.00393125`, 95% interval `[0.00069897, 0.00714914]`, exact `p=0.03827`. Under strong confounding its penalty rises to `+0.01866469`, 95% interval `[0.01562978, 0.02158199]`, exact `p=0.00003052`.

At the strong level, mean DCHAG effect MAE is `0.01791604` versus dense-g `0.03047146`. The secondary paired difference `MAE_DCHAG - MAE_dense` is `-0.01255542`, with 95% bootstrap interval `[-0.01514236, -0.00979946]` and exact `p=0.00003052`. This is evidence of better relative effect fidelity for DCHAG than dense-g **under this particular frozen latent-confounding mechanism**. It is not evidence of general hidden-confounding robustness or universal estimator superiority.

Both methods retain oracle-best-control selection in 16/16 worlds at both nonzero severity levels, with normalized regret 0. DCHAG ranking remains high but declines with severity: mean Kendall/Spearman `0.8333/0.9000` at moderate and `0.7917/0.8625` at strong. DCHAG target-SCM edge F1 declines from approximately `0.81245` at moderate to `0.79671` at strong; recall remains high (`0.97455` and `0.96744`) while precision is lower (`0.69727` and `0.67746`). These are semi-synthetic SCM recovery statistics only.

Monotonic increase from RQ1 through moderate to strong MAE occurs in 8/16 DCHAG worlds and 11/16 dense-g worlds. The monotonicity diagnostic is descriptive and does not override the primary world-level penalty analysis.

## Scientific conclusion

`V3-SS-HC-001` is PASS in the experiment-lifecycle sense: the prospective protocol completed, all predefined levels/worlds were retained, and the result was independently reproduced. The primary result demonstrates a genuine sensitivity boundary: sufficiently strong unobserved time-varying confounding degrades DCHAG effect estimation.

The simultaneous finding that dense-g degrades more is useful but secondary. The defensible interpretation is that DCHAG retains better relative effect fidelity than dense-g under the specific injected confounder structure while still suffering a significant absolute degradation from its own no-confounding baseline.

No claim is permitted that DCHAG identifies causal effects under arbitrary hidden confounding, is generally robust to latent variables, recovers real LANL causal mechanisms, or estimates real defensive-control effectiveness from observational data.
