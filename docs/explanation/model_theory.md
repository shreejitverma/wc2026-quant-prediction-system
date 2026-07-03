# Mathematical Modeling Suite Theory

This document provides a deep, first-principles mathematical explanation of the prediction models (M1–M6), the Meta-Ensembler, and the tournament simulation engine.

---

## 1. Predictive Models (M1–M6)

### 1.1 M1: Dixon-Coles Bivariate Poisson (`dixon_coles.py`)
- **Citation**: Dixon, M. J., & Coles, S. G. (1997). Modelling Association Football Scores and Inefficiencies in the Football Betting Market. *Journal of the Royal Statistical Society*, 46(2), 265-280.
- **Formulation**:
  We assume the goals scored by the home team ($X$) and away team ($Y$) are Poisson-distributed, adjusted by a low-score correction factor $\tau$:
  $$
  P(X=x, Y=y) = \tau_{\lambda, \mu}(x, y) \cdot \frac{e^{-\lambda} \lambda^x}{x!} \cdot \frac{e^{-\mu} \mu^y}{y!}
  $$
  Where:
  $$
  \lambda = \alpha_i \beta_j \gamma \qquad \mu = \alpha_j \beta_i
  $$
  - $\alpha_i$: Attack strength of home team $i$.
  - $\beta_j$: Defense weakness of away team $j$.
  - $\gamma$: Home advantage multiplier.
  - $\tau_{\lambda, \mu}(x, y)$ adjusts low-score cells (0-0, 0-1, 1-0, 1-1) using a correlation parameter $\rho$ to reflect score-dependent tactics.

- **Exponential Time Decay**:
  Matches are weighted during Maximum Likelihood Estimation (MLE) based on their age:
  $$
  w(t) = e^{-\xi \Delta t}
  $$
  Where $\xi = 0.004$ (approx. 173-day half-life).

- **MLE Objective & Identifiability**:
  We minimize the negative log-likelihood:
  $$
  \min_{\alpha, \beta, \gamma, \rho} - \sum_{\text{matches}} w(t) \log P_{\text{adjusted}}(X=x_t, Y=y_t) + C \left( \frac{1}{N}\sum_i \alpha_i - 1 \right)^2
  $$
  Where the quadratic penalty enforces identifiability (attack strengths average to 1.0).

---

### 1.2 M2: Dynamic State-Space Filter (`state_space.py`)
- **Formulation**:
  Rather than static optimization over a full historical block, M2 uses a sequential filter. Expected goals are predicted from the current state variables:
  $$
  \lambda_t = \exp(Att_{home} - Def_{away} + H_{adv})
  $$
  $$
  \mu_t = \exp(Att_{away} - Def_{home})
  $$
  Upon observing the actual goals ($g_h, g_a$), the state ratings are updated using a gradient step on the Poisson log-likelihood:
  $$
  Att_{home}^{(t+1)} = Att_{home}^{(t)} + \alpha_{\text{lr}} (g_h - \lambda_t)
  $$
  $$
  Def_{away}^{(t+1)} = Def_{away}^{(t)} - \alpha_{\text{lr}} (g_h - \lambda_t)
  $$
  Where $\alpha_{\text{lr}} \approx 0.05$ is the learning rate.

---

### 1.3 M3: Bayesian Hierarchical Goals (`hierarchical.py`)
- **Priors**:
  We model team attack/defense ratings as random variables drawn from a global distribution:
  $$
  \sigma_{att} \sim \text{HalfNormal}(0.5) \qquad \sigma_{def} \sim \text{HalfNormal}(0.5)
  $$
  $$
  Att_i \sim \mathcal{N}(0, \sigma_{att}) \qquad Def_i \sim \mathcal{N}(0, \sigma_{def})
  $$
  $$
  \text{Intercept} \sim \mathcal{N}(1.0, 0.5) \qquad H_{adv} \sim \mathcal{N}(0.2, 0.2)
  $$
- **Inference**:
  MCMC sampling using the JAX-accelerated No-U-Turn Sampler (NUTS) yields 2,000 joint posterior samples. The predictions are derived empirically by propagating these samples through the Poisson link function:
  $$
  \theta_{home} = \exp(\text{Intercept} + H_{adv} + Att_{home} - Def_{away})
  $$
  Shrinkage automatically dampens extreme parameters for teams with sparse histories.

---

### 1.4 M4: Player-Aggregation Team Strength (`player_agg.py`)
- **Bottom-up Formulation**:
  Aggregates club-level statistics per player to project expected national team performance:
  $$
  \lambda_{team} = \left( \sum_{p \in StartingXI} (xG_{90, p} + xA_{90, p}) \right) \cdot \psi_{team}
  $$
  Where $\psi_{team}$ is the minutes-weighted average of league-to-tournament step-up adjustment multipliers (e.g. Premier League = 0.95, MLS = 0.75).
  - *Discrepancy Note*: Currently implemented in code as a skeleton returning a constant `1.1` goal rate.

---

### 1.5 M5: Gradient Boosting (LightGBM) (`gbm.py`)
- **Formulation**:
  Learns non-linear interactions (such as the threshold impact of altitude and player rest days) directly from data without linear link constraints.
  Optimizes the Poisson regression loss function:
  $$
  \mathcal{L}(y, \hat{\lambda}) = -\sum_{k} (y_k \log \hat{\lambda}_k - \hat{\lambda}_k)
  $$
  Features include Elodiff ($Elo_{home} - Elo_{away}$), neutrality, and home advantage.

---

### 1.6 M6: Market-Implied Bivariate Poisson (`market_implied.py`)
- **Formulation**:
  Finds the parameters $(\lambda^*, \mu^*)$ that minimize the sum of squared discrepancies against the de-vigged market 1X2 probabilities ($T_H, T_D, T_A$):
  $$
  \min_{\lambda^*, \mu^* > 0} \left[ (P_{Home}(\lambda^*, \mu^*) - T_H)^2 + (P_{Draw}(\lambda^*, \mu^*) - T_D)^2 + (P_{Away}(\lambda^*, \mu^*) - T_A)^2 \right]
  $$
  Solves via L-BFGS-B optimization on every orderbook update.

---

## 2. Meta-Model Ensembler (`meta_ensemble.py`)

Individual predictions are combined dynamically.

### 2.1 Weight Optimization

Weights are optimized on a validation hold-out split (typically 15% chronologically) to minimize Categorical Cross-Entropy Log-Loss:

$$
\mathcal{L}(\mathbf{w}) = -\sum_{i} \sum_{c \in \{H, D, A\}} y_{i,c} \log \hat{p}_{i,c}(\mathbf{w})
$$

Using the BFGS quasi-Newton solver.

### 2.2 Log-Opinion Pooling

To combine the discrete score matrices, we use **Log-Opinion Pooling** (weighted geometric mean):

$$
P_{\text{ensemble}}(X=x, Y=y) \propto \exp\left( \sum_{m=1}^{6} w_m \log P_m(X=x, Y=y) \right)
$$

This pooling acts as a "hard veto": if any model assigns $P = 0$ to an event, the ensemble probability collapses to 0.

---

## 3. Tournament Simulator (`engine.py`)

The simulator runs 100,000 Monte Carlo paths through the 2026 bracket.

### 3.1 Group Stage & FIFA Tiebreaker Pipeline

1. **Match Simulation**: Draw scorelines by inverting the cumulative joint `ScoreDist` matrix for all 72 group stage matches.
2. **Point Calculation**: Compute table points (Win = 3, Draw = 1, Loss = 0).
3. **Tiebreakers**: Resolve ties sequentially per group:
   - Total Points
   - Goal Difference (GD)
   - Goals Scored (GS)
   - Head-to-Head (H2H) results between tied teams
4. **Third-Place Comparison**: Extract the 3rd-place team from each of the 12 groups, rank them using the same tiebreaker criteria, and select the top 8.

### 3.2 Bracket Slotting

The 8 advancing third-place teams are allocated to Round of 32 slots using a pre-computed lookup dictionary reflecting the $\binom{12}{8} = 495$ possible group combinations.

### 3.3 Knockout Stage

Knockout matches are simulated. If a path results in a draw, the simulator resolves advancement via an extra-time goal Poisson drawer followed by a static shootout model (typical probability of home team advancing: 50%).
