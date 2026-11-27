"""Attachment metadata. Payloads are never decoded."""

from __future__ import annotations

import re

from layersight.models import Attachment, RiskClass

_RISKY_FINAL = {
    "exe", "scr", "com", "msi", "bat", "cmd", "js", "vbs", "ps1", "hta", "wsf", "jar", "htm", "html", "svg",
}
_BENIGN = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "jpg", "jpeg", "png", "gif"}
_BY_EXT: dict[str, RiskClass] = {}
for _ext, _risk in (
    ("exe", "executable"),
    ("scr", "executable"),
    ("com", "executable"),
    ("msi", "executable"),
    ("bat", "executable"),
    ("cmd", "executable"),
    ("js", "script"),
    ("vbs", "script"),
    ("ps1", "script"),
    ("hta", "script"),
    ("wsf", "script"),
    ("jar", "script"),
    ("docm", "macro_document"),
    ("xlsm", "macro_document"),
    ("pptm", "macro_document"),
    ("zip", "archive"),
    ("rar", "archive"),
    ("7z", "archive"),
    ("iso", "archive"),
    ("img", "archive"),
    ("gz", "archive"),
    ("htm", "html"),
    ("html", "html"),
    ("svg", "html"),
    ("pdf", "document"),
    ("doc", "document"),
    ("docx", "document"),
    ("xls", "document"),
    ("xlsx", "document"),
    ("ppt", "document"),
    ("pptx", "document"),
    ("txt", "document"),
    ("csv", "document"),
    ("rtf", "document"),
    ("png", "image"),
    ("jpg", "image"),
    ("jpeg", "image"),
    ("gif", "image"),
    ("webp", "image"),
):
    _BY_EXT[_ext] = _risk  # type: ignore[assignment]

_BY_MIME: dict[str, RiskClass] = {
    "application/x-msdownload": "executable",
    "application/x-msdos-program": "executable",
    "application/javascript": "script",
    "text/javascript": "script",
    "application/zip": "archive",
    "application/x-zip-compressed": "archive",
    "application/pdf": "document",
    "text/html": "html",
    "image/png": "image",
    "image/jpeg": "image",
}

_PSEUDO = (
    re.compile(r"(?im)^[ \t]*Attachment:\s*(?P<name>\S+)\s*\((?P<type>[^)\n]+)\)[ \t]*$"),
    re.compile(r"(?im)^[ \t]*\[Attachment:\s*(?P<name>[^;\]]+?)\s*;\s*(?P<type>[^\]]+?)\][ \t]*$"),
    re.compile(r"(?im)^[ \t]*X-Attachment:\s*(?P<name>[^;\n]+?)\s*;\s*type=(?P<type>\S+)[ \t]*$"),
)


def _extensions(filename: str) -> list[str]:
    base = filename.replace("\\", "/").split("/")[-1].strip().strip('"')
    parts = [part for part in base.lower().split(".") if part]
    return parts[1:] if len(parts) > 1 else []


def classify_attachment(filename: str, content_type: str) -> Attachment:
    clean = filename.replace("\\", "/").split("/")[-1].strip().strip('"') or "unknown"
    exts = _extensions(clean)
    last = exts[-1] if exts else ""
    risk: RiskClass = _BY_EXT.get(last, "other")
    if risk == "other":
        mime = content_type.split(";", 1)[0].strip().lower()
        risk = _BY_MIME.get(mime, "other")
    double = len(exts) >= 2 and exts[-1] in _RISKY_FINAL and any(ext in _BENIGN for ext in exts[:-1])
    return Attachment(
        filename=clean,
        content_type=content_type.strip() or "application/octet-stream",
        extension=last,
        risk_class=risk,
        double_extension=double,
    )


def take_pseudo_attachments(text: str) -> tuple[list[Attachment], str]:
    found: list[Attachment] = []
    kept: list[str] = []
    for line in text.split("\n"):
        matched = False
        for pattern in _PSEUDO:
            match = pattern.match(line)
            if match is not None:
                found.append(classify_attachment(match.group("name").strip(), match.group("type").strip()))
                matched = True
                break
        if not matched:
            kept.append(line)
    return found, "\n".join(kept)
