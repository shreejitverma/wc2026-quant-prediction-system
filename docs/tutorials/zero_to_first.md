# Tutorial: Zero to First Prediction

This tutorial walks through setting up the WC2026 Prediction System from a clean machine to observing your first priced contracts on the Operator Console.

---

## 1. Prerequisites

Before starting, ensure your machine has the following tools installed:
- **Git**
- **Python 3.12**
- **Node.js** (v18 or higher)
- **`uv`**: Fast Python package manager. If missing, install it via curl:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

---

## 2. Environment Setup

### Step 2.1: Clone the Repository
Navigate to your desired workspace directory and clone the repository:
```bash
cd /Users/shreejitverma/github/
# (Or navigate to the existing folder)
cd /Users/shreejitverma/github/footbal_prediction
```

### Step 2.2: Build the Python Environment
Run `make setup` to create a virtual environment (`.venv`) and install all required dependencies (including scientific packages like NumPy, JAX, cvxpy, and LightGBM) from the lockfile:
```bash
make setup
```

### Step 2.3: Configure Git Hooks
Install pre-commit hooks (which include Ruff lint validation and the Point-in-Time database leakage gate check):
```bash
make hooks
```

### Step 2.4: Install Frontend Dependencies
Navigate to the `frontend/` directory and install the Node packages (Vite, React, React Router 8, Tailwind v4, Zustand, and TanStack Query):
```bash
cd frontend
npm install
cd ..
```

---

## 3. Data Bootstrapping

Initialize the local DuckDB database, populate historical international fixtures, and create sample runs and ledger logs:
```bash
make bootstrap-data
```
- **Expected Output**: Log records showing mock/historical datasets successfully initialized under `data/`.

---

## 4. Run the Full Stack

Launch the FastAPI backend server (running on port 8000) and the Vite React Single Page Application (running on port 3000/3001) concurrently with single-process cleanup:
```bash
./run.sh
```

---

## 5. Observe Predictions on the Console

1. Open your browser and navigate to: **`http://localhost:3000`** (or `http://localhost:3001` if port 3000 was occupied).
2. Verify the following on the **Command Center**:
   - The top banner displays `PAPER TRADING ACTIVE`.
   - The health panel displays green ticks for all services.
3. Click on the **Matches** tab in the navigation header:
   - Select a match (e.g. `Brazil vs France`).
   - Observe the computed team form timelines and the 15×15 scoreline probability heatmap matrix.
4. Click on the **Opportunities** tab:
   - Observe the live contracts, their market prices (Bid/Ask), our model's Fair Value interval, and the calculated Expected Value (EV).
