"""PAGE 6 — ARIMA Forecasting & Validation"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.utils.data_loader import load_ethereum, load_bitcoin
from src.analysis.forecasting.arima_model import (
    run_forecast_pipeline,
    adf_test,
    compute_acf_pacf,
)
from src.analysis.eda.visualizations import plot_arima_forecast, _dark_layout, _add_merge_line

st.title("🔮 ARIMA Time-Series Forecasting")
st.markdown("""
Time-series modeling using Autoregressive Integrated Moving Average (ARIMA).
The thesis references a baseline specification of **ARIMA(5,1,2)**.
Here we evaluate diagnostics, train-test holdout validation metrics (MAE, RMSE, MAPE),
and future trajectories.
""")
st.divider()

@st.cache_data(ttl=3600)
def get_data():
    return load_ethereum(), load_bitcoin()

df_eth, df_btc = get_data()

with st.sidebar:
    st.subheader("Model Configuration")
    chain_choice = st.selectbox("Select Blockchain", ["Ethereum", "Bitcoin"])
    df_selected = df_eth if chain_choice == "Ethereum" else df_btc

    # Available metrics
    available_metrics = [c for c in ["transaction_count", "hash_rate", "energy_consumption"] if c in df_selected.columns]
    target_metric = st.selectbox("Target Metric", available_metrics, format_func=lambda x: x.replace("_", " ").title())

    st.markdown("---")
    st.markdown("**ARIMA Parameters**")
    p = st.number_input("p (Autoregressive)", min_value=0, max_value=10, value=5)
    d = st.number_input("d (Differencing)", min_value=0, max_value=2, value=1)
    q = st.number_input("q (Moving Average)", min_value=0, max_value=10, value=2)

    use_auto = st.checkbox("Auto-select Order via AIC (pmdarima)", value=False)
    horizon = st.slider("Forecast Horizon (Days)", min_value=30, max_value=365, value=180, step=30)
    test_ratio = st.slider("Test Set Split Ratio", min_value=0.1, max_value=0.3, value=0.15, step=0.05)

if df_selected.empty:
    st.error(f"No data available for {chain_choice}.")
    st.stop()

# ── 1. Stationarity & Diagnostics ──────────────────────────────────────────
st.subheader("1. Stationarity Analysis & Diagnostics")
col_diag1, col_diag2 = st.columns([1, 1])

series = df_selected[target_metric].dropna()

with col_diag1:
    adf_res = adf_test(series, name=f"{chain_choice}_{target_metric}")
    st.markdown(f"**Augmented Dickey-Fuller (ADF) Test:**")
    st.markdown(f"- **ADF Statistic:** `{adf_res.adf_statistic:.4f}`")
    st.markdown(f"- **p-value:** `{adf_res.p_value:.6f}`")
    st.markdown(f"- **Lags Used:** `{adf_res.n_lags}` (Observations: `{adf_res.n_obs}`)")

    crit_str = " | ".join([f"{k}: {v:.3f}" for k, v in adf_res.critical_values.items()])
    st.markdown(f"- **Critical Values:** `{crit_str}`")

    if adf_res.is_stationary:
        st.success("✅ Series is Stationary (p < 0.05). Differencing d=0 may be tested.")
    else:
        st.warning("⚠️ Series is Non-Stationary (p ≥ 0.05). First differencing (d=1) is recommended.")

with col_diag2:
    st.markdown("**Thesis Baseline Comparison:**")
    st.info("""
    The thesis specifies **ARIMA(5,1,2)** where:
    - **p = 5**: 5 autoregressive lag terms
    - **d = 1**: First-order differencing applied to achieve stationarity
    - **q = 2**: 2 moving-average error lag terms

    Reported benchmarks in thesis:
    - MAE ≈ 27.76
    - RMSE ≈ 31.16
    - MAPE ≈ 26.08% (~73.92% accuracy index)
    """)

# ACF & PACF plots — side by side
with st.expander("📊 Show Autocorrelation (ACF) & Partial Autocorrelation (PACF) Functions"):
    corr_dict = compute_acf_pacf(series, nlags=30)

    fig_acf_pacf = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Autocorrelation Function (ACF)", "Partial Autocorrelation (PACF)"],
    )

    # ACF
    fig_acf_pacf.add_trace(
        go.Bar(x=corr_dict["lags"], y=corr_dict["acf"], name="ACF", marker_color="#627EEA"),
        row=1, col=1,
    )
    # Confidence interval lines for ACF (±1.96/√n)
    ci_bound = 1.96 / (len(series) ** 0.5)
    for val, name_, color_ in [(ci_bound, "+95% CI", "rgba(255,165,0,0.6)"), (-ci_bound, "−95% CI", "rgba(255,165,0,0.6)")]:
        fig_acf_pacf.add_hline(y=val, line_dash="dash", line_color="rgba(255,165,0,0.5)", row=1, col=1)

    # PACF
    fig_acf_pacf.add_trace(
        go.Bar(x=corr_dict["lags"], y=corr_dict["pacf"], name="PACF", marker_color="#F7931A"),
        row=1, col=2,
    )
    for val in [ci_bound, -ci_bound]:
        fig_acf_pacf.add_hline(y=val, line_dash="dash", line_color="rgba(255,165,0,0.5)", row=1, col=2)

    fig_acf_pacf.update_layout(
        paper_bgcolor="#0E1117",
        plot_bgcolor="#161B22",
        font=dict(color="#C9D1D9", family="Inter, sans-serif"),
        showlegend=True,
        height=350,
    )
    fig_acf_pacf.update_xaxes(title_text="Lag", gridcolor="#21262D")
    fig_acf_pacf.update_yaxes(title_text="Correlation", gridcolor="#21262D")

    st.plotly_chart(fig_acf_pacf, use_container_width=True)
    st.caption(
        "**ACF** shows autocorrelation at each lag — helps choose q (MA order). "
        "**PACF** shows partial autocorrelation controlling for shorter lags — helps choose p (AR order). "
        "Orange dashed lines = 95% confidence bounds. Bars outside the bounds are statistically significant."
    )

st.divider()

# ── 2. Run Pipeline & Evaluate ─────────────────────────────────────────────
st.subheader("2. Model Fitting & Out-of-Sample Holdout Evaluation")

with st.spinner("Fitting ARIMA model and generating predictions..."):
    result = run_forecast_pipeline(
        df=df_selected,
        metric=target_metric,
        blockchain=chain_choice.lower(),
        test_size=test_ratio,
        forecast_horizon=horizon,
        order=(p, d, q),
        use_auto_order=use_auto,
        scenario="baseline_forecast",
        is_hypothetical=False,
    )

# Metric Display Cards
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
mae_val = f"{result.mae:.2f}" if result.mae is not None else "N/A"
rmse_val = f"{result.rmse:.2f}" if result.rmse is not None else "N/A"
mape_val = f"{result.mape:.2f}%" if result.mape is not None else "N/A"
aic_val = f"{result.aic:.1f}" if result.aic is not None else "N/A"

m_col1.metric("Model Selected", result.model_name)
m_col2.metric("Holdout MAE", mae_val)
m_col3.metric("Holdout RMSE", rmse_val)
m_col4.metric("Holdout MAPE", mape_val)

# Benchmark comparison vs thesis
if result.mae is not None and chain_choice == "Ethereum" and target_metric == "transaction_count":
    st.subheader("📐 Benchmark: Our Results vs Thesis Reference")
    bench_df = pd.DataFrame([
        {"Metric": "MAE",  "Thesis Value": 27.76,  "Our Value": round(result.mae, 2),  "Unit": "transactions/day"},
        {"Metric": "RMSE", "Thesis Value": 31.16,  "Our Value": round(result.rmse, 2), "Unit": "transactions/day"},
        {"Metric": "MAPE", "Thesis Value": "26.08%", "Our Value": f"{result.mape:.2f}%", "Unit": "%"},
        {"Metric": "AIC",  "Thesis Value": "N/A",   "Our Value": aic_val,               "Unit": "lower is better"},
        {"Metric": "ARIMA Order", "Thesis Value": "ARIMA(5,1,2)", "Our Value": result.model_name, "Unit": "(p,d,q)"},
    ])
    st.dataframe(bench_df, use_container_width=True, hide_index=True)
else:
    st.markdown("""
    > **Metric Definitions:**
    > - **MAE (Mean Absolute Error):** Average magnitude of forecast errors in native units.
    > - **RMSE (Root Mean Squared Error):** Penalizes large deviations more heavily than MAE.
    > - **MAPE (Mean Absolute Percentage Error):** Average relative percentage error against actuals.
    > - Thesis benchmark (ETH transaction count, ARIMA(5,1,2)): MAE≈27.76 | RMSE≈31.16 | MAPE≈26.08%
    """)

st.divider()

# ── 3. Forecast Plot ────────────────────────────────────────────────────────
st.subheader(f"3. Forecast Visualizer: {chain_choice} {target_metric.replace('_', ' ').title()}")
fig_fc = plot_arima_forecast(result, target_metric, show_ci=True)
st.plotly_chart(fig_fc, use_container_width=True)

st.caption(
    "Grey = historical observed. Gold dotted = in-sample test period predictions. "
    "Blue/Red dashed = out-of-sample future forecast. Shaded band = 95% confidence interval. "
    "Dashed vertical line = Ethereum Merge (Sep 15, 2022)."
)

# ── 4. Forecast Output Table ────────────────────────────────────────────────
if result.forecast_df is not None and not result.forecast_df.empty:
    with st.expander("View Future Forecast Data & Download"):
        st.dataframe(result.forecast_df, use_container_width=True)
        csv_fc = result.forecast_df.to_csv(index=False)
        st.download_button("⬇️ Download Forecast CSV", csv_fc, f"{chain_choice}_{target_metric}_forecast.csv", "text/csv")

# ── 5. Model Interpretation ──────────────────────────────────────────────────
st.divider()
st.subheader("4. Model Interpretation & Research Significance")
st.markdown(f"""
**Why ARIMA for this research?**

ARIMA (Autoregressive Integrated Moving Average) captures three structural properties of blockchain time-series:
- **AR(p=5):** Hash rate and transaction count exhibit persistence — today's value depends on the past 5 days
- **I(d=1):** Most blockchain metrics are non-stationary (trending) — first differencing induces stationarity
- **MA(q=2):** Captures short-term shock propagation in the differenced series

**Key insight from ARIMA in this research context:**
By training ARIMA exclusively on the **PoW-era data** and forecasting forward, the model establishes a
**quantitative baseline** for what Ethereum's energy and hash rate *would have been* without the Merge.
The difference between this ARIMA projection and the actual post-Merge near-zero values is the
estimated **environmental benefit** of the consensus transition.

**Model fit (AIC={aic_val}):** A lower AIC indicates a better balance between model complexity and fit.
The MAPE of {mape_val} means the model's forecasts deviate by approximately {mape_val} on average
from the held-out test data.
""")
