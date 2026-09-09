# Consensus at a Turning Point: Analyzing Ethereum’s 2022 Migration From PoW to PoS

An end-to-end, empirical computational research software project analyzing Ethereum's historic September 2022 consensus transition from Proof-of-Work (PoW) to Proof-of-Stake (PoS) ("The Merge"), evaluated against Bitcoin's continued Proof-of-Work baseline.

---

## 1. Executive Summary & Research Context

This project computationally reproduces and evaluates the research thesis:
> **"Consensus at a Turning Point: Analyzing Ethereum’s 2022 Migration From PoW to PoS"**

### Central Research Question
*Was Ethereum's transition from Proof-of-Work to Proof-of-Stake environmentally imperative and strategically sustainable?*

### Core Research Hypotheses & Thesis Findings to Evaluate:
1. **Computational Intensity vs Energy in PoW:** During Ethereum's PoW period, energy consumption was almost entirely governed by mining computational power (Hash Rate, $r \approx 0.96$), rather than transaction processing demand ($r \approx 0.11$).
2. **Decoupling Transaction Activity:** Economic network utilization (Transaction Count) had only a weak association with hash rate ($r \approx 0.18$) and energy ($r \approx 0.11$).
3. **The Merge Turning Point (September 15, 2022):** The transition eliminated mining computational requirements, reducing Ethereum's annualized energy demand by **~99.95%** while network transaction capacity remained fully operational.
4. **Bitcoin as a PoW Control Group:** Bitcoin's continued use of PoW demonstrates the baseline trajectory of sustained mining competition, where hash rate and energy consumption continue to scale with security expenditure.
5. **ARIMA Time-Series Modeling:** An **ARIMA(5,1,2)** specification models the underlying time-series dynamics and establishes out-of-sample forecast benchmarks (MAE, RMSE, MAPE).
6. **Counterfactual Simulation:** A model-based hypothetical forecast projecting Ethereum's computational and energy trajectory if it had continued using PoW beyond 2022.

---

## 2. System Architecture

```
blockchain-sustainability/
│
├── src/
│   ├── data/
│   │   ├── api_clients/        # Coin Metrics, Blockchain.com, Energy API clients
│   │   ├── collectors/         # Master orchestrator & consensus labeling
│   │   ├── cleaners/           # Gap filling, outlier detection, deduplication
│   │   └── validators/         # Schema & bounds validation reports
│   │
│   ├── database/
│   │   ├── models.py           # SQLAlchemy ORM schema (metrics, sources, forecasts)
│   │   └── repository.py       # Session management & bulk upsert operations
│   │
│   ├── analysis/
│   │   ├── eda/                # Plotly visualizations with dark aesthetics
│   │   ├── correlation/        # Pearson & Spearman correlation with p-values
│   │   ├── trends/             # Pre/post-Merge segmentation & rolling statistics
│   │   └── forecasting/        # ARIMA(5,1,2), ADF tests, counterfactual PoW model
│   │
│   ├── models/                 # Shared data structures and dataclasses
│   └── utils/
│       ├── config.py           # Environment variables & constants
│       ├── logger.py           # Loguru central logger
│       ├── http_client.py      # Requests with exponential retry & rate limits
│       └── data_loader.py      # PostgreSQL-first loader with flat CSV fallback
│
├── dashboard/
│   ├── app.py                  # Streamlit entrypoint with navigation
│   └── pages/                  # 10 dedicated analytical pages
│       ├── 01_overview.py      # Research questions & PoW vs PoS primer
│       ├── 02_ethereum.py      # Ethereum daily metrics & Merge markers
│       ├── 03_bitcoin.py       # Bitcoin PoW benchmark metrics
│       ├── 04_correlation.py   # Pearson/Spearman matrices & scatter plots
│       ├── 05_trends.py        # Pre/post-Merge trend statistics
│       ├── 06_arima.py         # ARIMA model fitting & error metrics
│       ├── 07_counterfactual.py# Hypothetical continued-PoW trajectory
│       ├── 08_pow_vs_pos.py    # Direct sustainability comparison
│       ├── 09_methodology.py   # Equations, algorithms & pipeline diagrams
│       └── 10_data_sources.py  # Data provider inventory & limitations
│
├── notebooks/
│   └── 01_consensus_analysis.ipynb # Interactive research reproduction notebook
│
├── scripts/
│   ├── init_db.py              # PostgreSQL database initialization
│   ├── collect_data.py         # Live public API data ingestion
│   ├── seed_sample_data.py     # Verified empirical historical seeder
│   ├── run_analysis.py         # CLI statistical tests & correlation report
│   └── run_forecast.py         # CLI ARIMA(5,1,2) & counterfactual projection
│
├── tests/                      # Pytest suite (mocked APIs, cleaners, ARIMA, DB)
├── data/
│   ├── raw/                    # Raw API payloads
│   └── processed/              # Processed continuous daily CSVs
│
├── .env.example                # Configuration template
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition
└── docker-compose.yml          # Multi-container setup (PostgreSQL + Dashboard)
```

---

## 3. Data Sources & Units

| Variable | Canonical Unit | Primary Source | Notes |
| :--- | :--- | :--- | :--- |
| **Transaction Count** | Daily Count | Coin Metrics (`TxCnt`) | Confirmed on-chain transactions per UTC day |
| **Ethereum Hash Rate**| TH/s ($10^{12}$ H/s) | Coin Metrics (`HashRate`) | Daily mean. Strictly 0 after 2022-09-15 |
| **Bitcoin Hash Rate** | EH/s ($10^{18}$ H/s) | Coin Metrics / Blockchain.com | $1 \text{ EH/s} = 10^6 \text{ TH/s}$ |
| **PoW Energy (ETH)**  | TWh / year | Synthetic estimation | $\text{HashRate} \times 70\text{ J/TH} \times 8760 \text{ h} / 10^{12}$ |
| **PoS Energy (ETH)**  | TWh / year | CCRI empirical census | $\approx 0.0026\text{ TWh/year}$ constant (~2.6 GWh/yr) |
| **PoW Energy (BTC)**  | TWh / year | Digiconomist BECI | Benchmark economic/breakeven model |

---

## 4. Setup & Local Execution Guide

### Prerequisites
- Python 3.10+ (or Docker)
- PostgreSQL (optional; system automatically falls back to local processed CSVs if DB is offline)

### Step 1: Clone & Configure Environment
```bash
cd blockchain-sustainability
cp .env.example .env
```
Edit `.env` if you have API keys (Coin Metrics, Etherscan) or PostgreSQL credentials. Default settings work out-of-the-box without keys.

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Seed / Ingest Data
To seed verified historical benchmark datasets (2017 to 2024):
```bash
python scripts/seed_sample_data.py
```
To ingest live fresh data from public APIs:
```bash
python scripts/collect_data.py --chain all
```

### Step 4: Run Statistical Analysis & ARIMA Forecasts via CLI
```bash
python scripts/run_analysis.py
python scripts/run_forecast.py
```

### Step 5: Launch the 10-Page Interactive Dashboard
```bash
streamlit run dashboard/app.py
```
Open your browser at `http://localhost:8501`.

---

## 5. Docker Deployment

To launch both PostgreSQL and the Streamlit Dashboard in Docker:
```bash
docker-compose up --build
```
Access the dashboard at `http://localhost:8501`.

---

## 6. Running Unit Tests

The test suite runs with mocked network responses and in-memory databases, requiring no live external connections:
```bash
pytest tests/ -v
```

---

## 7. Research Findings & Analytical Interpretation

### A. PoW Correlation Findings
- **Hash Rate vs. Energy:** $r \approx 0.96$ ($p < 0.0001$). Under PoW, electricity consumption was almost completely locked to computational mining effort.
- **Transaction Count vs. Energy:** $r \approx 0.11$. Transaction demand did not drive energy consumption; miners expanded hash rate based on block rewards and ETH price, independent of day-to-day transaction count.

### B. What Constitutes Evidence for the Thesis?
- **Structural Decoupling:** When Ethereum moved to PoS, its computational hash rate fell to zero and estimated energy consumption decreased by **~99.95%**, while daily transaction counts remained steady (~1,000,000 tx/day).
- **Counterfactual Divergence:** The ARIMA continued-PoW model projects that Ethereum would have consumed an estimated 40–90+ TWh/year if PoW had continued, whereas actual PoS energy consumption collapsed to ~0.0026 TWh/year.
- **Control Group Validation:** Over the same timeframe, Bitcoin's continuing PoW consensus reached record hash rates and maintained high energy consumption (~120–160 TWh/year), confirming that the reduction in Ethereum was a function of the consensus transition rather than an external macroeconomic shift in crypto markets.

### C. Scientific Integrity & Limitations
- **No Causal Mathematical Proof:** Statistical correlations demonstrate empirical association, not absolute causal certainty.
- **Energy is Estimated:** Energy consumption is derived from hardware efficiency assumptions ($J/\text{TH}$) and validator node surveys; it cannot be queried directly from the blockchain state.
- **Univariate Forecasting Assumptions:** The ARIMA model assumes continuation of historical time-series trends without modeling endogenous price or hardware supply shocks.
