# Mathematical Modeling Suite (Deep Dive)

The WC2026 quantitative system relies on a dynamically weighted ensemble of highly specific sub-models. This document outlines the rigorous mathematical equations, statistical priors, data schemas, and operational trade-offs (pros, cons, and specific football-related failure modes) utilized in the modeling suite (`src/wc2026/models/`).

---

## 0. First-Principles: How Predictions Are Constructed From Scratch

> **Who is this for?** This section starts from absolute zero. You do not need a statistics background. We will build up from a simple question — *"How likely is it that Brazil beats France 2-1?"* — all the way to a live trading decision on a prediction market.

To understand the system, one must understand how a single historical match result eventually translates into a real-time contract quote on Kalshi or Polymarket. Below is the conceptual pipeline:

```
[Raw Historical Match Data: "Brazil 3-0 Serbia, 2022-11-24"]
           │
           ▼
[Step 1: What does history tell us about each team's strength?]
           │  → Attack Strength (α): "How many goals does Brazil tend to score?"
           │  → Defense Weakness (β): "How many goals does France tend to concede?"
           ▼
[Step 2: For THIS specific match, what scoreline rates should we expect?]
           │  → Home Expected Goals (λ): "Brazil vs France — expect ~1.5 goals for Brazil"
           │  → Away Expected Goals (μ): "Brazil vs France — expect ~1.1 goals for France"
           ▼
[Step 3: What is the probability of EACH exact scoreline (0-0, 1-0, 2-1, etc.)?]
           │  → The 15×15 Scoreline Matrix (ScoreDist): a full probability map of every possible result
           ▼
[Step 4: Run the tournament 100,000 times, respecting all the complex bracket rules]
           │  → "Brazil wins the World Cup" in 14,200 out of 100,000 simulations → 14.2% probability
           ▼
[Step 5: Compare our probability to the prediction market price → trade if there's edge]
           │  → Market says 12% → We say 14.2% → Buy the contract → $+0.022 edge per dollar
           ▼
[Execute Trade on Kalshi/Polymarket]
```

---

### Step 1: What is "Team Strength"? How do we measure it?

**Analogy**: Imagine you are a restaurant critic rating restaurants. You don't just count how many meals a restaurant has served — you rate them relative to the average restaurant. A restaurant rated $1.5$ is $50\%$ better than average. A restaurant rated $0.7$ is $30\%$ worse than average.

We do the same thing for football teams. We assign each team **two relative scores**:

*   **Attack Strength ($\alpha_i$)**: How many goals does this team score relative to an average team?
*   **Defense Weakness ($\beta_i$)**: How many goals does this team concede relative to an average team?

> **Important**: Both scores are normalized so that the global average of all teams is exactly $1.0$.

**Worked Example:**
| Team | Attack $\alpha$ | Defense $\beta$ | Interpretation |
|------|----------------|----------------|----------------|
| Brazil | 1.45 | 0.80 | Scores 45% more than average; concedes 20% fewer than average (strong all-round) |
| France | 1.35 | 0.85 | Scores 35% more than average; concedes 15% fewer than average |
| Morocco | 0.90 | 0.75 | Scores 10% less than average but concedes 25% fewer than average (defensive team) |
| Saudi Arabia | 0.75 | 1.15 | Scores 25% less than average; concedes 15% more than average (weak team) |

**How are these numbers estimated?** We feed the entire historical results database (thousands of international matches) into a mathematical optimization algorithm (called Maximum Likelihood Estimation). The optimizer finds the exact $\alpha$ and $\beta$ values for each team that best explain all the observed historical scorelines simultaneously.

Formally, we find the values that maximize the likelihood of having observed all historical results. If our parameters say Germany should score 2 goals but Germany historically scores 1.6, the optimizer adjusts them until the model fits reality as closely as possible.

---

### Step 2: From Ratings to Expected Goals for a Specific Match

**Analogy**: Now that you know the "strength rating" of each restaurant, you can predict the quality of a meal when they cook together. If a top-rated chef (strong attack $\alpha$) faces a weak sous-chef (weak defense $\beta$), you'd expect a lot of flavor (goals).

When two teams meet, we combine their ratings to calculate two **Expected Goals (xG)** values: one for each team:

*   **$\lambda$ (Expected Goals for the Home Team)**:
    $$
    \lambda = \alpha_{home} \times \beta_{away} \times \gamma
    $$
*   **$\mu$ (Expected Goals for the Away Team)**:
    $$
    \mu = \alpha_{away} \times \beta_{home}
    $$

**What does each term mean?**
*   $\alpha_{home}$: How prolific is the home team's attack?
*   $\beta_{away}$: How leaky is the away team's defense? (Higher = more goals conceded)
*   $\gamma$: The **Home Advantage** multiplier. Teams playing at home historically score ~$15$-$25\%$ more goals due to crowd support, familiarity with pitch, and lack of travel fatigue. Typically $\gamma \approx 1.20$.
*   For World Cup matches played on **neutral venues**, we set $\gamma = 1.0$ (no home advantage adjustment).

**Worked Example — Brazil vs France at a Neutral Venue:**

Using the ratings from Step 1 and $\gamma = 1.0$ (neutral):

$$
\lambda_{Brazil} = \alpha_{Brazil} \times \beta_{France} \times 1.0 = 1.45 \times 0.85 \times 1.0 = 1.23 \text{ expected goals}
$$

$$
\mu_{France} = \alpha_{France} \times \beta_{Brazil} \times 1.0 = 1.35 \times 0.80 \times 1.0 = 1.08 \text{ expected goals}
$$

**Interpretation**: On average, if Brazil and France play this match many times, Brazil would score around 1.23 goals and France would score around 1.08 goals per game. This makes Brazil a slight favorite, but France is competitive.

---

### Step 3: From Expected Goals to a Full Scoreline Matrix

We now know Brazil is expected to score 1.23 goals and France 1.08. But that's just the *average*. Football matches are not average — they are individual, unpredictable events. We need the full probability distribution of every possible outcome (0-0, 1-0, 2-1, 3-2, etc.).

#### 3a. Why the Poisson Distribution?

**Analogy**: Think of goals like cars passing through a quiet country road. On average, 3 cars pass per hour. But in any given hour, the number might be 0, 1, 2, 4, or even 7. The number of events in a fixed time window, when events are rare and random, follows a **Poisson distribution**.

Football goals share all the same properties:
*   They are rare (average $< 3$ per match).
*   They happen at random moments, independently of each other.
*   We have a known average rate ($\lambda$ or $\mu$ expected goals).

So we use the **Poisson Probability Mass Function (PMF)** to compute the probability of scoring exactly $x$ goals given an expected rate $\lambda$:

$$
P(X = x \;|\; \lambda) = \frac{\lambda^x \cdot e^{-\lambda}}{x!}
$$

**Breaking down the formula piece by piece:**
*   $\lambda$ = Expected goals (e.g. 1.23 for Brazil)
*   $x$ = The exact number of goals we're calculating probability for (e.g. 0, 1, 2, 3...)
*   $\lambda^x$ = The rate raised to the power of $x$: "how consistent is this rate with $x$ events?"
*   $e^{-\lambda}$ = A normalizing factor ensuring all probabilities sum to 1 (where $e \approx 2.718$, Euler's number)
*   $x!$ = "x factorial" = $x \times (x-1) \times ... \times 1$. This corrects for the number of ways $x$ events can be ordered.

**Worked Example — Brazil scoring exactly 0, 1, 2, or 3 goals ($\lambda = 1.23$):**

$$
P(X=0) = \frac{1.23^0 \cdot e^{-1.23}}{0!} = \frac{1 \times 0.2923}{1} = 29.2\%
$$

$$
P(X=1) = \frac{1.23^1 \cdot e^{-1.23}}{1!} = \frac{1.23 \times 0.2923}{1} = 35.9\%
$$

$$
P(X=2) = \frac{1.23^2 \cdot e^{-1.23}}{2!} = \frac{1.513 \times 0.2923}{2} = 22.1\%
$$

$$
P(X=3) = \frac{1.23^3 \cdot e^{-1.23}}{3!} = \frac{1.861 \times 0.2923}{6} = 9.1\%
$$

So Brazil scores 0 goals in a 1-in-3 chance, scores 1 goal in a 1-in-3 chance, and scores 2+ goals in roughly 1-in-3 chance. This makes intuitive sense for a strong team against a strong opponent.

#### 3b. Combining the Two Distributions into a Scoreline Matrix

Since Brazil's goals and France's goals are approximately **independent** (one team scoring doesn't directly cause or prevent the other from scoring), the probability of a specific exact scoreline $(x, y)$ is simply the **product** of their individual Poisson probabilities:

$$
P(\text{Brazil}=x, \text{France}=y) = P(X=x \;|\; \lambda_{Brazil}) \times P(Y=y \;|\; \mu_{France})
$$

**Worked Example — What is the probability of a 1-1 draw?**

$$
P(\text{Brazil}=1) = 35.9\%
$$

$$
P(\text{France}=1) = \frac{1.08^1 \cdot e^{-1.08}}{1!} = \frac{1.08 \times 0.3396}{1} = 36.7\%
$$

$$
P(\text{1-1 Draw}) = 0.359 \times 0.367 = 13.2\%
$$

We repeat this calculation for **every combination** of scorelines from 0-0 to 14-14, populating a 15×15 grid. This grid is called the **ScoreDist matrix** and it is the single most important data structure in our system. Here is a visual excerpt:

```
          France Goals (Y)
          0      1      2      3
Brazil  0 | 9.9% | 10.3% | 5.5% | 2.0% ...
Goals   1 | 12.2%| 12.7% | 6.8% | 2.4% ...
(X)     2 | 7.5% | 7.8%  | 4.2% | 1.5% ...
        3 | 3.1% | 3.2%  | 1.7% | 0.6% ...
        ...
```

*   **Brazil Win cells** (lower-left triangle, where $x > y$): Sum = ~53%
*   **Draw cells** (diagonal, where $x = y$): Sum = ~26%
*   **France Win cells** (upper-right triangle, where $x < y$): Sum = ~21%

#### 3c. The Low-Score Correction ($\tau$ matrix)

In pure Poisson theory, the 0-0 draw probability would be about 9.9%. But empirically, 0-0 draws, 1-0 wins, and 1-1 draws occur **slightly more often** than the pure independence assumption suggests. This is because of real-world tactical effects (teams defending a lead, match intensity management).

The **Dixon-Coles $\tau$ correction** adjusts the probability of the four "low-score" cells using a **correlation parameter $\rho$** (typically a small negative number around $-0.12$):

$$
\tau_{\lambda,\mu}(x, y) =
\begin{cases}
1 - \lambda \mu \rho & \text{if } x=0, y=0 \quad \text{(increases 0-0 probability)}\\
1 + \lambda \rho & \text{if } x=0, y=1 \quad \text{(adjusts 0-1 probability)}\\
1 + \mu \rho & \text{if } x=1, y=0 \quad \text{(adjusts 1-0 probability)}\\
1 - \rho & \text{if } x=1, y=1 \quad \text{(adjusts 1-1 probability)}\\
1 & \text{otherwise} \quad \text{(no change for higher scores)}
\end{cases}
$$

The adjusted probability becomes:

$$
P_{adjusted}(X=x, Y=y) = P(X=x, Y=y) \times \tau_{\lambda,\mu}(x, y)
$$

---

### Step 4: From One Match to a Full Tournament Simulation

**The core problem**: Even if we can price Brazil vs France perfectly, we cannot directly calculate "What is Brazil's probability of winning the World Cup?" by hand. The reason is that the tournament bracket is a **conditionally dependent** sequence of 104 matches.

**Analogy**: Imagine a giant maze with 64 rooms. Whether Brazil ends up in Room 12 (a Quarterfinal against Argentina) or Room 7 (a Quarterfinal against Spain) depends on every single result in every single group. These dependencies make exact analytical calculation mathematically intractable. The only efficient approach is to **simulate the maze thousands of times**.

#### 4a. The Monte Carlo Sampling Process

For each of 100,000 independent simulations (called "paths"):

1.  **Sample a Group Stage Scoreline**: For the Brazil vs France match, we draw a uniform random number $U \sim \text{Uniform}[0, 1]$ between 0 and 1. We then find the scoreline whose cumulative probability first exceeds $U$. If our cumulative scoreline matrix is:
    *   0-0: cumulative probability 0-9.9%
    *   1-0: cumulative probability 9.9%-22.1%
    *   0-1: cumulative probability 22.1%-32.4%
    *   1-1: cumulative probability 32.4%-45.1%
    *   ...
    And we drew $U = 0.38$, the simulation picks a **1-1 draw** (since 0.38 falls in the 32.4%-45.1% range).

2.  **Repeat** this for all 48 Group Stage matches simultaneously.

3.  **Compute Group Tables**: Award 3 points for win, 1 for draw, 0 for loss. Apply the strict FIFA tiebreaker rules in order:
    1.  Points
    2.  Goal Difference (GD)
    3.  Goals Scored
    4.  Head-to-Head points
    5.  Head-to-Head GD
    6.  Fair play points (yellow/red cards)
    7.  FIFA ranking (last resort)

4.  **Map to Knockout Bracket**: The top 2 from each group, plus the best 4 third-place teams, advance. Their positions in the bracket are assigned using pre-computed cross-group permutation index tables.

5.  **Simulate the Knockout Rounds (R16 → QF → SF → Final)**: For knockout matches, a draw after 90 minutes is resolved by sampling a "penalty shootout winner" (50/50 or biased by M4 player-level penalty conversion stats).

6.  **Record the Winner**: If Brazil wins the final in this simulation path, we add 1 to Brazil's counter.

#### 4b. Aggregating Results into Probabilities

After 100,000 simulations, we count how many times each team reached each stage:

```
Brazil wins Final:       14,200 / 100,000 = 14.2%
France wins Final:       11,800 / 100,000 = 11.8%
Brazil reaches Semi:     27,100 / 100,000 = 27.1%
Brazil wins Group A:     68,000 / 100,000 = 68.0%
```

Each of these is now a **frequency estimate of a true conditional probability**, incorporating all tournament path dependencies. The **Central Limit Theorem** guarantees that the standard error of our estimate is approximately:

$$
SE = \sqrt{\frac{p(1-p)}{N}} = \sqrt{\frac{0.142 \times 0.858}{100000}} \approx 0.11\%
$$

So our 14.2% estimate has a statistical error of only ±0.11%.

---

### Step 5: Converting Probabilities to Prices and Finding Trading Edge

**How do prediction markets work?** A contract on Kalshi/Polymarket for "Brazil wins the World Cup" pays $\$1.00$ if Brazil wins, $\$0.00$ if they don't. The contract currently trades at $\$0.12$ (meaning the market believes there is a 12% chance Brazil wins).

**Our fair value**: Our simulation says Brazil wins 14.2% of paths. Therefore:

$$
\text{Fair Value} = P(\text{Brazil Wins}) \times \$1.00 = 0.142 \times \$1.00 = \$0.142
$$

**The edge calculation**: The market is mispricing this contract! The market price is $\$0.12$ but we estimate fair value at $\$0.142$. The exchange charges a maker fee of, say, $\$0.00$:

$$
Edge = \text{Fair Value} - \text{Market Ask} - \text{Exchange Fee}
$$

$$
Edge = \$0.142 - \$0.120 - \$0.00 = +\$0.022 \text{ per contract}
$$

This means for every $\$1.00$ we invest buying this contract, we expect to profit $\$0.022$ on average (a $2.2\%$ expected return). Over many trades, this positive expectation compounds into consistent profitability.

**Why does this mispricing exist?** The human traders setting the 12% market price are likely:
1.  Not simulating the full tournament topology (they estimate Brazil's chances heuristically).
2.  Not correctly accounting for the 3rd-place cross-group permutation rules that affect how Brazil's knockout bracket assembles.
3.  Anchoring to Brazil's most recent form without properly accounting for opponent quality and venue effects.

Our fully quantitative, mathematically rigorous system captures all of these factors in a single, internally consistent model.

---

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

## 5. M5: Gradient Boosting (LightGBM) (`gbm.py`)

A non-linear model using LightGBM (Gradient Boosting Decision Trees) to predict team scoring expectations by mapping global Elo ratings differences, home advantage, and neutral field status.

### Non-linear Goal Expectancy
Matches are flattened into team-level training matrices where the target $Y$ is goals scored, and features are:

$$
X = [is\_home, neutral, Elo_{diff}] \in \mathbb{R}^{2N \times 3}
$$

Where $Elo_{diff} = Elo_{team} - Elo_{opponent}$. The trees are optimized using a Poisson objective function to directly output expected goals (lambdas) minimizing Poisson log-loss:

$$
Loss(Y, \hat{\lambda}) = - \sum_{k} (Y_k \log \hat{\lambda}_k - \hat{\lambda}_k)
$$

The individual expectations yield independent Poisson goals distributions:

$$
P(X=x, Y=y) = \text{poisson.pmf}(x, \hat{\lambda}_{home}) \times \text{poisson.pmf}(y, \hat{\lambda}_{away})
$$

### Operational Breakdown
*   **Why We Use It (Rationale)**: Traditional Poisson models (M1, M2, M3) assume log-linear relationships between ratings and goals. However, the true impact of team ratings differences on goal scoring is non-linear (e.g. a $200$-point Elo gap might scale scoring expectations exponentially up to a threshold, then plateau). LightGBM captures these non-linear boundaries natively.
*   **Pros**:
    *   **Non-linear Interaction**: Handles thresholds and conditional plateaus automatically.
    *   **No Parametric Assumptions**: Does not require manual link functions to scale rating gaps.
*   **Cons**:
    *   **Black-Box Trees**: Individual predictions lack direct coefficient interpretations.
    *   **Out-of-Bounds Extremes**: Fails on massive rating gaps that fall outside the historical training limits, sometimes producing highly volatile outputs.
*   **Data Requirements & Schema**:
    *   Queries Elo tables and normalized fixtures.
    *   Required fields: `elo_home`, `elo_away`, `neutral`, `home_score`, `away_score`.
*   **Football Failure Modes**:
    *   **Historical Imbalance**: In rare matchups (e.g., Elo diff exceeding $600$ points), LightGBM trees may output uncalibrated probabilities because it has never seen a similar split.

---

## 6. M6: Market-Implied Bivariate Poisson (`market_implied.py`)

Rather than looking at historical stats, M6 solves for the statistical parameters $\lambda$ and $\mu$ that minimize the discrepancy with live exchange pricing (1X2 Polymarket/Kalshi probabilities).

### De-vigged Optimization
We extract the target de-vigged market probabilities for Home Win ($T_H$), Draw ($T_D$), and Away Win ($T_A$). We then run an L-BFGS-B optimization to find the parameters $\lambda, \mu$ that satisfy:

$$
\min_{\lambda, \mu} \left( (P_{Home}(\lambda, \mu) - T_H)^2 + (P_{Draw}(\lambda, \mu) - T_D)^2 + (P_{Away}(\lambda, \mu) - T_A)^2 \right)
$$

Where $P_c$ are the computed probabilities derived from the Bivariate Poisson matrix. This allows us to convert raw 3-way moneyline pricing into a full 15x15 scoreline matrix.

### Operational Breakdown
*   **Why We Use It (Rationale)**: Market pricing represents the consensus belief of all participants (incorporating news, injuries, and weather). M6 acts as a market anchor. If our statistical models differ from the market-implied score distribution, M6 tells us *what the market expects* so we can calculate exact edges on complex side markets (e.g. Exact Scoreline, Over/Under, Handicap).
*   **Pros**:
    *   **Consensus Anchor**: Represents the sum of all market information.
    *   **Arbitrage Base**: Crucial for mapping 3-way moneyline contracts to complex derivative contracts coherently.
*   **Cons**:
    *   **No Independent Signal**: Does not generate its own alpha; completely dependent on the quality and liquidity of the primary market.
*   **Data Requirements & Schema**:
    *   Requires active real-time WebSocket or REST orderbook feeds from Kalshi or Polymarket.
    *   Required fields: `market_p_home`, `market_p_draw`, `market_p_away`.
*   **Football Failure Modes**:
    *   **Illiquid Markets**: In low-liquidity matches, wide spreads or manipulation can distort target probabilities, causing M6 to output completely uncalibrated score matrices.

---

## 7. Meta-Model Ensembler (`meta_ensemble.py`)

We combine M1, M2, M3, M4, M5, and M6 dynamically. The ensembler splits the data into a training set and a hold-out validation set.

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
