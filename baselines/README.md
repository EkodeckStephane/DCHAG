# DCHAG comparison models

The comparison set is separated by the scientific question each comparator can answer.

- **ObservationalOutcomeBaseline** is a strong prospective outcome-regression comparator. It models terminal compromise from the pre-trajectory risk context and the complete planned control history. Standardizing the control features yields an observational association estimate. It is the main non-interventional comparator for control-effect error.
- **Technical-only SCM** is implemented through `fit_scm(..., drop_types={"human","process"})`. It serves both as the technical probabilistic-graph comparator and the core technical-only ablation. It uses the same estimation machinery so the comparison isolates the removed human/process structure.
- **No-human SCM**, **no-process SCM**, and **static/no-lag SCM** are mechanistic ablations.
- **SEAGInspiredRiskBaseline** is restricted to the shared prospective compromise-risk endpoint. Kim et al. (2018, DOI 10.9708/jksci.2018.23.11.075) derives asset risk from social-engineering training results and system-asset information to generate probability-based attack graphs. The retained benchmark has no employee-training-result variable, so a literal reproduction would require inventing an input absent from the experimental design. The implemented comparator therefore uses only deployment-time risk context and planned-control summaries and is explicitly an adaptation, not an exact reproduction. It is excluded from intervention-effect accuracy tests.
- **QualitativeRiskMatrixBaseline** is a prospective context/control-coverage risk matrix, also restricted to the shared compromise-risk endpoint.

No baseline is assigned a causal metric it is not designed to answer. A direct published-method reproduction is claimed only when the required inputs and algorithmic details are actually available. Approximate/adapted comparators remain labelled as such.
