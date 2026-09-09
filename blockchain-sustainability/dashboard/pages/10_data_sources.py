"""PAGE 10 — Data Sources & Limitations"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd

st.title("📚 Data Sources, Units & Analytical Limitations")
st.markdown("""
A transparent overview of every upstream data provider, metric definitions, unit conversions, 
temporal coverage, and research limitations.
""")
st.divider()

# ── Data Provider Table ─────────────────────────────────────────────────────
st.subheader("1. Upstream Data Sources Inventory")

sources = [
    {
        "Data Provider": "Coin Metrics Community API (v4)",
        "API Endpoint": "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics",
        "Target Metrics": "TxCnt (Transaction Count), HashRate (Mean Hash Rate)",
        "Assets": "Ethereum (eth), Bitcoin (btc)",
        "Temporal Coverage": "Genesis / 2015 to Present",
        "Auth Required": "None (Community tier)",
        "Limitations": "Rate limits on free tier; daily aggregation granularity."
    },
    {
        "Data Provider": "Blockchain.com Charts API",
        "API Endpoint": "https://api.blockchain.info/charts/{chart-name}",
        "Target Metrics": "n-transactions, hash-rate",
        "Assets": "Bitcoin (btc only)",
        "Temporal Coverage": "2009 to Present",
        "Auth Required": "None (Public endpoints)",
        "Limitations": "Bitcoin-only; does not host Ethereum metrics."
    },
    {
        "Data Provider": "Digiconomist BECI",
        "API Endpoint": "GitHub BECI Public Dataset / Scraped Index",
        "Target Metrics": "Annualized Electricity Consumption (TWh/year)",
        "Assets": "Bitcoin (btc)",
        "Temporal Coverage": "2017 to Present",
        "Auth Required": "None",
        "Limitations": "Economic model based on miner profitability equilibrium; model-based estimate."
    },
    {
        "Data Provider": "CCRI (Crypto Carbon Ratings Institute)",
        "API Endpoint": "CCRI Published Research Reports & Benchmarks",
        "Target Metrics": "Ethereum PoS Electricity Consumption (~0.0026 TWh/year)",
        "Assets": "Ethereum (eth post-Merge)",
        "Temporal Coverage": "Sep 2022 to Present",
        "Auth Required": "None (Published constants)",
        "Limitations": "Static empirical census of validator hardware wattage rather than dynamic real-time telemetry."
    }
]

st.dataframe(pd.DataFrame(sources), use_container_width=True, hide_index=True)

st.divider()

# ── Units & Normalization ───────────────────────────────────────────────────
st.subheader("2. Metrics & Unit Standardization")

units_table = [
    {
        "Metric": "Transaction Count",
        "Canonical Unit": "Transactions / Day",
        "Source Units Encountered": "Count per day",
        "Conversion Applied": "Identity (Integer count)"
    },
    {
        "Metric": "Hash Rate (Ethereum PoW)",
        "Canonical Unit": "TH/s (Tera-Hashes per second)",
        "Source Units Encountered": "TH/s or H/s",
        "Conversion Applied": "Scaled to $10^{12}$ hashes/sec"
    },
    {
        "Metric": "Hash Rate (Bitcoin PoW)",
        "Canonical Unit": "EH/s (Exa-Hashes per second)",
        "Source Units Encountered": "GH/s, TH/s, EH/s",
        "Conversion Applied": "Scaled to $10^{18}$ hashes/sec ($1 \\text{ EH/s} = 10^6 \\text{ TH/s}$)"
    },
    {
        "Metric": "Energy Consumption",
        "Canonical Unit": "TWh / year (Annualized)",
        "Source Units Encountered": "GWh/day, TWh/year, Joules",
        "Conversion Applied": "Converted to annualized TWh/year ($1 \\text{ TWh} = 10^9 \\text{ kWh}$)"
    }
]

st.dataframe(pd.DataFrame(units_table), use_container_width=True, hide_index=True)

st.divider()

# ── Research Limitations ────────────────────────────────────────────────────
st.subheader("3. Explicit Research Limitations")
st.markdown("""
1. **Unobservable Energy Ground Truth:**
   Electricity consumption cannot be measured natively on a blockchain. All energy numbers are **estimates** 
   derived from difficulty/hash-rate combined with assumed hardware fleet efficiency constants, or economic 
   breakeven models.
2. **Hardware Fleet Heterogeneity:**
   Miners operate a heterogeneous mix of hardware generations (e.g. older Antminer S9 vs newer S19 XP; 
   differing GPU models for Ethash). Applying a uniform efficiency factor (J/TH) approximates the fleet average.
3. **Univariate Time-Series Constraints:**
   The ARIMA model assumes future values are a function of past values and stochastic error terms. It does not 
   explicitly model exogenous variables such as cryptocurrency spot prices, semiconductor supply shocks, 
   or global energy regulation.
4. **Discrepancy Preservation:**
   Different data aggregators (Coin Metrics vs Blockchain.com vs Etherscan) report slightly differing daily 
   block counts and timestamps due to differing UTC cutoffs. We preserve these discrepancies rather than smoothing them away.
""")
