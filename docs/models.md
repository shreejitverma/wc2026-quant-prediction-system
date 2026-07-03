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

> **One-line summary**: Fit attack/defense strengths to thousands of historical match results, then use the Poisson formula to compute the exact probability of every possible scoreline.

### 1.1 Intuition: Why Poisson?

**Analogy**: Imagine you are counting the number of buses that arrive at a bus stop in any 90-minute window. On average, 2 buses come per hour. But some windows see 0 buses, some see 1, and occasionally 4 arrive at once. This count — *rare, discrete events at a known average rate in a fixed time window* — is what the **Poisson distribution** was designed to model.

Football goals are statistically identical to buses:
- Goals are rare (average ~2.7 per match across all football).
- Goals happen at random moments independent of each other (scoring at minute 15 doesn't change the clock for minute 50).
- We have a model-estimated average rate (the expected goals, λ or μ).

The key insight of Dixon & Coles (1997) is that pure Poisson slightly *underpredicts* low-scoring results (0-0 draws, 1-0 wins). Empirically these happen ~8-12% more often than Poisson predicts — a real phenomenon caused by *score-dependent tactics* (a team winning 1-0 will play more defensively, suppressing both the home and away scoring rate). Dixon-Coles adds a tiny mathematical correction for this.

### 1.2 Model Parameters: Attack & Defense Ratings

Every team $i$ in the database is assigned two latent parameters:
- **$\alpha_i$ (Attack Strength)**: How many goals this team scores relative to the global average. $\alpha = 1.0$ is exactly average; $\alpha = 1.4$ means 40% more than average.
- **$\beta_i$ (Defense Weakness)**: How many goals this team concedes relative to the global average. $\beta = 1.0$ is average; $\beta = 0.7$ means conceding 30% fewer than average.

**Identifiability constraint** (important!): Without a constraint, infinite pairs of $(\alpha, \beta)$ can explain the same data (you can double all attacks and halve all defenses and get the same result). We enforce:

$$
\frac{1}{N} \sum_{i=1}^{N} \alpha_i = 1.0 \quad \text{(global average attack = 1)}
$$

### 1.3 Match-Specific Expected Goals

When Team $i$ (home) plays Team $j$ (away):

$$
\lambda = \alpha_i \times \beta_j \times \gamma
$$

$$
\mu = \alpha_j \times \beta_i
$$

- $\lambda$ = expected goals for the home team
- $\mu$ = expected goals for the away team  
- $\gamma$ = home advantage multiplier (typically 1.15–1.35, set to 1.0 on neutral venues)

**Worked example — Brazil (α=1.45, β=0.80) vs France (α=1.35, β=0.85), neutral venue:**

$$
\lambda_{Brazil} = 1.45 \times 0.85 \times 1.0 = 1.233
$$

$$
\mu_{France} = 1.35 \times 0.80 \times 1.0 = 1.080
$$

### 1.4 Base Poisson Probability Matrix

The probability of Brazil scoring exactly $x$ goals and France scoring exactly $y$ goals, assuming *independence*:

$$
P(X=x, Y=y) = \underbrace{\frac{e^{-\lambda} \lambda^x}{x!}}_{\text{Brazil's Poisson}} \times \underbrace{\frac{e^{-\mu} \mu^y}{y!}}_{\text{France's Poisson}}
$$

**Worked example — Probability of the 1-1 draw:**

$$
P(\text{Brazil}=1) = \frac{e^{-1.233} \times 1.233^1}{1!} = \frac{0.2914 \times 1.233}{1} = 0.3594
$$

$$
P(\text{France}=1) = \frac{e^{-1.080} \times 1.080^1}{1!} = \frac{0.3396 \times 1.080}{1} = 0.3667
$$

$$
P(\text{1-1 draw}) = 0.3594 \times 0.3667 = 13.18\%
$$

This calculation is performed for **all 225 cells** (0-14 × 0-14), producing the full ScoreDist matrix.

### 1.5 The Low-Score Dependence Correction ($\tau$)

Pure Poisson assumes independence. But real football shows a slight correlation: teams with a 1-0 lead slow down, suppressing the probability of high-scoring finishes. Dixon-Coles introduce a single correlation parameter $\rho$ (empirically around $-0.13$) to correct the four lowest-scoring cells:

$$
\tau_{\lambda,\mu}(x, y) =
\begin{cases}
1 - \lambda\mu\rho & x=0, y=0 \quad \text{(e.g., } 1 - 1.233 \times 1.080 \times (-0.13) = 1.173 \text{ → boosts 0-0)}\\
1 + \lambda\rho & x=0, y=1 \quad \text{(adjusts 0-1)}\\
1 + \mu\rho & x=1, y=0 \quad \text{(adjusts 1-0)}\\
1 - \rho & x=1, y=1 \quad \text{(adjusts 1-1)}\\
1 & \text{otherwise} \quad \text{(no change for } x+y \geq 3\text{)}
\end{cases}
$$

The final adjusted probability:

$$
P_{\text{adjusted}}(X=x, Y=y) = P(X=x, Y=y) \times \tau_{\lambda,\mu}(x, y)
$$

**The matrix must be renormalized** after applying $\tau$ so all cells still sum to exactly 1.0.

### 1.6 Exponential Time Decay

Not all historical matches are equally informative. A match from 5 years ago tells us less about today's team than a match from 3 weeks ago. We apply an **exponential time-decay weight** to each historical match when fitting the model:

$$
w(t) = e^{-\xi \cdot \Delta t}
$$

Where:
- $\Delta t$ = number of days between the match and today
- $\xi = 0.004$ (the decay rate, calibrated to give a half-life of $\ln(2)/0.004 \approx 173$ days)

This means a match from 6 months ago (≈180 days) carries roughly **half** the weight of a match played today.

**Why 173 days?** That's approximately one competitive international break cycle. After 6 months, coaching changes, fitness states, and squad evolution make old results progressively less predictive.

### 1.7 Maximum Likelihood Estimation (MLE): How Parameters Are Fitted

We find the $\{\alpha_i, \beta_i, \gamma, \rho\}$ that maximize the weighted log-likelihood of observing all historical match results:

$$
\mathcal{L}(\theta) = \sum_{\text{matches}} w(t) \cdot \log P_{\text{adjusted}}(X=x, Y=y \;|\; \theta)
$$

In practice, we **minimize the negative log-likelihood** (equivalent mathematically) using the `scipy.optimize.minimize` L-BFGS-B algorithm. L-BFGS-B is ideal because:
- It handles hundreds of parameters (one $\alpha$ and $\beta$ per team) efficiently.
- It respects box constraints (e.g., $\alpha_i > 0$ always).
- It converges in milliseconds on a laptop.

### 1.8 Operational Summary

| Aspect | Detail |
|--------|--------|
| **Primary Use** | Structural baseline ScoreDist for all matches; the "prior" model |
| **Input** | Historical results: `date`, `home_team`, `away_team`, `home_score`, `away_score`, `neutral` |
| **Output** | 15×15 `ScoreDist` matrix + fitted $\{\alpha, \beta, \gamma, \rho\}$ |
| **Speed** | Milliseconds (L-BFGS-B on ~5,000 international matches) |
| **Refit frequency** | After every new match played |

**Pros:**
- Computationally efficient; parameters are directly interpretable.
- The $\rho$ correction makes it specifically accurate for low-scoring draws.
- Time-decay ensures recent form is weighted appropriately.

**Cons:**
- Statically integrates all historical data — cannot respond to *real-time* within-game events.
- Requires the identifiability normalization constraint to prevent parameter drift.

**Critical Failure Modes:**

| Scenario | Why M1 Fails | Mitigation |
|----------|-------------|-----------|
| **Early red card (5th minute)** | M1's $\beta$ parameter was estimated from full-strength historical matches; a 10-vs-11 match is a different game entirely | Down-weight M1; activate M4 with amended lineup if available |
| **"Dead rubber" group matches** | Team A is already qualified, plays reserves. M1's $\alpha$ reflects the first-team squad, not the reserves | Flag dead-rubber status; reduce M1 weight; use M5 (which may pick up motivation signals via Elo features) |
| **Newly qualified nation** | A team plays their first-ever WC. M1 has <5 matches in the dataset — extremely noisy $\alpha/\beta$ estimates | Fall back to M3 (Bayesian hierarchical shrinkage) as primary |

---

## 2. M2: Dynamic State-Space Filter (`state_space.py`)

> **One-line summary**: Update team strength ratings after every match like a GPS constantly recalculating direction — instantly responsive to new information, not waiting for a full refit.

### 2.1 Intuition: The Elo Filter in xG-Space

**Analogy**: The Elo chess rating system updates a player's rating after every game: win = rating goes up, lose = rating goes down, by an amount proportional to how surprising the result was. We do the same thing, but instead of tracking "who won," we track *exactly how many goals were scored and conceded* relative to expectations. This gives us a much more information-rich signal than just win/loss/draw.

The fundamental difference from M1:
- **M1** fits the entire history simultaneously (like computing a career batting average). Slow to react to a recent hot streak.
- **M2** updates ratings sequentially match-by-match (like a live batting average that updates after every at-bat). Instantly reactive, but noisier.

### 2.2 State Representation

Each team maintains two continuously-updated state variables:
- **$Att_i^{(t)}$**: The team's attack rating after $t$ matches (in log-space, so values typically in the range $[-0.5, +0.5]$)
- **$Def_i^{(t)}$**: The team's defensive rating after $t$ matches

The predicted match goals use a log-link function (ensuring predictions are always positive):

$$
\lambda_{home}^{(t)} = \exp\!\left(Att_{home}^{(t)} - Def_{away}^{(t)} + H_{adv}\right)
$$

$$
\lambda_{away}^{(t)} = \exp\!\left(Att_{away}^{(t)} - Def_{home}^{(t)}\right)
$$

**Why log-space?** The exponential ensures predictions are always positive (you can't score a negative number of goals). It also means rating differences are multiplicative: a difference of 0.18 in log-space corresponds to a factor of $e^{0.18} \approx 1.20$ — a 20% advantage.

### 2.3 The Gradient Descent Update Rule

After observing the actual match result (Home: $g_h$ goals, Away: $g_a$ goals), we update the four ratings involved:

The gradient of the Poisson log-likelihood with respect to $\log(\lambda)$ is elegantly simple:

$$
\frac{\partial \log P(g | \lambda)}{\partial \log \lambda} = g - \lambda \quad \text{(actual goals minus expected goals)}
$$

This is the **residual error** — if we expected 1.5 goals but saw 3, the residual is $+1.5$, meaning the attack was better than estimated. We apply a gradient step:

$$
Att_{home}^{(t+1)} = Att_{home}^{(t)} + \alpha_{\text{lr}} \cdot (g_h - \lambda_{home}^{(t)})
$$

$$
Def_{away}^{(t+1)} = Def_{away}^{(t)} - \alpha_{\text{lr}} \cdot (g_h - \lambda_{home}^{(t)})
$$

$$
Att_{away}^{(t+1)} = Att_{away}^{(t)} + \alpha_{\text{lr}} \cdot (g_a - \lambda_{away}^{(t)})
$$

$$
Def_{home}^{(t+1)} = Def_{home}^{(t)} - \alpha_{\text{lr}} \cdot (g_a - \lambda_{away}^{(t)})
$$

Where $\alpha_{\text{lr}} \approx 0.05$ is the **learning rate** hyperparameter.

**Worked example — Brazil (Att=0.37, Def=-0.22) vs Saudi Arabia (Att=-0.30, Def=0.14), match result: 3-0:**

Pre-match predictions:
$$\lambda_{Brazil} = e^{0.37 - 0.14} = e^{0.23} = 1.259 \text{ expected goals}$$
$$\lambda_{Saudi} = e^{-0.30 - (-0.22)} = e^{-0.08} = 0.923 \text{ expected goals}$$

Residuals: Brazil $= 3 - 1.259 = +1.741$. Saudi $= 0 - 0.923 = -0.923$.

Post-match updates ($\alpha_{\text{lr}} = 0.05$):
$$Att_{Brazil}^{\text{new}} = 0.37 + 0.05 \times 1.741 = 0.37 + 0.087 = 0.457$$
$$Def_{Saudi}^{\text{new}} = 0.14 - 0.05 \times 1.741 = 0.14 - 0.087 = 0.053$$

Brazil's attack rating jumped from 0.37 to 0.457; Saudi Arabia's defense became visibly weaker.

### 2.4 Learning Rate Sensitivity

The learning rate $\alpha_{\text{lr}}$ controls the speed/noise tradeoff:
- **Too high** ($\alpha > 0.15$): Ratings overreact to single matches (a 5-0 thrashing permanently corrupts ratings).
- **Too low** ($\alpha < 0.01$): Ratings are slow-moving and don't capture genuine momentum shifts.
- **Optimal range** (~0.03–0.08): Validated on historical tournament data by minimizing Brier Score on out-of-sample matches.

### 2.5 Operational Summary

| Aspect | Detail |
|--------|--------|
| **Primary Use** | Capturing recent form, momentum, and manager-change effects |
| **Input** | Chronologically ordered results sequence |
| **Output** | 15×15 `ScoreDist` matrix derived from current state ratings |
| **Speed** | Sub-millisecond per match update |
| **Refit frequency** | Updated after every completed match (real-time in live mode) |

**Pros:**
- Immediately reflects a recent 5-1 destruction of a strong team.
- Low computational footprint — no refit needed, just an O(1) update.

**Cons:**
- High variance — outlier scorelines (e.g., a 7-1 "basketball score" caused by a goalkeeper injury) corrupt ratings.
- Cold start: a team with 0 historical matches starts at the global average and requires ~10 matches to reach stable ratings.

**Critical Failure Modes:**

| Scenario | Why M2 Fails | Mitigation |
|----------|-------------|-----------|
| **Statistical outlier result** | Germany's 7-1 win over Brazil (2014) would massively inflate Germany's attack rating | Apply a score cap: treat any result with $\|g - \lambda\| > 4$ as capped at 4 |
| **Friendly matches** | M2 updates ratings for all results equally, so a 10-0 friendly win inflates attack ratings | Pre-filter: only include competitive (official FIFA) matches in the update sequence |
| **Post-breakup of "golden generation"** | M2's ratings reflect the golden generation's form; the new squad plays nothing like them | Combine with M3 (which applies hierarchical shrinkage toward the global mean for rapidly changing squads) |

---

## 3. M3: Bayesian Hierarchical Goals (`hierarchical.py`)

> **One-line summary**: Use Bayesian statistics to estimate team strengths with built-in "skepticism" — preventing wild overreactions to small sample sizes by pulling estimates toward the global average.

### 3.1 Intuition: The Rookie Problem

**Analogy**: A basketball scout evaluates a rookie who hits 5 of his first 8 three-point attempts in his debut. Naively, you'd estimate his three-point percentage at 62.5%. But an experienced scout knows this is a small sample and the true rate is probably closer to 40-50%. The scout applies "skepticism" — pulling the rookie estimate toward the league average.

This skepticism is exactly what **Bayesian hierarchical modeling** provides, encoded mathematically through **priors**.

International football is the perfect use case: international teams play only 6-8 competitive matches per year. A 3-game World Cup group stage is an impossibly small sample to estimate attack and defense strength without structural skepticism.

### 3.2 The Hierarchical Model Structure

**Level 1 — Global Parameters (Hyperpriors):**
These capture the *overall distribution of team strength* across all teams:

$$
\sigma_{att} \sim \text{HalfNormal}(0.5) \qquad \text{(how much do teams' attacks vary?)}
$$

$$
\sigma_{def} \sim \text{HalfNormal}(0.5) \qquad \text{(how much do teams' defenses vary?)}
$$

A $\text{HalfNormal}(0.5)$ prior says: "I expect team strength to cluster within ~0 to +0.5 of the mean, but I'll allow the data to show me if it's wider or tighter."

**Level 2 — Team-Level Parameters:**
Each team's strengths are drawn from the global distribution:

$$
Att_i \sim \mathcal{N}(0, \sigma_{att}) \quad \forall \text{ teams } i
$$

$$
Def_i \sim \mathcal{N}(0, \sigma_{def}) \quad \forall \text{ teams } i
$$

**Level 3 — Global Intercept & Home Advantage:**

$$
\text{Intercept} \sim \mathcal{N}(1.0, 0.5) \qquad \text{(encodes average scoring rate, e.g., } e^{1.0} \approx 2.7\text{ goals/game)}
$$

$$
H_{adv} \sim \mathcal{N}(0.2, 0.2) \qquad \text{(home advantage adds } e^{0.2} - 1 \approx 22\%\text{ more goals)}
$$

**Identifiability:** We enforce a soft sum-to-zero constraint on attack and defense parameters:
$$
\sum_i Att_i \approx 0 \quad \text{and} \quad \sum_i Def_i \approx 0
$$

### 3.3 The Log-Link Function

Expected goals are computed via a log-link function (identical to M2's approach but on a full Bayesian posterior):

$$
\theta_{home} = \exp(\text{Intercept} + H_{adv} + Att_{home} - Def_{away})
$$

$$
\theta_{away} = \exp(\text{Intercept} + Att_{away} - Def_{home})
$$

The observed goals are modeled as Poisson-distributed:

$$
g_{home} \sim \text{Poisson}(\theta_{home})
$$

$$
g_{away} \sim \text{Poisson}(\theta_{away})
$$

### 3.4 NUTS MCMC Sampling

Instead of finding a single "best-fit" parameter value (like M1 does), M3 samples the **full posterior distribution** using the **No-U-Turn Sampler (NUTS)** via the `numpyro` library (JAX-accelerated).

**What does this mean practically?** Instead of outputting "Brazil's attack is 1.45," M3 outputs:
```
Brazil's attack = [1.38, 1.44, 1.51, 1.39, 1.47, 1.42, ...] (2000 samples)
```

These samples represent the *full uncertainty* in the estimate. When we generate predictions, we propagate this uncertainty through to the `ScoreDist` matrix:
- Draw one $Att_{Brazil}$, one $Def_{France}$ sample → compute $\theta_{home}$ → simulate goals.
- Repeat 2,000 times → empirical 2D probability distribution.

The result is a `ScoreDist` matrix that *includes* the uncertainty about team strengths, not just the uncertainty from Poisson sampling. This makes M3's tail probability estimates more reliable than M1's.

### 3.5 The Shrinkage Effect (Key Differentiator)

The hierarchical prior pulls extreme estimates toward zero (the mean). This is most visible for teams with small sample sizes:

| Team | Matches in DB | M1 Attack Estimate | M3 Attack Estimate | Why Different |
|------|--------------|---------------------|---------------------|--------------|
| Brazil | 850 | 1.45 | 1.43 | Large sample — both agree |
| Morocco | 280 | 1.12 | 1.09 | Medium sample — minor shrinkage |
| **Panama** | **38** | **1.52** | **1.18** | Small sample — heavy shrinkage! |

Panama's M1 estimate of 1.52 would imply they are stronger than Brazil — almost certainly noise from a few outlier results. M3's shrinkage correctly pulls this toward plausibility.

### 3.6 Operational Summary

| Aspect | Detail |
|--------|--------|
| **Primary Use** | Uncertainty-aware predictions; dominant for teams with sparse history |
| **Input** | Historical results mapped to team integer index dictionaries |
| **Output** | 15×15 `ScoreDist` matrix from predictive posterior samples |
| **Speed** | ~45 seconds MCMC warmup + 30 seconds sampling on CPU |
| **Refit frequency** | Daily (cached; real-time refit not feasible) |

**Pros:**
- Full uncertainty quantification — critical for pricing tail-risk contracts.
- Structural protection against overfitting on small samples (e.g., 3-game group stage history).

**Cons:**
- MCMC warmup cost makes real-time repricing impossible.
- Slow to respond to rapid form changes (priors dampen reactions to isolated shock results).

**Critical Failure Modes:**

| Scenario | Why M3 Fails | Mitigation |
|----------|-------------|-----------|
| **Rapid rise of a "golden generation"** | Prior shrinks the surprising new strength back toward historical average | Supplement with M2 (no shrinkage, responsive to recent form) in the ensemble |
| **In-play repricing needed** | MCMC cannot run in 2 seconds | Cache M3 output; use M1/M2 for real-time adjustments |

---

## 4. M4: Player-Aggregation (`player_agg.py`)

> **One-line summary**: Build the team's expected goals from the *bottom up*, player by player, from their individual club statistics. When the lineup is announced, M4 immediately reflects who is actually playing.

### 4.1 Intuition: The Fantasy Football Approach

**Analogy**: Fantasy football managers know that the team is the sum of its players. If your team's best striker is injured, your fantasy team's score drops immediately — you don't wait three more games to update your projection. M4 applies this same logic to tournament prediction.

Models M1, M2, and M3 all treat a national team as a **single entity** with a rating. They are blind to *who* is playing. If Kylian Mbappé is injured, these models still predict France's expected goals using France's historical team-level statistics. M4 directly models the player composition.

### 4.2 The Bottom-Up xG Aggregation Formula

For each player $p$ in the confirmed starting XI, we fetch their **rolling club-level statistics scaled per 90 minutes of play** (xG per 90, xA per 90, from FBref/StatsBomb):

$$
\lambda_{team} = \left( \sum_{p \in \text{StartingXI}} xG_{90,p} + xA_{90,p} \right) \times \psi_{team}
$$

Where:
- $xG_{90,p}$ = Expected Goals per 90 minutes for player $p$ (a quantification of shot quality and volume, not just whether the shots went in)
- $xA_{90,p}$ = Expected Assists per 90 minutes (a player who creates many high-quality chances contributes to expected goals even if they don't take them)
- $\psi_{team}$ = **Competition level adjustment factor** — a multiplier that adjusts for the step-up from club leagues to the World Cup

### 4.3 The Competition Level Adjustment ($\psi$)

Club statistics are measured in varying leagues. A La Liga striker's numbers are more predictive of World Cup performance than an MLS striker's because the La Liga is closer in quality to international football.

We compute $\psi$ using a **league-to-international quality mapping**:

| League | Quality Multiplier |
|--------|------------------|
| Champions League / Premier League | 0.95 (slight step-up to international) |
| La Liga / Bundesliga / Serie A | 0.90 |
| Ligue 1 / Eredivisie / CONCACAF | 0.80 |
| MLS / South American domestic | 0.75 |
| Other domestic leagues | 0.65 |

The $\psi_{team}$ for the whole team is the minutes-weighted average of its players' $\psi$ values.

### 4.4 The Lineup Timing Window (Critical Design Decision)

M4 is **inactive by default** until a confirmed lineup is released. This is a deliberate design choice:

```
Timeline:
T-12h: Expected lineup published by media → M4 runs with ~75% weight (uncertain)
T-60m: Official lineup confirmed on FA/FIFA app → M4 runs with ~85% weight (high confidence)
T-0:   Kickoff → M4 weight fixed; in-play M1/M2 dominate thereafter
T+90m: Full-time → M4 deactivated for next cycle
```

The Meta-Ensembler checks `lineup_confirmed` (boolean from the feature store) to determine M4's weight. Before lineup confirmation, M4 runs on *expected* lineups from beat journalists with uncertainty scaling.

### 4.5 Worked Example

Assume France's starting XI against Brazil:

| Player | xG/90 | xA/90 | League | ψ |
|--------|-------|-------|--------|---|
| Mbappé | 0.78 | 0.31 | PSG → Ligue 1 | 0.80 |
| Benzema | 0.62 | 0.24 | Real Madrid | 0.90 |
| Griezmann | 0.43 | 0.35 | Atletico | 0.90 |
| Dembélé | 0.31 | 0.38 | PSG → Ligue 1 | 0.80 |
| *7 defenders + GK* | *0.05 avg* | *0.02 avg* | *Mixed* | *0.82 avg* |

**Total xG+xA per 90 = sum over all 11 players ≈ 3.21 (raw)**

**Team ψ** (minutes-weighted average) ≈ 0.86

$$
\lambda_{France} = 3.21 \times 0.86 = 2.76 \text{ (pre-normalization)}
$$

But wait — this number seems high! The reason is that xG+xA counts include *assists to shots that someone else also counts*. We apply a double-counting correction: each player's xA contribution is weighted by the fraction of team shots that this player's assists feed.

After normalization, $\lambda_{France} \approx 1.45$, which is broadly consistent with M1's estimate — a good sanity check that the model is in the right ballpark.

### 4.6 Operational Summary

| Aspect | Detail |
|--------|--------|
| **Primary Use** | Lineup-sensitive repricing 60-75 minutes before kickoff |
| **Input** | Confirmed/expected XI + player-level xG/xA stats from FBref |
| **Output** | 15×15 `ScoreDist` matrix conditional on confirmed lineup |
| **Speed** | Sub-second (simple arithmetic, no optimization) |
| **Refit frequency** | Triggered by lineup confirmation event |

**Pros:**
- The *only* model that immediately responds to lineup news.
- Directly captures the effect of a star player's absence.

**Cons:**
- Entirely dependent on accurate, timely lineup data — wrong lineup = wrong prediction.
- Cannot capture *tactical* effects (e.g., a conservative 5-4-1 vs an attacking 4-3-3 with the same players).

**Critical Failure Modes:**

| Scenario | Why M4 Fails | Mitigation |
|----------|-------------|-----------|
| **Out-of-position players** | A midfielder filling in at center-back has high xG/xA but terrible defensive metrics — M4 will overstate attack and miss defensive weakness | Tag positional displacement in lineup parser; apply penalty multiplier |
| **International debut players** | No club stats available → M4 defaults to positional average, which may be very wrong for exceptional talents | Supplement with historical youth tournament data; flag high-uncertainty M4 outputs |
| **Wrong media lineup** | Beat journalist reported expected lineup was wrong → M4 ran on incorrect data | Always wait for *official* confirmed lineup before maximum M4 weighting |

---

## 5. M5: LightGBM Gradient Boosting (`gbm.py`)

> **One-line summary**: Feed a machine-learning tree model a rich feature matrix (Elo gap, home advantage, rest days, altitude) and let it learn non-linear patterns that standard Poisson models miss.

### 5.1 Intuition: Why Trees?

**Analogy**: A Poisson model assumes "the bigger the rating gap, the more goals by the stronger team — proportionally forever." But reality is non-linear: a 200-point Elo gap produces far fewer extra goals than a 400-point gap. Beyond 500 points, the superior team is essentially guaranteed to win regardless — doubling the gap doesn't double the goals. Decision trees naturally learn these **threshold effects and plateaus**.

The key limitation of M1, M2, M3: they assume the relationship between ratings and goals is **log-linear**:

$$
\lambda = \exp(\alpha - \beta + \text{constant})
$$

This is a strong parametric assumption. LightGBM makes *no parametric assumption* — it discovers the functional form empirically from data.

### 5.2 Feature Engineering

Each match is flattened into a **feature vector** representing both teams simultaneously:

$$
\mathbf{X}_i = [\text{elo\_diff},\; \text{is\_home},\; \text{neutral},\; \text{rest\_days\_home},\; \text{rest\_days\_away},\; \text{altitude\_m},\; \text{temp\_celsius}]
$$

Where:
- $\text{elo\_diff} = \text{Elo}_{team} - \text{Elo}_{opponent}$: The Elo rating gap (a single number capturing relative strength)
- $\text{is\_home}$: Binary flag (0/1)
- $\text{neutral}$: Binary flag (0/1) — overrides home
- $\text{rest\_days}$: Days since last competitive match (fatigue proxy)
- $\text{altitude\_m}$: Venue altitude in meters (affects stamina and goal rates)
- $\text{temp\_celsius}$: Temperature at kickoff (extreme heat reduces scoring)

The training set is built by creating **two rows per match** — one for the home team, one for the away team — each with their respective features and the target variable being their goals scored in that match.

### 5.3 The Poisson Objective Function

LightGBM is trained with a **Poisson regression objective**, which maximizes Poisson log-likelihood:

$$
\mathcal{L}(y, \hat{\lambda}) = \sum_{k=1}^{N} \left( y_k \log \hat{\lambda}_k - \hat{\lambda}_k - \log(y_k!) \right)
$$

The final leaf values output $\hat{\lambda}$ — the predicted expected goals for that team in that match. This is then used to generate the ScoreDist matrix:

$$
P(X=x, Y=y) = \text{Poisson}(x; \hat{\lambda}_{home}) \times \text{Poisson}(y; \hat{\lambda}_{away})
$$

(Note: M5 does not apply the Dixon-Coles τ correction — that is M1's speciality.)

### 5.4 Key Hyperparameters

| Parameter | Value | Why |
|-----------|-------|-----|
| `objective` | `poisson` | Direct Poisson loss — outputs goals, not probabilities |
| `n_estimators` | 200 | More trees = more complex patterns; 200 is sufficient for this feature set |
| `max_depth` | 4 | Shallow trees generalize better with limited data |
| `learning_rate` | 0.05 | Small steps prevent overfitting |
| `num_leaves` | 31 | Controls leaf granularity |
| `reg_lambda` | 1.0 | L2 regularization — prevents trees from memorizing noise |

### 5.5 What M5 Captures That Others Miss

**Example: High Altitude Effect**

At La Paz, Bolivia (3,640m altitude), home teams score dramatically more goals than at sea level due to:
- Visiting teams' cardiovascular systems struggling to process oxygen.
- Home team's physical adaptation advantage.

In M1's log-linear model, altitude is not a feature — only attack/defense ratings matter. M5 learns a **threshold**: altitude below 1,000m has negligible effect; altitude above 2,500m has a significant multiplicative effect on the home expected goals. This is a classic interaction effect that trees capture and log-linear models miss.

**Example: Rest Days Interaction**

M1 ignores rest days completely. M5 discovers: teams with ≤3 rest days score 12% fewer goals on average. But this effect is stronger for teams already rated as "physically demanding" styles (high-press, high-tempo). This is a **non-linear interaction** that only tree models can represent naturally.

### 5.6 Operational Summary

| Aspect | Detail |
|--------|--------|
| **Primary Use** | Non-linear feature interaction capture; venue/fatigue/weather modeling |
| **Input** | Feature matrix: Elo ratings, rest days, altitude, temperature, neutral flag |
| **Output** | $\hat{\lambda}_{home}$, $\hat{\lambda}_{away}$ → 15×15 `ScoreDist` |
| **Speed** | ~1ms inference; ~30s training on full historical dataset |
| **Refit frequency** | Weekly; re-triggered if a new Elo rating batch arrives |

**Pros:**
- Captures non-linear threshold effects and multi-variable interactions.
- No parametric assumptions — discovers the true function shape from data.
- Can incorporate arbitrary new features (weather, venue surface, referee stats) with zero code changes.

**Cons:**
- Black-box: individual tree decisions are not interpretable like regression coefficients.
- Out-of-distribution: extreme Elo gaps (never seen in training) produce uncalibrated predictions.
- Requires careful cross-validation to prevent overfitting.

---

## 6. M6: Market-Implied Bivariate Poisson (`market_implied.py`)

> **One-line summary**: Work backwards from the live market prices — if the market says 35% home win, what values of λ and μ would produce that, and what does *that* imply about Over/Under and exact scoreline markets?

### 6.1 Intuition: The Market as a Summarizer

**Analogy**: Imagine a brilliant friend who has already synthesized every newspaper article, injury report, weather forecast, and squad statistic for the match — but they will only tell you three numbers: the probability of a home win, draw, and away win. From these three numbers, can you reconstruct what they know about the full scoreline distribution?

M6 answers: **yes, approximately**. If you assume the market-implied 1X2 probabilities come from a Bivariate Poisson distribution (which is a reasonable assumption), then there is a unique pair (λ*, μ*) that produces exactly those three probabilities. We solve for (λ*, μ*) using numerical optimization.

The result is a full 15×15 `ScoreDist` matrix that is *consistent* with the market's 1X2 prices.

### 6.2 The De-Vigging Step

Prediction markets (and bookmakers) embed a **vig** (overround) — the exchange's profit margin. A bookmaker might price a match at:

| Outcome | Bookmaker Odds | Raw Probability |
|---------|---------------|-----------------|
| Home Win | 2.10 | 1/2.10 = 47.6% |
| Draw | 3.40 | 1/3.40 = 29.4% |
| Away Win | 3.60 | 1/3.60 = 27.8% |
| **Total** | — | **104.8%** |

The 4.8% overround is the vig. We normalize to remove it:

$$
P_{home}^{de-vig} = \frac{1/2.10}{1/2.10 + 1/3.40 + 1/3.60} = \frac{0.476}{1.048} = 45.4\%
$$

Similarly: $P_{draw}^{de-vig} = 28.1\%$ and $P_{away}^{de-vig} = 26.5\%$.

These de-vigged probabilities are our **target** for the optimization.

### 6.3 The L-BFGS-B Optimization

We solve for the parameters $(\lambda^*, \mu^*)$ that minimize the sum of squared errors between the market-implied probabilities and our model-computed probabilities:

$$
\min_{\lambda^*, \mu^* > 0} \left[ (P_{H}(\lambda^*, \mu^*) - T_H)^2 + (P_{D}(\lambda^*, \mu^*) - T_D)^2 + (P_{A}(\lambda^*, \mu^*) - T_A)^2 \right]
$$

Where:
- $P_H(\lambda, \mu) = \sum_{x > y} P(X=x, Y=y)$ — derived from Bivariate Poisson matrix
- $T_H, T_D, T_A$ — the de-vigged target probabilities

The L-BFGS-B optimizer finds the solution in ~50 iterations (milliseconds).

**Worked example:**

Target: Home Win 45.4%, Draw 28.1%, Away Win 26.5%

L-BFGS-B finds: $\lambda^* = 1.52$, $\mu^* = 1.18$

**Verification:** Computing the ScoreDist with these values:
- $P_{home}(\lambda=1.52, \mu=1.18) = 45.2\%$ ✓ (matches 45.4% within rounding)
- $P_{draw} = 27.9\%$ ✓
- $P_{away} = 26.9\%$ ✓

Now this ($\lambda^*=1.52$, $\mu^*=1.18$) is used to generate the full 15×15 ScoreDist, which we can use to price **any** market derived from the scoreline distribution — including exact scoreline, Over/Under 1.5/2.5/3.5, Both Teams to Score, and Asian Handicap contracts.

### 6.4 Why This Creates Value

Consider:
- Market prices Over 2.5 goals at 55%.
- M6's de-inverted ScoreDist implies Over 2.5 goals at 62%.

These two prices are **internally inconsistent**. If the market's 1X2 prices are correct (which M6 uses as inputs), then the Over 2.5 market should be at 62%, not 55%. This 7% discrepancy is a pure coherence-based edge — one that requires no alpha over the market's own beliefs, just consistent mathematics.

### 6.5 Operational Summary

| Aspect | Detail |
|--------|--------|
| **Primary Use** | Market-consistent ScoreDist for coherence pricing of derivative markets |
| **Input** | Live de-vigged 1X2 probabilities from Kalshi/Polymarket/Pinnacle |
| **Output** | 15×15 `ScoreDist` matrix consistent with market's own implied beliefs |
| **Speed** | ~10ms (L-BFGS-B converges quickly) |
| **Refit frequency** | Continuous — repriced every time the orderbook updates |

**Pros:**
- Incorporates all market information (news, injuries, sharp money) in a single implied number.
- Enables coherence-based trading without needing to "out-predict" the market.

**Cons:**
- Circular: M6 reflects market mispricings faithfully — if the 1X2 market is wrong, M6's derived scoreline matrix is also wrong.
- Illiquid markets (wide spreads) produce unstable implied probabilities → uncalibrated ScoreDist.

**Critical Failure Modes:**

| Scenario | Why M6 Fails | Mitigation |
|----------|-------------|-----------|
| **Illiquid early market** | Wide bid-ask spread → de-vigged probabilities noisy | Require minimum liquidity threshold (e.g., $10k notional) before using M6 |
| **Manipulated/spoofed orderbook** | Large spoofed orders temporarily shift implied probabilities | Cross-reference against at least 2 venues; only use M6 when Kalshi + Polymarket agree within 2% |

---

## 7. Meta-Model Ensembler (`meta_ensemble.py`)

> **One-line summary**: Combine all six models into one optimal prediction by learning *which models to trust*, and *when*, based on historical validation.

### 7.1 Intuition: The Expert Committee

**Analogy**: Imagine six doctors each independently diagnosing the same patient. Dr. M1 is very experienced but relies only on long-term history. Dr. M2 focuses on recent trends. Dr. M3 is cautious and always hedges. Dr. M4 knows exactly what the patient ate yesterday (lineup). Dr. M5 uses pattern recognition across thousands of similar cases. Dr. M6 considers what other doctors in the hospital are saying (market consensus).

You don't pick one doctor and ignore the others — you intelligently weight their opinions based on:
1. How reliable each doctor has been historically.
2. Which doctor has the most relevant information *right now*.

This is exactly what the Meta-Ensembler does.

### 7.2 Log-Opinion Pooling (The Preferred Method)

Rather than averaging the six `ScoreDist` matrices directly (Linear Pooling), we use **Log-Opinion Pooling** (geometric mean):

$$
P_{\text{ensemble}}(X=x, Y=y) \propto \exp\!\left(\sum_{m=1}^{6} w_m \log P_m(X=x, Y=y)\right)
$$

This is equivalent to the **geometric weighted mean** of the six probability matrices.

**Why geometric mean instead of arithmetic mean?** The key difference is how they handle model disagreement:

| Situation | Linear Pooling Result | Log-Opinion Result |
|-----------|----------------------|-------------------|
| All models agree: 20% | 20% | 20% |
| 5 models say 20%, 1 model says 0% | **3.3%** (zero only reduces by 1/6) | **0%** (zero veto is hard) |
| 5 models say 20%, 1 model says 50% | 25% (simple average) | 22.4% (geometric dampening) |

The "hard veto" property of Log-Opinion Pooling is *intentional*: if the Bayesian model (M3) assigns 0% probability to an event (because it violates a strong structural prior), we want that to override the other models. An event with 0% probability in a well-calibrated model should not be tradeable as if it has non-zero probability.

### 7.3 Weight Optimization via BFGS

We find the optimal weight vector $\mathbf{w} = (w_1, w_2, w_3, w_4, w_5, w_6)$ subject to $\sum w_m = 1$, $w_m \geq 0$.

The objective function is **Categorical Cross-Entropy Log-Loss** on a held-out validation set:

$$
\mathcal{L}(\mathbf{w}) = -\sum_{i \in \text{validation}} \sum_{c \in \{H, D, A\}} y_{i,c} \log \hat{p}_{i,c}(\mathbf{w})
$$

Where:
- $y_{i,c}$ = 1 if outcome $c$ occurred in match $i$, 0 otherwise
- $\hat{p}_{i,c}(\mathbf{w})$ = ensemble probability of outcome $c$ in match $i$, given weights $\mathbf{w}$

We minimize $\mathcal{L}(\mathbf{w})$ using **BFGS** (Broyden–Fletcher–Goldfarb–Shanno), a quasi-Newton gradient descent algorithm.

**Worked example — Typical converged weights:**

| Model | Weight $w_m$ | Interpretation |
|-------|-------------|---------------|
| M1 (Dixon-Coles) | 0.28 | Reliable baseline — highest single weight |
| M2 (State-Space) | 0.18 | Recent form signal |
| M3 (Bayesian) | 0.22 | Uncertainty quantification; dominant for sparse teams |
| M4 (Player-Agg) | 0.15 | Increases to ~0.40 when lineup confirmed |
| M5 (LightGBM) | 0.10 | Venue/fatigue signal |
| M6 (Market-Implied) | 0.07 | Market anchor; low weight — prevents circular feedback |

**The M4 Surge**: When a confirmed lineup drops, the Meta-Ensembler re-runs BFGS with M4's weight unconstrained from below. In practice, M4 surges to ~0.35-0.45 weight at lineup confirmation, drawing mostly from M1 and M2 which have no new information at that moment.

### 7.4 Context-Aware Weight Scheduling

Beyond just historical performance, the ensembler applies **context rules** to adjust weights:

| Context | Rule | Rationale |
|---------|------|-----------|
| `lineup_confirmed = True` | M4 weight ×2.5 | Best new information at lineup drop |
| `dead_rubber = True` | M1 weight ÷2, M4 weight ÷2 | Squad strength irrelevant when motivation is absent |
| `liquidity_usd < 10000` | M6 weight = 0 | Market-implied signal is noise in illiquid books |
| `team_matches_in_db < 20` | M3 weight ×1.5 | Bayesian shrinkage critical for sparse teams |

### 7.5 Linear vs Log-Opinion Pooling Comparison

| Property | Linear Pooling | Log-Opinion Pooling |
|----------|---------------|---------------------|
| **Formula** | $\sum_m w_m P_m$ | $\propto \exp(\sum_m w_m \log P_m)$ |
| **Type** | Weighted arithmetic mean | Weighted geometric mean |
| **Zero handling** | $P=0$ in one model: others still contribute | $P=0$ in any model: hard veto → ensemble = 0 |
| **Calibration** | Preserves averages; wider tails | Sharper; may understate tail probabilities |
| **Best for** | Smooth blending of similar models | Strong structural priors; tail-risk defense |
| **Our choice** | Secondary option | ✅ **Default** |

### 7.6 Operational Summary

| Aspect | Detail |
|--------|--------|
| **Primary Use** | Produces the single canonical `ScoreDist` used for all pricing |
| **Input** | Six `ScoreDist` matrices from M1–M6 + context flags |
| **Output** | One canonical 15×15 `ScoreDist` + current weight vector |
| **Speed** | ~5ms (BFGS on 6-dimensional weight space) |
| **Refit frequency** | Weights re-optimized weekly on expanding holdout window; context adjustments real-time |

**Pros:**
- Hedges against the specific blind spots of each model.
- Dynamic weight context allows optimal model selection by match lifecycle phase.

**Cons:**
- Log-Opinion veto can produce 0% ensemble probabilities if any model is miscalibrated.
- Black-box in the sense that the ensemble weight is a learned parameter, not a principled first-principles derivation.

**Monitoring Alert**: If any single model's weight exceeds 60%, trigger an alert — this indicates the ensemble has collapsed onto a single model, losing the diversification benefit.

---

## 8. Model Calibration & Validation Framework

> How do we know if our models are actually good? Calibration answers: "when I say 30%, does it happen 30% of the time?"

### 8.1 What is Calibration?

A model is **well-calibrated** if its predicted probabilities match empirical frequencies. If our model says "30% probability of a draw" across 1,000 matches, roughly 300 of those matches should end in draws.

**Calibration Plot**: Plot predicted probability (x-axis, binned in 5% intervals) against observed frequency (y-axis). A perfectly calibrated model's points all lie on the diagonal $y = x$.

Common calibration errors:
- **Overconfident**: Points cluster below the diagonal (model says 80%, only 60% happen).
- **Underconfident**: Points cluster above the diagonal (model says 20%, 35% actually happen).

### 8.2 Evaluation Metrics

| Metric | Formula | Interpretation | Target |
|--------|---------|----------------|--------|
| **Brier Score** | $\frac{1}{N}\sum (p - y)^2$ | Lower = better; 0 = perfect | < 0.20 for 3-outcome markets |
| **Log-Loss** | $-\frac{1}{N}\sum y \log p$ | Lower = better; measures calibration in tails | < 0.85 vs market benchmark |
| **RPS** (Ranked Probability Score) | $\frac{1}{2} \sum (F_i - O_i)^2$ | Rewards "almost right" ordinal predictions | < 0.18 |
| **CLV** (Closing Line Value) | $\text{our price} - \text{closing price}$ | Positive = we predict before the market | > 0.0 over 200+ bets |

### 8.3 The Closing Line Value (CLV) — Why It Matters

CLV is the most important metric for assessing *whether our edge is real or lucky*. It measures whether our fair-value prices are better than the eventual market consensus (closing line):

$$
CLV_i = P_i^{model} - P_i^{close}
$$

If we consistently produce fair values *higher* than the eventual closing price (positive CLV), it means we are identifying mispriced contracts *before* the market corrects them. This is evidence of genuine predictive edge — not just lucky wins.

Over 200+ trades, a $CLV > +0.5\%$ is statistically significant evidence of edge (see pre-registration PR-LIVE-0001).
