"""Bayesian Hierarchical Goals Model."""

from datetime import datetime

import jax.numpy as jnp
import numpy as np
import numpyro
import numpyro.distributions as dist
import pandas as pd
from jax import random
from numpyro.infer import MCMC, NUTS, Predictive

from wc2026.models.base import Model, ScoreDist


def _model(home_team_idx, away_team_idx, neutral, home_goals=None, away_goals=None, n_teams=48):
    # Global intercept
    intercept = numpyro.sample('intercept', dist.Normal(1.0, 0.5))
    
    # Home advantage (applied only if not neutral)
    home_adv_base = numpyro.sample('home_adv', dist.Normal(0.2, 0.2))
    home_adv = home_adv_base * (1.0 - neutral)
    
    # Hierarchical priors
    sigma_att = numpyro.sample('sigma_att', dist.HalfNormal(0.5))
    sigma_def = numpyro.sample('sigma_def', dist.HalfNormal(0.5))
    
    with numpyro.plate('teams', n_teams):
        att = numpyro.sample('att', dist.Normal(0, sigma_att))
        def_ = numpyro.sample('def', dist.Normal(0, sigma_def))
        
    # Sum-to-zero constraint (soft constraint via centering)
    att_c = att - jnp.mean(att)
    def_c = def_ - jnp.mean(def_)
    
    # Log-expected goals
    home_theta = jnp.exp(intercept + home_adv + att_c[home_team_idx] - def_c[away_team_idx])
    away_theta = jnp.exp(intercept + att_c[away_team_idx] - def_c[home_team_idx])
    
    with numpyro.plate('matches', len(home_team_idx)):
        numpyro.sample('home_obs', dist.Poisson(home_theta), obs=home_goals)
        numpyro.sample('away_obs', dist.Poisson(away_theta), obs=away_goals)

class BayesianHierarchicalModel(Model):
    """
    Fits a full posterior distribution for team strengths using JAX/numpyro.
    """
    def __init__(self, max_goals: int = 15, num_warmup: int = 500, num_samples: int = 1000):
        self.max_goals = max_goals
        self.num_warmup = num_warmup
        self.num_samples = num_samples
        self.team_to_idx = {}
        self.idx_to_team = {}
        self.posterior_samples = None

    def fit(self, df: pd.DataFrame, as_of_ts: datetime):
        # We need a stable index for all teams
        all_teams = sorted(list(set(df['home_team']).union(set(df['away_team']))))
        self.team_to_idx = {team: i for i, team in enumerate(all_teams)}
        self.idx_to_team = {i: team for i, team in enumerate(all_teams)}
        
        home_idx = jnp.array([self.team_to_idx[t] for t in df['home_team']])
        away_idx = jnp.array([self.team_to_idx[t] for t in df['away_team']])
        neutral = jnp.array(df['neutral'].astype(float).values)
        home_goals = jnp.array(df['home_score'].values)
        away_goals = jnp.array(df['away_score'].values)
        
        nuts_kernel = NUTS(_model)
        mcmc = MCMC(
            nuts_kernel, 
            num_warmup=self.num_warmup, 
            num_samples=self.num_samples,
            progress_bar=False
        )
        rng_key = random.PRNGKey(0)
        mcmc.run(rng_key, home_idx, away_idx, neutral, home_goals, away_goals, len(all_teams))
        
        self.posterior_samples = mcmc.get_samples()

    def predict_match(self, match_id: str, as_of_ts: datetime, features: dict) -> ScoreDist:
        if self.posterior_samples is None:
            raise ValueError("Model not fitted")
            
        home = features.get('home_team')
        away = features.get('away_team')
        neutral = features.get('neutral', False)
        
        # If team not in training data, default to average (index 0 for now, wait: we should handle unknowns)
        # For this prototype, assume team is known or use random idx 0 but zero out its effect.
        h_idx = self.team_to_idx.get(home, 0)
        a_idx = self.team_to_idx.get(away, 0)
        
        # Sample from posterior predictive
        predictive = Predictive(_model, self.posterior_samples)
        rng_key = random.PRNGKey(1)
        
        preds = predictive(
            rng_key, 
            home_team_idx=jnp.array([h_idx]), 
            away_team_idx=jnp.array([a_idx]), 
            neutral=jnp.array([1.0 if neutral else 0.0]),
            n_teams=len(self.team_to_idx)
        )
        
        home_sims = np.array(preds['home_obs'][:, 0])
        away_sims = np.array(preds['away_obs'][:, 0])
        
        # Create empirical 2D histogram
        prob_matrix, _, _ = np.histogram2d(
            home_sims, 
            away_sims, 
            bins=(self.max_goals, self.max_goals),
            range=[[-0.5, self.max_goals-0.5], [-0.5, self.max_goals-0.5]],
            density=True
        )
        
        return ScoreDist(home_team=home, away_team=away, prob_matrix=prob_matrix)

    def model_card(self) -> dict:
        return {
            "name": "BayesianHierarchicalModel",
            "type": "numpyro_MCMC",
            "num_samples": self.num_samples,
            "fitted": self.posterior_samples is not None
        }
