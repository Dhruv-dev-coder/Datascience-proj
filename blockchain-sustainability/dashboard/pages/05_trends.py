"""PAGE 5 — Trend Analysis"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.utils.data_loader import load_ethereum, load_bitcoin, filter_date_range
from src.analysis.trends.trends import (
    aggregate,
    split_pre_post_merge,
    period_statistics,
    compute_pow_pos_change,
    rolling_stats,
    MERGE_DATE,
)
from src.analysis.eda.visualizations import (
    plot_pow_pos_comparison,
    _dark_layout,
    _add_merge_line,
)

st.title("📈 Trend Analysis: Pre-Merge vs Post-Merge")
st.markdown("""
Examining the evolution of Ethereum across its Proof-of-Work era (pre-September 2022)
and Proof-of-Stake era (post-September 2022), alongside benchmark trends against Bitcoin.
""")
st.divider()

@st.cache_data(ttl=3600)
def get_data():
    return load_ethereum(), load_bitcoin()

df_eth, df_btc = get_data()

if df_eth.empty:
    st.error("No Ethereum data available. Please run data collection or seed script.")
    st.stop()

# ── Metric Selection & Options ──────────────────────────────────────────────
with st.sidebar:
    st.subheader("Trend Configuration")
    target_metric = st.selectbox(
        "Metric for Deep Dive",
        ["transaction_count", "hash_rate", "energy_consumption"],
        format_func=lambda x: x.replace("_", " ").title()
    )
    rolling_window = st.slider("Moving Average Window (Days)", min_value=7, max_value=90, value=30, step=7)

# ── Top Summary Cards: PoW vs PoS Shift ─────────────────────────────────────
st.subheader("1. Ethereum Structural Shift Summary")
change_df = compute_pow_pos_change(df_eth)

if not change_df.empty:
    cols = st.columns(len(change_df))
    for idx, row in change_df.iterrows():
        metric_label = row["metric"].replace("_", " ").title()
        pct = row["pct_change"]
        delta_color = "normal" if abs(pct) < 1.0 else ("inverse" if "energy" in row["metric"] or "hash" in row["metric"] else "normal")
        cols[idx].metric(
            label=f"{metric_label}",
            value=f"PoS Mean: {row['pos_mean']:,.2f}",
            delta=f"{pct:+.1f}% vs PoW",
            delta_color=delta_color
        )

st.plotly_chart(plot_pow_pos_comparison(change_df), use_container_width=True)

# ── Thesis Hypotheses Verdict ────────────────────────────────────────────────
st.subheader("🔬 Thesis Hypothesis Assessment")
en_row = change_df[change_df["metric"] == "energy_consumption"]
hr_row = change_df[change_df["metric"] == "hash_rate"]
tx_row = change_df[change_df["metric"] == "transaction_count"]

if not en_row.empty and not hr_row.empty and not tx_row.empty:
    en_pct = en_row["pct_change"].iloc[0]
    hr_pct = hr_row["pct_change"].iloc[0]
    tx_pct = tx_row["pct_change"].iloc[0]

    verdict_data = [
        {
            "Hypothesis": "Merge eliminated mining computation",
            "Expected": "Hash Rate drops to 0 post-Merge",
            "Observed Change": f"{hr_pct:+.1f}%",
            "Verdict": "✅ CONFIRMED" if hr_pct < -90 else "⚠️ PARTIAL",
        },
        {
            "Hypothesis": "Energy consumption collapsed post-Merge",
            "Expected": "~99.95% energy reduction",
            "Observed Change": f"{en_pct:+.1f}%",
            "Verdict": "✅ CONFIRMED" if en_pct < -90 else "⚠️ PARTIAL",
        },
        {
            "Hypothesis": "Transaction capacity maintained post-Merge",
            "Expected": "Transaction count stable or growing",
            "Observed Change": f"{tx_pct:+.1f}%",
            "Verdict": "✅ CONFIRMED" if tx_pct > -20 else "❌ NOT CONFIRMED",
        },
    ]
    st.dataframe(pd.DataFrame(verdict_data), use_container_width=True, hide_index=True)

    if en_pct < -90 and hr_pct < -90 and tx_pct > -30:
        st.success(
            f"**Research Thesis SUPPORTED:** Energy dropped {en_pct:+.1f}% and hash rate dropped {hr_pct:+.1f}% "
            f"while transaction count changed only {tx_pct:+.1f}% — confirming structural decoupling of "
            f"network security costs from network utility."
        )

st.divider()

# ── Detailed Pre vs Post Period Statistics ──────────────────────────────────
st.subheader("2. Summary Statistics by Consensus Era")
pre_df, post_df = split_pre_post_merge(df_eth)

stat_pre = period_statistics(pre_df, "Ethereum (PoW Era: Pre-Merge)")
stat_post = period_statistics(post_df, "Ethereum (PoS Era: Post-Merge)")
combined_stats = pd.concat([stat_pre, stat_post], ignore_index=True)

st.dataframe(combined_stats, use_container_width=True, hide_index=True)

st.divider()

# ── Rolling Trends & Structural Break ───────────────────────────────────────
st.subheader(f"3. Longitudinal Trajectory: {target_metric.replace('_', ' ').title()}")

df_eth_roll = rolling_stats(df_eth, target_metric, windows=[rolling_window])

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df_eth_roll["date"],
    y=df_eth_roll[target_metric],
    mode="lines",
    name="Raw Daily Value",
    line=dict(color="rgba(98, 126, 234, 0.35)", width=1),
))
fig.add_trace(go.Scatter(
    x=df_eth_roll["date"],
    y=df_eth_roll[f"{target_metric}_ma{rolling_window}"],
    mode="lines",
    name=f"{rolling_window}-Day Moving Average",
    line=dict(color="#627EEA", width=2.5),
))

# Safe merge line using helper (fixes add_vline TypeError)
_add_merge_line(fig)

fig.update_layout(
    **_dark_layout(
        f"Ethereum {target_metric.replace('_', ' ').title()} with {rolling_window}-Day Smoothing",
        yaxis_title=target_metric.replace("_", " ").title()
    )
)
st.plotly_chart(fig, use_container_width=True)

# ── Comparison against Bitcoin ──────────────────────────────────────────────
if not df_btc.empty and target_metric in df_btc.columns:
    st.subheader(f"4. Comparative Context vs Bitcoin (PoW Control Group)")
    st.markdown("""
    Because Bitcoin never transitioned away from Proof-of-Work, it serves as an empirical
    control benchmark against which Ethereum's structural divergence can be evaluated.
    """)

    fig_comp = go.Figure()
    df_eth_c = df_eth.copy()
    df_btc_c = df_btc.copy()
    df_eth_c["date"] = pd.to_datetime(df_eth_c["date"])
    df_btc_c["date"] = pd.to_datetime(df_btc_c["date"])

    eth_pre_vals = df_eth_c.loc[df_eth_c["date"] < MERGE_DATE, target_metric].dropna()
    btc_pre_vals = df_btc_c.loc[df_btc_c["date"] < MERGE_DATE, target_metric].dropna()

    if len(eth_pre_vals) > 0 and len(btc_pre_vals) > 0:
        eth_base = eth_pre_vals.iloc[-1]
        btc_base = btc_pre_vals.iloc[-1]

        if eth_base > 0 and btc_base > 0:
            fig_comp.add_trace(go.Scatter(
                x=df_eth_c["date"],
                y=(df_eth_c[target_metric] / eth_base) * 100,
                mode="lines",
                name="Ethereum (Base 100 at Merge)",
                line=dict(color="#627EEA", width=2),
            ))
            fig_comp.add_trace(go.Scatter(
                x=df_btc_c["date"],
                y=(df_btc_c[target_metric] / btc_base) * 100,
                mode="lines",
                name="Bitcoin (Base 100 at Merge)",
                line=dict(color="#F7931A", width=2),
            ))

            _add_merge_line(fig_comp)  # safe helper

            fig_comp.update_layout(
                **_dark_layout(
                    f"Normalized Index (Merge Date = 100): Ethereum vs Bitcoin ({target_metric.replace('_', ' ').title()})",
                    yaxis_title="Normalized Index (Base=100)"
                )
            )
            st.plotly_chart(fig_comp, use_container_width=True)
            st.caption(
                "Normalized index: both chains set to 100 at the last data point before the Merge (Sep 15, 2022). "
                "Divergence afterward shows the structural impact of the consensus transition."
            )
