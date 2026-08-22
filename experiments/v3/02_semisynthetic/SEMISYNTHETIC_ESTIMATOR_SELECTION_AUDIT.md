# Audit — V3-SS-SEL-001

## Scope and chronology

`V3-SS-SEL-001` selected the one DCHAG sparse sequential-estimator configuration that may enter the untouched 16-world `V3-SS-CONF-001` confirmatory experiment.

The selection protocol `SEMISYNTHETIC_ESTIMATOR_SELECTION_PROTOCOL.md` was committed at `7c393f3fae91ea1af764c786b3bbae4e3238ac80` **before any cap-specific performance was computed or inspected**. The candidate set was fixed to `max_parents ∈ {6,8,10}`. Screening `C=0.05`, local-refit `C=0.7`, feature admissibility, MI fallback, 100 paired Monte-Carlo replicates per anchor/regime, primary score and tie-breaking rule were all frozen in advance.

## Immutable input

The selector consumed only the already retained `V3-SS-DEV-001` artifact:

- Stage-A artifact id: `9462315359`;
- Stage-A ZIP SHA-256: `ca33420fe43da84d85b2785f9a845534cc22399f2ea30ed9fda416c64ecbecb5`;
- development worlds: exactly four;
- confirmatory worlds present in selector input: **0**.

The workflow firewall explicitly checked that the public and private input directories contained only `dev_helpdesk_identity`, `dev_bec_payment`, `dev_exfiltration`, and `dev_itot_change`.

## Execution identity

- GitHub Actions run: `32602279976`;
- job: `97102286205`;
- technical execution head: `c67b65ccab33ece4839ead0f2899c615f2afb71a`;
- retained selection artifact id: `9483227758`;
- selection artifact ZIP SHA-256: `333b14d5b98e8f759f6e5efe3ddc06f11141f14f811f24bbb33a6fa8de1cc0a0`.

Every workflow step passed: pinned dependency installation, five selection tests, immutable Stage-A artifact verification, development/confirmation firewall, candidate execution, output validation and artifact upload.

The selection code SHA-256 reported by the retained run is:

`6ebe0e1c440319e68a0c5df52511a6a7a952b9d07473d4a5a64070915a0a22f9`.

Pinned numerical environment:

- Python 3.11;
- NumPy 2.4.6;
- pandas 3.0.5;
- SciPy 1.17.0;
- scikit-learn 1.8.0.

## Primary selection result

The frozen primary score is the unweighted mean of the four development-world intervention-effect MAEs. Lower is better.

| max_parents | Mean world effect MAE | Mean signed bias | Mean Kendall | Mean Spearman | Top-control accuracy | Mean normalized regret |
|---:|---:|---:|---:|---:|---:|---:|
| 6 | 0.00556231 | -0.00135764 | 0.9167 | 0.9500 | 1.000 | 0.000 |
| **8** | **0.00533396** | +0.00222588 | 0.9167 | 0.9500 | 1.000 | 0.000 |
| 10 | 0.00661029 | +0.00357191 | 0.8333 | 0.9000 | 1.000 | 0.000 |

By the frozen rule, **`max_parents = 8` is selected**.

The absolute advantage over cap 6 is only about `0.00022835` MAE. This is a modest development-stage difference and must not be described as a large superiority. No significance test was used or permitted for the tuning choice.

## Secondary diagnostics and counter-evidence

Secondary metrics were explicitly barred from overriding the primary selection rule.

Cap 6 actually achieved the strongest mean development edge F1:

- cap 6: `0.88633`;
- cap 8: `0.82737`;
- cap 10: `0.79998`.

Thus the selected cap 8 does **not** dominate cap 6 structurally. Cap 8 instead has the lowest pre-registered causal-effect MAE and a slightly lower mean final-Y Brier (`0.07812`) than cap 6 (`0.07912`). This trade-off is retained as part of the audit rather than suppressed.

For cap 8, per-world effect MAE was:

- BEC/payment: `0.00416591`;
- exfiltration: `0.00186010`;
- helpdesk/identity: `0.00828611`;
- IT/OT change: `0.00702374`.

All three candidates chose the true best development control in all four worlds and had zero mean normalized regret. No node required the MI fallback for any candidate.

## Frozen estimator entering Stage B

`FROZEN_SEMISYNTHETIC_ESTIMATOR.json` records:

- `max_parents = 8`;
- L1 logistic conditional screening, `C=0.05`, `liblinear`, max_iter 500;
- local logistic refit, `C=0.7`, `lbfgs`, max_iter 500;
- selected main effects plus all pairwise selected-feature interactions;
- current-slice public-order predecessors plus full lag-1 public history;
- time-0 lag values fixed to zero;
- deterministic MI fallback as frozen, although unused in development;
- 100 paired intervention Monte-Carlo replicates per anchor;
- confirmatory tuning disabled.

The retained frozen-estimator member SHA-256 is:

`8d592bf54b5103501391c79204829dff88b1fb4831841022cfea2687d0660105`.

## Execution note

When the PR trigger was synchronized, the broad historical Stage-A workflow also launched an unnecessary development rebuild. No output from that re-execution is used in this audit, tuning decision, or any downstream input. The sole scientific Stage-A parent remains artifact `9462315359` with the SHA-256 above.

## Guardrails

The retained result asserts:

- `confirmatory_worlds_generated = 0`;
- `confirmatory_worlds_scored = 0`;
- `confirmatory_hyperparameter_tuning = false`;
- `estimator_private_SCM_access_during_fit = false`;
- private development oracle access occurred only in the development scorer;
- candidate set was not changed after inspection.

## Audit conclusion

`V3-SS-SEL-001` is **PASS** as a pre-confirmatory tuning experiment. The only estimator configuration eligible for the originally reserved Stage-B worlds is now the frozen cap-8 configuration. The development metrics themselves remain non-confirmatory and must not be promoted as RQ1 evidence. The next valid scientific action is to generate the untouched 16 confirmatory worlds and evaluate this frozen estimator alongside the pre-specified dense sequential g-formula and observational-association comparator, with prediction/effect outputs frozen before private oracle/edge scoring.
