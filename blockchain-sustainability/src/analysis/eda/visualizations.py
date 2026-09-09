"""
Exploratory Data Analysis (EDA) module.

Generates Plotly figures used in both the notebook and the dashboard.
All figures clearly label:
  • Data source
  • Units
  • Ethereum Merge date (vertical line on ETH charts)
  • Whether a value is observed, estimated, or hypothetical
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from src.utils.config import ETH_MERGE_DATE

MERGE_COLOR  = "rgba(255, 69, 0, 0.90)"
POW_COLOR    = "#F7931A"    # Bitcoin orange — used for PoW
POS_COLOR    = "#627EEA"    # Ethereum blue — used for PoS
BTC_COLOR    = "#F7931A"
ETH_COLOR    = "#627EEA"
FORECAST_CLR = "#00BFFF"
HYPOTH_CLR   = "#FF4500"

MERGE_DATE_STR = str(ETH_MERGE_DATE)[:10]   # "2022-09-15"


def _add_merge_line(fig: go.Figure, label: str = "The Merge<br>Sep 15 2022<br>PoW → PoS") -> go.Figure:
    """
    Add a vertical dashed line at the Ethereum Merge date plus an annotation label.

    Uses add_shape + add_annotation instead of add_vline to avoid the
    Plotly 5.x `shapeannotation._mean(X)` int+str TypeError bug on Windows.

    Parameters
    ----------
    fig   : Plotly Figure to annotate (mutated in-place and returned)
    label : Text to display beside the line
    """
    fig.add_shape(
        type="line",
        x0=MERGE_DATE_STR,
        x1=MERGE_DATE_STR,
        y0=0,
        y1=1,
        xref="x",
        yref="paper",
        line=dict(color=MERGE_COLOR, width=2, dash="dash"),
    )
    fig.add_annotation(
        x=MERGE_DATE_STR,
        y=0.97,
        xref="x",
        yref="paper",
        text=label,
        showarrow=False,
        font=dict(color=MERGE_COLOR, size=10, family="Inter, sans-serif"),
        align="left",
        xanchor="left",
        bgcolor="rgba(22,27,34,0.75)",
        bordercolor=MERGE_COLOR,
        borderwidth=1,
        borderpad=4,
    )
    return fig


def _dark_layout(title: str, xaxis_title: str = "Date", yaxis_title: str = "") -> dict:
    return dict(
        title=dict(text=title, font=dict(size=18, color="#E0E0E0")),
        paper_bgcolor="#0E1117",
        plot_bgcolor="#161B22",
        font=dict(color="#C9D1D9", family="Inter, sans-serif"),
        xaxis=dict(
            title=xaxis_title,
            gridcolor="#21262D",
            zeroline=False,
            showgrid=True,
        ),
        yaxis=dict(
            title=yaxis_title,
            gridcolor="#21262D",
            zeroline=False,
            showgrid=True,
        ),
        legend=dict(
            bgcolor="rgba(22,27,34,0.8)",
            bordercolor="#30363D",
            borderwidth=1,
        ),
        hovermode="x unified",
        margin=dict(l=60, r=40, t=60, b=60),
    )


# ── Single-metric time-series ─────────────────────────────────────────────────
def plot_metric_over_time(
    df: pd.DataFrame,
    metric: str,
    blockchain: str,
    title: str | None = None,
    yaxis_title: str | None = None,
    show_merge: bool = True,
    color: str | None = None,
) -> go.Figure:
    """
    Line chart for a single blockchain metric over time.
    For Ethereum, adds a vertical line at the Merge date.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)

    col = color or (ETH_COLOR if blockchain.lower() == "ethereum" else BTC_COLOR)
    t   = title or f"{blockchain.title()} — {metric.replace('_', ' ').title()}"
    yt  = yaxis_title or metric.replace("_", " ").title()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df[metric],
        mode="lines",
        name=blockchain.title(),
        line=dict(color=col, width=1.8),
        hovertemplate="%{x|%Y-%m-%d}<br>" + yt + ": %{y:,.2f}<extra></extra>",
    ))

    if show_merge and blockchain.lower() == "ethereum":
        _add_merge_line(fig)

    fig.update_layout(**_dark_layout(t, yaxis_title=yt))
    return fig


# ── Side-by-side ETH vs BTC ───────────────────────────────────────────────────
def plot_eth_btc_comparison(
    df_eth: pd.DataFrame,
    df_btc: pd.DataFrame,
    metric: str,
    yaxis_title: str = "",
) -> go.Figure:
    """Overlay Ethereum and Bitcoin on the same chart for a given metric."""
    df_eth = df_eth.copy()
    df_btc = df_btc.copy()
    df_eth["date"] = pd.to_datetime(df_eth["date"])
    df_btc["date"] = pd.to_datetime(df_btc["date"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_eth["date"], y=df_eth[metric],
        name="Ethereum", line=dict(color=ETH_COLOR, width=1.8),
    ))
    fig.add_trace(go.Scatter(
        x=df_btc["date"], y=df_btc[metric],
        name="Bitcoin", line=dict(color=BTC_COLOR, width=1.8),
    ))
    _add_merge_line(fig)

    title = f"Ethereum vs Bitcoin — {metric.replace('_', ' ').title()}"
    fig.update_layout(**_dark_layout(title, yaxis_title=yaxis_title or metric))
    return fig


# ── Correlation heatmap ────────────────────────────────────────────────────────
def plot_correlation_heatmap(corr_matrix: pd.DataFrame, title: str = "Correlation Matrix") -> go.Figure:
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(),
        colorscale="RdBu",
        zmid=0,
        zmin=-1, zmax=1,
        text=[[f"{v:.4f}" for v in row] for row in corr_matrix.values],
        texttemplate="%{text}",
        hovertemplate="x=%{x}<br>y=%{y}<br>r=%{z:.4f}<extra></extra>",
        colorbar=dict(title="r"),
    ))
    fig.update_layout(**_dark_layout(title))
    return fig


# ── Scatter plot with regression line ─────────────────────────────────────────
def plot_scatter_regression(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str | None = None,
    color_col: str | None = None,
) -> go.Figure:
    """Scatter plot with OLS regression line."""
    import numpy as np
    from scipy import stats

    valid = df[[x_col, y_col]].dropna()
    slope, intercept, r_val, p_val, _ = stats.linregress(valid[x_col], valid[y_col])

    x_range = np.linspace(valid[x_col].min(), valid[x_col].max(), 100)
    y_pred  = slope * x_range + intercept

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=valid[x_col], y=valid[y_col],
        mode="markers",
        marker=dict(color=ETH_COLOR, opacity=0.5, size=4),
        name="Data",
    ))
    fig.add_trace(go.Scatter(
        x=x_range, y=y_pred,
        mode="lines",
        line=dict(color=MERGE_COLOR, width=2, dash="dash"),
        name=f"OLS fit (r={r_val:.4f}, p={p_val:.4f})",
    ))

    t = title or f"{x_col.replace('_',' ')} vs {y_col.replace('_',' ')}"
    fig.update_layout(**_dark_layout(t, xaxis_title=x_col, yaxis_title=y_col))
    return fig


# ── ARIMA forecast plot ────────────────────────────────────────────────────────
def plot_arima_forecast(
    result,
    metric: str,
    show_ci: bool = True,
) -> go.Figure:
    """
    Plot historical data + ARIMA forecast + confidence interval.
    Works for both baseline and counterfactual scenarios.
    """
    fig = go.Figure()

    # Historical
    if result.history_df is not None:
        hist = result.history_df.copy()
        hist["date"] = pd.to_datetime(hist["date"])
        fig.add_trace(go.Scatter(
            x=hist["date"], y=hist[metric],
            name="Historical (Observed)", mode="lines",
            line=dict(color="#C9D1D9", width=1.5),
            hovertemplate="%{x|%Y-%m-%d}<br>Observed: %{y:,.2f}<extra></extra>",
        ))

    # Test predictions (in-sample)
    if result.test_df is not None and "predicted" in result.test_df.columns:
        td = result.test_df.copy()
        td["date"] = pd.to_datetime(td["date"])
        fig.add_trace(go.Scatter(
            x=td["date"], y=td["predicted"],
            name="Model — Test Period", mode="lines",
            line=dict(color="#FFD700", width=1.8, dash="dot"),
            hovertemplate="%{x|%Y-%m-%d}<br>Predicted: %{y:,.2f}<extra></extra>",
        ))

    # Future forecast
    if result.forecast_df is not None:
        fd = result.forecast_df.copy()
        fd["date"] = pd.to_datetime(fd["date"])
        fc_color = HYPOTH_CLR if result.is_hypothetical else FORECAST_CLR
        fc_label = ("Hypothetical PoW Continuation" if result.is_hypothetical
                    else f"Forecast ({result.model_name})")

        fig.add_trace(go.Scatter(
            x=fd["date"], y=fd["forecast"],
            name=fc_label, mode="lines",
            line=dict(color=fc_color, width=2.5, dash="dash"),
            hovertemplate="%{x|%Y-%m-%d}<br>Forecast: %{y:,.2f}<extra></extra>",
        ))
        if show_ci and "upper_ci_95" in fd.columns and "lower_ci_95" in fd.columns:
            try:
                r = int(fc_color.lstrip("#")[0:2], 16)
                g = int(fc_color.lstrip("#")[2:4], 16)
                b = int(fc_color.lstrip("#")[4:6], 16)
                fill_color = f"rgba({r},{g},{b},0.15)"
            except Exception:
                fill_color = "rgba(0,191,255,0.15)"

            fig.add_trace(go.Scatter(
                x=pd.concat([fd["date"], fd["date"][::-1]]),
                y=pd.concat([fd["upper_ci_95"], fd["lower_ci_95"][::-1]]),
                fill="toself",
                fillcolor=fill_color,
                line=dict(color="rgba(0,0,0,0)"),
                name="95% CI",
                hoverinfo="skip",
            ))

    # Merge line for ETH
    _add_merge_line(fig)

    title = (
        "Counterfactual PoW Forecast — Ethereum (HYPOTHETICAL)"
        if result.is_hypothetical
        else f"ARIMA Forecast — {metric.replace('_',' ').title()}"
    )
    fig.update_layout(**_dark_layout(title, yaxis_title=metric.replace("_", " ").title()))
    return fig


# ── PoW vs PoS bar comparison ─────────────────────────────────────────────────
def plot_pow_pos_comparison(change_df: pd.DataFrame) -> go.Figure:
    """Bar chart of percentage change from PoW to PoS for each Ethereum metric."""
    fig = go.Figure()
    colors = [POS_COLOR if v < 0 else "#FF4500" for v in change_df["pct_change"]]
    fig.add_trace(go.Bar(
        x=change_df["metric"].str.replace("_", " ").str.title(),
        y=change_df["pct_change"],
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in change_df["pct_change"]],
        textposition="outside",
        hovertemplate="%{x}<br>Change: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(**_dark_layout(
        "Ethereum: PoW → PoS Transition — Mean Metric Changes",
        xaxis_title="Metric",
        yaxis_title="% Change",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="grey")
    return fig


# ── Energy time-series overlay (ETH + BTC) ────────────────────────────────────
def plot_energy_comparison_overlay(
    df_eth: pd.DataFrame,
    df_btc: pd.DataFrame,
) -> go.Figure:
    """
    Dual-series energy overlay showing Ethereum PoW collapse and Bitcoin's continued growth.
    Uses a log-scale Y axis to handle the 99.95% drop in ETH energy.
    """
    df_eth = df_eth.copy()
    df_btc = df_btc.copy()
    df_eth["date"] = pd.to_datetime(df_eth["date"])
    df_btc["date"] = pd.to_datetime(df_btc["date"])

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_eth["date"], y=df_eth["energy_consumption"],
        name="Ethereum Energy (TWh/year)",
        line=dict(color=ETH_COLOR, width=2),
        hovertemplate="%{x|%Y-%m-%d}<br>ETH Energy: %{y:.4f} TWh/yr<extra></extra>",
    ))

    if not df_btc.empty and "energy_consumption" in df_btc.columns:
        fig.add_trace(go.Scatter(
            x=df_btc["date"], y=df_btc["energy_consumption"],
            name="Bitcoin Energy (TWh/year)",
            line=dict(color=BTC_COLOR, width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>BTC Energy: %{y:.2f} TWh/yr<extra></extra>",
        ))

    _add_merge_line(fig)

    layout = _dark_layout(
        "Energy Consumption Comparison: Ethereum vs Bitcoin (2017–2024)",
        yaxis_title="Energy (TWh/year) — Log Scale",
    )
    layout["yaxis"]["type"] = "log"
    fig.update_layout(**layout)
    return fig
