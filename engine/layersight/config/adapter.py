"""Load a canonical config, or adapt a looser official-style file onto it."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from layersight.config.schema import LayerConfig

_TRAINING = {
    "none": "none",
    "untrained": "none",
    "low": "none",
    "basic": "basic",
    "medium": "basic",
    "advanced": "advanced",
    "trained": "advanced",
    "high": "advanced",
}
_KNOWN = {
    "schema_version",
    "name",
    "org_domains",
    "email_filter",
    "user_training",
    "application_control",
    "antivirus",
    "segmentation",
    "simulation",
    "email_filter_catch_rate",
    "filter_catch_rate",
    "user_training_level",
    "application_control_effectiveness",
    "antivirus_detection_rate",
    "segmentation_containment_rate",
    "segmentation_applies_to_credential_harvest",
    "runs",
    "seed",
    "rules",
}


class ConfigError(Exception):
    def __init__(self, detail: str, fields: list[dict[str, str]]) -> None:
        super().__init__(detail)
        self.detail = detail
        self.fields = fields


def load_config(path: Path) -> tuple[LayerConfig, list[str]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError(f"{path.name} is not a mapping.", [{"field": path.name, "message": "expected a YAML mapping"}])
    return adapt(raw, source=path.name)


def adapt(data: dict[str, Any], source: str = "config") -> tuple[LayerConfig, list[str]]:
    warnings = [f"Ignored unknown key '{key}'." for key in data if key not in _KNOWN]
    if _is_canonical(data):
        try:
            config = LayerConfig.model_validate(data)
        except ValidationError as exc:
            raise ConfigError(_format_validation(exc), _fields(exc)) from exc
        config.org_domains = [item.lower() for item in config.org_domains]
        return config, warnings
    loose, extra = _from_loose(data, source)
    warnings.extend(extra)
    try:
        config = LayerConfig.model_validate(loose)
    except ValidationError as exc:
        raise ConfigError(_format_validation(exc), _fields(exc)) from exc
    return config, warnings


def _is_canonical(data: dict[str, Any]) -> bool:
    return data.get("schema_version") == 1 and isinstance(data.get("email_filter"), dict)


def _from_loose(data: dict[str, Any], source: str) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    level_raw = str(data.get("user_training_level", data.get("user_training", "none"))).strip().lower()
    if isinstance(data.get("user_training"), dict):
        raise ConfigError(
            "user_training must be a level name in the loose format, or use schema_version 1.",
            [{"field": "user_training", "message": "use schema_version 1 for the full object"}],
        )
    mapped = _TRAINING.get(level_raw)
    if mapped is None:
        raise ConfigError(
            f"user_training '{level_raw}' is not one of none, basic, advanced.",
            [{"field": "user_training", "message": "expected none, basic, or advanced"}],
        )
    rules = data.get("rules") or []
    if rules and not isinstance(rules, list):
        raise ConfigError("rules must be a list.", [{"field": "rules", "message": "expected a list"}])
    body = {
        "schema_version": 1,
        "name": str(data.get("name") or source),
        "org_domains": data.get("org_domains") or ["company.com"],
        "email_filter": {
            "base_catch_rate": _fraction(data.get("email_filter_catch_rate", data.get("filter_catch_rate", 0.35)), "email_filter_catch_rate", warnings),
            "rules": rules,
        },
        "user_training": {"level": mapped, "catch_rate": None},
        "application_control": {
            "effectiveness": _fraction(data.get("application_control_effectiveness", data.get("application_control", 0.25)), "application_control", warnings),
            "overrides": {"macro_document": 0.90, "executable": 0.95},
        },
        "antivirus": {
            "detection_rate": _fraction(data.get("antivirus_detection_rate", data.get("antivirus", 0.55)), "antivirus", warnings),
        },
        "segmentation": {
            "containment_rate": _fraction(data.get("segmentation_containment_rate", data.get("segmentation", 0.40)), "segmentation", warnings),
            "applies_to_credential_harvest": bool(data.get("segmentation_applies_to_credential_harvest", True)),
        },
        "simulation": {"runs": int(data.get("runs", 10000)), "seed": int(data.get("seed", 42))},
    }
    return body, warnings


def _fraction(value: Any, field: str, warnings: list[str]) -> float:
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("%"):
            return float(text[:-1]) / 100
        number = float(text)
    else:
        number = float(value)
    if number > 1:
        warnings.append(f"{field} was above 1 and was read as a percent.")
        return number / 100
    if number < 0:
        raise ConfigError(f"{field} must be between 0 and 1.", [{"field": field, "message": "expected 0 to 1"}])
    return number


def _format_validation(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        loc = ".".join(str(item) for item in error["loc"])
        parts.append(f"{loc}: {error['msg']}")
    return "; ".join(parts)


def _fields(exc: ValidationError) -> list[dict[str, str]]:
    return [
        {"field": ".".join(str(item) for item in error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]
