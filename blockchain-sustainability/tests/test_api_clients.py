"""
Unit tests for API clients with mocked HTTP responses.
Ensures parser correctness without requiring live network calls.
"""
import pytest
import pandas as pd
from unittest.mock import patch

from src.data.api_clients import coinmetrics_client, blockchain_com_client, energy_client


@pytest.fixture
def mock_coinmetrics_response():
    return {
        "data": [
            {"time": "2022-01-01T00:00:00.000Z", "TxCnt": "1200000", "HashRate": "850.5"},
            {"time": "2022-01-02T00:00:00.000Z", "TxCnt": "1250000", "HashRate": "860.2"},
        ],
        "next_page_url": None,
    }


@pytest.fixture
def mock_blockchain_response():
    return {
        "status": "ok",
        "name": "n-transactions",
        "unit": "Transactions",
        "values": [
            {"x": 1640995200, "y": 250000},  # 2022-01-01
            {"x": 1641081600, "y": 260000},  # 2022-01-02
        ],
    }


def test_coinmetrics_fetch_metrics(mock_coinmetrics_response):
    with patch("src.data.api_clients.coinmetrics_client.make_request", return_value=mock_coinmetrics_response):
        df = coinmetrics_client.fetch_metrics("ethereum", "2022-01-01", "2022-01-02")
        assert not df.empty
        assert "transaction_count" in df.columns
        assert "hash_rate" in df.columns
        assert df["transaction_count"].iloc[0] == 1200000
        assert df["hash_rate"].iloc[1] == 860.2
        assert df["data_source"].iloc[0] == "Coin Metrics"
        assert df["hash_rate_unit"].iloc[0] == "TH/s"


def test_blockchain_com_fetch_chart(mock_blockchain_response):
    with patch("src.data.api_clients.blockchain_com_client.make_request", return_value=mock_blockchain_response):
        df = blockchain_com_client.fetch_chart("transaction_count", "2022-01-01", "2022-01-02")
        assert not df.empty
        assert "transaction_count" in df.columns
        assert df["transaction_count"].iloc[0] == 250000
        assert df["blockchain"].iloc[0] == "bitcoin"


def test_energy_estimation_from_hashrate():
    sample_df = pd.DataFrame({
        "hash_rate": [100.0, 200.0],
        "blockchain": ["ethereum", "ethereum"],
    })
    res = energy_client.estimate_energy_from_hashrate(sample_df, "ethereum", "hash_rate", "TH/s")
    assert "energy_consumption" in res.columns
    assert "energy_unit" in res.columns
    assert res["energy_unit"].iloc[0] == "TWh/year"
    # Power = 100 * 70 = 7000 W = 7e-6 GW. 7e-6 * 8760 / 1000 = ~0.06132
    assert res["energy_consumption"].iloc[0] > 0
    assert res["energy_consumption"].iloc[1] > res["energy_consumption"].iloc[0]
