"""Registrable domains and look-alike scoring. The public suffix list is bundled; nothing is fetched."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import idna
import tldextract
from rapidfuzz.distance import DamerauLevenshtein, JaroWinkler

from layersight.models import CharDiff
from layersight.refs import homoglyphs
from layersight.textutil import host_of, refang

_PSL = Path(__file__).resolve().parents[1] / "reference" / "public_suffix_list.dat"
_LOOKALIKE_MIN = 0.80
_RANK = {
    "homoglyph": 5,
    "tld_swap": 4,
    "subdomain_abuse": 3,
    "combosquat": 2,
    "typosquat": 1,
}


@dataclass(frozen=True)
class HostParts:
    host: str
    subdomain: str
    domain: str
    suffix: str
    idn: bool


@dataclass(frozen=True)
class Similarity:
    score: float
    closest: str | None
    technique: str | None
    candidate_label: str
    closest_label: str
    diff: list[CharDiff]


@lru_cache(maxsize=1)
def _extractor() -> tldextract.TLDExtract:
    return tldextract.TLDExtract(
        suffix_list_urls=(_PSL.as_uri(),),
        cache_dir=None,
        fallback_to_snapshot=True,
    )


def is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def decode_host(host: str) -> tuple[str, bool]:
    idn_flag = False
    labels: list[str] = []
    for label in host.split("."):
        if label.startswith("xn--"):
            idn_flag = True
            try:
                labels.append(idna.decode(label))
            except idna.IDNAError:
                labels.append(label)
        else:
            if any(ord(char) > 127 for char in label):
                idn_flag = True
            labels.append(label)
    return ".".join(labels), idn_flag


def host_of_url(value: str) -> str:
    return host_of(value)


def split_host(host: str) -> HostParts:
    decoded, idn = decode_host(host_of(host))
    if not decoded or is_ip(decoded):
        return HostParts(decoded, "", "", "", idn)
    extracted = _extractor()(decoded)
    return HostParts(
        host=decoded,
        subdomain=(extracted.subdomain or "").lower(),
        domain=(extracted.domain or "").lower(),
        suffix=(extracted.suffix or "").lower(),
        idn=idn,
    )


def registrable(value: str) -> str:
    parts = split_host(value)
    if not parts.host:
        return ""
    if is_ip(parts.host):
        return parts.host
    if parts.domain and parts.suffix:
        return f"{parts.domain}.{parts.suffix}"
    return parts.host


def hosts_in_text(text: str) -> list[str]:
    found: list[str] = []
    pattern = re.compile(r"(?i)(?:https?://|hxxps?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})")
    for match in pattern.finditer(text):
        host = match.group(1).lower().rstrip(".")
        if host not in found:
            found.append(host)
    return found


def _skeleton(label: str) -> str:
    multi, chars = homoglyphs()
    text = label.lower()
    for source, target in chars.items():
        if len(source) == 1 and ord(source) > 127:
            text = text.replace(source, target)
    for source, target in multi:
        text = text.replace(source, target)
    for source, target in chars.items():
        if len(source) == 1 and ord(source) < 128:
            text = text.replace(source, target)
    return text.replace("-", "").replace("_", "")


def _char_diff(left: str, right: str) -> list[CharDiff]:
    return [
        CharDiff(char=char, changed=index >= len(right) or char != right[index])
        for index, char in enumerate(left)
    ]


def _typosquat(left: str, right: str) -> float:
    if min(len(left), len(right)) < 4 or abs(len(left) - len(right)) > 2:
        return 0.0
    damerau = float(DamerauLevenshtein.normalized_similarity(left, right))
    jaro = float(JaroWinkler.similarity(left, right))
    return max(damerau, jaro)


def _embeds(host: str, protected: str) -> bool:
    host = host.lower().strip(".")
    protected = protected.lower().strip(".")
    if not host or not protected or host == protected or host.endswith("." + protected):
        return False
    labels = host.split(".")
    prot = protected.split(".")
    width = len(prot)
    if len(labels) <= width:
        return False
    return any(labels[index : index + width] == prot for index in range(0, len(labels) - width))


def technique_label(technique: str | None) -> str:
    names = {
        "homoglyph": "homoglyph",
        "tld_swap": "TLD swap",
        "subdomain_abuse": "subdomain abuse",
        "combosquat": "combosquat",
        "typosquat": "typosquat",
        "legitimate": "legitimate",
    }
    return names.get(technique or "", technique or "none")


def similarity(candidate: str, protected: list[str] | tuple[str, ...]) -> Similarity:
    """Score one host. An exact protected domain is technique 'legitimate' with score 0."""
    parts = split_host(refang(candidate))
    blank = Similarity(0.0, None, None, "", "", [])
    if not parts.host or is_ip(parts.host):
        return blank
    own = registrable(parts.host)
    protected_regs: list[str] = []
    for item in protected:
        reg = registrable(item)
        if reg and reg not in protected_regs:
            protected_regs.append(reg)
    if own in protected_regs:
        return Similarity(0.0, own, "legitimate", parts.domain, parts.domain, [])

    best_score = 0.0
    best_tech: str | None = None
    best_closest: str | None = None
    best_target = ""
    best_diff: list[CharDiff] = []

    def consider(
        score: float,
        technique: str,
        closest: str,
        target_label: str,
        diff: list[CharDiff],
    ) -> None:
        nonlocal best_score, best_tech, best_closest, best_target, best_diff
        better = score > best_score + 1e-9
        tied = abs(score - best_score) <= 1e-9 and _RANK.get(technique, 0) > _RANK.get(best_tech or "", 0)
        if better or tied:
            best_score = score
            best_tech = technique
            best_closest = closest
            best_target = target_label
            best_diff = diff

    for preg in protected_regs:
        other = split_host(preg)
        if not other.domain:
            continue
        if parts.domain and _skeleton(parts.domain) == _skeleton(other.domain) and parts.domain != other.domain:
            consider(0.98, "homoglyph", preg, other.domain, _char_diff(parts.domain, other.domain))
        if parts.domain and parts.domain == other.domain and parts.suffix != other.suffix:
            consider(0.90, "tld_swap", preg, other.domain, _char_diff(parts.domain, other.domain))
        if _embeds(parts.host, preg):
            consider(0.90, "subdomain_abuse", preg, other.domain, _char_diff(parts.domain, other.domain))
        tokens = [token for token in re.split(r"[^a-z0-9]+", parts.domain) if token]
        if other.domain in tokens and parts.domain != other.domain:
            consider(0.85, "combosquat", preg, other.domain, _char_diff(parts.domain, other.domain))
        elif parts.domain and other.domain:
            for token in tokens:
                if token != other.domain and _skeleton(token) == _skeleton(other.domain):
                    consider(0.98, "homoglyph", preg, other.domain, _char_diff(token, other.domain))
        if parts.domain and other.domain and parts.domain != other.domain:
            score = _typosquat(parts.domain, other.domain)
            if score >= _LOOKALIKE_MIN:
                consider(score, "typosquat", preg, other.domain, _char_diff(parts.domain, other.domain))

    if best_tech is None or best_score < _LOOKALIKE_MIN:
        return Similarity(0.0, None, None, parts.domain, "", [])
    return Similarity(
        round(best_score, 4),
        best_closest,
        best_tech,
        parts.domain,
        best_target,
        best_diff,
    )
