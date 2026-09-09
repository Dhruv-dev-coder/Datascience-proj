"""
Database initialization script.
Connects to PostgreSQL using configured DATABASE_URL and creates all tables.
"""
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.database.models import init_db, get_engine
from src.database.repository import upsert_data_source
from src.utils.logger import logger


def main():
    logger.info("Initializing PostgreSQL tables...")
    try:
        engine = get_engine()
        init_db(engine)
        
        # Seed known data sources
        sources = [
            {
                "name": "Coin Metrics",
                "base_url": "https://community-api.coinmetrics.io/v4",
                "description": "Community API providing on-chain network metrics",
                "metrics_provided": "transaction_count, hash_rate",
                "limitations": "Community tier rate limits; daily frequency",
                "requires_key": False
            },
            {
                "name": "Blockchain.com",
                "base_url": "https://api.blockchain.info/charts",
                "description": "Public charts API for Bitcoin network data",
                "metrics_provided": "transaction_count, hash_rate",
                "limitations": "Bitcoin only",
                "requires_key": False
            },
            {
                "name": "Digiconomist",
                "base_url": "https://digiconomist.net",
                "description": "Bitcoin Energy Consumption Index",
                "metrics_provided": "energy_consumption",
                "limitations": "Economic model estimate",
                "requires_key": False
            },
            {
                "name": "CCRI",
                "base_url": "https://carbon-ratings.com",
                "description": "Crypto Carbon Ratings Institute empirical measurements for Ethereum PoS",
                "metrics_provided": "energy_consumption (PoS)",
                "limitations": "Point-in-time census of validator nodes",
                "requires_key": False
            }
        ]
        for s in sources:
            upsert_data_source(**s)
            
        logger.info("Database initialized successfully with default data source registries.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.info("Note: Ensure PostgreSQL is running and DB credentials in .env are correct.")


if __name__ == "__main__":
    main()
