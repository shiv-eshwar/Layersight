"""Brand and list files, read tolerantly.

The shared reference loader is still moving. Phase 6 only needs the lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1] / "reference"


@dataclass(frozen=True)
class Brand:
    name: str
    domains: tuple[str, ...]
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class CorpusRef:
    brands: tuple[Brand, ...]
    freemail: frozenset[str]
    shorteners: frozenset[str]
    suspicious_tlds: frozenset[str]

    @property
    def brand_domains(self) -> tuple[str, ...]:
        domains: list[str] = []
        for brand in self.brands:
            domains.extend(brand.domains)
        return tuple(domains)


@lru_cache(maxsize=1)
def load_corpus() -> CorpusRef:
    raw = yaml.safe_load((_ROOT / "brands.yaml").read_text(encoding="utf-8"))
    brands: list[Brand] = []
    for item in raw.get("brands", []):
        aliases = item.get("aliases") or item.get("labels") or []
        brands.append(
            Brand(
                name=str(item.get("name") or ""),
                domains=tuple(str(domain).lower() for domain in item.get("domains", [])),
                aliases=tuple(str(alias).lower() for alias in aliases),
            )
        )
    tlds = yaml.safe_load((_ROOT / "tlds.yaml").read_text(encoding="utf-8"))
    suspicious = tlds.get("suspicious", []) if isinstance(tlds, dict) else []
    return CorpusRef(
        brands=tuple(brands),
        freemail=_lines("freemail.txt"),
        shorteners=_lines("shorteners.txt"),
        suspicious_tlds=frozenset(str(item).lower() for item in suspicious),
    )


def _lines(name: str) -> frozenset[str]:
    text = (_ROOT / name).read_text(encoding="utf-8")
    return frozenset(
        line.strip().lower() for line in text.splitlines() if line.strip() and not line.startswith("#")  # noqa: E501
    )
