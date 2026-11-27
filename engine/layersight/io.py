"""Load stub or real phase-1 analyses from JSON."""

import json
from pathlib import Path

from pydantic import ValidationError

from layersight.models import EmailAnalysis


class AnalysisLoadError(ValueError):
    """An analysis file is missing or does not match the contract."""


def load_analyses(source: Path | str) -> list[EmailAnalysis]:
    path = Path(source)
    if path.is_dir():
        files = sorted(
            item
            for item in path.iterdir()
            if item.suffix == ".json" and not item.name.startswith("_")
        )
        if not files:
            raise AnalysisLoadError(f"{path}: no analysis JSON files found")
        emails: list[EmailAnalysis] = []
        for file in files:
            emails.extend(_read_analysis_file(file))
        return emails
    if path.is_file():
        return _read_analysis_file(path)
    raise AnalysisLoadError(f"{path}: not found")


def _read_analysis_file(path: Path) -> list[EmailAnalysis]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AnalysisLoadError(f"{path.name}: invalid JSON ({exc})") from exc
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict) and isinstance(raw.get("emails"), list):
        items = raw["emails"]
    elif isinstance(raw, dict):
        items = [raw]
    else:
        raise AnalysisLoadError(f"{path.name}: expected an analysis object or a list")
    emails: list[EmailAnalysis] = []
    for index, item in enumerate(items):
        try:
            emails.append(EmailAnalysis.model_validate(item))
        except ValidationError as exc:
            raise AnalysisLoadError(f"{path.name}[{index}]: {exc}") from exc
    return emails
