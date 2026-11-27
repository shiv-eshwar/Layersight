"""Vercel entrypoint. Every route, including /api/v1, is served by FastAPI.

Supabase's free plan already has two active projects, so this deployment
keeps the practice set in /tmp and reloads it on a cold start. Set
DATABASE_URL to a Postgres URL to make the data durable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "api"))
sys.path.insert(0, str(_ROOT / "engine"))

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/layersight.db")
os.environ.setdefault("CORS_ORIGINS", "*")

from app.main import app  # noqa: E402


def _seed_practice_set() -> None:
    if not os.environ.get("VERCEL"):
        return
    from app.db import session
    from app.services import list_datasets, reset_demo

    db = next(session())
    try:
        if list_datasets(db):
            return
        reset_demo(db)
    finally:
        db.close()


try:
    _seed_practice_set()
except Exception as exc:  # noqa: BLE001
    print(f"practice seed skipped: {exc}")
