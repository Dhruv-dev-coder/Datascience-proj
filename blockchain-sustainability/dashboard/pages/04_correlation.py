"""PAGE 4 — Correlation Analysis"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd

from src.utils.data_loader import load_ethereum, load_bitcoin
from src.analysis.correlation.correlation import (
    eth_pow_correlations,
    summarise_correlations,
    correlation_matrix,
    pearson,
    spearman,
)
from src.analysis.eda.visualizations import plot_correlation_heatmap, plot_scatter_regression

st.title("📊 Correlation Analysis")
st.markdown("""
Examining statistical relationships between blockchain activity, computational intensity,
and energy consumption during **Ethereum's PoW period**.

> ⚠️ **Important:** Correlation measures the strength of a linear association.
> It does **NOT** prove causation. All interpretations use this caveat explicitly.
""")
st.divider()

@st.cache_data(ttl=3600)
def get_data():
    return load_ethereum(), load_bitcoin()

df_eth, df_btc = get_data()

if df_eth.empty:
    st.error("No Ethereum data available. Run data collection first.")
    st.stop()

# ── Thesis Comparison Banner ──────────────────────────────────────────────────
st.subheader("📌 Thesis Reference Values vs. Our Calculated Values")
st.info("""
The thesis reports (for Ethereum PoW period):
- **Hash Rate ↔ Energy:** r ≈ 0.96 (very strong positive)
- **Transaction Count ↔ Hash Rate:** r ≈ 0.18 (very weak)
- **Transaction Count ↔ Energy:** r ≈ 0.11 (very weak / negligible)

**Our values are calculated from the actual API data below.** Differences may result from:
data source methodology, aggregation period, time range, energy estimation approach, or missing data.
""")

# ── Calculate correlations ────────────────────────────────────────────────────
with st.spinner("Calculating correlations …"):
    results = eth_pow_correlations(df_eth)
    corr_df = summarise_correlations(results)

if corr_df.empty:
    st.error("Could not calculate correlations — insufficient data.")
    st.stop()

# ── Correlation table ─────────────────────────────────────────────────────────
st.subheader("Correlation Results — Ethereum PoW Period")

pearson_df  = corr_df[corr_df["method"] == "Pearson"]
spearman_df = corr_df[corr_df["method"] == "Spearman"]

tab_p, tab_s = st.tabs(["Pearson (Parametric)", "Spearman (Non-Parametric Robustness Check)"])

def style_corr(df):
    def color_r(val):
        try:
            v = float(val)
            if abs(v) >= 0.70:   return "color: #00FF88; font-weight:600"
            if abs(v) >= 0.40:   return "color: #FFD700; font-weight:600"
            return "color: #FF6B6B"
        except:
            return ""
    return df.style.applymap(color_r, subset=["r"])

with tab_p:
    st.dataframe(style_corr(pearson_df[["x","y","r","p_value","n","significant","interpretation"]]),
                 use_container_width=True, hide_index=True)

with tab_s:
    st.dataframe(style_corr(spearman_df[["x","y","r","p_value","n","significant","interpretation"]]),
                 use_container_width=True, hide_index=True)

st.divider()

# ── Correlation matrix heatmap ────────────────────────────────────────────────
st.subheader("Correlation Matrix — Ethereum PoW Period")
pow_df = df_eth[df_eth["consensus"] == "PoW"].copy()
metric_cols = [c for c in ["transaction_count", "hash_rate", "energy_consumption"] if c in pow_df.columns]

if len(metric_cols) >= 2:
    corr_mat = correlation_matrix(pow_df, metric_cols)
    fig_heatmap = plot_correlation_heatmap(corr_mat, "Pearson Correlation Matrix — Ethereum PoW")
    st.plotly_chart(fig_heatmap, use_container_width=True)

st.divider()

# ── Scatter plots ─────────────────────────────────────────────────────────────
st.subheader("Scatter Plots — Ethereum PoW Period")
scatter_pairs = [
    ("hash_rate", "energy_consumption", "Hash Rate vs Energy Consumption"),
    ("transaction_count", "hash_rate", "Transaction Count vs Hash Rate"),
    ("transaction_count", "energy_consumption", "Transaction Count vs Energy Consumption"),
]

cols = st.columns(len(scatter_pairs))
for col, (x, y, title) in zip(cols, scatter_pairs):
    if x in pow_df.columns and y in pow_df.columns:
        fig = plot_scatter_regression(pow_df, x, y, title=title)
        col.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Interpretation ────────────────────────────────────────────────────────────
st.subheader("📝 Interpretation")
st.markdown("""
**Thesis Interpretation (to compare against our results):**

The thesis argues that during Ethereum's PoW period:
- The **very strong** positive correlation between hash rate and energy consumption
  suggests that *mining computational intensity* — not transaction demand — was the 
  primary driver of energy use.
- The **very weak** correlation between transaction count and energy consumption
  supports the view that *economic activity on the network* was largely decoupled
  from energy costs under PoW.
- This implies that PoW's energy consumption was driven by miner competition and hardware 
  investment, **independent of how much the network was actually used**.
- Therefore, transitioning to PoS — which eliminates mining — could substantially reduce
  energy use *regardless of transaction volume*.

**Our results are based on actual API data.** If they differ from the thesis values,
potential explanations include:
- Different date ranges (thesis may use a specific subset of the PoW period)
- Different energy estimation methodology
- Different data sources for hash rate
- Differences in daily vs. monthly aggregation
""")
