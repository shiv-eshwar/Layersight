"""Seed the database from the practice test set. `python -m app.demo_seed`."""

from __future__ import annotations

from app.db import session
from app.services import reset_demo


def main() -> None:
    db = next(session())
    try:
        result = reset_demo(db)
    finally:
        db.close()
    print(result)


if __name__ == "__main__":
    main()
