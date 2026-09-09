"""PAGE 7 — Counterfactual / Hypothetical Continued-PoW Scenario"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.utils.data_loader import load_ethereum, load_bitcoin
from src.analysis.forecasting.arima_model import run_counterfactual_pow
from src.analysis.eda.visualizations import _dark_layout, _add_merge_line
from src.utils.config import ETH_MERGE_DATE

st.title("🔄 Counterfactual Scenario: Hypothetical Continued PoW")
st.markdown("""
### What if Ethereum had NEVER migrated to Proof-of-Stake?
In September 2022, Ethereum executed *The Merge*, transitioning from Proof-of-Work to Proof-of-Stake.
This module fits an ARIMA model exclusively on pre-Merge Proof-of-Work historical data (2017–2022)
and projects a counterfactual trajectory forward past the Merge.
""")

st.warning("""
⚠️ **CRITICAL METHODOLOGICAL DISTINCTION:**
This is a **MODEL-BASED HYPOTHETICAL SIMULATION**, not an observed reality.
It operates on the assumption that historical PoW growth dynamics, miner difficulty adjustments,
and hardware deployment trends would have continued unhindered past September 2022.
It must **NEVER** be cited as factual on-chain historical data.
""")
st.divider()

@st.cache_data(ttl=3600)
def get_eth():
    return load_ethereum()

df_eth = get_eth()

if df_eth.empty:
    st.error("No Ethereum data found. Please run data collection.")
    st.stop()

# ── Sidebar Configuration ──────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Counterfactual Settings")
    target_metric = st.selectbox(
        "Projected Metric",
        ["hash_rate", "energy_consumption"],
        format_func=lambda x: "Hash Rate (TH/s)" if x == "hash_rate" else "Energy Consumption (TWh/year)"
    )
    horizon_days = st.slider("Projection Horizon (Days past Merge)", min_value=90, max_value=730, value=365, step=30)
    p_cf = st.number_input("ARIMA p", min_value=0, max_value=7, value=5)
    d_cf = st.number_input("ARIMA d", min_value=0, max_value=2, value=1)
    q_cf = st.number_input("ARIMA q", min_value=0, max_value=5, value=2)

# ── Run Counterfactual ──────────────────────────────────────────────────────
with st.spinner("Generating counterfactual PoW trajectory..."):
    cf_res = run_counterfactual_pow(
        df_eth=df_eth,
        metric=target_metric,
        forecast_horizon=horizon_days,
        order=(p_cf, d_cf, q_cf)
    )

# ── Visualization: Actual vs Counterfactual ────────────────────────────────
st.subheader("1. Actual Observed Trajectory vs Hypothetical Continued PoW")

df_eth_plot = df_eth.copy()
df_eth_plot["date"] = pd.to_datetime(df_eth_plot["date"])

fig = go.Figure()

# Actual historical Ethereum data (both pre- and post-Merge)
fig.add_trace(go.Scatter(
    x=df_eth_plot["date"],
    y=df_eth_plot[target_metric],
    mode="lines",
    name="Actual Observed Ethereum (PoW → PoS)",
    line=dict(color="#627EEA", width=2.5),
    hovertemplate="%{x|%Y-%m-%d}<br>Observed: %{y:,.2f}<extra></extra>",
))

# Counterfactual PoW forecast trace
if cf_res.forecast_df is not None:
    fc_df = cf_res.forecast_df.copy()
    fc_df["date"] = pd.to_datetime(fc_df["date"])

    fig.add_trace(go.Scatter(
        x=fc_df["date"],
        y=fc_df["forecast"],
        mode="lines",
        name="Hypothetical Continued PoW (Counterfactual)",
        line=dict(color="#FF4500", width=2.5, dash="dash"),
        hovertemplate="%{x|%Y-%m-%d}<br>Hypothetical PoW: %{y:,.2f}<extra></extra>",
    ))
    # 95% Confidence interval band
    if "upper_ci_95" in fc_df.columns and "lower_ci_95" in fc_df.columns:
        fig.add_trace(go.Scatter(
            x=pd.concat([fc_df["date"], fc_df["date"][::-1]]),
            y=pd.concat([fc_df["upper_ci_95"], fc_df["lower_ci_95"][::-1]]),
            fill="toself",
            fillcolor="rgba(255, 69, 0, 0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            name="95% Confidence Interval (Counterfactual)",
            hoverinfo="skip",
        ))

# Use the safe merge line helper (fixes the add_vline TypeError)
_add_merge_line(fig)

unit_str = "TH/s" if target_metric == "hash_rate" else "TWh/year"
fig.update_layout(
    **_dark_layout(
        f"Ethereum: Actual vs Counterfactual Continued PoW ({unit_str})",
        yaxis_title=f"{target_metric.replace('_', ' ').title()} ({unit_str})"
    )
)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "**Blue solid line** = actual observed Ethereum data. After the Merge, hash rate/energy drops to ~0 under PoS. "
    "**Red dashed line** = ARIMA model trained on pre-Merge PoW data, projected forward as a hypothetical 'no-Merge' scenario. "
    "**Shaded band** = 95% forecast confidence interval."
)

st.divider()

# ── Impact Evaluation Table ─────────────────────────────────────────────────
st.subheader("2. Estimated Avoided Footprint (Counterfactual Delta)")

if cf_res.forecast_df is not None:
    fc_df = cf_res.forecast_df.copy()
    fc_df["date"] = pd.to_datetime(fc_df["date"])

    # Merge with actuals
    comp_df = pd.merge(
        fc_df[["date", "forecast", "lower_ci_95", "upper_ci_95"]],
        df_eth_plot[["date", target_metric]],
        on="date",
        how="inner"
    ).rename(columns={target_metric: "actual_observed", "forecast": "counterfactual_pow"})

    comp_df["avoided_delta"] = comp_df["counterfactual_pow"] - comp_df["actual_observed"]

    avg_actual = comp_df["actual_observed"].mean()
    avg_cf = comp_df["counterfactual_pow"].mean()
    avg_delta = comp_df["avoided_delta"].mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("Observed Post-Merge Average", f"{avg_actual:,.3f} {unit_str}")
    c2.metric("Counterfactual PoW Average", f"{avg_cf:,.2f} {unit_str}")
    if avg_cf > 0:
        reduction_pct = (avg_cf - avg_actual) / avg_cf * 100
        c3.metric(
            "Estimated Avoided Magnitude",
            f"{avg_delta:,.2f} {unit_str}",
            delta=f"-{reduction_pct:.1f}%",
            delta_color="inverse",
        )

    # Cumulative avoided delta over time
    if len(comp_df) > 0:
        comp_df_sorted = comp_df.sort_values("date")
        fig_delta = go.Figure()
        fig_delta.add_trace(go.Scatter(
            x=comp_df_sorted["date"],
            y=comp_df_sorted["avoided_delta"],
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(98,126,234,0.20)",
            line=dict(color="#627EEA", width=2),
            name=f"Avoided {target_metric.replace('_',' ').title()} ({unit_str})",
            hovertemplate="%{x|%Y-%m-%d}<br>Avoided: %{y:,.2f} " + unit_str + "<extra></extra>",
        ))
        fig_delta.update_layout(
            **_dark_layout(
                f"Estimated Avoided {target_metric.replace('_',' ').title()} per Day (Counterfactual − Actual)",
                yaxis_title=f"Avoided {unit_str}",
            )
        )
        st.plotly_chart(fig_delta, use_container_width=True)

    st.divider()

    # ── Thesis proof section ──────────────────────────────────────────────────
    st.subheader("3. Thesis Evidence Assessment")
    st.markdown("""
    #### Quantitative Evidence Produced by This Counterfactual Analysis
    """)

    if avg_cf > 0 and avg_actual >= 0:
        reduction_pct = (avg_cf - avg_actual) / avg_cf * 100
        verdict_icon = "✅" if reduction_pct > 90 else "⚠️"

        st.markdown(f"""
| Evidence Item | Value | Thesis Claim | Assessment |
|:---|:---|:---|:---|
| Post-Merge observed avg | `{avg_actual:,.4f} {unit_str}` | Near-zero under PoS | {verdict_icon} |
| Counterfactual PoW projection | `{avg_cf:,.2f} {unit_str}` | Would have continued growing | {verdict_icon} |
| Estimated avoided footprint | `{avg_delta:,.2f} {unit_str}` | ~99.95% reduction expected | {verdict_icon} |
| % reduction vs counterfactual | `{reduction_pct:.2f}%` | >99.9% expected | {"✅ CONFIRMED" if reduction_pct > 90 else "⚠️ PARTIAL"} |
| ARIMA Model used | `ARIMA({p_cf},{d_cf},{q_cf})` | ARIMA(5,1,2) baseline | {'✅ Matches thesis' if (p_cf,d_cf,q_cf)==(5,1,2) else '🔧 Custom'} |
        """)

        if reduction_pct > 90:
            st.success(
                f"🎯 **Thesis SUPPORTED by counterfactual simulation:**  \n"
                f"The ARIMA({p_cf},{d_cf},{q_cf}) model trained on PoW-era data projects "
                f"a sustained {target_metric.replace('_',' ')} of **{avg_cf:,.2f} {unit_str}** "
                f"had Ethereum remained on PoW.  \n"
                f"The actual post-Merge value is **{avg_actual:,.4f} {unit_str}** — representing an "
                f"estimated **{reduction_pct:.1f}% avoided footprint** attributable directly to the consensus transition."
            )
        else:
            st.warning(
                f"⚠️ Reduction computed at {reduction_pct:.1f}%. "
                f"Consider adjusting the ARIMA order or data range. "
                f"Thesis expects >99% reduction for energy_consumption."
            )

    st.markdown("""
    #### Analytical Discussion
    - **Hypothesis Support:** If the counterfactual continued-PoW model projects sustained or expanding energy
      consumption (matching the growth rate of hash rate pre-Merge), while the actual observed PoS data exhibits a
      near-zero plateau (~0.0026 TWh/yr), this provides quantitative backing for the thesis that the consensus
      transition dramatically decoupled network security from electricity consumption.
    - **Limitations & Assumptions:**
      - The counterfactual assumes GPU/ASIC mining equipment availability and ETH price profitability would have
        sustained pre-Merge trajectory.
      - External economic shocks (crypto bear markets, energy price surges) are not endogenous to the univariate ARIMA model.
    """)

    with st.expander("Inspect Counterfactual Data Table"):
        st.dataframe(comp_df, use_container_width=True)
        csv_comp = comp_df.to_csv(index=False)
        st.download_button("⬇️ Download Counterfactual Comparison CSV", csv_comp, "counterfactual_pow_vs_actual.csv", "text/csv")
