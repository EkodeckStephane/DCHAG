# V3-OPTC-MAP-001 — Conservative eCAR → DCHAG mapping

Source schema: Five Directions / DARPA OpTC `ecar.md`.

## Mapping

| eCAR evidence | DCHAG role | Interpretation |
|---|---|---|
| event with non-empty `principal` | `H` | observable user-associated action only |
| `object == PROCESS` | `P` | process/activity transition |
| non-PROCESS object (file, flow, registry, etc.) | `T` | technical event/state evidence |
| defensive control | **not inferred** | OpTC observational telemetry does not provide a defensive-control intervention oracle |

A single source event may yield two typed observations, e.g. a process creation associated with a principal yields `H` and `P` observations at the same timestamp.

## Explicit exclusions

1. `principal` is not interpreted as a latent intention, cognitive state, susceptibility, or human decision; it only identifies a user-associated observable action.
2. Red-team ground truth is never read by the adapter and is not an input feature. It may be used only after freezing for attack/path evaluation.
3. Malware injection or malicious labels are not treated as defensive-control interventions.
4. No counterfactual control-effect truth is claimed from OpTC itself.
5. Missing or invalid negative PID/PPID values are represented as missing rather than assigned fabricated identities.
6. Events without a timestamp are rejected.

## Intended use

OpTC is an external technical/provenance anchor for DCHAG v3. The first-stage endpoints are schema coverage, temporal/path construction, learned-structure behavior, prediction, and external transportability. A separate semi-synthetic intervention protocol is required before effect-recovery MAE can be reported.

## Validation

The adapter regression cases cover:

- `PROCESS + principal → H + P`;
- technical event without principal → `T`;
- technical event with principal → `H + T`;
- invalid PID/PPID normalization;
- missing-timestamp rejection.

These cases passed in the v3 bootstrap execution before repository publication.
