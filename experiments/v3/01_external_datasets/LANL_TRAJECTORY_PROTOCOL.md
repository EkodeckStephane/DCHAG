# V3-LANL-TRAJ-001 — frozen trajectory-construction protocol

## Purpose

Construct externally anchored DCHAG observational trajectories from LANL Unified Host/Network day 02 after `V3-LANL-INGEST-001` established complete parseability and showed that the two released streams overlap only on `[118781, 172799]`.

No attack/red-team labels, intervention variables, or counterfactual outcomes are used.

## Frozen analysis interval

Use only the genuine common interval:

`[118781, 172799]` seconds inclusive.

Host observations before `118781` are excluded from this joint trajectory experiment rather than being imputed as if matching network data existed.

## Entity and temporal unit

Primary unit: `device × 300-second window`.

- Primary window width: **300 s** (5 min).
- Sensitivity widths: **60 s** and **900 s**.
- Window origin: the exact overlap start `118781`; windows are left-closed and right-open except the last naturally truncated interval.

The 300-s trajectory is the only trajectory promoted for downstream structure-learning experiments. The 60-s and 900-s constructions are sensitivity diagnostics and cannot replace the primary result after inspection.

## Host entity rule

A host event is attached to the machine on which it was logged, using `LogHost` when present and otherwise `Computer`.

Remote `Source`/`Destination` fields contained in authentication events are retained only as contextual identifiers; they do not replace the logged host as the trajectory entity.

## Network entity rule

Each flow contributes technical evidence to both endpoints with directional channels:

- source device: `net_out_flows += 1`, destination recorded as outgoing peer;
- destination device: `net_in_flows += 1`, source recorded as incoming peer.

This directional duplication is explicit and is not interpreted as two causal events.

## Per-device-window features

Host-derived:

- `H_count`, `H_present`;
- `P_count`, `P_present`;
- `T_host_count`, `T_host_present`;
- `unique_person_users`;
- `unique_process_names`;
- `logon_success_4624`;
- `logon_failure_4625`;
- `process_start_4688`;
- `process_end_4689`.

Network-derived:

- `net_out_flows`, `net_in_flows`, `T_net_present`;
- `unique_out_peers`, `unique_in_peers`.

Combined typed state:

- `T_present = T_host_present OR T_net_present`;
- `active_types = H_present + P_present + T_present`.

No `C` feature is created.

## Primary endpoints

1. number of active device-window rows at 300 s;
2. fraction of rows containing H, P and T evidence individually;
3. fraction containing all H/P/T simultaneously;
4. fraction containing at least two typed evidence classes;
5. number and fraction of devices with multi-modal host+network evidence;
6. continuity: distribution of active windows per device and longest consecutive active run;
7. path-building feasibility: number of windows with both human/process and technical evidence;
8. sensitivity of occupancy and multi-modal coverage at 60 s and 900 s.

## Retention

Retain:

- full primary 300-s trajectory as compressed CSV artifact;
- aggregate JSON for 300/60/900 s;
- source SHA-256 identities already frozen by `V3-LANL-INGEST-001`.

Do not commit raw LANL data.

## Claim boundary

This experiment can support claims about observational trajectory construction, typed-state co-occurrence, temporal continuity and multi-source operational plausibility. It cannot establish causal edges, intervention effects, causal identification, attacker intent, or defensive-control effectiveness.
