"""
Blockchain Sustainability Project — Global Configuration
Loads .env and exposes typed settings used throughout the project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (two levels up from src/utils)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# ── Database ────────────────────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", "5432"))
DB_NAME     = os.getenv("DB_NAME", "blockchain_sustainability")
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── API Keys ────────────────────────────────────────────────────────────────
COINMETRICS_API_KEY = os.getenv("COINMETRICS_API_KEY", "")
ETHERSCAN_API_KEY   = os.getenv("ETHERSCAN_API_KEY", "")
GLASSNODE_API_KEY   = os.getenv("GLASSNODE_API_KEY", "")

# ── Date Ranges ─────────────────────────────────────────────────────────────
ETH_START_DATE = os.getenv("ETH_START_DATE", "2017-01-01")
BTC_START_DATE = os.getenv("BTC_START_DATE", "2017-01-01")
ETH_MERGE_DATE = os.getenv("ETH_MERGE_DATE", "2022-09-15")   # PoW → PoS

# ── Directories ─────────────────────────────────────────────────────────────
DATA_DIR           = _PROJECT_ROOT / os.getenv("DATA_DIR", "data")
RAW_DATA_DIR       = _PROJECT_ROOT / os.getenv("RAW_DATA_DIR", "data/raw")
PROCESSED_DATA_DIR = _PROJECT_ROOT / os.getenv("PROCESSED_DATA_DIR", "data/processed")
for _d in (DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Rate Limiting ────────────────────────────────────────────────────────────
API_RATE_LIMIT_SECONDS  = float(os.getenv("API_RATE_LIMIT_SECONDS", "0.5"))
API_MAX_RETRIES         = int(os.getenv("API_MAX_RETRIES", "3"))
API_RETRY_DELAY_SECONDS = float(os.getenv("API_RETRY_DELAY_SECONDS", "2.0"))

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── Ethereum consensus constants ─────────────────────────────────────────────
ETHEREUM_MERGE_DATE = ETH_MERGE_DATE   # alias for clarity in analysis modules
CONSENSUS_POW = "PoW"
CONSENSUS_POS = "PoS"
