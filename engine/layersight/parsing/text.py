"""Defanging and URL cleanup. Display only; nothing is fetched."""

from __future__ import annotations

import re

_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def clean_url(url: str) -> str:
    return url.strip().rstrip(".,);]>\"'")


def defang(url: str) -> str:
    text = clean_url(url)
    lowered = text.lower()
    if lowered.startswith("https://"):
        scheme, rest = "hxxps://", text[8:]
    elif lowered.startswith("http://"):
        scheme, rest = "hxxp://", text[7:]
    else:
        scheme, rest = "", text
    slash = rest.find("/")
    host = rest if slash < 0 else rest[:slash]
    tail = "" if slash < 0 else rest[slash:]
    return scheme + host.replace(".", "[.]") + tail


def defang_text(text: str) -> str:
    return _URL.sub(lambda match: defang(match.group(0)), text)
