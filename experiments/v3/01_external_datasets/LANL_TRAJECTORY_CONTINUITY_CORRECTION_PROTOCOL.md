# V3-LANL-TRAJ-001-C1 — frozen continuity post-processing correction

## Reason for correction

`V3-LANL-TRAJ-001` pre-registered, as primary endpoint 6, both the distribution of active windows per device and the **longest consecutive active run**. The frozen trajectory builder reported the former but omitted the latter from its aggregate summary.

This correction does **not** alter, regenerate, filter, or re-bin the primary trajectory. It computes the missing pre-registered continuity endpoint from the retained 300-second trajectory artifact only.

## Immutable input

GitHub Actions run: `32498616088`.

Artifact: `dchag-v3-lanl-trajectory-300s` (artifact id `9453590911`).

Artifact ZIP SHA-256:

`d6cb979953d4f68bd45b464ee74105dcd4b41ed1d41c976889d7bb931028150b`

Contained file: `LANL_TRAJECTORY_300S.csv.gz`.

Contained compressed CSV SHA-256:

`6c45852d95ce583aa95e39d6560ce2ef61a8f1e84e51c01cc38292c113cd1d22`

The expected window width is 300 seconds and the expected origin remains `118781`, exactly as frozen in `V3-LANL-TRAJ-001`.

## Deterministic endpoint definition

Each retained row is one active `device × 300-second window`, identified by `(device, window_idx)`.

For each device:

1. consider its observed active `window_idx` values in ascending order;
2. a consecutive run continues only when the next active index is exactly `previous_index + 1`;
3. any gap of one or more missing window indices terminates the current run;
4. the device-level endpoint is the maximum run length observed for that device.

No inactive rows are imputed. Missing indices are interpreted only as breaks in active-window continuity.

## Frozen outputs

The correction must report:

- number of trajectory rows read;
- number of unique devices;
- minimum, median, p90, mean, and maximum device-level longest consecutive active-run length, in windows;
- the same durations in seconds/minutes where meaningful;
- counts and fractions of devices whose longest run is at least 2, 6, 12, 36, 72, and 181 windows (10 min, 30 min, 1 h, 3 h, 6 h, and complete 15 h 5 min nominal 300-s grid coverage, respectively);
- identity of the input artifact and contained file via SHA-256;
- guardrails inherited from `V3-LANL-TRAJ-001`.

Percentile convention: nearest-rank empirical p90, implemented as sorted value at index `ceil(0.90*n)-1`.

Median convention: standard midpoint median for even `n`.

## Validity checks

The post-processor must fail if:

- the CSV schema lacks `window_idx` or `device`;
- `(device, window_idx)` duplicates are encountered;
- `window_idx` decreases globally, because the one-pass deterministic algorithm relies on the frozen trajectory ordering;
- row count or unique-device count disagrees with the frozen primary summary (`2,642,689` rows; `31,243` devices);
- the compressed input SHA-256 differs from the value above.

## Claim boundary

This correction closes a reporting omission in a pre-registered observational continuity endpoint. It provides no causal identification, causal edge, intervention effect, attacker-intent, or defensive-control-effectiveness evidence.

The original `V3-LANL-TRAJ-001` result remains unchanged and must remain separately identifiable in the experiment ledger.
