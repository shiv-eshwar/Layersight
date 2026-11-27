"""Canonical layer configuration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Op = Literal["eq", "ne", "in", "gte", "lte", "contains", "exists"]
Training = Literal["none", "basic", "advanced"]


class Match(BaseModel):
    feature: str
    op: Op
    value: Any = None


class FilterRule(BaseModel):
    id: str
    description: str = ""
    match: Match
    catch_rate: float = Field(ge=0, le=1)
    enabled: bool = True


class EmailFilter(BaseModel):
    base_catch_rate: float = Field(ge=0, le=1)
    rules: list[FilterRule] = Field(default_factory=list)


class UserTraining(BaseModel):
    level: Training = "none"
    catch_rate: float | None = Field(default=None, ge=0, le=1)


class ApplicationControl(BaseModel):
    effectiveness: float = Field(ge=0, le=1)
    overrides: dict[str, float] = Field(default_factory=dict)


class Antivirus(BaseModel):
    detection_rate: float = Field(ge=0, le=1)


class Segmentation(BaseModel):
    containment_rate: float = Field(ge=0, le=1)
    applies_to_credential_harvest: bool = True


class SimulationSettings(BaseModel):
    runs: int = Field(default=10000, ge=1, le=1_000_000)
    seed: int = 42


class LayerConfig(BaseModel):
    schema_version: int = 1
    name: str
    org_domains: list[str] = Field(default_factory=lambda: ["company.com"])
    email_filter: EmailFilter
    user_training: UserTraining
    application_control: ApplicationControl
    antivirus: Antivirus
    segmentation: Segmentation
    simulation: SimulationSettings = Field(default_factory=SimulationSettings)


def match_feature(features: dict[str, Any], match: Match) -> bool:
    feature = features.get(match.feature)
    op = match.op
    value = match.value
    if op == "exists":
        return feature not in (None, "", False, "none")
    if op == "eq":
        return bool(feature == value)
    if op == "ne":
        return bool(feature != value)
    if op == "in":
        return feature in (value or [])
    if op == "contains":
        if isinstance(feature, str):
            return str(value) in feature
        if isinstance(feature, (list, tuple)):
            return value in feature
        return False
    if feature is None:
        return False
    try:
        number = float(feature)
        target = float(value)
    except (TypeError, ValueError):
        return False
    if op == "gte":
        return number >= target
    if op == "lte":
        return number <= target
    return False
