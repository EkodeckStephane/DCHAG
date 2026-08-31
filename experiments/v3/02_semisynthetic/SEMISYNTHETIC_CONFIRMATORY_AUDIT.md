# V3-SS-CONF-001 — Independent confirmatory audit

## 1. Audit status

**Status: PASS (execution and provenance).** The frozen RQ1 confirmatory experiment completed without confirmatory retuning, seed/world replacement, private-SCM access by the estimators, or pre-freeze oracle scoring.

A PASS here means that the experiment was executed and audited according to its frozen protocol. It does **not** mean that DCHAG was shown to be statistically superior to the dense sequential g-formula comparator.

## 2. Frozen preconditions

- Active estimator selection: `V3-SS-SEL-001-C1`.
- Active frozen-estimator SHA-256: `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`.
- Maximum parents: 8.
- Split-local trajectory IDs are qualified by split.
- Standardization population: exactly 1,500 anchors/world = 1,100 train + 400 test.
- Intervention oracle/estimator Monte Carlo: exactly 100 paired replicates per anchor and regime.
- Confirmatory worlds: exactly 16 pre-reserved worlds, four per family, with no substitution.
- Primary independent units for inference: 16 worlds, not 64 control rows.
- Bootstrap: 10,000 world-level resamples, seed `20260822`.
- Exact paired sign-flip test: all `2^16 = 65,536` assignments.

## 3. Execution identity and retained artifacts

- Execution PR: #12, execution-only, head `34e9e34173006185116814fa2b9c8ce1aad72689`.
- GitHub Actions run: `32626617080`.
- Generation job: `97162818450`.
- Scoring job: `97163303803`.
- Workflow PR merge SHA recorded by Actions: `c125a8026d5c671505694644c2784fe991ba704f`.
- Public confirmatory artifact: `9489870327`, SHA-256 `0f1c6ebe2c46b65a649d9b3e27d8f4c3b375fa6797cae39a76b8dcd9645a9ff3`.
- Private confirmatory artifact: `9489870511`, SHA-256 `898dde43e340d2852c43eab940fe46b6dc9652d2620dcf79705c061fcad03278`.
- Final scored artifact: `9489911175`, SHA-256 `dad2d38262c01f5f499c58b1b44229a8908fc29cb7cf6d41fefb51461d3f6a24`.

The local downloads of the public, private, and final-result ZIPs independently reproduced those three GitHub artifact digests.

## 4. Public/private separation audit

The generation job created physically separate public and private artifacts. The public artifact contains the 16 public world directories with train/test/schema material and no `world.json`, `oracle_effects.json`, `true_edges.json`, or private directory. The private artifact contains the SCM/oracle material and no public-data tree.

All hashes in `PUBLIC_MANIFEST.json` and `PRIVATE_MANIFEST.json` were independently recomputed: **0 mismatches**. All 16 pre-frozen seeds matched the protocol. All 64 world×control oracle records used exactly 1,500 anchors and 100 Monte Carlo replicates.

Each of the 16 estimator jobs downloaded only the public artifact, passed the physical-privacy assertion, and froze its outputs before the scoring job obtained the private oracle.

## 5. Frozen estimator artifacts

| World | Artifact ID | Artifact SHA-256 |
|---|---:|---|
| `confirm_helpdesk_identity_1` | 9489899734 | `b11ad950180a7205b35edd8a93af085fbaab17f3d0ceb741ca3eab5c74a4420c` |
| `confirm_helpdesk_identity_2` | 9489895438 | `83c2e60a92e732d9a976614ae46d28df7ab97501e9a8cc0ebe033158dfcd2c7e` |
| `confirm_helpdesk_identity_3` | 9489905022 | `e727fd8f7aa315f1ae186fdde75b94130e047c0b5a949ac68c78087d51665094` |
| `confirm_helpdesk_identity_4` | 9489906262 | `bd590a376f6e7f89d8f2ed97e4d92384c156c719e5b203db554cb87f52cb10cf` |
| `confirm_bec_payment_1` | 9489893823 | `faa2c569b782cf4c5d17285e28e27ece5dcaa907050b3151f7129da5a1c13543` |
| `confirm_bec_payment_2` | 9489901178 | `6f5e11fc7d96690a7da575d5eff66d802a12a9f32251d2ac44924718e13dbb96` |
| `confirm_bec_payment_3` | 9489896954 | `8b91607840753812fe9626932943b24e8a472d631b731f1dadf48559d9add930` |
| `confirm_bec_payment_4` | 9489902899 | `9954e834e61f4338d3cf031f1365ef5a43cf477b00375e860f9e1fab17a105bd` |
| `confirm_exfiltration_1` | 9489900172 | `8b6271aec298ee4ef16ed9e1b9f80eef144f324221b5a648ba6dd657cd48e106` |
| `confirm_exfiltration_2` | 9489902090 | `72939c3bcc0e68b8ea1c027b73d2a5a41240ce0db889d0681c47119e8938d31e` |
| `confirm_exfiltration_3` | 9489903545 | `b526c8cae47dae350659b0feb8923a7cc283f9a2f520c25c85496ab79de1229e` |
| `confirm_exfiltration_4` | 9489903840 | `871c07647668f80621c53fcbd50bdb45b2756d62168de9671cb6bba9f84bbd29` |
| `confirm_itot_change_1` | 9489900080 | `63aeda3e38772377325e805252eaa62145c6c1f56772efa0bd5ada79ad04e0ff` |
| `confirm_itot_change_2` | 9489900756 | `e8fd09e7b19401320500df82347e7c25293f7520037dc5e585057a1475e24c8a` |
| `confirm_itot_change_3` | 9489899846 | `dd250f87d7869948dc5760b888b49c7eebaf7c08810b4c093121ffe8757bc455` |
| `confirm_itot_change_4` | 9489901352 | `a393de1750ac72c9c2e16b119b1981ddd3c536d5c37e93352d945a7b142c6558` |

## 6. Primary causal-effect result

| Model | Effect MAE | Signed bias | Kendall | Spearman | Top-control accuracy | Normalized regret |
|---|---:|---:|---:|---:|---:|---:|
| DCHAG-Learned | 0.01131125 | +0.00086917 | 0.8125 | 0.8625 | 1.000 | 0.000 |
| Dense sequential g-formula | 0.01180677 | -0.00858240 | 0.8750 | 0.9125 | 1.000 | 0.000 |
| Observational association | 0.04873060 | -0.04770148 | 0.5625 | 0.6500 | 0.875 | 0.05334 |

The observational-association comparator is explicitly noncausal and must not be interpreted as an intervention estimator.

### Paired DCHAG vs dense-g inference

The pre-specified world-level difference was

`d_w = MAE_DCHAG,w - MAE_Dense,w`.

Across the 16 independent worlds:

- mean difference = **-0.0004955208**;
- 95% world-bootstrap CI = **[-0.0025682891, 0.0017177448]**;
- exact two-sided sign-flip p = **0.6671142578**.

The numerical point estimate slightly favors DCHAG, but the confidence interval includes zero and the exact randomization test provides no evidence of a non-zero paired difference. Therefore the admissible conclusion is **competitive/statistically compatible effect fidelity**, not DCHAG superiority. Because no equivalence margin was pre-specified, the result must also not be described as a formal equivalence test.

The mean paired difference, bootstrap interval, and exhaustive 65,536-assignment sign-flip p-value were recomputed independently from `world_metrics.csv` and reproduced the scored artifact.

## 7. Family-level qualification

DCHAG has lower mean effect MAE than dense-g in BEC/payment, exfiltration, and helpdesk/identity; dense-g has lower mean effect MAE in IT/OT change. In particular:

| Family | DCHAG MAE | Dense-g MAE | Association MAE |
|---|---:|---:|---:|
| BEC/payment | 0.01020458 | 0.01085292 | 0.04702753 |
| Exfiltration | 0.01085167 | 0.01272958 | 0.02998468 |
| Helpdesk/identity | 0.01139458 | 0.01302292 | 0.05684985 |
| IT/OT change | 0.01279417 | 0.01062167 | 0.06106035 |

This heterogeneity is part of the result and must not be hidden by the global mean.

## 8. Predictive and structural endpoints

Held-out final-outcome prediction slightly favors dense-g:

- DCHAG Brier = **0.12823842**, BSS = **0.00266641**;
- dense-g Brier = **0.12718992**, BSS = **0.00886682**.

DCHAG semi-synthetic structural recovery:

- mean learned edges = **84.625**;
- precision = **0.70445**;
- recall = **0.96844**;
- F1 = **0.81533**.

These edge metrics are recovery against the known semi-synthetic SCM structure only. They are **not** evidence that causal edges were recovered in LANL or in a real organization.

## 9. Result-file integrity

The eight scientific result members listed in `RESULT_SHA256.txt` were independently re-hashed and all matched, including:

- `SEMISYNTHETIC_CONFIRMATORY_RESULTS.json`: `ef656ff8fedf8ea217f7271d1b6b6159e99f489833c8d54f5e4dcb2b6c655497`;
- `world_metrics.csv`: `aa65fcbeb4d63865990920a4922fdc7c1ca756e547e8c691cb70628ea44190a7`;
- `model_summary.csv`: `c848bfa324eb5cf948315fa23892afe994579059216d14156bda16ac89a68e90`;
- `paired_dchag_dense_inference.json`: `3cf0688e95bcbf2bb5cf59b16a833402a5f4e115b031254fc4fadbff4207f808`.

Aggregate model summaries and DCHAG edge means were independently recomputed from the retained CSVs and reproduced the final JSON.

## 10. Guardrails

Final retained guardrails are:

- `confirmatory_hyperparameter_tuning = false`;
- `confirmatory_world_replacement = false`;
- `estimator_private_SCM_access = false`;
- `estimation_outputs_frozen_before_private_scoring = true`;
- `LANL_defensive_intervention_inferred = false`;
- `attack_or_red_team_labels_read = false`;
- `hidden_confounder_present = false` for this RQ1 benchmark;
- `real_anchor_treated_as_causal_truth = false`.

## 11. Claim boundary and scientific conclusion

> Causal-effect recovery evidence applies only to the explicit real-trajectory-anchored semi-synthetic SCM benchmark, not to LANL causal effects or real control effectiveness.

`V3-SS-CONF-001` therefore supports the following conclusion: DCHAG achieves causal-effect fidelity that is competitive with the frozen dense sequential g-formula comparator on the 16 confirmatory worlds, while providing recoverable sparse/control-path structure. There is no confirmatory evidence that DCHAG is causally more accurate than dense-g. Both methods identify the best control in all 16 worlds with zero normalized regret. The noncausal association comparator is substantially less accurate. Dense-g has a small predictive Brier/BSS advantage. All of these outcomes, including the IT/OT family reversal and the lack of superiority, are retained as scientific evidence.
