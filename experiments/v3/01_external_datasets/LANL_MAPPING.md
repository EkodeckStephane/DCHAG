# V3-LANL-MAP-001 — LANL Unified Host/Network → DCHAG observational mapping

## Source contract

The mapping is based on the official LANL Unified Host and Network Data Set description. Host events are JSON-lines Windows events and network records are CSV flow summaries. De-identified identities are consistent across host and network elements.

## Mapping principles

This mapping is deliberately conservative and observational. It does not infer intent, policy compliance, attacker identity, or defensive interventions.

### H — observable user-associated security event

A host record contributes `H` evidence only when it contains a nonempty user identity (`UserName` or `SubjectUserName`) and the Windows event belongs to an authentication/session/user-interaction family. This represents an observable user-associated event, not a psychological decision or intention.

Relevant event IDs include authentication/logon/logoff/session events documented by LANL: `4768`, `4769`, `4770`, `4774`, `4776`, `4624`, `4625`, `4634`, `4647`, `4648`, `4672`, `4800`, `4801`, `4802`, `4803`.

### P — executable process transition

Windows process start/end events contribute `P` evidence:

- `4688`: process start;
- `4689`: process end.

If a process event also carries a user identity, it may generate both `H` and `P` observational evidence, but the `H` role remains only `user_associated_action`.

### T — technical security/system/network evidence

Every LANL network-flow record contributes `T` evidence. Host authentication/session events also contribute `T` evidence because they are observable technical security-state transitions. System startup/shutdown/event-service events (`4608`, `4609`, `1100`) contribute only `T` unless a separate directly observed user field justifies `H` under the rule above.

### C — defensive controls

No `C` variable is inferred from LANL observations. Red-team labels from the separate LANL multi-source dataset, when used later, are evaluation labels only and are never treated as intervention truth.

## Cross-source linkage

The adapter retains de-identified user, source/destination/log host, process ID, parent process ID, logon ID and network endpoints when present. Cross-source identity consistency may subsequently support temporal path construction, but no edge is declared causal merely because two identifiers match.

## Claim boundary

This mapping can support external observational transportability, path construction and structure-learning tests. By itself it cannot validate counterfactual defensive-control effects because the operational dataset does not provide paired do-intervention outcomes.
