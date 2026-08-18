# Statistical-plan clarification v1.1

Date: 2026-08-17
Status: frozen before the retained scoring script reads any retained prediction/effect output.

The original frozen plan specified a context-stratified bootstrap for predictive score differences and Holm correction but did not define the p-value estimator attached to that bootstrap. This clarification fixes that computational detail without changing any endpoint, comparator, seed, sample, or retained prediction.

For each predictive comparator and endpoint (Brier and log loss):

1. compute the paired per-trajectory score difference `DCHAG_full - comparator` within each context;
2. compute the observed statistic as the equally weighted mean of the four context-specific mean differences;
3. perform 2,000 context-stratified paired bootstrap replicates, resampling trajectories with replacement independently within each context, using seed 62026 plus a deterministic endpoint/comparator offset;
4. report the percentile 95% CI;
5. compute a two-sided bootstrap tail probability around zero as `min(1, 2 * min(P*(delta <= 0), P*(delta >= 0)))`, using the finite-sample `(count+1)/(B+1)` correction;
6. apply Holm correction across the comparator family separately for Brier and log loss.

This clarification was made because the p-value computational definition was underspecified, not in response to observed comparative results. No retained prediction is rerun or altered.
