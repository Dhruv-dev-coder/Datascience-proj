"""
Unit tests for data cleaning pipeline.
"""
import pytest
import pandas as pd
import numpy as np
from src.data.cleaners.cleaner import clean_dataframe


def test_cleaner_removes_duplicates():
    df = pd.DataFrame({
        "date": ["2022-01-01", "2022-01-01", "2022-01-02"],
        "blockchain": ["ethereum", "ethereum", "ethereum"],
        "transaction_count": [100, 200, 300],
        "consensus": ["PoW", "PoW", "PoW"]
    })
    cleaned = clean_dataframe(df, "ethereum")
    assert len(cleaned) == 2
    assert cleaned["transaction_count"].iloc[0] == 200  # keep="last"


def test_cleaner_fills_calendar_gaps():
    df = pd.DataFrame({
        "date": ["2022-01-01", "2022-01-03"],  # missing Jan 2
        "blockchain": ["ethereum", "ethereum"],
        "transaction_count": [100.0, 300.0],
        "consensus": ["PoW", "PoW"]
    })
    cleaned = clean_dataframe(df, "ethereum")
    assert len(cleaned) == 3
    assert pd.to_datetime("2022-01-02") in cleaned["date"].values
    # Short gap <= 3 days should be forward filled
    assert cleaned.loc[cleaned["date"] == "2022-01-02", "transaction_count"].iloc[0] == 100.0


def test_cleaner_handles_negative_values():
    df = pd.DataFrame({
        "date": ["2022-01-01", "2022-01-02"],
        "blockchain": ["bitcoin", "bitcoin"],
        "transaction_count": [-50.0, 100.0],
        "consensus": ["PoW", "PoW"]
    })
    cleaned = clean_dataframe(df, "bitcoin")
    assert np.isnan(cleaned.loc[cleaned["date"] == "2022-01-01", "transaction_count"].iloc[0])
