"""PAGE 3 — Bitcoin Analysis"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd

from src.utils.data_loader import load_bitcoin, filter_date_range
from src.analysis.eda.visualizations import plot_metric_over_time
from src.analysis.trends.trends import aggregate

st.title("₿ Bitcoin — Blockchain Metrics")
st.markdown("Bitcoin continues to use Proof-of-Work. Included as a benchmark for PoW energy trajectory.")
st.divider()

@st.cache_data(ttl=3600)
def get_btc():
    return load_bitcoin()

df = get_btc()

if df.empty:
    st.error("⚠️ No Bitcoin data found. Run `python scripts/collect_data.py` to fetch data.")
    st.stop()

df["date"] = pd.to_datetime(df["date"])

with st.sidebar:
    st.subheader("₿ Bitcoin Filters")
    date_min = df["date"].min().date()
    date_max = df["date"].max().date()
    start, end = st.date_input("Date Range", [date_min, date_max], min_value=date_min, max_value=date_max, key="btc_dates")
    agg_freq = st.selectbox("Aggregation", ["Daily", "Weekly", "Monthly", "Quarterly"], index=2, key="btc_agg")

freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "M", "Quarterly": "Q"}
df_filtered = filter_date_range(df, str(start), str(end))
df_agg      = aggregate(df_filtered, freq=freq_map[agg_freq])

# KPIs
c1, c2, c3 = st.columns(3)
if "transaction_count" in df.columns:
    c1.metric("Total Transactions (All-time)", f"{df['transaction_count'].sum():,.0f}")
if "hash_rate" in df.columns:
    c2.metric("Latest Hash Rate", f"{df['hash_rate'].iloc[-1]:.2f} EH/s")
if "energy_consumption" in df.columns:
    c3.metric("Latest Energy (est.)", f"{df['energy_consumption'].iloc[-1]:.1f} TWh/yr")

st.divider()

tab_tx, tab_hr, tab_en, tab_raw = st.tabs([
    "📦 Transactions", "⛏️ Hash Rate", "⚡ Energy (Estimated)", "📋 Raw Data"
])

with tab_tx:
    if "transaction_count" in df_agg.columns:
        fig = plot_metric_over_time(
            df_agg, "transaction_count", "bitcoin",
            title=f"Bitcoin — Daily Transactions ({agg_freq})",
            yaxis_title="Transaction Count",
            show_merge=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Source: Coin Metrics (TxCnt). Bitcoin uses PoW throughout the entire period.")

with tab_hr:
    if "hash_rate" in df_agg.columns:
        fig = plot_metric_over_time(
            df_agg, "hash_rate", "bitcoin",
            title=f"Bitcoin — Hash Rate ({agg_freq})",
            yaxis_title="Hash Rate (EH/s)",
            show_merge=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.info("Bitcoin hash rate has grown substantially since 2017, "
                "reflecting increased mining participation and hardware efficiency gains.")
        st.caption("Source: Coin Metrics (HashRate). Unit: EH/s (exa-hashes per second = 10¹⁸ hashes/second).")

with tab_en:
    if "energy_consumption" in df_agg.columns:
        fig = plot_metric_over_time(
            df_agg, "energy_consumption", "bitcoin",
            title=f"Bitcoin — Estimated Energy Consumption ({agg_freq})",
            yaxis_title="Energy (TWh/year, estimated)",
            show_merge=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.warning(
            "**Data Type: ESTIMATE.** "
            "Primary source: Digiconomist Bitcoin Energy Consumption Index. "
            "Fallback: Synthetic estimate from hash rate × 30 J/TH efficiency constant. "
            "Different methodologies produce different estimates — see Data Sources page."
        )

with tab_raw:
    st.dataframe(df_filtered.tail(500), use_container_width=True)
    csv = df_filtered.to_csv(index=False)
    st.download_button("⬇️ Download Bitcoin CSV", csv, "bitcoin_data.csv", "text/csv")
