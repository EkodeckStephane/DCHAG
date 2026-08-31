# Audit — V3-LANL-MULTIDAY-001

## Execution integrity

GitHub Actions run `32509278918` completed successfully. The four per-day jobs (02–05) and the confirmatory aggregation job all passed their guardrails. The confirmatory artifact is `9457141464`, ZIP SHA-256 `9bb277715d28a0401d5f310c6333da5ce51cc79cd7f41173f5cf031cc5661e70`; its member `LANL_MULTIDAY_CONFIRMATORY_SUMMARY.json` has SHA-256 `c84966d6cd175578cd704710e2f89baea74785d118e88bc0b563533ee3519e54`.

Days 03–05 were retained exactly as the three chronological days following development day 02. No hyperparameter search or channel redefinition was performed after confirmatory inspection.

## Confirmatory data volume

Across days 03–05 the frozen runner parsed:

- 188,435,020 host records;
- 622,122,932 network-flow records;
- 810,557,952 total records;
- 13,023,210 active device×300-s windows;
- 17,940,084 person-account login events;
- 30,850,842 login events excluded from H because they were machine/system/non-person accounts;
- zero malformed records.

All three confirmatory days span their full theoretical 24-hour interval and contain 288 windows.

## Primary density endpoint

The original `FixedFull` selector saturates the admissible graph on every confirmatory day: 9.0 selected edges/fold on days 03, 04 and 05.

The pre-frozen `ScaledFull` candidate selects respectively 4.4, 4.0 and 5.0 edges/fold. The mean is 4.4667 versus 9.0 for FixedFull, a density ratio of 0.4963 and an edge-count reduction of 50.37%.

Thus the primary sparsification endpoint is supported on every confirmatory day.

## Predictive endpoints

### H_person_login

Mean day-level Brier:

- FixedFull: 0.00127270;
- ScaledFull: 0.00132485;
- SelfLag: 0.00125226.

ScaledFull is 4.10% worse than FixedFull and 5.80% worse than SelfLag on the mean-day metric. It does **not** beat SelfLag on any confirmatory day. On day 05 ScaledFull and SelfLag are effectively tied but ScaledFull remains numerically worse (`0.001045231566` vs `0.001045229294`).

Therefore no predictive cross-channel benefit is supported for corrected person-associated login activity. This negative endpoint must be retained.

A further audit of the 15 confirmatory folds shows that the L1 screen selected **no H parent in 15/15 folds**. Every ScaledFull H model therefore invoked the inherited hardened-v2 mutual-information fallback, which forces one parent when L1 selects none. The resulting H parent was `P_process[t-1]` in 10 folds and `H_person_login[t-1]` in 5 folds. Thus the displayed H edge is not evidence that sparse L1 structure selection found a robust cross-channel H dependency; it is a fallback artifact by construction. This reinforces, rather than weakens, the negative H conclusion.

### P_process

Mean day-level Brier:

- FixedFull: 0.00153999;
- ScaledFull: 0.00154477;
- SelfLag: 0.00154888.

ScaledFull beats SelfLag on all three confirmatory days, with a small mean Brier advantage of about 0.266%. It is about 0.310% worse than FixedFull. Thus the sparse candidate retains a small but consistent cross-channel predictive advantage over the self-lag comparator for P, while sacrificing little relative to the saturated model.

For P, the L1-selected self edge `P_process[t-1] -> P_process[t]` occurs in all 15 folds; `T_network[t-1] -> P_process[t]` occurs in 7/15 folds. No fallback is used for P.

### T_network

Mean day-level Brier:

- FixedFull: 0.03308015;
- ScaledFull: 0.03308199;
- SelfLag: 0.03689482.

ScaledFull beats SelfLag on all three confirmatory days and reduces mean Brier by about 10.33% relative to SelfLag. Its mean degradation versus FixedFull is only about 0.00555%. This is the strongest confirmatory predictive endpoint.

For T, both `P_process[t-1] -> T_network[t]` and `T_network[t-1] -> T_network[t]` are selected in all 15 folds, with no fallback. This is the most stable nontrivial observational dependency pattern in the confirmatory analysis.

## Structural recurrence across 15 confirmatory folds

ScaledFull selects three edges in all 15 confirmatory folds:

- `P_process[t-1] -> P_process[t]`;
- `P_process[t-1] -> T_network[t]`;
- `T_network[t-1] -> T_network[t]`.

Other recurrence frequencies are:

- `P_process[t-1] -> H_person_login[t]`: 10/15, but only through H fallback;
- `T_network[t-1] -> P_process[t]`: 7/15;
- `H_person_login[t-1] -> H_person_login[t]`: 5/15, but only through H fallback.

All recorded main-effect signs for selected ScaledFull edges are positive. Sign consistency is therefore 100% conditional on selection across these 15 folds. This sign stability is descriptive only and must not be interpreted as causal direction or monotonic intervention effect.

No H-originating cross-channel edge survives the candidate selector across the confirmatory folds.

These are observational lagged dependencies only. Frequency must not be interpreted as causal-edge probability or intervention evidence.

## Scientific conclusion

Outcome: **MIXED / PARTIAL SUPPORT**.

The unseen-day validation supports the sample-size-scaled selector as a substantially sparser observational lagged-dependency mechanism that preserves useful P/T predictive structure across consecutive operational days. It does not support a general claim that the sparse DCHAG mechanism improves all typed channels: the corrected H_person_login endpoint fails against SelfLag, and its single retained parent per fold is entirely due to the mandatory fallback rule.

Accordingly, `ScaledFull` may be carried forward in v3 as a **scale-aware observational structure candidate for P/T**, not as a universally validated replacement for the hardened-v2 selector and not as a causal structure estimator. Human-channel modeling requires a separate treatment rather than forcing the P/T result onto H.
