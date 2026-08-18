from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


def _prospective_features(cfg, df: pd.DataFrame) -> pd.DataFrame:
    """Build deployment-time features available before socio-technical states unfold.

    The benchmark exposes the organizational risk-context flag and the planned
    control sequence.  Realized human/process/technical states are deliberately
    excluded so all probability comparators answer the same prospective question.
    """
    tids = np.sort(df.trajectory_id.unique())
    first = df[df.time == 0].set_index('trajectory_id').reindex(tids)
    x = pd.DataFrame({'trajectory_id': tids})
    x['high_risk_context'] = first['high_risk_context'].to_numpy(float)
    for c in cfg.controls:
        piv = df.pivot(index='trajectory_id', columns='time', values=c).reindex(tids)
        x[f'{c}_mean'] = piv.mean(axis=1).to_numpy(float)
        x[f'{c}_ever'] = piv.max(axis=1).to_numpy(float)
    y = (df[df.time == cfg.horizon - 1]
         .set_index('trajectory_id').reindex(tids)[cfg.target])
    x['y'] = y.to_numpy(int)
    return x


class SEAGInspiredRiskBaseline:
    """Prospective shared-endpoint risk comparator; not a causal estimator.

    This deliberately modest comparator uses only risk context and planned
    controls.  It is inspired by social-engineering risk scoring but is not
    presented as a faithful reimplementation of any specific SEAG paper.
    """
    def __init__(self, cfg):
        self.cfg = cfg
        self.model = None
        self.cols = []

    def fit(self, df):
        x = _prospective_features(self.cfg, df)
        self.cols = [c for c in x.columns if c not in {'trajectory_id', 'y'}]
        self.model = LogisticRegression(C=1e6, solver='liblinear', max_iter=300).fit(x[self.cols], x.y)
        return self

    def predict_proba(self, df):
        x = _prospective_features(self.cfg, df)
        return self.model.predict_proba(x[self.cols])[:, 1]


class QualitativeRiskMatrixBaseline:
    """Prospective empirical risk matrix using context and control coverage only."""
    def __init__(self, cfg):
        self.cfg = cfg
        self.table = {}
        self.global_p = 0.5

    def _features(self, df):
        x = _prospective_features(self.cfg, df)
        ctl_cols = [c for c in x.columns if c.endswith('_mean')]
        coverage = x[ctl_cols].mean(axis=1) if ctl_cols else pd.Series(0.0, index=x.index)
        z = pd.DataFrame(index=x.index)
        z['context'] = x['high_risk_context'].astype(int)
        # Three coarse deployment-time control-coverage strata.
        z['coverage_level'] = pd.cut(coverage, bins=[-1e-9, 0.25, 0.75, 1.0000001], labels=[0, 1, 2]).astype(int)
        z['y'] = x['y'].astype(int)
        return z

    def fit(self, df):
        x = self._features(df)
        self.global_p = float((x.y.sum() + 1) / (len(x) + 2))
        for ctx in [0, 1]:
            for lev in [0, 1, 2]:
                ys = x[(x.context == ctx) & (x.coverage_level == lev)].y
                self.table[(ctx, lev)] = float((ys.sum() + 1) / (len(ys) + 2)) if len(ys) else self.global_p
        return self

    def predict_proba(self, df):
        x = self._features(df)
        return np.array([self.table.get((int(c), int(l)), self.global_p)
                         for c, l in zip(x.context, x.coverage_level)], dtype=float)
