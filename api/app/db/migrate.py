"""Apply the Alembic migration chain."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command

_API_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def upgrade(url: str) -> None:
    config = Config(str(_API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_MIGRATIONS))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")
