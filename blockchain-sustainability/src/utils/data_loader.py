"""
Data loading utility for the dashboard and analysis modules.

Priority order:
  1. Load from PostgreSQL (if DB is reachable)
  2. Load from processed CSV files (if DB unavailable)
  3. Return empty DataFrame with warning

This ensures the dashboard works even without a live database.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.config import PROCESSED_DATA_DIR, ETH_MERGE_DATE
from src.utils.logger import logger

_MERGE_DATE = pd.to_datetime(ETH_MERGE_DATE)

PROCESSED_ETH_CSV = PROCESSED_DATA_DIR / "ethereum_processed.csv"
PROCESSED_BTC_CSV = PROCESSED_DATA_DIR / "bitcoin_processed.csv"


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        logger.warning(f"CSV not found: {path}. Run `python scripts/collect_data.py` first.")
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def _load_from_db(blockchain: str) -> pd.DataFrame:
    try:
        from src.database.repository import load_metrics
        df = load_metrics(blockchain=blockchain)
        if not df.empty:
            logger.info(f"[Loader] Loaded {blockchain} from PostgreSQL ({len(df)} rows)")
            return df
    except Exception as exc:
        logger.debug(f"[Loader] DB unavailable for {blockchain}: {exc}")
    return pd.DataFrame()


def load_ethereum(use_db: bool = True) -> pd.DataFrame:
    if use_db:
        df = _load_from_db("ethereum")
        if not df.empty:
            return df
    df = _load_csv(PROCESSED_ETH_CSV)
    if df.empty:
        logger.error("No Ethereum data available. Please run data collection first.")
    return df


def load_bitcoin(use_db: bool = True) -> pd.DataFrame:
    if use_db:
        df = _load_from_db("bitcoin")
        if not df.empty:
            return df
    df = _load_csv(PROCESSED_BTC_CSV)
    if df.empty:
        logger.error("No Bitcoin data available. Please run data collection first.")
    return df


def load_both(use_db: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (df_eth, df_btc)."""
    return load_ethereum(use_db), load_bitcoin(use_db)


def filter_date_range(
    df: pd.DataFrame,
    start: str | None = None,
    end:   str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    if start:
        df = df[df["date"] >= pd.to_datetime(start)]
    if end:
        df = df[df["date"] <= pd.to_datetime(end)]
    return df.reset_index(drop=True)
