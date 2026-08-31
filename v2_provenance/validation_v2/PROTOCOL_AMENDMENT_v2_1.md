# DCHAG adversarial validation protocol amendment v2.1

Date: 2026-08-18
Timing: frozen after development-world scoring and before generation of any confirmatory or latent-sensitivity observations.

## Development finding

The initial v2 mutual-information screening rule produced acceptable predictive skill but excessive interventional bias because marginal screening could omit direct parents whose information became visible only conditionally on other history variables. This was observed exclusively on the four prespecified development worlds.

## Estimator revision

The confirmatory DCHAG-Learned estimator therefore uses:

- the same dense temporally admissible candidate set as v2;
- an L1-penalized logistic screening model (`C=0.05`) fitted from observed data only;
- ranking by absolute conditional screening coefficient;
- at most 10 selected parents per local node;
- a refitted local logistic model containing the selected main effects plus all pairwise interactions among them (`C=0.7`);
- no ground-truth parent, coefficient, interaction, link-function or hidden-variable input.

The parent cap was selected on the development worlds from 6, 8 and 10 using mean world-level intervention-effect MAE as the prespecified primary development criterion. Mean MAE values were approximately 0.03657, 0.02002 and 0.01843, respectively. The cap is now frozen at 10.

## Strong comparator

The dense sequential g-formula remains independent of the true DAG. Each local conditional model uses all temporally admissible observed history and a histogram gradient-boosting classifier, which can represent nonlinearities and interactions without receiving the sparse DCHAG topology.

## Confirmatory lock

No estimator hyperparameter or confirmatory world-generation rule may be changed after this amendment. Confirmatory worlds use seeds and observations that were not generated or inspected during development.
