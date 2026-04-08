"""Database engine/session helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def build_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    elif database_url.startswith("postgresql+psycopg"):
        # Disable server-side prepared statements to avoid conflicts with
        # transaction-pooled Postgres connections.
        connect_args = {"prepare_threshold": None}
    else:
        connect_args = {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def check_database_health(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
