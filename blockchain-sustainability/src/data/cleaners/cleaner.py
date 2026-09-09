"""
Data cleaning and preprocessing pipeline.

Transformations applied (all logged, none silent):
  1. Parse / normalise dates to pandas Timestamps
  2. Remove exact duplicate rows
  3. Fill date gaps (create a continuous daily index)
  4. Forward-fill short gaps (≤ 3 days) for time-series continuity
  5. Detect and log long gaps (> 3 days) as data quality issues
  6. Remove rows with clearly invalid values (negative counts, negative energy)
  7. Cap extreme outliers using IQR × 3 (flagged, not deleted)
  8. Standardise blockchain and consensus column values
  9. Log a transformation report at the end
"""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

from src.utils.logger import logger

# Maximum gap (days) to auto-fill via forward fill
_MAX_FFILL_DAYS = 3


def clean_dataframe(df: pd.DataFrame, blockchain: str) -> pd.DataFrame:
    """
    Full cleaning pipeline. Returns a cleaned copy of the DataFrame.
    Transformation decisions are logged; nothing is dropped silently.
    """
    if df.empty:
        logger.warning(f"[Cleaner:{blockchain}] Input DataFrame is empty.")
        return df

    report: List[str] = []
    n_initial = len(df)

    df = df.copy()

    # ── Step 1 : normalise dates ──────────────────────────────────────────────
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    n_bad_dates = df["date"].isna().sum()
    if n_bad_dates:
        report.append(f"Dropped {n_bad_dates} rows with un-parseable dates.")
        df.dropna(subset=["date"], inplace=True)

    # ── Step 2 : standardise string fields ───────────────────────────────────
    df["blockchain"] = blockchain.lower()
    if "consensus" not in df.columns:
        df["consensus"] = "unknown"

    # ── Step 3 : remove exact duplicate rows ─────────────────────────────────
    n_before = len(df)
    df.drop_duplicates(subset=["date", "blockchain"], keep="last", inplace=True)
    n_dupes = n_before - len(df)
    if n_dupes:
        report.append(f"Removed {n_dupes} duplicate (date, blockchain) rows.")

    # ── Step 4 : continuous daily date index ─────────────────────────────────
    df.sort_values("date", inplace=True)
    df.set_index("date", inplace=True)

    full_range = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_range)
    df.index.name = "date"
    n_added = len(df) - (n_initial - n_bad_dates - n_dupes)
    if n_added > 0:
        report.append(f"Inserted {n_added} missing date rows (NaN values).")

    # Restore string columns after reindex
    df["blockchain"] = blockchain.lower()
    if "consensus" in df.columns:
        df["consensus"] = df["consensus"].ffill()

    # ── Step 5 : forward fill short gaps ─────────────────────────────────────
    numeric_cols = ["transaction_count", "hash_rate", "energy_consumption"]
    for col in numeric_cols:
        if col not in df.columns:
            continue
        missing_before = df[col].isna().sum()
        df[col] = df[col].ffill(limit=_MAX_FFILL_DAYS)
        filled = missing_before - df[col].isna().sum()
        if filled:
            report.append(f"Forward-filled {filled} short gaps in '{col}'.")

    # ── Step 6 : detect long gaps ─────────────────────────────────────────────
    for col in numeric_cols:
        if col not in df.columns:
            continue
        na_runs = _find_gap_runs(df[col])
        long_gaps = [(s, e, l) for s, e, l in na_runs if l > _MAX_FFILL_DAYS]
        for start, end, length in long_gaps:
            report.append(
                f"LONG GAP in '{col}': {start} to {end} ({length} days) — values remain NaN."
            )

    # ── Step 7 : remove rows with negative metrics ───────────────────────────
    for col in ["transaction_count", "hash_rate", "energy_consumption"]:
        if col not in df.columns:
            continue
        mask = df[col] < 0
        if mask.any():
            report.append(f"Zeroed {mask.sum()} negative values in '{col}'.")
            df.loc[mask, col] = np.nan

    # ── Step 8 : flag extreme outliers (IQR × 3) ─────────────────────────────
    for col in ["transaction_count", "hash_rate", "energy_consumption"]:
        if col not in df.columns:
            continue
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        upper = q3 + 3 * iqr
        lower = q1 - 3 * iqr
        outliers = ((df[col] < lower) | (df[col] > upper)).sum()
        if outliers:
            report.append(
                f"Flagged {outliers} extreme outliers in '{col}' "
                f"(outside [{lower:.1f}, {upper:.1f}]). Values retained."
            )

    # ── Step 9 : restore date as column ──────────────────────────────────────
    df.reset_index(inplace=True)   # date becomes a column again
    df["date"] = pd.to_datetime(df["date"])

    # ── Transformation report ────────────────────────────────────────────────
    n_final = len(df)
    logger.info(
        f"[Cleaner:{blockchain}] Cleaning complete. "
        f"Rows: {n_initial} → {n_final}. "
        f"Transformations: {len(report)}"
    )
    for msg in report:
        logger.debug(f"  • {msg}")

    return df


def _find_gap_runs(series: pd.Series) -> list[tuple]:
    """
    Return list of (start_label, end_label, length) for each run of NaN values.
    Labels are the index values (dates).
    """
    is_na = series.isna()
    runs = []
    in_run = False
    run_start = None
    for idx, val in is_na.items():
        if val and not in_run:
            in_run   = True
            run_start = idx
        elif not val and in_run:
            in_run = False
            length = (idx - run_start).days if hasattr(idx, "days") else 0
            runs.append((run_start, idx, length))
    if in_run:
        runs.append((run_start, series.index[-1], 0))
    return runs
