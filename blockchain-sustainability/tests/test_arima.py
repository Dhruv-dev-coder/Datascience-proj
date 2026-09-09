"""
Unit tests for ARIMA forecasting and counterfactual pipeline.
"""
import pytest
import pandas as pd
import numpy as np
from src.analysis.forecasting.arima_model import (
    adf_test,
    evaluate,
    run_forecast_pipeline,
    run_counterfactual_pow,
)


def test_evaluate_metrics():
    actual = np.array([100.0, 105.0, 110.0])
    predicted = np.array([98.0, 107.0, 112.0])
    res = evaluate(actual, predicted)
    assert "mae" in res
    assert "rmse" in res
    assert "mape" in res
    assert res["mae"] == pytest.approx(2.0, rel=1e-2)
    assert res["accuracy"] > 95.0


def test_adf_stationary_detection():
    # Stationary series (white noise)
    np.random.seed(42)
    series = pd.Series(np.random.normal(0, 1, 200))
    res = adf_test(series, "white_noise")
    assert res.is_stationary
    assert res.p_value < 0.05


def test_run_forecast_pipeline():
    np.random.seed(42)
    dates = pd.date_range("2022-01-01", periods=100, freq="D")
    vals = 50 + np.cumsum(np.random.normal(0, 1, 100))  # random walk
    df = pd.DataFrame({"date": dates, "val": vals})

    res = run_forecast_pipeline(
        df=df,
        metric="val",
        blockchain="ethereum",
        test_size=0.15,
        forecast_horizon=10,
        order=(1, 1, 1),
    )
    assert res.forecast_df is not None
    assert len(res.forecast_df) == 10
    assert "lower_ci_95" in res.forecast_df.columns
    assert "upper_ci_95" in res.forecast_df.columns
    assert res.mae is not None


def test_counterfactual_pow_tagging():
    dates = pd.date_range("2022-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "consensus": ["PoW" if d < pd.to_datetime("2022-02-15") else "PoS" for d in dates],
        "hash_rate": [10.0 + i * 0.5 for i in range(60)],
    })
    cf_res = run_counterfactual_pow(df, "hash_rate", forecast_horizon=15, order=(1, 1, 0))
    assert cf_res.is_hypothetical
    assert "note" in cf_res.forecast_df.columns
    assert "HYPOTHETICAL" in cf_res.forecast_df["label"].iloc[0]
