"""Domain table and deceptive-link list for one dataset."""

from __future__ import annotations

import re

from layersight.features.domains import registrable_domain, similarity
from layersight.phase6.models import BrandRow, DeceptiveLink, DomainReport, DomainRow, SimilarityView
from layersight.phase6.records import ScoredMail
from layersight.reference_data import ReferenceData, load_reference
from layersight.textutil import host_of

_VISIBLE = re.compile(r"\b((?:[a-z0-9-]+\.)+[a-z]{2,})\b", re.IGNORECASE)


def domain_report(
    dataset_id: str,
    mails: list[ScoredMail],
    org_domains: list[str],
    reference: ReferenceData | None = None,
) -> DomainReport:
    ref = reference or load_reference()
    protected = _protected(ref, org_domains)
    rows: dict[str, _Bucket] = {}
    deceptive: list[DeceptiveLink] = []
    for mail in mails:
        hosts = _hosts(mail)
        for host in hosts:
            hit = similarity(host, protected, ref.homoglyphs)
            domain = registrable_domain(host) or host
            bucket = rows.get(domain)
            if bucket is None or hit.score > bucket.score:
                rows[domain] = _Bucket(
                    domain=domain,
                    score=hit.score,
                    closest=hit.closest,
                    technique=hit.technique,
                    diff=hit.diff,
                    sentence=_sentence(domain, hit.technique, hit.closest, hit.score),
                    occurrences=0,
                    email_ids=[],
                )
            current = rows[domain]
            current.occurrences += 1
            if mail.email_id not in current.email_ids:
                current.email_ids.append(mail.email_id)
        deceptive.extend(_deceptive_links(mail, protected, ref))
    ordered = sorted(rows.values(), key=lambda item: (-item.score, item.domain))
    return DomainReport(
        dataset_id=dataset_id,
        domains=[
            DomainRow(
                domain=item.domain,
                closest_brand=item.closest,
                similarity=item.score,
                technique=item.technique,
                occurrences=item.occurrences,
                email_ids=item.email_ids,
                diff=item.diff,
                sentence=item.sentence,
            )
            for item in ordered
        ],
        deceptive_links=deceptive,
    )


def check_domain(candidate: str, org_domains: list[str], reference: ReferenceData | None = None) -> SimilarityView:
    ref = reference or load_reference()
    hit = similarity(candidate, _protected(ref, org_domains), ref.homoglyphs)
    shown = registrable_domain(candidate) or candidate.strip()
    return SimilarityView(
        candidate=shown or candidate.strip(),
        score=hit.score,
        closest=hit.closest,
        technique=hit.technique,
        diff=hit.diff,
        sentence=_sentence(shown or candidate.strip(), hit.technique, hit.closest, hit.score),
        legitimate=hit.technique == "legitimate",
    )


def brand_rows(report: DomainReport) -> list[BrandRow]:
    grouped: dict[str, BrandRow] = {}
    for row in report.domains:
        if row.technique in {"legitimate", "none"} or not row.closest_brand or row.similarity < 0.8:
            continue
        current = grouped.get(row.closest_brand)
        if current is None or row.similarity > current.similarity:
            grouped[row.closest_brand] = BrandRow(
                brand=row.closest_brand,
                occurrences=row.occurrences,
                technique=row.technique,
                similarity=row.similarity,
            )
        else:
            grouped[row.closest_brand] = current.model_copy(
                update={"occurrences": current.occurrences + row.occurrences}
            )
    return sorted(grouped.values(), key=lambda item: (-item.occurrences, -item.similarity))


class _Bucket:
    def __init__(
        self,
        domain: str,
        score: float,
        closest: str | None,
        technique: str,
        diff: str,
        sentence: str,
        occurrences: int,
        email_ids: list[str],
    ) -> None:
        self.domain = domain
        self.score = score
        self.closest = closest
        self.technique = technique
        self.diff = diff
        self.sentence = sentence
        self.occurrences = occurrences
        self.email_ids = email_ids


def _hosts(mail: ScoredMail) -> list[str]:
    hosts: list[str] = []
    if mail.observed.sender_domain:
        hosts.append(mail.observed.sender_domain)
    if mail.observed.reply_domain:
        hosts.append(mail.observed.reply_domain)
    for _text, href in mail.observed.links:
        host = host_of(href)
        if host:
            hosts.append(host)
    return hosts


def _deceptive_links(mail: ScoredMail, protected: list[str], ref: ReferenceData) -> list[DeceptiveLink]:
    found: list[DeceptiveLink] = []
    for text, href in mail.observed.links:
        real = registrable_domain(host_of(href))
        for visible in _VISIBLE.findall(text):
            shown = registrable_domain(visible)
            if not shown or not real or shown == real:
                continue
            hit = similarity(real, protected, ref.homoglyphs)
            found.append(
                DeceptiveLink(
                    email_id=mail.email_id,
                    subject=mail.subject,
                    visible_text=text.strip(),
                    href=href,
                    visible_domain=shown,
                    real_domain=real,
                    closest_brand=hit.closest,
                    similarity=hit.score,
                    technique=hit.technique,
                    sentence=_sentence(real, hit.technique, hit.closest, hit.score),
                )
            )
            break
    return found


def _protected(ref: ReferenceData, org_domains: list[str]) -> list[str]:
    extra = [registrable_domain(domain) or domain.lower() for domain in org_domains]
    return list(ref.brand_domains) + [domain for domain in extra if domain]


def _sentence(domain: str, technique: str, closest: str | None, score: float) -> str:
    if technique == "legitimate":
        return f"{domain} matches a protected domain."
    if technique == "none" or not closest:
        return f"{domain} does not resemble a protected brand."
    label = technique.replace("_", " ")
    if technique == "homoglyph":
        return f"{domain} imitates {closest} by swapping characters (homoglyph, {score:.2f})."
    if technique == "tld_swap":
        return f"{domain} keeps the name of {closest} and changes the suffix (TLD swap, {score:.2f})."
    if technique == "subdomain_abuse":
        return f"{domain} places {closest} in a subdomain (subdomain abuse, {score:.2f})."
    if technique == "combosquat":
        return f"{domain} adds extra words around {closest} (combosquat, {score:.2f})."
    if technique == "typosquat":
        return f"{domain} is a small edit of {closest} (typosquat, {score:.2f})."
    return f"{domain} is closest to {closest} ({label}, {score:.2f})."
