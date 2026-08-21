# V3-LANL-STRUCT-001 — audited result

## Execution identity

- GitHub Actions run: `32506381773`
- runner head: `9e1ee8f82468091d87d9927f5d8b15bf63e68112`
- result artifact: `9455407225` (`dchag-v3-lanl-structure-results`)
- artifact ZIP SHA-256: `7a182523bad9e9996fefc4c1969a0abd3faee49a496cb7eb952d24ac7c219a69`
- result JSON SHA-256: `5ddd11378e95ab0ce326aad0ce85cb7d838ddaeb5ab25c19da837355083287ab`
- immutable source trajectory SHA-256: `6c45852d95ce583aa95e39d6560ce2ef61a8f1e84e51c01cc38292c113cd1d22`

All pre-data tests, source-identity checks, model execution and scientific guardrails passed.

## Frozen observational channels

The experiment uses mutually exclusive raw-event channels to avoid tautological dependencies created by the broader H/P/T evidence mapping:

- `H_login`: Windows 4624/4625 login events;
- `P_process`: Windows 4688/4689 process start/end events;
- `T_network`: network in/out flow activity.

Only lag-1 dependencies are admissible. Same-window directions are prohibited.

## Structural-selection result: saturation, not sparse transfer

There are 3 lagged candidate channels for each of 3 targets, hence 9 admissible lag-1 edges. The hardened-v2 selector selected **all 9 edges in every one of the five held-out-device folds**. It also selected all 9 in both the early (`1..90`) and late (`91..180`) temporal halves. The mutual-information fallback was never used.

Consequently:

- each edge-selection frequency is `5/5`;
- pairwise fold edge-set Jaccard is `1.0` for every pair;
- early/late edge Jaccard is `1.0`;
- signs agree on all shared edges.

These perfect stability values **must not be interpreted as evidence of successful sparse structural transportability**, because the admissible graph is saturated. The experiment therefore does not support the intended sparse-selectivity property on this large external sample under the unchanged v2 screening regularization.

## Predictive transportability result

Despite structural saturation, held-out-device prediction is consistently better than the self-lag comparator for all three channels.

| Target | DCHAG-Learned Brier | SelfLag Brier | Prevalence Brier | DCHAG − SelfLag | BSS vs prevalence |
|---|---:|---:|---:|---:|---:|
| `H_login` | 0.03710168 | 0.04070599 | 0.04233444 | -0.00360431 | 0.12360533 |
| `P_process` | 0.00819831 | 0.00841785 | 0.19843281 | -0.00021954 | 0.95868472 |
| `T_network` | 0.11733824 | 0.12672090 | 0.24525101 | -0.00938265 | 0.52155857 |

Thus the observed cross-channel lag-1 history carries predictive information beyond target self-persistence for all three channels on held-out devices. This is evidence of **predictive temporal transportability**, not causal edge validity.

## Scientific interpretation

The result is mixed:

1. **Supported:** the frozen DCHAG lagged multichannel model has external predictive utility beyond self-lag on held-out LANL devices.
2. **Not supported:** the unchanged hardened-v2 selector does not retain sparse structural selectivity on this external sample; it saturates all admissible lag-1 edges.
3. **Not established:** causal direction, intervention effects, human intention, or defensive-control effectiveness.

A plausible diagnostic explanation is sample-size dependence of the fixed L1 `C=0.05`: the original v2 development/confirmatory local fits used far fewer transition rows than the millions available in each LANL fold. This explanation is **not yet a result** and must be tested in a separately pre-registered regularization-scaling diagnostic rather than used to rewrite the current outcome.

## Guardrails

No red-team/attack labels, control variable `C`, simulator DAG, oracle effect, same-window direction, or LANL-specific hyperparameter tuning was used.
