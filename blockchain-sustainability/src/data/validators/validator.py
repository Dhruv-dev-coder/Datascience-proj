"""
Data validation module.

Validates DataFrames before they are persisted or used in analysis.
Returns a ValidationReport object that lists all detected issues.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pandas as pd


@dataclass
class ValidationReport:
    blockchain: str
    n_rows: int
    errors:   List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = [
            f"Validation Report — {self.blockchain} ({self.n_rows} rows)",
            f"  Errors  : {len(self.errors)}",
            f"  Warnings: {len(self.warnings)}",
        ]
        for e in self.errors:
            lines.append(f"  [ERROR]   {e}")
        for w in self.warnings:
            lines.append(f"  [WARNING] {w}")
        return "\n".join(lines)


REQUIRED_COLUMNS = ["date", "blockchain", "consensus"]
NUMERIC_COLUMNS  = ["transaction_count", "hash_rate", "energy_consumption"]
VALID_BLOCKCHAINS = {"ethereum", "bitcoin"}
VALID_CONSENSUS   = {"PoW", "PoS", "unknown"}


def validate(df: pd.DataFrame, blockchain: str) -> ValidationReport:
    report = ValidationReport(blockchain=blockchain, n_rows=len(df))

    if df.empty:
        report.errors.append("DataFrame is empty.")
        return report

    # Required columns
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            report.errors.append(f"Required column '{col}' is missing.")

    # blockchain values
    if "blockchain" in df.columns:
        bad = set(df["blockchain"].unique()) - VALID_BLOCKCHAINS
        if bad:
            report.errors.append(f"Unknown blockchain values: {bad}")

    # consensus values
    if "consensus" in df.columns:
        bad_c = set(df["consensus"].dropna().unique()) - VALID_CONSENSUS
        if bad_c:
            report.warnings.append(f"Unexpected consensus values: {bad_c}")

    # Date column
    if "date" in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df["date"]):
            report.warnings.append("'date' column is not datetime64 dtype.")
        n_na = df["date"].isna().sum()
        if n_na:
            report.errors.append(f"{n_na} NaT values in 'date' column.")

    # Numeric columns
    for col in NUMERIC_COLUMNS:
        if col not in df.columns:
            report.warnings.append(f"Optional column '{col}' is absent.")
            continue
        pct_missing = df[col].isna().mean() * 100
        if pct_missing > 50:
            report.warnings.append(
                f"'{col}' is {pct_missing:.1f}% missing — analysis may be unreliable."
            )
        if (df[col] < 0).any():
            report.errors.append(f"'{col}' contains negative values.")

    # Date duplicates
    if "date" in df.columns:
        n_dupes = df.duplicated(subset=["date"]).sum()
        if n_dupes:
            report.warnings.append(f"{n_dupes} duplicate date rows found.")

    return report
