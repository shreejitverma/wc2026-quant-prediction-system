"""M1 - Dixon-Coles adjusted Poisson model."""

from datetime import datetime
from math import factorial

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from wc2026.models.base import Model, ScoreDist


class DixonColesModel(Model):
    """
    Dixon-Coles bivariate Poisson model with low-score dependence and time decay.
    """
    def __init__(self, max_goals: int = 10, time_decay_tau: float = 0.004):
        self.max_goals = max_goals
        self.time_decay_tau = time_decay_tau
        self.teams: list[str] = []
        self.team_to_idx: dict[str, int] = {}
        
        # Parameters to fit
        self.alphas: np.ndarray = None  # Attack
        self.betas: np.ndarray = None   # Defense
        self.gamma: float = 1.0         # Home advantage
        self.rho: float = 0.0           # Low score dependence

    def _tau_matrix(self, lambda_: float, mu: float, rho: float) -> np.ndarray:
        """Compute the Dixon-Coles rho correction matrix."""
        tau = np.ones((self.max_goals + 1, self.max_goals + 1))
        
        # Valid tau constraints:
        # 1 - lambda * mu * rho > 0
        # 1 + lambda * rho > 0
        # 1 + mu * rho > 0
        # 1 - rho > 0
        
        tau[0, 0] = max(1e-10, 1.0 - lambda_ * mu * rho)
        tau[0, 1] = max(1e-10, 1.0 + lambda_ * rho)
        tau[1, 0] = max(1e-10, 1.0 + mu * rho)
        tau[1, 1] = max(1e-10, 1.0 - rho)
        return tau

    def _dc_log_likelihood(self, params, home_idx, away_idx, home_goals, away_goals, neutral, weights, n_teams):
        alphas = params[:n_teams]
        betas = params[n_teams:2*n_teams]
        gamma = params[2*n_teams]
        rho = params[2*n_teams + 1]

        home_alphas = alphas[home_idx]
        away_betas = betas[away_idx]
        away_alphas = alphas[away_idx]
        home_betas = betas[home_idx]

        lambdas = home_alphas * away_betas * np.where(neutral, 1.0, gamma)
        mus = away_alphas * home_betas

        # To prevent log(0)
        lambdas = np.clip(lambdas, 1e-10, np.inf)
        mus = np.clip(mus, 1e-10, np.inf)

        ll_pois = home_goals * np.log(lambdas) - lambdas + away_goals * np.log(mus) - mus

        tau = np.ones_like(lambdas)
        idx_00 = (home_goals == 0) & (away_goals == 0)
        idx_01 = (home_goals == 0) & (away_goals == 1)
        idx_10 = (home_goals == 1) & (away_goals == 0)
        idx_11 = (home_goals == 1) & (away_goals == 1)

        tau[idx_00] = 1 - lambdas[idx_00] * mus[idx_00] * rho
        tau[idx_01] = 1 + lambdas[idx_01] * rho
        tau[idx_10] = 1 + mus[idx_10] * rho
        tau[idx_11] = 1 - rho

        # Avoid log of negative or zero values
        tau = np.clip(tau, 1e-10, np.inf)

        ll = weights * (ll_pois + np.log(tau))

        # Constraint: mean(alpha) == 1 to make the system identifiable
        # We enforce this via a soft penalty here
        penalty = 1e5 * (np.mean(alphas) - 1.0)**2
        
        return -(np.sum(ll) - penalty)

    def fit(self, match_results: pd.DataFrame, as_of_ts: datetime):
        """
        match_results expected columns:
        - date: datetime
        - home_team: str
        - away_team: str
        - home_score: int
        - away_score: int
        - neutral: bool (or int 0/1)
        - weight: float (optional, defaults to 1.0 before time decay)
        """
        df = match_results.copy()
        
        # Calculate time decay
        # t_diff in days
        df['days_diff'] = (pd.to_datetime(as_of_ts, utc=True) - pd.to_datetime(df['date'], utc=True)).dt.total_seconds() / 86400
        # Discard future matches
        df = df[df['days_diff'] >= 0]
        
        decay_weights = np.exp(-self.time_decay_tau * df['days_diff'])
        
        if 'weight' in df.columns:
            weights = df['weight'].values * decay_weights.values
        else:
            weights = decay_weights.values

        # Build team mapping
        all_teams = sorted(list(set(df['home_team'].unique()) | set(df['away_team'].unique())))
        self.teams = all_teams
        self.team_to_idx = {t: i for i, t in enumerate(self.teams)}
        n_teams = len(self.teams)

        home_idx = df['home_team'].map(self.team_to_idx).values
        away_idx = df['away_team'].map(self.team_to_idx).values
        home_goals = df['home_score'].values
        away_goals = df['away_score'].values
        neutral = df['neutral'].values if 'neutral' in df.columns else np.zeros(len(df), dtype=bool)

        # Init params: alpha=1.0, beta=1.0, gamma=1.2, rho=0.0
        init_params = np.concatenate([
            np.ones(n_teams),      # alphas
            np.ones(n_teams),      # betas
            np.array([1.2]),       # gamma
            np.array([0.0])        # rho
        ])

        # Bounds: attack > 0.01, defense > 0.01, gamma > 0.5, rho in [-0.2, 0.2]
        # rho bounds are empirical to avoid invalid probabilities
        bounds = [(0.01, 5.0)] * (2 * n_teams) + [(0.5, 3.0), (-0.2, 0.2)]

        res = minimize(
            self._dc_log_likelihood,
            init_params,
            args=(home_idx, away_idx, home_goals, away_goals, neutral, weights, n_teams),
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': 500}
        )

        if not res.success:
            import warnings
            warnings.warn(f"Dixon-Coles optimization failed: {res.message}", stacklevel=2)

        opt_params = res.x
        self.alphas = opt_params[:n_teams]
        self.betas = opt_params[n_teams:2*n_teams]
        self.gamma = opt_params[2*n_teams]
        self.rho = opt_params[2*n_teams + 1]

        # Rescale alphas strictly to mean 1.0 just in case
        alpha_mean = np.mean(self.alphas)
        self.alphas /= alpha_mean
        self.betas *= alpha_mean  # keep alpha*beta constant

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        """
        features must contain:
        - home_team: str
        - away_team: str
        - neutral: bool (default False)
        """
        home_team = features.get('home_team')
        away_team = features.get('away_team')
        neutral = features.get('neutral', False)
        
        home_idx = self.team_to_idx.get(home_team)
        away_idx = self.team_to_idx.get(away_team)

        # Fallback to mean (1.0) if team unknown
        home_alpha = self.alphas[home_idx] if home_idx is not None else 1.0
        home_beta = self.betas[home_idx] if home_idx is not None else 1.0
        away_alpha = self.alphas[away_idx] if away_idx is not None else 1.0
        away_beta = self.betas[away_idx] if away_idx is not None else 1.0

        lambda_ = home_alpha * away_beta * (1.0 if neutral else self.gamma)
        mu = away_alpha * home_beta

        probs = np.zeros((self.max_goals + 1, self.max_goals + 1))
        
        # Pure Poisson probs
        goals_range = np.arange(self.max_goals + 1)
        # Factorials
        facts = np.array([factorial(i) for i in goals_range])
        
        # Vectorized poisson probabilities
        p_home = (lambda_ ** goals_range) * np.exp(-lambda_) / facts
        p_away = (mu ** goals_range) * np.exp(-mu) / facts
        
        # Outer product
        pois_matrix = np.outer(p_home, p_away)
        
        # Dixon-Coles rho correction
        tau = self._tau_matrix(lambda_, mu, self.rho)
        probs = pois_matrix * tau
        
        # Truncate and renormalize in case of small numerical drifts
        probs /= probs.sum()

        return ScoreDist(probs=probs)

    @property
    def model_card(self) -> dict:
        return {
            "name": "Dixon-Coles",
            "version": "1.0",
            "params": {
                "max_goals": self.max_goals,
                "time_decay_tau": self.time_decay_tau,
                "gamma": self.gamma,
                "rho": self.rho
            },
            "n_teams_fit": len(self.teams)
        }
