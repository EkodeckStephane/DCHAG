# DCHAG threat model and assumptions

## Protected system boundary

DCHAG evaluates socio-technical attack progression inside a declared organizational workflow and its supporting information system. The model consumes observed workflow/security events, contextual configuration, and a frozen causal specification.

## Adversary capabilities

The adversary may:

- initiate or combine technical and social-engineering actions;
- influence legitimate users through messages, requests, impersonation, urgency, or compromised communication channels;
- exploit workflow transitions after a legitimate human decision;
- exploit technical vulnerabilities or acquired credentials;
- sequence benign-looking and malicious steps over time;
- adapt later actions to observable workflow outcomes.

The adversary is not assumed to control every human action; human decisions are endogenous stochastic variables governed by the declared causal mechanism.

## Defensive control surface

Controls may affect human-verification mechanisms, process authorization, technical enforcement, or combinations declared in configuration. A control effect is interpreted only within the modeled intervention semantics.

## Trusted computing boundary for the reference evaluation

The following are trusted for formal guarantees:

- correctness of the frozen graph/configuration supplied to the evaluator;
- integrity of the event/evidence stream presented to the mapper;
- control-version binding;
- deterministic replay identifiers and seed handling;
- correct implementation of the reference evaluator.

Authenticated logging, tamper evidence, and protected configuration distribution can strengthen deployment integrity but are separate mechanisms unless explicitly implemented and evaluated.

## Partial observability

Operational evidence may omit events or expose only proxies. Missingness is represented explicitly. The evaluator does not receive simulator-hidden ground truth during normal inference. Robustness experiments vary evidence coverage and mechanism misspecification.

## Confounding

Observed control assignment may depend on pre-existing risk indicators. The simulator can therefore create observational confounding. DCHAG may adjust only for variables declared observable and temporally valid. Hidden-confounding stress tests intentionally violate identification assumptions and must be reported as such.

## Human-subject boundary

The planned core evaluation uses synthetic or sanitized event traces and a ground-truth simulator. No claim about real human behavioral causality is authorized from simulator evidence alone. Any future study recruiting participants requires an appropriate ethics review/approval process before data collection.

## Non-goals

The reference work does not establish:

- universal causal validity across organizations;
- a psychological theory of susceptibility;
- perfect causal discovery from arbitrary logs;
- production-grade authenticated telemetry unless separately implemented;
- real-world intervention effectiveness without corresponding intervention evidence.

These boundaries must later be narrated positively in the manuscript as scope and validity conditions.
