"""Database sessions. Connections open on first use, not at import."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.settings import Settings

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None
_ready = False


def _sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def build_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if _sqlite(url) else {}
    engine = create_engine(url, future=True, pool_pre_ping=not _sqlite(url), connect_args=connect_args)

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection: object, _record: object) -> None:
        if _sqlite(url):
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_engine() -> Engine:
    global _engine, _factory, _ready
    if _engine is None or _factory is None:
        url = Settings().database_url
        _engine = build_engine(url)
        _factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
        if not _ready:
            if _sqlite(url):
                Base.metadata.create_all(_engine)
            else:
                from app.db.migrate import upgrade

                upgrade(url)
            _ready = True
    return _engine


def get_db() -> Iterator[Session]:
    get_engine()
    assert _factory is not None
    session = _factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    assert _factory is not None
    session = _factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
