"""
ARIMA Forecasting Module.

Implements:
  1. Stationarity analysis (Augmented Dickey-Fuller test)
  2. ACF / PACF computation
  3. ARIMA model fitting (baseline ARIMA(5,1,2) as per thesis + auto-order selection)
  4. Train / test split and in-sample evaluation
  5. Forecast with confidence intervals
  6. Counterfactual "continued PoW" scenario generation
  7. Forecast validation metrics: MAE, RMSE, MAPE

ARIMA Order
───────────
The thesis reports ARIMA(5,1,2) as its specification.
This module:
  • Always fits ARIMA(5,1,2) as the "thesis baseline" model.
  • Optionally auto-selects order using pmdarima.auto_arima.
  • Reports which model produced which results.

IMPORTANT LABELS:
  • Any forecast beyond the actual data range is labelled "FORECAST".
  • Any forecast produced from PoW-era data extended past the Merge is labelled
    "HYPOTHETICAL / COUNTERFACTUAL — PoW Continuation Scenario".
  • These labels must NEVER be omitted in output DataFrames or visualisations.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller, acf, pacf
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.utils.logger import logger

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


# ── Dataclasses ───────────────────────────────────────────────────────────────
@dataclass
class ADFResult:
    adf_statistic: float
    p_value:       float
    n_lags:        int
    n_obs:         int
    critical_values: dict
    is_stationary:   bool
    interpretation:  str


@dataclass
class ARIMAForecastResult:
    model_name:    str
    order:         Tuple[int, int, int]
    scenario:      str
    is_hypothetical: bool

    # Evaluation (only if test set available)
    mae:  Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    aic:  Optional[float] = None
    bic:  Optional[float] = None

    # DataFrames
    train_df:    Optional[pd.DataFrame] = None
    test_df:     Optional[pd.DataFrame] = None
    forecast_df: Optional[pd.DataFrame] = None   # future forecast
    history_df:  Optional[pd.DataFrame] = None   # full historical series


# ── Stationarity ──────────────────────────────────────────────────────────────
def adf_test(series: pd.Series, name: str = "series") -> ADFResult:
    """
    Augmented Dickey-Fuller test for unit root (non-stationarity).

    H₀: Series has a unit root (non-stationary).
    H₁: Series is stationary.

    Reject H₀ (and conclude stationarity) when p-value < 0.05.
    """
    clean = series.dropna()
    result = adfuller(clean, autolag="AIC")

    adf_stat = result[0]
    p_value  = result[1]
    n_lags   = result[2]
    n_obs    = result[3]
    crit     = result[4]

    is_stationary = p_value < 0.05
    interp = (
        f"ADF statistic={adf_stat:.4f}, p={p_value:.4f}. "
        + ("The series appears STATIONARY (reject H₀). " if is_stationary
           else "The series appears NON-STATIONARY (fail to reject H₀). Differencing may be required. ")
        + f"Critical values: {crit}"
    )
    logger.info(f"[ADF:{name}] {interp}")
    return ADFResult(
        adf_statistic=adf_stat,
        p_value=p_value,
        n_lags=n_lags,
        n_obs=n_obs,
        critical_values=crit,
        is_stationary=is_stationary,
        interpretation=interp,
    )


def compute_acf_pacf(series: pd.Series, nlags: int = 40) -> dict:
    """Compute ACF and PACF arrays for plotting."""
    clean = series.dropna()
    acf_vals,  acf_ci  = acf(clean,  nlags=nlags, alpha=0.05)
    pacf_vals, pacf_ci = pacf(clean, nlags=nlags, alpha=0.05, method="ywm")
    return {
        "lags":     list(range(len(acf_vals))),
        "acf":      acf_vals.tolist(),
        "acf_ci":   acf_ci.tolist(),
        "pacf":     pacf_vals.tolist(),
        "pacf_ci":  pacf_ci.tolist(),
    }


# ── ARIMA fitting ─────────────────────────────────────────────────────────────
def fit_arima(
    series: pd.Series,
    order: Tuple[int, int, int] = (5, 1, 2),
) -> ARIMA:
    """Fit an ARIMA(p,d,q) model and return the fitted result."""
    model = ARIMA(series.dropna(), order=order)
    fitted = model.fit()
    logger.info(
        f"[ARIMA{order}] AIC={fitted.aic:.2f} | BIC={fitted.bic:.2f}"
    )
    return fitted


def auto_select_order(series: pd.Series, max_p: int = 5, max_q: int = 5) -> Tuple[int, int, int]:
    """
    Use pmdarima.auto_arima to select optimal order automatically.
    Falls back to (5,1,2) if pmdarima is unavailable.
    """
    try:
        import pmdarima as pm
        model = pm.auto_arima(
            series.dropna(),
            start_p=0, max_p=max_p,
            start_q=0, max_q=max_q,
            d=None,
            information_criterion="aic",
            stepwise=True,
            seasonal=False,
            error_action="ignore",
            suppress_warnings=True,
        )
        order = model.order
        logger.info(f"[AutoARIMA] Selected order: {order}")
        return order
    except ImportError:
        logger.warning("pmdarima not available. Using thesis default ARIMA(5,1,2).")
        return (5, 1, 2)


# ── Evaluation metrics ────────────────────────────────────────────────────────
def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean Absolute Percentage Error — excludes zero-valued actuals."""
    mask = actual != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def evaluate(actual: np.ndarray, predicted: np.ndarray) -> dict:
    mae  = float(mean_absolute_error(actual, predicted))
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    mape = _mape(actual, predicted)
    accuracy = max(0.0, 100.0 - mape)   # as reported in thesis: 100 - MAPE
    logger.info(f"[Eval] MAE={mae:.4f} | RMSE={rmse:.4f} | MAPE={mape:.2f}% | Accuracy≈{accuracy:.2f}%")
    return {"mae": mae, "rmse": rmse, "mape": mape, "accuracy": accuracy}


# ── Full forecast pipeline ────────────────────────────────────────────────────
def run_forecast_pipeline(
    df: pd.DataFrame,
    metric: str,
    blockchain: str,
    test_size: float = 0.2,
    forecast_horizon: int = 180,
    order: Tuple[int, int, int] = (5, 1, 2),
    use_auto_order: bool = False,
    scenario: str = "baseline",
    is_hypothetical: bool = False,
) -> ARIMAForecastResult:
    """
    Full ARIMA pipeline:
      1. Prepare series
      2. ADF stationarity test
      3. Train/test split
      4. Fit model
      5. In-sample test evaluation
      6. Future forecast with confidence intervals

    Parameters
    ----------
    df               : DataFrame with 'date' and <metric> columns
    metric           : metric column name
    blockchain       : "ethereum" | "bitcoin"
    test_size        : fraction of data to hold out for evaluation
    forecast_horizon : number of future days to forecast
    order            : ARIMA (p, d, q)
    use_auto_order   : if True, override order with auto_arima selection
    scenario         : label for this forecast run
    is_hypothetical  : if True, marks result as hypothetical/counterfactual
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    series = df[metric].copy()

    # ── ADF test (informational) ──────────────────────────────────────────────
    adf = adf_test(series, name=f"{blockchain}/{metric}")

    # If auto-order requested, override
    if use_auto_order:
        order = auto_select_order(series)

    model_name = f"ARIMA{order}"

    # ── Train / test split ────────────────────────────────────────────────────
    n        = len(series.dropna())
    n_test   = max(int(n * test_size), 1)
    n_train  = n - n_test

    train_series = series.iloc[:n_train]
    test_series  = series.iloc[n_train:]

    train_dates  = df["date"].iloc[:n_train]
    test_dates   = df["date"].iloc[n_train:]

    logger.info(
        f"[{model_name}] {blockchain}/{metric} | "
        f"Train: {len(train_series)} | Test: {len(test_series)} | "
        f"Forecast horizon: {forecast_horizon} days"
    )

    # ── Fit on training data ──────────────────────────────────────────────────
    try:
        fitted_model = fit_arima(train_series, order=order)
    except Exception as exc:
        logger.error(f"[{model_name}] Fit failed: {exc}")
        return ARIMAForecastResult(
            model_name=model_name, order=order,
            scenario=scenario, is_hypothetical=is_hypothetical,
        )

    # ── In-sample forecast on test set ────────────────────────────────────────
    try:
        test_pred = fitted_model.forecast(steps=len(test_series))
        metrics   = evaluate(test_series.values, test_pred.values)
    except Exception as exc:
        logger.warning(f"[{model_name}] Test forecast failed: {exc}")
        metrics = {}

    # ── Refit on full series for future forecast ──────────────────────────────
    try:
        full_model = fit_arima(series, order=order)
        forecast_res = full_model.get_forecast(steps=forecast_horizon)
        forecast_mean = forecast_res.predicted_mean
        forecast_ci   = forecast_res.conf_int(alpha=0.05)
    except Exception as exc:
        logger.error(f"[{model_name}] Future forecast failed: {exc}")
        return ARIMAForecastResult(
            model_name=model_name, order=order,
            scenario=scenario, is_hypothetical=is_hypothetical,
            **metrics,
        )

    # ── Build forecast DataFrame ──────────────────────────────────────────────
    last_date = df["date"].iloc[-1]
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=forecast_horizon,
        freq="D",
    )
    label = "HYPOTHETICAL / COUNTERFACTUAL — PoW Continuation Scenario" if is_hypothetical else "FORECAST"

    forecast_df = pd.DataFrame({
        "date":          future_dates,
        "forecast":      forecast_mean.values,
        "lower_ci_95":   forecast_ci.iloc[:, 0].values,
        "upper_ci_95":   forecast_ci.iloc[:, 1].values,
        "label":         label,
        "is_hypothetical": is_hypothetical,
        "metric":        metric,
        "blockchain":    blockchain,
        "scenario":      scenario,
        "model":         model_name,
    })

    # Build train/test DataFrames for plotting
    train_df = pd.DataFrame({"date": train_dates, metric: train_series.values, "split": "train"})
    test_df  = pd.DataFrame({
        "date":      test_dates,
        metric:      test_series.values,
        "predicted": test_pred.values if "mae" in metrics else np.nan,
        "split":     "test",
    })

    return ARIMAForecastResult(
        model_name=model_name,
        order=order,
        scenario=scenario,
        is_hypothetical=is_hypothetical,
        mae=metrics.get("mae"),
        rmse=metrics.get("rmse"),
        mape=metrics.get("mape"),
        aic=float(full_model.aic),
        bic=float(full_model.bic),
        train_df=train_df,
        test_df=test_df,
        forecast_df=forecast_df,
        history_df=df[["date", metric]].copy(),
    )


# ── Counterfactual scenario ───────────────────────────────────────────────────
def run_counterfactual_pow(
    df_eth: pd.DataFrame,
    metric: str = "hash_rate",
    forecast_horizon: int = 365,
    order: Tuple[int, int, int] = (5, 1, 2),
) -> ARIMAForecastResult:
    """
    Train ARIMA on Ethereum's PoW-era data and project forward past the Merge.

    This generates the HYPOTHETICAL trajectory: "What if Ethereum had NOT merged?"

    Parameters
    ----------
    df_eth           : Full Ethereum DataFrame (all dates)
    metric           : "hash_rate" or "energy_consumption"
    forecast_horizon : Number of days to project past the Merge
    order            : ARIMA order (thesis default: (5,1,2))

    Returns
    -------
    ARIMAForecastResult with is_hypothetical=True
    """
    pow_df = df_eth[df_eth["consensus"] == "PoW"].copy()
    logger.info(
        f"[Counterfactual] Training on Ethereum PoW-era {metric} "
        f"({len(pow_df)} rows). Projecting {forecast_horizon} days forward."
    )

    result = run_forecast_pipeline(
        df=pow_df,
        metric=metric,
        blockchain="ethereum",
        test_size=0.15,
        forecast_horizon=forecast_horizon,
        order=order,
        scenario="counterfactual_pow",
        is_hypothetical=True,
    )

    # Add explanatory note to forecast_df
    if result.forecast_df is not None:
        result.forecast_df["note"] = (
            "This forecast is a MODEL-BASED HYPOTHETICAL projection. "
            "It assumes that historical Ethereum PoW computational and energy patterns "
            "would have continued beyond the September 2022 Merge. "
            "It is NOT actual Ethereum data and should NOT be interpreted as a factual "
            "reconstruction of what would have occurred."
        )

    return result
