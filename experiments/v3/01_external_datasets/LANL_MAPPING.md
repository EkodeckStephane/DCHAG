# V3-LANL-MAP-001 — LANL Unified Host/Network → DCHAG observational mapping

## Source contract

The mapping is based on the official LANL Unified Host and Network Data Set description. Host events are JSON-lines Windows events and network records are CSV flow summaries. De-identified identities are consistent across host and network elements.

## Mapping principles

This mapping is deliberately conservative and observational. It does not infer intent, policy compliance, attacker identity, or defensive interventions.

### H — observable de-identified person-account event

A host record contributes `H` evidence only when:

1. the selected identity (`UserName`, falling back to `SubjectUserName`) matches the released de-identified person-account namespace `User<digits>`; and
2. the Windows event belongs to an authentication/session family or a process start/end event.

This restriction is intentional. The official LANL documentation states that a `UserName` ending in `$` is a computer account and that some system-level user names not associated with people remain recognizable rather than de-identified. Therefore, a merely nonempty `UserName` is not sufficient evidence for `H`.

`H` means only an observable event associated with a de-identified person account. It is not a psychological decision, intent, awareness, policy choice, or attacker label.

Relevant authentication/session IDs documented by LANL include `4768`, `4769`, `4770`, `4774`, `4776`, `4624`, `4625`, `4634`, `4647`, `4648`, `4672`, `4800`, `4801`, `4802`, `4803`.

### P — executable process transition

Windows process start/end events contribute `P` evidence:

- `4688`: process start;
- `4689`: process end.

If a process event also carries a de-identified person account matching `User<digits>`, it may generate both `H` and `P` observational evidence. Machine accounts such as `Comp123$`, named system/service accounts such as `SYSTEM` or `Scanner`, and other non-matching names do not create `H` evidence.

### T — technical security/system/network evidence

Every LANL network-flow record contributes `T` evidence. Host authentication/session events also contribute `T` evidence because they are observable technical security-state transitions. System startup/shutdown/event-service events (`4608`, `4609`, `1100`) contribute only `T`.

For process events, `P` is emitted instead of duplicating the same raw event as a generic `T` observation. Technical context remains retained in the process observation fields.

### C — defensive controls

No `C` variable is inferred from LANL observations. Red-team or compromise labels from other LANL releases, if used later, are evaluation labels only and are never treated as intervention truth.

## Cross-source linkage

The adapter retains de-identified user, source/destination/log host, process ID, parent process ID, logon ID and network endpoints when present. The official LANL release states that anonymized identities match across host and network elements. Identifier agreement can therefore support temporal linkage, but no edge is declared causal merely because identifiers match.

## Claim boundary

This mapping can support external observational transportability, path construction and structure-learning tests. By itself it cannot validate counterfactual defensive-control effects because the operational dataset does not provide paired `do`-intervention outcomes.

## Frozen regression conditions

The adapter tests must verify at minimum:

- `User<digits>` authentication → `H + T`;
- machine-account authentication (`*$`) → `T` only;
- named system/service account authentication → `T` only;
- `User<digits>` process start/end → `H + P`;
- process start/end without a de-identified person account → `P` only;
- network flow → `T` only;
- no input path may emit `C`.
