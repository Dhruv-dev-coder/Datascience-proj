"""
Correlation analysis module.

Computes:
  • Pearson correlation coefficient + p-value
  • Spearman correlation coefficient + p-value (non-parametric robustness check)
  • Full correlation matrix for a set of columns

All results include:
  - coefficient
  - p-value
  - interpretation string (statistically significant? strong/moderate/weak?)
  - method used
  - sample size

IMPORTANT: Correlation ≠ Causation.
All interpretation strings include this caveat.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from src.utils.logger import logger


@dataclass
class CorrelationResult:
    x_name:      str
    y_name:      str
    method:      str          # "Pearson" | "Spearman"
    r:           float
    p_value:     float
    n:           int
    interpretation: str

    def to_dict(self) -> dict:
        return {
            "x":             self.x_name,
            "y":             self.y_name,
            "method":        self.method,
            "r":             round(self.r, 4),
            "p_value":       round(self.p_value, 6),
            "n":             self.n,
            "significant":   self.p_value < 0.05,
            "interpretation": self.interpretation,
        }


def _interpret(r: float, p: float, x: str, y: str) -> str:
    """
    Return a plain-English interpretation of a correlation result.
    Includes explicit causation caveat.
    """
    abs_r = abs(r)
    direction = "positive" if r >= 0 else "negative"

    if abs_r >= 0.90:
        strength = "very strong"
    elif abs_r >= 0.70:
        strength = "strong"
    elif abs_r >= 0.40:
        strength = "moderate"
    elif abs_r >= 0.20:
        strength = "weak"
    else:
        strength = "very weak / negligible"

    sig_str = f"statistically significant (p={p:.4f})" if p < 0.05 else f"NOT statistically significant (p={p:.4f})"
    return (
        f"The {direction} correlation (r={r:.4f}) between {x} and {y} is {strength} "
        f"and {sig_str}. NOTE: Correlation does NOT imply causation."
    )


def pearson(df: pd.DataFrame, x_col: str, y_col: str) -> CorrelationResult:
    """Pearson correlation between two columns of a DataFrame."""
    valid = df[[x_col, y_col]].dropna()
    n = len(valid)
    if n < 3:
        raise ValueError(f"Insufficient data for correlation ({n} rows after dropping NaN).")
    r, p = stats.pearsonr(valid[x_col], valid[y_col])
    return CorrelationResult(
        x_name=x_col, y_name=y_col, method="Pearson",
        r=r, p_value=p, n=n,
        interpretation=_interpret(r, p, x_col, y_col),
    )


def spearman(df: pd.DataFrame, x_col: str, y_col: str) -> CorrelationResult:
    """Spearman rank correlation between two columns."""
    valid = df[[x_col, y_col]].dropna()
    n = len(valid)
    if n < 3:
        raise ValueError(f"Insufficient data for Spearman correlation ({n} rows).")
    r, p = stats.spearmanr(valid[x_col], valid[y_col])
    return CorrelationResult(
        x_name=x_col, y_name=y_col, method="Spearman",
        r=float(r), p_value=float(p), n=n,
        interpretation=_interpret(float(r), float(p), x_col, y_col),
    )


def correlation_matrix(
    df: pd.DataFrame,
    cols: List[str],
    method: str = "pearson",
) -> pd.DataFrame:
    """
    Return a correlation matrix DataFrame for the specified columns.
    Only computes on rows where ALL selected columns are non-NaN.
    """
    valid = df[cols].dropna()
    logger.info(f"Correlation matrix ({method}) on {len(valid)} complete rows.")
    return valid.corr(method=method)


def eth_pow_correlations(df_eth: pd.DataFrame) -> List[CorrelationResult]:
    """
    Compute the three key correlations the thesis focuses on,
    restricted to Ethereum's PoW period.

    Returns list of CorrelationResult (Pearson + Spearman for each pair).
    """
    pow_df = df_eth[df_eth["consensus"] == "PoW"].copy()
    logger.info(f"[Correlation] Ethereum PoW period rows: {len(pow_df)}")

    pairs = [
        ("hash_rate",         "energy_consumption"),
        ("transaction_count", "hash_rate"),
        ("transaction_count", "energy_consumption"),
    ]

    results: List[CorrelationResult] = []
    for x, y in pairs:
        for fn, method_name in [(pearson, "Pearson"), (spearman, "Spearman")]:
            try:
                res = fn(pow_df, x, y)
                results.append(res)
                logger.info(f"[{method_name}] {x} vs {y}: r={res.r:.4f}, p={res.p_value:.6f}")
            except ValueError as exc:
                logger.warning(f"[{method_name}] {x} vs {y}: {exc}")

    return results


def summarise_correlations(results: List[CorrelationResult]) -> pd.DataFrame:
    """Convert a list of CorrelationResult to a readable DataFrame."""
    return pd.DataFrame([r.to_dict() for r in results])
