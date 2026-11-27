"""Reference lists and weight files. Loaded from disk, cached, never fetched."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from layersight import __version__

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / "reference"


class Brand:
    def __init__(self, name: str, domains: list[str], labels: list[str]) -> None:
        self.name = name
        self.domains = [d.lower() for d in domains]
        self.labels = [label.lower() for label in labels]


class Weights:
    def __init__(self, bias: float, threshold: float, rules: dict[str, float], digest: str) -> None:
        self.bias = bias
        self.threshold = threshold
        self.rules = rules
        self.digest = digest

    def rule(self, rule_id: str) -> float:
        return self.rules[rule_id]


class CueWeights:
    def __init__(self, values: dict[str, float]) -> None:
        self.values = values

    @property
    def total(self) -> float:
        return sum(self.values.values()) or 1.0


class TrainingLevel:
    def __init__(self, base: float, sensitivity: float) -> None:
        self.base = base
        self.sensitivity = sensitivity


class Assumptions:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.default_org_domains = [str(d).lower() for d in raw["default_org_domains"]]
        clamp = raw["user_clamp"]
        self.user_clamp = (float(clamp[0]), float(clamp[1]))
        self.antivirus_password_factor = float(raw["antivirus_password_archive_factor"])
        self.training = {
            name: TrainingLevel(float(row["base"]), float(row["sensitivity"]))
            for name, row in raw["user_training"].items()
        }
        self.cues = CueWeights({k: float(v) for k, v in raw["cue_weights"].items()})
        self.statements = list(raw.get("statements", []))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def brands() -> tuple[Brand, ...]:
    raw = yaml.safe_load(_read(REFERENCE / "brands.yaml"))
    items = raw["brands"] if isinstance(raw, dict) else raw
    return tuple(
        Brand(str(item["name"]), list(item["domains"]), list(item["labels"])) for item in items
    )


@lru_cache(maxsize=1)
def freemail() -> frozenset[str]:
    lines = _read(REFERENCE / "freemail.txt").splitlines()
    return frozenset(line.strip().lower() for line in lines if line.strip())


@lru_cache(maxsize=1)
def shorteners() -> frozenset[str]:
    lines = _read(REFERENCE / "shorteners.txt").splitlines()
    return frozenset(line.strip().lower() for line in lines if line.strip())


@lru_cache(maxsize=1)
def suspicious_tlds() -> frozenset[str]:
    raw = yaml.safe_load(_read(REFERENCE / "tlds.yaml"))
    return frozenset(str(item).lower() for item in raw["suspicious"])


@lru_cache(maxsize=1)
def homoglyphs() -> tuple[tuple[tuple[str, str], ...], dict[str, str]]:
    raw = yaml.safe_load(_read(REFERENCE / "homoglyphs.yaml"))
    if "sequences" in raw:
        multi = tuple((str(item["from"]), str(item["to"])) for item in raw["sequences"])
        chars = {str(key): str(value) for key, value in raw.get("characters", {}).items()}
        return multi, chars
    multi = tuple((str(pair[0]), str(pair[1])) for pair in raw.get("multi", ()))
    chars = {str(key): str(value) for key, value in raw.get("single", {}).items()}
    chars.update({str(key): str(value) for key, value in raw.get("unicode", {}).items()})
    chars.update({str(key): str(value) for key, value in raw.get("chars", {}).items()})
    return multi, chars


@lru_cache(maxsize=1)
def phrases() -> dict[str, tuple[str, ...]]:
    raw = yaml.safe_load(_read(ROOT / "scoring" / "phrases.yaml"))
    return {str(key): tuple(str(item) for item in value) for key, value in raw.items()}


@lru_cache(maxsize=1)
def weights() -> Weights:
    path = ROOT / "scoring" / "weights.yaml"
    data = path.read_bytes()
    raw = yaml.safe_load(data.decode("utf-8"))
    digest = hashlib.sha256(data).hexdigest()[:16]
    rules = {str(key): float(value) for key, value in raw["rules"].items()}
    return Weights(float(raw["bias"]), float(raw["threshold"]), rules, digest)


@lru_cache(maxsize=1)
def assumptions() -> Assumptions:
    raw = yaml.safe_load(_read(ROOT / "config" / "assumptions.yaml"))
    return Assumptions(raw)


def engine_version() -> str:
    return __version__


def protected_domains(org_domains: list[str]) -> tuple[str, ...]:
    domains = {domain for brand in brands() for domain in brand.domains}
    domains.update(d.lower() for d in org_domains)
    return tuple(sorted(domains))
