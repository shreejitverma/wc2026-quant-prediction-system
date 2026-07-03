# Mathematical Modeling Suite (Deep Dive)

The WC2026 quantitative system relies on a dynamically weighted ensemble of highly specific sub-models. This document outlines the rigorous mathematical equations, statistical priors, data schemas, and operational trade-offs (pros, cons, and specific football-related failure modes) utilized in the modeling suite (`src/wc2026/models/`).

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
- $\alpha_i$ = Attack strength of team $i$. A value of $1.2$ indicates that team $i$ is expected to score $20\%$ more goals than an average team against an average defense.
- $\beta_j$ = Defense weakness of team $j$. A value of $0.8$ indicates that team $j$ is expected to concede $20\%$ fewer goals than an average defense against an average attack.
- $\gamma$ = Global Home Advantage multiplier (ignored if neutral venue). Typically fits to a value between $1.15$ and $1.35$.

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

The parameter $\rho$ models the correlation between the scoring rates. A positive $\rho$ increases the probability of low-scoring draws and reduces the probability of 1-0 or 0-1 scorelines, aligning the model with historical empirical distributions.

### Exponential Time Decay
To prioritize recent form without discarding historical sample sizes, we discount past matches exponentially when calculating the Log-Likelihood:

$$
w(t) = e^{-\xi \Delta t}
$$

Where $\Delta t$ is the number of days between the match and the date of evaluation $T$, and $\xi$ is the decay half-life parameter (set to $0.004$ empirically, representing a half-life of approximately $173$ days).

### Operational Breakdown
*   **Why We Use It (Rationale)**: M1 establishes our structural baseline of scoring expectations. Bivariate Poisson models are the industry-standard starting point for association football modeling because goals are rare, discrete events. Correcting for low scores is essential to avoid leaking value in low-score draw markets (e.g. 0-0 or 1-1).
*   **Pros**:
    *   **Computationally Efficient**: Optimization completes in milliseconds using standard L-BFGS-B minimizers.
    *   **Low Complexity**: Highly interpretable parameters (attack/defense strength coefficients are readable directly).
    *   **Draw Accuracy**: Explicitly captures the correlation between low scorelines.
*   **Cons**:
    *   **Static Regret**: The model uses a fixed historical dataset. It cannot easily capture sudden real-time shifts in form, structural play changes, or context-specific dynamics (e.g. key player injuries or motivation drops).
    *   **Identifiability Constraint**: Requires explicit normalization constraints ($\frac{1}{N}\sum_{i=1}^N \alpha_i = 1$) to prevent scaling drift during fitting.
*   **Data Requirements & Schema**:
    *   Queries the `fixtures` and `results` tables from the DuckDB Feature Store.
    *   Required fields: `date`, `home_team`, `away_team`, `home_score`, `away_score`, `neutral` (boolean).
*   **Football Failure Modes**:
    *   **Early Red Cards**: If a team receives a red card in the 5th minute, their effective defensive rating ($\beta$) worsens dramatically, which M1 cannot adapt to.
    *   **"Dead Rubber" Group Stage Matches**: If a team has already qualified for the knockouts and rests their starting XI, M1 will overstate their scoring expectations because it relies on historical team names rather than squad composition.

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

*(Where $\alpha$ is the `learning_rate` hyperparameter, which governs the responsiveness of the filter)*.

### Operational Breakdown
*   **Why We Use It (Rationale)**: Football team strength changes continuously. A static model (even with time decay) can be slow to adapt to sudden team transformations (e.g. a manager change or tactical evolution). M2 processes matches sequentially, behaving like a Kalman or Elo filter to capture dynamic momentum.
*   **Pros**:
    *   **Highly Responsive**: Adapts instantly to recent shock results or high-scoring trends.
    *   **Low Footprint**: Does not require retraining on full historical datasets; updates are local to the played match.
*   **Cons**:
    *   **High Variance**: Prone to overreacting to noisy, high-scoring statistical outliers (e.g. a fluke 5-0 win against a tired squad).
    *   **Cold Start Problem**: Newly promoted or rarely playing international teams take a significant number of matches to reach stable ratings.
*   **Data Requirements & Schema**:
    *   Requires a strictly chronological sequence of results.
    *   Required fields: `date`, `home_team`, `away_team`, `home_score`, `away_score`, `neutral`.
*   **Football Failure Modes**:
    *   **Overreacting to Outliers**: If a dominant team has a single defensive disaster (e.g. losing 7-1), M2 will aggressively downgrade their defensive rating ($\beta$), leading to mispriced value in subsequent matches when they revert to their defensive mean.
    *   **Friendly Matches**: M2 updates ratings for all matches equally, meaning a low-effort friendly match where teams test youth players can corrupt the competitive rating state.

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

The standard deviation parameters $\sigma_{att}$ and $\sigma_{def}$ represent the variability of team strengths globally. They are modeled with a weakly informative prior:

$$
\sigma_{att} \sim \text{HalfNormal}(0.5)
$$

$$
\sigma_{def} \sim \text{HalfNormal}(0.5)
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

### Operational Breakdown
*   **Why We Use It (Rationale)**: International matches are extremely sparse compared to domestic leagues. Traditional optimization techniques (like maximum likelihood) overfit wildly when a team plays only 3-5 competitive matches a year. Hierarchical priors shrink extreme estimates back toward the global mean, guaranteeing robust predictions.
*   **Pros**:
    *   **Uncertainty Quantification**: Yields a full distribution of outcomes (posterior probability density), not just point estimates, allowing for accurate pricing of tail-risk contracts.
    *   **Overfitting Resistance**: Structural shrinkage prevents wild model reactions to isolated upsets.
*   **Cons**:
    *   **Slow Inference**: MCMC sampling using NUTS requires significant CPU/GPU computation, making it unsuitable for high-frequency in-play pricing.
    *   **Cold Start Constraint**: Computation latency scales non-linearly with the number of teams and matches in the database.
*   **Data Requirements & Schema**:
    *   Requires historical fixtures and result histories mapped to an indexed team integer dictionary.
    *   Required fields: `home_team_idx`, `away_team_idx`, `neutral`, `home_goals`, `away_goals`.
*   **Football Failure Modes**:
    *   **Underestimating Rapid Risers**: If a small nation undergoes a golden generation of talent, the hierarchical prior will aggressively pull their rating back toward the global mean, causing the model to systematically underprice their winning probabilities during the transition phase.
    *   **Time-Invariant Assumptions**: M3 treats all games in the fitting window as equally relevant unless explicit time-weighting window filters are pre-applied to the training data.

---

## 4. M4: Player-Aggregation (`player_agg.py`)

A bottom-up structural model that calculates fractional xG (Expected Goals) contributions per player based on their club-level statistics, projected over the expected 90-minute starting XI. *(Phase 2 Implementation)*.

### Bottom-Up Aggregate Math
For each player $p$ in the announced starting XI, we fetch their historical club-level xG and xA (Expected Assists) metrics scaled per 90 minutes. The aggregate expected goals for the team is computed as:

$$
\lambda_{team} = \sum_{p \in StartingXI} \left( xG_{90, p} + xA_{90, p} \right) \times \psi_{team}
$$

Where $\psi_{team}$ is a scaling factor adjusting for the step-up in competition from club leagues (e.g. MLS or Eredivisie) to international tournament levels.

### Operational Breakdown
*   **Why We Use It (Rationale)**: National team performances are ultimately a function of their component players. If a national team’s star striker is injured or suspended, team-level models (M1, M2, M3) remain blind to this fact until subsequent matches are played. M4 uses bottom-up aggregation of player statistics to update ratings instantly when starting XI lineups are announced (~60-75 mins before kickoff).
*   **Pros**:
    *   **Lineup Sensitivity**: The only model capable of shifting probabilities immediately based on team sheet releases.
    *   **Granular Signal**: Leverages deep club-level data (e.g. Premier League or La Liga stats) to price players who have played few minutes for their national teams.
*   **Cons**:
    *   **Data Intensive**: Requires continuous, clean, high-velocity player statistics feeds (FBref/StatsBomb) and lineup parsers.
    *   **Lacks Cohesion Context**: Fails to capture tactical chemistry, language barriers, or managerial systems (e.g. a superstar team playing poorly due to lack of collective cohesion).
*   **Data Requirements & Schema**:
    *   Requires integration with real-time lineup data tables and player-level statistics databases.
    *   Required fields: `player_id`, `match_id`, `minutes_played`, `xg`, `xa`, `is_starting` (boolean).
*   **Football Failure Modes**:
    *   **Out of Position Players**: If a manager plays a traditional winger at center-back due to an injury crisis, M4 will aggregate their high club-level xG/xA metrics, overstating the team's attack strength and ignoring the defensive vulnerability.
    *   **Systemic Mismatch**: Players who excel in a highly structured club system (e.g. Manchester City) may perform poorly in a reactive national team setup.

---

## 5. Meta-Model Ensembler (`meta_ensemble.py`)

We combine M1, M2, M3, and M4 dynamically. The ensembler splits the data into a training set and a hold-out validation set.

### Weight Optimization
We define a vector of weights $w$ (where $\sum w_m = 1$) and optimize it using the BFGS algorithm to minimize the Categorical Cross-Entropy Log-Loss on the hold-out set:

$$
Loss(w) = - \sum_{i=1}^{N_{holdout}} \sum_{c \in \{H, D, A\}} y_{i,c} \log(\hat{p}_{i,c}(w))
$$

Where $\hat{p}_{i,c}$ is the blended probability of outcome $c$ for match $i$.

### Pooling Mechanisms
The system supports two methods of blending the individual model matrices ($P_m$):

1. **Linear Pooling** (Arithmetic Mean):

   $$ P_{ensemble} = \sum_{m=1}^M w_m P_m $$

2. **Log-Opinion Pooling** (Geometric Mean / Preferred Method):

   $$ P_{ensemble} \propto \exp \left( \sum_{m=1}^M w_m \log(P_m) \right) $$

Log-Opinion pooling is generally preferred in our architecture because it acts as a more aggressive "veto". If a single structurally sound model assigns a near-zero probability to a tail event, the ensemble probability drops dramatically, preserving the rigorous priors.

### Operational Breakdown
*   **Why We Use It (Rationale)**: No single statistical methodology handles all match lifecycle phases (historical compilation vs. dynamic form changes vs. lineup releases). The Meta-Model uses log-loss minimization to dynamically find the optimal linear or log combination of the sub-models based on historical validation.
*   **Pros**:
    *   **Error Hedging**: Dramatically decreases tail-risk exposure by mitigating the specific biases and blind spots of individual sub-models.
    *   **Dynamic Calibration**: Adapts weights as the tournament progresses (e.g. weighting M4 heavily once lineup sheets drop).
*   **Cons**:
    *   **Veto Dominance in Log-Pooling**: If one sub-model has a numerical error or mispricing that outputs zero probability for an event, log-opinion pooling vetoes it to absolute zero, regardless of other models.
    *   **Complex Debugging**: Isolating the root cause of an anomalous prediction is harder due to the blended nature of the ensemble.
*   **Comparison of Pooling Mechanisms**:

| Property | Linear Pooling | Log-Opinion Pooling |
| :--- | :--- | :--- |
| **Mathematical Formulation** | Weighted arithmetic mean | Weighted geometric mean |
| **Handling of Conflicting Forecasts** | Preserves consensus; compromise distribution | Can result in unimodal consensus or aggressive vetos |
| **Veto Sensitivity** | Low. If one model says $P=0$, the average remains $>0$. | High. If one model says $P=0$, the ensemble is forced to $0$. |
| **Best Used For** | General prediction intervals and smooth blending. | Tail-risk defense and pricing highly structured contracts. |
