"""Turn raw email text into a score, evidence, advice, and a presentation."""

from __future__ import annotations

import hashlib
import math
from typing import Any

from layersight import __version__
from layersight.models import (
    Band,
    Bundle,
    EmailAnalysis,
    Evidence,
    ParsedEmail,
    Presentation,
    Verdict,
)
from layersight.parsing.eml import parse_email
from layersight.parsing.text import defang_text
from layersight.refs import assumptions, protected_domains, weights
from layersight.scoring.advice import build_advice
from layersight.scoring.finding import Finding
from layersight.scoring.rules import collect_findings, content_hits, link_views, password_in_body
from layersight.scoring.vectors import classify


def analyze_email(raw: str, org_domains: list[str] | None = None) -> Bundle:
    parsed = parse_email(raw)
    orgs = [item.lower() for item in (org_domains or assumptions().default_org_domains)]
    protected = protected_domains(orgs)
    views = link_views(parsed.links, protected)
    content_source = "\n".join([parsed.body_text, parsed.subject, *(view.text for view in views)])
    hits = content_hits(content_source)
    findings = collect_findings(parsed, views, orgs, protected, hits)
    table = weights()
    logit = table.bias + sum(item.contribution for item in findings)
    risk = 1.0 / (1.0 + math.exp(-logit))
    label: Verdict = "phishing" if risk >= table.threshold else "genuine"
    band = _band(risk)
    cue = _cue(findings)
    max_lookalike = max((view.similarity for view in views), default=0.0)
    vector, reason = classify(
        parsed.attachments,
        views,
        credential="C02" in {item.rule_id for item in findings},
        payment="C03" in {item.rule_id for item in findings},
        max_lookalike=max_lookalike,
        body=content_source,
    )
    if label == "genuine":
        reason = "Predicted genuine, so this is not treated as an attack. " + reason
    features = _features(parsed, findings, views, risk, password_in_body(parsed.body_text))
    evidence = _evidence(findings)
    advice = build_advice(label, findings, parsed)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    analysis = EmailAnalysis(
        email_id=digest[:16],
        risk_score=risk,
        label=label,
        band=band,
        attack_vector=vector,
        vector_reason=reason,
        evidence=evidence,
        advice=advice,
        cue_score=cue,
        features=features,
        engine_version=__version__,
        weights_hash=table.digest,
    )
    mismatches: list[str] = []
    sender = parsed.sender.registrable_domain
    if parsed.reply_to and sender and parsed.reply_to.registrable_domain != sender:
        mismatches.append("Reply-To uses a different domain than From.")
    if parsed.return_path and sender and parsed.return_path.registrable_domain != sender:
        mismatches.append("Return-Path uses a different domain than From.")
    if any(item.rule_id == "H02" for item in findings):
        mismatches.append("The display name does not match the address domain.")
    presentation = Presentation(
        subject=parsed.subject,
        date=parsed.date,
        sender=parsed.sender,
        reply_to=parsed.reply_to,
        return_path=parsed.return_path,
        auth=parsed.auth,
        mismatches=mismatches,
        links=views,
        attachments=parsed.attachments,
        body_text_sanitized=defang_text(parsed.body_text),
        highlights=list(hits.values()),
        parse_warnings=parsed.parse_warnings,
    )
    return Bundle(sha256=digest, analysis=analysis, presentation=presentation)


def _band(risk: float) -> Band:
    if risk >= 0.85:
        return "critical"
    if risk >= 0.70:
        return "high"
    if risk >= 0.50:
        return "suspicious"
    return "low"


def _cue(findings: list[Finding]) -> float:
    fired = {item.rule_id for item in findings}
    cues = assumptions().cues
    present = 0.0
    if "C04" in fired:
        present += cues.values["generic_greeting"]
    if "C01" in fired:
        present += cues.values["urgency"]
    if "C05" in fired:
        present += cues.values["threat"]
    if "L01" in fired:
        present += cues.values["link_mismatch"]
    if "L02" in fired:
        present += cues.values["misspelled_domain"]
    if fired & {"T01", "T02", "T03", "T04", "T05"}:
        present += cues.values["unexpected_attachment"]
    if fired & {"C02", "C03"}:
        present += cues.values["credential_or_payment"]
    return present / cues.total


def _features(
    parsed: ParsedEmail,
    findings: list[Finding],
    views: list[Any],
    risk: float,
    password: bool,
) -> dict[str, Any]:
    fired = {item.rule_id for item in findings}
    attachments = parsed.attachments
    worst = "none"
    order = ["executable", "script", "macro_document", "html", "archive", "document", "image", "other"]
    classes = [item.risk_class for item in attachments]
    for name in order:
        if name in classes:
            worst = name
            break
    return {
        "auth.spf": parsed.auth.spf,
        "auth.dkim": parsed.auth.dkim,
        "auth.dmarc": parsed.auth.dmarc,
        "header.reply_to_mismatch": "H01" in fired,
        "header.return_path_mismatch": "H03" in fired,
        "header.display_name_mismatch": "H02" in fired,
        "links.max_lookalike_score": max((float(view.similarity) for view in views), default=0.0),
        "links.count": len(views),
        "attachment.risk_class": worst,
        "attachment.double_extension": any(item.double_extension for item in attachments),
        "attachment.password_in_body": password and worst == "archive",
        "content.urgency": "C01" in fired,
        "content.credential": "C02" in fired,
        "content.payment": "C03" in fired,
        "content.threat": "C05" in fired,
        "content.generic_greeting": "C04" in fired,
        "risk_score": risk,
    }


def _evidence(findings: list[Finding]) -> list[Evidence]:
    ordered = sorted(findings, key=lambda item: item.contribution, reverse=True)
    total = sum(abs(item.contribution) for item in ordered) or 1.0
    rows: list[Evidence] = []
    allowed: set[str] = {"header", "auth", "link", "domain", "content", "attachment", "trust"}
    for item in ordered:
        category = item.category if item.category in allowed else "content"
        rows.append(
            Evidence(
                rule_id=item.rule_id,
                category=category,  # type: ignore[arg-type]
                title=item.title,
                detail=item.detail,
                location=item.location,
                contribution=item.contribution,
                share=abs(item.contribution) / total,
                user_visible=item.user_visible,
            )
        )
    return rows


def rule_ids(raw: str) -> set[str]:
    return {item.rule_id for item in analyze_email(raw).analysis.evidence}
