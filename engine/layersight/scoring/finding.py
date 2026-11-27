"""One fired rule, before it is turned into evidence."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Finding:
    rule_id: str
    category: str
    title: str
    detail: str
    location: str | None
    weight: float
    strength: float = 1.0
    user_visible: bool = False
    variables: dict[str, str] = field(default_factory=dict)

    @property
    def contribution(self) -> float:
        return self.weight * self.strength
