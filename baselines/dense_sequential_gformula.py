from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

from dchag.config import ModelConfig


@dataclass(frozen=True)
class DenseSequentialEstimate:
    control: str
    baseline_risk: float
    intervention_risk: float
    risk_reduction: float
    n_trajectories: int
    folds: int
    mc_per_trajectory: int


@dataclass(frozen=True)
class _NodeModel:
    node_id: str
    preceding_states: tuple[str, ...]
    coef: np.ndarray
    intercept: float
    constant: float | None = None

    def probability(self, X: np.ndarray) -> np.ndarray:
        if self.constant is not None:
            return np.full(X.shape[0], self.constant, dtype=float)
        eta = self.intercept + X @ self.coef
        return 1.0 / (1.0 + np.exp(-np.clip(eta, -35.0, 35.0)))


class CrossFittedDenseSequentialGFormula:
    """Dense longitudinal g-computation without DCHAG sparse parent edges.

    The model uses the declared evaluation order only. Each attack-state variable is
    fitted from a dense admissible history: current context/controls, all preceding
    same-slice attack states, and one-step lag of every observed variable.
    """

    def __init__(
        self,
        cfg: ModelConfig,
        *,
        n_splits: int = 5,
        fold_seed: int = 260817,
        mc_per_trajectory: int = 20,
        simulation_seed_base: int = 811700,
    ):
        self.cfg = cfg
        self.n_splits = int(n_splits)
        self.fold_seed = int(fold_seed)
        self.mc_per_trajectory = int(mc_per_trajectory)
        self.simulation_seed_base = int(simulation_seed_base)
        self.contexts = tuple(n.id for n in cfg.nodes if n.type == "context")
        self.controls = tuple(cfg.controls)
        self.states = tuple(n.id for n in cfg.nodes if n.type not in {"context", "control"})
        if len(self.contexts) != 1:
            raise ValueError("frozen comparator expects one root context variable")
        self.context = self.contexts[0]

    def _trajectory_ids_and_outcomes(self, df: pd.DataFrame):
        ids = np.sort(df.trajectory_id.unique())
        y = (
            df[df.time == self.cfg.horizon - 1]
            .set_index("trajectory_id")[self.cfg.target]
            .reindex(ids)
            .to_numpy(int)
        )
        return ids, y

    def _feature_names(self, node_id: str) -> tuple[str, ...]:
        j = self.states.index(node_id)
        preceding = self.states[:j]
        current = [f"cur:{self.context}"] + [f"cur:{c}" for c in self.controls] + [f"cur:{s}" for s in preceding]
        lagged = [f"lag:{self.context}"] + [f"lag:{c}" for c in self.controls] + [f"lag:{s}" for s in self.states]
        return tuple(current + lagged)

    def _design(self, df: pd.DataFrame, node_id: str) -> tuple[np.ndarray, np.ndarray]:
        preceding = self.states[: self.states.index(node_id)]
        grouped = df.groupby("trajectory_id", sort=False)
        cols = []
        cols.append(pd.to_numeric(df[self.context], errors="coerce").to_numpy(float))
        for c in self.controls:
            cols.append(pd.to_numeric(df[c], errors="coerce").to_numpy(float))
        for s in preceding:
            cols.append(pd.to_numeric(df[s], errors="coerce").to_numpy(float))
        for v in (self.context,) + self.controls + self.states:
            lag = grouped[v].shift(1).where(df["time"] >= 1, 0.0)
            cols.append(pd.to_numeric(lag, errors="coerce").to_numpy(float))
        X = np.column_stack(cols)
        y = pd.to_numeric(df[node_id], errors="coerce").to_numpy(float)
        mask = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
        return X[mask], y[mask].astype(int)

    def _fit_fold(self, train_df: pd.DataFrame) -> tuple[_NodeModel, ...]:
        out = []
        for s in self.states:
            X, y = self._design(train_df, s)
            preceding = self.states[: self.states.index(s)]
            if len(y) == 0:
                out.append(_NodeModel(s, preceding, np.zeros(X.shape[1]), 0.0, 0.5))
                continue
            if len(np.unique(y)) < 2:
                out.append(_NodeModel(s, preceding, np.zeros(X.shape[1]), 0.0, float(y[0])))
                continue
            m = LogisticRegression(C=1e6, solver="liblinear", max_iter=1000, fit_intercept=True)
            m.fit(X, y)
            out.append(_NodeModel(s, preceding, m.coef_[0].astype(float), float(m.intercept_[0])))
        return tuple(out)

    def _context_matrix(self, hold_df: pd.DataFrame, ids: np.ndarray) -> np.ndarray:
        q = hold_df.pivot(index="trajectory_id", columns="time", values=self.context).reindex(ids)
        q = q.reindex(columns=range(self.cfg.horizon))
        arr = q.to_numpy(float)
        if not np.all(np.isfinite(arr)):
            raise ValueError("missing root context history")
        return arr.astype(np.int8)

    def _simulate_risk(
        self,
        models: tuple[_NodeModel, ...],
        contexts: np.ndarray,
        selected_control: str | None,
        seed: int,
    ) -> float:
        n_base = contexts.shape[0]
        k = self.mc_per_trajectory
        ctx = np.repeat(contexts, k, axis=0)
        n = ctx.shape[0]
        state = {s: np.zeros((n, self.cfg.horizon), dtype=np.int8) for s in self.states}
        ctrl = {}
        for c in self.controls:
            val = 1 if c == selected_control else int(self.cfg.baseline_controls[c])
            ctrl[c] = np.full((n, self.cfg.horizon), val, dtype=np.int8)
        rng = np.random.default_rng(seed)
        uniforms = {
            s: rng.random((n, self.cfg.horizon), dtype=np.float64) for s in self.states
        }
        mmap = {m.node_id: m for m in models}
        for t in range(self.cfg.horizon):
            for s in self.states:
                m = mmap[s]
                cols = [ctx[:, t].astype(float)]
                cols.extend(ctrl[c][:, t].astype(float) for c in self.controls)
                cols.extend(state[p][:, t].astype(float) for p in m.preceding_states)
                pt = t - 1
                if pt < 0:
                    cols.append(np.zeros(n, dtype=float))
                    cols.extend(np.zeros(n, dtype=float) for _ in self.controls)
                    cols.extend(np.zeros(n, dtype=float) for _ in self.states)
                else:
                    cols.append(ctx[:, pt].astype(float))
                    cols.extend(ctrl[c][:, pt].astype(float) for c in self.controls)
                    cols.extend(state[p][:, pt].astype(float) for p in self.states)
                X = np.column_stack(cols)
                p = m.probability(X)
                state[s][:, t] = (uniforms[s][:, t] < p).astype(np.int8)
        return float(state[self.cfg.target][:, -1].mean())

    def estimate_effects(self, df: pd.DataFrame) -> list[DenseSequentialEstimate]:
        ids, y = self._trajectory_ids_and_outcomes(df)
        splitter = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=self.fold_seed)
        fold_rows = []
        for fold, (train_i, hold_i) in enumerate(splitter.split(ids, y)):
            train_ids = set(ids[train_i].tolist())
            hold_ids = ids[hold_i]
            train_df = df[df.trajectory_id.isin(train_ids)].copy()
            hold_df = df[df.trajectory_id.isin(set(hold_ids.tolist()))].copy()
            models = self._fit_fold(train_df)
            contexts = self._context_matrix(hold_df, hold_ids)
            seed = self.simulation_seed_base + fold
            baseline = self._simulate_risk(models, contexts, None, seed)
            for c in self.controls:
                intervention = self._simulate_risk(models, contexts, c, seed)
                fold_rows.append((c, len(hold_ids), baseline, intervention, baseline - intervention))
        out = []
        for c in self.controls:
            rows = [r for r in fold_rows if r[0] == c]
            weights = np.array([r[1] for r in rows], dtype=float)
            weights /= weights.sum()
            base = float(np.sum(weights * np.array([r[2] for r in rows])))
            intervention = float(np.sum(weights * np.array([r[3] for r in rows])))
            effect = float(np.sum(weights * np.array([r[4] for r in rows])))
            out.append(DenseSequentialEstimate(c, base, intervention, effect, len(ids), self.n_splits, self.mc_per_trajectory))
        return out

    def local_positivity(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for c in self.controls:
            target = 1
            for t in range(self.cfg.horizon):
                q = df[df.time == t]
                for context_value in (0, 1):
                    s = q[q[self.context] == context_value]
                    n = int(len(s))
                    count = int((s[c] == target).sum())
                    prob = float(count / n) if n else float("nan")
                    rows.append({
                        "context": self.cfg.name,
                        "control": c,
                        "time": t,
                        "root_context": context_value,
                        "target_state": target,
                        "observed_count": count,
                        "stratum_n": n,
                        "empirical_target_probability": prob,
                        "severe_support_warning": bool(np.isfinite(prob) and prob < 0.05),
                    })
        return pd.DataFrame(rows)
