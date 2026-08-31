# DCHAG v2 baseline provenance for v3

## Public repository state before v3

At v3 initialization, `main` points to commit:

`17144d25be146929ed1d1bf4c9c2578d8ad8f7a8`

Its README still reports the older four-workflow retained benchmark (effect MAE 0.003906), so this commit must not be mislabeled as the final adversarial-validation v2 package.

## Recovered final v2 package

The project archive contains the intended public v2 artifact:

`DCHAG_GitHub_V2_FULL.zip`

SHA-256:

`d821d3f6e5a6f73efd7935f0cc2223f55e029b1730edb1fbfd8bfc2d0b7dace3`

The recovered package contains, among other assets:

- `adversarial_validation/` generation, estimation and scoring code;
- `benchmarks/validation_v2/` public and private benchmark material;
- `experiments/validation_v2/` frozen protocol and hyperparameters;
- `results/validation_v2/` confirmatory, development and latent-confounder outputs;
- `tests/test_validation_v2.py`;
- `requirements.lock` and `RELEASE_MANIFEST.json`.

An independent execution at v3 bootstrap reports:

`33 passed`

## Scientific v2 reference values

The confirmatory v2 manuscript/package reports DCHAG-Learned effect MAE 0.02846 and dense sequential g-formula effect MAE 0.02780, with paired world-level difference 0.000665, 95% CI [-0.00668, 0.00823], exact p=0.868. It therefore supports competitive, not superior, effect fidelity.

The hidden-confounder arm reports DCHAG effect MAE 0.04929, Kendall tau 0.583, normalized regret 0.110, and Brier Skill Score 8.0%, establishing an empirical identification boundary.

These results are protected baseline evidence for v3 and may not be removed because later experiments are more favorable.

## Branch note

The branch `dchag-v2-frozen` was initially created from the public pre-synchronization commit above solely to reserve an immutable branch name. Until the recovered v2 package is synchronized there, it is not the authoritative content-equivalent freeze of the final v2 package.
