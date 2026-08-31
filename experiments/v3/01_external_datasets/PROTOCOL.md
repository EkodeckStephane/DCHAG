# V3-EXT-001 — External dataset eligibility audit protocol

Status: FROZEN for discovery/audit.

## Purpose

Identify external datasets that can anchor DCHAG v3 without converting observational labels or red-team annotations into fictitious causal intervention truth.

## Eligibility dimensions

Each candidate is scored qualitatively on:

1. real operational trace vs synthetic generation;
2. identifiable/anonymized human or user events;
3. temporal ordering at useful resolution;
4. process or activity-state observability;
5. technical host/network/security-state observability;
6. malicious-event or attack ground truth;
7. cross-source identity correlation;
8. provenance/documentation quality;
9. public accessibility and explicit data-use/license information;
10. suitability for a semi-synthetic intervention layer without relabeling observational events as causal truth.

## Scientific rule

No external observational dataset will be presented as providing true counterfactual control effects unless the source contains a defensible randomized, quasi-experimental, or otherwise identified intervention design. Red-team labels establish malicious activity, not the causal effect of a defensive control.

## Decision categories

- `PRIMARY_REAL_ANCHOR`: operational trace suitable for external/semi-synthetic anchoring.
- `SECONDARY_REAL_ANCHOR`: useful real trace with a narrower layer coverage.
- `SYNTHETIC_SOCIO_TECHNICAL_ANCHOR`: useful scenario/behavior structure but not real-world external validation.
- `REJECT`: unsuitable for the planned v3 questions.

## Freeze rule

Dataset selection is based on documented properties and DCHAG coverage, not downstream model performance. Selection may be amended only with a dated rationale before scoring any DCHAG v3 external experiment on that dataset.
