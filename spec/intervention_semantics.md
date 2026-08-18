# DCHAG intervention semantics

## Atomic operation

A configured control `C` has an observational assignment equation `f_C(Pa(C),U_C)`. The intervention `do(C=c)` replaces that equation with `C:=c` and removes all incoming edges into `C` in the interventional graph. Descendant equations are evaluated with the intervened value.

## Baseline and defensive state

Each control configuration declares:

- `baseline_value`;
- one or more admissible defensive values;
- affected descendant equations through ordinary causal edges;
- optional implementation cost metadata.

The primary effect is baseline compromise risk minus defensive-state compromise risk. A positive value represents risk reduction.

## Simultaneous controls

A set intervention is valid when every control has a unique assignment and no two mechanism-replacement directives conflict. Standard parent-variable effects may coexist and are evaluated jointly.

## Conditional interventions

Evidence used for conditional interventional estimates must temporally precede the intervention or otherwise be explicitly justified as non-descendant context. Conditioning on post-treatment descendants is blocked by default because it changes the estimand and may induce bias.

## Counterfactual replay

For simulator units, paired factual/interventional replay uses the same retained exogenous realization `u`. This isolates the effect of the intervention within the declared SCM. Aggregate ground-truth effects are averages of paired unit-level effects or sufficiently precise Monte Carlo estimates from common random numbers.

## Observational estimation

The DCHAG estimator may fit structural-equation parameters from observational traces. It then computes interventional distributions by graph surgery and forward simulation/integration. Observational conditional probabilities `P(Y|C=c,E=e)` are not accepted as substitutes for `P(Y|do(C=c),E=e)`.

## Identification and reporting

Every reported causal effect must carry:

- intervention definition;
- target outcome;
- conditioning evidence/context;
- adjustment/identification assumption;
- estimator;
- uncertainty interval where estimated from finite data;
- simulator ground truth when available.
