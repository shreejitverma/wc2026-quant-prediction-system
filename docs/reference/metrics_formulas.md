# Metrics & Mathematical Formulations

This document provides the exact mathematical definitions of all metrics the system computes to measure model quality, calibration accuracy, and trading edge.

---

## 1. Primary Model Performance Metrics

For a match with three possible outcomes: Home Win ($H$), Draw ($D$), and Away Win ($A$), let $\mathbf{y}_i = [y_{i, H}, y_{i, D}, y_{i, A}] \in \{0, 1\}^3$ represent the actual one-hot encoded match outcome, and $\mathbf{p}_i = [p_{i, H}, p_{i, D}, p_{i, A}] \in [0, 1]^3$ represent the model's predicted probabilities, such that $\sum_{c} p_{i, c} = 1.0$.

### 1.1 Categorical Log Loss (Cross-Entropy)

Log Loss is the primary metric used to optimize meta-model weights. It penalizes overconfident wrong predictions exponentially:

$$
\text{Log Loss} = -\frac{1}{M} \sum_{i=1}^{M} \sum_{c \in \{H, D, A\}} y_{i,c} \log\!\big(\max(10^{-15}, p_{i,c})\big)
$$

- **Range**: $[0, \infty)$. A perfect model scores 0. A model guessing randomly ($1/3$ each) scores $\log(3) \approx 1.098$.
- **Interpretation**: Lower is better. The ensembler target is to maintain an out-of-sample Log Loss of $< 0.85$ against a de-vigged market baseline.

### 1.2 Brier Score

The Brier Score measures the mean squared error of the predicted probabilities:

$$
\text{Brier Score} = \frac{1}{M} \sum_{i=1}^{M} \sum_{c \in \{H, D, A\}} (p_{i,c} - y_{i,c})^2
$$

- **Range**: $[0, 2]$. A perfect model scores 0. A random model ($1/3$ each) scores $2/3 \approx 0.667$.
- **Interpretation**: Lower is better. Less sensitive to extreme tail errors than Log Loss.

### 1.3 Ranked Probability Score (RPS)

For ordinal outcomes (where a Draw is conceptually between a Home Win and an Away Win), RPS penalizes distance from the true outcome by comparing cumulative distributions:

$$
\text{RPS} = \frac{1}{M \cdot (N_c - 1)} \sum_{i=1}^{M} \sum_{k=1}^{N_c - 1} \left( \sum_{j=1}^{k} p_{i,j} - \sum_{j=1}^{k} y_{i,j} \right)^2
$$

Where $N_c = 3$ (outcomes ordered $H, D, A$).
- **Interpretation**: Lower is better. Ensures that if the true outcome is a Home Win ($H$), predicting a Draw ($D$) is penalized less than predicting an Away Win ($A$).

---

## 2. Calibration Metrics

### 2.1 Expected Calibration Error (ECE)

ECE measures the discrepancy between predicted confidence and actual frequency. Predictions are grouped into $K$ equal-width probability bins $B_k \subset (0, 1]$ (default: $K = 10$).

$$
\text{ECE} = \sum_{k=1}^{K} \frac{|B_k|}{M} \Big| \text{acc}(B_k) - \text{conf}(B_k) \Big|
$$

Where:
- $\text{conf}(B_k) = \frac{1}{|B_k|} \sum_{i \in B_k} p_i$: Average confidence in bin $k$.
- $\text{acc}(B_k) = \frac{1}{|B_k|} \sum_{i \in B_k} y_i$: Actual success frequency in bin $k$.
- **Target**: ECE $< 0.05$ on out-of-sample validation data.

---

## 3. Operational Trading Metrics

### 3.1 Closing Line Value (CLV)

CLV measures the quality of the execution price relative to the market's final consensus (the closing price), isolating quantitative alpha from the high statistical variance of match outcomes.

For a trade on contract $c$, let $P_{\text{fill}}$ be the execution price, $P_{\text{close}}$ be the de-vigged closing price of the contract at kickoff, and $S \in \{-1, +1\}$ represent the side ( $+1$ for BUY_YES, $-1$ for SELL_YES):

$$
\text{CLV} = (P_{\text{fill}} - P_{\text{close}}) \cdot S
$$

- **Interpretation**: Positive CLV indicates that the system is entering positions at prices superior to the eventual consensus. Over $N \ge 200$ trades, a mean CLV of $> +0.5\%$ is statistically significant evidence of a profitable edge.
