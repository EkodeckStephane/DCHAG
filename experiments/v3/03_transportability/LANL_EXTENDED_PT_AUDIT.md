# V3-LANL-PT-EXT-001 — extended P/T validation audit

## Execution identity

The frozen experiment `V3-LANL-PT-EXT-001` was executed by GitHub Actions run `32514587724` at head commit `f455baef10f6b0c298dc252117aa34a63614d9f3`. All five day jobs (LANL days 06–10) and the confirmatory aggregation job completed successfully. The technical execution PR is not part of the scientific branch history and must remain unmerged.

The confirmatory artifact is `9459249907` (`dchag-v3-lanl-extended-pt-confirmatory`), ZIP SHA-256 `359666281273e3d2771b5dbb47955e920eff0b056c93080bc06af8558bd2afb2`. Its retained member `LANL_EXTENDED_PT_CONFIRMATORY_SUMMARY.json` has SHA-256 `f3f90c07731dd894d5121e78580833744ad0570a6f73d7d5a0c81399e6e44051`.

Per-day artifact ZIP identities are:

- day 06: artifact `9458855852`, SHA-256 `cd7734eae1cbc3c94b95c6a774e407d1fd0923615f13f9bb491a849fe5ef1653`;
- day 07: artifact `9458799178`, SHA-256 `ef6120b1954ec63813a30041d8348eb048d79b947362f54987e0f32dfd29e769`;
- day 08: artifact `9459041307`, SHA-256 `e31fbeb8cae92243d02ece6856d9fb9115dbe1c19e4a73ac271e6783fa1f795c`;
- day 09: artifact `9458939093`, SHA-256 `06d66631393328c972b1c64030f6732350078e03566bb86b9ed55e9f1e8b7480`;
- day 10: artifact `9459242614`, SHA-256 `2ab13214d72ff8ad33d8e2c4e96629654f5df012944b8c4269b94b6f2da32ace`.

The five member JSON files were independently re-aggregated outside the workflow. Day ordering, edge counts, edge/sign frequencies, fallback counts, Brier comparisons, density statistics and all four frozen criteria exactly reproduce the retained confirmatory summary.

## Frozen primary criteria

All four pre-registered criteria pass without changing thresholds or excluding a day:

1. **C1 — sparsity:** `ScaledFull` selects fewer edges than `FixedFull` on 5/5 days. `FixedFull` remains saturated at 9.0 edges/fold; `ScaledFull` is 4.0, 4.0, 5.0, 5.0 and 5.0 edges/fold on days 06–10, mean 4.6. The density ratio is `0.511111...`, a 48.89% reduction.
2. **C2 — P predictive transfer:** `P_process` has lower Brier than `SelfLag` on 5/5 days.
3. **C3 — T predictive transfer:** `T_network` has lower Brier than `SelfLag` on 5/5 days.
4. **C4 — P/T recurrence:** `P[t-1]→P[t]`, `P[t-1]→T[t]` and `T[t-1]→T[t]` each occur in 25/25 folds, exceeding the frozen 20/25 threshold. Their fitted signs are positive in every fold in which they are selected.

## Predictive magnitude, not only direction

The confirmatory PASS must not be presented as uniform practical improvement across channels.

For `T_network`, the relative Brier improvement over `SelfLag` is 9.82–10.66% across the five unseen days, with mean approximately **10.26%**. This is the strongest external predictive result.

For `P_process`, the direction is consistent on all five days, but the mean relative improvement is only approximately **0.336%**. On days 06 and 07 the absolute differences are approximately `7.67e-10` and `8.01e-10`, respectively. Therefore the defensible claim is that sparse cross-channel modelling preserves/slightly improves P prediction across unseen days, not that it yields a large P performance gain.

`H_person_login` is deliberately secondary. It beats `SelfLag` on only 2/5 days; its mean relative change is negative (approximately −5.03%). Moreover, the inherited mutual-information fallback is invoked for H in **25/25 folds**. H-related selected edges therefore must not be promoted as robust sparse-structure transportability evidence.

## Data scale and integrity

Across days 06–10 the audit covers `298,351,913` parsed host records and `1,033,576,592` parsed network records, with zero malformed records in every day job. The construction records `27,694,727` person-login events and excludes `49,691,852` non-person login events from H semantics. The five day results contain `21,018,973` active device-window rows. Each day covers exactly 288 five-minute windows.

## Structural interpretation

The three core P/T lagged dependencies recur in all 25 device-held-out folds with positive fitted signs. Two additional cross-channel patterns, `P[t-1]→H[t]` and `T[t-1]→P[t]`, recur in 15/25 folds, while `H[t-1]→H[t]` appears in 10/25 folds. Because H uses fallback in all folds, H-related recurrence is descriptive only.

Even the three 25/25 core P/T edges are **observational lagged dependencies**, not causal edges. Stability, sign recurrence and predictive improvement do not establish intervention semantics or causal direction.

## Guardrails and manuscript eligibility

No red-team/attack labels, simulator truth, defensive intervention `C`, counterfactual outcomes, same-window directions, per-day tuning, post-hoc day selection or H repair were used. All confirmatory days 06–10 were retained.

The experiment is manuscript-eligible as evidence for **extended temporal observational transportability** of the scale-aware sparse P/T mechanism, subject to the magnitude qualification above. It is not evidence for causal identification, attacker intent, defensive-control effectiveness or counterfactual risk reduction.
