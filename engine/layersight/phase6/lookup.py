"""A stable view over domain similarity.

`features.domains` is shared with the analysis phase and its signature can move.
Callers in phase 6 go through this module.
"""

from __future__ import annotations

from dataclasses import dataclass

from layersight.features.domains import registrable, similarity, split_host
from layersight.models import CharDiff


@dataclass(frozen=True)
class Hit:
    score: float
    closest: str | None
    technique: str
    diff: str
    idn: bool


def registrable_domain(value: str) -> str:
    return registrable(value)


def score(candidate: str, protected: list[str] | tuple[str, ...]) -> Hit:
    found = similarity(candidate, protected)
    technique = found.technique or "none"
    return Hit(
        score=found.score,
        closest=found.closest,
        technique=technique,
        diff=_diff_text(found.diff, found.closest_label),
        idn=split_host(candidate).idn,
    )


def suffix_of(host: str) -> str:
    return split_host(host).suffix


def _diff_text(diff: list[CharDiff], closest_label: str) -> str:
    if not diff:
        return closest_label
    text = "".join(f"[{item.char}]" if item.changed else item.char for item in diff)
    if closest_label:
        return f"{text} vs {closest_label}"
    return text
