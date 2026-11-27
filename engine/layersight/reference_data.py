"""Bundled reference data. Loaded from disk so the analysis path stays offline."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent / "reference"


@dataclass(frozen=True)
class Brand:
    name: str
    domains: tuple[str, ...]
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Homoglyphs:
    single: dict[str, str]
    multi: tuple[tuple[str, str], ...]
    unicode_map: dict[str, str]


@dataclass(frozen=True)
class ReferenceData:
    brands: tuple[Brand, ...]
    freemail: frozenset[str]
    shorteners: frozenset[str]
    suspicious_tlds: frozenset[str]
    homoglyphs: Homoglyphs

    @property
    def brand_domains(self) -> tuple[str, ...]:
        domains: list[str] = []
        for brand in self.brands:
            domains.extend(brand.domains)
        return tuple(domains)


def _lines(name: str) -> tuple[str, ...]:
    text = (_ROOT / name).read_text(encoding="utf-8")
    return tuple(line.strip().lower() for line in text.splitlines() if line.strip() and not line.startswith("#"))


@lru_cache(maxsize=1)
def load_reference() -> ReferenceData:
    raw = yaml.safe_load((_ROOT / "brands.yaml").read_text(encoding="utf-8"))
    brands: list[Brand] = []
    for item in raw["brands"]:
        brands.append(
            Brand(
                name=str(item["name"]),
                domains=tuple(str(domain).lower() for domain in item["domains"]),
                aliases=tuple(str(alias).lower() for alias in item.get("aliases", [])),
            )
        )
    glyphs = yaml.safe_load((_ROOT / "homoglyphs.yaml").read_text(encoding="utf-8"))
    tlds = yaml.safe_load((_ROOT / "tlds.yaml").read_text(encoding="utf-8"))
    return ReferenceData(
        brands=tuple(brands),
        freemail=frozenset(_lines("freemail.txt")),
        shorteners=frozenset(_lines("shorteners.txt")),
        suspicious_tlds=frozenset(str(item).lower() for item in tlds["suspicious"]),
        homoglyphs=Homoglyphs(
            single={str(key): str(value) for key, value in glyphs["single"].items()},
            multi=tuple((str(pair[0]), str(pair[1])) for pair in glyphs["multi"]),
            unicode_map={str(key): str(value) for key, value in glyphs["unicode"].items()},
        ),
    )
