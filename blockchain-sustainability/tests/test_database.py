"""
Unit tests for Database ORM models and SQLite in-memory repository tests.
Allows verifying schema and ORM operations without an external PostgreSQL service.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, BlockchainMetric, DataSource, ForecastResult


@pytest.fixture
def in_memory_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_insert_blockchain_metric(in_memory_session):
    record = BlockchainMetric(
        date="2022-09-15",
        blockchain="ethereum",
        consensus="PoS",
        transaction_count=1150000.0,
        hash_rate=0.0,
        hash_rate_unit="TH/s",
        energy_consumption=0.0026,
        energy_unit="TWh/year",
        data_source="Test",
    )
    in_memory_session.add(record)
    in_memory_session.commit()

    retrieved = in_memory_session.query(BlockchainMetric).filter_by(date="2022-09-15").first()
    assert retrieved is not None
    assert retrieved.blockchain == "ethereum"
    assert retrieved.consensus == "PoS"
    assert retrieved.hash_rate == 0.0


def test_data_source_registry(in_memory_session):
    src = DataSource(
        name="Coin Metrics",
        base_url="https://community-api.coinmetrics.io/v4",
        metrics_provided="TxCnt, HashRate",
    )
    in_memory_session.add(src)
    in_memory_session.commit()

    loaded = in_memory_session.query(DataSource).filter_by(name="Coin Metrics").first()
    assert loaded is not None
    assert "TxCnt" in loaded.metrics_provided
