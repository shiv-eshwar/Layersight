"""Load scoring weights. The file bytes are the source of the weights hash."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_PATH = Path(__file__).resolve().parent / "weights.yaml"


@dataclass(frozen=True)
class Weights:
    bias: float
    threshold: float
    critical: float
    high: float
    suspicious: float
    rules: dict[str, float]
    graded: dict[str, dict[str, float]]
    bonus: dict[str, float]
    cue: dict[str, float]
    digest: str

    def rule(self, rule_id: str) -> float:
        return self.rules[rule_id]

    def graded_points(self, rule_id: str, status: str) -> float | None:
        table = self.graded.get(rule_id, {})
        if status in table:
            return float(table[status])
        if status == "fail" and rule_id in self.rules:
            return float(self.rules[rule_id])
        return None


@lru_cache(maxsize=1)
def load_weights() -> Weights:
    raw = _PATH.read_bytes()
    data = yaml.safe_load(raw)
    bands = data["bands"]
    graded = {
        str(rule_id): {str(status): float(points) for status, points in table.items()}
        for rule_id, table in data.get("graded", {}).items()
    }
    return Weights(
        bias=float(data["bias"]),
        threshold=float(data["threshold"]),
        critical=float(bands["critical"]),
        high=float(bands["high"]),
        suspicious=float(bands["suspicious"]),
        rules={str(rule_id): float(points) for rule_id, points in data["rules"].items()},
        graded=graded,
        bonus={str(key): float(points) for key, points in data.get("bonus", {}).items()},
        cue={str(rule_id): float(points) for rule_id, points in data.get("cue", {}).items()},
        digest=hashlib.sha256(raw).hexdigest(),
    )
