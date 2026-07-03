# Mathematical Modeling Suite

The WC2026 quantitative system relies on a dynamically weighted ensemble of highly specific sub-models. This document outlines the rigorous mathematical and statistical priors utilized in the modeling suite (`src/wc2026/models/`).

---

## 1. M1: Dixon-Coles Bivariate Poisson (`dixon_coles.py`)

A classic Poisson model inherently assumes that the goals scored by the Home team ($X$) and Away team ($Y$) are entirely independent. The Dixon-Coles model introduces a dependence parameter $\rho$ to correct the empirical under-pricing of low-scoring draws (0-0, 1-1) and narrow wins (1-0, 0-1) found in pure Poisson models.

### Base Poisson Probabilities
The baseline independent expectation of a match outcome is defined as:

$$
P(X=x, Y=y) = \frac{e^{-\lambda} \lambda^x}{x!} \frac{e^{-\mu} \mu^y}{y!}
$$

Where:
- $\lambda = \alpha_i \beta_j \gamma$ (Home Expected Goals)
- $\mu = \alpha_j \beta_i$ (Away Expected Goals)
- $\alpha_i$ = Attack strength of team $i$
- $\beta_j$ = Defense weakness of team $j$
- $\gamma$ = Global Home Advantage multiplier (ignored if neutral venue)

### The Low-Score Dependence Correction ($\tau$)
The joint probability is corrected by multiplying it by $\tau_{\lambda, \mu}(x, y)$:

$$
\tau_{\lambda, \mu}(x, y) = 
\begin{cases} 
1 - \lambda \mu \rho & \text{if } x=0, y=0 \\
1 + \lambda \rho & \text{if } x=0, y=1 \\
1 + \mu \rho & \text{if } x=1, y=0 \\
1 - \rho & \text{if } x=1, y=1 \\
1 & \text{otherwise}
\end{cases}
$$

### Exponential Time Decay
To prioritize recent form without discarding historical sample sizes, we discount past matches exponentially when calculating the Log-Likelihood:

$$
w(t) = e^{-\xi \Delta t}
$$

Where $\Delta t$ is the number of days between the match and today, and $\xi$ is the decay half-life (set to $0.004$ empirically).

---

## 2. M2: Dynamic State-Space Filter (`state_space.py`)

While M1 fits a static optimization over the entire dataset, M2 behaves like a recursive filter (conceptually similar to Elo, but strictly in the space of Expected Goals).

### Update Rule (Gradient Descent)
For every match played, we calculate the expected goals using the current state ratings:

$$
\lambda_{home} = \exp(Att_{home} - Def_{away} + H_{adv})
$$

$$
\lambda_{away} = \exp(Att_{away} - Def_{home})
$$

We then perform a discrete gradient descent step on the Poisson log-likelihood. The gradient of the log-likelihood with respect to the $\log(\lambda)$ parameter simplifies elegantly to the residual error ($Goals_{actual} - Goals_{expected}$). 

Therefore, the state update step after a match is simply:

$$
Att_{home, t+1} = Att_{home, t} + \alpha (Goals_{home} - \lambda_{home})
$$

$$
Def_{away, t+1} = Def_{away, t} - \alpha (Goals_{home} - \lambda_{home})
$$

*(Where $\alpha$ is the `learning_rate` hyperparameter)*.

---

## 3. M3: Bayesian Hierarchical (`hierarchical.py`)

M3 utilizes `numpyro` to sample the full posterior joint distribution of team strengths using the No-U-Turn Sampler (NUTS) MCMC algorithm. This model imposes rigid priors to prevent overfitting on small sample sizes (such as a 3-game World Cup Group Stage).

### Statistical Model Structure
**Priors**:

$$
Intercept \sim \mathcal{N}(1.0, 0.5)
$$

$$
H_{adv} \sim \mathcal{N}(0.2, 0.2)
$$

$$
Att_i \sim \mathcal{N}(0, \sigma_{att}) \quad \forall \text{ teams } i
$$

$$
Def_i \sim \mathcal{N}(0, \sigma_{def}) \quad \forall \text{ teams } i
$$

To make the system mathematically identifiable, we enforce a soft sum-to-zero constraint by centering the samples:

$$
\sum_{i} Att_i = 0 \quad \text{and} \quad \sum_{i} Def_i = 0
$$

**Log-Expected Goals (Link Function)**:

$$
\theta_{home} = \exp(Intercept + H_{adv} + Att_{home} - Def_{away})
$$

$$
\theta_{away} = \exp(Intercept + Att_{away} - Def_{home})
$$

### Prediction
Instead of a point estimate, M3 samples from the `Predictive` posterior yielding thousands of simulated match outcomes, which we then convert into an empirical 2D discrete probability density matrix.

---

## 4. M4: Player-Aggregation (`player_agg.py`)

A bottom-up structural model that calculates fractional xG (Expected Goals) contributions per player based on their club-level statistics, projected over the expected 90-minute starting XI. *(Phase 2 Implementation)*.

---

## 5. Meta-Model Ensembler (`meta_ensemble.py`)

We combine M1, M2, M3, and M4 dynamically. The ensembler splits the data into a training set and a hold-out validation set.

### Weight Optimization
We define a vector of weights $w$ (where $\sum w_m = 1$) and optimize it using the BFGS algorithm to minimize the Categorical Cross-Entropy Log-Loss on the hold-out set:

$$
Loss(w) = - \sum_{i=1}^{N_{holdout}} \sum_{c \in \{H, D, A\}} y_{i,c} \log(\hat{p}_{i,c}(w))
$$

Where $\hat{p}_{i,c}$ is the blended probability of outcome $c$ for match $i$.

### Pooling Mechanism
The system supports two methods of blending the individual model matrices ($P_m$):

1. **Linear Pooling** (Arithmetic Mean):

   $$ P_{ensemble} = \sum_{m=1}^M w_m P_m $$

2. **Log-Opinion Pooling** (Geometric Mean / Preferred Method):

   $$ P_{ensemble} \propto \exp \left( \sum_{m=1}^M w_m \log(P_m) \right) $$

Log-Opinion pooling is generally preferred in our architecture because it acts as a more aggressive "veto". If a single structurally sound model assigns a near-zero probability to a tail event, the ensemble probability drops dramatically, preserving the rigorous priors.
