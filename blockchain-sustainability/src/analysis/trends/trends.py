"""
Trend analysis module.

Provides:
  • Period-level aggregation (daily, weekly, monthly)
  • Pre/post Merge comparison statistics
  • Percentage change calculations
  • Rolling window statistics
"""
from __future__ import annotations

from typing import Literal

import pandas as pd
import numpy as np

from src.utils.config import ETH_MERGE_DATE
from src.utils.logger import logger

MERGE_DATE = pd.to_datetime(ETH_MERGE_DATE)

AggFreq = Literal["D", "W", "M", "Q", "Y"]   # pandas resample frequencies (pandas 2.1.x compatible)


def aggregate(
    df: pd.DataFrame,
    freq: AggFreq = "ME",
    numeric_agg: str = "mean",
) -> pd.DataFrame:
    """
    Resample a time-series DataFrame to a lower frequency.

    Parameters
    ----------
    df          : DataFrame with a 'date' column (datetime)
    freq        : pandas resample frequency string
    numeric_agg : aggregation function for numeric columns ('mean', 'sum', 'median')
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    numeric_cols = df.select_dtypes(include="number").columns
    string_cols  = df.select_dtypes(exclude="number").columns

    resampled_num = df[numeric_cols].resample(freq).agg(numeric_agg)
    resampled_str = df[string_cols].resample(freq).first()

    result = pd.concat([resampled_num, resampled_str], axis=1)
    result.index.name = "date"
    result.reset_index(inplace=True)
    return result


def split_pre_post_merge(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split Ethereum DataFrame into PoW (pre-Merge) and PoS (post-Merge) periods.
    """
    df["date"] = pd.to_datetime(df["date"])
    pre  = df[df["date"] <  MERGE_DATE].copy()
    post = df[df["date"] >= MERGE_DATE].copy()
    logger.info(f"Pre-Merge rows: {len(pre)} | Post-Merge rows: {len(post)}")
    return pre, post


def period_statistics(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """
    Compute descriptive statistics for each numeric column.
    Returns a DataFrame suitable for display.
    """
    numeric = df.select_dtypes(include="number")
    stats   = numeric.describe().T
    stats["period"] = label
    stats.reset_index(inplace=True)
    stats.rename(columns={"index": "metric"}, inplace=True)
    return stats


def compute_pow_pos_change(df: pd.DataFrame) -> pd.DataFrame:
    """
    For Ethereum data, compute the percentage change in each metric
    between the mean PoW value and the mean PoS value.
    """
    pre, post = split_pre_post_merge(df)
    metrics = ["transaction_count", "hash_rate", "energy_consumption"]
    rows = []
    for m in metrics:
        if m not in pre.columns or m not in post.columns:
            continue
        pre_mean  = pre[m].mean()
        post_mean = post[m].mean()
        pct_change = ((post_mean - pre_mean) / pre_mean * 100) if pre_mean else np.nan
        rows.append({
            "metric":        m,
            "pow_mean":      pre_mean,
            "pos_mean":      post_mean,
            "abs_change":    post_mean - pre_mean,
            "pct_change":    pct_change,
        })
    return pd.DataFrame(rows)


def rolling_stats(
    df: pd.DataFrame,
    column: str,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """
    Add rolling mean and standard deviation columns for a given metric.

    Parameters
    ----------
    df      : DataFrame with 'date' and <column>
    column  : metric column name
    windows : list of rolling window sizes in days
    """
    if windows is None:
        windows = [7, 30, 90]

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)

    for w in windows:
        df[f"{column}_ma{w}"]  = df[column].rolling(w, min_periods=1).mean()
        df[f"{column}_std{w}"] = df[column].rolling(w, min_periods=1).std()

    return df
