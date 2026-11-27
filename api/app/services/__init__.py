"""Re-export app/services.py. This package otherwise hides that module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_PATH = Path(__file__).resolve().parent.parent / "services.py"
_SPEC = importlib.util.spec_from_file_location("app._services_file", _PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("app/services.py is missing")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules["app._services_file"] = _MODULE
_SPEC.loader.exec_module(_MODULE)

APIError: Any = _MODULE.APIError
email_detail: Any = _MODULE.email_detail
ingest: Any = _MODULE.ingest
list_configs: Any = _MODULE.list_configs
list_datasets: Any = _MODULE.list_datasets
list_emails: Any = _MODULE.list_emails
report_csv: Any = _MODULE.report_csv
reset_demo: Any = _MODULE.reset_demo
validation_report: Any = _MODULE.validation_report
import_config_text: Any = _MODULE.import_config_text
simulate_dataset: Any = _MODULE.simulate_dataset
load_run: Any = _MODULE.load_run
compare_configs: Any = _MODULE.compare_configs
recommend_dataset: Any = _MODULE.recommend_dataset
override_vector: Any = _MODULE.override_vector
