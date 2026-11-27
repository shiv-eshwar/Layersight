"""Read a raw message far enough for intelligence, the quiz, and the command center.

The full parser lives in `layersight.parsing`. This reader stays on the standard
library so these screens still load while that package is in progress. It never
decodes attachment bytes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from email import message_from_string
from email.policy import default as default_policy
from email.utils import getaddresses
from html.parser import HTMLParser

from layersight.features.domains import is_ip, registrable_domain
from layersight.textutil import host_of

_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_AUTH = re.compile(r"\b(spf|dkim|dmarc)=([a-z]+)", re.IGNORECASE)
_PSEUDO = (
    re.compile(r"(?im)^Attachment:\s*(.+?)\s*\(([^)]+)\)\s*$"),
    re.compile(r"(?im)^\[Attachment:\s*([^;\]]+?)\s*;\s*([^\]]+?)\s*\]\s*$"),
    re.compile(r"(?im)^X-Attachment:\s*([^;\n]+?)\s*;\s*(?:type=)?(\S+)\s*$"),
)
_AUTH_MAP = {
    "pass": "pass",
    "fail": "fail",
    "softfail": "softfail",
    "none": "none",
    "neutral": "none",
    "temperror": "softfail",
    "permerror": "fail",
}
_RANK = {"none": 0, "pass": 1, "softfail": 2, "fail": 3}
_RISK = {
    "exe": "executable",
    "scr": "executable",
    "com": "executable",
    "msi": "executable",
    "bat": "executable",
    "cmd": "executable",
    "js": "script",
    "vbs": "script",
    "ps1": "script",
    "hta": "script",
    "wsf": "script",
    "jar": "script",
    "docm": "macro_document",
    "xlsm": "macro_document",
    "pptm": "macro_document",
    "zip": "archive",
    "rar": "archive",
    "7z": "archive",
    "iso": "archive",
    "img": "archive",
    "htm": "html",
    "html": "html",
    "svg": "html",
    "pdf": "document",
    "doc": "document",
    "docx": "document",
    "xls": "document",
    "xlsx": "document",
    "ppt": "document",
    "pptx": "document",
    "txt": "document",
    "csv": "document",
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "gif": "image",
    "webp": "image",
}


@dataclass(frozen=True)
class ObservedAttachment:
    filename: str
    content_type: str
    extension: str
    risk_class: str
    double_extension: bool


@dataclass(frozen=True)
class Observation:
    subject: str
    date: str | None
    sender_display: str
    sender_address: str
    sender_domain: str
    reply_domain: str | None
    return_domain: str | None
    spf: str
    dkim: str
    dmarc: str
    links: tuple[tuple[str, str], ...]
    attachments: tuple[ObservedAttachment, ...]
    body: str


class _Anchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            found = dict(attrs).get("href")
            self._href = found or ""
            self._chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append(("".join(self._chunks).strip(), self._href.strip()))
            self._href = None
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._chunks.append(data)


def read_message(raw: str) -> Observation:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    if "\n\n" not in text and "\n" in text:
        lines = text.split("\n")
        body_at = next((i for i, line in enumerate(lines) if line and not _headerish(line)), None)
        if body_at:
            text = "\n".join(lines[:body_at]) + "\n\n" + "\n".join(lines[body_at:])
    message = message_from_string(text, policy=default_policy)
    plain, html = _bodies(message)
    links = _links(plain, html)
    body = plain or _visible_html(html)
    attachments = _attachments(message, raw)
    sender_name, sender_addr = _first(message.get("from"))
    _reply_name, reply_addr = _first(message.get("reply-to"))
    _return_name, return_addr = _first(message.get("return-path"))
    auth = _auth(message)
    return Observation(
        subject=str(message.get("subject") or ""),
        date=str(message.get("date") or "") or None,
        sender_display=sender_name,
        sender_address=sender_addr,
        sender_domain=_reg(sender_addr),
        reply_domain=_reg(reply_addr) or None,
        return_domain=_reg(return_addr) or None,
        spf=auth["spf"],
        dkim=auth["dkim"],
        dmarc=auth["dmarc"],
        links=tuple(links),
        attachments=tuple(attachments),
        body=body.strip(),
    )


def _headerish(line: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9-]+:\s*", line))


def _bodies(message: object) -> tuple[str, str]:
    plain: list[str] = []
    html: list[str] = []
    parts = message.walk() if hasattr(message, "walk") else [message]
    for part in parts:
        if part.get_content_maintype() == "multipart":
            continue
        disposition = (part.get_content_disposition() or "").lower()
        if disposition == "attachment" or part.get_filename():
            continue
        try:
            content = part.get_content()
        except Exception:
            payload = part.get_payload(decode=False)
            content = payload if isinstance(payload, str) else ""
        if not isinstance(content, str):
            continue
        if part.get_content_type() == "text/html":
            html.append(content)
        else:
            plain.append(content)
    return "\n".join(plain).strip(), "\n".join(html).strip()


def _links(plain: str, html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(text: str, href: str) -> None:
        href = href.strip().rstrip(".,);]")
        if not href or href.startswith(("mailto:", "javascript:", "#")):
            return
        key = (text.strip(), href)
        if key in seen:
            return
        seen.add(key)
        found.append(key)

    if html:
        parser = _Anchors()
        try:
            parser.feed(html)
        except Exception:
            parser.links = []
        for text, href in parser.links:
            add(text or href, href)
    for match in _URL.finditer(plain or ""):
        url = match.group(0).rstrip(".,);]")
        add(url, url)
    return found


def _visible_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def _attachments(message: object, raw: str) -> list[ObservedAttachment]:
    found: list[ObservedAttachment] = []
    seen: set[str] = set()
    parts = message.walk() if hasattr(message, "walk") else []
    for part in parts:
        filename = part.get_filename()
        disposition = (part.get_content_disposition() or "").lower()
        if not filename and disposition != "attachment":
            continue
        _add_attachment(found, seen, filename or "unknown", part.get_content_type() or "")
    for pattern in _PSEUDO:
        for name, kind in pattern.findall(raw):
            _add_attachment(found, seen, name.strip(), kind.strip())
    return found


def _add_attachment(found: list[ObservedAttachment], seen: set[str], filename: str, kind: str) -> None:
    clean = filename.strip().strip('"')
    key = clean.lower()
    if not clean or key in seen:
        return
    seen.add(key)
    parts = [part.lower() for part in clean.split(".") if part]
    extension = parts[-1] if len(parts) > 1 else ""
    earlier = parts[:-1]
    double = len(parts) >= 3 and any(part in _RISK for part in earlier) and extension in _RISK
    found.append(
        ObservedAttachment(
            filename=clean,
            content_type=kind or "application/octet-stream",
            extension=extension,
            risk_class=_RISK.get(extension, "other"),
            double_extension=double,
        )
    )


def _first(header: str | None) -> tuple[str, str]:
    if not header:
        return "", ""
    pairs = getaddresses([header])
    if not pairs:
        return "", ""
    name, address = pairs[0]
    return name.strip(), address.strip()


def _reg(address: str) -> str:
    host = host_of(address)
    if not host or is_ip(host):
        return host
    return registrable_domain(host)


def _auth(message: object) -> dict[str, str]:
    found = {"spf": "none", "dkim": "none", "dmarc": "none"}
    headers = []
    getter = getattr(message, "get_all", None)
    if getter:
        headers.extend(getter("authentication-results") or [])
    for header in headers:
        for method, raw in _AUTH.findall(str(header)):
            mapped = _AUTH_MAP.get(raw.lower(), "none")
            if _RANK[mapped] >= _RANK[found[method.lower()]]:
                found[method.lower()] = mapped
    if found["spf"] == "none":
        received = str(getattr(message, "get", lambda _key: "")("received-spf") or "")
        match = re.match(
            r"\s*(pass|fail|softfail|neutral|none|temperror|permerror)\b",
            received,
            re.IGNORECASE,
        )
        if match:
            found["spf"] = _AUTH_MAP.get(match.group(1).lower(), "none")
    return found
