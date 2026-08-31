# V3-TMA-001 — Typed mechanism attribution protocol

## Scientific purpose

This experiment tests whether the typed causal structure in DCHAG supports a scientifically useful capability beyond scalar control-effect estimation: decomposition of each sustained defensive-control effect into auditable contributions carried through human, process, technical, secondary-control, and context mechanisms, plus a direct component into the outcome mechanism.

The experiment is an extension motivated by scientific positioning. It is frozen before any typed-attribution result is inspected. It does not alter, replace, retune, or selectively reinterpret RQ1–RQ4 or V3-SCALE-001.

## Immutable evidence base

Use exactly the 16 audited confirmatory worlds from `V3-SS-CONF-001` and their already retained public/private artifacts:

- public benchmark artifact: `9489870327`, ZIP SHA-256 `0f1c6ebe2c46b65a649d9b3e27d8f4c3b375fa6797cae39a76b8dcd9645a9ff3`;
- private SCM/oracle artifact: `9489870511`, ZIP SHA-256 `898dde43e340d2852c43eab940fe46b6dc9652d2620dcf79705c061fcad03278`;
- audited RQ1 scored artifact: `9489911175`, ZIP SHA-256 `dad2d38262c01f5f499c58b1b44229a8908fc29cb7cf6d41fefb51461d3f6a24`.

Worlds, seeds, train/test partitions, anchors, structural equations, controls, and oracle truth must not be regenerated or replaced.

## Frozen estimators

### DCHAG

Use the active corrected estimator `V3-SS-SEL-001-C1` exactly as frozen:

- freeze SHA-256 `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`;
- `max_parents=8`;
- L1 screening `C=0.05`;
- local logistic refit `C=0.7` with retained pairwise interactions;
- 1,500 split-qualified standardization anchors per world;
- no confirmatory tuning.

### Dense comparator

Use the same dense sequential g-formula implementation and hyperparameters as `V3-SS-CONF-001`.

The dense comparator is included because typed mechanism attribution should be evaluated against an adversarially strong full-history causal estimator, not only against DCHAG's own oracle.

## Typed mechanism blocks

For every fitted model and every private oracle SCM, endogenous mechanisms are partitioned into five intermediary blocks:

1. `H` — human decision/event nodes;
2. `P` — process/workflow nodes;
3. `T` — technical state nodes excluding the final target `Y`;
4. `C` — natural response mechanisms of controls other than the focal intervened control;
5. `R` — context/risk-state mechanism.

Real anchor nodes remain fixed observed inputs and are not attributed. The target `Y` mechanism is always active so that upstream changes can propagate into the final compromise outcome.

## Sustained intervention and paired mechanism replay

For focal control `c`, retain the RQ1 sustained intervention convention:

`Delta_c = E[Y_5(do(c_{0:5}=0)) - Y_5(do(c_{0:5}=1))]`.

All attribution simulations use the same 1,500 fixed anchor trajectories and paired common-random-number exogenous draws for the two regimes.

For a subset `S` of the five mechanism blocks, construct a hybrid intervention replay:

- first simulate the matched `do(c=0)` baseline trajectory and retain every endogenous node value at every time;
- then simulate `do(c=1)` with the same exogenous uniforms;
- mechanisms belonging to blocks in `S` are allowed to update under the intervened regime;
- mechanisms belonging to blocks outside `S` are replay-locked at each time to their matched `do(c=0)` baseline values;
- the focal control remains fixed by intervention in every time slice;
- `Y` is always recomputed from its structural mechanism.

Define the coalition value

`v_c(S) = E[Y_5(do(c=0)) - Y_5(hybrid do(c=1); S)]`.

`v_c(empty)` is the direct component that reaches `Y` when all intermediary mechanism blocks are replay-locked. `v_c(G)` for the full five-block set `G={H,P,T,C,R}` must equal the ordinary total effect computed under the same simulator and random-number stream, up to floating-point tolerance.

This is a model-based typed mechanism-replay attribution. It is not claimed to be a natural indirect effect or to be nonparametrically identified from arbitrary observational telemetry.

## Shapley attribution

For each block `g` in `G`, compute its Shapley contribution

`phi_g = sum_{S subseteq G\{g}} |S|! (|G|-|S|-1)! / |G|! * [v_c(S union {g}) - v_c(S)]`.

The decomposition must satisfy the efficiency identity

`Delta_c = d_c + phi_H + phi_P + phi_T + phi_C + phi_R`,

where `d_c = v_c(empty)`.

All 32 coalitions are evaluated exactly; no Monte-Carlo approximation over coalitions is allowed.

## Estimator–oracle firewall

Estimator jobs receive only:

- public train/test trajectories and schema;
- the frozen DCHAG estimator configuration;
- the dense comparator code;
- target anchors needed for the frozen intervention standardization.

They must not receive `world.json`, `true_edges.json`, `oracle_effects.json`, or any private SCM parameter before their typed-attribution outputs are frozen and hashed.

Private SCM attribution is computed only in a later scoring job after all 16 estimator outputs are frozen.

## Monte Carlo configuration

Use exactly 100 paired Monte Carlo draws per anchor/regime/coalition, matching the RQ1 intervention simulation depth. Seeds are deterministic under namespace `V3-TMA-001` and must encode world, model, control, coalition, and purpose.

No seed may be changed after inspecting results.

## Primary endpoint

For each world `w` and model `m`, compute component-wise attribution error over the six components `{direct,H,P,T,C,R}` and four controls:

`TMAE_{w,m} = mean_{c,k} |a_hat_{w,m,c,k} - a_oracle_{w,c,k}|`.

The primary endpoint is the paired world-level difference

`d_w = TMAE_{w,DCHAG} - TMAE_{w,Dense}`

over the 16 independent worlds.

Report:

- mean DCHAG TMAE;
- mean dense TMAE;
- mean paired difference;
- 10,000 world bootstrap 95% CI, seed `20260852`;
- exact 2^16 sign-flip p-value.

A negative point estimate favors DCHAG; superiority may be claimed only if the pre-specified interval/test support it. A null or dense-favorable outcome must be retained.

## Secondary endpoints

1. **Decomposition closure error** — absolute difference between total effect and direct-plus-Shapley sum; numerical tolerance target <= `1e-10` for every record.
2. **Total-effect replay consistency** — `v(G)` versus the ordinary intervention effect under the identical seed stream; numerical tolerance target <= `1e-10`.
3. **Dominant mechanism accuracy** — whether the estimated component with largest absolute magnitude among `{direct,H,P,T,C,R}` matches the oracle dominant component for each world/control; ties resolved lexicographically after tolerance `1e-12`.
4. **Component sign agreement** — evaluated only when `|oracle attribution| >= 0.005`; report numerator, denominator, and rate.
5. **Family-specific summaries** — descriptive means for helpdesk/identity, BEC/payment, exfiltration, and IT/OT.
6. **Attribution sparsity/readability** — DCHAG learned-edge count and number of non-negligible (`|a| >= 0.005`) mechanism components; descriptive only and never used to override the primary endpoint.

No secondary endpoint may replace or redefine the primary endpoint after result inspection.

## Guardrails

The implementation and scored result must assert:

- exactly 16 fixed worlds;
- exactly four fixed controls per world;
- exactly 32 coalitions per world/control/model/oracle;
- exactly 1,500 standardization anchors per world;
- exactly 100 paired MC reps;
- DCHAG cap remains 8;
- no hyperparameter selection;
- no world or control exclusion;
- no target/private SCM access by estimator jobs;
- estimation outputs frozen before private scoring;
- all negative/null components retained;
- RQ1–RQ4 and scaling records unchanged.

## Claim boundary

If successful, `V3-TMA-001` may support the following bounded contribution: DCHAG provides a typed, auditable mechanism attribution of sustained control effects and the attribution can be quantitatively scored against a known SCM oracle.

It may not support claims that:

- the decomposition is uniquely identifiable from real observational LANL/OpTC telemetry;
- Shapley mechanism contributions are natural indirect effects;
- learned edges are real-world causal edges;
- typed attribution proves real defensive-control effectiveness;
- DCHAG is universally superior to dense causal estimation.

## Publication role

This experiment is intended to test the distinctive scientific value of the typed graph itself. Scalar effect fidelity remains governed by the already audited RQ1 result. The new contribution is manuscript-eligible only after a separate independent artifact audit and ledger entry are complete.
