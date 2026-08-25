# V3-SS-LOFO-001 independent audit

## Scope

This audit covers the frozen leave-one-family-out semi-synthetic transport analysis executed as GitHub Actions run `32627445235`. The analysis was pre-classified as a locked secondary post-RQ1 analysis and is not treated as fresh independent confirmatory evidence.

## Execution integrity

All workflow jobs completed successfully: clean-input preparation, four held-out-family estimation jobs, and private scoring. Each estimator job received only the firewalled fold artifact. Target-family endogenous variables, outcomes, private SCM files, oracle effects, and target `test.csv` files were absent during fitting. Each fold pooled exactly 12 source worlds / 13,200 source training trajectories. Target worlds contributed only split-qualified anchor tensors for intervention standardization and prospective simulation. No target-family hyperparameter selection, fold replacement, or confirmatory retuning occurred.

The active corrected estimator remained `V3-SS-SEL-001-C1`, SHA-256 `d6dfcf53370b5a2b0408f08ddfd88325ca58ce3737750457abd516769a501c31`, with cap 8 and 1,500 target anchor units per world. Each intervention used 100 paired Monte Carlo replicates per anchor/regime.

## Retained artifacts

Final scored artifact: `9490226674`, SHA-256 `247a7b07118f8a71f76a5a58edc9eaa581db3a54ebb140d347b52ca940c5cc93`.

Frozen fold-estimation artifacts:

- BEC/payment: `9490207237`, SHA-256 `be58613bec2fcb3b45ba4022fa6124173bd5349a5a4990497c90dbe8014e5ebd`.
- Exfiltration: `9490220634`, SHA-256 `d9014ed65df44b0bc26183cb3bc465089803819d46d83a3e4f5cfbee0fb8cf7b`.
- Helpdesk/identity: `9490203158`, SHA-256 `8f000030f699bbaf8761e5b276cfbcddf229e6d07780280e769388840a1666ad`.
- IT/OT change: `9490205437`, SHA-256 `a1b87d2dd4e1a11b9690543489599614dd0894cf5861a28b32663b625ff46180`.

## Independent reproduction

The downloaded final ZIP SHA-256 matched GitHub exactly. Every file covered by `RESULT_SHA256.txt` matched its retained hash. Model-level means, family-level DCHAG-minus-dense differences, the 10,000-replicate hierarchical bootstrap with seed `20260823`, the exhaustive four-family sign-flip enumeration (16 assignments), and transfer-penalty means were independently recomputed from the retained CSV files and reproduced the scored outputs.

## Primary results

DCHAG LOFO mean causal-effect MAE is `0.0329182292`; dense sequential g-formula LOFO is `0.0315633333`. The mean paired target-world difference `MAE_DCHAG - MAE_dense` is `+0.0013548958`. Family mean differences are BEC/payment `-0.0018908333`, exfiltration `+0.0043462500`, helpdesk/identity `+0.0066700000`, and IT/OT change `-0.0037058333`.

The hierarchical bootstrap 95% interval is `[-0.0031651953, 0.0057690313]`. The family-level exact sign-flip value is `p=0.625`, retained only as a descriptive secondary quantity. These results do not support DCHAG superiority over dense-g.

DCHAG and dense-g both select the oracle-best control in 16/16 target worlds with normalized regret 0. DCHAG mean Kendall/Spearman ranking correlations are 0.7083/0.8125 versus 0.7708/0.8500 for dense-g. DCHAG structural recovery against the target semi-synthetic SCM has mean precision 0.6354, recall 0.9919, and F1 0.7746. These edge metrics are semi-synthetic structural-recovery metrics only.

Mean transfer penalty relative to the already audited RQ1 within-world estimates is `0.0216069792` for DCHAG and `0.0197565625` for dense-g. Thus the main RQ2 finding is not model superiority but a substantial cross-family degradation in effect fidelity for both estimators, with dense-g showing a slightly smaller mean penalty.

Predictive Brier scores are 0.1339245 for DCHAG and 0.1337985 for dense-g. Both source-prevalence-reference BSS means are slightly negative, so cross-family prospective prediction is not promoted as a positive endpoint.

## Scientific conclusion

`V3-SS-LOFO-001` is PASS in the experiment-lifecycle sense: protocol-complete, retained, and independently audited. The evidence shows that causal-effect estimates are sensitive to workflow-family transport. DCHAG preserves top-control choice across all target worlds and recovers most target SCM edges, but it does not outperform dense sequential g-formula on transported effect MAE or predictive Brier. No formal equivalence claim is made.

The claim boundary is strict: these findings concern the explicit LANL-anchored semi-synthetic SCM benchmark. They do not establish transport of causal mechanisms, attacker pathways, or defensive-control effects across real organizations, and they do not convert observational LANL evidence into causal truth.
