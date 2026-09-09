"""
Blockchain.com Public Chart API client.

Provides free historical data (no API key required) for Bitcoin metrics:
  - Transaction count  : /charts/n-transactions
  - Hash rate          : /charts/hash-rate  (GH/s)
  - Miners revenue     : /charts/miners-revenue

Base URL: https://api.blockchain.info/charts

Limitation: Bitcoin only. Does NOT cover Ethereum.
"""
from __future__ import annotations

import pandas as pd

from src.utils.http_client import make_request
from src.utils.logger import logger

_BASE_URL = "https://api.blockchain.info/charts"

CHART_MAP = {
    "transaction_count": "n-transactions",
    "hash_rate":         "hash-rate",         # unit: GH/s
}


def fetch_chart(
    metric_key: str,
    start_date: str,
    end_date: str,
    timespan: str | None = None,
) -> pd.DataFrame:
    """
    Fetch a single Blockchain.com chart metric for Bitcoin.

    Parameters
    ----------
    metric_key : one of CHART_MAP keys
    start_date : ISO-8601 e.g. "2017-01-01"
    end_date   : ISO-8601 e.g. "2023-12-31"
    timespan   : optional override e.g. "5years" (uses start/end by default)

    Returns
    -------
    pd.DataFrame with columns: date, <metric_key>, data_source, blockchain
    """
    if metric_key not in CHART_MAP:
        raise ValueError(f"Unsupported metric '{metric_key}'. Choose from {list(CHART_MAP)}")

    chart = CHART_MAP[metric_key]
    url   = f"{_BASE_URL}/{chart}"

    params: dict = {
        "format":     "json",
        "cors":       "true",
        "start":      start_date,
        "end":        end_date,
        "timespan":   timespan or f"{_date_diff_years(start_date, end_date)}years",
        "rollingAverage": "0days",
        "sampled":    "false",
    }

    logger.info(f"[Blockchain.com] Fetching {chart} from {start_date} to {end_date}")
    data = make_request(url, params=params)

    values = data.get("values", [])
    if not values:
        logger.warning(f"[Blockchain.com] No values returned for {chart}")
        return pd.DataFrame()

    df = pd.DataFrame(values)                          # columns: x (unix ts), y (value)
    df["date"]   = pd.to_datetime(df["x"], unit="s").dt.normalize()
    df[metric_key] = pd.to_numeric(df["y"], errors="coerce")
    df = df[["date", metric_key]].copy()
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

    df["data_source"]  = "Blockchain.com"
    df["blockchain"]   = "bitcoin"

    if metric_key == "hash_rate":
        df["hash_rate_unit"] = "GH/s"

    logger.info(f"[Blockchain.com] Retrieved {len(df)} rows for {chart}")
    return df


def fetch_bitcoin_metrics(start_date: str, end_date: str) -> pd.DataFrame:
    """Convenience function: fetch tx_count + hash_rate and merge."""
    frames = []
    for metric in CHART_MAP:
        df = fetch_chart(metric, start_date, end_date)
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    merged = frames[0]
    for df in frames[1:]:
        merged = pd.merge(
            merged,
            df.drop(columns=["data_source", "blockchain"], errors="ignore"),
            on="date",
            how="outer",
        )

    merged.sort_values("date", inplace=True)
    merged.reset_index(drop=True, inplace=True)
    return merged


# ── helpers ───────────────────────────────────────────────────────────────────
def _date_diff_years(start: str, end: str) -> int:
    from datetime import datetime
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end,   "%Y-%m-%d")
    return max(1, int((e - s).days / 365) + 1)
