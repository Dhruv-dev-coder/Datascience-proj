"""
Energy consumption data client.

Energy consumption is NOT directly measured on-chain; it is ESTIMATED.
This module fetches estimates from multiple public sources and clearly
labels each estimate with its source and methodology.

Sources used:
  1. Coin Metrics  — PowerMean / KiloHashPerSecond proxies (available on paid tier)
  2. Digiconomist  — Bitcoin Energy Consumption Index (web-scraped CSV)
     URL: https://digiconomist.net/bitcoin-energy-consumption/
  3. Etherscan     — Ethereum energy consumption estimates (post-Merge only for PoS)
  4. Synthetic estimation — derive from hash rate using published efficiency constants
     when no direct API is available.

IMPORTANT:
  All energy values are ESTIMATES derived from hash rate and assumed hardware efficiency.
  They are NOT direct measurements. This is clearly documented in the data_source field.

Unit: TWh/year (tera-watt-hours per year) unless otherwise specified.

Efficiency constants used for synthetic estimation:
  - Bitcoin miners: ~0.03 J/GH  (conservative mid-2022 ASIC estimate)
  - Ethereum PoW miners: ~0.07 J/MH  (GPU + early ASIC era)
These are deliberately conservative. The Cambridge CBECI uses a similar approach.
"""
from __future__ import annotations

import io
import math
from datetime import datetime

import pandas as pd
import requests

from src.utils.logger import logger

# ─── Digiconomist Bitcoin Energy Consumption Index ───────────────────────────
_DIGICONOMIST_BTC_CSV = (
    "https://raw.githubusercontent.com/Digiconomist/bitcoin-energy-consumption"
    "/refs/heads/master/data/BECI.csv"
)

# ─── Our own synthetic estimator constants ────────────────────────────────────
# These are rough estimates used ONLY when no API source is available.
# Source for efficiency numbers: Cambridge CBECI methodology documentation.
_BTC_EFFICIENCY_J_PER_TH  = 30.0     # Joules per TeraHash (BTC, 2022 average)
_ETH_POW_EFFICIENCY_J_PER_TH = 70.0  # Joules per TeraHash (ETH PoW, GPU-era)


def fetch_digiconomist_bitcoin_energy() -> pd.DataFrame:
    """
    Download Bitcoin energy consumption estimates from Digiconomist's public CSV.
    Units returned: TWh/year (annualised).
    Data source label: "Digiconomist"
    """
    logger.info("[Energy] Fetching Digiconomist Bitcoin energy CSV …")
    try:
        resp = requests.get(_DIGICONOMIST_BTC_CSV, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
    except Exception as exc:
        logger.warning(f"[Energy] Digiconomist CSV failed: {exc}")
        return pd.DataFrame()

    # Normalise column names (vary by file version)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Try to find date and energy columns
    date_col   = next((c for c in df.columns if "date" in c or "timestamp" in c), None)
    energy_col = next(
        (c for c in df.columns if "annualized" in c and "gwh" in c.lower()), None
    )
    if energy_col is None:
        energy_col = next((c for c in df.columns if "twh" in c or "energy" in c), None)

    if date_col is None or energy_col is None:
        logger.warning(f"[Energy] Digiconomist column detection failed. Cols: {df.columns.tolist()}")
        return pd.DataFrame()

    df["date"]             = pd.to_datetime(df[date_col], errors="coerce")
    df["energy_consumption"] = pd.to_numeric(df[energy_col], errors="coerce")

    # Convert GWh → TWh if needed
    if "gwh" in energy_col.lower():
        df["energy_consumption"] = df["energy_consumption"] / 1000.0
        energy_unit = "TWh/year"
    else:
        energy_unit = "TWh/year"

    df["energy_unit"]  = energy_unit
    df["data_source"]  = "Digiconomist"
    df["blockchain"]   = "bitcoin"

    df = df[["date", "energy_consumption", "energy_unit", "data_source", "blockchain"]].dropna(subset=["date", "energy_consumption"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    logger.info(f"[Energy] Digiconomist: {len(df)} rows loaded")
    return df


def estimate_energy_from_hashrate(
    df: pd.DataFrame,
    blockchain: str,
    hashrate_col: str = "hash_rate",
    hashrate_unit: str = "TH/s",
) -> pd.DataFrame:
    """
    Estimate daily energy consumption from hash rate using efficiency constants.

    This is a SYNTHETIC ESTIMATE used when direct energy API data is unavailable.
    Methodology mirrors Cambridge CBECI's lower-bound estimation.

    Formula:
        Power (GW) = HashRate (TH/s) × Efficiency (J/TH) / 1e9
        Energy (TWh/year) = Power (GW) × 8760 hours / 1000

    Parameters
    ----------
    df            : DataFrame containing hash_rate column
    blockchain    : "ethereum" or "bitcoin"
    hashrate_col  : name of the hash rate column
    hashrate_unit : unit of hash rate values (used for unit conversion)

    Returns
    -------
    df with added columns: energy_consumption, energy_unit
    """
    df = df.copy()

    # Convert hash rate to TH/s for consistent calculation
    hr = df[hashrate_col].copy()
    if hashrate_unit == "EH/s":
        hr = hr * 1e6    # EH/s → TH/s
    elif hashrate_unit == "GH/s":
        hr = hr / 1e3    # GH/s → TH/s
    elif hashrate_unit == "PH/s":
        hr = hr * 1e3    # PH/s → TH/s
    # TH/s stays as-is

    efficiency = _BTC_EFFICIENCY_J_PER_TH if blockchain.lower() == "bitcoin" else _ETH_POW_EFFICIENCY_J_PER_TH

    # Power in Watts = TH/s × J/TH
    power_w = hr * efficiency
    # Convert to GW
    power_gw = power_w / 1e9
    # TWh/year = GW × 8760 / 1000
    energy_twh_yr = power_gw * 8760.0 / 1000.0

    df["energy_consumption"] = energy_twh_yr
    df["energy_unit"]        = "TWh/year"
    df["data_source_energy"] = f"Synthetic (hash rate × {efficiency} J/TH efficiency)"

    logger.info(
        f"[Energy] Synthetic estimate for {blockchain}: "
        f"mean={energy_twh_yr.mean():.2f} TWh/year using {hashrate_unit} hash rate"
    )
    return df
