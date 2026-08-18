from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

from dchag.config import ModelConfig


@dataclass(frozen=True)
class GFormulaEstimate:
    control: str
    baseline_risk: float
    intervention_risk: float
    risk_reduction: float
    n_trajectories: int
    folds: int


class CrossFittedFlexibleGFormula:
    """Cross-fitted flexible g-computation comparator for sustained control regimes.

    The estimator intentionally uses only root context history plus complete control
    history. Realized human/process/technical mediators are excluded from the
    adjustment set. This matches the frozen Q1 causal-baseline amendment.
    """

    def __init__(self, cfg: ModelConfig, *, n_splits: int = 5, fold_seed: int = 260817):
        self.cfg = cfg
        self.n_splits = int(n_splits)
        self.fold_seed = int(fold_seed)

    def trajectory_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        parts = []
        context = df.pivot(index="trajectory_id", columns="time", values="high_risk_context")
        context.columns = [f"high_risk_context@{int(t)}" for t in context.columns]
        parts.append(context)
        for control in self.cfg.controls:
            piv = df.pivot(index="trajectory_id", columns="time", values=control)
            piv.columns = [f"{control}@{int(t)}" for t in piv.columns]
            parts.append(piv)
        x = pd.concat(parts, axis=1).sort_index().reset_index()
        y = (
            df[df.time == self.cfg.horizon - 1]
            .set_index("trajectory_id")[self.cfg.target]
            .reindex(x.trajectory_id)
        )
        x["y"] = y.to_numpy(int)
        return x

    @property
    def context_columns(self) -> list[str]:
        return [f"high_risk_context@{t}" for t in range(self.cfg.horizon)]

    @property
    def control_columns(self) -> list[str]:
        return [f"{c}@{t}" for c in self.cfg.controls for t in range(self.cfg.horizon)]

    @property
    def feature_columns(self) -> list[str]:
        return self.context_columns + self.control_columns

    def _learner(self) -> HistGradientBoostingClassifier:
        return HistGradientBoostingClassifier(
            max_iter=250,
            learning_rate=0.05,
            max_leaf_nodes=31,
            min_samples_leaf=50,
            l2_regularization=1.0,
            early_stopping=False,
        )

    def _scenario(self, x: pd.DataFrame, selected_control: str | None) -> pd.DataFrame:
        q = x[self.feature_columns].copy()
        for c in self.cfg.controls:
            val = 1 if selected_control == c else int(self.cfg.baseline_controls[c])
            for t in range(self.cfg.horizon):
                q[f"{c}@{t}"] = val
        return q

    def estimate_effects(self, df: pd.DataFrame) -> list[GFormulaEstimate]:
        x = self.trajectory_frame(df)
        features = x[self.feature_columns]
        y = x["y"].to_numpy(int)
        splitter = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=self.fold_seed)

        base_pred = np.empty(len(x), dtype=float)
        treat_pred = {c: np.empty(len(x), dtype=float) for c in self.cfg.controls}

        for train_idx, hold_idx in splitter.split(features, y):
            model = self._learner()
            model.fit(features.iloc[train_idx], y[train_idx])
            hold = x.iloc[hold_idx]
            base_pred[hold_idx] = model.predict_proba(self._scenario(hold, None))[:, 1]
            for c in self.cfg.controls:
                treat_pred[c][hold_idx] = model.predict_proba(self._scenario(hold, c))[:, 1]

        baseline = float(base_pred.mean())
        out = []
        for c in self.cfg.controls:
            intervention = float(treat_pred[c].mean())
            out.append(
                GFormulaEstimate(
                    control=c,
                    baseline_risk=baseline,
                    intervention_risk=intervention,
                    risk_reduction=float((base_pred - treat_pred[c]).mean()),
                    n_trajectories=len(x),
                    folds=self.n_splits,
                )
            )
        return out

    def positivity_diagnostics(self, df: pd.DataFrame) -> pd.DataFrame:
        x = self.trajectory_frame(df)
        rows = []
        regimes: list[tuple[str, str | None]] = [("baseline", None)] + [
            (f"intervention:{c}", c) for c in self.cfg.controls
        ]
        prop_models: dict[tuple[str, int], tuple[LogisticRegression | None, float]] = {}

        for c in self.cfg.controls:
            for t in range(self.cfg.horizon):
                a = x[f"{c}@{t}"].to_numpy(int)
                z = x[[f"high_risk_context@{t}"]].to_numpy(float)
                if len(np.unique(a)) < 2:
                    prop_models[(c, t)] = (None, float(a[0]))
                else:
                    m = LogisticRegression(C=1e6, solver="liblinear", max_iter=300)
                    m.fit(z, a)
                    prop_models[(c, t)] = (m, np.nan)

        for label, selected in regimes:
            target = {}
            for c in self.cfg.controls:
                val = 1 if selected == c else int(self.cfg.baseline_controls[c])
                for t in range(self.cfg.horizon):
                    target[(c, t)] = val

            exact = np.ones(len(x), dtype=bool)
            regimen_prob = np.ones(len(x), dtype=float)
            for (c, t), val in target.items():
                obs = x[f"{c}@{t}"].to_numpy(int)
                exact &= obs == val
                model, constant = prop_models[(c, t)]
                if model is None:
                    p1 = np.full(len(x), constant, dtype=float)
                else:
                    z = x[[f"high_risk_context@{t}"]].to_numpy(float)
                    p1 = model.predict_proba(z)[:, 1]
                regimen_prob *= p1 if val == 1 else (1.0 - p1)

            rows.append(
                {
                    "context": self.cfg.name,
                    "regime": label,
                    "exact_matches": int(exact.sum()),
                    "n_trajectories": int(len(x)),
                    "observed_match_fraction": float(exact.mean()),
                    "mean_estimated_regime_probability": float(regimen_prob.mean()),
                    "median_estimated_regime_probability": float(np.median(regimen_prob)),
                    "min_estimated_regime_probability": float(regimen_prob.min()),
                    "max_estimated_regime_probability": float(regimen_prob.max()),
                    "expected_support_count": float(regimen_prob.sum()),
                }
            )
        return pd.DataFrame(rows)
