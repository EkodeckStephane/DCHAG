# DCHAG formal specification

## 1. Scope

DCHAG models finite socio-technical attack trajectories as a **time-unrolled structural causal model (SCM)**. The attack-state projection contains three endogenous state families:

\[
G_t=(V_H^t\cup V_P^t\cup V_T^t,E_t),
\]

where `H` denotes observable human decisions/events, `P` denotes business/workflow states, and `T` denotes technical security/compromise states. Defensive controls are represented in a separate intervention family `V_C`; they influence attack-state equations but are not counted as attack-state nodes.

The complete causal model over a horizon `0..T` is

\[
\mathcal M=(U,V_H,V_P,V_T,V_C,F,P_U),
\]

with a finite acyclic unrolling. Each endogenous binary variable obeys a structural assignment

\[
X_{i,t}=\mathbf 1\{U_{i,t}<\sigma(\eta_{i,t})\},\qquad U_{i,t}\sim \mathrm{Uniform}(0,1),
\]

\[
\eta_{i,t}=b_i+\sum_{j\in Pa_0(i)}\beta_{ji}X_{j,t}+\sum_{k\in Pa_-(i)}\beta_{ki}X_{k,t-\ell_{ki}}+\sum_{c\in Pa_C(i)}\gamma_{ci}C_{c,t}.
\]

`σ(z)=1/(1+exp(-z))`. The reference implementation may additionally support deterministic Boolean equations, provided that equation type is declared in configuration and replay remains deterministic for fixed exogenous variables.

## 2. Node semantics

### Human decision/event nodes (`H`)

A human node records an observable or operationally inferable decision/event, such as `approve_reset`, `disclose_credential`, `authorize_payment`, `approve_export`, or `approve_maintenance`.

A human node must not encode an unmeasured personality adjective as if it were an observed causal state. Traits may enter only as explicitly measured context variables with provenance and measurement assumptions.

### Process/workflow nodes (`P`)

A process node represents workflow state or authorization progression, for example `reset_authorized`, `beneficiary_change_pending`, `export_authorized`, or `maintenance_window_open`.

### Technical state nodes (`T`)

A technical node records a system state relevant to compromise, for example `credential_compromised`, `mailbox_controlled`, `privileged_session`, `sensitive_data_accessed`, or the declared target outcome `compromise`.

### Control variables (`C`)

A control is a manipulable defensive variable with an observational assignment mechanism and a declared intervention value. Examples include stronger identity verification, out-of-band payment confirmation, export approval separation, and maintenance jump-host enforcement.

The observational mechanism may depend on observed risk/context. Under `do(C=c)`, the assignment mechanism of `C` is replaced by the constant assignment `C:=c`; all other structural equations remain unchanged unless the control specification explicitly declares a mechanism replacement.

## 3. Temporal validity

The unrolled causal graph must be acyclic. A parent edge is valid when either:

1. it points from time `t-lag` to `t` with `lag >= 1`; or
2. it is a same-slice edge with `lag = 0` and respects the declared topological order.

A persistent state may have a lag-1 self-parent. Same-slice self-loops are invalid.

## 4. Evidence and event ingestion

An external event is

\[
e=\langle timestamp,actor,action,resource,attributes\rangle.
\]

Each workflow adapter contains deterministic mapping rules from external records to observed DCHAG variables. The mapper may emit `unknown` for unobserved states. It must never map simulator-hidden variables into the observable projection unless the deployment model declares an equivalent sensor/log source.

For an evidence set `E=e`, all observations used by inference must carry provenance: adapter rule, source field(s), timestamp, and confidence/quality metadata where applicable.

## 5. Intervention semantics

For a control variable `C_k`, the atomic intervention

\[
do(C_k=c)
\]

creates a modified model `M_{C_k:=c}` by replacing the structural assignment of `C_k` with the constant `c` and deleting its incoming causal edges in the unrolled graph. Descendant equations retain their declared dependence on `C_k`.

For a control set `S`, interventions are applied simultaneously when their structural targets do not conflict. A conflicting intervention set is invalid and must fail explicitly.

The primary control-effect estimand for target compromise `Y` is the **conditional interventional risk reduction**

\[
\Delta_c(e)=P(Y=1\mid E=e,do(C=c_0))-P(Y=1\mid E=e,do(C=c)),
\]

where `c_0` is the declared baseline control state and `c` is the candidate defensive state. Positive values indicate lower compromise risk under the candidate intervention.

When no conditioning evidence is supplied, the marginal version is used.

## 6. Counterfactual semantics

A unit-level counterfactual is defined only relative to an exogenous realization `u` or a posterior over exogenous variables inferred from factual evidence:

\[
Y_c(u)=Y_{M_{C:=c}}(u).
\]

The reference simulator retains `u` and can therefore compute exact paired factual/counterfactual outcomes for a simulated unit. In observational/deployment inference, DCHAG reports a posterior expectation over compatible exogenous states unless stronger identification is justified. The manuscript must keep this distinction explicit.

## 7. Causal identification contract

Interventional estimates from observational data are claimed to be identified only under the declared graph and the following conditions for the relevant estimand:

- consistency/SUTVA at the modeled unit level;
- positivity for the evaluated control values;
- correct temporal ordering;
- a valid adjustment set blocking backdoor paths between control and outcome, or a separately justified identification strategy;
- no unmodeled selection mechanism that invalidates the estimand.

If these conditions are intentionally violated in a stress test, the resulting error is reported as robustness evidence. The method must not relabel observational conditioning as an intervention.

## 8. Attack paths

A realized causal attack path to target `Y_t=1` is a directed path in the unrolled graph containing active endogenous attack-state nodes whose parent contributions satisfy the declared path-activation rule. For logistic equations, path extraction is an explanatory structural path, not a proof of deterministic necessity; the implementation must identify the rule used (e.g., active-parent threshold or causal-contribution threshold).

Ground-truth simulator paths are generated from the same retained exogenous realization and structural equations. Evaluation must state the granularity (node path, edge path, or causal-parent set).

## 9. Control ranking

For candidate controls `c in C`, DCHAG ranks controls by estimated `Delta_c(e)` by default. Ties are broken deterministically by control identifier. If costs are included, a separately declared utility may be used:

\[
U_c(e)=\Delta_c(e)-\lambda\,Cost(c).
\]

Cost-aware ranking is a secondary estimand and must never be mixed with risk-reduction ranking without explicit labeling.

## 10. Portability contract

The **core semantics** consist of:

- node typing and temporal validity rules;
- structural-equation evaluator;
- intervention surgery;
- evidence representation;
- risk/effect estimator interface;
- path extraction interface;
- serialization/replay semantics.

A workflow is portable when a new context changes only configuration, adapters, node instances, graph topology, equation parameters, control definitions, and domain predicates. Changes to the core evaluator, intervention operator, or type semantics count as a portability failure and must be reported.

## 11. Determinism and replay

A frozen run is identified by:

- configuration SHA-256;
- code commit/hash;
- random seed(s);
- environment manifest;
- simulator/model version.

For fixed inputs and exogenous draws, the reference evaluator must reproduce node states, target outcome, intervention effects, and extracted paths exactly.

## 12. Invalid states and fail-fast behavior

The implementation must reject:

- unknown node types;
- duplicate node identifiers;
- same-slice cycles;
- invalid parent references;
- negative lags;
- controls targeting undeclared variables/equations;
- conflicting simultaneous interventions;
- target variables absent from the graph;
- evidence values outside a variable domain.

## 13. Formal properties to test

### P1 — Type preservation
Every attack-state node belongs to exactly one of `H`, `P`, or `T`.

### P2 — Unrolled acyclicity
Every valid finite-horizon configuration yields a DAG after temporal unrolling.

### P3 — Intervention locality
`do(C=c)` replaces only the control assignment mechanism and leaves non-descendant structural equations unchanged.

### P4 — Replay determinism
For fixed configuration, evidence, interventions and exogenous variables, evaluation is deterministic.

### P5 — No-effect sanity
If a control has no directed path to `Y`, then its exact interventional effect on `Y` is zero up to numerical Monte-Carlo error in marginal estimation; paired exact replay with the same `u` yields identical `Y`.

### P6 — Protective monotonicity test cases
For configurations explicitly declared monotone-protective with non-positive control coefficients on all directed target paths, switching the control from baseline to defensive state must not increase the target probability under exact enumeration or sufficiently precise Monte Carlo evaluation.

P6 is a test-fixture property, not a universal theorem for arbitrary configurations.
