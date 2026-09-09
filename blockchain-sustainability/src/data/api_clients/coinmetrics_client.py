"""
Coin Metrics Community API client.

Coin Metrics provides free-tier access to many blockchain metrics including:
  - Transaction count  (TxCnt)
  - Hash rate          (HashRate)
  - Estimated daily hash power (computed from difficulty)

Docs: https://docs.coinmetrics.io/api/v4
Base URL: https://community-api.coinmetrics.io/v4

No API key is required for Community endpoints.
A paid key unlocks higher rate limits and more metrics.
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Generator

import pandas as pd

from src.utils.config import COINMETRICS_API_KEY, API_RATE_LIMIT_SECONDS
from src.utils.http_client import make_request
from src.utils.logger import logger

_BASE_URL = "https://community-api.coinmetrics.io/v4"
_HEADERS: dict = {}
if COINMETRICS_API_KEY:
    _HEADERS["Authorization"] = f"Bearer {COINMETRICS_API_KEY}"

# Coin Metrics asset identifiers
_ASSET_MAP = {
    "ethereum": "eth",
    "bitcoin":  "btc",
}

# Metric identifiers available on the Community tier
# Reference: https://docs.coinmetrics.io/info/metrics
METRIC_ALIASES = {
    "transaction_count": "TxCnt",
    "hash_rate":         "HashRate",   # mean hash rate (EH/s for BTC, TH/s for ETH)
    "fees_usd":          "FeeTotUSD",  # not used in core analysis but useful
}


def _paginate_timeseries(
    asset: str,
    metrics: list[str],
    start_time: str,
    end_time: str,
    frequency: str = "1d",
) -> list[dict]:
    """
    Fetch all pages of /timeseries/asset-metrics for a single asset.
    Handles cursor-based pagination.
    """
    url    = f"{_BASE_URL}/timeseries/asset-metrics"
    params = {
        "assets":    asset,
        "metrics":   ",".join(metrics),
        "start_time": start_time,
        "end_time":   end_time,
        "frequency":  frequency,
        "page_size":  1000,
    }

    all_rows: list[dict] = []
    while True:
        data = make_request(url, params=params, headers=_HEADERS)
        rows = data.get("data", [])
        all_rows.extend(rows)
        next_page = data.get("next_page_url")
        if not next_page:
            break
        # next_page_url contains full URL with cursor baked in
        url    = next_page
        params = {}
        time.sleep(API_RATE_LIMIT_SECONDS)

    return all_rows


def fetch_metrics(
    blockchain: str,
    start_date: str,
    end_date: str,
    metric_keys: list[str] | None = None,
) -> pd.DataFrame:
    """
    Download daily metrics from Coin Metrics Community API.

    Parameters
    ----------
    blockchain  : "ethereum" or "bitcoin"
    start_date  : ISO-8601 date string  e.g. "2017-01-01"
    end_date    : ISO-8601 date string  e.g. "2023-12-31"
    metric_keys : subset of METRIC_ALIASES keys; defaults to all

    Returns
    -------
    pd.DataFrame with columns: date, transaction_count, hash_rate
    """
    asset = _ASSET_MAP.get(blockchain.lower())
    if asset is None:
        raise ValueError(f"Unsupported blockchain '{blockchain}'")

    if metric_keys is None:
        metric_keys = list(METRIC_ALIASES.keys())

    cm_metrics = [METRIC_ALIASES[k] for k in metric_keys if k in METRIC_ALIASES]
    logger.info(
        f"[CoinMetrics] Fetching {cm_metrics} for {asset} "
        f"from {start_date} to {end_date}"
    )

    rows = _paginate_timeseries(
        asset=asset,
        metrics=cm_metrics,
        start_time=start_date,
        end_time=end_date,
    )

    if not rows:
        logger.warning(f"[CoinMetrics] No data returned for {asset}")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"]).dt.normalize()
    df = df.rename(columns={"time": "date"})

    # Rename CM metric names to our standard column names
    reverse_map = {v: k for k, v in METRIC_ALIASES.items()}
    df = df.rename(columns={cm: our for cm, our in reverse_map.items() if cm in df.columns})

    # Cast to numeric
    for col in ["transaction_count", "hash_rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["data_source"] = "Coin Metrics"
    df["blockchain"]  = blockchain.lower()

    # Hash rate unit varies by asset
    if "hash_rate" in df.columns:
        df["hash_rate_unit"] = "EH/s" if blockchain.lower() == "bitcoin" else "TH/s"

    logger.info(f"[CoinMetrics] Retrieved {len(df)} rows for {blockchain}")
    return df
