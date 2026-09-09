"""
Database repository — all read/write helpers so the rest of the project
never has to write raw SQL or ORM queries.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import pandas as pd
from sqlalchemy.orm import Session

from src.database.models import (
    BlockchainMetric,
    DataSource,
    ForecastResult,
    ModelMetric,
    RawApiResponse,
    get_engine,
    get_session_factory,
    init_db,
)
from src.utils.logger import logger

_engine  = get_engine()
init_db(_engine)
_Session = get_session_factory(_engine)


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager that provides a transactional database session."""
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── DataSource helpers ────────────────────────────────────────────────────────
def upsert_data_source(name: str, **kwargs) -> DataSource:
    with db_session() as s:
        src = s.query(DataSource).filter_by(name=name).first()
        if src is None:
            src = DataSource(name=name, **kwargs)
            s.add(src)
            s.flush()
            logger.info(f"Registered data source: {name}")
        return src


# ── BlockchainMetric helpers ──────────────────────────────────────────────────
def upsert_metric(row: dict) -> None:
    """
    Insert or update a single daily metric row.
    Unique key: (date, blockchain, data_source).
    """
    with db_session() as s:
        existing = (
            s.query(BlockchainMetric)
            .filter_by(
                date=row["date"],
                blockchain=row["blockchain"],
                data_source=row.get("data_source"),
            )
            .first()
        )
        if existing:
            for k, v in row.items():
                setattr(existing, k, v)
        else:
            s.add(BlockchainMetric(**row))


def bulk_upsert_metrics(rows: list[dict]) -> None:
    """Efficient bulk upsert using per-row upsert (PostgreSQL ON CONFLICT)."""
def bulk_upsert_metrics(rows: list[dict]) -> None:
    """Bulk upsert supporting both PostgreSQL and SQLite."""
    if not rows:
        return

    engine = _engine
    if engine.url.drivername.startswith("postgresql"):
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        with db_session() as s:
            stmt = pg_insert(BlockchainMetric).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["date", "blockchain", "data_source"],
                set_={
                    "transaction_count":  stmt.excluded.transaction_count,
                    "hash_rate":          stmt.excluded.hash_rate,
                    "hash_rate_unit":     stmt.excluded.hash_rate_unit,
                    "energy_consumption": stmt.excluded.energy_consumption,
                    "energy_unit":        stmt.excluded.energy_unit,
                    "updated_at":         stmt.excluded.updated_at,
                },
            )
            s.execute(stmt)
    else:
        # SQLite / other dialect
        with db_session() as s:
            for row in rows:
                existing = (
                    s.query(BlockchainMetric)
                    .filter_by(
                        date=row["date"],
                        blockchain=row["blockchain"],
                        data_source=row.get("data_source"),
                    )
                    .first()
                )
                if existing:
                    for k, v in row.items():
                        setattr(existing, k, v)
                else:
                    s.add(BlockchainMetric(**row))
    logger.info(f"Upserted {len(rows)} metric rows.")


def load_metrics(
    blockchain: str | None = None,
    start_date: str | None = None,
    end_date:   str | None = None,
) -> pd.DataFrame:
    """Load blockchain_metrics into a DataFrame."""
    with db_session() as s:
        q = s.query(BlockchainMetric)
        if blockchain:
            q = q.filter_by(blockchain=blockchain.lower())
        if start_date:
            q = q.filter(BlockchainMetric.date >= start_date)
        if end_date:
            q = q.filter(BlockchainMetric.date <= end_date)
        rows = q.order_by(BlockchainMetric.date).all()

    if not rows:
        return pd.DataFrame()

    records = [
        {
            "date":               r.date,
            "blockchain":         r.blockchain,
            "consensus":          r.consensus,
            "transaction_count":  r.transaction_count,
            "hash_rate":          r.hash_rate,
            "hash_rate_unit":     r.hash_rate_unit,
            "energy_consumption": r.energy_consumption,
            "energy_unit":        r.energy_unit,
            "data_source":        r.data_source,
        }
        for r in rows
    ]
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ── Forecast helpers ──────────────────────────────────────────────────────────
def save_forecast(rows: list[dict]) -> None:
    with db_session() as s:
        s.bulk_insert_mappings(ForecastResult, rows)
    logger.info(f"Saved {len(rows)} forecast rows.")


def save_model_metrics(row: dict) -> None:
    with db_session() as s:
        s.add(ModelMetric(**row))
    logger.info(f"Saved model metrics for {row.get('model_name')} / {row.get('scenario')}")


# ── RawApiResponse ────────────────────────────────────────────────────────────
def save_raw_response(source: str, endpoint: str, params: dict, response: dict) -> None:
    with db_session() as s:
        s.add(RawApiResponse(
            source_name=source,
            endpoint=endpoint,
            params=params,
            response=response,
        ))
