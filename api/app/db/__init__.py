"""The db package shares its name with app/db.py. Re-export that module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_PATH = Path(__file__).resolve().parent.parent / "db.py"
_SPEC = importlib.util.spec_from_file_location("app._db_file", _PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("app/db.py is missing")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules["app._db_file"] = _MODULE
_SPEC.loader.exec_module(_MODULE)

Analysis: Any = _MODULE.Analysis
ConfigRow: Any = _MODULE.ConfigRow
Dataset: Any = _MODULE.Dataset
Email: Any = _MODULE.Email
ensure_db: Any = _MODULE.ensure_db
reset_engine: Any = _MODULE.reset_engine
session: Any = _MODULE.session
RunRow: Any = _MODULE.RunRow
