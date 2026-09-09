"""PAGE 9 — Methodology & Computational Pipeline"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

st.title("📋 Research Methodology & Computational Architecture")
st.markdown("""
A complete documentation of the data pipelines, mathematical formulas, statistical tests, 
and forecasting methodologies applied in this software implementation.
""")
st.divider()

t1, t2, t3, t4, t5 = st.tabs([
    "1. Data Collection & Preprocessing",
    "2. Energy Estimation Model",
    "3. Correlation Formulations",
    "4. ARIMA Mathematics",
    "5. Counterfactual Modeling"
])

with t1:
    st.subheader("Data Collection, Validation & Ingestion Pipeline")
    st.markdown("""
    ```
    ┌──────────────────────────┐    ┌───────────────────────────┐
    │  Coin Metrics API (v4)   │    │    Blockchain.com API     │
    │  (TxCnt, HashRate)       │    │    (TxCnt, HashRate)      │
    └─────────────┬────────────┘    └─────────────┬─────────────┘
                  │                               │
                  ▼                               ▼
    ┌───────────────────────────────────────────────────────────┐
    │           Collector & Consensus Labeling Layer            │
    │   • Dates < 2022-09-15  -> Consensus = "PoW"               │
    │   • Dates >= 2022-09-15 -> Consensus = "PoS", HashRate = 0│
    └─────────────────────────────┬─────────────────────────────┘
                                  ▼
    ┌───────────────────────────────────────────────────────────┐
    │              Data Cleaner & Gap Normalizer                │
    │   • Continuous daily date index reindexing                │
    │   • Forward fill short gaps (<= 3 days)                   │
    │   • Flag extreme IQR outliers                             │
    └─────────────────────────────┬─────────────────────────────┘
                                  ▼
    ┌───────────────────────────────────────────────────────────┐
    │          PostgreSQL Schema & Flat CSV Cache Layer         │
    └───────────────────────────────────────────────────────────┘
    ```
    - **No Silent Dropping:** All transformations, imputed rows, and outlier boundaries are strictly logged.
    - **Dual Persistence:** Writes simultaneously to relational PostgreSQL tables (`blockchain_metrics`) and local processed CSVs.
    """)

with t2:
    st.subheader("Energy Estimation Equations")
    st.markdown("""
    Because energy consumption cannot be queried directly from the Ethereum or Bitcoin state machine,
    it is calculated mathematically based on the lower-bound bottom-up hardware efficiency method:

    $$\\text{Power (Watts)} = \\text{HashRate (H/s)} \\times \\text{Hardware Efficiency } \\left(\\frac{\\text{Joules}}{\\text{Hash}}\\right)$$

    $$\\text{Annualized Energy (TWh/year)} = \\frac{\\text{Power (Watts)} \\times 8,760 \\text{ hours/year}}{10^{12} \\text{ Wh/TWh}}$$

    - **Bitcoin Assumptions:** $\\approx 30.0 \\text{ J/TH}$ (representative blended ASIC efficiency for modern Antminer / Whatsminer fleets).
    - **Ethereum PoW Assumptions:** $\\approx 70.0 \\text{ J/TH}$ (reflecting GPU rig efficiency prior to Ethash ASIC maturation).
    - **Ethereum PoS Post-Merge:** Fixed constant at $\\approx 0.0026 \\text{ TWh/year}$ based on the Crypto Carbon Ratings Institute (CCRI) validator node power census.
    """)

with t3:
    st.subheader("Statistical Correlation Framework")
    st.markdown("""
    #### 1. Pearson Product-Moment Correlation Coefficient ($r$)
    Measures linear association between continuous variables:

    $$r_{xy} = \\frac{\\sum_{i=1}^n (x_i - \\bar{x})(y_i - \\bar{y})}{\\sqrt{\\sum_{i=1}^n (x_i - \\bar{x})^2 \\sum_{i=1}^n (y_i - \\bar{y})^2}}$$

    Hypothesis test on correlation significance:
    - $H_0: \\rho = 0$ (No linear association)
    - $H_1: \\rho \\neq 0$ (Significant association)
    - Test statistic: $t = r \\sqrt{\\frac{n-2}{1-r^2}} \\sim t_{n-2}$

    #### 2. Spearman Rank Correlation ($\\rho_s$)
    Non-parametric robustness check measuring monotonic relationships without assuming normality:

    $$\\rho_s = 1 - \\frac{6 \\sum d_i^2}{n(n^2 - 1)}$$

    > **Scientific Caveat:** Correlation measures association, not causality.
    """)

with t4:
    st.subheader("ARIMA(p, d, q) Time-Series Specification")
    st.markdown("""
    The Autoregressive Integrated Moving Average model combines autoregression, differencing, and moving averages:

    $$\\Phi_p(B) (1 - B)^d X_t = \\Theta_q(B) \\epsilon_t$$

    Where:
    - $B$ is the backshift operator: $B^k X_t = X_{t-k}$
    - $(1 - B)^d$ denotes order-$d$ differencing
    - $\\Phi_p(B) = 1 - \\sum_{i=1}^p \\phi_i B^i$ (Autoregressive component of order $p$)
    - $\\Theta_q(B) = 1 + \\sum_{j=1}^q \\theta_j B^j$ (Moving average component of order $q$)
    - $\\epsilon_t \\sim \\text{WN}(0, \\sigma^2)$ (White noise error)

    #### Thesis Baseline Model: ARIMA(5, 1, 2)
    - **$p = 5$**: 5 lag terms capture weekly cyclical miner behavior.
    - **$d = 1$**: First differencing eliminates trend non-stationarity identified via the ADF test.
    - **$q = 2$**: 2 shock lags absorb short-term volatility.

    #### Validation Metrics:
    - **MAE:** $\\frac{1}{n} \\sum_{t=1}^n |y_t - \\hat{y}_t|$
    - **RMSE:** $\\sqrt{\\frac{1}{n} \\sum_{t=1}^n (y_t - \\hat{y}_t)^2}$
    - **MAPE:** $\\frac{100\\%}{n} \\sum_{t=1}^n \\left|\\frac{y_t - \\hat{y}_t}{y_t}\\right|$
    """)

with t5:
    st.subheader("Counterfactual Continued-PoW Methodology")
    st.markdown("""
    #### Counterfactual Simulation Architecture
    1. **Training Sample Truncation:**  
       The training sample is strictly restricted to Ethereum historical observations where $\\text{Date} < 2022-09-15$ (PoW era).
    2. **Model Parameter Estimation:**  
       An ARIMA model is fitted exclusively to this pre-Merge sample.
    3. **Out-of-Sample Extrapolation:**  
       The model generates forecasted values $\\hat{Y}_{T+h}$ for $h \\in [1, H]$ past September 15, 2022, accompanied by 95% forecast intervals:
       $$\\hat{Y}_{T+h} \\pm 1.96 \\times \\text{SE}(\\hat{Y}_{T+h})$$
    4. **Delta Calculation:**  
       $$\\Delta_t = \\hat{Y}_{\\text{Counterfactual}, t} - Y_{\\text{Actual Observed PoS}, t}$$
    5. **Epistemological Constraint:**  
       This projection estimates what computational demand *could* have been under continued PoW based purely on historical univariate trends; it does not model macroeconomic feedback or mining hardware supply constraints.
    """)
