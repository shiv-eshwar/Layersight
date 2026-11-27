"""SQLite by default, Postgres when DATABASE_URL points there. Created on first use."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from app.settings import settings


class Base(DeclarativeBase):
    pass


class Dataset(Base):
    __tablename__ = "dataset"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Email(Base):
    __tablename__ = "email"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64))
    raw_text: Mapped[str] = mapped_column(Text)
    ground_truth: Mapped[str | None] = mapped_column(String(16), nullable=True)


class Analysis(Base):
    __tablename__ = "analysis"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email_id: Mapped[str] = mapped_column(ForeignKey("email.id", ondelete="CASCADE"), unique=True)
    engine_version: Mapped[str] = mapped_column(String(32))
    weights_hash: Mapped[str] = mapped_column(String(64))
    risk_score: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(16))
    payload: Mapped[str] = mapped_column(Text)


class ConfigRow(Base):
    __tablename__ = "layer_config"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)


_engine = None
_session_factory: sessionmaker[Session] | None = None
_url: str | None = None


def database_url() -> str:
    return os.environ.get("DATABASE_URL", settings.database_url)


def reset_engine() -> None:
    global _engine, _session_factory, _url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
    _url = None


def _build(url: str):
    if url.startswith("sqlite"):
        if url.startswith("sqlite:///"):
            path = url.removeprefix("sqlite:///")
            if path and path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}
        if ":memory:" in url:
            return create_engine(url, connect_args=connect_args, poolclass=StaticPool)
        return create_engine(url, connect_args=connect_args)
    return create_engine(url, pool_pre_ping=True)


def ensure_db() -> sessionmaker[Session]:
    global _engine, _session_factory, _url
    url = database_url()
    if _session_factory is not None and _url == url:
        return _session_factory
    reset_engine()
    _engine = _build(url)
    Base.metadata.create_all(_engine)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    _url = url
    return _session_factory


def session() -> Iterator[Session]:
    factory = ensure_db()
    db = factory()
    try:
        yield db
    finally:
        db.close()
