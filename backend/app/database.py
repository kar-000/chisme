import logging
import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = (
    {"connect_args": {"check_same_thread": False}}
    if _is_sqlite
    else {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20}
)

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def configure_wal_for_replication() -> None:
    """Configure PostgreSQL WAL for streaming replication.

    Only runs when CHISME_ROLE=primary (the default) and the database is
    PostgreSQL.  Safe to call multiple times — ALTER SYSTEM is idempotent.
    Logs a warning and returns quietly on any error (e.g. insufficient privs).
    """
    if _is_sqlite:
        return  # SQLite has no WAL replication concept

    role = os.getenv("CHISME_ROLE", "primary")
    if role != "primary":
        logger.info("Skipping WAL configuration (CHISME_ROLE=%s)", role)
        return

    logger.info("Configuring PostgreSQL WAL for future replication support…")
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER SYSTEM SET wal_level = 'replica';"))
            conn.execute(text("ALTER SYSTEM SET max_wal_senders = 10;"))
            conn.execute(text("ALTER SYSTEM SET max_replication_slots = 10;"))
            conn.execute(text("ALTER SYSTEM SET hot_standby = on;"))
            conn.execute(text("ALTER SYSTEM SET wal_keep_size = '1GB';"))
            conn.commit()
        logger.info("WAL configuration applied. A PostgreSQL restart is required for settings to take effect.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("WAL configuration skipped: %s", exc)
