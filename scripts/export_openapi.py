"""Write the FastAPI schema to api/openapi.json for `make types`."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "api" / "openapi.json"


def main() -> None:
    DESTINATION.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(DESTINATION)


if __name__ == "__main__":
    main()
