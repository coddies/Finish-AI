from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import get_settings


def _database_url() -> str:
    url = get_settings().database_url
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _engine_options(url: str) -> dict:
    connect_args = ({"check_same_thread": False} if url.startswith("sqlite") else
                    {"prepare_threshold": None} if url.startswith("postgresql+psycopg://") else {})
    return {"poolclass": StaticPool if url.endswith(":memory:") else NullPool,
            "connect_args": connect_args, "pool_pre_ping": True,
            "hide_parameters": True, "future": True}


class Base(DeclarativeBase):
    pass


_url = _database_url()
engine = create_engine(_url, **_engine_options(_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
