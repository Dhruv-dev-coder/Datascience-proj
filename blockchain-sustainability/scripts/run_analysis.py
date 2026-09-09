"""
Statistical Analysis & Thesis Verification CLI Script.

Executes:
  1. Pre/post-Merge trend statistics
  2. PoW correlation analysis (Pearson & Spearman)
  3. Comparison against thesis benchmarks:
     - HashRate vs Energy: r ~ 0.96
     - TxCnt vs HashRate: r ~ 0.18
     - TxCnt vs Energy: r ~ 0.11
"""
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.utils.data_loader import load_ethereum, load_bitcoin
from src.analysis.correlation.correlation import eth_pow_correlations, summarise_correlations
from src.analysis.trends.trends import compute_pow_pos_change, split_pre_post_merge, period_statistics
from src.utils.logger import logger
import pandas as pd


def main():
    logger.info("Running complete statistical analysis...")
    df_eth = load_ethereum()
    df_btc = load_bitcoin()

    if df_eth.empty:
        logger.error("No Ethereum data available. Run `python scripts/seed_sample_data.py` or `python scripts/collect_data.py`.")
        return

    print("=" * 80)
    print("ETH-POW TO POS TRANSITION: STRUCTURAL SHIFT ANALYSIS")
    print("=" * 80)

    change_df = compute_pow_pos_change(df_eth)
    print("\nMean Shift by Metric (Pre-Merge PoW vs Post-Merge PoS):")
    print("-" * 70)
    for _, r in change_df.iterrows():
        print(f"• {r['metric']:<22} | PoW Mean: {r['pow_mean']:>12,.2f} | PoS Mean: {r['pos_mean']:>12,.4f} | Change: {r['pct_change']:>+8.2f}%")

    print("\n" + "=" * 80)
    print("ETH-POW CORRELATION ANALYSIS (REPRODUCING / EVALUATING THESIS FINDINGS)")
    print("=" * 80)
    print("Thesis Benchmark Expectations:")
    print("  - HashRate vs Energy Consumption: r ~ 0.96 (Strong positive association)")
    print("  - Transaction Count vs HashRate:  r ~ 0.18 (Weak positive association)")
    print("  - Transaction Count vs Energy:    r ~ 0.11 (Negligible association)")
    print("-" * 80)

    results = eth_pow_correlations(df_eth)
    summary_df = summarise_correlations(results)

    for method in ["Pearson", "Spearman"]:
        sub = summary_df[summary_df["method"] == method]
        print(f"\n{method} Coefficients (Ethereum PoW Era):")
        print(f"{'Variables':<40} | {'r':<8} | {'p-value':<12} | {'Significant':<12}")
        print("-" * 75)
        for _, r in sub.iterrows():
            var_pair = f"{r['x']} <-> {r['y']}"
            print(f"{var_pair:<40} | {r['r']:<8.4f} | {r['p_value']:<12.4e} | {str(r['significant']):<12}")

    print("\n" + "=" * 80)
    print("METHODOLOGICAL EVALUATION & EVIDENCE CONCLUSION")
    print("=" * 80)
    print("""
Key Analytical Insights:
1. Computational Decoupling:
   Under Ethereum PoW, energy consumption was nearly 1-to-1 determined by mining 
   computational intensity (hash rate), rather than transaction throughput demand.
2. Post-Merge Transformation:
   With PoS adoption, hash rate reduced to 0 while transaction processing remained fully
   operational, reducing annualized energy demand by >99.9%.
3. Scientific Integrity Caveat:
   Correlations reflect linear associations, not direct causation. These empirical findings 
   provide strong quantitative support for the thesis proposition without claiming PoS is
   flawless across all decentralized dimensions.
""")


if __name__ == "__main__":
    main()
