"""
Unit tests for correlation analysis calculations.
"""
import pytest
import pandas as pd
import numpy as np
from src.analysis.correlation.correlation import (
    pearson,
    spearman,
    correlation_matrix,
    eth_pow_correlations,
)


def test_pearson_perfect_correlation():
    df = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0, 5.0],
        "y": [2.0, 4.0, 6.0, 8.0, 10.0],
    })
    res = pearson(df, "x", "y")
    assert round(res.r, 4) == 1.0
    assert res.p_value < 0.001
    assert "very strong" in res.interpretation


def test_spearman_monotonic_relationship():
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [1, 8, 27, 64, 125],  # non-linear monotonic (y = x^3)
    })
    res = spearman(df, "x", "y")
    assert round(res.r, 4) == 1.0


def test_correlation_matrix_shape():
    df = pd.DataFrame({
        "a": [1, 2, 3, 4],
        "b": [4, 3, 2, 1],
        "c": [2, 3, 2, 3],
    })
    mat = correlation_matrix(df, ["a", "b", "c"])
    assert mat.shape == (3, 3)
    assert mat.loc["a", "b"] == -1.0


def test_eth_pow_correlations_logic():
    df = pd.DataFrame({
        "consensus": ["PoW", "PoW", "PoW", "PoW", "PoS"],
        "hash_rate": [10.0, 20.0, 30.0, 40.0, 0.0],
        "energy_consumption": [2.0, 4.0, 6.0, 8.0, 0.0026],
        "transaction_count": [100.0, 105.0, 95.0, 102.0, 110.0],
    })
    results = eth_pow_correlations(df)
    # 3 pairs * 2 methods (Pearson, Spearman) = 6 results
    assert len(results) == 6
    hr_energy_pearson = next(r for r in results if r.x_name == "hash_rate" and r.y_name == "energy_consumption" and r.method == "Pearson")
    assert hr_energy_pearson.r > 0.95
