"""
Unit tests for data validation module.
"""
import pytest
import pandas as pd
from src.data.validators.validator import validate


def test_validator_detects_missing_required_columns():
    df = pd.DataFrame({"date": [pd.to_datetime("2022-01-01")]})
    report = validate(df, "ethereum")
    assert not report.is_valid
    assert any("blockchain" in err for err in report.errors)


def test_validator_passes_valid_dataframe():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2022-01-01", "2022-01-02"]),
        "blockchain": ["ethereum", "ethereum"],
        "consensus": ["PoW", "PoW"],
        "transaction_count": [100000.0, 110000.0],
        "hash_rate": [800.0, 810.0],
        "energy_consumption": [50.0, 51.0],
    })
    report = validate(df, "ethereum")
    assert report.is_valid
    assert len(report.errors) == 0


def test_validator_detects_negative_metrics():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2022-01-01"]),
        "blockchain": ["bitcoin"],
        "consensus": ["PoW"],
        "transaction_count": [-10.0],
    })
    report = validate(df, "bitcoin")
    assert not report.is_valid
    assert any("negative" in err for err in report.errors)
