"""Links and visible text. HTML is parsed, never rendered in a browser and never fetched."""

from __future__ import annotations

from bs4 import BeautifulSoup, FeatureNotFound

from layersight.models import ParsedLink
from layersight.textutil import angle_links, plain_urls, refang, strip_url_tail


def _soup(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


def _href(value: object) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def links_from_html(html: str) -> tuple[list[ParsedLink], str]:
    soup = _soup(html)
    links: list[ParsedLink] = []
    for anchor in soup.find_all("a"):
        href = refang(_href(anchor.get("href"))).strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        text = anchor.get_text(" ", strip=True)
        links.append(ParsedLink(text=text, href=href, source="html"))
    rendered = soup.get_text("\n", strip=True)
    return links, rendered


def links_from_text(text: str) -> list[ParsedLink]:
    links: list[ParsedLink] = []
    consumed: list[tuple[int, int]] = []
    for visible, href, span in angle_links(text):
        links.append(ParsedLink(text=refang(visible), href=refang(href), source="text"))
        consumed.append(span)
    for url, span in plain_urls(text):
        if any(span[0] >= start and span[1] <= end for start, end in consumed):
            continue
        cleaned = refang(strip_url_tail(url))
        if cleaned:
            links.append(ParsedLink(text=cleaned, href=cleaned, source="text"))
    return links
