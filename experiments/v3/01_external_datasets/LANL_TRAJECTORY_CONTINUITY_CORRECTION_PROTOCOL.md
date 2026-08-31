# V3-LANL-TRAJ-001-C1 — post-hoc reproducibility specification

## Chronology and status

This file is **not a preregistration and must not be cited as a protocol frozen before result inspection**. The original `V3-LANL-TRAJ-001` protocol had already pre-registered longest-consecutive-active-window continuity as part of endpoint 6, and the retained correction result `LANL_TRAJECTORY_CONTINUITY_CORRECTION.json` already existed on `dchag-v3` before this specification was added.

This later document only makes the deterministic post-processing algorithm and independent verification checks explicit. Git history preserves that chronology.

## Reason for the original correction

`V3-LANL-TRAJ-001` pre-registered both the distribution of active windows per device and the **longest consecutive active run**. The original aggregate trajectory script reported the former but omitted the latter. `V3-LANL-TRAJ-001-C1` recovered that omitted endpoint from the immutable retained 300-second trajectory without altering, regenerating, filtering, or re-binning the parent trajectory.

## Immutable input used for independent verification

- GitHub Actions run: `32498616088`.
- Artifact: `dchag-v3-lanl-trajectory-300s` (artifact id `9453590911`).
- Artifact ZIP SHA-256: `d6cb979953d4f68bd45b464ee74105dcd4b41ed1d41c976889d7bb931028150b`.
- Contained file: `LANL_TRAJECTORY_300S.csv.gz`.
- Contained compressed CSV SHA-256: `6c45852d95ce583aa95e39d6560ce2ef61a8f1e84e51c01cc38292c113cd1d22`.
- Expected primary width: 300 s.
- Frozen overlap origin: `118781`.

## Deterministic endpoint definition

Each retained row is one active `device × 300-second window`, identified by `(device, window_idx)`.

For each device:

1. sort/consume its active `window_idx` values in ascending order;
2. a run continues only when the next active index is exactly `previous_index + 1`;
3. any missing index terminates the current run;
4. the device-level endpoint is the maximum run length observed for that device.

No inactive rows are imputed. Missing indices are interpreted only as breaks in active-window continuity.

The retained correction reports median `7`, p90 `181`, maximum `181`, `4,274` devices active in all 181 retained grid indices, and `9,512` devices with a longest run of at least 90 windows. Independent recomputation from the immutable artifact reproduced these values exactly.

## Additional verification diagnostics

For reproducibility auditing only, later independent checks also evaluated thresholds of 2, 6, 12, 36, 72 and 181 consecutive windows. These thresholds were **not pre-registered outputs of C1** and must not be presented as such.

The final 300-second grid cell is naturally truncated by the frozen overlap interval. Therefore 181 consecutive active windows means activity in every retained grid index (`0..180`), not 905 minutes of observed source coverage.

## Verification failure conditions

An independent post-processor should fail if:

- the CSV schema lacks `window_idx` or `device`;
- duplicate `(device, window_idx)` rows are encountered;
- `window_idx` decreases globally when using the retained file ordering;
- row count or unique-device count disagrees with the parent summary (`2,642,689` rows; `31,243` devices);
- the compressed input SHA-256 differs from the value above.

## Claim boundary

The correction closes a reporting omission in a pre-registered observational continuity endpoint. It provides no causal identification, causal edge, intervention effect, attacker-intent, or defensive-control-effectiveness evidence. The original `V3-LANL-TRAJ-001` result remains unchanged and separately identifiable in the experiment ledger.
