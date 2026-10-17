"""Lazy database engine/session factory.

Deferring driver loading lets health endpoints and unit tests load even when the
configured database driver is not installed; readiness still fails safely if the
real database dependency cannot be initialized.
"""
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings


def build_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


@lru_cache

def get_engine():
    return build_engine()


@lru_cache

def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
