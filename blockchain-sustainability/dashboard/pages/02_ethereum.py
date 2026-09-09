"""PAGE 2 — Ethereum Analysis"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd

from src.utils.data_loader import load_ethereum, filter_date_range
from src.analysis.eda.visualizations import plot_metric_over_time, plot_eth_btc_comparison
from src.analysis.trends.trends import aggregate, compute_pow_pos_change, rolling_stats, split_pre_post_merge

st.title("⟠ Ethereum — Blockchain Metrics")
st.markdown("Daily metrics for Ethereum across its PoW (pre-Merge) and PoS (post-Merge) periods.")
st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_eth():
    return load_ethereum()

df = get_eth()

if df.empty:
    st.error("⚠️ No Ethereum data found. Run `python scripts/collect_data.py` to fetch data.")
    st.code("python scripts/collect_data.py")
    st.stop()

df["date"] = pd.to_datetime(df["date"])

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⟠ Ethereum Filters")
    date_min = df["date"].min().date()
    date_max = df["date"].max().date()
    start, end = st.date_input("Date Range", [date_min, date_max], min_value=date_min, max_value=date_max)
    agg_freq   = st.selectbox("Aggregation", ["Daily", "Weekly", "Monthly", "Quarterly"], index=2)
    show_ma    = st.checkbox("Show Moving Average (30-day)", value=True)

freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "M", "Quarterly": "Q"}
freq     = freq_map[agg_freq]

df_filtered = filter_date_range(df, str(start), str(end))
df_agg      = aggregate(df_filtered, freq=freq)

# ── Top KPIs ──────────────────────────────────────────────────────────────────
pre, post = split_pre_post_merge(df)
c1, c2, c3, c4 = st.columns(4)
pow_rows = len(pre)
pos_rows = len(post)
if "transaction_count" in df.columns:
    pow_tx  = pre["transaction_count"].mean()
    pos_tx  = post["transaction_count"].mean()
    c1.metric("Avg Daily Txns (PoW)", f"{pow_tx:,.0f}")
    c2.metric("Avg Daily Txns (PoS)", f"{pos_tx:,.0f}", f"{((pos_tx-pow_tx)/pow_tx*100):+.1f}%")
if "energy_consumption" in df.columns:
    pow_en = pre["energy_consumption"].mean()
    pos_en = post["energy_consumption"].mean()
    c3.metric("Avg Energy (PoW, TWh/yr)", f"{pow_en:.2f}")
    c4.metric("Avg Energy (PoS, TWh/yr)", f"{pos_en:.4f}", f"{((pos_en-pow_en)/pow_en*100):+.1f}%")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
tab_tx, tab_hr, tab_en, tab_raw = st.tabs([
    "📦 Transactions", "⛏️ Hash Rate", "⚡ Energy", "📋 Raw Data"
])

with tab_tx:
    if "transaction_count" in df_agg.columns:
        df_plot = df_agg.copy()
        if show_ma:
            df_plot = rolling_stats(df_filtered, "transaction_count", windows=[30])
        fig = plot_metric_over_time(
            df_agg, "transaction_count", "ethereum",
            title=f"Ethereum — Daily Transactions ({agg_freq})",
            yaxis_title="Transaction Count",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Source: Coin Metrics (TxCnt). Vertical red line = Ethereum Merge (Sep 15, 2022).")
    else:
        st.warning("Transaction data not available.")

with tab_hr:
    if "hash_rate" in df_agg.columns:
        fig = plot_metric_over_time(
            df_agg, "hash_rate", "ethereum",
            title=f"Ethereum — Hash Rate ({agg_freq})",
            yaxis_title="Hash Rate (TH/s) — PoW only; PoS = 0",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.info("⚠️ After the Merge (Sep 2022), Ethereum hash rate drops to 0 — "
                "no mining computation is required under PoS.")
        st.caption("Source: Coin Metrics (HashRate). Unit: TH/s (tera-hashes per second).")
    else:
        st.warning("Hash rate data not available.")

with tab_en:
    if "energy_consumption" in df_agg.columns:
        fig = plot_metric_over_time(
            df_agg, "energy_consumption", "ethereum",
            title=f"Ethereum — Estimated Energy Consumption ({agg_freq})",
            yaxis_title="Energy (TWh/year, estimated)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.warning(
            "**Data Type: ESTIMATE.** "
            "PoW energy is estimated from hash rate × hardware efficiency constants (J/TH). "
            "PoS energy uses the CCRI estimate (~0.0026 TWh/year for the entire network). "
            "These are approximations, not direct measurements."
        )
        if "energy_consumption" in df.columns:
            chg = compute_pow_pos_change(df)
            en_row = chg[chg["metric"] == "energy_consumption"]
            if not en_row.empty:
                pct = en_row["pct_change"].iloc[0]
                st.success(f"**Observed change in estimated energy:** {pct:+.1f}% from PoW to PoS mean")
    else:
        st.warning("Energy data not available.")

with tab_raw:
    st.dataframe(df_filtered.tail(500), use_container_width=True)
    csv = df_filtered.to_csv(index=False)
    st.download_button("⬇️ Download Ethereum CSV", csv, "ethereum_data.csv", "text/csv")
