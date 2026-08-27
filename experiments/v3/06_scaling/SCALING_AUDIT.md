# V3-SCALE-001 independent audit

## Scope

This audit covers the first execution of the frozen computational and graph-size scaling benchmark. It verifies provenance, artifact integrity, exact configuration retention, independent aggregation, and the claim boundary. It does not reinterpret the benchmark as a causal-effect experiment.

## Execution provenance

- GitHub Actions run: `33062315720`
- job: `98483835505`
- execution PR: `#17`
- PR base: `dchag-v3` at `37251e5ca998fb0f53a2d5eb7daa218d1658e05a`
- PR head: `d028333ed420c5c45650e95330163e1c8e578ef5`
- checked-out PR merge-ref recorded by the workflow: `95e16af0eceaecf93fd3fa044f4b926ae1a001d4`
- the merge-ref commit message identifies it as the merge of the exact head into the exact base; its diff contains only the five-line V3-SCALE-001 trigger.
- result artifact: `9642303712`
- artifact ZIP SHA-256: `70d9646690f4f04d58cbd364c1f533ee849b971bdde394091e0c0633d1c93a6c`

The artifact ZIP digest independently matches the GitHub artifact digest. Every entry listed in the artifact `SHA256SUMS.txt` was independently rehashed with zero mismatches.

## Environment

The retained runner metadata reports:

- Ubuntu 24.04 GitHub-hosted runner
- AMD EPYC 7763 64-Core Processor
- 4 logical CPUs visible to the job
- Python 3.11.16
- frozen Python package inventory retained in `SOFTWARE_FREEZE.txt`

These measurements are therefore runner-specific and cannot be promoted as hardware-independent complexity results.

## Frozen configuration completeness

The raw artifact contains exactly 36 rows:

- 6 unique frozen configurations;
- 3 deterministic replicates per configuration;
- 2 estimators per replicate;
- no missing or replaced configuration;
- no missing or replaced replicate.

The graph-size axis uses 600 trajectories with 12, 24, 36, and 48 endogenous nodes. The sample-size axis uses 24 endogenous nodes with 300, 600, and 1200 trajectories. The shared 24-node/600-trajectory point is represented once in the unique configuration set.

All DCHAG rows respect `max_parents <= 8`; the observed maximum is exactly 8. No MI fallback occurred in any DCHAG fit. The raw guardrails report no private-oracle access, no hyperparameter tuning, and no configuration replacement.

## Independent numerical reproduction

The configuration medians were independently recomputed from `SCALING_RAW_RESULTS.csv`. The maximum absolute discrepancy from `SCALING_CONFIGURATION_MEDIANS.csv` is exactly 0 over all scored median columns.

The log-log slopes were independently recomputed from the retained medians:

- graph-size axis: DCHAG `1.545736171847489`, dense-g `1.405314964300599`;
- sample-size axis: DCHAG `0.596796627792985`, dense-g `0.300888757078680`.

The scorer's slope differences are therefore reproduced:

- graph-size DCHAG minus dense-g: `+0.140421207546889`;
- sample-size DCHAG minus dense-g: `+0.295907870714305`.

The largest-configuration ratios were independently reproduced:

- 48 endogenous nodes / 600 trajectories: dense-g median fit time is `4.320648842x` DCHAG; incremental peak-memory ratio dense/DCHAG is `1.070592606x`;
- 24 endogenous nodes / 1200 trajectories: dense-g median fit time is `3.652818958x` DCHAG; incremental peak-memory ratio dense/DCHAG is `0.722576785x`.

Runtime variation across the three replicates is low on this runner: fit-time coefficients of variation are approximately 0.3%–3.0% across the frozen model/configuration cells.

## Observed computational profile

On the graph-size axis, median fit time increases as follows:

| Endogenous nodes | DCHAG (s) | dense-g (s) | dense/DCHAG |
|---:|---:|---:|---:|
| 12 | 0.233647 | 1.204943 | 5.157x |
| 24 | 0.665590 | 3.025680 | 4.546x |
| 36 | 1.297234 | 5.486547 | 4.229x |
| 48 | 1.966915 | 8.498348 | 4.321x |

Thus DCHAG is faster at every frozen graph-size point. However, its fitted log-log slope is steeper than dense-g's over these four points. The benchmark therefore supports an absolute runtime advantage on this range, but it does **not** support a claim that DCHAG has a better empirical scaling exponent.

On the sample-size axis, dense/DCHAG median fit-time ratios are `5.505x`, `4.546x`, and `3.653x` at 300, 600, and 1200 trajectories respectively. The absolute DCHAG runtime advantage remains present, while the ratio narrows as sample size grows.

## Memory

Memory does not show a consistent DCHAG advantage. At the largest graph point, incremental peak RSS is 21.027 MiB for DCHAG and 22.512 MiB for dense-g. At the largest sample point, it is 19.586 MiB for DCHAG and 14.152 MiB for dense-g. The manuscript must therefore avoid a general memory-efficiency superiority claim.

## Structural representation

DCHAG's median selected-edge density relative to admissible feature specifications decreases monotonically with graph size:

- 12 endogenous nodes: 67 / 282 = 0.23759;
- 24: 164 / 996 = 0.16466;
- 36: 271 / 2142 = 0.12652;
- 48: 372 / 3720 = 0.10000.

This is consistent with the frozen parent cap producing a progressively sparser relative representation as the admissible feature space grows. It is a representation-size observation, not evidence of causal-edge correctness in larger graphs.

## Claim decision

**PASS** means the frozen benchmark executed completely and reproducibly. The result supports the following bounded statement:

> On the frozen synthetic scaling benchmark and this GitHub-hosted runner, DCHAG fitted substantially faster than the frozen dense-g comparator across all tested graph and sample sizes, while its empirical log-log runtime slope was steeper and its memory use showed no consistent advantage. Its relative selected-edge density decreased as graph size increased under the fixed parent cap.

The result does not support asymptotic-complexity, production-latency, universal scalability, memory-superiority, causal-validity, or universal estimator-superiority claims.
