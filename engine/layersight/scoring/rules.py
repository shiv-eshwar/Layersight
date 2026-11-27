"""Header, authentication, link, content, attachment, and trust rules."""

from __future__ import annotations

import re

from layersight.features.domains import (
    hosts_in_text,
    host_of_url,
    registrable,
    similarity,
    split_host,
    technique_label,
)
from layersight.models import Address, Attachment, AuthResult, LinkView, ParsedEmail, ParsedLink
from layersight.parsing.text import defang
from layersight.refs import Brand, brands, freemail, phrases, shorteners, suspicious_tlds, weights
from layersight.scoring.finding import Finding

_ROLES = (
    r"\bceo\b",
    r"\bcfo\b",
    r"\bchief executive\b",
    r"\bchief financial\b",
    r"\bpresident\b",
    r"\bit support\b",
    r"\bhelp\s?desk\b",
    r"\bsecurity team\b",
    r"\bpayroll\b",
)
_LOGIN = re.compile(r"login|verify|password|signin|sign-in", re.IGNORECASE)
_PASSWORD = re.compile(r"\bpassword\b", re.IGNORECASE)


def content_hits(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for rule_id, options in phrases().items():
        for phrase in options:
            match = re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE)
            if match:
                found[rule_id] = match.group(0)
                break
    return found


def password_in_body(text: str) -> bool:
    return _PASSWORD.search(text) is not None


def link_views(links: list[ParsedLink], protected: tuple[str, ...]) -> list[LinkView]:
    views: list[LinkView] = []
    for link in links:
        host = host_of_url(link.href)
        sim = similarity(host, protected) if host else None
        views.append(
            LinkView(
                text=link.text,
                href=link.href,
                display_href=defang(link.href),
                registrable_domain=link.registrable_domain,
                similarity=0.0 if sim is None else sim.score,
                closest=None if sim is None else sim.closest,
                technique=None if sim is None else sim.technique,
                candidate_label="" if sim is None else sim.candidate_label,
                closest_label="" if sim is None else sim.closest_label,
                diff=[] if sim is None else list(sim.diff),
            )
        )
    return views


def collect_findings(
    parsed: ParsedEmail,
    views: list[LinkView],
    org_domains: list[str],
    protected: tuple[str, ...],
    content: dict[str, str],
) -> list[Finding]:
    table = weights()
    found: list[Finding] = []
    found.extend(_headers(parsed, org_domains, table))
    found.extend(_auth(parsed.auth, table))
    found.extend(_links(parsed, views, protected, table))
    found.extend(_content(content, table))
    found.extend(_attachments(parsed.attachments, table, content_password=password_in_body(parsed.body_text)))
    found.extend(_trust(parsed, views, org_domains, table))
    return found


def _headers(parsed: ParsedEmail, org_domains: list[str], table: object) -> list[Finding]:
    weight = table.rule  # type: ignore[attr-defined]
    found: list[Finding] = []
    sender = parsed.sender.registrable_domain
    reply = parsed.reply_to.registrable_domain if parsed.reply_to else ""
    return_path = parsed.return_path.registrable_domain if parsed.return_path else ""
    if sender and reply and sender != reply:
        found.append(
            Finding(
                rule_id="H01",
                category="header",
                title="Reply-To is a different domain",
                detail=f"Replies would go to {reply}, not {sender}.",
                location="Reply-To",
                weight=weight("H01"),
                user_visible=True,
                variables={"reply_domain": reply, "from_domain": sender},
            )
        )
    if _display_mismatch(parsed.sender, org_domains):
        found.append(
            Finding(
                rule_id="H02",
                category="header",
                title="Display name doesn't match the address",
                detail=(
                    f"The name \"{parsed.sender.display_name}\" doesn't belong with {sender or 'this address'}."
                ),
                location="From",
                weight=weight("H02"),
                user_visible=True,
            )
        )
    if sender and return_path and sender != return_path:
        found.append(
            Finding(
                rule_id="H03",
                category="header",
                title="Return-Path is a different domain",
                detail=f"The envelope sender is {return_path}, not {sender}.",
                location="Return-Path",
                weight=weight("H03"),
                user_visible=False,
            )
        )
    if _freemail_claim(parsed.sender):
        found.append(
            Finding(
                rule_id="H04",
                category="header",
                title="Free mail claiming an organization",
                detail=f"{parsed.sender.address} is free webmail, and the name claims a role or a brand.",
                location="From",
                weight=weight("H04"),
                user_visible=True,
            )
        )
    return found


def _display_mismatch(sender: Address, org_domains: list[str]) -> bool:
    display = sender.display_name.strip()
    if not display:
        return False
    domain = sender.registrable_domain
    if domain in org_domains:
        return False
    low = display.lower()
    catalog = brands()
    for brand in catalog:
        if _mentions_brand(low, brand) and domain not in brand.domains:
            return True
    if any(re.search(pattern, low) for pattern in _ROLES):
        if domain in freemail():
            return True
        brand_domains = {item for brand in catalog for item in brand.domains}
        if domain not in brand_domains:
            return True
    return False


def _freemail_claim(sender: Address) -> bool:
    domain = sender.registrable_domain
    if domain not in freemail():
        return False
    low = sender.display_name.lower()
    if not low:
        return False
    for brand in brands():
        if _mentions_brand(low, brand) and domain not in brand.domains:
            return True
    return any(re.search(pattern, low) for pattern in _ROLES)


def _mentions_brand(display: str, brand: Brand) -> bool:
    names = [brand.name.lower(), *brand.labels]
    return any(re.search(rf"\b{re.escape(name)}\b", display) for name in names)


def _auth(auth: AuthResult, table: object) -> list[Finding]:
    weight = table.rule  # type: ignore[attr-defined]
    found: list[Finding] = []
    if auth.spf == "fail":
        found.append(_auth_finding("A01", "SPF failed", "The sending server is not allowed to send this mail.", weight("A01")))
    elif auth.spf == "softfail":
        found.append(_auth_finding("A01", "SPF soft-failed", "The sending server is only weakly authorized.", weight("A01_softfail")))
    if auth.dkim == "fail" or auth.dkim == "softfail":
        found.append(_auth_finding("A02", "DKIM failed", "The message signature failed, so the body may have been altered.", weight("A02")))
    elif auth.dkim == "none":
        found.append(_auth_finding("A02", "No DKIM signature", "The message has no DKIM signature.", weight("A02_none")))
    if auth.dmarc == "fail":
        found.append(_auth_finding("A03", "DMARC failed", "Sender authentication failed, so the From address is probably forged.", weight("A03")))
    if auth.spf == "pass" and auth.dkim == "pass" and auth.dmarc == "pass":
        found.append(
            Finding(
                rule_id="A04",
                category="auth",
                title="Authentication passed",
                detail="SPF, DKIM, and DMARC all passed and align with the From address.",
                location="Authentication-Results",
                weight=weight("A04"),
                user_visible=False,
            )
        )
    return found


def _auth_finding(rule_id: str, title: str, detail: str, points: float) -> Finding:
    return Finding(
        rule_id=rule_id,
        category="auth",
        title=title,
        detail=detail,
        location="Authentication-Results",
        weight=points,
        user_visible=False,
    )


def _links(
    parsed: ParsedEmail,
    views: list[LinkView],
    protected: tuple[str, ...],
    table: object,
) -> list[Finding]:
    weight = table.rule  # type: ignore[attr-defined]
    found: list[Finding] = []
    sender = parsed.sender.registrable_domain
    sender_sim = similarity(sender, protected) if sender else None

    best: LinkView | None = None
    best_score = sender_sim.score if sender_sim and sender_sim.technique not in (None, "legitimate") else 0.0
    best_source = "sender domain"
    best_sim_domain = sender if sender_sim and best_score else ""
    best_closest = sender_sim.closest if sender_sim else None
    best_technique = sender_sim.technique if sender_sim else None
    if best_score < 0.80:
        best_score = 0.0
        best_closest = None
        best_technique = None
        best_sim_domain = ""

    text_mismatch = False
    mismatch_view: LinkView | None = None
    suspicious_host = False
    shortener = False
    ip_link = False
    idn = False
    http_login = False
    brand_abuse: str | None = None
    unrelated = False

    for view in views:
        host = host_of_url(view.href)
        parts = split_host(host)
        if parts.host and re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", parts.host):
            ip_link = True
        if parts.idn:
            idn = True
        if view.registrable_domain in shorteners():
            shortener = True
        suffix = parts.suffix.split(".")[-1] if parts.suffix else ""
        if suffix in suspicious_tlds() or parts.suffix in suspicious_tlds():
            suspicious_host = True
        if view.href.lower().startswith("http://") and _LOGIN.search(f"{view.href} {view.text}"):
            http_login = True
        if sender and view.registrable_domain and view.registrable_domain != sender:
            unrelated = True
        text_domains = {registrable(item) for item in hosts_in_text(view.text)}
        text_domains.discard("")
        if text_domains and view.registrable_domain and view.registrable_domain not in text_domains:
            text_mismatch = True
            mismatch_view = view
        if view.similarity >= 0.80 and view.technique not in (None, "legitimate") and view.similarity > best_score:
            best = view
            best_score = view.similarity
            best_source = "link href"
            best_sim_domain = view.registrable_domain
            best_closest = view.closest
            best_technique = view.technique
        abuse = _brand_in_url(view.href, view.registrable_domain)
        if abuse and brand_abuse is None:
            brand_abuse = abuse

    if text_mismatch and mismatch_view is not None:
        shown = ", ".join(sorted({registrable(item) for item in hosts_in_text(mismatch_view.text) if item}))
        found.append(
            Finding(
                rule_id="L01",
                category="link",
                title="Link text hides the destination",
                detail=(
                    f"The link reads as {shown or mismatch_view.text}, "
                    f"but it goes to {mismatch_view.registrable_domain}."
                ),
                location="link",
                weight=weight("L01"),
                user_visible=True,
                variables={
                    "domain": mismatch_view.registrable_domain,
                    "brand_domain": shown or mismatch_view.registrable_domain,
                },
            )
        )
    if best_score >= 0.80 and best_closest and best_technique not in (None, "legitimate"):
        found.append(
            Finding(
                rule_id="L02",
                category="domain",
                title="Look-alike domain",
                detail=(
                    f"{best_sim_domain} imitates {best_closest} "
                    f"({technique_label(best_technique)}, {best_score:.2f})."
                ),
                location=best_source if best is None else "link href",
                weight=weight("L02"),
                strength=best_score,
                user_visible=True,
                variables={"domain": best_sim_domain, "brand_domain": best_closest},
            )
        )
    if ip_link:
        found.append(_link("L03", "Link uses an IP address", "A link points at a bare IP address instead of a domain.", weight("L03")))
    if idn:
        found.append(_link("L04", "Punycode or internationalized host", "A link uses an internationalized or punycode host.", weight("L04")))
    if shortener:
        found.append(_link("L05", "Shortened link", "A link uses a URL shortener, so the destination is hidden.", weight("L05")))
    if brand_abuse:
        found.append(
            _link(
                "L06",
                "Brand name in the wrong place",
                f"The brand {brand_abuse} appears in the subdomain or the path of an unrelated site.",
                weight("L06"),
            )
        )
    if suspicious_host:
        found.append(_link("L07", "Suspicious top-level domain", "A link uses a top-level domain that is often abused.", weight("L07")))
    if http_login:
        found.append(_link("L08", "Unencrypted login link", "A login or verify link uses plain HTTP.", weight("L08")))
    if unrelated:
        found.append(
            _link(
                "L09",
                "Link leaves the sender's domain",
                "At least one link goes to a different registrable domain than the sender.",
                weight("L09"),
            )
        )
    return found


def _brand_in_url(href: str, reg_domain: str) -> str | None:
    host = host_of_url(href)
    parts = split_host(host)
    labels = [label for label in parts.subdomain.split(".") if label and label != "www"]
    path_tokens = [token for token in re.split(r"[^a-z0-9]+", href.lower()) if token]
    for brand in brands():
        if reg_domain in brand.domains:
            continue
        for label in brand.labels:
            if len(label) < 4:
                continue
            if label in labels or label in path_tokens:
                return brand.domains[0]
    return None


def _link(rule_id: str, title: str, detail: str, points: float) -> Finding:
    return Finding(
        rule_id=rule_id,
        category="link",
        title=title,
        detail=detail,
        location="link",
        weight=points,
        user_visible=True,
    )


def _content(content: dict[str, str], table: object) -> list[Finding]:
    weight = table.rule  # type: ignore[attr-defined]
    catalog = {
        "C01": ("Urgency", "The message pushes the reader to act quickly."),
        "C02": ("Credential request", "The message asks the reader to verify an account or a password."),
        "C03": ("Payment request", "The message asks for a payment, a wire, or new bank details."),
        "C04": ("Generic greeting", "The greeting doesn't name the recipient."),
        "C05": ("Threat of loss", "The message threatens a locked, suspended, or deleted account."),
    }
    found: list[Finding] = []
    for rule_id, (title, lead) in catalog.items():
        if rule_id not in content:
            continue
        phrase = content[rule_id]
        found.append(
            Finding(
                rule_id=rule_id,
                category="content",
                title=title,
                detail=f"{lead} It says \"{phrase}\".",
                location="body",
                weight=weight(rule_id),
                user_visible=True,
                variables={"phrase": phrase},
            )
        )
    return found


def _attachments(attachments: list[Attachment], table: object, *, content_password: bool) -> list[Finding]:
    weight = table.rule  # type: ignore[attr-defined]
    found: list[Finding] = []
    if any(item.risk_class in {"executable", "script"} for item in attachments):
        name = next(item.filename for item in attachments if item.risk_class in {"executable", "script"})
        found.append(
            Finding(
                rule_id="T01",
                category="attachment",
                title="Executable or script attachment",
                detail=f"{name} is an executable or a script. The file itself was not opened.",
                location="attachment",
                weight=weight("T01"),
                user_visible=True,
                variables={"filename": name},
            )
        )
    if any(item.double_extension for item in attachments):
        name = next(item.filename for item in attachments if item.double_extension)
        found.append(
            Finding(
                rule_id="T02",
                category="attachment",
                title="Double file extension",
                detail=f"{name} hides an executable extension behind a document name.",
                location="attachment",
                weight=weight("T02"),
                user_visible=True,
                variables={"filename": name},
            )
        )
    if any(item.risk_class == "macro_document" for item in attachments):
        name = next(item.filename for item in attachments if item.risk_class == "macro_document")
        found.append(
            Finding(
                rule_id="T03",
                category="attachment",
                title="Macro-enabled document",
                detail=f"{name} can run macros. The file itself was not opened.",
                location="attachment",
                weight=weight("T03"),
                user_visible=True,
                variables={"filename": name},
            )
        )
    if any(item.risk_class == "archive" for item in attachments):
        name = next(item.filename for item in attachments if item.risk_class == "archive")
        extra = weight("T04_password") if content_password else 0.0
        detail = f"{name} is an archive. The file itself was not opened."
        if content_password:
            detail += " The message also contains a password."
        found.append(
            Finding(
                rule_id="T04",
                category="attachment",
                title="Archive attachment",
                detail=detail,
                location="attachment",
                weight=weight("T04") + extra,
                user_visible=True,
                variables={"filename": name},
            )
        )
    if any(item.risk_class == "html" for item in attachments):
        name = next(item.filename for item in attachments if item.risk_class == "html")
        found.append(
            Finding(
                rule_id="T05",
                category="attachment",
                title="HTML attachment",
                detail=f"{name} is an HTML file, which can imitate a login page. The file itself was not opened.",
                location="attachment",
                weight=weight("T05"),
                user_visible=True,
                variables={"filename": name},
            )
        )
    return found


def _trust(
    parsed: ParsedEmail,
    views: list[LinkView],
    org_domains: list[str],
    table: object,
) -> list[Finding]:
    weight = table.rule  # type: ignore[attr-defined]
    found: list[Finding] = []
    sender = parsed.sender.registrable_domain
    aligned = parsed.auth.dmarc == "pass"
    if sender in org_domains and aligned:
        found.append(
            Finding(
                rule_id="G01",
                category="trust",
                title="Organization domain, authentication aligned",
                detail=f"{sender} is an organization domain and DMARC passed.",
                location="From",
                weight=weight("G01"),
                user_visible=False,
            )
        )
    domains = {view.registrable_domain for view in views if view.registrable_domain}
    if domains and sender and domains <= {sender}:
        found.append(
            Finding(
                rule_id="G02",
                category="trust",
                title="Links stay on the sender's domain",
                detail=f"Every link stays on {sender}.",
                location="link",
                weight=weight("G02"),
                user_visible=False,
            )
        )
    return found
