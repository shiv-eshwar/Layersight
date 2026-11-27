"""URL normalization shared by the parser and the link rules.

Analysis never fetches a URL. Defanging is for display; matching uses the real address.
"""

from __future__ import annotations

import re
import urllib.parse

_SCHEME = re.compile(r"(?i)^(?:https?|hxxps?)://")
_URL = re.compile(
    r"(?ix)"
    r"(?<![A-Za-z0-9@])("
    r"(?:https?|hxxps?)://[^\s<>\"')\]]+"
    r"|www\.[^\s<>\"')\]]+"
    r"|(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:/[^\s<>\"')\]]*)?"
    r"|(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|uk|gov|edu|info|biz|xyz|top|click|"
    r"link|ru|de|fr|app|dev|bank|zip|mov|us|io)\b(?:/[^\s<>\"')\]]*)?"
    r")"
)
_ANGLE = re.compile(
    r"(?P<text>(?:https?|hxxps?)://[^\s<>]+)\s*<(?P<href>(?:https?|hxxps?)://[^>\s]+)>"
)


def refang(value: str) -> str:
    text = value.strip()
    text = re.sub(r"(?i)\bhxxps://", "https://", text)
    text = re.sub(r"(?i)\bhxxp://", "http://", text)
    text = text.replace("[.]", ".").replace("(.)", ".").replace("{.}", ".")
    return text


def defang_url(url: str) -> str:
    text = url
    text = re.sub(r"(?i)^https://", "hxxps://", text)
    text = re.sub(r"(?i)^http://", "hxxp://", text)
    match = re.match(r"(?i)((?:hxxps?|https?)://)([^/\s]+)", text)
    if match is None:
        return text
    host = match.group(2).replace(".", "[.]")
    return match.group(1) + host + text[match.end() :]


def defang_text(text: str) -> str:
    return _URL.sub(lambda match: defang_url(refang(match.group(1))), text)


def strip_url_tail(url: str) -> str:
    return url.rstrip(".,;:!?\"'")


def host_of(value: str) -> str:
    """Host from a URL, an email address, or a bare domain. Empty when none is present."""
    text = refang(value).strip().strip("<>").strip()
    if not text:
        return ""
    if "@" in text and "://" not in text and "/" not in text:
        text = text.rsplit("@", 1)[-1]
    if text.startswith("//"):
        text = "https:" + text
    elif text.startswith("www.") or (
        "://" not in text and re.match(r"(?i)(?:\d{1,3}\.){3}\d{1,3}(?:/|$)", text)
    ):
        text = "http://" + text
    elif "://" not in text and re.match(r"(?i)[a-z0-9.-]+\.[a-z]{2,}", text):
        text = "http://" + text
    if "://" not in text:
        return text.lower().strip(".")
    parts = urllib.parse.urlsplit(text)
    host = parts.hostname or ""
    return host.lower().strip(".")


def split_http_url(value: str) -> tuple[str, str, str]:
    """Return scheme, host, and path. Scheme is empty when the value is not an http(s) URL."""
    text = refang(value).strip()
    if text.startswith("//"):
        text = "https:" + text
    if not _SCHEME.match(text):
        host = host_of(text)
        return "", host, ""
    parts = urllib.parse.urlsplit(text)
    return (parts.scheme or "").lower(), (parts.hostname or "").lower(), parts.path or ""


def angle_links(text: str) -> list[tuple[str, str, tuple[int, int]]]:
    found: list[tuple[str, str, tuple[int, int]]] = []
    for match in _ANGLE.finditer(text):
        found.append((strip_url_tail(match.group("text")), strip_url_tail(match.group("href")), match.span()))
    return found


def plain_urls(text: str) -> list[tuple[str, tuple[int, int]]]:
    found: list[tuple[str, tuple[int, int]]] = []
    for match in _URL.finditer(text):
        found.append((strip_url_tail(match.group(1)), match.span(1)))
    return found
