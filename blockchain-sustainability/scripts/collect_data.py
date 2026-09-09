"""
Data Collection CLI Script.
Fetches real historical blockchain metrics from Coin Metrics, Blockchain.com,
and energy sources, cleans the data, and writes to both processed CSV and PostgreSQL.
"""
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import argparse
from src.data.collectors.collector import collect_all, collect_ethereum, collect_bitcoin
from src.utils.logger import logger


def main():
    parser = argparse.ArgumentParser(description="Ingest historical blockchain metrics via public APIs.")
    parser.add_argument("--chain", choices=["all", "ethereum", "bitcoin"], default="all", help="Blockchain to collect")
    parser.add_argument("--start", type=str, default="2017-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--skip-db", action="store_true", help="Skip PostgreSQL persistence (write CSV only)")
    args = parser.parse_args()

    save_db = not args.skip_db
    logger.info(f"Starting data collection for chain={args.chain}, start={args.start}, end={args.end}...")

    try:
        if args.chain == "all":
            results = collect_all(save_to_db=save_db)
            for k, v in results.items():
                logger.info(f"Finished {k}: {len(v)} rows collected.")
        elif args.chain == "ethereum":
            df = collect_ethereum(start_date=args.start, end_date=args.end)
            logger.info(f"Finished Ethereum: {len(df)} rows collected.")
        elif args.chain == "bitcoin":
            df = collect_bitcoin(start_date=args.start, end_date=args.end)
            logger.info(f"Finished Bitcoin: {len(df)} rows collected.")
            
        logger.info("Data collection finished successfully.")
    except Exception as e:
        logger.error(f"Collection error: {e}")
        logger.info("Tip: If APIs are unreachable, use `python scripts/seed_sample_data.py` to seed benchmark data.")


if __name__ == "__main__":
    main()
