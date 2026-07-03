# Pricing, De-vigging, & Market-Making Theory

This document details the mathematical framework for de-vigging market orderbooks, classifying edge types, calculating optimal quoting spreads, and optimizing portfolio positions under inventory risk.

---

## 1. De-vigging Methods

To extract clear consensus probabilities from exchange orderbooks, we must remove the market spread and exchange transaction costs (the "vig"). The system implements three distinct methodologies in `wc2026.features.market_fv`:

### 1.1 Proportional Method

Assumes the vig is distributed proportionally across all contracts:

$$
P_i = \frac{\pi_i}{\sum_{j} \pi_j}
$$

Where $\pi_i$ is the raw market price of contract $i$ (e.g., the midpoint of the bid-ask spread). This method is fast but fails to capture the favorite-longshot bias.

### 1.2 Power Method

Assumes the consensus probability is a power function of the raw price:

$$
P_i = \pi_i^n
$$

Where the exponent $n$ is solved numerically (typically via Brent's method) to satisfy:

$$
\sum_{j} \pi_j^n = 1.0
$$

This model accounts for the empirical observation that longshot contract prices contain relatively higher vig fractions than favorite contracts.

### 1.3 Shin Method

- **Citation**: Shin, H. S. (1993). Measuring the Incidence of Insider Trading in a Market for State-Contingent Claims. *Economic Journal*, 103(420), 1141-1153.
- **Formulation**:
  Shin models the market as composed of two types of traders:
  1. A fraction $z$ of **insiders** who know the true outcome with certainty.
  2. A fraction $1 - z$ of **noise traders** who buy randomly.

  The exchange sets prices to protect itself against adverse selection from insiders. The raw price $\pi_i$ is a function of the true probability $P_i$ and the insider fraction $z$:

  $$
  \pi_i = z + (1 - z) \frac{P_i^2}{\sum_j P_j^2}
  $$

  The system solves for $z$ and $P_i$ simultaneously using Brent's root-finding method to minimize squared pricing discrepancy. Shin's method is the default for liquid, active books.

---

## 2. Quoting Engine (Avellaneda-Stoikov Adaptation)

- **Citation**: Avellaneda, M., & Stoikov, S. (2008). High-frequency trading in a limit order book. *Quantitative Finance*, 8(3), 217-224.
- **Formulation**:
  The classic Avellaneda-Stoikov model solves for the optimal bid/ask spreads of a market-maker handling inventory risk. For binary prediction markets (where payouts are strictly bounded in $[0.00, 1.00]$ dollars), we adapt the reservation price $r$ and quoting spread $s$:

  $$\text{Reservation Price: } r(q) = P_{\text{fair}} - \gamma \cdot \sigma^2 \cdot q \cdot (T - t)$$
  $$\text{Optimal Spread: } s(q) = \gamma \cdot \sigma^2 \cdot (T - t) + \frac{2}{\gamma} \ln\left(1 + \frac{\gamma}{\kappa}\right)$$

  Where:
  - $P_{\text{fair}}$: Blended ensemble fair probability.
  - $q$: Current inventory (number of contracts held; positive for long, negative for short).
  - $\gamma$: Risk aversion parameter.
  - $\sigma^2$: Volatility of the asset (for binary contracts, we approximate variance as $P_{\text{fair}}(1 - P_{\text{fair}})$).
  - $T - t$: Time remaining until contract settlement in years/days.
  - $\kappa$: Order arrival intensity (liquidity parameter).

  The quoted Bid and Ask prices are centered around the reservation price:

  $$P_{\text{bid}} = r(q) - \frac{s(q)}{2} \qquad P_{\text{ask}} = r(q) + \frac{s(q)}{2}$$

  This shifts quotes defensively to discourage fills that increase inventory exposure.

---

## 3. Portfolio Position Optimization

To allocate capital across $N$ correlated contracts, the system solves a convex optimization problem in `wc2026.execution.portfolio`.

### 3.1 Mathematical Program (QCQP)

We maximize expected edge subject to a variance risk budget and position limits:

$$
\max_{\mathbf{w}} \quad \mathbf{e}^T \mathbf{w}
$$

$$
\text{subject to} \quad \mathbf{w}^T \mathbf{\Sigma} \mathbf{w} \le \text{Budget}_{\text{risk}}
$$

$$
\quad \|\mathbf{w}\|_{\infty} \le \text{Limit}_{\text{event}}
$$

Where:
- $\mathbf{w} \in \mathbb{R}^N$: Position weights (number of contracts to hold; positive for long, negative for short).
- $\mathbf{e} \in \mathbb{R}^N$: Expected edges vector ($\text{Edge}_i = P_{\text{fair}, i} - \text{Ask}_i$).
- $\mathbf{\Sigma} \in \mathbb{R}^{N \times N}$: Covariance matrix of contract payoffs, extracted directly from the tournament simulator's joint draw matrix.
- $\text{Budget}_{\text{risk}}$: Maximum allowed portfolio variance.
- $\text{Limit}_{\text{event}}$: Maximum single-event exposure limit.

### 3.2 Conic Solver Rationale

Because the variance constraint $\mathbf{w}^T \mathbf{\Sigma} \mathbf{w} \le \text{Budget}_{\text{risk}}$ is quadratic, the problem is a **Quadratically Constrained Quadratic Program (QCQP)**. 

Standard active-set or simplex QP solvers (such as OSQP) cannot handle non-linear quadratic constraints. The system uses **Clarabel** (cvxpy's bundled interior-point conic solver) to solve the second-order cone program (SOCP) natively. If Clarabel encounters numerical errors, the system falls back to **SCS** (splitting cone solver).
