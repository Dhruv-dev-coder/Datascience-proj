"""
Master data collector — orchestrates all API clients, applies consensus labels,
merges energy estimates, and persists to both CSV and the PostgreSQL database.

Metrics collected
─────────────────
Ethereum:
  • transaction_count   — Coin Metrics (TxCnt)
  • hash_rate           — Coin Metrics (HashRate, TH/s) [PoW period only]
  • energy_consumption  — Synthetic from hash rate (PoW) / near-zero constant (PoS)

Bitcoin:
  • transaction_count   — Coin Metrics (TxCnt)  or Blockchain.com fallback
  • hash_rate           — Coin Metrics (HashRate, EH/s)
  • energy_consumption  — Digiconomist / synthetic fallback

Ethereum Merge date: 2022-09-15
  • dates < merge  → consensus = "PoW"
  • dates ≥ merge  → consensus = "PoS", hash_rate set to 0
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data.api_clients import coinmetrics_client, blockchain_com_client, energy_client
from src.data.cleaners.cleaner import clean_dataframe
from src.database import repository
from src.utils.config import (
    ETH_START_DATE, BTC_START_DATE, ETH_MERGE_DATE,
    RAW_DATA_DIR, PROCESSED_DATA_DIR,
    CONSENSUS_POW, CONSENSUS_POS,
)
from src.utils.logger import logger

# Post-Merge Ethereum PoS energy is effectively negligible relative to PoW.
# CCRI estimates ~0.0026 TWh/year for the entire Ethereum PoS network (2023).
# We use this constant for PoS dates.
ETH_POS_ENERGY_TWH_YEAR = 0.0026   # TWh/year  (CCRI Ethereum PoS estimate)
ETH_POS_ENERGY_SOURCE   = "CCRI (Crypto Carbon Ratings Institute) estimate"


def _assign_consensus(df: pd.DataFrame, blockchain: str, merge_date: str) -> pd.DataFrame:
    df = df.copy()
    if blockchain.lower() == "ethereum":
        merge_dt = pd.to_datetime(merge_date)
        df["consensus"] = df["date"].apply(
            lambda d: CONSENSUS_POW if d < merge_dt else CONSENSUS_POS
        )
    else:
        df["consensus"] = CONSENSUS_POW
    return df


def collect_ethereum(
    start_date: str = ETH_START_DATE,
    end_date:   str | None = None,
    save_raw:   bool = True,
) -> pd.DataFrame:
    """
    Collect all Ethereum metrics and return a cleaned, consensus-labelled DataFrame.
    """
    if end_date is None:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

    logger.info(f"=== Collecting Ethereum data {start_date} → {end_date} ===")

    # ── 1. Transaction count + hash rate from Coin Metrics ──────────────────
    df_cm = coinmetrics_client.fetch_metrics(
        blockchain="ethereum",
        start_date=start_date,
        end_date=end_date,
        metric_keys=["transaction_count", "hash_rate"],
    )

    if df_cm.empty:
        logger.error("Coin Metrics returned no Ethereum data. Check API connectivity.")
        return pd.DataFrame()

    if save_raw:
        _save_raw(df_cm, "ethereum_coinmetrics_raw")

    # ── 2. Assign consensus labels ────────────────────────────────────────────
    df_cm = _assign_consensus(df_cm, "ethereum", ETH_MERGE_DATE)

    # ── 3. Energy consumption ─────────────────────────────────────────────────
    merge_dt = pd.to_datetime(ETH_MERGE_DATE)

    pow_mask = df_cm["date"] <  merge_dt
    pos_mask = df_cm["date"] >= merge_dt

    # PoW: estimate from hash rate
    df_pow = df_cm[pow_mask].copy()
    if not df_pow.empty and "hash_rate" in df_pow.columns:
        hr_unit = df_pow["hash_rate_unit"].iloc[0] if "hash_rate_unit" in df_pow.columns else "TH/s"
        df_pow  = energy_client.estimate_energy_from_hashrate(
            df_pow, blockchain="ethereum", hashrate_unit=hr_unit
        )

    # PoS: near-zero constant
    df_pos = df_cm[pos_mask].copy()
    if not df_pos.empty:
        df_pos["energy_consumption"] = ETH_POS_ENERGY_TWH_YEAR
        df_pos["energy_unit"]        = "TWh/year"
        df_pos["data_source_energy"] = ETH_POS_ENERGY_SOURCE
        # Zero out hash rate for PoS period
        df_pos["hash_rate"] = 0.0

    df = pd.concat([df_pow, df_pos], ignore_index=True).sort_values("date")

    # ── 4. Clean ──────────────────────────────────────────────────────────────
    df = clean_dataframe(df, blockchain="ethereum")

    if save_raw:
        _save_processed(df, "ethereum_processed")

    return df


def collect_bitcoin(
    start_date: str = BTC_START_DATE,
    end_date:   str | None = None,
    save_raw:   bool = True,
) -> pd.DataFrame:
    """
    Collect all Bitcoin metrics and return a cleaned DataFrame.
    """
    if end_date is None:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

    logger.info(f"=== Collecting Bitcoin data {start_date} → {end_date} ===")

    # ── 1. Transaction count + hash rate from Coin Metrics ──────────────────
    df_cm = coinmetrics_client.fetch_metrics(
        blockchain="bitcoin",
        start_date=start_date,
        end_date=end_date,
        metric_keys=["transaction_count", "hash_rate"],
    )

    if df_cm.empty:
        logger.warning("Coin Metrics empty for Bitcoin. Falling back to Blockchain.com …")
        df_cm = blockchain_com_client.fetch_bitcoin_metrics(start_date, end_date)

    if df_cm.empty:
        logger.error("All Bitcoin data sources failed.")
        return pd.DataFrame()

    if save_raw:
        _save_raw(df_cm, "bitcoin_coinmetrics_raw")

    df_cm = _assign_consensus(df_cm, "bitcoin", ETH_MERGE_DATE)

    # ── 2. Energy from Digiconomist ───────────────────────────────────────────
    df_energy = energy_client.fetch_digiconomist_bitcoin_energy()

    if not df_energy.empty:
        df_energy = df_energy[["date", "energy_consumption", "energy_unit"]].copy()
        df_energy["date"] = pd.to_datetime(df_energy["date"]).dt.normalize()
        df_cm["date"]     = pd.to_datetime(df_cm["date"]).dt.normalize()
        df_cm = pd.merge(df_cm, df_energy, on="date", how="left")
        df_cm["data_source_energy"] = "Digiconomist"
    else:
        logger.warning("Digiconomist unavailable — estimating Bitcoin energy from hash rate.")
        hr_unit = df_cm["hash_rate_unit"].iloc[0] if "hash_rate_unit" in df_cm.columns else "EH/s"
        df_cm = energy_client.estimate_energy_from_hashrate(
            df_cm, blockchain="bitcoin", hashrate_unit=hr_unit
        )

    # ── 3. Clean ──────────────────────────────────────────────────────────────
    df = clean_dataframe(df_cm, blockchain="bitcoin")

    if save_raw:
        _save_processed(df, "bitcoin_processed")

    return df


def collect_all(save_to_db: bool = True) -> dict[str, pd.DataFrame]:
    """
    Collect Ethereum and Bitcoin data, optionally persist to PostgreSQL.

    Returns dict with keys "ethereum" and "bitcoin".
    """
    results = {}

    df_eth = collect_ethereum()
    results["ethereum"] = df_eth

    df_btc = collect_bitcoin()
    results["bitcoin"] = df_btc

    if save_to_db:
        _persist_to_db(df_eth, source_name="Coin Metrics / Synthetic")
        _persist_to_db(df_btc, source_name="Coin Metrics / Digiconomist")

    return results


# ── I/O helpers ───────────────────────────────────────────────────────────────

def _save_raw(df: pd.DataFrame, name: str) -> None:
    path = RAW_DATA_DIR / f"{name}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    df.to_csv(path, index=False)
    logger.info(f"Raw data saved → {path}")


def _save_processed(df: pd.DataFrame, name: str) -> None:
    path = PROCESSED_DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    logger.info(f"Processed data saved → {path}")


def _persist_to_db(df: pd.DataFrame, source_name: str) -> None:
    if df.empty:
        return

    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date":               str(r["date"])[:10],
            "blockchain":         r.get("blockchain", ""),
            "consensus":          r.get("consensus", ""),
            "transaction_count":  r.get("transaction_count"),
            "hash_rate":          r.get("hash_rate"),
            "hash_rate_unit":     r.get("hash_rate_unit"),
            "energy_consumption": r.get("energy_consumption"),
            "energy_unit":        r.get("energy_unit", "TWh/year"),
            "data_source":        source_name,
        })
    repository.bulk_upsert_metrics(rows)
    logger.info(f"Persisted {len(rows)} rows to DB for {source_name}")
