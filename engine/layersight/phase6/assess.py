"""Turn one observed message into an EmailAnalysis.

Labels and file names are not inputs. Weights come from scoring/weights.yaml.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from layersight import __version__
from layersight.features.domains import SimilarityHit, is_ip, registrable_domain, similarity, split_domain
from layersight.models import EmailAnalysis, Evidence
from layersight.phase6.read import Observation
from layersight.reference_data import ReferenceData, load_reference
from layersight.scoring.weights import Weights, load_weights
from layersight.textutil import host_of

_PHRASES = Path(__file__).resolve().parents[1] / "scoring" / "phrases.yaml"
_RISKY_EXT = {
    "exe",
    "scr",
    "com",
    "msi",
    "bat",
    "cmd",
    "js",
    "vbs",
    "ps1",
    "hta",
    "wsf",
    "jar",
    "docm",
    "xlsm",
    "pptm",
    "html",
    "htm",
    "svg",
    "zip",
    "rar",
    "7z",
    "iso",
    "img",
}
_ROLES = ("ceo", "cfo", "president", "director", "executive", "payroll", "help desk", "it support")
_DOWNLOAD = re.compile(r"\b(download|install|enable macros|enable content)\b", re.IGNORECASE)
_PASSWORD = re.compile(r"\bpassword\b", re.IGNORECASE)


@dataclass
class _Hit:
    rule_id: str
    category: str
    title: str
    detail: str
    location: str | None
    points: float
    user_visible: bool


def analyze_observation(
    observed: Observation,
    email_id: str,
    org_domains: list[str] | None = None,
    reference: ReferenceData | None = None,
    weights: Weights | None = None,
) -> EmailAnalysis:
    ref = reference or load_reference()
    scale = weights or load_weights()
    org = tuple(registrable_domain(domain) or domain.lower() for domain in (org_domains or []))
    protected = list(ref.brand_domains) + [domain for domain in org if domain]
    hits: list[_Hit] = []
    lookalikes = _lookalikes(observed, protected, ref)
    best = max(lookalikes, key=lambda item: item[1].score, default=None)
    _headers(observed, ref, hits)
    _auth(observed, scale, hits)
    _links(observed, lookalikes, best, ref, scale, hits)
    flags = _content(observed.body, hits)
    attachment_class, password_archive = _attachments(observed, hits, scale)
    _trust(observed, org, hits)
    evidence = _evidence(hits)
    cue = _cue(scale, [hit.rule_id for hit in hits])
    risk = _risk(scale.bias, [item.contribution for item in evidence])
    label = "phishing" if risk >= scale.threshold else "genuine"
    vector, reason = _vector(observed, flags, best[1].score if best else 0.0, attachment_class)
    features: dict[str, object] = {
        "auth.spf": observed.spf,
        "auth.dkim": observed.dkim,
        "auth.dmarc": observed.dmarc,
        "header.reply_to_mismatch": bool(
            observed.reply_domain and observed.reply_domain != observed.sender_domain
        ),
        "links.max_lookalike_score": best[1].score if best else 0.0,
        "content.urgency": flags["C01"],
        "content.credential_request": flags["C02"],
        "content.payment_request": flags["C03"],
        "attachment.password_protected": password_archive,
    }
    if attachment_class:
        features["attachment.risk_class"] = attachment_class
    return EmailAnalysis(
        email_id=email_id,
        risk_score=risk,
        label=label,  # type: ignore[arg-type]
        band=_band(scale, risk),  # type: ignore[arg-type]
        attack_vector=vector,  # type: ignore[arg-type]
        vector_reason=reason,
        evidence=evidence,
        advice=_advice(evidence, label),
        cue_score=cue,
        features=features,
        engine_version=__version__,
        weights_hash=scale.digest,
    )


def _lookalikes(
    observed: Observation,
    protected: list[str],
    ref: ReferenceData,
) -> list[tuple[str, SimilarityHit]]:
    hosts: list[str] = []
    if observed.sender_domain:
        hosts.append(observed.sender_domain)
    if observed.reply_domain:
        hosts.append(observed.reply_domain)
    for _text, href in observed.links:
        host = host_of(href)
        if host:
            hosts.append(host)
    scored = []
    for host in hosts:
        hit = similarity(host, protected, ref.homoglyphs)
        scored.append((host, hit))
    return scored


def _headers(observed: Observation, ref: ReferenceData, hits: list[_Hit]) -> None:
    if observed.reply_domain and observed.reply_domain != observed.sender_domain:
        hits.append(
            _Hit(
                "H01",
                "header",
                "Reply-To mismatch",
                (
                    f"Replies go to {observed.reply_domain}, not {observed.sender_domain or 'the sender'}."
                ),
                "Reply-To",
                1.5,
                True,
            )
        )
    claimed = _claimed_brand(observed.sender_display, observed.sender_domain, ref)
    if claimed:
        hits.append(
            _Hit(
                "H02",
                "header",
                "Display name impersonates a brand",
                f"The name says {claimed}, but the address is {observed.sender_domain or 'unknown'}.",
                "From",
                1.5,
                True,
            )
        )
    if observed.return_domain and observed.return_domain != observed.sender_domain:
        hits.append(
            _Hit(
                "H03",
                "header",
                "Return-Path mismatch",
                f"The envelope domain is {observed.return_domain}.",
                "Return-Path",
                0.8,
                False,
            )
        )
    display = observed.sender_display.casefold()
    role = any(role in display for role in _ROLES)
    if observed.sender_domain in ref.freemail and (claimed or role):
        hits.append(
            _Hit(
                "H04",
                "header",
                "Free-mail account claiming a role",
                f"{observed.sender_address or observed.sender_domain} is free mail, not the organization.",
                "From",
                1.0,
                True,
            )
        )


def _claimed_brand(display: str, sender_domain: str, ref: ReferenceData) -> str | None:
    folded = display.casefold()
    if not folded:
        return None
    for brand in ref.brands:
        if sender_domain in brand.domains:
            continue
        for alias in brand.aliases:
            if alias and alias in folded:
                return brand.name
    return None


def _auth(observed: Observation, scale: Weights, hits: list[_Hit]) -> None:
    for rule_id, status, title in (
        ("A01", observed.spf, "SPF failed"),
        ("A02", observed.dkim, "DKIM failed"),
        ("A03", observed.dmarc, "DMARC failed"),
    ):
        points = scale.graded_points(rule_id, status)
        if points is None or points == 0:
            continue
        if status == "pass":
            continue
        hits.append(
            _Hit(
                rule_id,
                "auth",
                title if status == "fail" else f"{title} ({status})",
                f"Authentication reported {status}.",
                "Authentication-Results",
                points,
                False,
            )
        )
    if observed.spf == "pass" and observed.dkim == "pass" and observed.dmarc == "pass":
        hits.append(
            _Hit(
                "A04",
                "auth",
                "Authentication aligned",
                "SPF, DKIM, and DMARC all passed.",
                "Authentication-Results",
                scale.rule("A04"),
                False,
            )
        )


def _links(
    observed: Observation,
    lookalikes: list[tuple[str, object]],
    best: tuple[str, SimilarityHit] | None,
    ref: ReferenceData,
    scale: Weights,
    hits: list[_Hit],
) -> None:
    deceptive = _deceptive(observed)
    if deceptive:
        visible, href, real = deceptive
        hits.append(
            _Hit(
                "L01",
                "link",
                "Link text hides the destination",
                f"The link reads {visible}, but it goes to {real}.",
                "link",
                scale.rule("L01"),
                True,
            )
        )
    if best is not None:
        host, hit = best
        technique = hit.technique
        score = hit.score
        closest = hit.closest
        if technique not in {"none", "legitimate"} and score >= 0.8 and closest:
            hits.append(
                _Hit(
                    "L02",
                    "domain",
                    "Look-alike domain",
                    f"{host} imitates {closest} ({technique.replace('_', ' ')}, {score:.2f}).",
                    "domain",
                    scale.rule("L02") * score,
                    True,
                )
            )
    hosts = [host_of(href) for _text, href in observed.links]
    if any(is_ip(host) for host in hosts if host):
        hits.append(
            _Hit("L03", "link", "IP-address link", "A link uses a raw IP address.", "link", scale.rule("L03"), True)
        )
    if any(hit.idn for _host, hit in lookalikes):
        hits.append(
            _Hit("L04", "domain", "Punycode or IDN host", "A domain uses internationalized characters.", "domain", scale.rule("L04"), True)
        )
    if any(registrable_domain(host) in ref.shorteners for host in hosts if host):
        hits.append(
            _Hit("L05", "link", "URL shortener", "A link goes through a shortener.", "link", scale.rule("L05"), True)
        )
    if _brand_buried(observed, ref):
        hits.append(
            _Hit(
                "L06",
                "domain",
                "Brand hidden in the subdomain or path",
                "A protected brand appears somewhere other than the registrable domain.",
                "link",
                scale.rule("L06"),
                True,
            )
        )
    if any(_suspicious_suffix(host, ref) for host in hosts if host):
        hits.append(
            _Hit("L07", "domain", "Suspicious TLD", "A link uses a TLD often seen in phishing.", "link", scale.rule("L07"), True)
        )
    if _plain_http_login(observed):
        hits.append(
            _Hit("L08", "link", "Plain HTTP login link", "A login link is not protected by HTTPS.", "link", scale.rule("L08"), True)
        )
    unrelated = [
        registrable_domain(host)
        for host in hosts
        if host and registrable_domain(host) and registrable_domain(host) != observed.sender_domain
    ]
    if unrelated:
        hits.append(
            _Hit(
                "L09",
                "link",
                "Link leaves the sender's domain",
                f"A link goes to {unrelated[0]}, not {observed.sender_domain or 'the sender'}.",
                "link",
                scale.rule("L09"),
                True,
            )
        )


def _deceptive(observed: Observation) -> tuple[str, str, str] | None:
    for text, href in observed.links:
        real = registrable_domain(host_of(href))
        visible_hosts = re.findall(r"\b((?:[a-z0-9-]+\.)+[a-z]{2,})\b", text, flags=re.IGNORECASE)
        for visible in visible_hosts:
            shown = registrable_domain(visible)
            if shown and real and shown != real:
                return text.strip(), href, real
    return None


def _brand_buried(observed: Observation, ref: ReferenceData) -> bool:
    labels = {
        domain.split(".")[0]
        for domain in ref.brand_domains
        if "." in domain and len(domain.split(".")[0]) >= 4
    }
    for _text, href in observed.links:
        host = host_of(href).lower()
        reg = registrable_domain(host)
        subdomain = host[: -(len(reg) + 1)] if reg and host.endswith("." + reg) else ""
        path = href.split("?", 1)[0].lower()
        for label in labels:
            buried = label in subdomain.split(".") or f"/{label}" in path
            if buried and reg not in ref.brand_domains:
                return True
    return False


def _plain_http_login(observed: Observation) -> bool:
    pattern = re.compile(r"login|verify|password|sign in", re.IGNORECASE)
    for text, href in observed.links:
        if href.lower().startswith("http://") and pattern.search(f"{text} {href}"):
            return True
    return False


def _suspicious_suffix(host: str, ref: ReferenceData) -> bool:
    _label, suffix = split_domain(host)
    if not suffix:
        return False
    last = suffix.split(".")[-1]
    return suffix in ref.suspicious_tlds or last in ref.suspicious_tlds


def _content(body: str, hits: list[_Hit]) -> dict[str, bool]:
    phrases = _phrase_table()
    flags = {"C01": False, "C02": False, "C03": False, "C04": False, "C05": False}
    titles = {
        "C01": ("Urgency", 0.8, "The message pushes the reader to act quickly."),
        "C02": ("Credential request", 1.2, "The message asks for an account or password action."),
        "C03": ("Payment request", 1.2, "The message asks for money or new payment details."),
        "C04": ("Generic greeting", 0.4, "The greeting does not use the recipient's name."),
        "C05": ("Threat of loss", 0.6, "The message threatens a locked, suspended, or deleted account."),
    }
    folded = body.casefold()
    for rule_id, options in phrases.items():
        if rule_id not in titles:
            continue
        for phrase in options:
            if re.search(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", folded):
                title, points, detail = titles[rule_id]
                hits.append(_Hit(rule_id, "content", title, detail, "body", points, True))
                flags[rule_id] = True
                break
    return flags


def _phrase_table() -> dict[str, tuple[str, ...]]:
    if not _PHRASES.is_file():
        return {}
    raw = yaml.safe_load(_PHRASES.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    return {str(key): tuple(str(item) for item in value) for key, value in raw.items()}


def _attachments(
    observed: Observation, hits: list[_Hit], scale: Weights
) -> tuple[str | None, bool]:
    if not observed.attachments:
        return None, False
    order = ["executable", "script", "macro_document", "html", "archive", "document", "image", "other"]
    chosen = min(observed.attachments, key=lambda item: order.index(item.risk_class) if item.risk_class in order else 99)
    password = bool(_PASSWORD.search(observed.body)) and chosen.risk_class == "archive"
    if chosen.risk_class in {"executable", "script"}:
        hits.append(
            _Hit(
                "T01",
                "attachment",
                "Executable or script attachment",
                f"Don't open {chosen.filename}. Real invoices are never executable files.",
                chosen.filename,
                scale.rule("T01"),
                True,
            )
        )
    if chosen.double_extension:
        hits.append(
            _Hit(
                "T02",
                "attachment",
                "Double extension",
                f"{chosen.filename} hides a second extension.",
                chosen.filename,
                scale.rule("T02"),
                True,
            )
        )
    if chosen.risk_class == "macro_document":
        hits.append(
            _Hit("T03", "attachment", "Macro-enabled document", f"{chosen.filename} can run macros.", chosen.filename, scale.rule("T03"), True)
        )
    if chosen.risk_class == "archive":
        points = scale.rule("T04") + (scale.bonus.get("T04_password", 0.0) if password else 0.0)
        hits.append(
            _Hit("T04", "attachment", "Archive attachment", f"{chosen.filename} is an archive.", chosen.filename, points, True)
        )
    if chosen.risk_class == "html":
        hits.append(
            _Hit("T05", "attachment", "HTML attachment", f"{chosen.filename} is an HTML file.", chosen.filename, scale.rule("T05"), True)
        )
    return chosen.risk_class, password


def _trust(observed: Observation, org: tuple[str, ...], hits: list[_Hit]) -> None:
    aligned = observed.spf == "pass" and observed.dkim == "pass" and observed.dmarc == "pass"
    if observed.sender_domain in org and aligned:
        hits.append(
            _Hit(
                "G01",
                "trust",
                "Organization domain, authenticated",
                f"{observed.sender_domain} is an organization domain and authentication passed.",
                "From",
                -1.0,
                False,
            )
        )
    regs = [registrable_domain(host_of(href)) for _text, href in observed.links]
    regs = [item for item in regs if item]
    if regs and observed.sender_domain and all(item == observed.sender_domain for item in regs):
        hits.append(
            _Hit(
                "G02",
                "trust",
                "Links stay on the sender's domain",
                "Every link uses the sender's registrable domain.",
                "link",
                -0.5,
                False,
            )
        )


def _evidence(hits: list[_Hit]) -> list[Evidence]:
    total = sum(abs(hit.points) for hit in hits) or 1.0
    evidence = [
        Evidence(
            rule_id=hit.rule_id,
            category=hit.category,  # type: ignore[arg-type]
            title=hit.title,
            detail=hit.detail,
            location=hit.location,
            contribution=hit.points,
            share=hit.points / total,
            user_visible=hit.user_visible,
        )
        for hit in hits
    ]
    evidence.sort(key=lambda item: item.contribution, reverse=True)
    return evidence


def _cue(scale: Weights, rule_ids: list[str]) -> float:
    total = sum(scale.cue.values()) or 1.0
    present = sum(scale.cue.get(rule_id, 0.0) for rule_id in set(rule_ids))
    return max(0.0, min(1.0, present / total))


def _risk(bias: float, contributions: list[float]) -> float:
    logit = bias + sum(contributions)
    return 1.0 / (1.0 + math.exp(-logit))


def _band(scale: Weights, risk: float) -> str:
    if risk >= scale.critical:
        return "critical"
    if risk >= scale.high:
        return "high"
    if risk >= scale.suspicious:
        return "suspicious"
    return "low"


def _vector(
    observed: Observation,
    flags: dict[str, bool],
    lookalike: float,
    attachment_class: str | None,
) -> tuple[str, str]:
    risky = {"executable", "script", "macro_document", "archive", "html"}
    if attachment_class in risky:
        return "malware_attachment", "The attachment is a file an endpoint control can inspect."
    risky_link = False
    for text, href in observed.links:
        path = href.rsplit("/", 1)[-1].lower()
        extension = path.rsplit(".", 1)[-1] if "." in path else ""
        if extension in _RISKY_EXT or _DOWNLOAD.search(text):
            risky_link = True
            break
    if risky_link and observed.links:
        return "malware_link", "A link offers a download or a risky file type."
    if observed.links and (flags["C02"] or lookalike >= 0.8):
        return "credential_harvest", "The message asks for credentials or imitates a brand."
    if not observed.links and attachment_class not in risky and flags["C03"]:
        return "payment_fraud", "The message asks for payment and carries no malware payload."
    if observed.links:
        return "credential_harvest", "The message contains links and no stronger vector."
    return "payment_fraud", "The message has no link or risky attachment."


def _advice(evidence: list[Evidence], label: str) -> list[str]:
    chosen = [item.detail for item in evidence if item.contribution > 0][:3]
    if label == "phishing":
        chosen.append("Report it with the Report Phish button, then delete it.")
    elif not chosen:
        chosen.append(
            "No strong warning signs. Still confirm unexpected requests for money or credentials through a separate channel."
        )
    return chosen
