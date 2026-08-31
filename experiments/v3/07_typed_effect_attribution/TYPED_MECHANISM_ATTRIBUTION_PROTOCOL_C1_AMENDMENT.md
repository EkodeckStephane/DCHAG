# V3-TMA-001-C1 — Common-random-number coalition amendment

## Status

This amendment is frozen before any typed-mechanism-attribution estimator output or private-oracle attribution result is inspected. It corrects one Monte Carlo design detail in `TYPED_MECHANISM_ATTRIBUTION_PROTOCOL.md`; all datasets, worlds, estimators, components, endpoints, thresholds, bootstrap settings, and claim boundaries remain unchanged.

## Reason for correction

The base protocol required deterministic seeds to encode the coalition. That would cause distinct exogenous Monte Carlo draws for distinct Shapley coalitions. Although the algebraic Shapley efficiency identity would still hold for the resulting finite-sample characteristic function, coalition contrasts would then mix mechanism activation differences with Monte Carlo realization differences. This is undesirable for a mechanism-attribution endpoint.

The correction is therefore methodological rather than result-driven: all coalition values for a fixed `(world, model, focal control)` must be evaluated on the same exogenous uniform tensor.

## Corrected seed rule

For every fixed `(world, model, focal control, purpose)` construct one deterministic seed in namespace `V3-TMA-001-C1`:

`seed = stable_seed("V3-TMA-001-C1|world|model|control|purpose")`.

The seed MUST NOT encode the coalition. The resulting uniform tensor is reused unchanged for:

- the matched sustained `do(control=0)` baseline;
- every one of the 32 intermediary-block coalitions under sustained `do(control=1)`;
- the full-coalition ordinary-effect replay consistency check.

Separate deterministic seeds may be used for distinct worlds, models, controls, or purposes, but never to distinguish Shapley coalitions within the same attribution calculation.

## Consequences

1. Each coalition contrast is a paired common-random-number contrast.
2. `v(S union {g}) - v(S)` isolates the change in allowed mechanism propagation under the same exogenous realization.
3. The direct component, Shapley components, and full replay effect are computed from one coherent finite-sample characteristic function.
4. The exact Shapley efficiency check and total-effect replay check remain required at tolerance `1e-10`.

## Unchanged protocol elements

Unchanged from the base protocol:

- 16 immutable `V3-SS-CONF-001` worlds;
- four controls per world;
- five intermediary blocks `{H,P,T,C,R}` plus direct component;
- exact 32-coalition enumeration;
- 1,500 split-qualified target anchors per world;
- 100 paired Monte Carlo draws per anchor;
- active corrected DCHAG estimator `V3-SS-SEL-001-C1`, cap 8;
- frozen dense sequential g-formula comparator;
- estimator/private-SCM firewall;
- primary TMAE endpoint;
- 10,000 world bootstrap with seed `20260852`;
- exhaustive 65,536 sign-flip test;
- all secondary endpoints and claim boundaries;
- prohibition on retuning, world replacement, control exclusion, or result-conditioned reruns.

This C1 amendment supersedes only the coalition-specific seed sentence in the base protocol.