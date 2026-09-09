"""
ARIMA Forecasting & Counterfactual Scenario CLI Script.

Executes:
  1. ARIMA(5,1,2) modeling on historical metrics
  2. Holdout evaluation (MAE, RMSE, MAPE)
  3. Counterfactual Continued-PoW projection beyond the 2022 Merge
"""
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.utils.data_loader import load_ethereum
from src.analysis.forecasting.arima_model import run_forecast_pipeline, run_counterfactual_pow
from src.utils.logger import logger


def main():
    logger.info("Running ARIMA modeling and counterfactual generation...")
    df_eth = load_ethereum()
    if df_eth.empty:
        logger.error("No Ethereum data available.")
        return

    print("=" * 80)
    print("1. ARIMA(5,1,2) MODEL FITTING & OUT-OF-SAMPLE EVALUATION")
    print("=" * 80)

    for metric in ["transaction_count", "hash_rate"]:
        if metric in df_eth.columns:
            print(f"\nFitting ARIMA(5,1,2) on Ethereum: {metric}...")
            res = run_forecast_pipeline(
                df=df_eth,
                metric=metric,
                blockchain="ethereum",
                test_size=0.15,
                forecast_horizon=180,
                order=(5, 1, 2)
            )
            print(f"  Model:        {res.model_name}")
            print(f"  Holdout MAE:  {res.mae:.4f}")
            print(f"  Holdout RMSE: {res.rmse:.4f}")
            print(f"  Holdout MAPE: {res.mape:.2f}% (Accuracy Index: {100 - res.mape:.2f}%)")
            print(f"  AIC / BIC:    {res.aic:.2f} / {res.bic:.2f}")

    print("\n" + "=" * 80)
    print("2. HYPOTHETICAL COUNTERFACTUAL CONTINUED-POW PROJECTION")
    print("=" * 80)
    print("Simulating trajectory if Ethereum had NOT executed The Merge in Sep 2022...")

    cf_res = run_counterfactual_pow(df_eth, metric="hash_rate", forecast_horizon=365, order=(5, 1, 2))
    if cf_res.forecast_df is not None:
        fc = cf_res.forecast_df
        print(f"Counterfactual Projection Generated: {len(fc)} days forward.")
        print(f"  Mean Counterfactual Hash Rate:  {fc['forecast'].mean():.2f} TH/s")
        print(f"  Min / Max 95% Confidence Band:  [{fc['lower_ci_95'].min():.2f} TH/s, {fc['upper_ci_95'].max():.2f} TH/s]")
        print(f"  Actual Observed Hash Rate (PoS): 0.00 TH/s")

    print("\nForecast completed. Visualizations available via the Streamlit dashboard (`streamlit run dashboard/app.py`).")


if __name__ == "__main__":
    main()
