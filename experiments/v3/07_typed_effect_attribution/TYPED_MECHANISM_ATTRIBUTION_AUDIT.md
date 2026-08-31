# V3-TMA-001-C1 independent audit

## Scope

This audit verifies the frozen typed mechanism-attribution execution after GitHub Actions completed and after all estimator outputs had been frozen before private SCM scoring. It does not alter the protocol, worlds, estimators, seeds, controls, coalition set, or endpoints.

## Provenance

- Execution PR: #20 (`dchag-v3-tma-run` -> `dchag-v3`), execution-only.
- Execution head: `9d4713c798575bf135441b22d49879210ef47faf`.
- Workflow run: `33258386552`.
- Final scored artifact: `9716909530`.
- Artifact ZIP SHA-256: `b4e57bb104072fb55209eeb6a287465d2608ec0953e008df962f610c5397bd0a`.
- Active estimator freeze: `V3-SS-SEL-001-C1`, SHA-256 `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`, cap 8.
- Immutable RQ1 public/private worlds are reused exactly; no world regeneration or replacement occurred.

## Workflow integrity

The preflight job passed the frozen-estimator verification, regression/non-regression tests, and Python compilation. All 16 world estimator jobs completed successfully using only the immutable public RQ1 artifact. Each world output was frozen and hashed before the scoring job downloaded the private SCM material. The private scoring job verified all 16 freeze manifests before accessing the oracle.

The scored result asserts and the audit confirms:

- 16 fixed worlds;
- four controls per world;
- 32 exact coalitions per control;
- 1,500 split-qualified anchors per world;
- 100 paired Monte Carlo draws per anchor;
- common random numbers reused across all coalitions for a fixed world/model/control;
- no confirmatory hyperparameter tuning;
- no world replacement or control exclusion;
- no private SCM access in estimator jobs;
- negative and null components retained.

## Artifact integrity

The downloaded ZIP digest exactly matches the GitHub artifact digest. Every member listed in `RESULT_SHA256.txt` was independently re-hashed; there were zero mismatches.

The maximum closure and replay-consistency errors are numerical only:

- estimator closure: `5.551115123125783e-17`;
- estimator replay consistency: `0.0`;
- oracle closure: `5.551115123125783e-17`;
- oracle replay consistency: `0.0`.

All are below the frozen `1e-10` tolerance.

## Primary endpoint reproduction

From `world_tmae.csv`, independently recomputed over the 16 independent worlds:

- DCHAG mean world TMAE: `0.002735284722222213`;
- dense sequential g-formula mean world TMAE: `0.0038510005787036955`;
- paired mean `DCHAG - dense`: `-0.0011157158564814827`.

DCHAG has lower TMAE in 15 of 16 worlds. The single dense-favorable world is `confirm_bec_payment_3` and is retained unchanged.

The pre-specified 10,000-replicate world bootstrap with seed `20260852` was independently reproduced:

- 95% percentile CI: `[-0.0015380566840277753, -0.0007259242766203751]`.

The exhaustive `2^16 = 65,536` sign-flip test was independently recomputed:

- exact two-sided p-value: `0.000091552734375`.

Therefore the frozen primary endpoint supports lower typed mechanism-attribution error for DCHAG than for the frozen dense comparator on this benchmark.

## Secondary endpoints

Dominant-mechanism accuracy:

- DCHAG: `59/64 = 0.921875`;
- dense: `55/64 = 0.859375`.

Component-sign agreement, evaluated under the frozen oracle-magnitude threshold, is identical:

- DCHAG: `158/159 = 0.9937106918238994`;
- dense: `158/159 = 0.9937106918238994`.

Family-level mean TMAE favors DCHAG in all four families:

- BEC/payment: `0.00264219` vs `0.00363272`;
- exfiltration: `0.00237959` vs `0.00317897`;
- helpdesk/identity: `0.00304018` vs `0.00384283`;
- IT/OT change: `0.00287918` vs `0.00474948`.

These secondary findings support the primary result but do not replace it.

## Scientific interpretation

`V3-TMA-001-C1` provides positive evidence for the distinctive typed-graph capability of DCHAG: under the explicit semi-synthetic SCM oracle, its frozen typed mechanism-replay decomposition has significantly lower attribution error than the frozen dense sequential g-formula comparator.

This result does **not** revise the RQ1 scalar-effect conclusion. RQ1 remains a competitive/statistically compatible scalar causal-effect result with no demonstrated DCHAG superiority. TMA establishes superiority only for the separately pre-specified typed mechanism-attribution endpoint.

The decomposition is model-based and must not be described as a natural indirect effect. It does not establish real LANL/OpTC causal mechanisms, real-world causal edges, or real defensive-control effectiveness.

## Audit verdict

**PASS.** The execution is protocol-complete, artifact-integrity checks pass, primary inference is independently reproducible, and the bounded typed-attribution claim is manuscript-eligible subject to the repository claim boundaries.
