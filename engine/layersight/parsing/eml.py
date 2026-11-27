"""Tolerant RFC 5322, MIME, and simplified-text parser.

Malformed input returns a ParsedEmail and a warning. It does not raise.
Attachment bytes are never decoded.
"""

from __future__ import annotations

import email
import re
from email import policy
from email.message import EmailMessage
from email.utils import getaddresses

from layersight.features.domains import registrable
from layersight.models import Address, ParsedEmail, ParsedLink
from layersight.parsing.attachments import classify_attachment, take_pseudo_attachments
from layersight.parsing.auth_results import parse_auth
from layersight.parsing.html import links_from_html, links_from_text

_HEADER = re.compile(r"^[A-Za-z][A-Za-z0-9-]*:[ \t]*")


def normalize_newlines(raw: str) -> str:
    return raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


def separate_headers(text: str) -> str:
    if "\n\n" in text:
        return text
    lines = text.split("\n")
    index = 0
    saw = False
    while index < len(lines):
        line = lines[index]
        if line == "":
            break
        if _HEADER.match(line) or (saw and line[:1] in {" ", "\t"}):
            saw = True
            index += 1
            continue
        break
    if not saw:
        return text
    return "\n".join(lines[:index]) + "\n\n" + "\n".join(lines[index:])


def _address(name: str, addr: str) -> Address | None:
    cleaned = addr.strip().strip("<>").strip().lower()
    if "@" not in cleaned:
        return None
    local, domain = cleaned.rsplit("@", 1)
    domain = domain.strip().strip(".")
    if not local or not domain:
        return None
    return Address(
        display_name=" ".join(name.split()),
        address=f"{local}@{domain}",
        domain=domain,
        registrable_domain=registrable(domain),
    )


def _addresses(value: str | None) -> list[Address]:
    if not value:
        return []
    found: list[Address] = []
    for name, addr in getaddresses([value]):
        parsed = _address(name, addr)
        if parsed is not None:
            found.append(parsed)
    return found


def _text(part: EmailMessage) -> str:
    try:
        content = part.get_content()
    except Exception:
        payload = part.get_payload(decode=False)
        content = payload if isinstance(payload, str) else ""
    if isinstance(content, bytes):
        charset = part.get_content_charset() or "utf-8"
        return content.decode(charset, errors="replace")
    return str(content or "")


def _with_registrable(link: ParsedLink) -> ParsedLink:
    if link.registrable_domain:
        return link
    return link.model_copy(update={"registrable_domain": registrable(link.href)})


def _dedupe(links: list[ParsedLink]) -> list[ParsedLink]:
    seen: set[tuple[str, str]] = set()
    unique: list[ParsedLink] = []
    for link in links:
        key = (link.text.strip(), link.href.strip())
        if not link.href.strip() or key in seen:
            continue
        seen.add(key)
        unique.append(_with_registrable(link))
    return unique


def parse_email(raw: str) -> ParsedEmail:
    warnings: list[str] = []
    try:
        normalized = normalize_newlines(raw)
        text = separate_headers(normalized)
        if text != normalized:
            warnings.append("inserted a blank line between the headers and the body")
        message = email.message_from_string(text, policy=policy.default)
        if not isinstance(message, EmailMessage):
            warnings.append("message used a legacy parser container")
            return ParsedEmail(body_text=raw.strip(), parse_warnings=warnings)
        senders = _addresses(str(message.get("from") or ""))
        if not senders:
            warnings.append("no From address")
        elif len(senders) > 1:
            warnings.append("multiple From addresses; the first one is the sender")
        replies = _addresses(str(message.get("reply-to") or ""))
        returns = _addresses(str(message.get("return-path") or ""))
        plain_parts: list[str] = []
        rendered_parts: list[str] = []
        links: list[ParsedLink] = []
        attachments = []
        parts = [part for part in message.walk() if not part.is_multipart()] if message.is_multipart() else [message]
        for part in parts:
            filename = part.get_filename()
            disposition = (part.get_content_disposition() or "").lower()
            if disposition == "attachment" or filename:
                attachments.append(
                    classify_attachment(filename or "unknown", part.get_content_type() or "application/octet-stream")
                )
                continue
            try:
                body = _text(part)
            except Exception as exc:
                warnings.append(f"skipped a body part: {exc.__class__.__name__}")
                continue
            if part.get_content_type() == "text/html":
                extracted, rendered = links_from_html(body)
                links.extend(extracted)
                if rendered.strip():
                    rendered_parts.append(rendered.strip())
            else:
                plain_parts.append(body)
        plain = "\n".join(part.strip() for part in plain_parts if part.strip())
        rendered = "\n".join(rendered_parts)
        body_text = plain
        if rendered and rendered.strip() != plain.strip():
            body_text = f"{plain}\n{rendered}".strip() if plain else rendered
        links.extend(links_from_text(plain))
        links.extend(links_from_text(rendered))
        pseudo, body_text = take_pseudo_attachments(body_text)
        attachments.extend(pseudo)
        for key, value in message.items():
            header_items, _rest = take_pseudo_attachments(f"{key}: {value}")
            attachments.extend(header_items)
        deduped = []
        seen_files: set[tuple[str, str]] = set()
        for item in attachments:
            file_key = (item.filename.lower(), item.content_type.lower())
            if file_key in seen_files:
                continue
            seen_files.add(file_key)
            deduped.append(item)
        return ParsedEmail(
            subject=str(message.get("subject") or ""),
            date=str(message.get("date") or "") or None,
            sender=senders[0] if senders else Address(),
            reply_to=replies[0] if replies else None,
            return_path=returns[0] if returns else None,
            auth=parse_auth(message),
            links=_dedupe(links),
            attachments=deduped,
            body_text=body_text,
            parse_warnings=warnings,
        )
    except Exception as exc:
        warnings.append(f"parser recovered from {exc.__class__.__name__}")
        return ParsedEmail(body_text=raw.strip(), parse_warnings=warnings)
