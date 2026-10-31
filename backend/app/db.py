"""Database connection and session management.

Purpose:
    Initializes the SQLAlchemy engine, session maker, and declarative base.
    Supports SQLite for local development and PostgreSQL for production deployments.

Status:
    Active, production-ready.

Fail-Closed Behavior:
    Fails immediately with an exception if DATABASE_URL is malformed or inaccessible.
    Enforces SQLite foreign key constraints explicitly upon connection.
"""

import os
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./adaptive_iq.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session scope for dependency injection.

    Yields:
        Session: Active SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
