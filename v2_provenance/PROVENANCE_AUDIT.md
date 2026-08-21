# Hardened v2 provenance audit

## Source snapshot

Recovered source: `DCHAG_GitHub_V2_FULL.zip`.

Snapshot SHA-256:

`d821d3f6e5a6f73efd7935f0cc2223f55e029b1730edb1fbfd8bfc2d0b7dace3`

This archive is the recovered hardened-v2 scientific package. The public `main` branch predates this hardened learned-structure validation path and must not be used as the source of the v2 learned estimator.

## Byte-identity verification

GitHub Actions run `32525658719`, job `96907007726`, verified all seven preserved source/protocol files against the recovered snapshot. The verified SHA-256 values are:

| Source path in recovered snapshot | Repository archive path | SHA-256 |
|---|---|---|
| `adversarial_validation/common.py` | `provenance/v2_hardened/adversarial_validation/common.py` | `a3310b65d59b72cc0ee5a9c09f5b4909e75a84fc37072cc5b230cc438120ce09` |
| `adversarial_validation/estimate_validation_v2.py` | `provenance/v2_hardened/adversarial_validation/estimate_validation_v2.py` | `c3eed21e3606cb71c55e4c954c9dd8bcb9462e2df0dd58845da98e56800bfba7` |
| `adversarial_validation/generate_validation_v2.py` | `v2_provenance/adversarial_validation/generate_validation_v2.py` | `d67b74b58a58c0a35c4beb5df7576129b0841858ea04b82a95d5bc0309dbc473` |
| `adversarial_validation/score_validation_v2.py` | `v2_provenance/adversarial_validation/score_validation_v2.py` | `32f2f427a430680a2957378d63c866ef74f21e62726174e04815dc84bf909037` |
| `experiments/validation_v2/FROZEN_HYPERPARAMETERS.json` | `v2_provenance/validation_v2/FROZEN_HYPERPARAMETERS.json` | `c689ad1c68a4c7691d25a98561cdc7fc852a4ec2a49fb295fe920eaa83c1d779` |
| `experiments/validation_v2/FROZEN_PROTOCOL_v2.md` | `v2_provenance/validation_v2/FROZEN_PROTOCOL_v2.md` | `f8d8e53fb5f0c901af89e8f1c880cc22568bfa6fc029b77edcd3dfd8f1ddfe9d` |
| `experiments/validation_v2/PROTOCOL_AMENDMENT_v2_1.md` | `v2_provenance/validation_v2/PROTOCOL_AMENDMENT_v2_1.md` | `681244f3a102816231bfef37018f8de4d6f88165db4cd815512bb295bc5d1918` |

The same workflow also syntax-compiled all four archived Python sources and passed.

## Protocol chronology

The apparent development-cap discrepancy is historical and is preserved rather than edited:

1. `FROZEN_PROTOCOL_v2.md` is the initial v2 protocol and states a development parent-cap choice among `{4, 6}`.
2. Development-only diagnostics exposed excessive interventional bias from the initial mutual-information screening rule.
3. `PROTOCOL_AMENDMENT_v2_1.md` explicitly states that it was frozen **after development-world scoring and before generation of any confirmatory or latent-sensitivity observations**.
4. The amendment replaces the learned selector with L1-penalized logistic conditional screening (`C=0.05`), evaluates caps `6, 8, 10`, and freezes `max_parents=10` because the corresponding development-world mean intervention-effect MAEs were approximately `0.03657`, `0.02002`, and `0.01843`.
5. The local refit is logistic with selected main effects plus all selected pairwise interactions (`C=0.7`). The dense comparator remains `HistGradientBoostingClassifier` over all temporally admissible observed history.

Therefore `{4,6}` must not be presented as the final confirmatory-v2 cap search. The final confirmatory estimator is defined by the later, pre-confirmatory v2.1 amendment plus `FROZEN_HYPERPARAMETERS.json`.

## Audit history

An earlier verification run (`32525439773`) correctly failed because the first archived copy of `generate_validation_v2.py` was not byte-identical to the recovered snapshot. That failure is retained in GitHub Actions history. The archive copy was then replaced from the recovered snapshot; run `32525658719` passed all byte-identity, semantic chronology, and syntax checks.

## Claim boundary

This audit establishes provenance and byte identity of the hardened-v2 validation machinery. It does not create new experimental evidence and does not alter the previously reported v2 scientific outcomes. It also does not promote the stale pre-hardened public `main` implementation to hardened-v2 status.
