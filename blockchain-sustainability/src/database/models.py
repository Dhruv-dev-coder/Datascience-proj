"""
SQLAlchemy ORM models and schema for the Blockchain Sustainability database.

Tables
------
data_sources        — registry of every upstream data provider used
blockchain_metrics  — core daily time-series (transactions, hash rate, energy)
raw_api_responses   — optional store of raw JSON payloads for reproducibility
forecast_results    — saved ARIMA / counterfactual forecast rows
model_metrics       — MAE / RMSE / MAPE per model run
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from src.utils.config import DATABASE_URL
from src.utils.logger import logger

Base = declarative_base()


# ────────────────────────────────────────────────────────────────────────────
# data_sources
# ────────────────────────────────────────────────────────────────────────────
class DataSource(Base):
    __tablename__ = "data_sources"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), unique=True, nullable=False)   # e.g. "Coin Metrics"
    base_url    = Column(String(255))
    description = Column(Text)
    metrics_provided = Column(Text)   # free-text list of metrics
    limitations      = Column(Text)
    requires_key     = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    metrics = relationship("BlockchainMetric", back_populates="source")


# ────────────────────────────────────────────────────────────────────────────
# blockchain_metrics  (core table)
# ────────────────────────────────────────────────────────────────────────────
class BlockchainMetric(Base):
    __tablename__ = "blockchain_metrics"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    date       = Column(String(10), nullable=False)          # ISO-8601 YYYY-MM-DD
    blockchain = Column(String(20), nullable=False)          # "ethereum" | "bitcoin"
    consensus  = Column(String(10), nullable=False)          # "PoW" | "PoS"

    # Core metrics — NULL when unavailable from the source
    transaction_count = Column(Float)
    hash_rate         = Column(Float)
    hash_rate_unit    = Column(String(20))   # e.g. "TH/s", "GH/s"
    energy_consumption = Column(Float)
    energy_unit        = Column(String(30))  # e.g. "TWh/year", "GWh/day"

    # Provenance
    data_source_id = Column(Integer, ForeignKey("data_sources.id"))
    data_source    = Column(String(100))     # denormalised for quick filtering

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("DataSource", back_populates="metrics")

    __table_args__ = (
        UniqueConstraint("date", "blockchain", "data_source", name="uq_date_chain_src"),
    )


# ────────────────────────────────────────────────────────────────────────────
# raw_api_responses  (audit / reproducibility)
# ────────────────────────────────────────────────────────────────────────────
class RawApiResponse(Base):
    __tablename__ = "raw_api_responses"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    fetched_at  = Column(DateTime, default=datetime.utcnow)
    source_name = Column(String(100))
    endpoint    = Column(String(255))
    params      = Column(JSON)
    response    = Column(JSON)


# ────────────────────────────────────────────────────────────────────────────
# forecast_results
# ────────────────────────────────────────────────────────────────────────────
class ForecastResult(Base):
    __tablename__ = "forecast_results"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    run_id          = Column(String(50))          # e.g. timestamp-based run identifier
    date            = Column(String(10))           # ISO-8601
    blockchain      = Column(String(20))
    metric          = Column(String(50))           # "hash_rate" | "energy_consumption" etc.
    model_name      = Column(String(50))           # "ARIMA(5,1,2)"
    scenario        = Column(String(50))           # "baseline" | "counterfactual_pow"
    forecast_value  = Column(Float)
    lower_ci_95     = Column(Float)
    upper_ci_95     = Column(Float)
    is_hypothetical = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)


# ────────────────────────────────────────────────────────────────────────────
# model_metrics
# ────────────────────────────────────────────────────────────────────────────
class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    run_id     = Column(String(50))
    blockchain = Column(String(20))
    metric     = Column(String(50))
    model_name = Column(String(50))
    scenario   = Column(String(50))
    mae        = Column(Float)
    rmse       = Column(Float)
    mape       = Column(Float)
    aic        = Column(Float)
    bic        = Column(Float)
    arima_order = Column(String(20))    # "(p,d,q)"
    train_start = Column(String(10))
    train_end   = Column(String(10))
    test_start  = Column(String(10))
    test_end    = Column(String(10))
    created_at  = Column(DateTime, default=datetime.utcnow)


def get_engine():
    try:
        engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        # Test connection
        with engine.connect() as conn:
            pass
        return engine
    except Exception as e:
        # Fallback to local SQLite database in DATA_DIR
        from src.utils.config import DATA_DIR
        sqlite_path = DATA_DIR / "blockchain_sustainability.db"
        sqlite_url = f"sqlite:///{sqlite_path}"
        engine = create_engine(sqlite_url, echo=False)
        return engine


def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(engine=None) -> None:
    """Create all tables if they do not yet exist."""
    if engine is None:
        engine = get_engine()
    logger.info(f"Initialising database schema on {engine.url.drivername} …")
    Base.metadata.create_all(engine)
    logger.info("Database schema ready.")
