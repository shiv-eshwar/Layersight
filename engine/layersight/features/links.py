"""Per-link facts: host, registrable domain, and look-alike score."""

from __future__ import annotations

import re
from dataclasses import dataclass

from layersight.features.domains import SimilarityHit, is_ip, similarity, split_domain
from layersight.models import ParsedEmail, ParsedLink
from layersight.reference_data import Brand, Homoglyphs
from layersight.textutil import host_of, split_http_url

_LOGIN = re.compile(
    r"\b(login|log[\s-]?in|sign[\s-]?in|verify|password|account|banking)\b",
    re.IGNORECASE,
)
_DOMAIN_IN_TEXT = re.compile(r"(?i)(?:https?://|hxxps?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})")


@dataclass(frozen=True)
class LinkFact:
    index: int
    text: str
    href: str
    source: str
    host: str
    registrable: str
    scheme: str
    path: str
    idn: bool
    ip: bool
    similarity: SimilarityHit


def annotate(
    links: list[ParsedLink],
    protected: list[str],
    glyphs: Homoglyphs,
) -> list[LinkFact]:
    facts: list[LinkFact] = []
    for index, link in enumerate(links, start=1):
        scheme, host, path = split_http_url(link.href)
        if not host:
            host = host_of(link.href)
        hit = similarity(host, protected, glyphs) if host else SimilarityHit(0.0, None, "none", "", False)
        facts.append(
            LinkFact(
                index=index,
                text=link.text,
                href=link.href,
                source=link.source,
                host=host,
                registrable=hit.closest if hit.technique == "legitimate" and hit.closest else _registrable(host),
                scheme=scheme,
                path=path,
                idn=hit.idn or host.startswith("xn--") or ".xn--" in host,
                ip=is_ip(host) if host else False,
                similarity=hit,
            )
        )
    return facts


def _registrable(host: str) -> str:
    from layersight.features.domains import registrable_domain

    return registrable_domain(host) if host else ""


def text_domain(text: str) -> str | None:
    match = _DOMAIN_IN_TEXT.search(text)
    if match is None:
        return None
    return match.group(1).lower()


def brand_in_unrelated(link: LinkFact, brands: tuple[Brand, ...]) -> Brand | None:
    if not link.host or link.ip:
        return None
    labels = {token for token in re.split(r"[^a-z0-9]+", f"{link.host}/{link.path}".lower()) if token}
    blob = f"{link.host}/{link.path}".lower()
    for brand in brands:
        if link.registrable in brand.domains:
            continue
        for domain in brand.domains:
            label = domain.split(".")[0]
            if len(label) >= 3 and label in labels:
                return brand
        if " " in brand.name and brand.name.lower() in blob:
            return brand
    return None


def suspicious_suffix(host: str, suspicious: frozenset[str]) -> str | None:
    if not host or is_ip(host):
        return None
    _label, suffix = split_domain(host)
    if not suffix:
        return None
    last = suffix.split(".")[-1]
    if last in suspicious or suffix in suspicious:
        return last
    return None


def is_shortener(link: LinkFact, shorteners: frozenset[str]) -> bool:
    return link.host in shorteners or link.registrable in shorteners


def http_login(link: LinkFact) -> bool:
    if link.scheme != "http":
        return False
    blob = f"{link.text} {link.path} {link.href}"
    return _LOGIN.search(blob) is not None


def sender_hit(parsed: ParsedEmail, protected: list[str], glyphs: Homoglyphs) -> SimilarityHit:
    domain = parsed.sender.domain or parsed.sender.registrable_domain
    if not domain:
        return SimilarityHit(0.0, None, "none", "", False)
    return similarity(domain, protected, glyphs)
